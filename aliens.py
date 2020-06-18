import re
import os
import asyncio
import tweepy
from datetime import datetime, timedelta

import utils
import imgflip


class ContinueOuter(Exception):
    pass



async def create_twitter():
    return await utils.create_twitter(
        key=os.environ["ALIENSGUY_TWITTER_ACCESS_KEY"],
        secret=os.environ["ALIENSGUY_TWITTER_ACCESS_SECRET"],
        access_token=os.environ["ALIENSGUY_TWITTER_ACCESS_TOKEN"],
        access_token_secret=os.environ["ALIENSGUY_TWITTER_ACCESS_TOKEN_SECRET"],
    )


async def main():
    utils.log.info("started")
    twitter = await create_twitter()
    redis = utils.redis()
    me = await twitter.me()
    key = f"twitter_{me.id}_last"
    while True:
        last = await redis.get(key)
        for t in await twitter.mentions_timeline(last):
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

            # If this is a reply to us, then it reply
            # and the tweet replied has an image, we just ignore
            # This is to avoid user comment on results trigger another
            # meme. When an user reply on eof our messages we're
            if await utils.reply_to_us(twitter, t, me):
                continue

            text = re.sub(r"@[^ ]+", "", t.text).strip()
            ats = re.findall(r"(@[^ ]+)", t.text)
            ats = {at for at in ats if at != f"@{me.screen_name}"}
            ats = ats.union({f"@{t.user.screen_name}"})
            ats = " ".join(ats)

            utils.log.debug(f"found %s %s %s", t.id, ats, text)

            if "DRYRUN" in os.environ:
                continue

            url = await imgflip.post_meme("Ancient Aliens", text1=text)

            if not url:
                continue

            async with utils.download_image(url) as path:
                tweet = await twitter.update_with_media(
                    path, status=ats, in_reply_to_status_id=t.id
                )
        await asyncio.sleep(60)


if __name__ == "__main__":
    asyncio.run(main())
