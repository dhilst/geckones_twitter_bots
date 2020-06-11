import asyncio
import functools

import tweepy
from tweepy import *

async def acall(f, *args, **kwargs):
    return await asyncio.get_running_loop().run_in_executor(
        None, lambda: f(*args, **kwargs)
    )


def awrap(f):
    @functools.wraps(f)
    async def wrapper(*args, **kwargs):
        return await acall(f, *args, **kwargs)

    return wrapper

def create_aproxy_class(cls):
    class AsyncProxy:
        __name__ = cls.__name__
        __doc__ = cls.__doc__
        def __init__(self, *args, **kwargs):
            self.proxy = cls(*args, **kwargs)

        def __getattr__(self, attr):
            attr = getattr(self.proxy, attr)
            return awrap(attr) if callable(attr) else attr
    return AsyncProxy


API = create_aproxy_class(tweepy.API)
