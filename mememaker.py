from typing import *
import sys
import asyncio
import textwrap
import tempfile
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw


import utils


def draw_text_border(draw, text, x, y, font):
    for i in (x - 1, x + 1):
        for j in (y - 1, y + 1):
            draw.text(
                (i, j), text, font=font, fill="#000000"
            )  # this will draw text with Blackcolor and 16 size
    draw.text(
        (x, y), text, font=font, fill="#ffffff"
    )  # this will draw text with Blackcolor and 16 size


def img_center_width(img, draw, text, font):
    W, _ = img.size
    w, _ = draw.textsize(text, font=font)
    return (W - w) / 2


def img_margin_bottom(img, draw, text, font, margin):
    _, H = img.size
    _, h = draw.textsize(text, font=font)
    return ((H - h) / 16 * 15) - margin


def bin_search(n, f, l=0, r=1000):
    old_i = 0
    while True:
        i = (l + r) // 2
        if old_i == i:
            return i
        elif n > f(i):
            l = i
        elif n < f(i):
            r = i
        else:
            return i
        old_i = i


def create_font(img, draw, text, fontpath):
    left = 0
    right = 100
    W, H = img.size
    ideal_size = W // 16 * 14

    max_size = H // 8
    make_font = lambda s: draw.textsize(text, ImageFont.truetype(fontpath, s))[0]
    fsize = min(bin_search(ideal_size, make_font), max_size)
    return ImageFont.truetype(fontpath, fsize)


def draw_text(img, draw, text: List[str], font):
    offset = 0
    font = create_font(img, draw, text[0], "unicode.impact.ttf")
    _, fheight = draw.textsize(text[0], font)
    for line in reversed(text):
        h = img_margin_bottom(img, draw, line, font, offset)
        w = img_center_width(img, draw, line, font)
        draw_text_border(draw, line, w, h, font)
        offset += fheight + 10


async def create_meme(imgpath, outpath, text):
    img = Image.open(imgpath)
    font = ImageFont.truetype("unicode.impact.ttf", 32)
    draw = ImageDraw.Draw(img)
    text = text.upper()
    text = textwrap.wrap(text, 30)

    draw_text(img, draw, text, font)

    img.save(outpath)


async def create_meme_tempfile(imgpath, text):
    ext = utils.get_extension(imgpath)
    temp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
    await create_meme(imgpath, temp.name, text)
    return temp.name


if __name__ == "__main__":
    asyncio.run(create_meme(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:])))
