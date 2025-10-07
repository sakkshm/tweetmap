# 𝕏 TweetMap

TweetMap lets you visualize your Twitter/X activity as a GitHub-style heatmap.

It scrapes your tweets, processes them into daily counts, and renders them as an interactive heatmap. You can download your heatmap as a PNG or share it publicly with Twitter/X.

[Demo Video](https://youtu.be/8U8RCc7iNV4)

## Features

* Enter a Twitter/X username and generate a tweet activity heatmap.
* GitHub-style heatmap visualization of tweets over the last six months.
* Scraper supports multiple accounts with automatic account cycling and failure handling.
* FastAPI backend with job queue and caching using Supabase.
* React frontend with Tailwind CSS and Shadcn UI components.
* Save heatmap as PNG.
* Share the heatmap on Twitter/X with Open Graph cards.
* Built-in rate limiting and scraping delays to prevent bans/abuse.


## Architecture

```
React + Vite (frontend)  -->  FastAPI (backend)  -->  Supabase (DB + Storage)
```



### Backend

* **FastAPI & uvicorn**
* **Job Queue**: Handles scraping requests asynchronously so the frontend does not block.
* **Supabase Database**: Caches results in `tweet_results` to avoid redundant scrapes.
* **Supabase Storage**: Stores generated heatmap PNGs in `heatmaps` bucket.
* **SlowAPI**: Provides rate limiting to protect against abuse.

### Scraper (twikit-based)

* Built with [twikit](https://github.com/twikit) for login and tweet fetching.
* **Multi-account support** via `accounts.json` (credentials + user-agent), with per-account cookies stored in `account-cookies/`.
* **Round-robin cycling** for account rotation; failed accounts skipped until reset.
* **Rate control**: up to `MAX_TWEETS` (default 500), with random delays (`PAGE_DELAY_RANGE`) to mimic human activity.
* **Async execution**: uses `asyncio` with FastAPI’s event loop for non-blocking scraping and delays.
* **Collected data**:
  * `tweets_per_day`: daily tweet counts.
  * `user_info`: metadata (profile image, verified status, tweet count, created_at, etc.).
* **Cutoff**: restricts scraping to past 180 days for heatmap relevance.

### Supabase

* **Database**: Stores cached scrape results keyed by username and timestamp.
* **Storage**: Public bucket for heatmap PNGs, used for social sharing.
* **Row-Level Security (RLS)**: Configured for controlled access.

## Techniques Used

* **Asynchronous Programming** (`asyncio`, `await`): Non-blocking scraping for scalability.
* **Account Pooling and Cycling** (`itertools.cycle`): Distributes load across multiple accounts to avoid bans.
* **Account Failover**: Failed accounts are tracked and skipped automatically.
* **Cookie Management**: Session cookies are persisted per account to reduce logins.
* **Randomized Delays** (`random.uniform`): Mimics human browsing behavior to avoid detection.
* **Rate Limiting** (SlowAPI): Ensures fair usage of backend APIs.
* **Caching**: Scraped data is cached in Supabase for re-use within a TTL.
* **Data Aggregation** (`collections.Counter`): Efficiently counts tweets per day.
* **Cutoff Filtering**: Limits data collection to a 6-month window.
* **Open Graph / Twitter Cards**: Provides shareable previews for generated heatmaps.
* **PNG Export**: Allows client-side saving and server-side sharing of visualizations.
* **Job Queue with Workers**: Enables background tasks without blocking API calls.


## Getting Started

### Clone the repository

```bash
git clone https://github.com/sakkshm/tweetmap.git
cd tweetmap
```

### Backend Setup (FastAPI)

Create a `.env` file in `backend/`:

```env
SUPABASE_URL=your-supabase-url
SUPABASE_KEY=your-supabase-service-role-key
SUPABASE_IMAGE_PUBLIC_BASE=https://<project-id>.supabase.co/storage/v1/object/public/heatmaps

CACHE_TTL=3600
WORKER_COUNT=3
JOB_TTL=3600
```

Install dependencies:

```bash
cd backend
pip install -r requirements.txt
```

Run the backend:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

### Frontend Setup (React + Vite)

```bash
cd frontend
npm install
```

Add `.env` in `frontend/`:

```env
VITE_PUBLIC_SERVER_URL=http://localhost:8000
```

Run the frontend:

```bash
npm run dev
```

Open [http://localhost:5173](http://localhost:5173).

---

## API Endpoints

| Endpoint             | Method | Description                              |
| -------------------- | ------ | ---------------------------------------- |
| `/fetch/{username}`  | POST   | Start or fetch scrape job for a username |
| `/status/{job_id}`   | GET    | Check status of a job                    |
| `/result/{job_id}`   | GET    | Fetch job result once done               |
| `/upload/{username}` | POST   | Upload heatmap PNG to Supabase           |
| `/share/{username}`  | GET    | Public share page with OG/Twitter card   |


## Tech Stack

* **Frontend**: React, Vite, Tailwind CSS, Shadcn UI, lucide-react
* **Backend**: FastAPI, twikit, asyncio, Supabase, SlowAPI, uvicorn
* **Infrastructure**: Supabase (Postgres + Storage)

