import sys
import asyncio
import textwrap
from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw

def draw_text_border(draw, text, x, y, font):
    for i in (x-1, x+1):
        for j in (y-1, y+1):
            draw.text((i, j), text, font=font, fill="#000000") # this will draw text with Blackcolor and 16 size
    draw.text((x, y), text, font=font, fill="#ffffff") # this will draw text with Blackcolor and 16 size

def img_center_width(img, draw, text, font):
    W, _ = img.size
    w, _ = draw.textsize(text, font=font)
    return (W-w)/2

def img_margin_bottom(img, draw, text, font):
    _, H = img.size
    _, h = draw.textsize(text, font=font)
    return (H - h) / 8 * 7

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

def draw_text(img, draw, text, font):
    text = text.upper()
    h = img_margin_bottom(img, draw, text, font)
    font = create_font(img, draw, text, 'unicode.impact.ttf')
    w = img_center_width(img, draw, text, font)
    draw_text_border(draw, text, w, h, font)

async def create_meme(imgpath, outpath, text):
    img = Image.open(imgpath)
    font = ImageFont.truetype('unicode.impact.ttf', 32)
    draw = ImageDraw.Draw(img)
    text = textwrap.wrap(text, 32)
    text = (line.center(32) for line in text)
    text = "\n".join(text)
    text = text.upper()

    create_font(img, draw, text, 'unicode.impact.ttf')
    draw_text(img, draw, text, font)

    img.save(outpath)

if __name__ == '__main__':
    asyncio.run(create_meme(sys.argv[1], sys.argv[2], " ".join(sys.argv[3:])))
