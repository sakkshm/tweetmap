import json, time, os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "../account-configs/accounts.json")
COOKIES_DIR = os.path.join(BASE_DIR, "../account-cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)

# Keys we want to prioritize in the final cookie.json
DESIRED_KEYS = [
    "guest_id_marketing","guest_id_ads","personalization_id","guest_id","__cf_bm",
    "att","_twitter_sess","kdt","twid","ct0","auth_token"
]

# Delay between accounts to reduce rate-limits
TIMEOUT_DELAY = 30  # seconds

def save_cookies(driver, username):
    cookies = driver.get_cookies()
    cookie_obj = {c['name']: c['value'] for c in cookies}

    final = {}
    for k in DESIRED_KEYS:
        if k in cookie_obj:
            final[k] = cookie_obj[k]
    for k, v in cookie_obj.items():
        if k not in final:
            final[k] = v

    cookie_path = os.path.join(COOKIES_DIR, f"cookie_{username}.json")
    with open(cookie_path, 'w', encoding='utf-8') as f:
        json.dump(final, f, indent=2)

    print(f"Saved {len(final)} cookies for {username} -> {cookie_path}")
    print("Preview keys:", list(final.keys()))

def format_account_block(account):
    """
    Return a nicely formatted block of account info for printing and copying.
    """
    block = (
        "==================== COPY-PASTE CREDENTIALS ====================\n"
        f"USERNAME: {account.get('username')}\n"
        f"EMAIL:    {account.get('email')}\n"
        f"PASSWORD: {account.get('password')}\n"
        f"USER-AGENT:\n{account.get('user_agent')}\n"
        "================================================================\n"
        "Tip: paste the username/email and password into the browser login form.\n"
    )
    return block

def login_and_save(account):
    print(f"\nProcessing account: {account['username']}")

    options = webdriver.ChromeOptions()
    options.add_argument("--start-maximized")
    # Set account-specific user-agent
    if account.get("user_agent"):
        options.add_argument(f"user-agent={account['user_agent']}")
    # You can add proxy/captcha settings here if needed

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        # Open login page first so you can paste credentials
        driver.get("https://x.com/login")

        # Print account info block for easy copy
        acct_block = format_account_block(account)
        print("\n" + acct_block)

        input("After you've submitted the credentials in the browser, press ENTER here to continue and save cookies...")

        # navigate to main domain to collect cookies
        driver.get("https://x.com")
        time.sleep(2)

        save_cookies(driver, account['username'])
    finally:
        time.sleep(1)
        driver.quit()

def main():
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            accounts = json.load(f)

        for acc in accounts:
            if acc.get("status") != "active":
                print(f"Skipping inactive account: {acc.get('username')}")
                continue

            cookie_path = os.path.join(COOKIES_DIR, f"cookie_{acc['username']}.json")
            if os.path.exists(cookie_path):
                print(f"Cookie already exists for {acc['username']}, skipping...")
                continue

            login_and_save(acc)
            print(f"Waiting {TIMEOUT_DELAY} seconds before next account...")
            time.sleep(TIMEOUT_DELAY)

    except FileNotFoundError:
        print(f"Accounts file not found: {ACCOUNTS_FILE}")
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in accounts file: {e}")
    except Exception as e:
        print("Unexpected error:", e)

if __name__ == "__main__":
    main()
