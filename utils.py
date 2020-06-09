import os
import functools
import asyncio
import tempfile

import aiohttp
import aiofiles
import aiofiles.os
import tweepy
import contextlib
from aredis import StrictRedis


def run_async(f):
    @functools.wraps(f)
    def inner(*args, **kwargs):
        loop = asyncio.get_running_loop()
        return loop.run_in_executor(None, lambda: f(*args, **kwargs))

    return inner


@run_async
def create_twitter(key, secret, access_token, access_token_secret):
    try:
        auth = tweepy.OAuthHandler(key, secret)
    except tweepy.TweepError:
        return
    auth.set_access_token(access_token, access_token_secret)
    api = tweepy.API(
        auth,
        retry_count=3,
        retry_delay=10,
        wait_on_rate_limit_notify=True,
        wait_on_rate_limit=True,
        compression=True,
    )
    return api


def get_extension(string):
    try:
        return string.rsplit(".", 1)[1]
    except IndexError:
        pass


def is_image(url):
    return get_extension(url) in ("jpeg", "jpg", "png", "gif")

@contextlib.asynccontextmanager
async def download_image(url):
    async with aiohttp.ClientSession() as session:
        extension = get_extension(url)
        if extension is None:
            return
        async with session.get(url) as resp:
            if resp.status == 200:
                with tempfile.NamedTemporaryFile(suffix=f".{extension}", delete=False) as f:
                    fname = f.name
                async with aiofiles.open(fname, 'wb') as f:
                    content = await resp.read()
                    await f.write(content)
                yield fname
                await aiofiles.os.remove(fname)


@run_async
def tweet_image(twitter, path, status=None, reply_id=None):
    return twitter.update_with_media(path, status, in_reply_to_status_id=reply_id)

def redis():
    return StrictRedis.from_url(os.environ['REDIS_URL'], decode_responses=True)
