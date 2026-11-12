"""Minimal WordprocessingML writer for the study guide.

Paragraphs with inline markup, tables, callout boxes, PNG images, OMML equations, a TOC field
and page numbers. Written so the guide needs no third-party package; Word opens the result
without repair. Only what the guide uses is implemented.

Inline markup in text: **bold**, ~italic~, `code`, _{subscript}, ^{superscript},
<<https://url>> for a hyperlink, and provenance labels such as [SIM] rendered as coloured chips.
"""
from __future__ import annotations

import re
import struct
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from xml.sax.saxutils import escape

PAGE_W, PAGE_H, MARGIN = 11906, 16838, 1134
TEXT_W = PAGE_W - 2 * MARGIN  # 9638 twips
BODY = 21  # half-points (10.5 pt)

NAVY, BLUE, INK, INK2, GRID = "1F3A5F", "2A78D6", "1B1B1A", "52514E", "D9D8D3"
LABELS = {
    "SIM": ("1F5FAD", "E3EEFB"), "SYNTHETIC": ("B3261E", "FBE9E7"), "VIVADO-STA": ("127A55", "E2F5EE"),
    "HW": ("6B3FA0", "EFE8F8"), "OFFICIAL": ("1F3A5F", "E6EBF2"), "UNKNOWN": ("52514E", "EFEEEB"),
    "INFERENCE": ("52514E", "EFEEEB"), "PROPOSAL": ("52514E", "EFEEEB"), "HW-TBD": ("6B3FA0", "EFE8F8"),
}
CALLOUTS = {
    "intuisi": ("INTUISI", "FFF8E6", "EDA100"),
    "rumus": ("RUMUS KUNCI", "EEF4FC", "2A78D6"),
    "sentinel": ("DI SENTINEL", "E9F7F1", "1BAF7A"),
    "board": ("BELUM BISA DIJAWAB TANPA BOARD", "FCEDEC", "B3261E"),
    "latihan": ("LATIHAN", "F3F0FA", "6B3FA0"),
    "catatan": ("CATATAN", "F2F1EE", "8A8984"),
    "jujur": ("BATASAN YANG HARUS DITULIS JUJUR", "FCEDEC", "B3261E"),
}
TOKEN = re.compile(r"(\*\*.+?\*\*|~[^~\n]+?~|`[^`]+`|\[(?:SIM|SYNTHETIC|VIVADO-STA|HW|OFFICIAL|UNKNOWN|INFERENCE|PROPOSAL|HW-TBD)\]"
                   r"|_\{[^}]*\}|\^\{[^}]*\}|<<[^>]+>>)")
REL_IMAGE = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/image"
REL_LINK = "http://schemas.openxmlformats.org/officeDocument/2006/relationships/hyperlink"
NS = ('xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
      'xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships" '
      'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math" '
      'xmlns:wp="http://schemas.openxmlformats.org/drawingml/2006/wordprocessingDrawing" '
      'xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" '
      'xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture"')
W_NS = 'xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main"'


def esc(text: str) -> str:
    return escape(text, {'"': "&quot;"})


def run(text: str, b=False, i=False, code=False, color=None, size=None, vert=None, fill=None, font=None, caps=False,
        spacing=None, u=False) -> str:
    pr = []
    f = "Consolas" if code else font
    if f:
        pr.append(f'<w:rFonts w:ascii="{f}" w:hAnsi="{f}" w:cs="{f}"/>')
    if b:
        pr.append("<w:b/><w:bCs/>")
    if i:
        pr.append("<w:i/><w:iCs/>")
    if caps:
        pr.append("<w:caps/>")
    if color:
        pr.append(f'<w:color w:val="{color}"/>')
    if spacing:
        pr.append(f'<w:spacing w:val="{spacing}"/>')
    if size:
        pr.append(f'<w:sz w:val="{size}"/><w:szCs w:val="{size}"/>')
    if u:
        pr.append('<w:u w:val="single"/>')
    if fill:
        pr.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>')
    if vert:
        pr.append(f'<w:vertAlign w:val="{vert}"/>')
    rpr = f"<w:rPr>{''.join(pr)}</w:rPr>" if pr else ""
    pieces = text.split("\t")
    inner = "<w:tab/>".join(f'<w:t xml:space="preserve">{esc(p)}</w:t>' if p else "" for p in pieces)
    return f"<w:r>{rpr}{inner}</w:r>"


def para(runs, style=None, align=None, before=None, after=None, line=None, keep_next=False, keep_lines=False,
         page_break_before=False, ind_left=None, ind_hanging=None, num=None, border_left=None, shading=None, tabs=None,
         border_bottom=None) -> str:
    pp = []
    if style:
        pp.append(f'<w:pStyle w:val="{style}"/>')
    if keep_next:
        pp.append("<w:keepNext/>")
    if keep_lines:
        pp.append("<w:keepLines/>")
    if page_break_before:
        pp.append("<w:pageBreakBefore/>")
    if num:
        pp.append(f'<w:numPr><w:ilvl w:val="{num[1]}"/><w:numId w:val="{num[0]}"/></w:numPr>')
    if border_left or border_bottom:
        inner = ""
        if border_left:
            inner += f'<w:left w:val="single" w:sz="18" w:space="8" w:color="{border_left}"/>'
        if border_bottom:
            inner += f'<w:bottom w:val="single" w:sz="6" w:space="4" w:color="{border_bottom}"/>'
        pp.append(f"<w:pBdr>{inner}</w:pBdr>")
    if shading:
        pp.append(f'<w:shd w:val="clear" w:color="auto" w:fill="{shading}"/>')
    if tabs:
        pp.append("<w:tabs>" + "".join(f'<w:tab w:val="{v}" w:pos="{p}"/>' for v, p in tabs) + "</w:tabs>")
    if before is not None or after is not None or line is not None:
        attrs = ""
        if before is not None:
            attrs += f' w:before="{before}"'
        if after is not None:
            attrs += f' w:after="{after}"'
        if line is not None:
            attrs += f' w:line="{line}" w:lineRule="auto"'
        pp.append(f"<w:spacing{attrs}/>")
    if ind_left is not None or ind_hanging is not None:
        attrs = f' w:left="{ind_left or 0}"' + (f' w:hanging="{ind_hanging}"' if ind_hanging else "")
        pp.append(f"<w:ind{attrs}/>")
    if align:
        pp.append(f'<w:jc w:val="{align}"/>')
    ppr = f"<w:pPr>{''.join(pp)}</w:pPr>" if pp else ""
    return f"<w:p>{ppr}{''.join(runs)}</w:p>"


# ----------------------------------------------------------------------------- OMML (equations)

_MF = '<w:rPr><w:rFonts w:ascii="Cambria Math" w:hAnsi="Cambria Math"/></w:rPr>'


def mr(text: str, sty: str | None = None) -> str:
    pr = f'<m:rPr><m:sty m:val="{sty}"/></m:rPr>' if sty else ""
    return f'<m:r>{pr}{_MF}<m:t xml:space="preserve">{esc(text)}</m:t></m:r>'


def mi(text: str) -> str:
    """Math run in the default math style (letters italic, digits upright)."""
    return mr(text)


def mt(text: str) -> str:
    """Upright math text: function names, words, labels."""
    return mr(text, "p")


def frac(num: str, den: str) -> str:
    return f"<m:f><m:num>{num}</m:num><m:den>{den}</m:den></m:f>"


def sub(base: str, s: str) -> str:
    return f"<m:sSub><m:e>{base}</m:e><m:sub>{s}</m:sub></m:sSub>"


def sup(base: str, s: str) -> str:
    return f"<m:sSup><m:e>{base}</m:e><m:sup>{s}</m:sup></m:sSup>"


def subsup(base: str, s: str, p: str) -> str:
    return f"<m:sSubSup><m:e>{base}</m:e><m:sub>{s}</m:sub><m:sup>{p}</m:sup></m:sSubSup>"


def nary(lo: str, hi: str, body: str, ch: str = "∑") -> str:
    hide = ("" if lo else '<m:subHide m:val="1"/>') + ("" if hi else '<m:supHide m:val="1"/>')
    return (f'<m:nary><m:naryPr><m:chr m:val="{ch}"/><m:limLoc m:val="undOvr"/>{hide}</m:naryPr>'
            f"<m:sub>{lo}</m:sub><m:sup>{hi}</m:sup><m:e>{body}</m:e></m:nary>")


def delim(x: str, beg: str = "(", end: str = ")") -> str:
    return f'<m:d><m:dPr><m:begChr m:val="{esc(beg)}"/><m:endChr m:val="{esc(end)}"/></m:dPr><m:e>{x}</m:e></m:d>'


def func(name: str, arg: str, lim: str | None = None) -> str:
    fname = mt(name) if lim is None else f"<m:limLow><m:e>{mt(name)}</m:e><m:lim>{lim}</m:lim></m:limLow>"
    return f"<m:func><m:fName>{fname}</m:fName><m:e>{arg}</m:e></m:func>"


def rad(x: str) -> str:
    return f'<m:rad><m:radPr><m:degHide m:val="1"/></m:radPr><m:deg/><m:e>{x}</m:e></m:rad>'


def acc(x: str, ch: str = "̂") -> str:
    return f'<m:acc><m:accPr><m:chr m:val="{ch}"/></m:accPr><m:e>{x}</m:e></m:acc>'


def gap() -> str:
    return mt("  ")


# ----------------------------------------------------------------------------- document


class Doc:
    def __init__(self):
        self.body: list[str] = []
        self.rels: list[tuple[str, str, str, bool]] = []
        self.media: list[tuple[str, bytes]] = []
        self.nums: list[int] = []  # numId of each numbered list (bullet list is numId 1)
        self.pic_id = 0
        self.counters: dict[tuple[str, str], int] = {}
        self.chapter = "0"

    # relationships ----------------------------------------------------------
    def _rel(self, rtype: str, target: str, external: bool = False) -> str:
        rid = f"rIdX{len(self.rels) + 1}"
        self.rels.append((rid, rtype, target, external))
        return rid

    def _next(self, kind: str) -> str:
        key = (kind, self.chapter)
        self.counters[key] = self.counters.get(key, 0) + 1
        return f"{self.chapter}.{self.counters[key]}"

    # inline markup ----------------------------------------------------------
    def rich(self, text: str, **base) -> list[str]:
        out, pos = [], 0
        size = base.get("size") or BODY
        for m in TOKEN.finditer(text):
            if m.start() > pos:
                out.append(run(text[pos:m.start()], **base))
            tok = m.group(0)
            if tok.startswith("**"):
                out += self.rich(tok[2:-2], **{**base, "b": True})
            elif tok.startswith("~"):
                out += self.rich(tok[1:-1], **{**base, "i": True})
            elif tok.startswith("`"):
                out.append(run(tok[1:-1], **{**base, "code": True, "color": "3A3936", "size": size - 2}))
            elif tok.startswith("["):
                fg, bg = LABELS[tok[1:-1]]
                out.append(run(" " + tok + " ", b=True, color=fg, fill=bg, size=size - 4))
            elif tok.startswith("_{"):
                out.append(run(tok[2:-1], **{**base, "vert": "subscript"}))
            elif tok.startswith("^{"):
                out.append(run(tok[2:-1], **{**base, "vert": "superscript"}))
            else:
                url = tok[2:-2]
                rid = self._rel(REL_LINK, url, external=True)
                out.append(f'<w:hyperlink r:id="{rid}" w:history="1">{run(url, color=BLUE, size=size - 1, u=True)}</w:hyperlink>')
            pos = m.end()
        if pos < len(text):
            out.append(run(text[pos:], **base))
        return out

    # blocks -------------------------------------------------------------------
    def add(self, xml: str) -> None:
        self.body.append(xml)

    def h1(self, number: str, title: str, page_break: bool = True) -> None:
        self.chapter = number
        text = f"{number}. {title}" if number[0].isdigit() else f"Lampiran {number}. {title}"
        self.add(para([run(text)], style="Heading1", page_break_before=page_break))

    def h2(self, title: str) -> None:
        self.add(para(self.rich(title), style="Heading2"))

    def h3(self, title: str) -> None:
        self.add(para(self.rich(title), style="Heading3"))

    def p(self, text: str, align=None, after=None, before=None, size=None, color=None, keep_next=False, b=False, i=False) -> None:
        keep_next = keep_next or text.rstrip().endswith(":")
        self.add(para(self.rich(text, size=size, color=color, b=b, i=i), align=align, after=after, before=before, keep_next=keep_next))

    def bullets(self, items, level: int = 0, size=None) -> None:
        for it in items:
            if isinstance(it, (list, tuple)):
                self.bullets(it, level + 1, size)
                continue
            self.add(para(self.rich(it, size=size), num=(1, level), after=60))

    def numbered(self, items, size=None) -> None:
        num_id = 2 + len(self.nums)
        self.nums.append(num_id)
        for it in items:
            self.add(para(self.rich(it, size=size), num=(num_id, 0), after=60))

    def code(self, lines: list[str]) -> None:
        for k, ln in enumerate(lines):
            self.add(para([run(ln if ln else " ", code=True, size=17, color="2B2B2A")], shading="F4F4F2", border_left=BLUE,
                          before=60 if k == 0 else 0, after=60 if k == len(lines) - 1 else 0, line=240, ind_left=170,
                          keep_next=k < len(lines) - 1, keep_lines=True))

    def spacer(self, after: int = 60) -> None:
        self.add(para([], after=after, before=0, line=200))

    def page_break(self) -> None:
        self.add('<w:p><w:r><w:br w:type="page"/></w:r></w:p>')

    def picture(self, path: Path, width_cm: float, alt: str = "") -> str:
        """Inline PNG drawing run; the caller wraps it in a paragraph."""
        data = path.read_bytes()
        w_px, h_px = struct.unpack(">II", data[16:24])
        cx = int(width_cm * 360000)
        cy = int(cx * h_px / w_px)
        n = len(self.media) + 1
        target = f"media/image{n}.png"
        self.media.append((f"word/{target}", data))
        rid = self._rel(REL_IMAGE, target)
        self.pic_id += 1
        pid = self.pic_id
        return (f'<w:r><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0"><wp:extent cx="{cx}" cy="{cy}"/>'
                f'<wp:effectExtent l="0" t="0" r="0" b="0"/><wp:docPr id="{pid}" name="Gambar {pid}" descr="{esc(alt[:200])}"/>'
                '<wp:cNvGraphicFramePr><a:graphicFrameLocks noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                '<a:graphic><a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture"><pic:pic>'
                f'<pic:nvPicPr><pic:cNvPr id="{pid}" name="image{n}.png"/><pic:cNvPicPr/></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm><a:prstGeom prst="rect"><a:avLst/></a:prstGeom></pic:spPr>'
                "</pic:pic></a:graphicData></a:graphic></wp:inline></w:drawing></w:r>")

    def figure(self, path: Path, caption: str, width_cm: float = 17.0) -> str:
        label = self._next("fig")
        drawing = self.picture(path, width_cm, re.sub(r"[`*~]", "", caption))
        self.add(para([drawing], align="center", before=120, after=60, keep_next=True))
        self.add(para([run(f"Gambar {label}. ", b=True, color=NAVY, size=18)] + self.rich(caption, size=18, color=INK2), style="Caption"))
        return label

    def eq(self, omml: str) -> str:
        label = self._next("eq")
        mid = (f'<w:p><w:pPr><w:spacing w:before="40" w:after="40"/><w:jc w:val="center"/></w:pPr>'
               f'<m:oMathPara><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr><m:oMath>{omml}</m:oMath></m:oMathPara></w:p>')
        right = para([run(f"({label})", color=INK2, size=19)], align="right", after=0, before=0)
        cells = [para([], after=0), mid, right]
        widths = [900, TEXT_W - 1800, 900]
        tc = "".join(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>{c}</w:tc>' for w, c in zip(widths, cells))
        self.add(f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
                 '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
                 '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>'
                 f'<w:tblGrid>{"".join(f"<w:gridCol w:w=\"{w}\"/>" for w in widths)}</w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr>{tc}</w:tr></w:tbl>')
        self.add(para([], after=0, before=0, line=120))
        return label

    def table(self, header: list[str], rows: list[list], widths: list[int], caption: str | None = None, size: int = 18,
              align: list[str] | None = None, first_col_bold: bool = False, keep: bool | None = None) -> str | None:
        label = None
        if caption:
            label = self._next("tab")
            self.add(para([run(f"Tabel {label}. ", b=True, color=NAVY, size=18)] + self.rich(caption, size=18, color=INK2),
                          style="Caption", keep_next=True, before=160, align="left"))
        assert abs(sum(widths) - TEXT_W) < 5 or sum(widths) <= TEXT_W, (sum(widths), TEXT_W)
        total = sum(widths)
        align = align or ["left"] * len(widths)
        keep = len(rows) <= 15 if keep is None else keep

        def cell(content, w, fill=None, bold=False, color=None, al="left", kn=False):
            items = content if isinstance(content, list) else [content]
            ps = "".join(para(self.rich(str(it), size=size, b=bold, color=color), before=30, after=30, line=250, align=al, keep_next=kn)
                         for it in items)
            shd = f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>' if fill else ""
            return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{shd}<w:vAlign w:val="center"/></w:tcPr>{ps}</w:tc>'

        trs = []
        if header:
            trs.append('<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' +
                       "".join(cell(h, w, fill=NAVY, bold=True, color="FFFFFF", al=a, kn=keep) for h, w, a in zip(header, widths, align)) + "</w:tr>")
        for k, r in enumerate(rows):
            fill = "F6F8FB" if k % 2 else None
            trs.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' +
                       "".join(cell(c, w, fill=fill, bold=first_col_bold and j == 0, al=a, kn=keep and k < len(rows) - 1)
                               for j, (c, w, a) in enumerate(zip(r, widths, align))) + "</w:tr>")
        b = f'w:val="single" w:sz="4" w:space="0" w:color="{GRID}"'
        self.add(f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/>'
                 f'<w:tblBorders><w:top {b}/><w:left w:val="nil"/><w:bottom {b}/><w:right w:val="nil"/><w:insideH {b}/><w:insideV w:val="nil"/></w:tblBorders>'
                 '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="85" w:type="dxa"/><w:right w:w="85" w:type="dxa"/></w:tblCellMar>'
                 '<w:tblLook w:val="0000" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="0" w:noVBand="1"/></w:tblPr>'
                 f'<w:tblGrid>{"".join(f"<w:gridCol w:w=\"{w}\"/>" for w in widths)}</w:tblGrid>{"".join(trs)}</w:tbl>')
        self.add(para([], after=80, before=0, line=200))
        return label

    def callout(self, kind: str, items: list, title: str | None = None) -> None:
        t, fill, edge = CALLOUTS[kind]
        ps = [para([run(title or t, b=True, color=edge if kind != "intuisi" else "8A5A00", size=17, spacing=10)], after=60, before=20, keep_next=True)]
        for it in items:
            if isinstance(it, tuple) and it[0] == "bullet":
                ps.append(para(self.rich(it[1], size=20), num=(1, 0), after=40))
            elif isinstance(it, tuple) and it[0] == "num":
                ps.append(para(self.rich(it[1], size=20), after=40, ind_left=340, ind_hanging=340))
            else:
                ps.append(para(self.rich(it, size=20), after=60))
        tc = (f'<w:tc><w:tcPr><w:tcW w:w="{TEXT_W}" w:type="dxa"/>'
              f'<w:tcBorders><w:top w:val="nil"/><w:left w:val="single" w:sz="24" w:space="0" w:color="{edge}"/><w:bottom w:val="nil"/><w:right w:val="nil"/></w:tcBorders>'
              f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/><w:tcMar><w:top w:w="100" w:type="dxa"/><w:left w:w="200" w:type="dxa"/>'
              f'<w:bottom w:w="60" w:type="dxa"/><w:right w:w="200" w:type="dxa"/></w:tcMar></w:tcPr>{"".join(ps)}</w:tc>')
        self.add(f'<w:tbl><w:tblPr><w:tblW w:w="{TEXT_W}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
                 '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>'
                 f'<w:tblGrid><w:gridCol w:w="{TEXT_W}"/></w:tblGrid><w:tr>{tc}</w:tr></w:tbl>')
        self.add(para([], after=60, before=0, line=200))

    def toc(self) -> None:
        self.add('<w:p><w:pPr><w:spacing w:after="0"/></w:pPr><w:r><w:fldChar w:fldCharType="begin" w:dirty="true"/></w:r>'
                 '<w:r><w:instrText xml:space="preserve"> TOC \\o "1-2" \\h \\z \\u </w:instrText></w:r>'
                 '<w:r><w:fldChar w:fldCharType="separate"/></w:r>'
                 '<w:r><w:t>Daftar isi muncul setelah field diperbarui (di Word: klik kanan di sini, lalu Update Field).</w:t></w:r>'
                 '<w:r><w:fldChar w:fldCharType="end"/></w:r></w:p>')

    # package ------------------------------------------------------------------
    def save(self, path: Path, title: str, header_text: str) -> None:
        doc_rels = [("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "styles.xml", False),
                    ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings", "settings.xml", False),
                    ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering", "numbering.xml", False),
                    ("rId4", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/header", "header1.xml", False),
                    ("rId5", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer", "footer1.xml", False)] + self.rels
        rels_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
                    "".join(f'<Relationship Id="{i}" Type="{t}" Target="{esc(g)}"' + (' TargetMode="External"' if e else "") + "/>"
                            for i, t, g, e in doc_rels) + "</Relationships>")
        sect = (f'<w:sectPr><w:headerReference w:type="default" r:id="rId4"/><w:footerReference w:type="default" r:id="rId5"/>'
                f'<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/><w:pgMar w:top="{MARGIN}" w:right="{MARGIN}" w:bottom="{MARGIN}" w:left="{MARGIN}" '
                'w:header="567" w:footer="567" w:gutter="0"/><w:cols w:space="708"/><w:titlePg/></w:sectPr>')
        document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {NS}><w:body>' +
                    "".join(self.body) + sect + "</w:body></w:document>")
        header = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:hdr {NS}>' +
                  para([run(header_text, color="8A8984", size=16)], align="right", after=0, border_bottom="E4E3DF") + "</w:hdr>")
        footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {NS}><w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="0"/></w:pPr>'
                  '<w:r><w:rPr><w:color w:val="8A8984"/><w:sz w:val="17"/></w:rPr><w:t xml:space="preserve">Halaman </w:t></w:r>'
                  '<w:fldSimple w:instr=" PAGE "><w:r><w:rPr><w:color w:val="8A8984"/><w:sz w:val="17"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>')
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
                f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{esc(title)}</dc:title><dc:creator>SENTINEL study-guide generator</dc:creator>'
                f'<dc:language>id-ID</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
                f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
        app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
               "<Application>SENTINEL study-guide generator</Application></Properties>")
        content_types = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                         '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                         '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
                         '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                         '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                         '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
                         '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
                         '<Override PartName="/word/header1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.header+xml"/>'
                         '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
                         '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                         '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')
        root_rels = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                     '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                     '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                     '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>')
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", content_types)
            z.writestr("_rels/.rels", root_rels)
            z.writestr("docProps/core.xml", core)
            z.writestr("docProps/app.xml", app)
            z.writestr("word/document.xml", document)
            z.writestr("word/styles.xml", STYLES)
            z.writestr("word/settings.xml", SETTINGS)
            z.writestr("word/numbering.xml", self._numbering())
            z.writestr("word/header1.xml", header)
            z.writestr("word/footer1.xml", footer)
            z.writestr("word/_rels/document.xml.rels", rels_xml)
            for name, data in self.media:
                z.writestr(name, data)

    def _numbering(self) -> str:
        bullet = ('<w:abstractNum w:abstractNumId="0"><w:multiLevelType w:val="hybridMultilevel"/>'
                  '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="•"/><w:lvlJc w:val="left"/>'
                  '<w:pPr><w:ind w:left="397" w:hanging="227"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="2A78D6"/></w:rPr></w:lvl>'
                  '<w:lvl w:ilvl="1"><w:start w:val="1"/><w:numFmt w:val="bullet"/><w:lvlText w:val="–"/><w:lvlJc w:val="left"/>'
                  '<w:pPr><w:ind w:left="794" w:hanging="227"/></w:pPr><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri"/><w:color w:val="52514E"/></w:rPr></w:lvl>'
                  "</w:abstractNum>")
        decimal = ('<w:abstractNum w:abstractNumId="1"><w:multiLevelType w:val="hybridMultilevel"/>'
                   '<w:lvl w:ilvl="0"><w:start w:val="1"/><w:numFmt w:val="decimal"/><w:lvlText w:val="%1."/><w:lvlJc w:val="left"/>'
                   '<w:pPr><w:ind w:left="397" w:hanging="340"/></w:pPr><w:rPr><w:b/><w:color w:val="1F3A5F"/></w:rPr></w:lvl></w:abstractNum>')
        nums = '<w:num w:numId="1"><w:abstractNumId w:val="0"/></w:num>' + "".join(
            f'<w:num w:numId="{n}"><w:abstractNumId w:val="1"/><w:lvlOverride w:ilvl="0"><w:startOverride w:val="1"/></w:lvlOverride></w:num>'
            for n in self.nums)
        return f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:numbering {W_NS}>{bullet}{decimal}{nums}</w:numbering>'


def _style(sid, name, ppr="", rpr="", based="Normal", kind="paragraph", nxt="Normal", extra=""):
    b = f'<w:basedOn w:val="{based}"/>' if based else ""
    n = f'<w:next w:val="{nxt}"/>' if nxt else ""
    return (f'<w:style w:type="{kind}" w:styleId="{sid}"><w:name w:val="{name}"/>{b}{n}{extra}<w:qFormat/>'
            f"{f'<w:pPr>{ppr}</w:pPr>' if ppr else ''}{f'<w:rPr>{rpr}</w:rPr>' if rpr else ''}</w:style>")


STYLES = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:styles {W_NS}>'
    '<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:eastAsia="Calibri" w:cs="Calibri"/>'
    f'<w:color w:val="{INK}"/><w:sz w:val="{BODY}"/><w:szCs w:val="{BODY}"/><w:lang w:val="id-ID" w:eastAsia="en-US" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="120" w:line="276" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
    '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>'
    '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:semiHidden/>'
    '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
    '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>'
    + _style("Heading1", "heading 1",
             f'<w:keepNext/><w:keepLines/><w:pBdr><w:bottom w:val="single" w:sz="12" w:space="6" w:color="{BLUE}"/></w:pBdr>'
             '<w:spacing w:before="0" w:after="240" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="0"/>',
             f'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:b/><w:bCs/><w:color w:val="{NAVY}"/><w:sz w:val="40"/><w:szCs w:val="40"/>')
    + _style("Heading2", "heading 2", '<w:keepNext/><w:keepLines/><w:spacing w:before="300" w:after="100" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="1"/>',
             f'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:b/><w:bCs/><w:color w:val="{NAVY}"/><w:sz w:val="28"/><w:szCs w:val="28"/>')
    + _style("Heading3", "heading 3", '<w:keepNext/><w:keepLines/><w:spacing w:before="200" w:after="80" w:line="240" w:lineRule="auto"/><w:outlineLvl w:val="2"/>',
             f'<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:b/><w:bCs/><w:color w:val="{BLUE}"/><w:sz w:val="23"/><w:szCs w:val="23"/>')
    + _style("Caption", "caption", '<w:spacing w:before="0" w:after="200" w:line="240" w:lineRule="auto"/><w:jc w:val="center"/>',
             f'<w:color w:val="{INK2}"/><w:sz w:val="18"/><w:szCs w:val="18"/>')
    + _style("TOC1", "toc 1", f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W}"/></w:tabs><w:spacing w:before="100" w:after="20"/>',
             f'<w:b/><w:color w:val="{NAVY}"/>')
    + _style("TOC2", "toc 2", f'<w:tabs><w:tab w:val="right" w:leader="dot" w:pos="{TEXT_W}"/></w:tabs><w:spacing w:before="0" w:after="20"/><w:ind w:left="340"/>',
             '<w:sz w:val="20"/><w:szCs w:val="20"/>')
    + '<w:style w:type="character" w:styleId="Hyperlink"><w:name w:val="Hyperlink"/><w:basedOn w:val="DefaultParagraphFont"/>'
      f'<w:rPr><w:color w:val="{BLUE}"/><w:u w:val="single"/></w:rPr></w:style>'
    + "</w:styles>"
)

SETTINGS = (
    '<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
    '<w:settings xmlns:w="http://schemas.openxmlformats.org/wordprocessingml/2006/main" '
    'xmlns:m="http://schemas.openxmlformats.org/officeDocument/2006/math">'
    '<w:zoom w:percent="100"/><w:defaultTabStop w:val="709"/><w:characterSpacingControl w:val="doNotCompress"/>'
    '<w:compat><w:compatSetting w:name="compatibilityMode" w:uri="http://schemas.microsoft.com/office/word" w:val="15"/></w:compat>'
    '<m:mathPr><m:mathFont m:val="Cambria Math"/><m:brkBin m:val="before"/><m:brkBinSub m:val="--"/><m:smallFrac m:val="0"/>'
    '<m:dispDef/><m:lMargin m:val="0"/><m:rMargin m:val="0"/><m:defJc m:val="centerGroup"/><m:wrapIndent m:val="1440"/>'
    '<m:intLim m:val="subSup"/><m:naryLim m:val="undOvr"/></m:mathPr>'
    '<w:themeFontLang w:val="id-ID"/></w:settings>'
)
