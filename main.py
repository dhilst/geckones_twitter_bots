import asyncio

# Bots
import kittensupport
import memesbr
import aliens
import mememize

if __name__ == '__main__':
    loop = asyncio.get_event_loop()

    loop.create_task(memesbr.main())
    loop.create_task(mememize.main())
    loop.run_forever()
