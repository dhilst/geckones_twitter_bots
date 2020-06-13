import asyncio
import sys
import shutil
import tempfile
import os
import requests
from io import StringIO
from random import randint, choice
from time import sleep
from bs4 import BeautifulSoup

from tweepy import API, OAuthHandler, TweepError  # type: ignore

def create_api() -> API:
    key = os.environ["ACCESS_KEY"]
    secret = os.environ["ACCESS_SECRET"]
    access_token = os.environ["ACCESS_TOKEN"]
    access_token_secret = os.environ["ACCESS_TOKEN_SECRET"]
    try:
        auth = OAuthHandler(key, secret)
    except TweepError:
        sys.exit(-1)
    auth.set_access_token(access_token, access_token_secret)
    api = API(
        auth,
        retry_count=3,
        retry_delay=10,
        wait_on_rate_limit_notify=True,
        wait_on_rate_limit=True,
        compression=True,
    )
    return api

def format_phrase(p):
    words = p.split()
    s = StringIO()
    s2 = StringIO()
    l = 0
    for w in words:
        s.write(w)
        s.write(" ")
        if len(s.getvalue()) > 32:
            s.write("\n")
            s2.write(s.getvalue())
            s = StringIO()
    s2.write(s.getvalue())
    if s2.getvalue().endswith("\n"):
        s2 = StringIO(s2.getvalue()[0:-1])
    return s2.getvalue()

def get_random_message():
    p = randint(1,20)
    page = requests.get(f"https://www.pensador.com/frases/{p}/")
    if page.status_code != 200:
        return
    soup = BeautifulSoup(page.content, 'html.parser')
    phrase = choice(soup.find_all('p', class_='frase'))
    author = phrase.parent.find('span', class_='autor').find('a')
    phrase = format_phrase(phrase.get_text())
    phrase = f'{phrase}\n\n{author.get_text()}'
    return phrase

def download_random_kitten_image():
    p = get_random_message()
    res = requests.get(f"https://cataas.com/cat/says/{p}?width=600", stream=True)
    if res.status_code != 200:
        raise RuntimeError("placekitten request failed")

    res.raw.decode_content = True
    with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as f:
        shutil.copyfileobj(res.raw, f)
    return f.name

def tweet_random_kitten(api, img_path, status=None, reply=None):
    status = api.update_with_media(
        img_path, status=status, in_reply_to_status_id=getattr(reply, 'id', None),
    )
    return status

async def main() -> None:
    print("kiitensupport bot started")
    api = create_api()
    me = api.me().screen_name
    url = "https://twitter.com/{}/status/{{}}".format(me)
    while True:
        path = None
        try:
            path = download_random_kitten_image()
            status = tweet_random_kitten(api, path)
            print(url.format(status.id))
        except TweepError as e:
            print(f"TweepError {e}")
        except RuntimeError:
            printf("Cat as a service unavailable")
        finally:
            if path:
                os.remove(path)
        await asyncio.sleep(3600)


if __name__ == "__main__":
    asyncio.run(main())
