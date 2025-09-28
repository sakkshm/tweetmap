import asyncio
import re
import time
import uuid
import os
import base64
from datetime import datetime, timezone
from collections import defaultdict
import signal
import html

from fastapi import FastAPI, Request, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from supabase import create_client, Client
from dotenv import load_dotenv

from utils.scrape_tweets import scrape_tweets

# ---------------- Load environment variables ----------------
load_dotenv()  # Load .env file for secrets and config

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # Service role key
CACHE_TTL = int(os.getenv("CACHE_TTL", 3600))  # Cache duration for DB results
WORKER_COUNT = int(os.getenv("WORKER_COUNT", 3))  # Background worker count
JOB_TTL = int(os.getenv("JOB_TTL", 3600))  # Time-to-live for jobs in memory
SUPABASE_IMAGE_PUBLIC_BASE = os.getenv("SUPABASE_IMAGE_PUBLIC_BASE")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env")

# ---------------- Supabase client ----------------
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

async def db_execute(func, *args, **kwargs):
    """
    Execute blocking Supabase SDK calls in a thread pool.
    Prevents blocking the main asyncio event loop.
    """
    return await asyncio.to_thread(func, *args, **kwargs)

# ---------------- FastAPI setup ----------------
app = FastAPI()

# Enable Cross-Origin Resource Sharing
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allow all origins (change in prod!)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ---------------- Rate Limiter ----------------
limiter = Limiter(key_func=get_remote_address, default_limits=["5/minute"])
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ---------------- IP Ban / Abuse Prevention ----------------
banned_ips = {}
ip_hits = defaultdict(list)

BAN_THRESHOLD = 20  # Max requests within BAN_WINDOW
BAN_WINDOW = 60     # Seconds window
BAN_DURATION = 600  # Ban duration in seconds

def get_client_ip(request: Request):
    """Return the client IP for rate-limiting / banning."""
    return get_remote_address(request)

@app.middleware("http")
async def block_banned_ips(request: Request, call_next):
    """
    Middleware to block abusive IPs.
    Tracks request timestamps and bans IPs exceeding the threshold.
    """
    client_ip = get_client_ip(request)

    # If IP is currently banned
    if client_ip in banned_ips:
        ban_expires = banned_ips[client_ip]
        if time.time() < ban_expires:
            return JSONResponse(
                status_code=429,
                content={"error": "Too many requests, try again later."}
            )
        else:
            del banned_ips[client_ip]  # Ban expired, remove

    # Track request times for IP
    now = time.time()
    ip_hits[client_ip].append(now)
    ip_hits[client_ip] = [t for t in ip_hits[client_ip] if now - t < BAN_WINDOW]

    # Ban IP if threshold exceeded
    if len(ip_hits[client_ip]) > BAN_THRESHOLD:
        banned_ips[client_ip] = now + BAN_DURATION
        return JSONResponse(
            status_code=429,
            content={"error": f"IP banned for {BAN_DURATION//60} minutes due to abuse"}
        )

    # Continue request processing
    return await call_next(request)

# ---------------- Job Queue ----------------
job_queue = asyncio.Queue()  # Queue for background scraping jobs
jobs = {}                     # In-memory job metadata {job_id: {"status": str, "result": dict, "created": datetime}}
worker_tasks = []             # List of background worker tasks

# ---------------- Helper Functions ----------------
def sanitize_username(input_str: str) -> str:
    """Strip whitespace and remove leading @."""
    username = input_str.strip()
    if username.startswith("@"):
        username = username[1:]
    return username

def is_valid_twitter_username(username: str) -> bool:
    """Validate Twitter username according to Twitter rules."""
    sanitized_username = sanitize_username(username)
    username_regex = re.compile(r"^(?!.*\.\.)(?!.*\.$)[A-Za-z0-9_]{1,15}$")
    return bool(username_regex.match(sanitized_username))

# ---------------- Worker Function ----------------
async def worker(worker_id: int):
    """
    Background worker to process scraping jobs.
    Each job:
        - Calls scrape_tweets()
        - Saves result to Supabase
        - Updates job status
    """
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
                # Save result to Supabase (upsert)
                await db_execute(
                    supabase.table("tweet_results")
                    .upsert({
                        "username": username,
                        "result": result,
                        "last_updated": datetime.now(timezone.utc).isoformat()
                    }, on_conflict="username").execute
                )
                jobs[job_id]["status"] = "done"
                jobs[job_id]["result"] = result

        except Exception as e:
            print(f"[Worker {worker_id}] Error: {e}")
            jobs[job_id]["status"] = "error"
            jobs[job_id]["result"] = {"error": str(e)}

        finally:
            job_queue.task_done()

# ---------------- Job Cleanup ----------------
async def cleanup_jobs():
    """Periodically remove expired jobs from memory to prevent unbounded growth."""
    while True:
        now = datetime.now(timezone.utc)
        expired = [job_id for job_id, data in jobs.items()
                   if (now - data["created"]).total_seconds() > JOB_TTL]
        for job_id in expired:
            jobs.pop(job_id, None)
            print(f"Cleaned up expired job {job_id}")
        await asyncio.sleep(60)

# ---------------- Startup & Shutdown Events ----------------
@app.on_event("startup")
async def startup_event():
    """Start background workers and cleanup task."""
    global worker_tasks
    for i in range(WORKER_COUNT):
        task = asyncio.create_task(worker(i + 1))
        worker_tasks.append(task)
    cleanup_task = asyncio.create_task(cleanup_jobs())
    worker_tasks.append(cleanup_task)
    print(f"Started {WORKER_COUNT} workers and cleanup task")

@app.on_event("shutdown")
async def shutdown_event():
    """Graceful shutdown: cancel workers and close DB connections."""
    print("Shutting down gracefully...")
    for task in worker_tasks:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    try:
        await db_execute(supabase.auth.sign_out)
    except Exception:
        pass
    print("Shutdown complete.")

# Handle signals for graceful shutdown
def handle_exit(sig, frame):
    print(f"Received signal {sig}. Exiting...")
    loop = asyncio.get_event_loop()
    loop.create_task(shutdown_event())
    loop.stop()

signal.signal(signal.SIGINT, handle_exit)
signal.signal(signal.SIGTERM, handle_exit)

# ---------------- API Endpoints ----------------
@app.get("/")
@limiter.limit("10/minute")
def read_root(request: Request):
    """Health check endpoint."""
    return {"message": "Server Running!"}

@app.post("/fetch/{username}")
@limiter.limit("3/minute")
async def fetch(username: str, request: Request):
    """
    Start a scraping job:
        - Returns cached result if fresh
        - Queues new job if stale or not cached
    """
    username = sanitize_username(username)
    if not is_valid_twitter_username(username):
        return {"error": "Invalid username"}

    # Check cache in Supabase
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

    # Queue new job
    job_id = str(uuid.uuid4())
    jobs[job_id] = {"status": "queued", "result": None, "created": datetime.now(timezone.utc)}
    await job_queue.put((job_id, username))
    return {"job_id": job_id, "cached": False, "fresh": False}

@app.get("/status/{job_id}")
@limiter.limit("30/minute")
async def status(job_id: str, request: Request):
    """Get status of a queued/fetching job."""
    return jobs.get(job_id, {"error": "Invalid job id"})

@app.get("/result/{job_id}")
@limiter.limit("30/minute")
async def result(job_id: str, request: Request):
    """Get result of a completed job."""
    job = jobs.get(job_id)
    if not job:
        return {"error": "Invalid job id"}
    if job["status"] != "done":
        return {"status": job["status"]}
    return job["result"]

@app.post("/upload/{username}")
@limiter.limit("3/minute")
async def upload_heatmap(
    request: Request,
    username: str,
    file: UploadFile = File(None),
    data_url: str = Form(None)
):
    """
    Upload a heatmap image:
        - Accepts file upload or data_url (base64)
        - Checks cache to avoid re-uploading
    """
    username = sanitize_username(username)
    if not is_valid_twitter_username(username):
        return {"error": "Invalid username"}

    try:
        storage = supabase.storage.from_("heatmaps")
        filename = f"heatmaps/{username}.png"
        files = await db_execute(storage.list, path="heatmaps")

        existing_file = next((f for f in files if f["name"] == f"{username}.png"), None)
        now_ts = datetime.now(timezone.utc).timestamp()

        if existing_file:
            updated_at = datetime.fromisoformat(existing_file["updated_at"].replace("Z", "+00:00")).timestamp()
            age = now_ts - updated_at
            if age < CACHE_TTL:
                public_url_data = storage.get_public_url(filename)
                return {"url": public_url_data}

        # Read file bytes
        if file:
            f_bytes = await file.read()
        elif data_url:
            if "," in data_url:
                _, encoded = data_url.split(",", 1)
            else:
                encoded = data_url
            f_bytes = base64.b64decode(encoded)
        else:
            return {"error": "No file or data_url provided"}

        supabase.storage.from_("heatmaps").upload(
            file=f_bytes, 
            path=filename, 
            file_options={"cache-control": "3600", "upsert": "true", "content-type": "image/png"}
        )

        public_url_data = storage.get_public_url(filename)
        return {"url": public_url_data}

    except Exception as e:
        return {"error": str(e)}

@app.get("/share/{username}", response_class=HTMLResponse)
async def share_heatmap(request: Request, username: str):
    """Serve a shareable HTML page with the heatmap image."""
    username = sanitize_username(username)
    if not is_valid_twitter_username(username):
        return {"error": "Invalid username"}

    timestamp = int(time.time())
    image_url = f"{SUPABASE_IMAGE_PUBLIC_BASE}/{username}.png?v={timestamp}"
    safe_url = html.escape(image_url, quote=True)

    html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
        <meta charset="UTF-8">
        <title>@{username}'s Heatmap</title>
        <meta name="twitter:card" content="summary_large_image">
        <meta name="twitter:title" content="@{username}'s Heatmap">
        <meta name="twitter:description" content="Generated a heatmap of my tweets!">
        <meta name="twitter:image" content="{safe_url}">
        <meta property="og:title" content="@{username}'s Heatmap">
        <meta property="og:description" content="Generated a heatmap of my tweets!">
        <meta property="og:image" content="{safe_url}">
    </head>
    <body style="display:flex; flex-direction:column; justify-content:center; align-items:center; min-height:100vh; text-align:center; font-family:Arial, sans-serif; background:#f5f7fa; color:#333; padding:20px;">
        <h1 style="font-size:2.5rem; margin-bottom:20px;">@{username}'s Heatmap</h1>
        <img src="{safe_url}" alt="Heatmap for {username}" style="max-width:90%; height:auto; border-radius:15px; box-shadow:0 8px 20px rgba(0,0,0,0.2); margin-bottom:30px;">
        <a href="https://tweetmap.sakkshm.me" style="text-decoration:none;">
            <button style="padding:15px 30px; font-size:1.2rem; font-weight:bold; color:white; background:#2575fc; border:none; border-radius:50px; cursor:pointer; transition:all 0.3s ease; box-shadow:0 5px 15px rgba(0,0,0,0.2);" 
                onmouseover="this.style.transform='scale(1.05)'; this.style.boxShadow='0 10px 25px rgba(0,0,0,0.3)';" 
                onmouseout="this.style.transform='scale(1)'; this.style.boxShadow='0 5px 15px rgba(0,0,0,0.2)';">
                Generate Your Own
            </button>
        </a>
    </body>
    </html>
    """
    return HTMLResponse(content=html_content)

# ---------------- Health Check Endpoints ----------------
@app.get("/health", tags=["Health"])
async def health():
    """
    Health check endpoint.
    Returns status of app, DB, queue size, and active jobs.
    """
    try:
        response = await db_execute(supabase.table("tweet_results").select("username").limit(1).execute)
        db_status = "ok" if response.data is not None else "fail"
    except Exception:
        db_status = "fail"

    status = {
        "app": "ok",
        "db": db_status,
        "jobs_in_queue": job_queue.qsize(),
        "active_jobs": len([j for j in jobs.values() if j["status"] == "fetching"])
    }

    return JSONResponse(status_code=200 if db_status == "ok" else 503, content=status)

@app.get("/ready", tags=["Health"])
async def readiness():
    """Readiness probe endpoint. Returns 200 if server is ready to accept requests."""
    return JSONResponse(status_code=200, content={"ready": True})
