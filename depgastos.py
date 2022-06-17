import os
import asyncio
import aiohttp
from random import choice
from functools import reduce
from operator import itemgetter
import json
import utils
import tweepy

async def get_random_dep():
    baseurl = "https://dadosabertos.camara.leg.br/api/v2"
    async with aiohttp.ClientSession() as session:
        async with session.get(f"{baseurl}/deputados") as resp:
            dep = choice((await resp.json())['dados'])
            dep_id = dep['id']
        async with session.get(f"{baseurl}/deputados/{dep_id}/despesas") as resp:
            data = (await resp.json())['dados']
            maior = reduce((lambda a, b: a if a['valorDocumento'] > b['valorDocumento'] else b), data)
            dep["gasto"] = maior
            return dep

def mount_tweet(dep):
    text = f"Nome: {dep['nome']} {dep['siglaPartido']}-{dep['siglaUf']}\nDespesa: {dep['gasto']['tipoDespesa']}\nValor R$ {dep['gasto']['valorDocumento']}\n{dep['gasto']['urlDocumento']}"
    img = dep["urlFoto"]
    return text, img
            
async def main():
    client = tweepy.Client(
        os.environ["DEPGASTOS_TWITTER_BEARER_TOKEN"],
        os.environ["DEPGASTOS_TWITTER_ACCESS_KEY"],
        os.environ["DEPGASTOS_TWITTER_ACCESS_SECRET"],
        os.environ["DEPGASTOS_TWITTER_ACCESS_TOKEN"],
        os.environ["DEPGASTOS_TWITTER_ACCESS_TOKEN_SECRET"],
    )
    utils.log.info("depgastos bot started")

    while True:
        utils.log.info("sleeping")
        await asyncio.sleep(utils.next_hour(00).total_seconds())
        try:
            dep = await get_random_dep()
            status, imgurl = mount_tweet(dep)
            if "DRYRUN" not in os.environ:
                status = client.create_tweet(text=status)
                utils.log.info(f"posted {status}")
            else:
                utils.log.info("dryrun, skipping")
        except Exception as e:
            utils.log.error(f"Unexpected error {e}")
        await asyncio.sleep(10)

if __name__ == '__main__':
    asyncio.run(main())
