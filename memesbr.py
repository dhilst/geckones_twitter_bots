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
    return reddit.subreddit("MemesBrasil").new(limit=1000)

    # The above code is okay but it doesn't work beacuse
    # reddit removed the timestamp search from their API
    # we have to use http://redditsearch.io/ which I'm
    # not whilling to implement at statuday

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
        back_up_to = {"days": 30}
        prev = last_timestamp - timedelta(**back_up_to)
        d1, d2 = int(prev.timestamp()), int(last_timestamp.timestamp())
        return reddit.subreddit("MemesBrasil").new(params={"timestamp": f"{d1}..{d2}"})

    return reddit.subreddit("MemesBrasil").new()


async def getmemeurl(redis, reddit):
    posts = await get_memesbrasil_subreddits(redis, reddit)
    for post in posts:
        if post.url and utils.is_image(post.url):
            if await redis.zscore("memesbrasil", post.id):
                continue
            utils.log.debug(
                "found %s %s %s %s",
                datetime.fromtimestamp(post.created),
                post.id,
                post.title,
                post.url,
            )
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

    utils.log.info("memesbr bot started")

    while True:
        utils.log.info("sleeping")
        await asyncio.sleep(utils.next_hour(19).total_seconds())
        memeurl = await getmemeurl(redis, reddit)
        if memeurl is None:
            return

        async with utils.download_image(memeurl) as memepath:
            utils.log.debug("memepath %s", memepath)
            if "DRYRUN" not in os.environ:
                status = await twitter.update_with_media(memepath)
            else:
                utils.log.info("dryrun, skipping")


if __name__ == "__main__":
    asyncio.run(main())
