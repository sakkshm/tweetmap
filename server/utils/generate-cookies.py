import asyncio
import json
from twikit import Client

'''
,
  {
    "username": "MarcusLee324063",
    "email": "tweetmap81+tweetmap.extra2@gmail.com",
    "password": "HeatMap456$"
  },
  {
    "username": "AliceJohns50842",
    "email": "tweetmap81+tweetmap.extra1@gmail.com",
    "password": "TestPass123!"
  }
'''

"""
TODO: Look into Client setting/params to prevent blocking
- proxy
- captcha_solver
- user_agent
"""
import time

async def main():
    client = Client('en-US')

    try:
        with open("../account-configs/accounts.json", "r") as file:
            data = json.load(file)

            for person in data:

                print(person)
                cookies_path = f"../account-cookies/cookie_{person['username']}.json"

                #Create cookie file
                #open(cookies_path, "w").close()

                await client.login(
                    auth_info_1 = person['username'],
                    auth_info_2 = person['email'],
                    password = person['password'],
                    cookies_file = cookies_path
                )
                
                print(f"Cookie generated for {person['username']}")
                client.save_cookies(cookies_path)
                print(f"Cookie saved for {person['username']}")

                await asyncio.sleep(5)

                await client.logout()
                print(f"{person['username']} logged out!")

    except FileNotFoundError:
        print("Error: 'accounts.json' not found.")

    except json.JSONDecodeError as e:
        print("Error: Invalid JSON format in 'accounts.json'.")
        print(e)

    except Exception as e:
        print(e)


asyncio.run(main())