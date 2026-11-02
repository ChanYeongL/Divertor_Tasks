#!/usr/bin/env python3
"""Replace every picture in an unpacked HWPX with a readable [FIGURE:<id>] note
and drop the image binaries from the package.

usage: strip_figures.py UNPACKED_DIR figure_slots.json
Pictures are matched to slots in document order (slot k = k-th <hp:pic>).
"""
import json, os, re, sys
from xml.sax.saxutils import escape

d, slots_path = sys.argv[1:]
slots = json.load(open(slots_path, encoding="utf-8"))
sec_path = os.path.join(d, "Contents", "section0.xml")
x = open(sec_path, encoding="utf-8").read()

pics = list(re.finditer(r"<hp:pic\b.*?</hp:pic>", x, re.S))
assert len(pics) == len(slots), (len(pics), len(slots))

def note(s):
    t = f"[FIGURE:{s['id']}] 그림 삽입 위치 | 기존(삭제됨): {s['was']} | 작성 시 필요한 데이터: {s['need']}"
    if s["ref"]:
        t += f" | 참고: {s['ref']}"
    return f"<hp:t>{escape(t)}</hp:t>"

out, pos, images = [], 0, []
for m, s in zip(pics, slots):
    images.append(re.search(r'binaryItemIDRef="([^"]+)"', m.group(0)).group(1))
    out.append(x[pos:m.start()])
    out.append(note(s))
    # drop the stale line-layout cache of this paragraph so Hancom re-flows the new text
    end_p = x.index("</hp:p>", m.end())
    tail = re.sub(r"<hp:linesegarray>.*?</hp:linesegarray>", "", x[m.end():end_p], flags=re.S)
    out.append(tail)
    pos = end_p
out.append(x[pos:])
open(sec_path, "w", encoding="utf-8").write("".join(out))

hpf_path = os.path.join(d, "Contents", "content.hpf")
hpf = open(hpf_path, encoding="utf-8").read()
for img in images:
    item = re.search(rf'<opf:item id="{img}" href="([^"]+)"[^>]*/>', hpf)
    os.remove(os.path.join(d, item.group(1)))
    hpf = hpf.replace(item.group(0), "")
open(hpf_path, "w", encoding="utf-8").write(hpf)
if os.path.isdir(os.path.join(d, "BinData")) and not os.listdir(os.path.join(d, "BinData")):
    os.rmdir(os.path.join(d, "BinData"))
print(len(images), "pictures replaced")
