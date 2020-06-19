import re
import os
import asyncio
import aiofiles.os
from datetime import datetime, timedelta

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
        last = await redis.get(key)
        utils.log.info("Searching for metions last=%s", last)
        for t in await twitter.mentions_timeline(
            last, tweet_mode="extended", include_entities=True
        ):
            if last is None or t.id > int(last):
                utils.log.debug("Saving last=%s t.id=%s", last, t.id)
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

            if t.in_reply_to_status_id:
                text = t.full_text
                text = re.sub(r"@[^ ]+", "", text).strip()
                text = re.sub(r"#[^ ]+", "", text).strip()
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
                            output_path = await mememaker.create_meme_tempfile(path, text)
                            if 'DRYRUN' not in os.environ:
                                status = await twitter.update_with_media(
                                    output_path, status=ats, in_reply_to_status_id=t.id
                                )
                                utils.log.info(
                                    "%s posted", await utils.get_tweet_url(twitter, status)
                                )
                            else:
                                utils.log.debug('DRYRUN, skipping %s', await utils.get_tweet_url(twitter, t))
                            await aiofiles.os.remove(output_path)
        await asyncio.sleep(20)


if __name__ == "__main__":
    asyncio.run(main())
