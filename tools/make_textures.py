#!/usr/bin/env python3
"""Generate 16x16 music disc textures styled after the BULLY-era palette.

Programmatic pixel art: black disc, cream/vinyl-noise ring, each disc gets
its own accent color from the BULLY aesthetic (washed browns, bone, rust,
muted gold). No copyrighted artwork is reproduced.
"""
import os
import random

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
TEX = os.path.join(ROOT, "assets", "bully_discs", "textures", "item")
os.makedirs(TEX, exist_ok=True)

# BULLY-era palette: washed tan, bone, rust, olive, muted gold, faded cream
ACCENTS = {
    "king":               (196, 157, 106),  # dusty gold — crown
    "this_a_must":        (168, 62, 48),    # rust red — rage
    "father":             (222, 208, 160),  # candlelight — church
    "all_the_love":       (150, 126, 178),  # muted violet
    "punch_drunk":        (185, 140, 96),   # tan
    "whatever_works":     (134, 122, 88),   # olive khaki
    "mamas_favorite":     (208, 176, 152),  # warm blush — mother
    "sisters_and_brothers": (110, 132, 104),# sage
    "bully":              (60, 56, 52),     # near-black — title
    "highs_and_lows":     (176, 190, 168),  # pale sage
    "i_cant_wait":        (204, 168, 110),  # amber
    "white_lines":        (222, 220, 214),  # bone white
    "circles":            (142, 108, 84),   # vinyl brown — Cortex loop
    "preacher_man":       (120, 96, 64),    # dark oak — pulpit
    "beauty_and_the_beast": (176, 148, 140),# dusty rose
    "damn":               (92, 88, 84),     # charcoal
    "last_breath":        (170, 60, 74),    # deep salsa red
    "this_one_here":      (186, 140, 84),   # brass
    "losing_your_mind":   (84, 94, 108),    # steel blue — kraut creep
}

DISC = [
    "................",
    "......xxxx......",
    "....xxxxxxxx....",
    "...xxxxxxxxxx...",
    "..xxxxxxxxxxxx..",
    "..xxxxxxxxxxxx..",
    ".xxxxxxxxxxxxxx.",
    ".xxxxxxxxxxxxxx.",
    ".xxxxxxxxxxxxxx.",
    ".xxxxxxxxxxxxxx.",
    "..xxxxxxxxxxxx..",
    "..xxxxxxxxxxxx..",
    "...xxxxxxxxxx...",
    "....xxxxxxxx....",
    "......xxxx......",
    "................",
]

def px(x, y, r, g, b, a=255):
    return (y * 16 + x, (r, g, b, a))

def build(name, accent):
    rng = random.Random(hash(name) & 0xFFFF)
    pixels = {}
    ax, ay, aa = accent
    # disc body: near-black with subtle vinyl wobble
    for y, row in enumerate(DISC):
        for x, ch in enumerate(row):
            if ch == 'x':
                n = rng.randint(-6, 6)
                base = (28 + n, 26 + n, 24 + n)
                # accent ring at radius ~5 from center (8,8)
                d = ((x - 7.5) ** 2 + (y - 7.5) ** 2) ** 0.5
                if 4.6 <= d <= 5.9:
                    fade = rng.randint(-24, 18)
                    base = (max(0, min(255, ax + fade)),
                            max(0, min(255, ay + fade)),
                            max(0, min(255, aa + fade)))
                pixels[y * 16 + x] = base + (255,)
    # center hole
    pixels[7 * 16 + 7] = (0, 0, 0, 255)
    pixels[7 * 16 + 8] = (0, 0, 0, 255)
    pixels[8 * 16 + 7] = (0, 0, 0, 255)
    pixels[8 * 16 + 8] = (0, 0, 0, 255)
    # cream center dot ring around hole
    for (x, y) in [(6, 7), (7, 6), (8, 6), (9, 7), (9, 8), (8, 9), (7, 9), (6, 8)]:
        pixels[y * 16 + x] = (222, 214, 196, 255)
    # sheen: a couple of lighter pixels top-left
    sheen = [(3, 3), (4, 2), (2, 4), (5, 3)]
    for (x, y) in sheen:
        if DISC[y][x] == 'x':
            n = rng.randint(10, 40)
            pixels[y * 16 + x] = (70 + n, 66 + n, 60 + n, 255)
    # write PNG
    out = os.path.join(TEX, f"bully_disc_{name}.png")
    with open(out, "wb") as f:
        f.write(b"\x89PNG\r\n\x1a\n")
        # IHDR
        ihdr = struct_pack(b">IIBBBBB", 16, 16, 8, 6, 0, 0, 0)
        f.write(png_chunk(b"IHDR", ihdr))
        # IDAT
        raw = b""
        for y in range(16):
            raw += b"\x00"
            for x in range(16):
                p = pixels.get(y * 16 + x, (0, 0, 0, 0))
                raw += bytes((p[0], p[1], p[2], p[3]))
        f.write(png_chunk(b"IDAT", zlib_compress(raw)))
        f.write(png_chunk(b"IEND", b""))
    return out

# tiny helpers to avoid imports
import struct as _struct
def struct_pack(fmt, *vals):
    return _struct.pack(fmt, *vals)
import zlib as _zlib
def zlib_compress(data):
    return _zlib.compress(data, 9)

def crc32(data):
    import zlib
    return zlib.crc32(data) & 0xFFFFFFFF

def png_chunk(typ, data):
    import struct
    return struct.pack(">I", len(data)) + typ + data + struct.pack(">I", crc32(typ + data))

if __name__ == "__main__":
    for name, accent in ACCENTS.items():
        out = build(name, accent)
        print("wrote", out)
