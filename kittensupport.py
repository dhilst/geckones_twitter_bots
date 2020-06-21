import json
import asyncio
import sys
import shutil
import tempfile
import os
import aiohttp

from io import StringIO
from random import randint, choice
from time import sleep
from bs4 import BeautifulSoup  # type: ignore

from tweepy import API, OAuthHandler, TweepError  # type: ignore

import utils
import mememaker


async def create_api() -> API:
    key = os.environ["KIITENSUPORT_ACCESS_KEY"]
    secret = os.environ["KIITENSUPORT_ACCESS_SECRET"]
    access_token = os.environ["KIITENSUPORT_ACCESS_TOKEN"]
    access_token_secret = os.environ["KIITENSUPORT_ACCESS_TOKEN_SECRET"]
    return await utils.create_twitter(key, secret, access_token, access_token_secret)


async def get_random_message():
    p = randint(1, 20)
    async with aiohttp.ClientSession() as session:
        async with session.get(f"https://www.pensador.com/frases/{p}/") as resp:
            if resp.status != 200:
                return
            content = await resp.text()
            soup = BeautifulSoup(content, "html.parser")
            phrase = choice(soup.find_all("p", class_="frase"))
            if not phrase:
                return
            author = phrase.parent.find("span", class_="autor").find("a")
            if not author:
                return
            phrase = f"“{phrase.get_text()}” — {author.get_text()}"
            return phrase


async def get_random_kitten_image_url():
    key = os.environ["KIITENSUPORT_THECATAPI_KEY"]
    url = "https://api.thecatapi.com/v1/images/search?api_key={key}&limit=1"
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as resp:
            if resp.status != 200:
                return
            data = await resp.json()
            if not isinstance(data, (list,)) or len(data) == 0:
                return
            return data[0].get("url")


async def main() -> None:
    utils.log.info("kiitensupport bot started")
    api = await create_api()
    while True:
        if not "DRYRUN" in os.environ:
            await asyncio.sleep(utils.next_hour(19).seconds)
        else:
            await asyncio.sleep(1)
        try:
            phrase = await get_random_message()
            if not phrase:
                continue

            kitten_url = await get_random_kitten_image_url()
            if not kitten_url:
                continue

            async with utils.download_image(kitten_url) as path:
                new_image_path = await mememaker.create_meme_tempfile(path, phrase)
                if not new_image_path:
                    continue

            if not "DRYRUN" in os.environ:
                status = await api.update_with_media(new_image_path)
                utils.log.info("Posted %s", await utils.get_tweet_url(api, status))
            else:
                utils.log.debug("DRYRUN, skipping")
        except TweepError as e:
            utils.log.error(f"TweepError %s", e)
        except Exception as e:
            utils.log.error("Uncaught exception %s", e)


if __name__ == "__main__":
    asyncio.run(main())
