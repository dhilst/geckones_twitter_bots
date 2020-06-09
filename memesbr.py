import os
import asyncio
from datetime import datetime, timedelta

import aiohttp
import praw

import utils

@utils.run_async
def create_reddit():
    reddit = praw.Reddit(
        client_id=os.environ["MEMESBR_REDDIT_CLIENT_ID"],
        client_secret=os.environ["MEMESBR_REDDIT_SECRET"],
        user_agent=os.environ["MEMESBR_REDDIT_USER_AGENT"],
    )

    return reddit

@utils.run_async
def get_memesbrasil_subreddits_new(reddit):
    return reddit.subreddit("MemesBrasil").new()

async def getmemeurl(reddit):
    redis = utils.redis()
    posts = await get_memesbrasil_subreddits_new(reddit)
    for post in posts:
        if post.url and utils.is_image(post.url):
            key = f'memesbrasil_{post.id}'
            if await redis.exists(key):
                continue
            now = datetime.now()
            await redis.set(key, now)
            await redis.expireat(key, now + timedelta(days=90))
            return post.url


async def main():
    print("memesbr bot started")
    reddit = await create_reddit()
    twitter = await utils.create_twitter(
        key=os.environ["MEMESBR_TWITTER_ACCESS_KEY"],
        secret=os.environ["MEMESBR_TWITTER_ACCESS_SECRET"],
        access_token=os.environ["MEMESBR_TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["MEMESBR_TWITTER_ACCESS_TOKEN_SECRET"],
    )
    while True:
        memeurl = await getmemeurl(reddit)
        if memeurl is None:
            return

        async with utils.download_image(memeurl) as memepath:
            status = await utils.tweet_image(twitter, memepath)
            print(status.text)
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
