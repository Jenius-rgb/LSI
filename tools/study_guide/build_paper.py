#!/usr/bin/env python3
"""Build the SENTINEL paper (Indonesian, IEEE journal layout) as build/study_guide/SENTINEL_paper.docx and, on
Windows with Word, SENTINEL_paper.pdf next to it.

Two columns, Times New Roman, Roman-numbered sections, "Gbr."/"TABEL" captions and IEEE references. Text,
tables and diagrams are black and white; only the charts keep colour. Every number is read from result files
in the repository (or from build/study_guide/facts.json, written by tools/study_guide/figures.py).

    python tools/study_guide/figures.py     # facts.json (once per result change)
    python tools/study_guide/build_paper.py # this paper; --no-pdf skips Word
"""
from __future__ import annotations

import json
import re
import subprocess
import sys
import zipfile
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from common import FACTS, OUT, ROOT, load_json, nf, pct, regression_latest  # noqa: E402
from docx_lib import SETTINGS, W_NS, NS, Doc, delim, esc, gap, mi, mt, nary, para, run, sub, sup  # noqa: E402

OUT_DOCX = OUT / "SENTINEL_paper.docx"
PFIG = OUT / "paper_fig"

PAGE_W, PAGE_H = 11906, 16838
MAR_TB, MAR_LR = 1080, 1077
TEXT_W = PAGE_W - 2 * MAR_LR          # 9752 twips, 17,2 cm
COL_GAP = 284
COL_W = (TEXT_W - COL_GAP) // 2       # 4734 twips, 8,35 cm
FONT = "Times New Roman"
ROMAN = ["I", "II", "III", "IV", "V", "VI", "VII", "VIII", "IX", "X"]


# ============================================================================ writer


class Paper(Doc):
    """Doc with IEEE-like styles, black and white tables, sequential numbering and column sections."""

    def __init__(self):
        super().__init__()
        self.cur_cols = 1
        self.n_fig = self.n_tab = self.n_eq = self.n_sec = 0
        self.n_sub = 0

    # sections -------------------------------------------------------------
    def _sect(self, cols: int) -> str:
        c = f'<w:cols w:num="2" w:space="{COL_GAP}"/>' if cols == 2 else '<w:cols w:space="708"/>'
        return (f'<w:sectPr><w:footerReference w:type="default" r:id="rId5"/><w:type w:val="continuous"/>'
                f'<w:pgSz w:w="{PAGE_W}" w:h="{PAGE_H}"/><w:pgMar w:top="{MAR_TB}" w:right="{MAR_LR}" w:bottom="{MAR_TB}" '
                f'w:left="{MAR_LR}" w:header="567" w:footer="567" w:gutter="0"/>{c}</w:sectPr>')

    def cols(self, n: int) -> None:
        if n != self.cur_cols:
            self.add(f'<w:p><w:pPr><w:spacing w:before="0" w:after="0" w:line="20" w:lineRule="exact"/>{self._sect(self.cur_cols)}</w:pPr></w:p>')
            self.cur_cols = n

    # text -----------------------------------------------------------------
    def txt(self, text: str, indent: bool = True, keep_next: bool = False) -> None:
        ppr_extra = ""
        xml = para(self.rich(text), style="Body", keep_next=keep_next)
        if not indent:
            xml = xml.replace('<w:pStyle w:val="Body"/>', '<w:pStyle w:val="BodyFirst"/>')
        self.add(xml + ppr_extra)

    def section(self, title: str) -> None:
        self.n_sec += 1
        self.n_sub = 0
        self.add(para([run(f"{ROMAN[self.n_sec - 1]}. {title}")], style="Heading1"))

    def subsection(self, title: str) -> None:
        self.n_sub += 1
        self.add(para([run(f"{chr(64 + self.n_sub)}. {title}")], style="Heading2"))

    def items(self, entries: list[str], numbered: bool = True) -> None:
        for k, it in enumerate(entries, 1):
            mark = f"{k})" if numbered else "•"
            self.add(para([run(mark + "\t")] + self.rich(it), style="Item"))

    # floats ---------------------------------------------------------------
    def figure(self, path: Path, caption: str, width_cm: float = 16.0) -> int:
        self.n_fig += 1
        drawing = self.picture(path, width_cm, re.sub(r"[`*~]", "", caption))
        self.add(para([drawing], align="center", before=120, after=40, keep_next=True))
        self.add(para([run(f"Gbr. {self.n_fig}. ")] + self.rich(caption), style="Caption"))
        return self.n_fig

    def table(self, header: list[str], rows: list[list], widths: list[int], caption: str, align: list[str] | None = None) -> int:
        self.n_tab += 1
        self.add(para([run(f"TABEL {ROMAN[self.n_tab - 1]}")], style="TableCaption", keep_next=True))
        self.add(para(self.rich(caption), style="TableTitle", keep_next=True))
        total = sum(widths)
        align = align or ["left"] * len(widths)

        def cell(content, w, al, bottom=None, top=None, kn=False):
            ps = para(self.rich(str(content)), style="TableText", align=al, keep_next=kn)
            borders = ""
            if top or bottom:
                borders = "<w:tcBorders>" + (f'<w:top w:val="single" w:sz="{top}" w:space="0" w:color="000000"/>' if top else "") + \
                          (f'<w:bottom w:val="single" w:sz="{bottom}" w:space="0" w:color="000000"/>' if bottom else "") + "</w:tcBorders>"
            return f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/>{borders}<w:vAlign w:val="center"/></w:tcPr>{ps}</w:tc>'

        trs = ['<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' +
               "".join(cell(h, w, a, bottom=6, top=12, kn=True) for h, w, a in zip(header, widths, align)) + "</w:tr>"]
        for k, r in enumerate(rows):
            last = k == len(rows) - 1
            trs.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' +
                       "".join(cell(c, w, a, bottom=12 if last else None, kn=not last and len(rows) <= 12) for c, w, a in zip(r, widths, align)) + "</w:tr>")
        self.add(f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/>'
                 '<w:tblBorders><w:top w:val="nil"/><w:left w:val="nil"/><w:bottom w:val="nil"/><w:right w:val="nil"/>'
                 '<w:insideH w:val="nil"/><w:insideV w:val="nil"/></w:tblBorders>'
                 '<w:tblLayout w:type="fixed"/><w:tblCellMar><w:left w:w="57" w:type="dxa"/><w:right w:w="57" w:type="dxa"/></w:tblCellMar>'
                 '<w:tblLook w:val="0000" w:firstRow="1" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>'
                 f'<w:tblGrid>{"".join(f"<w:gridCol w:w=\"{w}\"/>" for w in widths)}</w:tblGrid>{"".join(trs)}</w:tbl>')
        self.add(para([], after=120, before=0, line=120))
        return self.n_tab

    def equation(self, omml: str) -> int:
        self.n_eq += 1
        width = COL_W if self.cur_cols == 2 else TEXT_W
        mid = (f'<w:p><w:pPr><w:spacing w:before="60" w:after="60"/><w:jc w:val="center"/></w:pPr>'
               f'<m:oMathPara><m:oMathParaPr><m:jc m:val="center"/></m:oMathParaPr><m:oMath>{omml}</m:oMath></m:oMathPara></w:p>')
        right = para([run(f"({self.n_eq})")], align="right", after=0, before=0)
        widths = [width - 560, 560]
        tc = "".join(f'<w:tc><w:tcPr><w:tcW w:w="{w}" w:type="dxa"/><w:vAlign w:val="center"/></w:tcPr>{c}</w:tc>' for w, c in zip(widths, (mid, right)))
        self.add(f'<w:tbl><w:tblPr><w:tblW w:w="{width}" w:type="dxa"/><w:tblLayout w:type="fixed"/>'
                 '<w:tblCellMar><w:left w:w="0" w:type="dxa"/><w:right w:w="0" w:type="dxa"/></w:tblCellMar>'
                 '<w:tblLook w:val="0000" w:firstRow="0" w:lastRow="0" w:firstColumn="0" w:lastColumn="0" w:noHBand="1" w:noVBand="1"/></w:tblPr>'
                 f'<w:tblGrid>{"".join(f"<w:gridCol w:w=\"{w}\"/>" for w in widths)}</w:tblGrid><w:tr><w:trPr><w:cantSplit/></w:trPr>{tc}</w:tr></w:tbl>')
        return self.n_eq

    def code(self, lines: list[str]) -> None:
        for k, ln in enumerate(lines):
            self.add(para([run(ln if ln else " ", font="Courier New", size=15)], before=40 if k == 0 else 0,
                          after=80 if k == len(lines) - 1 else 0, line=220, ind_left=170, keep_next=k < len(lines) - 1, keep_lines=True))

    def reference(self, n: int, text: str) -> None:
        self.add(para([run(f"[{n}]\t")] + self.rich(text), style="Reference"))

    # package --------------------------------------------------------------
    def save(self, path: Path, title: str) -> None:
        rels = [("rId1", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/styles", "styles.xml", False),
                ("rId2", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/settings", "settings.xml", False),
                ("rId3", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/numbering", "numbering.xml", False),
                ("rId5", "http://schemas.openxmlformats.org/officeDocument/2006/relationships/footer", "footer1.xml", False)] + self.rels
        rels_xml = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n'
                    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">' +
                    "".join(f'<Relationship Id="{i}" Type="{t}" Target="{esc(g)}"' + (' TargetMode="External"' if e else "") + "/>"
                            for i, t, g, e in rels) + "</Relationships>")
        document = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:document {NS}><w:body>' +
                    "".join(self.body_xml()) + self._sect(self.cur_cols) + "</w:body></w:document>")
        footer = (f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:ftr {NS}><w:p><w:pPr><w:jc w:val="center"/><w:spacing w:after="0"/></w:pPr>'
                  '<w:fldSimple w:instr=" PAGE "><w:r><w:rPr><w:sz w:val="16"/></w:rPr><w:t>1</w:t></w:r></w:fldSimple></w:p></w:ftr>')
        now = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")
        core = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<cp:coreProperties xmlns:cp="http://schemas.openxmlformats.org/package/2006/metadata/core-properties" '
                'xmlns:dc="http://purl.org/dc/elements/1.1/" xmlns:dcterms="http://purl.org/dc/terms/" xmlns:dcmitype="http://purl.org/dc/dcmitype/" '
                f'xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"><dc:title>{esc(title)}</dc:title><dc:creator>Tim SENTINEL</dc:creator>'
                f'<dc:language>id-ID</dc:language><dcterms:created xsi:type="dcterms:W3CDTF">{now}</dcterms:created>'
                f'<dcterms:modified xsi:type="dcterms:W3CDTF">{now}</dcterms:modified></cp:coreProperties>')
        app = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Properties xmlns="http://schemas.openxmlformats.org/officeDocument/2006/extended-properties">'
               "<Application>SENTINEL paper generator</Application></Properties>")
        ctypes = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
                  '<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
                  '<Default Extension="xml" ContentType="application/xml"/><Default Extension="png" ContentType="image/png"/>'
                  '<Override PartName="/word/document.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.document.main+xml"/>'
                  '<Override PartName="/word/styles.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.styles+xml"/>'
                  '<Override PartName="/word/settings.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.settings+xml"/>'
                  '<Override PartName="/word/numbering.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.numbering+xml"/>'
                  '<Override PartName="/word/footer1.xml" ContentType="application/vnd.openxmlformats-officedocument.wordprocessingml.footer+xml"/>'
                  '<Override PartName="/docProps/core.xml" ContentType="application/vnd.openxmlformats-package.core-properties+xml"/>'
                  '<Override PartName="/docProps/app.xml" ContentType="application/vnd.openxmlformats-officedocument.extended-properties+xml"/></Types>')
        root = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
                '<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="word/document.xml"/>'
                '<Relationship Id="rId2" Type="http://schemas.openxmlformats.org/package/2006/relationships/metadata/core-properties" Target="docProps/core.xml"/>'
                '<Relationship Id="rId3" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/extended-properties" Target="docProps/app.xml"/></Relationships>')
        path.parent.mkdir(parents=True, exist_ok=True)
        with zipfile.ZipFile(path, "w", zipfile.ZIP_DEFLATED) as z:
            z.writestr("[Content_Types].xml", ctypes)
            z.writestr("_rels/.rels", root)
            z.writestr("docProps/core.xml", core)
            z.writestr("docProps/app.xml", app)
            z.writestr("word/document.xml", document)
            z.writestr("word/styles.xml", STYLES)
            z.writestr("word/settings.xml", SETTINGS.replace("<w:zoom w:percent=\"100\"/>", "<w:zoom w:percent=\"100\"/><w:autoHyphenation/>"))
            z.writestr("word/numbering.xml", self._numbering())
            z.writestr("word/footer1.xml", footer)
            z.writestr("word/_rels/document.xml.rels", rels_xml)
            for name, data in self.media:
                z.writestr(name, data)

    def body_xml(self) -> list[str]:
        return self.body


def _style(sid, name, ppr="", rpr="", based="Normal", kind="paragraph", nxt=None):
    b = f'<w:basedOn w:val="{based}"/>' if based else ""
    n = f'<w:next w:val="{nxt}"/>' if nxt else ""
    return (f'<w:style w:type="{kind}" w:styleId="{sid}"><w:name w:val="{name}"/>{b}{n}<w:qFormat/>'
            f"{f'<w:pPr>{ppr}</w:pPr>' if ppr else ''}{f'<w:rPr>{rpr}</w:rPr>' if rpr else ''}</w:style>")


_SZ = lambda hp: f'<w:sz w:val="{hp}"/><w:szCs w:val="{hp}"/>'  # noqa: E731
STYLES = (
    f'<?xml version="1.0" encoding="UTF-8" standalone="yes"?>\n<w:styles {W_NS}>'
    f'<w:docDefaults><w:rPrDefault><w:rPr><w:rFonts w:ascii="{FONT}" w:hAnsi="{FONT}" w:eastAsia="{FONT}" w:cs="{FONT}"/>'
    f'<w:color w:val="000000"/>{_SZ(20)}<w:lang w:val="id-ID" w:eastAsia="en-US" w:bidi="ar-SA"/></w:rPr></w:rPrDefault>'
    '<w:pPrDefault><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/></w:pPr></w:pPrDefault></w:docDefaults>'
    '<w:style w:type="paragraph" w:default="1" w:styleId="Normal"><w:name w:val="Normal"/><w:qFormat/></w:style>'
    '<w:style w:type="character" w:default="1" w:styleId="DefaultParagraphFont"><w:name w:val="Default Paragraph Font"/><w:uiPriority w:val="1"/><w:semiHidden/></w:style>'
    '<w:style w:type="table" w:default="1" w:styleId="TableNormal"><w:name w:val="Normal Table"/><w:semiHidden/>'
    '<w:tblPr><w:tblInd w:w="0" w:type="dxa"/><w:tblCellMar><w:top w:w="0" w:type="dxa"/><w:left w:w="108" w:type="dxa"/>'
    '<w:bottom w:w="0" w:type="dxa"/><w:right w:w="108" w:type="dxa"/></w:tblCellMar></w:tblPr></w:style>'
    + _style("Title", "Title", '<w:jc w:val="center"/><w:spacing w:before="0" w:after="200" w:line="240" w:lineRule="auto"/>', _SZ(48))
    + _style("Author", "Author", '<w:jc w:val="center"/><w:spacing w:before="0" w:after="60"/>', _SZ(22))
    + _style("Affil", "Affiliation", '<w:jc w:val="center"/><w:spacing w:before="0" w:after="280"/>', "<w:i/><w:iCs/>" + _SZ(18))
    + _style("Abstract", "Abstract", '<w:jc w:val="both"/><w:spacing w:before="0" w:after="120"/>', "<w:b/><w:bCs/>" + _SZ(18))
    + _style("Body", "Body Text", '<w:jc w:val="both"/><w:ind w:firstLine="202"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>', _SZ(20))
    + _style("BodyFirst", "Body First", '<w:jc w:val="both"/><w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>', _SZ(20))
    + _style("Item", "List Item", '<w:jc w:val="both"/><w:tabs><w:tab w:val="left" w:pos="340"/></w:tabs><w:ind w:left="340" w:hanging="340"/>'
             '<w:spacing w:before="20" w:after="20"/>', _SZ(20))
    + _style("Heading1", "heading 1", '<w:keepNext/><w:keepLines/><w:jc w:val="center"/><w:spacing w:before="240" w:after="120"/><w:outlineLvl w:val="0"/>',
             "<w:smallCaps/>" + _SZ(20))
    + _style("Heading2", "heading 2", '<w:keepNext/><w:keepLines/><w:spacing w:before="120" w:after="60"/><w:outlineLvl w:val="1"/>',
             "<w:i/><w:iCs/>" + _SZ(20))
    + _style("Caption", "caption", '<w:jc w:val="both"/><w:spacing w:before="0" w:after="200" w:line="220" w:lineRule="auto"/>', _SZ(16))
    + _style("TableCaption", "Table Caption", '<w:keepNext/><w:jc w:val="center"/><w:spacing w:before="200" w:after="0"/>', "<w:smallCaps/>" + _SZ(16))
    + _style("TableTitle", "Table Title", '<w:keepNext/><w:jc w:val="center"/><w:spacing w:before="0" w:after="80"/>', "<w:smallCaps/>" + _SZ(16))
    + _style("TableText", "Table Text", '<w:spacing w:before="20" w:after="20" w:line="220" w:lineRule="auto"/>', _SZ(16))
    + _style("Reference", "Reference", '<w:jc w:val="both"/><w:tabs><w:tab w:val="left" w:pos="397"/></w:tabs><w:ind w:left="397" w:hanging="397"/>'
             '<w:spacing w:before="0" w:after="30"/>', _SZ(16))
    + "</w:styles>"
)


# ============================================================================ context and figures


def clocks(summary: dict) -> dict:
    return {c["name"]: c for c in summary["clocks"] if "fmax_mhz" in c}


def load_context() -> dict:
    if not FACTS.exists():
        raise SystemExit("build/study_guide/facts.json is missing: run tools/study_guide/figures.py first")
    ctx = {"facts": json.loads(FACTS.read_text(encoding="utf-8"))}
    ctx["arch"] = load_json("results/model/arch_s.json")
    ctx["fl"] = {m: load_json(f"results/model/{m}/float_result.json") for m in ("s", "xs")}
    ctx["qr"] = {m: load_json(f"results/model/{m}/quant_result.json") for m in ("s", "xs")}
    ctx["camp"] = load_json("results/sim/campaign_s.json")
    ctx["reg"] = regression_latest()
    ctx["lut"] = load_json("results/vivado/official/summary.json")
    ctx["dsp"] = load_json("results/vivado/official_dsp/summary.json")
    return ctx


def camp_row(ctx, k, c3, kind) -> dict:
    return next(r for r in ctx["camp"]["rows"] if r["k"] == k and r["c3"] == c3 and r["kind"] == kind)


def cycles(entry: dict) -> tuple[int, int]:
    m = re.search(r"cycles_mean=(\d+) ideal=(\d+)", entry["summary"])
    return int(m.group(1)), int(m.group(2))


def fig(name: str) -> Path:
    return PFIG / f"{name}.png"


def make_figures(ctx) -> None:
    import matplotlib.pyplot as plt
    import figures as F

    F.FIG = PFIG
    F.setup()
    F.tag = lambda *a, **k: None  # no provenance tags in the paper's charts
    colours = ("BLUE", "ORANGE", "GREEN", "YELLOW", "NAVY", "RED", "STA_GREEN", "HW_PURPLE", "SAFE_FILL", "FAST_FILL", "HOST_FILL")
    saved = {n: getattr(F, n) for n in colours}
    for n in colours[:8]:
        setattr(F, n, "#000000")
    F.SAFE_FILL, F.FAST_FILL, F.HOST_FILL = "#ffffff", "#ececec", "#ffffff"
    F.fig_system()
    F.fig_dataflow()
    F.fig_decision()
    F.fig_timing()
    from PIL import Image

    for name in ("fig_system", "fig_dataflow", "fig_decision", "fig_timing"):
        Image.open(PFIG / f"{name}.png").convert("L").save(PFIG / f"{name}.png")
    for n, v in saved.items():
        setattr(F, n, v)
    F.fig_campaign()
    F.fig_governor({})

    lut, dsp = ctx["lut"], ctx["dsp"]
    names = [("lut", "Slice LUT"), ("ff", "Flip-flop"), ("bram_tile", "Block RAM"), ("dsp", "DSP48E1")]
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(F.W, 2.6), gridspec_kw={"width_ratios": [1.0, 1.15], "wspace": 0.42})
    y = list(range(len(names)))[::-1]
    h = 0.36
    for off, (s, col, lab) in zip((h / 2 + 0.02, -h / 2 - 0.02), ((lut, F.BLUE, "varian LUT"), (dsp, F.ORANGE, "varian DSP"))):
        u = s["utilization_post_route"]
        vals = [u[k]["util_pct"] for k, _ in names]
        a1.barh([v + off for v in y], vals, height=h, color=col, label=lab)
        for yy, v, (k, _) in zip(y, vals, names):
            a1.text(v + 1.2, yy + off, nf(u[k]["used"]), va="center", fontsize=6.8, color=F.INK2)
    a1.set_yticks(y, [n for _, n in names])
    a1.set_xlim(0, 60)
    a1.set_xlabel("% dari kapasitas XC7S25")
    a1.set_title("Resource sesudah place & route")
    F.bar_axis(a1, "x")
    a1.legend(loc="lower right", fontsize=7)
    cl_l, cl_d = clocks(lut), clocks(dsp)
    rows = [("LUT: clk_safe", cl_l["clk_safe_raw"]["fmax_mhz"], F.BLUE), ("LUT: lane", cl_l["clk_fast_turbo"]["fmax_mhz"], F.BLUE),
            ("DSP: clk_safe", cl_d["clk_safe_raw"]["fmax_mhz"], F.ORANGE), ("DSP: lane", cl_d["clk_fast_turbo"]["fmax_mhz"], F.ORANGE)]
    yy = list(range(len(rows)))[::-1]
    a2.barh(yy, [r[1] for r in rows], height=0.55, color=[r[2] for r in rows])
    for y0, (_, v, _) in zip(yy, rows):
        a2.text(v + 4, y0, f"{nf(v, 1)} MHz", va="center", fontsize=6.8, color=F.INK2)
    a2.set_yticks(yy, [r[0] for r in rows])
    a2.set_xlim(0, 320)
    for x, txt in ((125, "clock aman\n125 MHz"), (250, "batas suplai\noperand 250 MHz")):
        a2.axvline(x, color=F.INK2, lw=0.9, ls=(0, (3, 2)))
        a2.text(x, len(rows) - 0.35, txt, ha="center", va="bottom", fontsize=6.5, color=F.INK2, linespacing=1.0)
    a2.set_xlabel("Fmax statis (MHz)")
    a2.set_title("Frekuensi menurut STA", pad=22)
    F.bar_axis(a2, "x")
    F.save(fig, "fig_variants")


# ============================================================================ content


REFS = [
    ("lsi", "LSI Design Contest, \"Design specification.\" [Online]. Available: https://www.lsi-contest.com/shiyou_1e.html"),
    ("cham", "Chamberlin ~et al.~, \"Understanding timing error characteristics from overclocked systolic multiply–accumulate arrays in FPGAs,\" ~J. Low Power Electron. Appl.~, vol. 14, no. 1, art. no. 4, 2024."),
    ("marty", "T. Marty, T. Yuki, and S. Derrien, \"Safe overclocking for CNN accelerators through algorithm-level error detection,\" ~IEEE Trans. Comput.-Aided Design Integr. Circuits Syst.~, vol. 39, no. 12, pp. 4777–4790, Dec. 2020, doi: 10.1109/TCAD.2020.2981056."),
    ("huang", "K.-H. Huang and J. A. Abraham, \"Algorithm-based fault tolerance for matrix operations,\" ~IEEE Trans. Comput.~, vol. C-33, no. 6, pp. 518–528, Jun. 1984."),
    ("zhao", "K. Zhao ~et al.~, \"FT-CNN: Algorithm-based fault tolerance for convolutional neural networks,\" ~IEEE Trans. Parallel Distrib. Syst.~, 2021, arXiv:2003.12203."),
    ("hari", "S. K. S. Hari, M. B. Sullivan, T. Tsai, and S. W. Keckler, \"Making convolutions resilient via algorithm-based error detection techniques,\" arXiv:2006.04984, 2020."),
    ("aos", "Jiang, Yu, Chen, and Ha, \"AOS: An automated overclocking system for high-performance CNN accelerator through timing delay measurement on FPGA,\" ~IEEE Trans. Comput.-Aided Design Integr. Circuits Syst.~, 2023."),
    ("li", "Li, Xu, Xing, Liu, Wang, Li, and Li, \"Squeezing the last MHz for CNN acceleration on FPGAs,\" in ~Proc. IEEE Int. Test Conf. Asia (ITC-Asia)~, 2019, pp. 151–156, doi: 10.1109/ITC-Asia.2019.00039."),
    ("thunder", "J. Zhang ~et al.~, \"ThUnderVolt: Enabling aggressive voltage underscaling and timing error resilience for energy efficient deep neural network accelerators,\" arXiv:1802.03806, 2018."),
    ("gao", "Gao ~et al.~, \"Detect and replace: Efficient soft error protection of FPGA-based CNN accelerators,\" ~IEEE Trans. Very Large Scale Integr. (VLSI) Syst.~, vol. 33, no. 1, 2024, doi: 10.1109/TVLSI.2024.3443834."),
    ("parhi", "K. K. Parhi, ~VLSI Digital Signal Processing Systems: Design and Implementation~. New York, NY, USA: Wiley, 1999."),
    ("review", "Jiang, Zhou, Gong, Yuan, and Liu, \"FPGA-based acceleration for convolutional neural networks: A comprehensive review,\" arXiv:2505.13461, 2025."),
]
CITE = {key: k + 1 for k, (key, _) in enumerate(REFS)}


def c(*keys: str) -> str:
    nums = sorted(CITE[k] for k in keys)
    return "[" + "], [".join(str(n) for n in nums) + "]"


def sn(x: int) -> str:
    return ("−" if x < 0 else "") + nf(abs(x))


def title_block(d: Paper, ctx) -> None:
    lut, dsp = ctx["lut"], ctx["dsp"]
    cyc, ideal = cycles(ctx["reg"]["engine_s_k8_c1_n200"])
    single = camp_row(ctx, 8, 1, "single")
    d.add(para([run("SENTINEL: Akselerator CNN dengan Checksum Tertimbang untuk Overclocking Aman pada FPGA Spartan-7")], style="Title"))
    d.add(para([run("Tim SENTINEL")], style="Author"))
    d.add(para([run("LSI Design Contest")], style="Affil"))
    d.add(para([run("Abstrak", b=True, i=True), run("—", b=True)] + d.rich(
        "Frekuensi clock yang dilaporkan analisis timing statis (STA) dihitung untuk kondisi terburuk, sehingga chip FPGA nyata biasanya masih "
        "bekerja benar di atas frekuensi itu. Ruang ini tidak bisa dipakai begitu saja karena error timing muncul tanpa tanda. SENTINEL adalah "
        "akselerator CNN INT8 untuk FPGA AMD Spartan-7 XC7S25 yang memisahkan lane multiply-accumulate (MAC) ke domain clock yang dapat "
        "dipercepat, sementara memori, kontrol, dan pemeriksa berjalan di domain clock aman. Di samping K lane data terdapat tiga lane "
        "checksum dengan bobot Σw_{k}, Σk·w_{k}, dan Σk²·w_{k}. Selisih ketiganya mendeteksi error, menunjuk lane yang salah, dan memberi nilai "
        "koreksinya, sehingga error satu lane diperbaiki di tempat tanpa hitung ulang. Kami menunjukkan bahwa checksum ketiga menjamin error "
        "dua lane tidak pernah salah dikoreksi. Governor di dalam FPGA memilih frekuensi lane per layer dari jumlah error yang tertangkap. "
        f"Dalam simulasi RTL, hasil akselerator identik bit demi bit dengan golden model pada 200 gambar uji, dan {nf(single['corrected'])} dari "
        f"{nf(single['n'])} error satu lane yang disuntikkan terkoreksi. Implementasi lengkap muat di XC7S25CSGA225-1 dengan "
        f"{nf(lut['utilization_post_route']['lut']['used'])} LUT untuk varian lane LUT dan {nf(dsp['utilization_post_route']['lut']['used'])} LUT "
        f"ditambah 14 DSP untuk varian lane DSP, dengan lane yang mengisi {pct(ctx['arch']['total_macs'] / (8 * cyc))} siklus kerjanya."), style="Abstract"))
    d.add(para([run("Kata Kunci", b=True, i=True), run("—", b=True)] + d.rich(
        "akselerator CNN, FPGA Spartan-7, overclocking, algorithm-based fault tolerance, checksum, toleransi kesalahan."), style="Abstract", after=240))
    d.cols(2)


def sec_intro(d: Paper, ctx) -> None:
    d.section("Pendahuluan")
    d.txt("Kecepatan akselerator CNN kira-kira sebanding dengan jumlah unit multiply-accumulate (MAC) yang bekerja paralel dikali frekuensi "
           "clock. Pada FPGA kecil seperti AMD Spartan-7 XC7S25, chip yang ditetapkan LSI Design Contest pada board ZERO7 {lsi}, "
           "hanya tersedia 14.600 LUT, 80 DSP, dan 45 block RAM. Jumlah unit dibatasi area, sehingga frekuensi menjadi sumber kecepatan yang "
           "tersisa.".format(lsi=c("lsi")), indent=False)
    d.txt("Frekuensi maksimum yang diizinkan alat sintesis berasal dari analisis timing statis (STA). STA mengandaikan proses fabrikasi paling "
           "lambat, suhu tertinggi, dan tegangan terendah terjadi bersamaan, sehingga chip yang bekerja pada suhu ruang dengan catu daya normal "
           f"umumnya masih benar di frekuensi yang lebih tinggi. Pengukuran pada array MAC di FPGA Zybo menunjukkan error baru muncul di sekitar "
           f"315 MHz, padahal STA memperkirakan sekitar 168 MHz {c('cham')}. Akselerator CNN yang di-overclock dengan pemeriksaan checksum mencapai "
           f"rata-rata 68% throughput lebih tinggi {c('marty')}.")
    d.txt("Masalahnya, ketika frekuensi melewati batas chip, sebagian bit tertangkap salah tanpa alarm apa pun (Gbr. 1). Bagi akselerator CNN, "
           "akibatnya berupa kanal fitur yang menyimpang, logit yang bergeser, atau kelas yang berubah. Overclocking hanya berguna kalau setiap "
           "kesalahan tertangkap, dan sebaiknya diperbaiki tanpa mengulang perhitungan.")
    d.cols(1)
    d.figure(fig("fig_timing"), "Jalur timing antara dua flip-flop. Pada clock aman data stabil sebelum tepi clock (slack positif). Pada clock "
             "yang terlalu cepat data masih berubah saat ditangkap, sehingga flip-flop menyimpan nilai yang salah.", 15.0)
    d.cols(2)
    d.txt("Makalah ini menyajikan SENTINEL, akselerator CNN INT8 untuk XC7S25 yang menggabungkan checksum berbasis algoritma dengan "
           "domain clock lane yang dapat dipercepat. Kontribusinya sebagai berikut:", indent=True)
    d.items([
        "Arsitektur dua domain clock yang hanya mempercepat lane MAC, sementara pembangkit operand, pemeriksa, dan memori tetap di domain yang "
        "lolos timing.",
        "Skema deteksi, lokalisasi, dan koreksi error satu lane di tempat memakai tiga checksum tertimbang, beserta bukti bahwa checksum ketiga "
        "mencegah salah koreksi pada error dua lane.",
        "Governor frekuensi per layer yang seluruhnya berada di dalam FPGA, tanpa CPU, dengan perpindahan clock bebas glitch dan rekonfigurasi MMCM.",
        "Implementasi RTL yang identik bit demi bit dengan golden model, dalam dua varian lane (LUT dan DSP) yang muat di XC7S25CSGA225-1.",
    ])
    d.txt("Bagian II membahas karya terkait. Bagian III menjelaskan arsitektur, Bagian IV skema checksum, dan Bagian V governor. Bagian VI "
           "menjelaskan infrastruktur pengujian, Bagian VII menyajikan hasil, dan Bagian VIII menutup makalah.")


def sec_related(d: Paper, ctx) -> None:
    d.section("Karya Terkait")
    d.txt(f"Algorithm-based fault tolerance (ABFT) memeriksa hasil komputasi memakai sifat aljabar algoritmanya; checksum baris dan kolom untuk "
           f"operasi matriks diperkenalkan oleh Huang dan Abraham {c('huang')}. FT-CNN menerapkan ABFT pada berbagai implementasi konvolusi dengan "
           f"overhead 4–8% {c('zhao')}, dan Hari dkk. memakai checksum untuk mendeteksi error konvolusi di GPU {c('hari')}. Karya-karya ini "
           "berfokus pada deteksi dan tidak menyasar error timing di FPGA.", indent=False)
    d.txt(f"Marty dkk. menjalankan akselerator CNN di FPGA di atas frekuensi nominal dan memakai satu checksum masukan dan satu checksum "
           f"keluaran per tile; tile yang salah dihitung ulang di frekuensi dasar, dan frekuensi diatur software per tile {c('marty')}. Mereka "
           "secara eksplisit tidak mengoreksi error karena dua error dalam satu tile dianggap sering terjadi. AOS memilih frekuensi dari monitor "
           f"delay tanpa checksum {c('aos')}, dan Li dkk. membahas overclocking akselerator CNN dengan alur dari deteksi sampai pemulihan {c('li')}. "
           f"ThUnderVolt menurunkan tegangan sampai error timing muncul pada akselerator mirip TPU dalam simulasi {c('thunder')}. Chamberlin dkk. "
           f"mengkarakterisasi error timing array MAC yang di-overclock dan menemukan bahwa error bersifat deterministik dan bergantung data {c('cham')}. "
           f"Pada sisi soft error, Gao dkk. melindungi array PE akselerator CNN dari radiasi {c('gao')}.")
    d.txt("SENTINEL berbeda pada tiga hal. Pemeriksaan dilakukan per unit hitung, yaitu satu posisi keluaran untuk K kanal, sehingga error satu "
           "lane dapat ditunjuk dan dikoreksi di tempat. Frekuensi dipilih per layer oleh governor hardware tanpa CPU. Pemeriksa sendiri tidak "
           "pernah di-overclock karena berada di domain clock aman.")


def sec_arch(d: Paper, ctx) -> None:
    arch, qs = ctx["arch"], ctx["qr"]["s"]
    d.section("Arsitektur SENTINEL")
    d.subsection("Gambaran Umum")
    d.txt("SENTINEL membagi desain menjadi dua domain clock (Gbr. 2). Domain clk_safe memuat memori bobot dan aktivasi, pembangkit operand, "
           "pembangkit bobot checksum, komparator dan korektor, post-processing, pooling, governor, dan antarmuka SPI ke Raspberry Pi. Domain ini "
           "selalu berjalan pada frekuensi yang lolos STA, yaitu 125 MHz. Domain clk_fast hanya memuat lane MAC, register penampung hasil, dan "
           "serializer. Clock domain ini dipilih oleh BUFGCTRL antara clock aman dan clock turbo dari MMCM kedua yang frekuensinya dapat diubah "
           "saat berjalan. Operand dan hasil menyeberang antar-domain melalui FIFO asinkron dengan pointer Gray code, sehingga kedua clock tidak "
           "memerlukan hubungan fase.", indent=False)
    d.cols(1)
    d.figure(fig("fig_system"), "Arsitektur SENTINEL. Hanya lane MAC (kanan) yang berjalan di clock cepat; memori, pembangkit operand, "
             "komparator, governor, dan antarmuka berada di domain clock aman.", 16.0)
    d.cols(2)
    d.subsection("Model CNN dan Aritmetika Integer")
    d.txt("Model yang diimplementasikan terdiri dari tiga konvolusi 3×3 dengan ReLU dan max pooling 2×2, diikuti satu layer fully connected "
           "(Tabel I). Input berupa gambar 32×32 RGB.", indent=False)
    rows = []
    for L in arch["layers"]:
        inp = L["input"]
        if L["kind"] == "conv":
            op = f"konv 3×3, {inp[0]}→{L['output_channels']}"
        else:
            n_in = 1
            for v in inp:
                n_in *= v
            op = f"FC {nf(n_in)}→{L['output_channels']}"
        rows.append([L["name"], op, nf(L["weights"]), nf(L["macs"])])
    rows.append(["total", "", nf(arch["total_weights"]), nf(arch["total_macs"])])
    d.table(["Layer", "Operasi", "Bobot", "MAC"], rows, [900, 1700, 950, 1100], "Struktur model CNN", align=["left", "left", "right", "right"])
    d.txt("Aktivasi disimpan sebagai uint8, bobot sebagai int8 dalam rentang −127 sampai 127, dan bias sebagai int32. Satu keluaran konvolusi adalah")
    d.equation(mt("acc") + delim(mi("o,y,x"), "[", "]") + mi("=") + nary(mi("c,i,j"), "", sub(mi("w"), mi("o,c,i,j")) + mi("·") +
               sub(mi("a"), mi("c,y+i−1,x+j−1"))))
    d.txt("dengan nilai di luar batas gambar bernilai nol. Hasilnya ditambah bias lalu dikembalikan ke uint8 dengan satu perkalian bilangan "
           "bulat M 16 bit dan satu geser kanan n, sedangkan pemotongan ke 0..255 sekaligus menjadi ReLU:", indent=False)
    d.equation(mi("q=") + delim(delim(mt("acc") + mi("+b")) + mi("·M+") + sup(mi("2"), mi("n−1"))) + mi("≫n"))
    d.equation(mi("y=") + mt("min") + delim(mt("max") + delim(mi("q,0")) + mi(",255")))
    d.txt("Layer terakhir tidak dikuantisasi ulang: kelas adalah indeks terkecil dengan logit int32 terbesar. Model dilatih dalam floating point, "
           f"lalu dikuantisasi setelah training dengan skala dari persentil 99,99 aktivasi pada {nf(qs['calib_images'])} gambar kalibrasi; "
           "BatchNorm dilebur ke bobot sebelum kuantisasi. Bobot dimuat lewat SPI, sehingga model untuk kelas lain dapat dipakai tanpa sintesis "
           "ulang selama struktur konvolusinya sama.", indent=False)
    d.subsection("Engine Output-Stationary")
    cyc, ideal = cycles(ctx["reg"]["engine_s_k8_c1_n200"])
    d.txt("Engine memakai dataflow output-stationary dengan K = 8 lane. Lane k menghitung kanal keluaran o = g·K + (k − 1) untuk grup g. Selama "
           "satu unit hitung, yaitu satu posisi keluaran untuk satu grup, setiap lane mengakumulasi T = C_{in}·9 suku untuk konvolusi atau "
           "T = N_{in} untuk fully connected. Setiap siklus, semua lane menerima satu operand set berisi satu aktivasi yang disiarkan ke semua "
           "lane, K bobot, dan tiga bobot checksum. Jumlah siklus ideal satu gambar adalah", indent=False)
    d.equation(sub(mi("N"), mt("ideal")) + mi("=") + nary(mt("conv"), "", sub(mi("H"), mt("out")) + sub(mi("W"), mt("out")) + mi("G") +
               sub(mi("C"), mt("in")) + mi("·9")) + mi("+") + nary(mt("fc"), "", mi("G") + sub(mi("N"), mt("in"))))
    d.txt(f"yang bernilai {nf(ideal)} siklus untuk model pada Tabel I. Pembangkit operand menghasilkan R = 2 operand set per siklus clock aman, "
           "sehingga lane dapat diberi operand hingga 2 × 125 = 250 MHz.", indent=False)
    d.subsection("Lane Data dan Lane Checksum")
    d.txt("Untuk setiap siklus t, pembangkit di domain aman menghitung tiga bobot checksum dari K bobot yang sama yang dikirim ke lane data:", indent=False)
    k1 = mi("k=1")
    d.equation(sub(mi("wc"), mi("1")) + mi("=") + nary(k1, mi("K"), sub(mi("w"), mi("k"))) + gap() + sub(mi("wc"), mi("2")) + mi("=") +
               nary(k1, mi("K"), mi("k") + sub(mi("w"), mi("k"))))
    d.equation(sub(mi("wc"), mi("3")) + mi("=") + nary(k1, mi("K"), sup(mi("k"), mi("2")) + sub(mi("w"), mi("k"))))
    d.txt("Lane checksum c mengakumulasi S_{c} = Σ_{t} wc_{c}(t)·a(t) dengan aktivasi a(t) yang sama dengan lane data (Gbr. 3). Karena "
           "perkalian dan penjumlahan bilangan bulat bersifat distributif, akumulator lane data Y_{k} memenuhi", indent=False)
    d.equation(sub(mi("S"), mi("1")) + mi("=") + nary(k1, mi("K"), sub(mi("Y"), mi("k"))) + gap() + sub(mi("S"), mi("2")) + mi("=") +
               nary(k1, mi("K"), mi("k") + sub(mi("Y"), mi("k"))))
    d.equation(sub(mi("S"), mi("3")) + mi("=") + nary(k1, mi("K"), sup(mi("k"), mi("2")) + sub(mi("Y"), mi("k"))))
    d.txt("jika tidak ada error. Identitas ini berlaku eksak karena seluruh aritmetika berupa bilangan bulat dan akumulator lane checksum "
           "selebar 48 bit tidak pernah overflow. Bobot checksum dihitung ulang setiap siklus, sehingga tidak memerlukan memori tambahan, dan bobot "
           "lane data yang rusak setelah keluar dari domain aman tetap terdeteksi.", indent=False)
    d.cols(1)
    d.figure(fig("fig_dataflow"), "Aliran data lane. Satu aktivasi disiarkan ke K lane data dan lane checksum; komparator di domain aman "
             "membandingkan jumlah hasil lane data dengan akumulator checksum.", 16.0)
    d.cols(2)
    d.subsection("Pembangkit Bobot Checksum")
    d.txt(f"Perkalian dengan konstanta k dan k² diuraikan menjadi salinan w_{{k}} yang digeser, satu salinan untuk setiap bit 1 dari konstanta "
           f"{c('parhi')}. Untuk K = 8, wc2 tersusun dari 13 salinan dan wc3 dari 14 salinan. Semua salinan satu keluaran dijumlahkan dalam satu "
           "pohon penjumlah datar dengan 16 daun dan empat level, dengan register di level tengah, sehingga setiap tahap pipeline hanya memuat dua "
           "penjumlah. Latensinya dua siklus.", indent=False)
    d.subsection("Dua Varian Lane")
    d.txt("Lane tersedia dalam dua implementasi dengan fungsi yang identik. Varian LUT membangun pengali 8×8 dari logika fabric, sehingga "
           "pengali menjadi jalur kritis domain cepat dan perilaku error timing dapat dipelajari. Varian DSP memetakan pengali ke blok DSP48E1 "
           "dan menjadi varian dengan throughput tertinggi. Kedua varian memakai golden model, pembangkit operand, dan pemeriksa yang sama.", indent=False)
    d.subsection("Perpindahan Clock")
    d.txt("Pemilih BUFGCTRL hanya berubah ketika domain cepat idle, yaitu di antara layer atau sebelum dan sesudah hitung ulang. Sebelum MMCM "
           "kedua direkonfigurasi, lane dipindah ke clock aman; rekonfigurasi dilakukan lewat antarmuka AXI4-Lite Clocking Wizard di antara "
           "gambar, lalu turbo baru dipakai lagi setelah sinyal LOCKED aktif. Semua penyeberangan sinyal tunggal melewati synchronizer dua "
           "flip-flop, dan register reset domain aman direplikasi untuk membatasi fan-out.", indent=False)


def sec_checksum(d: Paper, ctx) -> None:
    d.section("Deteksi, Lokalisasi, dan Koreksi Error")
    d.subsection("Selisih Checksum")
    d.txt("Setelah satu unit selesai, komparator menghitung d_{1} = ΣY_{k} − S_{1}, d_{2} = Σk·Y_{k} − S_{2}, dan d_{3} = Σk²·Y_{k} − S_{3}. "
           "Jika lane j salah sebesar e sehingga terbaca Y_{j} + e, maka", indent=False)
    d.equation(sub(mi("d"), mi("1")) + mi("=e") + gap() + sub(mi("d"), mi("2")) + mi("=j·e") + gap() + sub(mi("d"), mi("3")) + mi("=") +
               sup(mi("j"), mi("2")) + mi("·e"))
    d.txt("Lane yang salah adalah j = d_{2}/d_{1}, dan koreksinya Y_{j} ← Y_{j} − d_{1}. Hardware tidak memakai pembagi: komparator mencoba "
           "j = 1, …, K dan memeriksa d_{2} = j·d_{1} serta d_{3} = j²·d_{1}. Bobot lane dimulai dari 1 agar error pada lane C1 tidak tampak "
           "seperti error pada lane data pertama.", indent=False)
    d.subsection("Keputusan Komparator")
    d.txt("Gbr. 4 menunjukkan keputusan untuk satu unit. Register mode memilih mode 0 tanpa pemeriksaan, mode 1 yang hanya memakai C1 dan "
           f"menghitung ulang setiap selisih seperti pada {c('marty')}, atau mode 2 yang mengoreksi. Ketiga mode berada dalam bitstream yang sama. "
           "Error pada lane checksum menghasilkan pola d_{1} ≠ 0 dengan d_{2} = 0, atau sebaliknya; pola ini dihitung ulang karena tanpa C3 pola "
           "yang sama dapat berasal dari dua error yang saling meniadakan.", indent=False)
    d.cols(1)
    d.figure(fig("fig_decision"), "Keputusan komparator untuk satu unit hitung. Mode 0 dan 1 adalah pembanding; mode 2 adalah koreksi SENTINEL.", 14.5)
    d.cols(2)
    d.subsection("Jaminan untuk Error Dua Lane")
    d.txt("Dua lane yang salah bersamaan dapat kebetulan memenuhi d_{2} = j·d_{1} untuk j yang keliru. Misalkan lane a dan b dengan a ≠ b salah "
           "sebesar e_{a} dan e_{b}, dan p = e_{a}/(e_{a} + e_{b}). Koreksi palsu memerlukan j = ap + b(1 − p) dan sekaligus j² = a²p + b²(1 − p). "
           "Selisih kedua syarat adalah", indent=False)
    d.equation(sup(mi("a"), mi("2")) + mi("p+") + sup(mi("b"), mi("2")) + delim(mi("1−p")) + mi("−") +
               sup(delim(mi("ap+b") + delim(mi("1−p"))), mi("2")) + mi("=p") + delim(mi("1−p")) + sup(delim(mi("a−b")), mi("2")))
    d.txt("yang hanya bernilai nol jika salah satu error bernilai nol. Dengan C3, error dua lane karenanya selalu berakhir pada hitung ulang dan "
           "tidak pernah salah dikoreksi. Jika e_{a} + e_{b} = 0, maka d_{1} = 0 dan koreksi tidak dicoba.", indent=False)
    d.subsection("Contoh Numerik")
    ce = ctx["facts"]["checksum_example"]
    s1, du = ce["single"], ce["dual"]
    d.txt(f"Tabel II memakai akumulator nyata layer {ce['layer']} dari golden model, dengan S_{{1}} = {sn(ce['s1'])} dan S_{{2}} = {sn(ce['s2'])}. "
           f"Membalik bit {s1['bit']} di lane {s1['lane']} menghasilkan d_{{1}} = {sn(s1['d1'])} dan d_{{2}} = {sn(s1['d2'])} = {s1['j']}·d_{{1}}, "
           f"sehingga lane {s1['j']} ditunjuk dan dikembalikan tepat ke {sn(s1['corrected'][s1['lane'] - 1])}. Membalik bit {du['bit']} di lane "
           f"{du['lanes'][0]} dan {du['lanes'][1]} menghasilkan d_{{1}} = {sn(du['d1'])} dan d_{{2}} = {sn(du['d2'])} = {du['j_c3_off']}·d_{{1}}. Tanpa C3, "
           f"lane {du['j_c3_off']} yang benar akan dirusak. Dengan C3, d_{{3}} = {sn(du['d3'])} berbeda dari {du['j_c3_off']}²·d_{{1}} = "
           f"{sn(du['j_c3_off'] ** 2 * du['d1'])}, sehingga unit dihitung ulang.", indent=False)
    rows = [[str(k + 1), sn(ce["y"][k]), sn(s1["observed"][k]), sn(du["observed"][k])] for k in range(8)]
    d.table(["k", "Y_{k}", f"lane {s1['lane']} salah", f"lane {du['lanes'][0]}, {du['lanes'][1]} salah"], rows, [500, 1300, 1450, 1450],
            "Akumulator satu unit conv2", align=["center", "right", "right", "right"])
    d.subsection("Hitung Ulang di Clock Aman")
    d.txt("Unit yang tidak dapat dipastikan dicatat dalam log berkapasitas 256 entri per layer. Setelah layer selesai, lane dipindah ke clock "
           "aman, semua unit dalam log dihitung ulang, lalu hasilnya ditulis ulang setelah requantization dan pooling. Komparator tetap aktif; jika "
           "hasil di clock aman pun tidak bersih, flag FATAL dinyalakan. Jika log penuh, seluruh layer diulang di clock aman. Setiap jalur keluar "
           "komparator dengan demikian berakhir pada hasil yang benar atau pada flag yang terbaca host.", indent=False)


def sec_governor(d: Paper, ctx) -> None:
    d.section("Governor Frekuensi per Layer")
    d.txt("Governor menyimpan level frekuensi turbo L, yaitu indeks tabel frekuensi MMCM kedua, serta izin turbo dan hitungan cooldown untuk "
           "setiap layer. Di akhir setiap gambar, governor menjalankan aturan berikut:", indent=False)
    d.code([
        "untuk setiap layer l:",
        "  jika fails[l] > 0:",
        "    turbo_en[l] = 0; cool[l] = COOLDOWN",
        "  jika tidak dan cool[l] > 0:",
        "    cool[l] -= 1",
        "    jika cool[l] = 0: turbo_en[l] = 1",
        "jika ada gagal atau koreksi > CORR_HI:",
        "  L = max(L - 1, L_MIN); streak = 0",
        "jika tidak:",
        "  streak += 1",
        "  jika streak >= N_UP:",
        "    L = min(L + 1, L_MAX); streak = 0",
    ])
    d.txt("Level naik setelah N_UP gambar bersih dan turun segera ketika ada unit gagal atau jumlah koreksi melewati ambang. Layer yang gagal "
           "beristirahat dari turbo selama COOLDOWN gambar, sehingga layer yang lebih tahan dapat tetap berjalan cepat. Gbr. 5 memperlihatkan "
           "trajektori governor pada urutan kejadian sintetis. Mode manual memungkinkan host menetapkan level dan izin turbo untuk sapuan frekuensi.")
    d.cols(1)
    d.figure(fig("fig_governor"), "Trajektori governor pada urutan kejadian sintetis: level turbo L (atas) dan izin turbo per layer (bawah).", 15.0)
    d.cols(2)


def sec_infra(d: Paper, ctx) -> None:
    d.section("Infrastruktur Pengujian")
    d.txt("Logika fault injection disintesis bersama desain. Dua slot injeksi memilih layer, unit, lane, dan mask; register penampung lane "
           "terpilih di-XOR dengan mask saat unitnya cocok. Error buatan ini melewati FIFO, serializer, dan komparator yang sama dengan error "
           "timing sungguhan. Host mengakses register, memori bobot, dan gambar melalui SPI dengan peta register yang dibangkitkan dari satu "
           "sumber untuk Verilog dan Python, dan setiap layer memiliki penghitung unit bersih, terkoreksi, error lane checksum, dan hitung ulang. "
           "Suhu chip dibaca dari XADC.", indent=False)
    d.txt("Infrastruktur ini mendukung delapan eksperimen pada Tabel III. Tiga di antaranya menguji hipotesis desain: pada frekuensi error "
           "terendah sebagian besar error hanya mengenai satu lane (E1), error timing bersifat deterministik (E2), dan layer yang lebih dalam mulai "
           "error pada frekuensi lebih tinggi (E3).")
    d.table(["ID", "Pengukuran", "Kriteria"], [
        ["E1", "atlas error per frekuensi, layer, lane, dan bit", "≥ 90% error di tiga frekuensi terendah hanya satu lane"],
        ["E2", "pengulangan pola error", "≥ 95% pengulangan identik"],
        ["E3", "frekuensi awal error per layer", "layer dalam ≥ 10% di atas layer 1"],
        ["E4", "throughput dan akurasi tiga mode", "mode 2 ≥ 1,2× mode 1 dan ≥ 1,4× baseline"],
        ["E5", "cakupan fault injection", "100% error satu lane terkoreksi"],
        ["E6", "governor terhadap suhu", "tanpa hasil salah"],
        ["E7", "bit-exact pada set validasi", "100% kelas dan logit identik"],
        ["E8", "resource, daya, keuntungan bersih", "keuntungan bersih positif"]],
        [450, 2150, 2100], "Eksperimen yang didukung", align=["left", "left", "left"])


def sec_results(d: Paper, ctx) -> None:
    reg, lut, dsp = ctx["reg"], ctx["lut"], ctx["dsp"]
    d.section("Hasil")
    d.subsection("Akurasi Model")
    d.txt(f"Model dilatih pada CIFAR-10. Tabel IV memberi akurasi pada 10.000 gambar uji. Kuantisasi ke INT8 menurunkan akurasi model utama "
           f"sebesar {nf(ctx['qr']['s']['drop_points'], 2)} poin persentase.", indent=False)
    d.table(["Model", "Float", "INT8", "Selisih"], [
        [m, pct(ctx["qr"][m]["test_acc_float"]), pct(ctx["qr"][m]["test_acc_integer"]), nf(ctx["qr"][m]["drop_points"], 2)] for m in ("s", "xs")],
        [1100, 1200, 1200, 1200], "Akurasi pada set uji CIFAR-10", align=["left", "right", "right", "right"])
    d.subsection("Verifikasi Bit-Exact")
    cyc, ideal = cycles(reg["engine_s_k8_c1_n200"])
    cyc_d, _ = cycles(reg["engine_s_k8_c1_dsp_n200"])
    d.txt("Golden model integer di Python menjadi acuan. Verifikasi berjenjang dari test unit, testbench per modul, engine satu clock, hingga "
           "sistem lengkap dengan SPI dan dua domain clock pada rasio clock 1,0 sampai 2,0, ditambah governor yang dibandingkan dengan model "
           "Python. Simulator yang dipakai adalah Icarus Verilog dan Vivado xsim, dan Verilator dipakai untuk lint. Tabel V merangkum regresi "
           f"utama. Engine membutuhkan rata-rata {nf(cyc)} siklus per gambar untuk varian LUT dan {nf(cyc_d)} untuk varian DSP, "
           f"{pct(cyc / ideal - 1)} di atas jumlah ideal, sehingga lane terisi {pct(ctx['arch']['total_macs'] / (8 * cyc))} dari waktunya.", indent=False)
    pick = [("engine_s_k8_c1_n200", "engine, lane LUT, 200 gambar"), ("engine_s_k8_c1_dsp_n200", "engine, lane DSP, 200 gambar"),
            ("system_s_k8_c1", "sistem dua clock, lane LUT"), ("system_s_k8_c1_dsp", "sistem dua clock, lane DSP"),
            ("checker_k8_c1", "komparator"), ("governor", "governor, 60 skenario"), ("wc_gen_k8_c1_1m", "bobot checksum, 10⁶ vektor")]
    rows = []
    for name, desc in pick:
        e = reg.get(name)
        if e:
            m = re.match(r"PASS (\d+)/(\d+)", e["summary"])
            rows.append([desc, f"{nf(int(m.group(1)))}/{nf(int(m.group(2)))}"])
    d.table(["Pengujian", "Lulus"], rows, [3100, 1600], "Regresi RTL terhadap golden model", align=["left", "right"])
    d.subsection("Kampanye Fault Injection")
    single = camp_row(ctx, 8, 1, "single")
    dual0 = camp_row(ctx, 8, 0, "dual")
    dual1 = camp_row(ctx, 8, 1, "dual")
    d.txt(f"Model komparator diberi akumulator nyata dari golden model pada {ctx['camp']['images']} gambar uji dan disuntik error XOR (Gbr. 6). "
           f"Semua {nf(single['n'])} error satu lane terkoreksi. Tanpa C3, {nf(dual0['miscorrected'])} dari {nf(dual0['n'])} error dua lane salah "
           f"dikoreksi ({pct(dual0['miscorrected'] / dual0['n'], 1)}); dengan C3 tidak ada salah koreksi dan semua {nf(dual1['recompute'])} kasus "
           "dihitung ulang, sesuai jaminan pada Bagian IV-C. Semua error lane checksum dihitung ulang.", indent=False)
    d.cols(1)
    d.figure(fig("fig_campaign"), "Hasil kampanye fault injection pada model komparator untuk K = 8 dan K = 16.", 15.5)
    d.cols(2)
    d.subsection("Implementasi pada XC7S25")
    ul, ud = lut["utilization_post_route"], dsp["utilization_post_route"]
    cl, cd = clocks(lut), clocks(dsp)
    d.txt("Desain lengkap, termasuk dua MMCM, SPI, memori, dan seluruh logika pemeriksa, diimplementasikan pada XC7S25CSGA225-1 dengan Vivado "
           "2025.2. Tabel VI dan Gbr. 7 memberi hasil sesudah place and route menurut analisis timing statis. Kedua varian lolos timing di clock "
           f"aman 125 MHz, dengan Fmax clk_safe {nf(cl['clk_safe_raw']['fmax_mhz'], 1)} MHz dan {nf(cd['clk_safe_raw']['fmax_mhz'], 1)} MHz.", indent=False)
    rows = [["Slice LUT", f"{nf(ul['lut']['used'])}", f"{nf(ud['lut']['used'])}"],
            ["Flip-flop", nf(ul["ff"]["used"]), nf(ud["ff"]["used"])],
            ["Block RAM", nf(ul["bram_tile"]["used"]), nf(ud["bram_tile"]["used"])],
            ["DSP48E1", nf(ul["dsp"]["used"]), nf(ud["dsp"]["used"])],
            ["Fmax clk_safe (MHz)", nf(cl["clk_safe_raw"]["fmax_mhz"], 1), nf(cd["clk_safe_raw"]["fmax_mhz"], 1)],
            ["Fmax lane (MHz)", nf(cl["clk_fast_turbo"]["fmax_mhz"], 1), nf(cd["clk_fast_turbo"]["fmax_mhz"], 1)],
            ["Daya estimasi (W)", nf(lut["power"]["total_w"], 3), nf(dsp["power"]["total_w"], 3)]]
    d.table(["Butir", "Lane LUT", "Lane DSP"], rows, [2200, 1250, 1250], "Hasil implementasi pada XC7S25CSGA225-1", align=["left", "right", "right"])
    d.txt(f"Lane DSP lolos STA hingga {nf(cd['clk_fast_turbo']['fmax_mhz'], 1)} MHz, di atas laju suplai operand 250 MHz, sehingga throughput "
           "varian DSP ditentukan oleh suplai operand. Lane LUT mencapai "
           f"{nf(cl['clk_fast_turbo']['fmax_mhz'], 1)} MHz menurut STA, sehingga pada varian ini lane MAC adalah jalur kritis dan rentang "
           f"hingga 250 MHz menjadi ruang kerja overclocking yang dijaga checksum.")
    d.cols(1)
    d.figure(fig("fig_variants"), "Resource kedua varian (kiri) dan Fmax statis clk_safe serta lane (kanan), dibandingkan dengan clock aman "
             "125 MHz dan batas suplai operand 250 MHz.", 15.5)
    d.cols(2)
    d.subsection("Latensi")
    t_c = cyc * 8e-6
    d.txt(f"Pada clock aman 125 MHz, komputasi satu gambar memakan {nf(t_c, 3)} ms, atau {nf(1 / t_c * 1e3, 0)} gambar per detik untuk "
           f"komputasi saja. Dengan definisi pada {c('review')}, throughput komputasi pada frekuensi itu adalah "
           f"{nf(2 * ctx['arch']['total_macs'] / (t_c * 1e-3) / 1e9, 2)} GOP/s. Pengiriman gambar 3.072 byte melalui SPI berlangsung di luar engine; "
           "pada SPI 10 MHz waktunya 2,458 ms, sehingga waktu komputasi FPGA dan waktu ujung ke ujung dilaporkan terpisah.", indent=False)


def sec_conclusion(d: Paper, ctx) -> None:
    lut, dsp = ctx["lut"], ctx["dsp"]
    d.section("Kesimpulan")
    d.txt("SENTINEL memisahkan lane MAC ke domain clock yang dapat dipercepat dan menjaganya dengan tiga checksum tertimbang yang dihitung dari "
           "bobot yang sama. Error satu lane dideteksi, ditunjuk, dan dikoreksi di tempat; error dua lane dijamin berakhir pada hitung ulang; dan "
           "governor di dalam FPGA memilih frekuensi per layer. Seluruh desain telah diimplementasikan dalam RTL yang identik bit demi bit dengan "
           "golden model dan disintesis lengkap pada XC7S25CSGA225-1 dalam dua varian, dengan "
           f"{nf(lut['utilization_post_route']['lut']['used'])} dan {nf(dsp['utilization_post_route']['lut']['used'])} LUT. Infrastruktur fault "
           "injection, penghitung per layer, dan mode manual governor menyediakan semua yang dibutuhkan untuk mengukur perilaku error timing "
           "Spartan-7 pada board ZERO7.", indent=False)


def references(d: Paper) -> None:
    d.add(para([run("Referensi")], style="Heading1"))
    for k, (_, text) in enumerate(REFS, 1):
        d.reference(k, text)


def build(ctx) -> Paper:
    d = Paper()
    title_block(d, ctx)
    sec_intro(d, ctx)
    sec_related(d, ctx)
    sec_arch(d, ctx)
    sec_checksum(d, ctx)
    sec_governor(d, ctx)
    sec_infra(d, ctx)
    sec_results(d, ctx)
    sec_conclusion(d, ctx)
    references(d)
    return d


def main() -> int:
    ctx = load_context()
    make_figures(ctx)
    d = build(ctx)
    d.save(OUT_DOCX, "SENTINEL: Akselerator CNN dengan Checksum Tertimbang untuk Overclocking Aman pada FPGA Spartan-7")
    print(f"wrote {OUT_DOCX.relative_to(ROOT)}")
    if "--no-pdf" not in sys.argv:
        ps = ROOT / "tools" / "study_guide" / "finalize_word.ps1"
        res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", str(ps), "-Docx", str(OUT_DOCX)],
                             capture_output=True, text=True, cwd=ROOT)
        print(res.stdout.strip() or res.stderr.strip())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
