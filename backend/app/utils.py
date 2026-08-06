"""Cac ham tien ich chuyen doi don vi (mm <-> point)."""
import fitz

def mm_to_pt(mm):
    return mm * 72 / 25.4

def pt_to_mm(pt):
    return pt * 25.4 / 72


# ============================================================
# Oc be (registration marks cho may be) - toa do trich xuat chinh xac tu
# 2 file mau "oc_tron.pdf" / "oc_vuong.pdf" (khong nhung nguyen file PDF,
# ve lai bang toa do de tu dong dung voi MOI kho giay, khong chi rieng
# khổ 320x430mm ma file mau duoc thiet ke san).
# ============================================================

_OC_COLOR = (0.135, 0.122, 0.124)  # mau den ngoc (rich black) giong file mau

# Oc tron: hinh tron dac, duong kinh 5mm, tam cach deu 2 canh 7mm
_OC_TRON_DIAMETER_MM = 5.0
_OC_TRON_MARGIN_MM = 7.0

# Oc vuong: hinh chu L, diem goc cach mep, 2 canh dai khac nhau
_OC_VUONG_MARGIN_X_MM = 5.26
_OC_VUONG_MARGIN_Y_MM = 4.83
_OC_VUONG_ARM_H_MM = 11.9
_OC_VUONG_ARM_V_MM = 13.4
_OC_VUONG_LINE_WIDTH_MM = 1.06


def draw_oc_tron_marks(page, paper_w_pt, paper_h_pt):
    """Ve 4 oc tron (dau cham tron) tai 4 goc trang, dung cho may be co dinh vi tron."""
    r_pt = mm_to_pt(_OC_TRON_DIAMETER_MM / 2)
    margin_pt = mm_to_pt(_OC_TRON_MARGIN_MM)
    centers = [
        (margin_pt, margin_pt),
        (paper_w_pt - margin_pt, margin_pt),
        (margin_pt, paper_h_pt - margin_pt),
        (paper_w_pt - margin_pt, paper_h_pt - margin_pt),
    ]
    for cx, cy in centers:
        rect = fitz.Rect(cx - r_pt, cy - r_pt, cx + r_pt, cy + r_pt)
        page.draw_oval(rect, color=_OC_COLOR, fill=_OC_COLOR, width=0)


def draw_oc_vuong_marks(page, paper_w_pt, paper_h_pt):
    """Ve 4 oc vuong (dau goc hinh chu L) tai 4 goc trang, dung cho may be co dinh vi goc."""
    corner_x = mm_to_pt(_OC_VUONG_MARGIN_X_MM)
    corner_y = mm_to_pt(_OC_VUONG_MARGIN_Y_MM)
    h_arm = mm_to_pt(_OC_VUONG_ARM_H_MM)
    v_arm = mm_to_pt(_OC_VUONG_ARM_V_MM)
    line_w = mm_to_pt(_OC_VUONG_LINE_WIDTH_MM)

    def draw_bracket(cx, cy, dir_h, dir_v):
        p_corner = fitz.Point(cx, cy)
        p_h_end = fitz.Point(cx + dir_h * h_arm, cy)
        p_v_end = fitz.Point(cx, cy + dir_v * v_arm)
        page.draw_line(p_corner, p_h_end, color=_OC_COLOR, width=line_w)
        page.draw_line(p_corner, p_v_end, color=_OC_COLOR, width=line_w)

    draw_bracket(corner_x, corner_y, +1, +1)  # goc tren-trai: canh huong phai/xuong
    draw_bracket(paper_w_pt - corner_x, corner_y, -1, +1)  # goc tren-phai
    draw_bracket(corner_x, paper_h_pt - corner_y, +1, -1)  # goc duoi-trai
    draw_bracket(paper_w_pt - corner_x, paper_h_pt - corner_y, -1, -1)  # goc duoi-phai


def draw_registration_marks(page, paper_w_pt, paper_h_pt, oc_type):
    """oc_type: 'tron' | 'vuong' | bat ky gia tri khac (vd 'none') = khong ve gi ca."""
    if oc_type == "tron":
        draw_oc_tron_marks(page, paper_w_pt, paper_h_pt)
    elif oc_type == "vuong":
        draw_oc_vuong_marks(page, paper_w_pt, paper_h_pt)


# ============================================================
# Chen noi dung "Lenh san xuat" len trang noi dung, cach mep giay 7mm
# ============================================================

PRODUCTION_TEXT_MARGIN_MM = 7.0


import os

_FONT_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fonts", "DejaVuSans.ttf")
_FONT_NAME = "dejavu-vn"


def insert_production_text(page, text, paper_w_pt):
    """
    Chen dong chu Lenh san xuat len GOC TREN-TRAI trang, cach mep tren 7mm.
    Cach mep TRAI xa hon (14mm) de KHONG de len oc be (oc be nam trong vung
    ~4.5-13mm tinh tu mep trai/phai, tuy loai tron/vuong). Tu dong xuong dong
    neu qua dai so voi chieu rong trang.

    Dung font DejaVu Sans nhung theo file (khong dung font "helv" mac dinh cua
    PyMuPDF) vi font mac dinh KHONG hien du dau tieng Viet (vd "giấy" -> "gi?y").
    """
    if not text:
        return
    top_margin_pt = mm_to_pt(PRODUCTION_TEXT_MARGIN_MM)
    left_margin_pt = mm_to_pt(14.0)
    box_height_pt = mm_to_pt(15)  # du cho 2-3 dong neu text dai, tu dong wrap
    box = fitz.Rect(left_margin_pt, top_margin_pt, paper_w_pt - left_margin_pt, top_margin_pt + box_height_pt)

    page.insert_font(fontname=_FONT_NAME, fontfile=_FONT_PATH)
    page.insert_textbox(
        box, text, fontsize=9, color=(0.35, 0.05, 0.05), fontname=_FONT_NAME, align=0,
    )
