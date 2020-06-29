import re
import os
import asyncio
import aiofiles.os  # type: ignore
import html
from datetime import datetime, timedelta
import tweepy  # type: ignore

import utils
from utils import get
import imgflip
import mememaker


class ContinueOuter(Exception):
    pass


async def create_api():
    twitter = await utils.create_twitter(
        key=os.environ["MEMEMIZE_TWITTER_ACCESS_KEY"],
        secret=os.environ["MEMEMIZE_TWITTER_ACCESS_SECRET"],
        access_token=os.environ["MEMEMIZE_TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["MEMEMIZE_TWITTER_ACCESS_TOKEN_SECRET"],
    )
    return twitter


async def mememize_url(twitter, t: tweepy.Status, url, text, ats):
    async with utils.download_image(url) as path:
        top, bottom = mememaker.text_split(text)
        # skip if there is no text to render
        if not top and not bottom:
            return
        utils.log.debug("top=%s bottom=%s", top, bottom)
        output_path = await mememaker.create_meme_tempfile(path, bottom, top)
        utils.log.debug("path=%s", output_path)
        if "DRYRUN" not in os.environ:
            status = await twitter.update_with_media(
                output_path, status=ats, in_reply_to_status_id=t.id
            )
            utils.log.info("%s posted", utils.get_tweet_url(twitter, status))
            await aiofiles.os.remove(output_path)
        else:
            utils.log.debug("DRYRUN, skipping %s", utils.get_tweet_url(twitter, t))


async def already_replied(twitter, t: tweepy.Status, me):
    for reply in await twitter.search(
        q=f"to:{me.screen_name}", since_id=t.id, tweet_mode="extended"
    ):
        if reply.in_reply_to_status_id == t.id:
            return True
    return False


async def main():
    utils.log.info("bot started")
    redis = utils.redis()
    twitter = await create_api()
    me = await twitter.me()
    key = f"twitter_{me.id}_last"
    while True:
        try:
            last = await redis.get(key)
            if "MEMEMIZE_TRACE_REDIS" in os.environ:
                utils.log.info("Searching for metions last=%s at %s", last, key)
            for t in await twitter.mentions_timeline(
                last, tweet_mode="extended", include_entities=True
            ):
                utils.log.info("Handling %s", utils.get_tweet_url(twitter, t))
                if last is None or t.id > int(last):
                    utils.log.debug(
                        "Found, saving tweet id: last=%s t.id=%s", last, t.id
                    )
                    await redis.set(key, t.id)
                    await redis.expireat(key, datetime.now() + timedelta(days=30))
                    last = t.id
                # Skip if already replied
                # should normally not happen because of Redis state
                # but Redis state is not invicible
                if await already_replied(twitter, t, me):
                    continue

                # Dont reply our selves
                if t.user.id == me.id:
                    continue

                a, b = t.display_text_range
                text = t.full_text[a:b]

                # Skip auto mentions. When a user reply one of our posts
                # Twiter will insert our @ on the full_text, but it will
                # not be visible in display_text_range
                if f"@{me.screen_name}" not in text:
                    utils.log.debug("Not an explicity mention, ignoring")
                    continue

                if text:
                    utils.log.debug("Has text")
                    text = text.replace("\n", " ")
                    text = re.sub(r"[\t\r]+", " ", text)
                    text = re.sub(r"\s+", " ", text)
                    text = re.sub(r"@[^ ]+", "", text)
                    text = re.sub(r"#[^ ]+", "", text)
                    text = re.sub("https://[^ ]+", "", text)
                    text = text.strip()
                    text = html.unescape(text)
                    ats = {
                        f"@{u['screen_name']}"
                        for u in t.entities["user_mentions"]
                        if u["screen_name"] != me.screen_name
                    }
                    ats = ats.union({f"@{t.user.screen_name}"})
                    ats = " ".join(ats)
                    url = t.entities >> get("media") >> get(0) >> get("media_url")
                    if url:
                        utils.log.debug("Has an image")
                    elif t.in_reply_to_status_id:
                        utils.log.debug("Is a reply")
                        replied = await twitter.get_status(
                            t.in_reply_to_status_id,
                            include_entities=True,
                            tweet_mode="extended",
                        )
                        if replied.user.id == me.id:
                            utils.log.debug(
                                "Is a reply to a previous meme, and has no image, ignoring"
                            )
                            continue
                        url = (
                            replied.entities
                            >> get("media")
                            >> get(0)
                            >> get("media_url")
                        )
                        if url:
                            utils.log.debug("And has media")
                    if url:
                        await mememize_url(twitter, t, url, text, ats)
        except tweepy.TweepError as e:
            utils.log.error("TweepError %s", e)
        except Exception as e:
            utils.log.exception("Uncaught Exception")
        finally:
            await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(main())
