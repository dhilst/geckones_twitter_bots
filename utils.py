import asyncio
import contextlib
import functools
import inspect
import logging
import os
import tempfile
from datetime import datetime, timedelta

import aiohttp
import aiofiles
import aiofiles.os
import tweepy
from pytz import timezone

import atweepy
from aredis import StrictRedis


tz_America_Sao_Paulo = timezone("America/Sao_Paulo")
run_async = atweepy.awrap  # don't break older code


def next_hour(hour):
    now = datetime.now(tz=tz_America_Sao_Paulo)
    d = now.replace(hour=hour, minute=0, second=0, microsecond=0)
    if d < now:
        d += timedelta(hours=24)

    return d - now


class _Logger:
    """
    Logger proxy

    Usage:
    from utils import log

    log.info("foo")
    """

    _loggers = {}

    @classmethod
    def create_logger(cls, name):
        l = logging.getLogger(name)
        handler = logging.StreamHandler()
        handler.setFormatter(
            logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        )
        l.addHandler(handler)
        l.setLevel(logging.DEBUG)
        return l

    def __getattr__(self, attr):
        name = os.path.splitext(os.path.basename(inspect.stack()[1].filename))[
            0
        ].upper()
        if name not in self.__class__._loggers:
            self.__class__._loggers[name] = self.__class__.create_logger(name)
        return getattr(self.__class__._loggers[name], attr)


log = _Logger()


async def create_twitter(key, secret, access_token, access_token_secret):
    try:
        auth = atweepy.OAuthHandler(key, secret)
    except tweepy.TweepError:
        return
    auth.set_access_token(access_token, access_token_secret)
    api = atweepy.API(
        auth,
        retry_count=3,
        retry_delay=10,
        wait_on_rate_limit_notify=True,
        wait_on_rate_limit=True,
        compression=True,
    )
    return api


async def get_tweet_url(twitter, tweet):
    return f"https://twitter.com/{tweet.user.screen_name}/status/{tweet.id}"

def get_extension(string):
    try:
        return string.rsplit(".", 1)[1]
    except IndexError:
        pass

async def reply_to_us(twitter, tweet, me):
    while True:
        if tweet.in_reply_to_status_id is None:
            return False

        parent = await twitter.get_status(tweet.in_reply_to_status_id)
        if parent.user.id == me.id:
            return True

        tweet = parent


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
                with tempfile.NamedTemporaryFile(
                    suffix=f".{extension}", delete=False
                ) as f:
                    fname = f.name
                async with aiofiles.open(fname, "wb") as f:
                    content = await resp.read()
                    await f.write(content)
                yield fname
                await aiofiles.os.remove(fname)


@run_async
def tweet_image(twitter, path, status=None, reply_id=None):
    return twitter.update_with_media(path, status, in_reply_to_status_id=reply_id)


def redis():
    return StrictRedis.from_url(os.environ["REDIS_URL"], decode_responses=True)
