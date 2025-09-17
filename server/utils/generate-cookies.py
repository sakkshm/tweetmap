"""
TODO: Look into Client setting/params to prevent blocking
- proxy
- captcha_solver
- user_agent
"""

import asyncio
import json
import os
from twikit import Client

# File path where Twitter account credentials are stored
ACCOUNTS_FILE = "../account-configs/accounts.json"

# Directory where cookie files will be saved
COOKIES_DIR = "../account-cookies"

# Waiting time to avoid being rate-limited (sec)
TIMEOUT_DELAY = 5

async def main():
    """
    Main coroutine:
    - Reads account credentials from JSON
    - Logs into each account
    - Saves cookies for session persistence
    - Logs out safely
    """

    try:
        with open(ACCOUNTS_FILE, "r") as file:
            data = json.load(file)

            # Ensure cookies directory exists
            os.makedirs(COOKIES_DIR, exist_ok=True)

            for person in data:
                try:
                    client = Client('en-US')

                    # Path for saving the cookie file for this account
                    cookies_path = os.path.join(COOKIES_DIR, f"cookie_{person['username']}.json")

                    # Mask password before printing for safety
                    safe_person = {**person, "password": "***"}
                    print(f"\nTrying to get cookies for: \n{json.dumps(safe_person, indent=2)}")

                    # Skip login if cookie file already exists
                    if os.path.exists(cookies_path):
                        print(f"Cookie file already exists for {person['username']}, skipping...")
                        continue

                    await client.login(
                        auth_info_1=person['username'],
                        auth_info_2=person['email'],
                        password=person['password'],
                        cookies_file=cookies_path
                    )

                    print(f"Cookie generated for {person['username']}")

                    # Save cookies to file
                    client.save_cookies(cookies_path)
                    print(f"Cookie saved for {person['username']}")

                    # Wait some time to avoid being rate-limited
                    await asyncio.sleep(TIMEOUT_DELAY)

                except Exception as e:
                    # Catch and print errors specific to this account
                    print(f"Error handling account {person['username']}: {e}\n")

    except FileNotFoundError:
        print("Error: 'accounts.json' not found.")

    except json.JSONDecodeError as e:
        print("Error: Invalid JSON format in 'accounts.json'.")
        print(e)

    except Exception as e:
        # Catch any other unexpected errors
        print(e)


if __name__ == "__main__":
    asyncio.run(main())
