import json
import os

# Paths
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ACCOUNTS_FILE = os.path.join(BASE_DIR, "../account-configs/accounts.json")
COOKIES_DIR = os.path.join(BASE_DIR, "../account-cookies")
os.makedirs(COOKIES_DIR, exist_ok=True)

# Keys to prioritize in final cookie
DESIRED_KEYS = [
    "guest_id_marketing","guest_id_ads","personalization_id","guest_id","__cf_bm",
    "att","_twitter_sess","kdt","twid","ct0","auth_token"
]

def input_cookie_and_save(account):
    username = account.get("username", "unknown")
    print(f"\n--- Processing account: {username} ---")
    print(f"USERNAME: {account.get('username', '')}")
    print(f"EMAIL:    {account.get('email', '')}")
    print(f"PASSWORD: {account.get('password', '')}")
    print("\nPaste the cookie JSON (list of objects or flat dict). End input with Ctrl+D (Linux/mac) or Ctrl+Z + Enter (Windows):")

    # Read multiline input until EOF
    lines = []
    try:
        while True:
            line = input()
            lines.append(line)
    except EOFError:
        pass

    raw = "\n".join(lines)

    try:
        data = json.loads(raw)
    except json.JSONDecodeError as e:
        print("Invalid JSON! Skipping this account.", e)
        return

    # Convert list of objects into {name: value}
    if isinstance(data, list):
        cookie_map = {c['name']: c['value'] for c in data}
    elif isinstance(data, dict):
        cookie_map = data
    else:
        print("Unexpected format! Must be a list or dict. Skipping.")
        return

    # Build final dict with desired key order
    final_cookies = {}
    for key in DESIRED_KEYS:
        if key in cookie_map:
            final_cookies[key] = cookie_map[key]
    for k, v in cookie_map.items():
        if k not in final_cookies:
            final_cookies[k] = v

    # Save to file
    cookie_path = os.path.join(COOKIES_DIR, f"cookie_{username}.json")
    with open(cookie_path, "w", encoding="utf-8") as f:
        json.dump(final_cookies, f, indent=2)

    print(f"Saved cookies for {username} -> {cookie_path}")
    print("Keys saved (in order):", list(final_cookies.keys()))

def main():
    # Load accounts
    try:
        with open(ACCOUNTS_FILE, 'r', encoding='utf-8') as f:
            accounts = json.load(f)
    except FileNotFoundError:
        print(f"Accounts file not found: {ACCOUNTS_FILE}")
        return
    except json.JSONDecodeError as e:
        print(f"Invalid JSON in accounts file: {e}")
        return

    for account in accounts:
        if account.get("status") != "active":
            print(f"Skipping inactive account: {account.get('username', '')}")
            continue

        cookie_path = os.path.join(COOKIES_DIR, f"cookie_{account.get('username', 'unknown')}.json")
        if os.path.exists(cookie_path):
            print(f"Cookie already exists for {account.get('username', '')}, skipping...")
            continue

        input_cookie_and_save(account)

if __name__ == "__main__":
    main()
