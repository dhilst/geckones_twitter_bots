import os
import asyncio
from datetime import datetime, timedelta

import aiohttp
import praw

import utils
from atweepy import acall, awrap

@awrap
def create_reddit():
    reddit = praw.Reddit(
        client_id=os.environ["MEMESBR_REDDIT_CLIENT_ID"],
        client_secret=os.environ["MEMESBR_REDDIT_SECRET"],
        user_agent=os.environ["MEMESBR_REDDIT_USER_AGENT"],
    )

    return reddit

def to_date(dstr):
    return datetime.strptime(dstr, r"%Y-%m-%d %H:%M:%S.%f")

async def get_memesbrasil_subreddits(redis, reddit=None):
    if reddit is None:
        reddit = await create_reddit()

    try:
         # get older post date
        val = await redis.zrange("memesbrasil", 0, 0, withscores=True)
        tstamp = val[0][1]
        last_timestamp = datetime.fromtimestamp(tstamp)
    except IndexError:
        pass

    if last_timestamp is not None:
        back_up_to = {'days': 30}
        prev = last_timestamp - timedelta(**back_up_to)
        d1, d2 = int(prev.timestamp()), int(last_timestamp.timestamp())
        return reddit.subreddit("MemesBrasil").new(params={"timestamp": f"{d1}..{d2}"})

    return reddit.subreddit("MemesBrasil").new()


async def migrate_keys(redis, reddit):
    await redis.delete('memesbrasil')
    for k in await redis.keys("memesbrasil_*"):
        val = await redis.get(k)
        val = to_date(val)
        id_ = k.replace("memesbrasil_", "")
        post = reddit.submission(id_)
        await redis.zadd("memesbrasil", post.created, id_)
        print(id_, 'migrated wiht score', post.created)

async def getmemeurl(redis, reddit):
    posts = await get_memesbrasil_subreddits(redis, reddit)
    for post in posts:
        if post.url and utils.is_image(post.url):
            if await redis.zscore("memesbrasil", post.id):
                continue
            print('[memesbr] found', datetime.fromtimestamp(post.created), post.id, post.title, post.url)
            now = datetime.now()
            await redis.zadd("memesbrasil", post.created, post.id)
            return post.url


async def main():

    redis = utils.redis()
    reddit = await create_reddit()
    twitter = await utils.create_twitter(
        key=os.environ["MEMESBR_TWITTER_ACCESS_KEY"],
        secret=os.environ["MEMESBR_TWITTER_ACCESS_SECRET"],
        access_token=os.environ["MEMESBR_TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["MEMESBR_TWITTER_ACCESS_TOKEN_SECRET"],
    )

    print("memesbr bot started")
    if 'MEMESBR_MIGRATE_KEYS' in os.environ:
        await migrate_keys(redis, reddit)
        return

    while True:
        memeurl = await getmemeurl(redis, reddit)
        if memeurl is None:
            return

        async with utils.download_image(memeurl) as memepath:
            print(memepath);
            if 'DRYRUN' not in os.environ:
                status = await twitter.update_with_media(memepath)
            else:
                print('[memesbr] dryrun, skipping')
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
