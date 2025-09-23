import asyncio
import datetime
import json
import os
import random
from collections import Counter
from itertools import cycle
from twikit import Client

# ---------------- Paths ----------------
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "account-configs", "accounts.json")
COOKIES_DIR = os.path.join(BASE_DIR, "account-cookies")

# ---------------- Scraper Settings ----------------
MAX_TWEETS = 500  # maximum tweets per scrape
PAGE_DELAY_RANGE = (2, 5)  # random delay between pages

# ---------------- Account Cycling ----------------
_account_cycle = None
_failed_accounts = set()

def load_accounts():
    """Load accounts from config file."""
    try:
        with open(ACCOUNTS_FILE, "r") as file:
            accounts = json.load(file)
        return accounts
    
    except Exception as e:
        print(f"[ERROR] Failed to load accounts: {e}")
        return []

def get_next_account():
    """Round-robin account selector with reset if all fail."""
    global _account_cycle, _failed_accounts

    accounts = load_accounts()
    active_accounts = [acct for acct in accounts if acct.get("status") == "active"]

    if not active_accounts:
        print("[ERROR] No active accounts available!")
        return None

    # Reset cycle if needed
    if _account_cycle is None or len(_failed_accounts) >= len(active_accounts):
        _account_cycle = cycle(active_accounts)
        _failed_accounts.clear()
        print(f"[INFO] Reset account cycle with {len(active_accounts)} active accounts.")

    account = next(_account_cycle)
    print(f"[INFO] Selected account: {account['username']}")
    return account

def mark_account_failed(username: str):
    """Mark account as failed to avoid reusing it endlessly."""
    global _failed_accounts
    _failed_accounts.add(username)
    print(f"[WARN] Account {username} marked as failed.")

# ---------------- Scraper ----------------
async def scrape_tweets(target_username: str):
    print(f"[INFO] Starting scrape for target: {target_username}")

    account = get_next_account()
    if not account:
        return {"error": "No active accounts available for scraping."}

    username = account["username"]
    email = account["email"]
    password = account["password"]
    user_agent = account.get("user_agent")

    os.makedirs(COOKIES_DIR, exist_ok=True)
    cookies_path = os.path.join(COOKIES_DIR, f"cookie_{username}.json")

    client = Client("en-US", user_agent=user_agent)

    try:
        print(f"[INFO] Logging in with account: {username}")
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
            cookies_file=cookies_path
        )
        print("[INFO] Login successful!")

        user = await client.get_user_by_screen_name(target_username)
        if not user:
            print("[ERROR] Target user not found!")
            return {"error": "User not found."}

        tweets_timestamp = []
        count = 0
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=180)

        print("[INFO] Fetching first page of tweets...")
        tweets_page = await user.get_tweets(tweet_type="Tweets", count=50)

        while tweets_page and count < MAX_TWEETS:
            for tweet in tweets_page:

                ts = tweet.created_at_datetime.astimezone(datetime.timezone.utc)
                
                if ts < cutoff_date:
                    print("[INFO] Reached cutoff date. Stopping fetch.")
                    tweets_page = None
                    break
                
                tweets_timestamp.append(ts)
                count += 1
                
                if count % 50 == 0:
                    print(f"[INFO] Fetched {count} tweets so far...")
                if count >= MAX_TWEETS:
                    break

            if tweets_page and hasattr(tweets_page, "next") and tweets_page.next:
                delay = random.uniform(*PAGE_DELAY_RANGE)
                
                print(f"[INFO] Sleeping {delay:.2f}s before next page...")
                await asyncio.sleep(delay)
                tweets_page = await tweets_page.next()
            
            else:
                break

        date_counts = Counter([ts.date() for ts in tweets_timestamp])

        user_info = {
            "username": user.screen_name,
            "name": user.name,
            "profile": user.profile_image_url,
            "tweet_count": user.statuses_count,
            "is_verified": user.is_blue_verified,
            "created_at": user.created_at_datetime.isoformat(),
            "has_default_profile_image": user.default_profile_image,
            "start_date": min(tweets_timestamp).isoformat() if tweets_timestamp else None,
            "end_date": datetime.datetime.now(datetime.timezone.utc).isoformat()
        }

        print(f"[INFO] Scraping complete. Total tweets fetched: {len(tweets_timestamp)}")
        return {
            "user_info": user_info,
            "tweets_per_day": {str(date): c for date, c in date_counts.items()},
            "total_tweets_fetched": len(tweets_timestamp)
        }

    except Exception as e:
        print(f"[ERROR] Exception while scraping with {username}: {e}")
        mark_account_failed(username)
        return {"error": f"Unable to fetch tweets: {e}"}

# ---------------- Test Run ----------------
if __name__ == "__main__":
    target_user = "sakkshm"
    result = asyncio.run(scrape_tweets(target_user))
    print("[RESULT]", json.dumps(result, indent=2, default=str))
