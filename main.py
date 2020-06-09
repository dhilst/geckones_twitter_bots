import asyncio

# Bots
import kittensupport
import memesbr

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    loop.create_task(kittensupport.main())
    loop.create_task(memesbr.main())
    loop.run_forever()
