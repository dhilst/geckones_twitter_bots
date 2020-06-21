import re
import os
import asyncio
import aiofiles.os
import html
from datetime import datetime, timedelta
from tweepy import TweepError

import utils
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


async def main():
    utils.log.info("bot started")
    redis = utils.redis()
    twitter = await create_api()
    me = await twitter.me()
    key = f"twitter_{me.id}_last"
    while True:
        try:
            last = await redis.get(key)
            if 'MEMEMIZE_TRACE_REDIS' in os.environ:
                utils.log.info("Searching for metions last=%s", last)
            for t in await twitter.mentions_timeline(
                last, tweet_mode="extended", include_entities=True
            ):
                if last is None or t.id > int(last):
                    utils.log.debug("Found, saving last=%s t.id=%s", last, t.id)
                    await redis.set(key, t.id)
                    await redis.expireat(key, datetime.now() + timedelta(days=30))
                    last = t.id
                # Skip if already replied
                # should normally not happen because of Redis state
                # but Redis state is not invicible
                try:
                    for reply in await twitter.search(
                        q=f"to:{me.screen_name}", since_id=t.id, tweet_mode="extended"
                    ):
                        if reply.in_reply_to_status_id == t.id:
                            raise ContinueOuter
                except ContinueOuter:
                    continue

                if await utils.reply_to_us(twitter, t, me):
                    continue

                if getattr(t, 'in_reply_to_status_id', None) and getattr(t, 'full_text', None):
                    text = t.full_text
                    text = re.sub(r"@[^ ]+", "", text).strip()
                    text = re.sub(r"#[^ ]+", "", text).strip()
                    text = re.sub("https//[^ ]+", "", text).strip()
                    text = html.unescape(text)
                    ats = re.findall(r"(@[^ ]+)", t.full_text)
                    ats = {at for at in ats if at != f"@{me.screen_name}"}
                    ats = ats.union({f"@{t.user.screen_name}"})
                    ats = " ".join(ats)
                    replied = await twitter.get_status(
                        t.in_reply_to_status_id, include_entities=True
                    )
                    if "media" in replied.entities and len(replied.entities["media"]) and text:
                        url = replied.entities["media"][0].get("media_url")
                        if url:
                            async with utils.download_image(url) as path:
                                print(text)
                                top, bottom = mememaker.text_split(text)
                                # skip if there is no text to render
                                if not top and not bottom:
                                    continue
                                utils.log.debug("top=%s bottom=%s", top, bottom)
                                output_path = await mememaker.create_meme_tempfile(path, bottom, top)
                                utils.log.debug("path=%s", output_path)
                                if 'DRYRUN' not in os.environ:
                                    status = await twitter.update_with_media(
                                        output_path, status=ats, in_reply_to_status_id=t.id
                                    )
                                    utils.log.info(
                                        "%s posted", await utils.get_tweet_url(twitter, status)
                                    )
                                    await aiofiles.os.remove(output_path)
                                else:
                                    utils.log.debug('DRYRUN, skipping %s', await utils.get_tweet_url(twitter, t))
            await asyncio.sleep(20)
        except TweepError as e:
            utils.log.error("TweepError %s", e)
        except Exception as e:
            utils.log.error("Uncaught Exception %s", e)


if __name__ == "__main__":
    asyncio.run(main())
