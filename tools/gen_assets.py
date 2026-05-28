#!/usr/bin/env python3
"""Generate brand image assets with no external libraries (stdlib only).

Outputs:
  og-home.png   1200x1200 (1:1) Open Graph card — brand bg + skyline emblem
  favicon.ico   32x32 brand icon (PNG-in-ICO)

Run:  python3 tools/gen_assets.py
"""
import os, struct, zlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def png_bytes(w, h, buf):
    def chunk(typ, data):
        c = typ + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xffffffff)
    sig = b"\x89PNG\r\n\x1a\n"
    ihdr = struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0)  # 8-bit RGB
    stride = w * 3
    raw = bytearray()
    for y in range(h):
        raw.append(0)  # filter: none
        raw += buf[y * stride:(y + 1) * stride]
    return sig + chunk(b"IHDR", ihdr) + chunk(b"IDAT", zlib.compress(bytes(raw), 9)) + chunk(b"IEND", b"")


def make_buf(w, h, top, bottom):
    """Vertical gradient RGB buffer."""
    buf = bytearray(w * h * 3)
    for y in range(h):
        t = y / (h - 1)
        r = int(top[0] + (bottom[0] - top[0]) * t)
        g = int(top[1] + (bottom[1] - top[1]) * t)
        b = int(top[2] + (bottom[2] - top[2]) * t)
        row = bytes((r, g, b)) * w
        buf[y * w * 3:(y + 1) * w * 3] = row
    return buf


def fill_rect(buf, w, x0, y0, x1, y1, color):
    x0, x1 = max(0, x0), min(w, x1)
    for y in range(max(0, y0), y1):
        base = (y * w + x0) * 3
        seg = bytes(color) * (x1 - x0)
        buf[base:base + len(seg)] = seg


def gen_og():
    w = h = 1200
    buf = make_buf(w, h, (29, 64, 175), (37, 99, 235))  # #1d40af -> #2563eb
    white = (255, 255, 255)
    gold = (250, 204, 21)  # accent
    # skyline of buildings centered, sitting on a ground line
    ground = 860
    fill_rect(buf, w, 0, ground, w, ground + 8, (255, 255, 255))
    bars = [  # (cx_offset, width, height)
        (-360, 110, 150), (-235, 130, 250), (-95, 150, 360),
        (75, 150, 300), (245, 120, 210), (370, 100, 130),
    ]
    cx = w // 2
    for off, bw, bht in bars:
        x = cx + off
        fill_rect(buf, w, x, ground - bht, x + bw, ground, white)
        # windows (brand-colored dots)
        for wy in range(ground - bht + 26, ground - 20, 46):
            for wx in range(x + 18, x + bw - 18, 40):
                fill_rect(buf, w, wx, wy, wx + 18, wy + 24, (37, 99, 235))
    # top accent bar + bottom band
    fill_rect(buf, w, 0, 150, w, 158, gold)
    fill_rect(buf, w, 0, h - 90, w, h, (15, 23, 42))
    open(os.path.join(ROOT, "og-home.png"), "wb").write(png_bytes(w, h, buf))
    print("og-home.png 1200x1200 written")


def gen_favicon():
    s = 32
    buf = bytearray(s * s * 3)
    fill_rect(buf, s, 0, 0, s, s, (37, 99, 235))      # brand bg
    fill_rect(buf, s, 7, 18, 12, 26, (255, 255, 255))  # 3 white bars (skyline)
    fill_rect(buf, s, 14, 11, 19, 26, (255, 255, 255))
    fill_rect(buf, s, 21, 15, 26, 26, (255, 255, 255))
    png = png_bytes(s, s, buf)
    # ICO wrapping a PNG (supported by modern browsers/crawlers)
    ico = struct.pack("<HHH", 0, 1, 1)
    ico += struct.pack("<BBBBHHII", 32, 32, 0, 0, 1, 32, len(png), 22)
    ico += png
    open(os.path.join(ROOT, "favicon.ico"), "wb").write(ico)
    print("favicon.ico 32x32 written")


if __name__ == "__main__":
    gen_og()
    gen_favicon()
    print("DONE")
