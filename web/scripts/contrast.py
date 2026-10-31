# WCAG contrast for every text and ground pair FINN uses. usage: python3 contrast.py   exits 1 if any pair fails
# Text needs 4.5:1 (3:1 at 24 px and up); marks (bars, rules you must see, focus) need 3:1. Translucent colours are laid over their ground first.
import sys

def rgb(c, ground=None):
    c = c.strip()
    if c.startswith('rgba'):
        *v, a = [float(x) for x in c[5:-1].split(',')]
        g = rgb(ground)
        return tuple(v[i] / 255 * a + g[i] * (1 - a) for i in range(3))
    c = c.lstrip('#'); return tuple(int(c[i:i + 2], 16) / 255 for i in (0, 2, 4))

def lum(c):
    f = lambda x: x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4
    r, g, b = map(f, c); return 0.2126 * r + 0.7152 * g + 0.0722 * b

def ratio(fg, bg):
    a, b = lum(rgb(fg, bg)), lum(rgb(bg)); return (max(a, b) + 0.05) / (min(a, b) + 0.05)

def check(grounds, pairs):
    bad = 0
    for gname, g in grounds.items():
        for name, fg, need in pairs[gname]:
            r = ratio(fg, g); ok = r >= need; bad += not ok
            print(f"{'pass' if ok else 'FAIL'}  {r:5.2f}:1 (needs {need})  {name} on {gname}")
    return bad

if __name__ == '__main__':
    from tokens import GROUNDS, PAIRS
    sys.exit(1 if check(GROUNDS, PAIRS) else 0)
