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

def img_margin_top(img, draw, text, font, margin):
    _, H = img.size
    _, h = draw.textsize(text, font=font)
    return ((H - h) / 16 * 1) + margin

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


def draw_text(img, draw, text: List[str], font, text_top: List[str] = None):
    offset = 0
    offset_top = 0
    larger_text = max(text, key=len)
    font = create_font(img, draw, larger_text, "unicode.impact.ttf")
    _, fheight = draw.textsize(text[0], font)
    for line in reversed(text):
        h = img_margin_bottom(img, draw, line, font, offset)
        w = img_center_width(img, draw, line, font)
        draw_text_border(draw, line, w, h, font)
        offset += fheight + 10

    if text_top:
        larger_text = max(text_top, key=len)
        font = create_font(img, draw, larger_text, "unicode.impact.ttf")
        _, fheight = draw.textsize(text_top[0], font)
        for line in text_top:
            h = img_margin_top(img, draw, line, font, offset_top)
            w = img_center_width(img, draw, line, font)
            draw_text_border(draw, line, w, h, font)
            offset_top += fheight + 10



async def create_meme(imgpath, outpath, text, text_top=None):
    img = Image.open(imgpath)
    font = ImageFont.truetype("unicode.impact.ttf", 32)
    draw = ImageDraw.Draw(img)
    text = text.upper()
    text = textwrap.wrap(text, 30)
    if text_top:
        text_top = text_top.upper()
        text_top = textwrap.wrap(text_top, 30)

    draw_text(img, draw, text, font, text_top)

    img.save(outpath)


def text_split(text):
    """
    >>> text_split('foo // bar')
    ('foo', 'bar')
    >>> text_split('foo')
    (None, 'foo')
    """
    try:
        top, bottom = map(str.strip, text.split("//", 1))
    except ValueError:
        bottom = text.strip()
        top = None
    return top, bottom


async def create_meme_tempfile(imgpath, text, text_top=None):
    ext = utils.get_extension(imgpath)
    temp = tempfile.NamedTemporaryFile(suffix=f".{ext}", delete=False)
    await create_meme(imgpath, temp.name, text, text_top)
    return temp.name


if __name__ == "__main__":
    try:
        text = sys.argv[4]
        text_top = sys.argv[3]
    except IndexError:
        text = sys.argv[3]
        text_top = None
    asyncio.run(create_meme(sys.argv[1], sys.argv[2], text, text_top))
