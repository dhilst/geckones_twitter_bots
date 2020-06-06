import sys
import shutil
import tempfile
import os
import requests
from random import choice
from time import sleep

from tweepy import API, OAuthHandler, TweepError  # type: ignore

messages = [
    "Eu reparei que você ta mal, então preparei uma foto de gatinho pra vc! 🤗",
    "Espero que as coisas melhorem, enquanto isso, olha esse gatinho 🥰",
    "Eu vi que tá triste. Será que uma foto de gatinho ajuda? 😕",
]


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


def download_random_kitten_image():
    "Returns the file name, user should delete it after using"
    res = requests.get("https://cataas.com/cat?width=200", stream=True)
    if res.status_code != 200:
        raise RuntimeError("placekitten request failed")

    res.raw.decode_content = True
    with tempfile.NamedTemporaryFile(suffix=".jpeg", delete=False) as f:
        shutil.copyfileobj(res.raw, f)
    return f.name


def tweet_random_kitten(api, img_path, reply):
    status = choice(messages)
    message = f"@{reply.user.screen_name} {status}"
    status = api.update_with_media(
        img_path, status=message, in_reply_to_status_id=reply.id,
    )
    return f"https://twitter.com/kiitenstatus/status/{status.id}"


def get_last_id():
    try:
        return open(".lastid", "r").read()
    except IOError:
        return "0"


def save_last_id(last_id):
    open(".lastid", "w").write(str(last_id))


def find_sad_tweets(api):
    tweets = api.search(
        q="to tão triste",
        lang="pt",
        result_type="recent",
        count=3,
        since_id=get_last_id(),
    )
    tweets = [
        t
        for t in tweets
        if not hasattr(t, "retweet_status")
        and not t.text.startswith("RT @")
        and not hasattr(t, "in_reply_status_id")
    ]

    if tweets:
        save_last_id(max(int(t.id) for t in tweets))
    return tweets


def main() -> None:
    api = create_api()
    while True:
        try:
            tweets = find_sad_tweets(api)
            for t in tweets:
                path = download_random_kitten_image()
                url = tweet_random_kitten(api, path, t)
                print(url)
                os.remove(path)
        except TweepError as e:
            print(f"TweepError {e}")
        sleep(300)


if __name__ == "__main__":
    main()
