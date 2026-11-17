"""
Generate Master IPS V2 Final Executable Constitution (.docx) directly from
verified 10,000-path V1 (simulation_results.json) & V2 (simulation_v2_results.json) data.
"""
from __future__ import annotations
import json
import os
import shutil
from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT, WD_ALIGN_VERTICAL
from docx.oxml import OxmlElement, parse_xml
from docx.oxml.ns import nsdecls, qn

NAVY_HEX = "1B365D"
BLUE_HEX = "2C5282"
SLATE_HEX = "4A5568"
CALLOUT_HEX = "F0F4F8"
WARN_BG_HEX = "FFFBEB"
WARN_BDR_HEX = "B7791F"
ALT_ROW_HEX = "F8FAFC"
BORDER_HEX = "CBD5E0"

NAVY = RGBColor(0x1B, 0x36, 0x5D)
BLUE = RGBColor(0x2C, 0x52, 0x82)
DARK = RGBColor(0x1A, 0x20, 0x2C)
BODY = RGBColor(0x2D, 0x37, 0x48)
MUTED = RGBColor(0x71, 0x80, 0x96)
WHITE = RGBColor(0xFF, 0xFF, 0xFF)
WARN_CLR = RGBColor(0x97, 0x5A, 0x16)
GOOD_CLR = RGBColor(0x27, 0x67, 0x49)
LIGHT_SUB = RGBColor(0xE2, 0xE8, 0xF0)

FONT_ZH = "Microsoft JhengHei"


def set_run_font(run, size_pt: float, bold: bool = False, color: RGBColor = BODY, font_name: str = FONT_ZH):
    run.font.name = font_name
    run.font.size = Pt(size_pt)
    run.bold = bold
    if color is not None:
        run.font.color.rgb = color
    rPr = run._r.get_or_add_rPr()
    rFonts = rPr.find(qn("w:rFonts"))
    if rFonts is None:
        rFonts = OxmlElement("w:rFonts")
        rPr.insert(0, rFonts)
    rFonts.set(qn("w:ascii"), font_name)
    rFonts.set(qn("w:hAnsi"), font_name)
    rFonts.set(qn("w:eastAsia"), font_name)
    rFonts.set(qn("w:cs"), font_name)


def set_cell_shading(cell, fill_hex: str):
    tcPr = cell._tc.get_or_add_tcPr()
    for el in tcPr.findall(qn("w:shd")):
        tcPr.remove(el)
    shd = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{fill_hex}"/>')
    tcPr.append(shd)


def set_cell_margins(cell, top=90, bottom=90, left=110, right=110):
    tcPr = cell._tc.get_or_add_tcPr()
    for el in tcPr.findall(qn("w:tcMar")):
        tcPr.remove(el)
    tcMar = OxmlElement("w:tcMar")
    for k, val in [("top", top), ("bottom", bottom), ("left", left), ("right", right)]:
        node = OxmlElement(f"w:{k}")
        node.set(qn("w:w"), str(val))
        node.set(qn("w:type"), "dxa")
        tcMar.append(node)
    tcPr.append(tcMar)


def set_table_clean_borders(table, border_hex: str = BORDER_HEX):
    tblPr = table._tbl.tblPr
    for el in tblPr.findall(qn("w:tblBorders")):
        tblPr.remove(el)
    borders = parse_xml(
        f'<w:tblBorders {nsdecls("w")}>'
        f'  <w:top w:val="single" w:sz="6" w:space="0" w:color="{NAVY_HEX}"/>'
        f'  <w:bottom w:val="single" w:sz="6" w:space="0" w:color="{NAVY_HEX}"/>'
        f'  <w:left w:val="none"/>'
        f'  <w:right w:val="none"/>'
        f'  <w:insideH w:val="single" w:sz="4" w:space="0" w:color="{border_hex}"/>'
        f'  <w:insideV w:val="single" w:sz="4" w:space="0" w:color="{border_hex}"/>'
        f'</w:tblBorders>'
    )
    tblPr.append(borders)


def set_callout_borders(cell, left_hex: str = NAVY_HEX, sz: int = 24):
    tcPr = cell._tc.get_or_add_tcPr()
    for el in tcPr.findall(qn("w:tcBorders")):
        tcPr.remove(el)
    borders = parse_xml(
        f'<w:tcBorders {nsdecls("w")}>'
        f'  <w:top w:val="none"/>'
        f'  <w:bottom w:val="none"/>'
        f'  <w:left w:val="single" w:sz="{sz}" w:space="0" w:color="{left_hex}"/>'
        f'  <w:right w:val="none"/>'
        f'</w:tcBorders>'
    )
    tcPr.append(borders)


def set_row_repeat_header(row):
    trPr = row._tr.get_or_add_trPr()
    tblHeader = OxmlElement("w:tblHeader")
    trPr.append(tblHeader)


def set_row_cant_split(row):
    trPr = row._tr.get_or_add_trPr()
    cantSplit = OxmlElement("w:cantSplit")
    trPr.append(cantSplit)


def set_table_widths(table, col_widths_dxa):
    table.autofit = False
    tblGrid = table._tbl.tblGrid
    if tblGrid is not None:
        for gridCol in list(tblGrid):
            tblGrid.remove(gridCol)
        for w in col_widths_dxa:
            gc = OxmlElement("w:gridCol")
            gc.set(qn("w:w"), str(w))
            tblGrid.append(gc)
    for row in table.rows:
        for idx, w in enumerate(col_widths_dxa):
            tcPr = row.cells[idx]._tc.get_or_add_tcPr()
            for el in tcPr.findall(qn("w:tcW")):
                tcPr.remove(el)
            tcW = OxmlElement("w:tcW")
            tcW.set(qn("w:w"), str(w))
            tcW.set(qn("w:type"), "dxa")
            tcPr.append(tcW)


def add_bottom_border(paragraph, color_hex: str = NAVY_HEX, sz: int = 12):
    pPr = paragraph._p.get_or_add_pPr()
    pBdr = parse_xml(
        f'<w:pBdr {nsdecls("w")}>'
        f'  <w:bottom w:val="single" w:sz="{sz}" w:space="4" w:color="{color_hex}"/>'
        f'</w:pBdr>'
    )
    pPr.append(pBdr)


def add_field(paragraph, field_text: str, size_pt: float = 8.5, color: RGBColor = MUTED):
    run = paragraph.add_run()
    set_run_font(run, size_pt, bold=False, color=color)
    fldChar1 = parse_xml(r'<w:fldChar %s w:fldCharType="begin"/>' % nsdecls("w"))
    instrText = parse_xml(r'<w:instrText %s xml:space="preserve"> %s </w:instrText>' % (nsdecls("w"), field_text))
    fldChar2 = parse_xml(r'<w:fldChar %s w:fldCharType="separate"/>' % nsdecls("w"))
    fldChar3 = parse_xml(r'<w:fldChar %s w:fldCharType="end"/>' % nsdecls("w"))
    run._r.append(fldChar1)
    run._r.append(instrText)
    run._r.append(fldChar2)
    run._r.append(fldChar3)


def add_h1(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(14)
    p.paragraph_format.space_after = Pt(6)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, 13.0, bold=True, color=NAVY)
    add_bottom_border(p, NAVY_HEX, 12)
    return p


def add_h2(doc: Document, text: str):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(9)
    p.paragraph_format.space_after = Pt(4)
    p.paragraph_format.keep_with_next = True
    r = p.add_run(text)
    set_run_font(r, 10.8, bold=True, color=BLUE)
    return p


def add_body(doc: Document, text: str, space_after: float = 4.0, bold_prefix: str = ""):
    p = doc.add_paragraph()
    p.paragraph_format.space_before = Pt(0)
    p.paragraph_format.space_after = Pt(space_after)
    p.paragraph_format.line_spacing = 1.22
    if bold_prefix:
        rp = p.add_run(bold_prefix)
        set_run_font(rp, 9.5, bold=True, color=DARK)
    r = p.add_run(text)
    set_run_font(r, 9.5, bold=False, color=BODY)
    return p


def add_bullet(doc: Document, bold_prefix: str, text: str):
    p = doc.add_paragraph(style="List Bullet")
    p.paragraph_format.space_before = Pt(1)
    p.paragraph_format.space_after = Pt(3)
    p.paragraph_format.line_spacing = 1.22
    if bold_prefix:
        rp = p.add_run(bold_prefix)
        set_run_font(rp, 9.5, bold=True, color=DARK)
    r = p.add_run(text)
    set_run_font(r, 9.5, bold=False, color=BODY)
    return p


def add_callout_box(doc: Document, title: str, bullets: list[tuple[str, str]], fill_hex: str = CALLOUT_HEX, left_hex: str = NAVY_HEX, title_color: RGBColor = NAVY):
    tbl = doc.add_table(rows=1, cols=1)
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    cell = tbl.cell(0, 0)
    set_table_widths(tbl, [9936])
    set_cell_shading(cell, fill_hex)
    set_cell_margins(cell, top=120, bottom=120, left=190, right=160)
    set_callout_borders(cell, left_hex=left_hex, sz=24)
    set_row_cant_split(tbl.rows[0])

    p0 = cell.paragraphs[0]
    p0.paragraph_format.space_before = Pt(0)
    p0.paragraph_format.space_after = Pt(4)
    rt = p0.add_run(title)
    set_run_font(rt, 10.5, bold=True, color=title_color)

    for b_bold, b_text in bullets:
        p = cell.add_paragraph()
        p.paragraph_format.space_before = Pt(1)
        p.paragraph_format.space_after = Pt(3)
        p.paragraph_format.line_spacing = 1.20
        p.paragraph_format.left_indent = Inches(0.14)
        p.paragraph_format.first_line_indent = Inches(-0.14)
        rb = p.add_run("•  " + b_bold)
        set_run_font(rb, 9.2, bold=True, color=DARK)
        rt2 = p.add_run(b_text)
        set_run_font(rt2, 9.2, bold=False, color=BODY)

    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(4)


def add_styled_table(doc: Document, headers: list[str], rows_data: list[list[str]], col_widths_dxa: list[int], col_alignments: list[int] | None = None, font_size: float = 8.4):
    tbl = doc.add_table(rows=1 + len(rows_data), cols=len(headers))
    tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    set_table_clean_borders(tbl)

    # Header row
    hdr_row = tbl.rows[0]
    set_row_repeat_header(hdr_row)
    set_row_cant_split(hdr_row)
    for ci, h_text in enumerate(headers):
        c = hdr_row.cells[ci]
        set_cell_shading(c, NAVY_HEX)
        set_cell_margins(c, top=85, bottom=85, left=85, right=85)
        c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
        p = c.paragraphs[0]
        p.paragraph_format.space_before = Pt(0)
        p.paragraph_format.space_after = Pt(0)
        if col_alignments and col_alignments[ci] is not None:
            p.alignment = col_alignments[ci]
        r = p.add_run(h_text)
        set_run_font(r, font_size, bold=True, color=WHITE)

    # Data rows
    for ri, row_vals in enumerate(rows_data):
        row = tbl.rows[ri + 1]
        set_row_cant_split(row)
        bg = ALT_ROW_HEX if ri % 2 == 1 else "FFFFFF"
        for ci, val in enumerate(row_vals):
            c = row.cells[ci]
            set_cell_shading(c, bg)
            set_cell_margins(c, top=70, bottom=70, left=85, right=85)
            c.vertical_alignment = WD_ALIGN_VERTICAL.CENTER
            p = c.paragraphs[0]
            p.paragraph_format.space_before = Pt(0)
            p.paragraph_format.space_after = Pt(0)
            p.paragraph_format.line_spacing = 1.15
            if col_alignments and col_alignments[ci] is not None:
                p.alignment = col_alignments[ci]
            # Support first line bold if separated by newline and flagged or leading 【...】
            is_bold = (ci == 0)
            r = p.add_run(val)
            set_run_font(r, font_size, bold=is_bold, color=DARK if is_bold else BODY)

    set_table_widths(tbl, col_widths_dxa)
    sp = doc.add_paragraph()
    sp.paragraph_format.space_before = Pt(0)
    sp.paragraph_format.space_after = Pt(3)
    return tbl


def main():
    base_dir = "/home/antigravity/Johntsai0320/long-term-investment"
    with open(os.path.join(base_dir, "simulation_results.json"), encoding="utf-8") as f:
        v1_list = {d["name"]: d for d in json.load(f)}
    with open(os.path.join(base_dir, "simulation_v2_results.json"), encoding="utf-8") as f:
        v2_list = {d["name"]: d for d in json.load(f)}

    v1_b = v1_list["B_CMA_Base"]
    v1_e2 = v1_list["E2_Rigid_77_NoGK"]
    v1_c = v1_list["C_Stagflation"]

    v2_b = v2_list["V2_Base_Primary"]
    v2_o = v2_list["V2_Optimistic"]
    v2_s = v2_list["V2_Stagflation"]
    v2_tw = v2_list["V2_TW_Tail_Shock"]
    v2_cr = v2_list["V2_CardRate_VWRA"]
    v2_h3 = v2_list["V2_Hard25y_3_7_10"]
    v2_h35 = v2_list["V2_Hard25y_35_75_12"]

    doc = Document()
    sec = doc.sections[0]
    sec.page_width = Inches(8.5)
    sec.page_height = Inches(11.0)
    sec.left_margin = Inches(0.8)
    sec.right_margin = Inches(0.8)
    sec.top_margin = Inches(0.75)
    sec.bottom_margin = Inches(0.75)
    sec.different_first_page_header_footer = True

    # Running Header & Footer (Pages 2+)
    hp = sec.header.paragraphs[0]
    hp.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    hr = hp.add_run("Master IPS 投資執行憲法（25年加速版｜修正定案版 V2：全額剛性底線 × 愛爾蘭 UCITS ETF）")
    set_run_font(hr, 8.5, color=MUTED)

    fp = sec.footer.paragraphs[0]
    fp.alignment = WD_ALIGN_PARAGRAPH.LEFT
    fr1 = fp.add_run("個人投資政策聲明書（Master IPS V2 定案憲法）｜雙券商執行與抗通膨實證版　　　第 ")
    set_run_font(fr1, 8.5, color=MUTED)
    add_field(fp, "PAGE")
    fr2 = fp.add_run(" 頁 / 共 ")
    set_run_font(fr2, 8.5, color=MUTED)
    add_field(fp, "NUMPAGES")
    fr3 = fp.add_run(" 頁")
    set_run_font(fr3, 8.5, color=MUTED)

    # First page footer
    fp1 = sec.first_page_footer.paragraphs[0]
    fp1.alignment = WD_ALIGN_PARAGRAPH.CENTER
    fr_first = fp1.add_run("依據 10,000 條三體系馬可夫蒙地卡羅路徑校準定版（2026–2027 稅制暨雙券商實務參數）｜第 1 頁")
    set_run_font(fr_first, 8.5, color=MUTED)

    # Set default Normal style font
    norm = doc.styles["Normal"]
    norm.font.name = FONT_ZH
    norm.font.size = Pt(9.5)

    # =========================================================================
    # 0. TITLE BANNER CARD
    # =========================================================================
    title_tbl = doc.add_table(rows=1, cols=1)
    title_tbl.alignment = WD_TABLE_ALIGNMENT.CENTER
    tcell = title_tbl.cell(0, 0)
    set_table_widths(title_tbl, [9936])
    set_cell_shading(tcell, NAVY_HEX)
    set_cell_margins(tcell, top=200, bottom=200, left=220, right=220)
    tp1 = tcell.paragraphs[0]
    tp1.paragraph_format.space_before = Pt(0)
    tp1.paragraph_format.space_after = Pt(4)
    tr1 = tp1.add_run("25年加速版 Master IPS 投資執行憲法（修正定案版 V2）")
    set_run_font(tr1, 17.5, bold=True, color=WHITE)

    tp2 = tcell.add_paragraph()
    tp2.paragraph_format.space_before = Pt(0)
    tp2.paragraph_format.space_after = Pt(0)
    tr2 = tp2.add_run("全額剛性月支底線 × 愛爾蘭 UCITS 雙券商架構｜就緒閘門、稅務分軌切換與零減薪退休引擎")
    set_run_font(tr2, 10.0, bold=False, color=LIGHT_SUB)

    sp0 = doc.add_paragraph()
    sp0.paragraph_format.space_before = Pt(0)
    sp0.paragraph_format.space_after = Pt(5)

    # =========================================================================
    # SUMMARY CALLOUT BOX
    # =========================================================================
    b_r = v2_b["buckets_p50_real"]
    b_n = v2_b["buckets_p50_nom"]
    add_callout_box(
        doc,
        "核心修訂總憲與 10,000 條路徑實證摘要",
        [
            ("全額剛性生活費承諾（Layer 1）：",
             "每年實質領取 77.0 萬元（相當於今日購買力 6.42 萬元/月），100% 連動台灣 CPI 足額調升；永久取消原版（V1）之「負報酬凍漲」、「5.10% 減薪 10%」、「第 11/21 年通膨扣減」與「6% 通膨封頂」，實質購買力削弱機率由 69.3% 降至 0.0%。"),
            ("愛爾蘭 UCITS 雙券商引擎：",
             "海外股債全面自美國 ETF（VT/QQQM/VGIT/VTIP）升級為倫敦 LSE 美元掛牌愛爾蘭 UCITS ETF（VALU、FWRA、CBU7、TIP5、IB01），徹底根除「超過 US $6 萬面臨 40% 美國遺產稅」及 30% 股利稅損（美股稅負減半至 15%、美債及 TIPS 退稅與來源稅 0%），全組加權內扣率壓低至 ~0.11%。"),
            ("購買力校準階梯＋就緒閘門：",
             f"累積期月扣款升級為「實質購買力連動」3.0 → 7.0 → 10.0 萬元/月（25 年累計投入實質 2,295 萬／預估名目 ~3,066 萬），配合退休「就緒閘門」（生活實質資本 ≥ 2,750 萬、含醫療池共 ≥ 2,900 萬，否則最多遞延 +4 年）：{v2_b['on_time_y25_pct']:.1f}% 準時第 25 年退休、平均第 {v2_b['retire_year_mean']:.2f} 年退休。"),
            ("壓倒性風險逆轉實證：",
             f"在完整剛性 77 萬/年購買力承諾下，基準情境 P50 退休生活資產達 {b_r['total_real']:,.1f} 萬元實質（名目 {b_n['total_nom']:,.1f} 萬元），30 年破產率由 V1 實證之 {v1_e2['retirement']['ruin_prob_pct']:.2f}% 大幅壓低至 {v2_b['retirement']['ruin_prob_pct']:.2f}%；55 年實質遺產中位數從 {v1_e2['retirement']['y55_legacy_real']['p50']:,.1f} 萬元倍增至 {v2_b['retirement']['y55_legacy_real']['p50']:,.1f} 萬元；全週期四大紅線違規率 0.00%。"),
        ],
    )

    # =========================================================================
    # SECTION 1: V1 -> V2 RECALIBRATION COMPARISON
    # =========================================================================
    add_h1(doc, "一、 修訂緣由：原版 IPS 五大結構衝突與 V1 → V2 參數校準總表")
    add_body(
        doc,
        "經三體系馬可夫體制轉換與 Student-t 肥尾（df=7）蒙地卡羅一萬條路徑壓力稽核，原版複委託憲法（V1）表面僅 0.08% 破產率，實則依賴 GK 護欄與通膨降階將 69.3% 退休者之實質購買力大砍 ≥20%（停滯性通膨情境大砍 ≥20% 高達 96.6%，第 55 年實質生活費僅剩 7.8 萬/年）。若不允許刪減今日 6.42 萬/月之基本生活底線，V1 基準破產率高達 40.97%，且第 1 年與第 16 年因單標 >40% 導致 100% 路徑違反模組 R 紅線。本修正定案版（V2）以數學優化重構以下關鍵參數：",
    )

    v1_v2_rows = [
        ["退休提領底線（Layer 1）",
         "初始 4.25% × GK 四護欄 + Y11/Y21 減調 CPI；69.3% 路徑實質購買力縮水 ≥20%（原版剛性測試破產 40.97%）。",
         "今日 77.0 萬/年（6.42 萬/月）全額剛性 100% 連動台灣 CPI，永久零減薪、零凍漲（購買力縮水率 0.0%）。"],
        ["繁榮超額紅利（Layer 2）",
         "無明確分層；WR < 3.40% 即連本金一併加薪 10%，與剛性低消混同導致牛熊市支出大起大落。",
         "僅當期剛性提領率 ≤ 1.80%（水桶溢流）時始於次年加發繁榮紅利（目標 2.20%、封頂 +35% = 103.95 萬實質），增加 0.00% 破產風險。"],
        ["累積期月投入軌跡",
         "名目金額鎖死 2.0 → 4.0 → 5.5 萬元/月（累計投入 1,335 萬，因通膨 25 年實質縮水近 40%）。",
         "Year-0 實質購買力 3.0 → 7.0 → 10.0 萬元/月隨台灣 CPI 連動（累計投入實質 2,295 萬；若堅持 25 年零遞延則採 3.5 / 7.5 / 12.0 萬元）。"],
        ["海外核心工具與稅負遺產",
         "美股 ETF (VT/QQQM/VGIT/VTIP)：30% 股利稅、US $6 萬以上曝險 40% 美國遺產稅、國泰僅 QI 退美債息且無美股 DRIP。",
         "倫敦 LSE 美元愛爾蘭 UCITS（VALU / FWRA / CBU7 / TIP5 / IB01）：股息內扣僅 15%、美債/TIPS 0% WHT、0% 美國遺產稅、累積型免股利稅與二代健保。"],
        ["單標紅線與發行商分散",
         "階段一 VT 45%、階段三 QQQM 併入 VT 推升 VT 至 50%+，100% 路徑違規單一標的 ≤ 40%。",
         "全球股票對半切分雙發行商 Vanguard VALU（≤35%）＋ Invesco FWRA（≤30%），刪除 QQQM 重疊曝險，全部情境紅線違規 0.00%。"],
        ["台股質押 vs 連結基金衝突",
         "20% 稅率要求「全數轉連結基金」，卻使緊急 SOP 第三階「0050 股票質押借貸」無券可用。",
         "精準雙軌切分：保留原型 0050 ETF 質押核心（上限 250 萬實質、LTV ≤20% 供 50 萬緊急融資），超額與高稅階全導向 0050 連結基金 A 不配息。"],
        ["退休防禦股債結構與現金",
         "54% 股 / 32% 債（其中 50% 為 11.86 年超長 BBB 債 00725B，矩陣存續 8.16 年）＋ 2.3 年現金。",
         "非現金轉「45% 股 / 55% 防禦債」（債池降 00725B 至 10%、CBU7 45%、TIP5 45%，矩陣存續腰斬至 4.11 年）＋ 3.0 年雙幣現金池（含 IB01）。"],
        ["基準 30 年破產率／P50 資產",
         f"剛性 77 萬實測：破產率 {v1_e2['retirement']['ruin_prob_pct']:.2f}% ｜ Y25 實質 P50 {v1_b['y25_real']['p50']:,.1f} 萬 ｜ Y55 遺產 {v1_e2['retirement']['y55_legacy_real']['p50']:,.1f} 萬。",
         f"剛性 77 萬定案：破產率 {v2_b['retirement']['ruin_prob_pct']:.2f}% ｜ 退休實質 P50 {v2_b['w_at_retire_real']['p50']:,.1f} 萬 ｜ Y55 遺產 {v2_b['retirement']['y55_legacy_real']['p50']:,.1f} 萬。"],
    ]
    add_styled_table(
        doc,
        ["核心治理維度", "原版 V1（國泰美股版）實證狀態", "修正定案版 V2（UCITS × 全額剛性底線）"],
        v1_v2_rows,
        [2050, 3850, 4036],
        [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=8.2,
    )

    # =========================================================================
    # SECTION 2: MODULE R RISK BUDGETING
    # =========================================================================
    add_h1(doc, "二、 模組 R：修訂版四大硬性風險紅線（Risk Budgeting V2）")
    add_body(
        doc,
        "經共變異數矩陣實證，原版 V1 所訂「階段二（85/15）股票風險貢獻 ≤ 85%（實際高達 98.3%）」及「階段三（70/30）≤ 75%（實際達 92.5%）」在數學上無法同時滿足。V2 改以可驗證之真實年化波動度與歐拉（Euler）風險貢獻作為剛性憲法邊界，凡年度 12 月末檢核或新增資金逾越下述任一邊界，強制依資金導流與年度再平衡程序修正：",
    )
    redline_rows = [
        ["1. 台灣市場總曝險上限", "累積期 ≤ 35%（0050）\n退休期 ≤ 20%（0050）",
         "0050 原型 ETF ＋ 0050 連結基金 A",
         "較 V1（50%）實質收緊，徹底隔離台積電單一成分股（~57%）及台海地緣尾端風險（註：00725B 為台幣交易美元公司債，屬美元信用風險且佔總資產 ≤ 5%）。"],
        ["2. 單一標的曝險上限", "硬性 ≤ 40%\n（目標權重設定 ≤ 35%）",
         "任一單檔 ETF 或連結基金（VALU, FWRA, 0050, CBU7, TIP5 等）",
         "階段一設 35% / 35% / 30% 預留 5%+ 安全緩衝；階段二至退休期單標皆 ≤ 35%，於 7 大模擬情境實現 0.00% 違規率。"],
        ["3. 美元計價海外資產下限", "硬性 ≥ 35%\n（實質運作維持 65%–80%）",
         "VALU, FWRA, CBU7, TIP5/IDTP, IB01（愛爾蘭 LSE 美元資產）",
         "當極端避險導致新台幣驟貶或本地系統承壓時，提供無美國遺產稅風險之硬通貨購買力防禦盾牌。"],
        ["4. 組合波動度與風險貢獻", "階段二 ≤ 13.0% 年化波動（80/20）\n階段三 ≤ 10.5% 波動（65/35）\n退休池 ≤ 8.0% 波動且股票 RC ≤ 80%",
         "整體投資組合（股＋債共變異數矩陣）",
         "經 V2 三體系共變異數實證：階段一 15.45% 波動；階段二 12.36%；階段三 10.21%；退休 45/55 池總波動僅 7.29%–7.78%、股票風險貢獻 77.2%（≤80%）。"],
    ]
    add_styled_table(
        doc,
        ["風險管理維度", "V2 硬性約束邊界", "納管資產集合", "數學驗證與治理防禦機制"],
        redline_rows,
        [1900, 1950, 2350, 3736],
        [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=8.2,
    )

    # =========================================================================
    # SECTION 3: INVESTABLE UNIVERSE & DUAL-BROKER EXECUTION SPECS
    # =========================================================================
    add_h1(doc, "三、 投資標的全宇宙暨雙券商實戰下單對照表（2026–2027 最新規格）")
    add_body(
        doc,
        "鑑於國泰證券複委託僅支援美股／港股／日股、未開放倫敦交易所（LSE），本憲法正式確立「雙券商／雙軌專戶」執行規範：台股標的留存國泰（與基金平台）；英國 LSE 美元掛牌之愛爾蘭註冊 UCITS ETF 則配置於「富邦證券英股外幣（美元）交割專戶」（或國際券商 IBKR 備援）。下表為全部核准標的之 ISIN 與防誤買規格：",
    )
    universe_rows = [
        ["台股核心 ETF\n(可質押底倉)", "0050（元大台灣50）\n【限額 ≤ 250萬實質】", "TW0000050004\n（臺交所 台幣）",
         "約 0.13%–0.14%（2025 分割降費後）；國泰定期定額單筆 1 元。",
         "保留最多 250 萬實質作為 LTV ≤ 20% 股票質押緊急融通擔保品；達限額或 12–20% 稅率即改投連結基金。"],
        ["台股免配息核\n(稅務蓄水池)", "元大 0050 連結基金\n【限選 A 類型不配息】", "開放式基金（基富通／鉅亨買基金／元大／國泰，台幣）",
         "經理/保管費率銜接 ETF；無二代健保、無 54C 股利所得稅。",
         "嚴禁買入「TISA 級別」（受限 24 個月連續扣款及 6 個月贖回違約金限制）。單筆 0050 配息近 2 萬或稅階達 12% 末段/20% 即強制切換。"],
        ["全球全市場股 A\n(主軸發行商 1)", "VALU / VWRA（備）\nVanguard FTSE All-Cap / All-World Acc", "IE000VAHT5T0（LSE USD）\n【富邦顯示 VAVALU / IBKR: VALL】",
         "VALU TER 0.07% (~$4.85/股)；VWRA TER 0.14% (~$187/股)；15% 愛爾蘭基金端預扣、0% 美國遺產稅。",
         "VALU 為 2026 年 8 月新掛牌超低費 All-Cap 基金；若盤中買賣價差 > 0.25% 過寬時，暫以老牌 VWRA（IE00BK5BQT80）同比例替代。"],
        ["全球全市場股 B\n(發行商防火牆)", "FWRA（Invesco FTSE All-World Acc）", "IE000716YHJ7\n（LSE USD；替代 IMID）",
         "TER 0.15% (~$9.24/股)；規模 ~$53.7 億美元；0% 美國遺產稅。",
         "專責對沖 Vanguard 單一發行商風險並分攤持股比例，徹底鎖死全週期單一標的 ≤ 40%（階段一設 30% 緩衝）。"],
        ["台股高息公司債\n(台幣美元信用)", "00725B（國泰投資級公司債）", "TW00000725B3\n（櫃買中心 台幣）",
         "TER 0.35%；2026 殖利率 ~6.0%–6.68%；有效存續期 11.86 年。",
         "因超長存續期與衰退信用利差擴大風險，由原版佔債池 50% 大幅下調至 10%（總資產 ≤ 5%）；免二代健保且享 750 萬 AMT 免稅。"],
        ["中天期美國國債\n(危機防禦主彈藥)", "CBU7（iShares $ Treasury 3-7yr Acc）", "IE00B3VWN393\n（LSE USD Acc）",
         "TER 0.07% (~$142/股)；有效存續 4.21 年；0% 預扣稅、免 QI 退稅、0% 美國遺產稅。",
         "取代美股 VGIT 成為退休防禦債池主體（45%）；衰退降息期間價格彈性強，累積/退休皆作為情境 A 賣債買股核心彈藥。"],
        ["短天期抗通膨債\n(對抗滯脹與配息)", "TIP5 / IDTP（備）\niShares $ TIPS 0-5 Dist / All-Mat Acc", "IE00BDQYWQ65\n（LSE 美元代碼 TIP5）",
         "TER 0.10% (~$4.87/股)；有效存續 2.28 年；半年度現金配息屬 750 萬免稅海外所得。",
         "【防誤買警告】英鎊計價為 TP05／ITPS，下單務必確認掛牌幣別為 USD（TIP5 / IDTP）！IBKR 累積期可選荷蘭美元 Acc 版 TI5A.AS（非英鎊 TI5A.L）。"],
        ["超短天期現金庫\n(退休美元備援)", "IB01 / IBTU（配息）\niShares $ Treasury 0-1yr Acc", "IE00BGSF1X88\n（LSE USD Acc）",
         "TER 0.07% (~$122.6/股)；有效存續 0.34 年；2026 殖利率 ~4.23%；0% WHT。",
         "僅於退休啟動當日配置，專司承接「水桶一現金庫（3.0 年）」之 50% 美元部位（18 個月生活備用金），對抗台幣匯率風險。"],
    ]
    add_styled_table(
        doc,
        ["資產角色", "核准標的名稱", "ISIN 與掛牌幣別代碼", "費率 / 單價 / 稅務結構", "執行細節與防誤買紅字警示"],
        universe_rows,
        [1350, 1750, 1750, 1950, 3136],
        [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=7.9,
    )

    add_callout_box(
        doc,
        "雙券商下單與手續費議價實戰 SOP（富邦英股複委託 vs. IBKR 損益兩平）",
        [
            ("富邦英股複委託設定（預設執行路線）：",
             "務必開立「外幣（美元）交割」複委託專戶（富邦不開放同市場每筆切換交割幣別，用美元交割可杜絕雙向換匯價差）。電子下單牌告費率為 0.60%（免收最低手續費）＋ 0.0325% 交割費 ＋ 0.0075% 交易徵費（合計 ~0.64%，無英國 0.5% 印花稅；嚴禁電話人工下單 1.0% / min $70）。簽約前洽營業員專案議價至 0.15%–0.25% 並留存電郵書面確認。"),
            ("每季整股批買節奏（取代碎股自動扣款）：",
             "因富邦英股不支援碎股且未開放自動定期定額，台股仍維持「每月 5 號／15 號自動化定期定額」；英股 UCITS 則將每月預留之美元投資金累積於外幣帳戶，固定於每季末（3/6/9/12 月最後三個營業日內）執行一次「限價（賣一價 + 1–2 ticks）整股批買」。"),
            ("IBKR 海外券商替代路徑評估：",
             "若採 Interactive Brokers 買入 LSE 股分級別（0.05%、最低 ~$1.70、支援碎股與自動定期投入），搭配零/低電匯銀行（星展 $0 / 永豐大戶 NT$130 / LINE Bank NT$150）匯出，單筆達 US $1,600+ 即優於富邦 0.25% 議價成本，惟須自行承擔未來海外帳戶遺產認證與年度匯出操作程序。經 V2 敏感度實證，即便全週期採富邦未議價 0.64% 牌告費率買 VWRA，30 年破產率僅微幅增加 0.11%（1.17% → 1.28%），仍高度穩健。"),
        ],
        fill_hex=WARN_BG_HEX,
        left_hex=WARN_BDR_HEX,
        title_color=WARN_CLR,
    )

    # =========================================================================
    # SECTION 4: MODULE A ACCUMULATION SCHEDULE
    # =========================================================================
    add_h1(doc, "四、 模組 A：25 年累積期三階段 CPI 連動配置與每季批買表")
    add_body(
        doc,
        f"執行鐵律：取消累積期閒置現金水庫（100% 投入市場），並全面啟動「台灣 CPI 購買力同步指數化」——每年元月依主計總處公布之上年度台灣 CPI 漲幅同步微調當年月扣款金額（以下均以今日 Year-0 實質購買力編列，括號為以模擬年均通膨 {v2_b['y25_inflation_cagr']*100:.2f}% 試算之未來名目金額；美元以 1 USD = 32 TWD 估算）。",
    )

    acc_rows = [
        ["階段一\n成長衝刺期\n(100% 股票)",
         "第 1～5 年\n(初始 75 萬；實質總資產 < 350 萬時適用)\n【約 29.0% 路徑提前進入階段二】",
         "30,000 元/月\n（90,000 元/季）\n[今日購買力；Y5 名目約 3.25 萬/月]",
         "• 0050 ETF：10,500 元/月 (35%)\n（國泰定期定額 $1 手續費）",
         "【LSE 每季批買 $1,828/季】\n• VALU：31,500 元/季 ≈ $984 (35%, ~203 股)\n• FWRA：27,000 元/季 ≈ $844 (30%, ~91 股)",
         "100% 股票擴張；雙全球 ETF 預留 ≥5% 單標緩衝。若觸及人力資本紅線（收入波動 CV>0.25、剛性支出比>50% 或扶養比>25%），提前轉為 85/15 納入 CBU7。"],
        ["階段二\n防禦導入期\n(80 股 / 20 債)",
         "第 6～15 年\n（或實質總資產 ≥ 350 萬元次月提前觸發）",
         "70,000 元/月\n（210,000 元/季）\n[Y6 名目約 7.72 萬；Y15 約 9.22 萬]",
         "• 0050／連結 A：19,600 元/月 (28%)\n• 00725B：1,400 元/月（或 4,200/季）(2%)",
         "【LSE 每季批買 $4,594/季】\n• VALU：$2,297/季 (35%, ~474 股)\n• FWRA：$1,116/季 (17%, ~121 股)\n• CBU7：$591/季 (9%, ~4 股)\n• TIP5：$591/季 (9%, ~121 股)",
         "• 稅務分軌：0050 原型達 250 萬實質或個人所得近 12% 末段即導流連結 A 不配息。\n• TIP5 半年配息免 30% WHT，併入次季 LSE 批買。"],
        ["階段三\n成熟收斂期\n(65 股 / 35 債)",
         "第 16～25 年\n（及未達就緒閘門之第 26～29 年遞延緩衝期）",
         "100,000 元/月\n（300,000 元/季）\n[Y16 名目約 13.43 萬；Y25 約 16.02 萬]",
         "• 0050 連結 A：23,000 元/月 (23%)\n• 00725B：3,500 元/月 (3.5%)",
         "【LSE 每季批買 $6,891/季】\n• VALU：$2,813/季 (30%, ~580 股)\n• FWRA：$1,125/季 (12%, ~122 股)\n• CBU7：$1,477/季 (15.75%, ~10 股)\n• TIP5：$1,477/季 (15.75%, ~303 股)",
         "• 第 16 年初再平衡至 65/35，全程維持任意單檔 ETF ≤30%、台股 0050 目標 23%（含 00725B ≤26.5%）。\n• 每年 12 月末偏離 ±6% 或單標 >38.5% 強制校準。"],
    ]
    add_styled_table(
        doc,
        ["累積階段", "時間與觸發條件", "每月總投入\n（CPI 連動）", "台股端每月扣款\n（國泰 / 基金平台）", "英股 UCITS 每季整股批買\n（富邦外幣複委託）", "操作紀律與稅務風控"],
        acc_rows,
        [1180, 1450, 1400, 1750, 2150, 2006],
        [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=7.9,
    )

    add_body(
        doc,
        f"純累積 25 年投入實質本金合計 2,295 萬元（含期初 75 萬；按年均 ~1.98% CPI 換算名目累計投入約 3,066 萬元）。【強制 25 年零遞延替代條款】：若因屆齡或職業規劃無法接受「就緒閘門」最長 +4 年彈性延後（75.9% 準時退休；若維持 3/7/10 硬於第 25 年強制啟動，剛性破產率將升至 {v2_h3['retirement']['ruin_prob_pct']:.2f}%），應自期初即採「嚴格零遞延儲蓄表：3.5 → 7.5 → 12.0 萬元/月 CPI 連動」，實證 100% 第 25 年準時退休下之破產率僅 {v2_h35['retirement']['ruin_prob_pct']:.2f}%、第 25 年 P50 實質資產可達 {v2_h35['y25_real']['p50']:,.1f} 萬元（名目 {v2_h35['y25_nominal']['p50']:,.1f} 萬元）。",
        bold_prefix="投入總額與強制準時選項說明：",
    )

    add_h2(doc, "1. 累積期危機量化決策樹（股票較目標權重低配 ≥ 6% 且進入階段二後啟用）")
    add_bullet(
        doc,
        "情境 A（通縮或衰退型股災 —【授權執行賣債買股】）：",
        "必須同時滿足三條件：(1) 美國核心 CPI < 3.0%、(2) 聯準會停止升息或啟動降息、(3) 過去 6 個月美股美債相關係數 ρ < 0.2。執行一次性賣出 20% 之 CBU7 中期美國國債，於未來 3 個月等分三批買進全球股票（65% VALU ＋ 35% FWRA），台股則透過次月新投入薪資補強，絕不將大量資金跨海匯回台灣換匯損耗。",
    )
    add_bullet(
        doc,
        "情境 B（停滯性通膨／暴力升息雙殺 —【強制鎖債禁售】）：",
        "凡符合任一警訊：美國 CPI ≥ 3.0%、央行處於升息循環、或股債呈現高度正相關（ρ ≥ 0.5）。嚴禁拋售任何 CBU7 或 TIP5，依靠每季 CPI 連動之新現金流入自動逢低攤平股權，確保抗通膨本金完整留存。",
    )

    # =========================================================================
    # SECTION 5: MODULE B RETIREMENT GATE, 4 BUCKETS & RIGID WITHDRAWAL
    # =========================================================================
    add_h1(doc, "五、 模組 B：退休「就緒閘門」× 45/55 四水桶重組 × 全額剛性雙軌提領")
    add_h2(doc, "1. 退休啟動判定「就緒閘門」（Readiness Gate — 破產率壓低至 1.17% 之關鍵護城河）")
    add_bullet(
        doc,
        "閘門達標標準：",
        "自第 25 年末起逐年檢核：唯有當「年末總實質資產（依台灣累計 CPI 折現至 Year-0 購買力）－ 150 萬實質獨立醫療池 ≥ 2,750 萬元實質」（即總資產 ≥ 2,900 萬元實質；依 1.98% 基準通膨第 25 年約當名目 ~4,740 萬元）時，方正式啟動退休並執行四水桶重組。",
    )
    add_bullet(
        doc,
        "遞延緩衝機制（最長 +4 年封頂）：",
        f"若第 25 年適逢股災導致實質生活資本暫時低於 2,750 萬，自動順延 1 年並繼續執行階段三「10 萬/月實質」定額投債投資，直至任一年末達標或至遲第 29 年（+4 年）無論市況全數進入退休期。10,000 條路徑實證：{v2_b['on_time_y25_pct']:.1f}% 路徑準時第 25 年達標，P90 遞延者於第 {v2_b['retire_year_p90']:.0f} 年達標，全體平均啟動年為第 {v2_b['retire_year_mean']:.2f} 年，成功消除「熊市底部硬著陸並剛性提領」之 70% 序列風險。",
    )

    add_h2(doc, "2. 退休啟動日「四水桶」資產重組配置表（P50 基準情境實證數值）")
    add_body(
        doc,
        f"於正式退休啟動日，資產以基準中位數 P50 總額 {b_r['total_real']:,.1f} 萬實質（名目 {b_n['total_nom']:,.1f} 萬元；CPI 折現倍率 {b_n['cpi_factor_at_ret']:.2f}×；首年剛性提領率中位數僅 {v2_b['retirement']['rigid_wr_p50_at_ret_pct']:.2f}%、P10 僅 {v2_b['retirement']['rigid_wr_p10_at_ret_pct']:.2f}%）無縫切分並重組為「45% 核心股票 / 55% 防禦債券（扣除 3 年現金與醫療後）」四大獨立水桶：",
    )
    b_rows = [
        ["水桶一：雙幣流動現金庫\n（3.0 年剛性生活費）",
         f"{b_r['b1_cash_real']:,.1f} 萬 ({b_r['b1_cash_real']/b_r['total_real']*100:.1f}%)",
         f"{b_n['b1_cash_nom']:,.1f} 萬",
         "• 50% 台幣高利活存／定存（18 個月開銷）\n• 50% IB01 美元 0–1y 短債 UCITS（18 個月避險備援）",
         "隔絕連續 3 年股災衝擊；混合利率 ~2.0%–2.8%，配合水桶二配息完全承接日常支出，跌破 2.2 年（169.4 萬實質）始於年末補回 3.0 年。"],
        ["水桶二：三軌防禦債券池\n（非現金之 55%）",
         f"{b_r['b2_bonds_real']:,.1f} 萬 ({b_r['b2_bonds_real']/b_r['total_real']*100:.1f}%)",
         f"{b_n['b2_bonds_nom']:,.1f} 萬",
         f"• 45% CBU7 ({b_r['b2_bonds_real']*0.45:,.1f}萬, dur 4.21y)\n• 45% TIP5 ({b_r['b2_bonds_real']*0.45:,.1f}萬, dur 2.28y)\n• 10% 00725B ({b_r['b2_bonds_real']*0.10:,.1f}萬, dur 11.86y)",
         "矩陣有效存續期壓縮至 4.11 年；00725B (5.2%–5.5%) 與 TIP5 (3.2%–3.5%) 年產 ~36.7–39.8 萬實質自然債息自動回填水桶一（涵蓋 ~50% 剛性支出）。"],
        ["水桶三：全球抗通膨股票池\n（非現金之 45%）",
         f"{b_r['b3_equity_real']:,.1f} 萬 ({b_r['b3_equity_real']/b_r['total_real']*100:.1f}%)",
         f"{b_n['b3_equity_nom']:,.1f} 萬",
         f"• 43% VALU ({b_r['b3_equity_real']*0.43:,.1f}萬, Acc)\n• 35% 0050體系 ({b_r['b3_equity_real']*0.35:,.1f}萬：含 250萬 ETF 質押核心 ＋ 連結 A)\n• 22% FWRA ({b_r['b3_equity_real']*0.22:,.1f}萬, Acc)",
         "全數累積免稅滾存抗通膨；台股僅佔總退休資產 14.2%（≤20% 紅線）；非現金部位 45/55 偏離逾 ±6% 時每年末進行對價再平衡。"],
        ["水桶四：獨立醫療專項池\n（與生活盤絕對隔離）",
         f"{b_r['b4_medical_real']:,.1f} 萬 ({b_r['b4_medical_real']/b_r['total_real']*100:.1f}%)",
         f"{b_n['b4_medical_nom']:,.1f} 萬",
         "獨立台幣低波動帳戶（短天期定存 / 貨幣市場 / 實支醫療保險銜接）",
         "嚴禁計入任何年度生活費提領率分母；專供自費標靶、長期照護或重大傷病核銷。"],
    ]
    add_styled_table(
        doc,
        ["功能水桶名稱", "P50 實質金額（佔比）", "P50 預估名目", "底層標的細部配置", "現金流機制與風控鎖定"],
        b_rows,
        [1650, 1450, 1150, 2750, 2936],
        [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.LEFT],
        font_size=7.9,
    )

    add_h2(doc, "3. 雙軌提領憲法（層一全額剛性＋層二繁榮紅利）＆ 新四階緊急流動性 SOP")
    add_bullet(
        doc,
        "層一（絕對剛性基本生活費 — 零削減、零凍漲）：",
        "退休後每月初自動發放今日購買力 6.42 萬元（每年 77.0 萬元 × 累計台灣 CPI 指數）。不論當年股債是否同時負報酬或遭遇高通膨，皆由水桶一全額給付，絕不啟動原版之 -10% 減薪或 CPI 封頂。",
    )
    add_bullet(
        doc,
        "層二（繁榮選擇權紅利 — 零負擔安全閥）：",
        f"每年 12 月末結算「次年層一剛性預算 / 年末生活總資產」。唯當該比率 ≤ 1.80%（即生活資產 ≥ 4,278 萬實質之大幅富裕安全邊際）時，次年額外加發奢侈旅遊／贈與紅利至總提領率 2.20%（單年紅利以 +35% 封頂 ＝ 最高 103.95 萬實質／8.66 萬月支出）。經模擬驗證，此上限紅利增加之破產率為 0.00%，基準情境下生命週期平均有 {v2_b['retirement']['avg_bonus_yrs']:.1f} 年享有加碼紅利，第 55 年末中位數可支配實質消費力自然成長至 103.9 萬元/年。",
    )
    add_bullet(
        doc,
        "水桶一告急「新四階緊急流動性 SOP」（修正原版矛盾）：",
        "第一階【醫療轉帳】：自費醫療先扣水桶四（150 萬實質）；\n"
        "第二階【債息與利息優先承接】：00725B（5.2%–5.5%）、TIP5（3.2%–3.5%）與水桶一利息每年湧入約 41–46 萬實質現金（佔剛性支出 54%–60%），毋須變賣 UCITS 累積標的（正式廢除 V1 「關閉連結基金與美股 DRIP 錯覺條款」）；\n"
        "第三階【獨立 0050 ETF 過橋質押】：50–150 萬臨時急用僅限動用事前分離保留之 250 萬實質「原型 0050 ETF」專戶辦理券商股票質押（LTV 嚴控 ≤ 20%，約可融資 ~50 萬且維持率 ≥ 500%，與連結基金完全實體隔離）；\n"
        "第四階【存續期由短至長贖回順位】：現金庫跌破 2.2 年並耗盡前，嚴格依序賣出 ① IB01（0.34y）→ ② TIP5（2.28y）→ ③ CBU7（4.21y）→ ④ 00725B → ⑤ 最後方按比例減碼 VALU / FWRA / 0050。",
    )
    add_bullet(
        doc,
        "極端停滯性通膨緊急應變條款（Stagflation Tail Protocol）：",
        f"本憲法坦承極限壓測結果：在極罕見長達 24% 時間駐留高通膨（均值 ~3.15%）＋股債長期正相關雙殺（C_Stagflation）下，V2 雖已將剛性破產率自 V1 同條件之 94.65% 劇降至 {v2_s['retirement']['ruin_prob_pct']:.2f}%，但長週期高黏著通膨仍是唯一威脅。條文規範：若觸發「退休前 5 年滾動實質總報酬 < 0% 且 CPI > 3.5%」，除運用就緒閘門遞延外，應啟動「第一性工作橋接機制」（於退休首 3–5 年透過兼職／顧問創造月均 2.0–2.5 萬實質收入，即可填補 >35% 提領壓力，將極端滯脹存活率拉回 90% 以上）。",
    )

    # =========================================================================
    # SECTION 6: MODULE T TAIWAN TAX & ESTATE FIREWALL
    # =========================================================================
    add_h1(doc, "六、 模組 T：台灣稅務分軌（115 年度綜所稅）、AMT 與遺產稅防火牆 SOP")
    add_bullet(
        doc,
        "1. 115 年度（2026–2027 適用）台灣綜所稅與二代健保雙軌切換線：",
        "依財政部 115 年最新綜所稅級距（淨額 0–61 萬 5%、61–138 萬 12%、138–277 萬 20%、277–519 萬 30%）：累計至多 250 萬元實質原型 0050 ETF（作質押底倉）並配合 8.5% / 8 萬元股利抵減額，尚處低稅區間。凡「預估單次 0050 配息金額逼近 NT$20,000 二代健保補充保費（2.11%）起扣點，或進入 12% 級距中後段」，建議提前轉買「元大 0050 連結基金 A 類型不配息」；淨所得觸及 20% 級距（>138 萬）則強制將後續 100% 台股新資金導向連結基金，實現零股利稅、零健保費複利累積。",
    )
    add_bullet(
        doc,
        "2. 美國遺產稅歸零設計（解決 H.R. 33 台美雙重課稅法案懸案）：",
        "台灣投資人直接持有美國掛牌 ETF（如 VT、QQQM、VGIT），凡市值超過 US $60,000 即面臨最高 40% 美國聯邦遺產稅且過戶需申請 IRS Transfer Certificate（歷時 1–2 年）。全面改用「愛爾蘭 ICAV 架構之 LSE UCITS ETF（VALU / FWRA / CBU7 / TIP5 / IB01）」屬於非美國註冊 situs 資產，不論未來規模累積至台幣數千萬乃至上億（第 55 年名目 P50 達 1.63 億），美國聯邦遺產稅均為 0%，且富邦複委託由台灣本國繼承法規直接過戶。",
    )
    add_bullet(
        doc,
        "3. 海外所得最低稅負制（750 萬元 AMT）與海外利息免稅試算：",
        "愛爾蘭累積型 ETF（VALU / FWRA / CBU7 / IB01）每年不派發股息與債息，累積期 25 年間幾乎產生 0 元海外應稅所得；即便進入退休提領期，77 萬/年實質支出換算未來名目海外處分淨利（扣除成本與台幣定存、0050）＋ TIP5/00725B 配息合計僅約台幣 100–180 萬元/年（僅佔每人每年 750 萬元個人 AMT 免稅額度之 13%–24%），全生命週期實質海外所得稅負預估皆為 NT$ 0 元（年底大額再平衡時分跨 12 月末與次年 1 月初錯開實現即可永遠維持 0 稅）。",
    )

    # =========================================================================
    # SECTION 7: FULL MONTE CARLO STRESS TEST MATRIX (10,000 PATHS)
    # =========================================================================
    add_h1(doc, "七、 10,000 條路徑蒙地卡羅壓力測試實證對照總表（V1 vs V2 全情境）")
    add_body(
        doc,
        "所有數值均於相同隨機種子（seed=20261116）、三體系馬可夫體制轉換（正常擴張／通縮衰退／停滯通膨）及 Student-t（df=7）肥尾聯合衝擊下跑足 10,000 條完整生命週期模擬產出（金額單位：台幣萬元）：",
    )

    def fmt_s_row(tag, d, is_v1=False):
        r = d["retirement"]
        red = d["redline_breach_rates"]
        if is_v1:
            ontime = "100% (Y25)"
            wret = f"{d['y25_real']['p50']:,.1f}\n(P10: {d['y25_real']['p10']:,.0f})"
            if d["name"] == "E2_Rigid_77_NoGK":
                spend_cut = "0.0%\n(強撐破產)"
                wr_p50 = 77.0 / max(d['y25_real']['p50'] - 150.0, 1.0) * 100.0
                wr_p10 = 77.0 / max(d['y25_real']['p10'] - 150.0, 1.0) * 100.0
                wr_ret = f"{wr_p50:.2f}%\n(P10: {wr_p10:.2f}%)"
            else:
                spend_cut = f"{r['prob_real_spend_cut_20pct']*100:.1f}%"
                wr_ret = "4.25% 浮動\n(無閘門)"
        else:
            ontime = f"{d['on_time_y25_pct']:.1f}%\n(均 {d['retire_year_mean']:.2f}y)"
            wret = f"{d['w_at_retire_real']['p50']:,.1f}\n(P10: {d['w_at_retire_real']['p10']:,.0f})"
            spend_cut = "0.0%\n(全額剛性)"
            wr_ret = f"{r['rigid_wr_p50_at_ret_pct']:.2f}%\n(P10: {r['rigid_wr_p10_at_ret_pct']:.2f}%)"
        return [
            tag,
            ontime,
            wret,
            f"{d['w_at_retire_nom']['p50'] if not is_v1 else d['y25_nominal']['p50']:,.1f}",
            wr_ret,
            f"{r['ruin_prob_pct']:.2f}%",
            spend_cut,
            f"{r['y55_legacy_real']['p50']:,.1f}\n(P10: {r['y55_legacy_real']['p10']:,.0f})",
            f"{red['any_year_single_gt_40pct']*100:.2f}%",
        ]

    mc_rows = [
        fmt_s_row("【V1 對照】B_CMA 基準（GK 減薪保命）", v1_b, True),
        fmt_s_row("【V1 破功】E2_剛性 77 萬（無 GK 減薪）", v1_e2, True),
        fmt_s_row("【V1 滯脹】C_停滯通膨（GK 狂砍實質剩 8 萬）", v1_c, True),
        fmt_s_row("★【V2 主架構】基準 CMA（3/7/10＋閘門）", v2_b, False),
        fmt_s_row("【V2 樂觀】高股權溢酬（Layer 2 領 23.3 年）", v2_o, False),
        fmt_s_row("【V2 費率極端測試】富邦未議價 0.64%＋VWRA", v2_cr, False),
        fmt_s_row("【V2 台海衝擊】Y12/Y28 台股 -45%＋貶 12%", v2_tw, False),
        fmt_s_row("【V2 滯脹測試】24% 長滯脹（含應急條款說明）", v2_s, False),
        fmt_s_row("【V2 無閘門對照】3/7/10 第 25 年硬退（無遞延）", v2_h3, False),
        fmt_s_row("◆【V2 準時硬退備案】3.5/7.5/12.0 零遞延方案", v2_h35, False),
    ]
    add_styled_table(
        doc,
        ["模擬版本與壓力情境", "Y25 準時率\n(平均啟動年)", "退休實質 P50\n(P10下檔)", "退休名目 P50", "首年剛性\n提領率 P50", "30年破產率\n(Rigid 77)", "生活費大砍\n≥20% 機率", "Y55 實質遺產 P50\n(P10)", "單標 >40%\n違規率"],
        mc_rows,
        [2086, 1020, 1140, 920, 960, 880, 930, 1180, 820],
        [WD_ALIGN_PARAGRAPH.LEFT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.CENTER, WD_ALIGN_PARAGRAPH.RIGHT, WD_ALIGN_PARAGRAPH.RIGHT],
        font_size=7.6,
    )

    # =========================================================================
    # SECTION 8: 12-ITEM EXECUTIVE CHECKLIST
    # =========================================================================
    add_h1(doc, "八、 年度 12 月末 12 項執行長健康檢查儀表板（Executive Checklist V2）")
    add_body(
        doc,
        "每年 12 月最後一個營業日，逐項核對並存檔（累積期檢核第 1–9 項；退休期檢核全數 1–12 項）：",
        space_after=4.0,
    )

    checklist = [
        ("☐  1. 台灣曝險上限檢核：", "0050（原型＋連結基金）佔全資產比重是否符合 ≤ 35%（退休期 ≤ 20%）？超標時將下年度所有新資金轉投 VALU / FWRA。"),
        ("☐  2. 單一 ETF ≤ 40% 紅線檢核：", "檢視 VALU、FWRA、0050、CBU7、TIP5 各自市值佔總資產是否均 ≤ 40%（達 > 38.5% 即行年底再平衡減碼）。"),
        ("☐  3. 美元計價 UCITS 下限檢核：", "英股愛爾蘭美元資產合計（VALU + FWRA + CBU7 + TIP5 + IB01）是否維持 ≥ 35%（實質目標 65%–80%）？"),
        ("☐  4. 組合風險預算與 TER 檢核：", "股債實際權重是否處於該階段目標 ±6% 區間（階段二 80/20、階段三 65/35、退休期 45/55；總加權 TER ≤ 0.15%）？"),
        ("☐  5. 每季 LSE 批買與匯費稽核：", "富邦英股專戶是否確以「外幣（美元）交割」執行四季整股批買？手續費率是否維持書面專案議價（≤ 0.25%）？且無誤買 GBP 掛牌級別（TP05 / ITPS / TI5A.L）？"),
        ("☐  6. CPI 購買力連動校正（次年 1 月生效）：", "查詢主計總處最新台灣 CPI 年增率，精確調整次年度每月定投目標金額（如 3 / 7 / 10 萬基數 × 累計 CPI 倍率）或退休層一月領基數。"),
        ("☐  7. 0050 質押與連結基金雙軌檢核：", "原型 0050 ETF 是否嚴格封頂 ≤ 250 萬實質作緊急質押底倉，且個人所得淨額逼近 12% 末段（或單次配息近 2 萬）時即將全數新錢導流至 0050 連結 A 不配息（嚴禁 TISA）？"),
        ("☐  8. 750 萬 AMT 海外所得跨年調節檢核：", "結算當年度實質已實現海外所得（TIP5 現金息 ＋ UCITS 賣出已實現獲利），確認總額遠低於 NT$750 萬免稅額；大額調整分跨 12 月末與 1 月初執行。"),
        ("☐  9. 人力資本與階段二提前觸發檢核：", "（前 5 年適用）實質總資產是否已跨越 350 萬元提前切換至 7.0 萬/月 80/20？或有收入波動/扶養比超標須提前納入 CBU7？"),
        ("☐ 10. 退休就緒閘門驗算：", "（第 25～29 年適用）計算「年末總實質資產 − 150 萬實質醫療池」是否達 ≥ 2,750 萬元實質（或觸發停滯性通膨橋接條款）？"),
        ("☐ 11. 雙軌提領與水桶一補庫檢核：", "（退休期專用）檢核層一 77 萬實質 100% 足額給付；若 WR ≤ 1.80% 核發層二紅利（封頂 2.20% / +35%）；檢查水桶一台幣與 IB01 餘額，若低於 2.2 年（169.4 萬實質）依 45/55 紀律補滿 3.0 年。"),
        ("☐ 12. 緊急備援與遺產隔離確認：", "確認水桶四 150 萬實質醫療專戶完整獨立未遭生活費挪用，且全部海外部位 100% 皆為愛爾蘭註冊 UCITS（0% 美國遺產稅曝險）。"),
    ]
    for c_bold, c_text in checklist:
        p = doc.add_paragraph()
        p.paragraph_format.space_before = Pt(1.5)
        p.paragraph_format.space_after = Pt(2.5)
        p.paragraph_format.line_spacing = 1.18
        p.paragraph_format.left_indent = Inches(0.25)
        p.paragraph_format.first_line_indent = Inches(-0.25)
        rb = p.add_run(c_bold)
        set_run_font(rb, 9.0, bold=True, color=NAVY)
        rt = p.add_run(c_text)
        set_run_font(rt, 9.0, bold=False, color=DARK)

    out_repo = os.path.join(base_dir, "25年加速版_Master_IPS_投資執行憲法_修正定案版.docx")
    out_home = "/home/antigravity/25年加速版_Master_IPS_投資執行憲法_修正定案版.docx"
    doc.save(out_repo)
    shutil.copy2(out_repo, out_home)
    print(f"Generated V2 Master IPS DOCX:\n  1) {out_repo}\n  2) {out_home}")


if __name__ == "__main__":
    main()
