#!/usr/bin/env python3
"""List the fonts of a PDF like poppler's `pdffonts` (name, type, emb, sub, uni, object), standard library only.

Used because poppler is not installed on every machine of the team. Reads plain objects and objects inside
compressed object streams (/ObjStm, FlateDecode). Exit status 1 if any font is not embedded.

    python tools/pdf_fonts.py build/study_guide/SENTINEL_paper.pdf
"""
from __future__ import annotations

import re
import sys
import zlib
from pathlib import Path

OBJ = re.compile(rb"(\d+)\s+(\d+)\s+obj\b(.*?)endobj", re.S)


def _stream(body: bytes) -> tuple[bytes, bytes | None]:
    m = re.search(rb"stream\r?\n", body)
    if not m:
        return body, None
    head, data = body[:m.start()], body[m.end():]
    data = data[:data.rfind(b"endstream")]
    if b"/FlateDecode" in head:
        try:
            data = zlib.decompress(data)
        except zlib.error:
            data = zlib.decompressobj().decompress(data)
    return head, data


def objects(pdf: bytes) -> dict[int, bytes]:
    out: dict[int, bytes] = {}
    for m in OBJ.finditer(pdf):
        num, body = int(m.group(1)), m.group(3)
        head, data = _stream(body)
        out[num] = head
        if data is not None and b"/ObjStm" in head:
            n = int(re.search(rb"/N\s+(\d+)", head).group(1))
            first = int(re.search(rb"/First\s+(\d+)", head).group(1))
            nums = [int(x) for x in data[:first].split()]
            pairs = list(zip(nums[0::2], nums[1::2]))[:n]
            for k, (onum, off) in enumerate(pairs):
                end = first + pairs[k + 1][1] if k + 1 < len(pairs) else len(data)
                out[onum] = data[first + off:end]
    return out


def ref(d: bytes, key: bytes) -> int | None:
    m = re.search(re.escape(key) + rb"\s*\[?\s*(\d+)\s+0\s+R", d)
    return int(m.group(1)) if m else None


def name(d: bytes, key: bytes) -> str:
    m = re.search(re.escape(key) + rb"\s*/([^\s/\[\]<>()]+)", d)
    return m.group(1).decode("latin-1") if m else "-"


def fonts(pdf: bytes) -> list[dict]:
    objs = objects(pdf)
    rows = []
    for num, d in sorted(objs.items()):
        if not re.search(rb"/Type\s*/Font\b", d) or b"/FontDescriptor" in d and b"/Subtype" not in d:
            continue
        subtype = name(d, b"/Subtype")
        if subtype in ("CIDFontType0", "CIDFontType2"):
            continue  # descendants are reported through their Type0 parent
        base = name(d, b"/BaseFont")
        desc_obj = d
        if subtype == "Type0":
            child = ref(d, b"/DescendantFonts")
            if child is not None and child not in objs:
                child = None
            if child is not None:
                # DescendantFonts may point to an array object
                arr = objs[child]
                inner = re.search(rb"(\d+)\s+0\s+R", arr)
                desc_obj = objs.get(int(inner.group(1)), arr) if inner and b"/Type" not in arr else arr
        fd = ref(desc_obj, b"/FontDescriptor")
        fdd = objs.get(fd, b"") if fd else b""
        emb = any(k in fdd for k in (b"/FontFile ", b"/FontFile/", b"/FontFile2", b"/FontFile3")) or bool(re.search(rb"/FontFile\s", fdd))
        if subtype == "Type3":
            emb = True
        enc = name(d, b"/Encoding")
        rows.append({"name": base, "type": subtype, "encoding": enc, "emb": emb, "sub": bool(re.match(r"[A-Z]{6}\+", base)),
                     "uni": b"/ToUnicode" in d, "obj": num})
    return rows


def tounicode_chars(pdf: bytes) -> dict[str, str]:
    """Non-ASCII characters each font maps through its /ToUnicode CMap (which glyphs the font really carries)."""
    raw = {int(m.group(1)): m.group(3) for m in OBJ.finditer(pdf)}
    objs = objects(pdf)
    out = {}
    for r in fonts(pdf):
        tu = ref(objs[r["obj"]], b"/ToUnicode")
        if tu is None or tu not in raw:
            continue
        _, cmap = _stream(raw[tu])
        chars = set()
        for block in re.findall(rb"beginbfchar(.*?)endbfchar", cmap or b"", re.S):
            for dst in re.findall(rb"<[0-9A-Fa-f]+>\s*<([0-9A-Fa-f]+)>", block):
                chars.add(bytes.fromhex(dst.decode()).decode("utf-16-be", "replace"))
        for block in re.findall(rb"beginbfrange(.*?)endbfrange", cmap or b"", re.S):
            for lo, hi, dst in re.findall(rb"<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>\s*<([0-9A-Fa-f]+)>", block):
                start = int(dst, 16)
                for k in range(int(hi, 16) - int(lo, 16) + 1):
                    chars.add(chr(start + k))
        out[r["name"]] = "".join(sorted(c for c in chars if ord(c) > 127))
    return out


def main() -> int:
    path = Path(sys.argv[1])
    rows = fonts(path.read_bytes())
    if "--chars" in sys.argv:
        for font, chars in tounicode_chars(path.read_bytes()).items():
            print(f"{font}: {chars}")
        print()
    print(f"{'name':<44} {'type':<14} {'encoding':<18} emb sub uni object ID")
    print(f"{'-' * 44} {'-' * 14} {'-' * 18} --- --- --- ---------")
    for r in rows:
        yn = lambda v: "yes" if v else "no "  # noqa: E731
        print(f"{r['name'][:44]:<44} {r['type'][:14]:<14} {r['encoding'][:18]:<18} {yn(r['emb'])} {yn(r['sub'])} {yn(r['uni'])} {r['obj']:>6} 0")
    missing = [r["name"] for r in rows if not r["emb"]]
    print(f"\n{len(rows)} fonts, {len(rows) - len(missing)} embedded" + (f"; NOT embedded: {', '.join(missing)}" if missing else ""))
    return 1 if missing else 0


if __name__ == "__main__":
    raise SystemExit(main())
