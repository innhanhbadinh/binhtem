"""
Test API backend. Chay: pytest tests/ -v (tu thu muc backend/)

Khong can khoi dong server that - dung FastAPI TestClient (goi thang vao app,
khong qua mang that).
"""
import os
import re
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

# Mat khau tai file dung cho test - can co gia tri de khong bao 503 "chua cau hinh"
TEST_DOWNLOAD_PASSWORD = "test-password-123"
os.environ.setdefault("DOWNLOAD_PASSWORD", TEST_DOWNLOAD_PASSWORD)

from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)

FIXTURES = os.path.join(os.path.dirname(os.path.abspath(__file__)), "fixtures")
STAR_PDF = os.path.join(FIXTURES, "star_shape.pdf")
CIRCLE_PDF = os.path.join(FIXTURES, "circle_20mm.pdf")


def test_health_check():
    r = client.get("/")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"


def _post_ghep(path, data, password=TEST_DOWNLOAD_PASSWORD):
    full_data = dict(data)
    if password is not None:
        full_data["download_password"] = password
    with open(path, "rb") as f:
        return client.post(
            "/api/ghep",
            files={"file": ("test.pdf", f, "application/pdf")},
            data=full_data,
        )


def test_ghep_rect_returns_pdf_file():
    r = _post_ghep(STAR_PDF, {"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"
    assert len(r.content) > 0


def test_ghep_circle_returns_pdf_file():
    r = _post_ghep(CIRCLE_PDF, {"shape": "circle", "paper_w": 320, "paper_h": 430, "gap": 2})
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_ghep_custom_free_nesting():
    r = _post_ghep(STAR_PDF, {
        "shape": "custom", "paper_w": 150, "paper_h": 150, "gap": 3,
        "allow_rotation": True, "res_mm_per_px": 0.4, "use_grid": False,
    })
    assert r.status_code == 200


def test_ghep_ellipse():
    r = _post_ghep(STAR_PDF, {
        "shape": "ellipse", "paper_w": 200, "paper_h": 200, "gap": 2,
        "ellipse_w": 40, "ellipse_h": 25, "allow_rotation": True,
    })
    assert r.status_code == 200
    assert r.headers["content-type"] == "application/pdf"


def test_ghep_uses_filename_hint_from_frontend():
    """Ten file tra ve phai dung filename_hint (noi dung Lenh san xuat) neu co gui len."""
    r = _post_ghep(STAR_PDF, {
        "shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2,
        "filename_hint": "Decal 7 mau 32x43cm, in 5 to.pdf",
    })
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    # FileResponse ma hoa ten file dang UTF-8 percent-encoding trong header
    # (RFC 5987), vi du dau cach -> %20, dau phay -> %2C. Giai ma lai truoc khi so sanh.
    import urllib.parse
    match = re.search(r"filename\*=UTF-8''([^;]+)", cd, re.IGNORECASE)
    assert match, f"Khong tim thay filename* trong header: {cd}"
    decoded = urllib.parse.unquote(match.group(1))
    assert decoded == "Decal 7 mau 32x43cm, in 5 to.pdf"


def test_ghep_sanitizes_dangerous_filename_hint():
    """filename_hint chua ky tu khong hop le (vd dau /) phai duoc loai bo, khong gay loi."""
    r = _post_ghep(STAR_PDF, {
        "shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2,
        "filename_hint": '../../etc/passwd:*?"<>|.pdf',
    })
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    # Lay rieng phan TEN FILE trong header (khong tinh dau ngoac kep bao quanh
    # von la cu phap chuan cua chinh header, khong phai du lieu nguoi dung)
    match = re.search(r'filename="([^"]*)"', cd)
    assert match, f"Khong tim thay filename= trong header: {cd}"
    extracted_name = match.group(1)
    for bad_char in ["/", "\\", ":", "*", "?", "<", ">", "|"]:
        assert bad_char not in extracted_name


def test_ghep_empty_filename_hint_falls_back():
    r = _post_ghep(STAR_PDF, {"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2})
    assert r.status_code == 200
    cd = r.headers.get("content-disposition", "")
    assert "ghep_rect" in cd  # fallback dung ten file goc + kieu ghep


def test_ghep_ellipse_missing_size_returns_400():
    r = _post_ghep(STAR_PDF, {"shape": "ellipse", "paper_w": 200, "paper_h": 200, "gap": 2})
    assert r.status_code == 400


def test_ghep_invalid_shape_returns_400():
    r = _post_ghep(STAR_PDF, {"shape": "tamgiac", "paper_w": 200, "paper_h": 200, "gap": 2})
    assert r.status_code == 400


def test_ghep_invalid_paper_size_returns_400():
    r = _post_ghep(STAR_PDF, {"shape": "rect", "paper_w": 0, "paper_h": 200, "gap": 2})
    assert r.status_code == 400


def test_ghep_non_pdf_file_returns_400():
    r = client.post(
        "/api/ghep",
        files={"file": ("test.txt", b"hello", "text/plain")},
        data={"shape": "rect", "paper_w": 200, "paper_h": 200, "gap": 2,
              "download_password": TEST_DOWNLOAD_PASSWORD},
    )
    assert r.status_code == 400


def test_ghep_missing_password_returns_422():
    r = _post_ghep(STAR_PDF, {"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2}, password=None)
    assert r.status_code == 422


def test_ghep_wrong_password_returns_403():
    r = _post_ghep(STAR_PDF, {"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2},
                    password="mat-khau-sai")
    assert r.status_code == 403
    assert "không đúng" in r.json()["detail"].lower()


def test_ghep_correct_password_succeeds():
    r = _post_ghep(STAR_PDF, {"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2})
    assert r.status_code == 200


def test_ghep_missing_server_password_config_returns_503():
    old_pass = os.environ.pop("DOWNLOAD_PASSWORD", None)
    try:
        r = _post_ghep(STAR_PDF, {"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2})
        assert r.status_code == 503
    finally:
        if old_pass is not None:
            os.environ["DOWNLOAD_PASSWORD"] = old_pass


def test_preview_does_not_require_password():
    """Xem truoc KHONG can mat khau - chi ghep/tai file that moi can."""
    with open(STAR_PDF, "rb") as f:
        r = client.post(
            "/api/preview",
            files={"file": ("test.pdf", f, "application/pdf")},
            data={"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2},
        )
    assert r.status_code == 200


def test_ghep_invalid_oc_type_returns_400():
    r = _post_ghep(STAR_PDF, {
        "shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2, "oc_type": "tamgiac",
    })
    assert r.status_code == 400


def test_ghep_with_oc_tron_and_production_text_no_overlap():
    """
    Ghep that voi oc tron + lenh san xuat, kiem tra bang so hoc (khong chi
    nhin bang mat): 4 oc phai nam dung vi tri (7mm tu moi canh, duong kinh 5mm)
    va KHONG chong len nhau (hien nhien vi o 4 goc khac nhau tren kho giay
    320x430mm, nhung van kiem tra de chac chan khong bi ve sai/du thua).
    """
    import fitz

    r = _post_ghep(CIRCLE_PDF, {
        "shape": "circle", "paper_w": 320, "paper_h": 430, "gap": 2,
        "oc_type": "tron",
        "production_text": "Decal giấy Oji 32x43cm, in 11 tờ, Cán màng - cán bóng, Gia công - kẻ thành phẩm",
    })
    assert r.status_code == 200

    doc = fitz.open(stream=r.content, filetype="pdf")
    page = doc[0]  # trang noi dung (trang 1)

    # Tim cac hinh tron da fill (drawings type='f') co kich thuoc ~5mm - chinh la oc be,
    # phan biet voi cac hinh tron NOI DUNG (tem) vi tem KHONG duoc fill dac (chi la outline
    # duoc show_pdf_page tu file goc, thuong la stroke, khong phai fill dac mau den).
    drawings = page.get_drawings()
    oc_candidates = []
    for d in drawings:
        if d["type"] == "f" and d.get("fill"):
            rect = d["rect"]
            diam_mm = (rect.x1 - rect.x0) * 25.4 / 72
            if 4.5 < diam_mm < 5.5:  # duong kinh ~5mm
                oc_candidates.append(rect)

    print(f"So oc tim thay: {len(oc_candidates)}")
    assert len(oc_candidates) == 4, f"Phai co dung 4 oc tron, tim thay {len(oc_candidates)}"

    # Kiem tra tung oc dung vi tri: tam cach deu 7mm tu canh gan nhat
    paper_w_pt, paper_h_pt = page.rect.width, page.rect.height
    expected_margin_pt = 7.0 * 72 / 25.4
    for rect in oc_candidates:
        cx = (rect.x0 + rect.x1) / 2
        cy = (rect.y0 + rect.y1) / 2
        dist_left, dist_right = cx, paper_w_pt - cx
        dist_top, dist_bottom = cy, paper_h_pt - cy
        near_x = min(dist_left, dist_right)
        near_y = min(dist_top, dist_bottom)
        assert abs(near_x - expected_margin_pt) < 1, f"Le ngang sai: {near_x}"
        assert abs(near_y - expected_margin_pt) < 1, f"Le doc sai: {near_y}"

    # Kiem tra co chen text (bang cach tim trong danh sach text tren trang)
    page_text = page.get_text()
    assert "Decal" in page_text and "Oji" in page_text
    print("OK: 4 oc tron dung vi tri + co chen text lenh san xuat")


def test_ghep_with_oc_vuong_draws_brackets():
    import fitz

    r = _post_ghep(CIRCLE_PDF, {
        "shape": "circle", "paper_w": 320, "paper_h": 430, "gap": 2,
        "oc_type": "vuong",
    })
    assert r.status_code == 200

    doc = fitz.open(stream=r.content, filetype="pdf")
    page = doc[0]
    drawings = page.get_drawings()
    # Oc vuong ve bang draw_line (type='s', stroke) - dem so duong thang gan
    # dung 4 goc trang co mau toi (gan den) va do day ~1mm
    stroke_lines_near_corners = 0
    paper_w_pt, paper_h_pt = page.rect.width, page.rect.height
    for d in drawings:
        if d["type"] != "s":
            continue
        rect = d["rect"]
        # Gan 1 trong 4 goc (trong pham vi 20mm)
        near_corner = (
            (rect.x0 < mm_to_pt_local(20) or rect.x1 > paper_w_pt - mm_to_pt_local(20))
            and (rect.y0 < mm_to_pt_local(20) or rect.y1 > paper_h_pt - mm_to_pt_local(20))
        )
        if near_corner:
            stroke_lines_near_corners += 1

    print(f"So duong stroke gan goc: {stroke_lines_near_corners}")
    assert stroke_lines_near_corners >= 4, "Phai co it nhat vai net ve o cac goc (oc vuong)"


def mm_to_pt_local(mm):
    return mm * 72 / 25.4


def test_ghep_without_oc_no_registration_marks():
    """Mac dinh oc_type='none' -> khong duoc tu dong ve oc be nao ca."""
    import fitz

    r = _post_ghep(CIRCLE_PDF, {"shape": "circle", "paper_w": 320, "paper_h": 430, "gap": 2})
    assert r.status_code == 200

    doc = fitz.open(stream=r.content, filetype="pdf")
    page = doc[0]
    drawings = page.get_drawings()
    oc_candidates = [
        d for d in drawings
        if d["type"] == "f" and d.get("fill")
        and 4.5 < (d["rect"].x1 - d["rect"].x0) * 25.4 / 72 < 5.5
    ]
    assert len(oc_candidates) == 0, "Khong duoc co oc be nao khi oc_type=none (mac dinh)"


def _count_oc_tron_on_page(page):
    drawings = page.get_drawings()
    return sum(
        1 for d in drawings
        if d["type"] == "f" and d.get("fill")
        and 4.5 < (d["rect"].x1 - d["rect"].x0) * 25.4 / 72 < 5.5
    )


def test_ghep_oc_tron_appears_on_all_pages_fixed_layout():
    """
    Oc be phai xuat hien tren TAT CA cac trang PDF (ca trang noi dung LAN trang
    khuon), khong chi rieng trang dau. Ap dung cho Chu nhat/Tron.
    """
    import fitz

    r = _post_ghep(CIRCLE_PDF, {
        "shape": "circle", "paper_w": 320, "paper_h": 430, "gap": 2, "oc_type": "tron",
    })
    assert r.status_code == 200

    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) >= 2, "File phai co it nhat 2 trang (noi dung + khuon) de test co y nghia"
    for i in range(len(doc)):
        n = _count_oc_tron_on_page(doc[i])
        assert n == 4, f"Trang {i + 1} thieu oc be (tim thay {n}/4)"


def test_ghep_oc_vuong_appears_on_all_pages_custom_nesting():
    """Tuong tu nhung cho Elip/Hinh bat ky (nesting.py)."""
    import fitz

    r = _post_ghep(STAR_PDF, {
        "shape": "ellipse", "paper_w": 200, "paper_h": 200, "gap": 2,
        "ellipse_w": 40, "ellipse_h": 25, "oc_type": "vuong",
    })
    assert r.status_code == 200

    doc = fitz.open(stream=r.content, filetype="pdf")
    assert len(doc) >= 2

    def count_oc_vuong(page):
        drawings = page.get_drawings()
        return sum(1 for d in drawings if d["type"] == "s")

    for i in range(len(doc)):
        n = count_oc_vuong(doc[i])
        assert n > 0, f"Trang {i + 1} khong co net ve nao cua oc vuong"


def test_ghep_production_text_shows_vietnamese_diacritics_correctly():
    """
    Dam bao chu tieng Viet co dau hien DUNG (khong bi mat/loi thanh '?') -
    day la loi tung gap voi font mac dinh cua PyMuPDF.
    """
    import fitz

    text_with_diacritics = "Decal giấy Oji 32x43cm, cán bóng, kẻ thành phẩm"
    r = _post_ghep(CIRCLE_PDF, {
        "shape": "circle", "paper_w": 320, "paper_h": 430, "gap": 2,
        "production_text": text_with_diacritics,
    })
    assert r.status_code == 200

    doc = fitz.open(stream=r.content, filetype="pdf")
    page_text = doc[0].get_text()
    assert "giấy" in page_text, f"Dau tieng Viet bi loi, noi dung trang: {page_text[:200]!r}"
    assert "cán bóng" in page_text
    # Kiem tra cu the khong co ky tu thay the loi (mojibake dang '?')
    assert "gi?y" not in page_text and "b?ng" not in page_text


# ===== /api/preview =====

def _post_preview(path, data):
    with open(path, "rb") as f:
        return client.post(
            "/api/preview",
            files={"file": ("test.pdf", f, "application/pdf")},
            data=data,
        )


def test_preview_rect_no_email_needed():
    r = _post_preview(STAR_PDF, {"shape": "rect", "paper_w": 320, "paper_h": 430, "gap": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["shape_mode"] == "rect"
    assert body["count"] > 0
    assert body["count"] == len(body["pieces"])
    assert all(p["type"] == "rect" for p in body["pieces"])
    assert body["paper_w_mm"] > 0 and body["paper_h_mm"] > 0


def test_preview_circle_matches_no_overlap():
    r = _post_preview(CIRCLE_PDF, {"shape": "circle", "paper_w": 320, "paper_h": 430, "gap": 2})
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 100
    assert all(p["type"] == "circle" for p in body["pieces"])

    import itertools
    centers = [(p["cx_mm"], p["cy_mm"]) for p in body["pieces"]]
    r0 = body["pieces"][0]["r_mm"]
    min_dist = min(
        ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5
        for (x1, y1), (x2, y2) in itertools.combinations(centers, 2)
    )
    assert min_dist >= 2 * r0 - 0.1  # khong chong lan (cho sai so nho)


def test_preview_custom_returns_polygons():
    r = _post_preview(STAR_PDF, {
        "shape": "custom", "paper_w": 150, "paper_h": 150, "gap": 3,
        "allow_rotation": True, "res_mm_per_px": 0.4, "use_grid": False,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["count"] >= 4
    assert all(p["type"] == "polygon" and len(p["points_mm"]) >= 4 for p in body["pieces"])


def test_preview_ellipse_returns_ellipses():
    r = _post_preview(STAR_PDF, {
        "shape": "ellipse", "paper_w": 200, "paper_h": 200, "gap": 2,
        "ellipse_w": 40, "ellipse_h": 25, "allow_rotation": True,
    })
    assert r.status_code == 200
    body = r.json()
    assert body["count"] > 10
    assert all(p["type"] == "ellipse" for p in body["pieces"])


def test_preview_invalid_shape_returns_400():
    r = _post_preview(STAR_PDF, {"shape": "tamgiac", "paper_w": 200, "paper_h": 200, "gap": 2})
    assert r.status_code == 400
