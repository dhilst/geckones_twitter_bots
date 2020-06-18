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


async def main():
    utils.log.info("bot started")
    twitter = await utils.create_twitter(
        key=os.environ["MEMEMIZE_TWITTER_ACCESS_KEY"],
        secret=os.environ["MEMEMIZE_TWITTER_ACCESS_SECRET"],
        access_token=os.environ["MEMEMIZE_TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["MEMEMIZE_TWITTER_ACCESS_TOKEN_SECRET"],
    )
    redis = utils.redis()
    me = await twitter.me()
    key = f"twitter_{me.id}_last"
    while True:
        last = await redis.get(key)
        for t in await twitter.mentions_timeline(
            last, tweet_mode="extended", include_entities=True
        ):
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
                if len(replied.entities["media"]):
                    url = replied.entities["media"][0]["media_url"]
                    async with utils.download_image(url) as path:
                        output_path = await mememaker.create_meme_tempfile(path, text)
                        status = await twitter.update_with_media(
                            output_path, status=ats, in_reply_to_status_id=t.id
                        )
                        utils.log.info(
                            "%s posted", await utils.get_tweet_url(twitter, status)
                        )
                        await aiofiles.os.remove(output_path)
            await redis.set(key, t.id)
            await redis.expireat(key, datetime.now() + timedelta(days=30))
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
