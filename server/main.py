import asyncio
import time
import uuid
import os
from datetime import datetime, timezone

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi import Query
import html

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from supabase import create_client, Client
from dotenv import load_dotenv

from utils.scrape_tweets import scrape_tweets

load_dotenv()

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # service role key
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # default 1 hour
WORKER_COUNT = int(os.getenv("WORKER_COUNT", 3))  # default 3 workers
JOB_TTL = int(os.getenv("JOB_TTL", 3600))  # jobs expire after 1h
SUPABASE_IMAGE_PUBLIC_BASE = os.getenv("SUPABASE_IMAGE_PUBLIC_BASE") 

TWITTER_BOT_USER_AGENTS = [
    "Twitterbot",
]

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

# ---------------- Supabase client ----------------
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def db_execute(func, *args, **kwargs):
    """Run blocking supabase call in thread pool to avoid blocking event loop."""
    return await asyncio.to_thread(func, *args, **kwargs)

# ---------------- FastAPI setup ----------------
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Rate Limiter ----------------
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------- Job queue ----------------
job_queue = asyncio.Queue()
jobs = {}  # {job_id: {"status": str, "result": dict, "created": datetime}}

async def worker(worker_id: int):
    """Worker that processes scrape jobs."""
    while True:
        job_id, username = await job_queue.get()
        jobs[job_id]["status"] = "fetching"
        print(f"[Worker {worker_id}] Processing job {job_id} for {username}")
        
        try:
            result = await scrape_tweets(username)
        
            if result.get("error"):
                jobs[job_id]["status"] = "error"
                jobs[job_id]["result"] = {"error": result.get("error")}
            else:
                await db_execute(
                    supabase.table("tweet_results")
                    .upsert(
                        {
                            "username": username,
                            "result": result,
                            "last_updated": datetime.now(timezone.utc).isoformat()
                        },
                        on_conflict="username" 
                    ).execute
                )
        
                jobs[job_id]["status"] = "done"
                jobs[job_id]["result"] = result
        
        except Exception as e:
            print(f"[Worker {worker_id}] Error: {e}")
            jobs[job_id]["status"] = "error"
            jobs[job_id]["result"] = {"error": str(e)}
        
        finally:
            job_queue.task_done()

async def cleanup_jobs():
    """Periodically remove old jobs to prevent memory bloat."""
    while True:
        now = datetime.now(timezone.utc)
        expired = [job_id for job_id, data in jobs.items()
                   if (now - data["created"]).total_seconds() > JOB_TTL]
        for job_id in expired:
            jobs.pop(job_id, None)
            print(f"Cleaned up expired job {job_id}")
        await asyncio.sleep(60)  # check every minute

@app.on_event("startup")
async def startup_event():
    # Start multiple workers
    for i in range(WORKER_COUNT):
        asyncio.create_task(worker(i + 1))
    # Start cleanup task
    asyncio.create_task(cleanup_jobs())
    print(f"Started {WORKER_COUNT} workers and cleanup task")

# ---------------- API Endpoints ----------------
@app.get("/")
@limiter.limit("10/minute")
def read_root(request: Request):
    return {"message": "Server Running!"}

@app.post("/fetch/{username}")
@limiter.limit("10/minute")
async def fetch(username: str, request: Request):
    # Check Supabase cache
    response = await db_execute(
        supabase.table("tweet_results").select("*").eq("username", username).execute
    )
    existing = response.data[0] if response.data else None

    if existing:
        last_updated = datetime.fromisoformat(existing["last_updated"])
        if last_updated.tzinfo is None:
            last_updated = last_updated.replace(tzinfo=timezone.utc)
        age = (datetime.now(timezone.utc) - last_updated).total_seconds()
        if age < CACHE_TTL:
            return {"job_id": None, "cached": True, "fresh": True, "result": existing["result"]}

        # Cached but stale
        job_id = str(uuid.uuid4())
        jobs[job_id] = {"status": "queued", "result": None, "created": datetime.now(timezone.utc)}
        await job_queue.put((job_id, username))
        return {"job_id": job_id, "cached": True, "fresh": False, "result": existing["result"]}

    # Not cached: new scrape
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "result": None, "created": datetime.now(timezone.utc)}
    await job_queue.put((job_id, username))
    return {"job_id": job_id, "cached": False, "fresh": False}

@app.get("/status/{job_id}")
@limiter.limit("30/minute")
async def status(job_id: str, request: Request):
    return jobs.get(job_id, {"error": "Invalid job id"})

@app.get("/result/{job_id}")
@limiter.limit("10/minute")
async def result(job_id: str, request: Request):
    job = jobs.get(job_id)
    if not job:
        return {"error": "Invalid job id"}
    if job["status"] != "done":
        return {"status": job["status"]}
    return job["result"]


@app.get("/share/{username}", response_class=HTMLResponse)
async def share_heatmap(request: Request, username: str):
    # Construct a public-friendly URL with cache buster
    timestamp = int(time.time())
    image_url = f"{SUPABASE_IMAGE_PUBLIC_BASE}/{username}.png?v={timestamp}"
    safe_url = html.escape(image_url, quote=True)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>@{username}'s Heatmap</title>

        <!-- Twitter Card -->
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:title" content="@{username}'s Heatmap">
        <meta name="twitter:description" content="Generated a heatmap of my tweets!">
        <meta name="twitter:image" content="{safe_url}">

        <!-- Open Graph -->
        <meta property="og:title" content="@{username}'s Heatmap">
        <meta property="og:description" content="Generated a heatmap of my tweets!">
        <meta property="og:image" content="{safe_url}">
    </head>
    <body style="display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; text-align:center; font-family:Arial, sans-serif; background: #f5f7fa; color:#333; padding:20px;">

        <h1 style="font-size:2.5rem; margin-bottom:20px;">@{username}'s Heatmap</h1>

        <img src="{safe_url}" alt="Heatmap for {username}" 
            style="max-width:90%; height:auto; border-radius:15px; box-shadow:0 8px 20px rgba(0,0,0,0.2); margin-bottom:30px;">

        <a href="https://tweetmap.sakkshm.me" style="text-decoration:none;">
            <button style="
                padding:15px 30px; 
                font-size:1.2rem; 
                font-weight:bold; 
                color:white; 
                background:  #2575fc;
                border:none; 
                border-radius:50px; 
                cursor:pointer; 
                transition: all 0.3s ease;
                box-shadow: 0 5px 15px rgba(0,0,0,0.2);
            " 
            onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 10px 25px rgba(0,0,0,0.3)';" 
            onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 5px 15px rgba(0,0,0,0.2)';">
                Generate Your Own
            </button>
        </a>

    </body>
    </html>
    """
    return HTMLResponse(content=html_content)