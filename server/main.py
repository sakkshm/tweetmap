import asyncio
import datetime
import json
import os
import random
from collections import Counter
from twikit import Client

ACCOUNTS_FILE = "./account-configs/accounts.json"
COOKIES_DIR = "./account-cookies"

TARGET_USERNAME = "sakkshm"
MAX_TWEETS = 500
PAGE_DELAY = 1.5  # seconds delay between pages


async def main():
    # Load accounts
    try:
        with open(ACCOUNTS_FILE, "r") as file:
            accounts = json.load(file)

    except FileNotFoundError:
        print("Error: 'accounts.json' not found.")
        return
    except json.JSONDecodeError as e:
        print("Error: Invalid JSON format in 'accounts.json'.")
        print(e)
        return

    if not accounts:
        print("No accounts found in the file.")
        return

    # Pick a random account
    account = random.choice(accounts)
    username = account['username']
    email = account['email']
    password = account['password']

    # Ensure cookies directory exists
    os.makedirs(COOKIES_DIR, exist_ok=True)
    cookies_path = os.path.join(COOKIES_DIR, f"cookie_{username}.json")

    client = Client('en-US')

    try:
        print(f"Logging in for {username}")

        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
            cookies_file=cookies_path
        )

        # Save cookies if file doesn't exist
        if not os.path.exists(cookies_path):
            client.save_cookies(cookies_path)
            print(f"Cookie saved for {username}")

        # --- Check if target user exists ---
        try:
            user = await client.get_user_by_screen_name(TARGET_USERNAME)
        except Exception as e:
            print(f"User '{TARGET_USERNAME}' does not exist or could not be fetched.")
            print(f"Error: {e}")
            return

        if not user:
            print(f"User '{TARGET_USERNAME}' not found.")
            return

        print(f"Getting tweets for {TARGET_USERNAME}")

        tweets_timestamp = []
        count = 0

        # --- Define cutoff date (6 months ago, UTC) ---
        cutoff_date = datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(days=6 * 30)

        # Fetch initial page
        tweets_page = await user.get_tweets(tweet_type='Tweets', count=50)

        while tweets_page and count < MAX_TWEETS:
            for tweet in tweets_page:
                ts = tweet.created_at_datetime.astimezone(datetime.timezone.utc)

                # Skip tweets older than 6 months
                if ts < cutoff_date:
                    print(f"Stopping at tweet older than 6 months: {ts.isoformat()}")
                    tweets_page = None
                    break

                tweets_timestamp.append(ts)
                count += 1

                if count >= MAX_TWEETS:
                    break

            # Fetch next page if exists
            if tweets_page and hasattr(tweets_page, 'next') and tweets_page.next:
                await asyncio.sleep(PAGE_DELAY)
                tweets_page = await tweets_page.next()
            else:
                break

        # Convert timestamps to dates
        dates = [ts.date() for ts in tweets_timestamp]

        # Count occurrences per date
        date_counts = Counter(dates)

        print("\nTweets per day:")
        for date, c in date_counts.items():
            print(f"{date}: {c}")

        # Extract user info
        x_username = user.screen_name
        name = user.name
        profile = user.profile_image_url
        tweet_count = user.statuses_count
        is_verified = user.is_blue_verified
        created_at = user.created_at_datetime
        has_default_profile_image = user.default_profile_image

        # --- Find start_date & end_date in UTC ---
        if tweets_timestamp:
            start_date = min(tweets_timestamp)
        else:
            start_date = None

        end_date = datetime.datetime.now(datetime.timezone.utc)

        user_info = {
            "username": x_username,
            "name": name,
            "profile": profile,
            "tweet_count": tweet_count,
            "is_verified": is_verified,
            "created_at": created_at,
            "has_default_profile_image": has_default_profile_image,
            "start_date": start_date.isoformat() if start_date else None,
            "end_date": end_date.isoformat()
        }

        print(user_info)

        print(f"\nFetched {len(tweets_timestamp)} tweets for {TARGET_USERNAME}")

    except Exception as e:
        print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(main())
