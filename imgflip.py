import os
import json
import aiohttp
import asyncio
import urllib

this_path = os.path.abspath(os.path.dirname(__file__))
memes = json.load(open(os.path.join(this_path, 'memes.json')))

def find_meme_id(name):
    for meme in memes['data']['memes']:
        name_ = meme.get('name')
        if name_ and name_ == name:
            return meme.get('id')
    else:
        raise KeyError(name)

async def post_meme(name, **data):
    id_ = find_meme_id(name)
    if not id_:
        return
    async with aiohttp.ClientSession() as session:
        data = {
            'template_id': id_,
            'username': os.environ['IMGFLIP_USERNAME'],
            'password': os.environ['IMGFLIP_PASSWORD'],
            **data,
        }
        async with session.post('https://api.imgflip.com/caption_image', data=data) as resp:
            if resp.status != 200:
                print(f'[imgflip] Error in response, {resp.status}')
            resp_data = await resp.json()
            if not resp_data.get('success'):
                return

            return resp_data.get('data', {}).get('url')
