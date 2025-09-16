import asyncio
from twikit import Client

USERNAME = 'JohnDavid199144'
EMAIL = 'tweetmap81+tweetmap.extra3@gmail.com'
PASSWORD = 'TestPass#003'

"""
TODO: Look into Client setting/params to prevent blocking
- proxy
- captcha_solver
- user_agent
"""
client = Client('en-US')

async def main():
    # Login
    await client.login(
        auth_info_1=USERNAME,
        auth_info_2=EMAIL,
        password=PASSWORD,
        cookies_file='cookies.json'
    )

    # Get user
    user = await client.get_user_by_screen_name('elonmusk')

    # Fetch initial tweets
    tweets = await user.get_tweets(tweet_type='Tweets', count=50)

    for tweet in tweets:
        print(tweet)

    # while tweets:

    #     if hasattr(tweets, 'next') and tweets.next:
    #         tweets = await tweets.next()
    #     else:
    #         break

asyncio.run(main())
