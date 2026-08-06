"""
Nest engine: trich xuat hinh dang (die-line) tu PDF va ghep khit (nesting)
cho Elip / Hinh dang bat ky. Xem giai thich thuat toan trong README.md.
"""
import math
import fitz
import numpy as np
import cv2
from shapely.geometry import Polygon, MultiPolygon
from shapely.affinity import translate, rotate as _shapely_rotate
from shapely.ops import unary_union
from scipy.signal import fftconvolve
from scipy.ndimage import binary_dilation
from PIL import Image, ImageDraw

from .utils import mm_to_pt, pt_to_mm, draw_registration_marks, insert_production_text

def _rotate_cw(poly, angle_cw_deg, origin="centroid"):
    return _shapely_rotate(poly, -angle_cw_deg, origin=origin)

def _bezier_flatten(p0, p1, p2, p3, n=8):
    pts = []
    for i in range(1, n + 1):
        t = i / n
        mt = 1 - t
        x = (mt**3) * p0.x + 3 * (mt**2) * t * p1.x + 3 * mt * (t**2) * p2.x + (t**3) * p3.x
        y = (mt**3) * p0.y + 3 * (mt**2) * t * p1.y + 3 * mt * (t**2) * p2.y + (t**3) * p3.y
        pts.append((x, y))
    return pts

def extract_shape_from_vectors(page):
    drawings = page.get_drawings()
    polys = []
    for d in drawings:
        pts = []
        def add_pt(p):
            xy = (p.x, p.y)
            if not pts or pts[-1] != xy:
                pts.append(xy)
        for item in d["items"]:
            op = item[0]
            if op == "l":
                add_pt(item[1]); add_pt(item[2])
            elif op == "c":
                p0, p1, p2, p3 = item[1], item[2], item[3], item[4]
                add_pt(p0)
                for xy in _bezier_flatten(p0, p1, p2, p3):
                    if not pts or pts[-1] != xy:
                        pts.append(xy)
            elif op == "re":
                r = item[1]
                for xy in [(r.x0, r.y0), (r.x1, r.y0), (r.x1, r.y1), (r.x0, r.y1)]:
                    if not pts or pts[-1] != xy:
                        pts.append(xy)
            elif op == "qu":
                q = item[1]
                for xy in [(q.ul.x, q.ul.y), (q.ur.x, q.ur.y), (q.lr.x, q.lr.y), (q.ll.x, q.ll.y)]:
                    if not pts or pts[-1] != xy:
                        pts.append(xy)
        if len(pts) >= 3:
            try:
                p = Polygon(pts)
                if not p.is_valid:
                    p = p.buffer(0)
                if p.area > 0:
                    polys.append(p)
            except:
                pass
    if not polys:
        return None
    merged = unary_union(polys)
    if isinstance(merged, MultiPolygon):
        merged = max(merged.geoms, key=lambda g: g.area)
    return merged

def extract_shape_from_raster(page, dpi=200, threshold=250):
    pix = page.get_pixmap(dpi=dpi)
    img = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)
    if pix.n >= 3:
        gray = cv2.cvtColor(img[:, :, :3], cv2.COLOR_RGB2GRAY)
    else:
        gray = img[:, :, 0]
    _, mask = cv2.threshold(gray, threshold, 255, cv2.THRESH_BINARY_INV)
    contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    if not contours:
        return None
    largest = max(contours, key=cv2.contourArea)
    largest = cv2.approxPolyDP(largest, epsilon=1.0, closed=True)
    if len(largest) < 3:
        return None
    px_to_pt = 72.0 / dpi
    pts = [(pt[0][0] * px_to_pt, pt[0][1] * px_to_pt) for pt in largest]
    try:
        poly = Polygon(pts)
        if not poly.is_valid:
            poly = poly.buffer(0)
        return poly if poly.area > 0 else None
    except:
        return None

def extract_shape_from_page(page, raster_dpi=200):
    poly = extract_shape_from_vectors(page)
    if poly is not None:
        return poly, "vector"
    poly = extract_shape_from_raster(page, dpi=raster_dpi)
    if poly is not None:
        return poly, "raster"
    return None, None

def make_ellipse_polygon(w_pt, h_pt, n_points=72):
    a, b = w_pt / 2, h_pt / 2
    pts = [(a * math.cos(2*math.pi*i/n_points), b * math.sin(2*math.pi*i/n_points)) for i in range(n_points)]
    return Polygon(pts)

def polygon_to_mask(poly: Polygon, res_pt_per_px):
    minx, miny, maxx, maxy = poly.bounds
    w = max(1, int(math.ceil((maxx - minx) / res_pt_per_px)) + 1)
    h = max(1, int(math.ceil((maxy - miny) / res_pt_per_px)) + 1)
    img = Image.new("1", (w, h), 0)
    draw = ImageDraw.Draw(img)
    pts = [((x - minx) / res_pt_per_px, (y - miny) / res_pt_per_px) for x, y in poly.exterior.coords]
    draw.polygon(pts, fill=1)
    return np.array(img, dtype=bool)

def _best_fit_position(occupied: np.ndarray, piece_mask: np.ndarray):
    H, W = occupied.shape
    h, w = piece_mask.shape
    if h > H or w > W:
        return None
    occ_f = occupied.astype(np.float32)
    piece_f = piece_mask.astype(np.float32)
    flipped = piece_f[::-1, ::-1]
    full = fftconvolve(occ_f, flipped, mode="full")
    overlap = full[h-1:h-1+(H-h+1), w-1:w-1+(W-w+1)]
    valid = overlap < 0.5
    if not np.any(valid):
        return None
    ys, xs = np.where(valid)
    order = np.lexsort((xs, ys))
    best = order[0]
    return int(ys[best]), int(xs[best])

# ===== HÀM grid_placements ĐÃ SỬA =====
def grid_placements(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px, rotations_deg=(0,)):
    """
    Xếp các hình lên lưới đều, thử tất cả các góc xoay (nếu có) và chọn góc cho số lượng nhiều nhất.
    Trả về danh sách các placement (mỗi placement gồm x_pt, y_pt, rot, w_pt, h_pt).
    """
    minx0, miny0, _, _ = poly.bounds
    poly_norm = translate(poly, xoff=-minx0, yoff=-miny0)
    best_placements = []
    best_count = -1

    for ang in rotations_deg:
        rp = _rotate_cw(poly_norm, ang)
        rp = translate(rp, xoff=-rp.bounds[0], yoff=-rp.bounds[1])
        w, h = rp.bounds[2], rp.bounds[3]
        cell_w, cell_h = w + gap_pt, h + gap_pt
        cols = int(sheet_w_pt // cell_w)
        rows = int(sheet_h_pt // cell_h)
        if cols <= 0 or rows <= 0:
            continue
        offset_x = (sheet_w_pt - cols * cell_w) / 2
        offset_y = (sheet_h_pt - rows * cell_h) / 2
        placements = []
        for r in range(rows):
            for c in range(cols):
                placements.append({
                    "x_pt": offset_x + c * cell_w,
                    "y_pt": offset_y + r * cell_h,
                    "rot": ang,
                    "w_pt": w,
                    "h_pt": h,
                })
        count = len(placements)
        if count > best_count:
            best_count = count
            best_placements = placements
    return best_placements

def nest_pieces(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px, rotations_deg=(0,), max_pieces=None):
    minx, miny, _, _ = poly.bounds
    poly = translate(poly, xoff=-minx, yoff=-miny)
    W = int(math.ceil(sheet_w_pt / res_pt_per_px))
    H = int(math.ceil(sheet_h_pt / res_pt_per_px))
    occupied = np.zeros((H, W), dtype=bool)
    gap_px = max(0, int(round(gap_pt / res_pt_per_px)))
    rot_masks = {}
    for ang in rotations_deg:
        rp = _rotate_cw(poly, ang)
        rp = translate(rp, xoff=-rp.bounds[0], yoff=-rp.bounds[1])
        mask = polygon_to_mask(rp, res_pt_per_px)
        if gap_px > 0:
            mask = binary_dilation(mask, iterations=gap_px)
        rot_masks[ang] = mask
    placements = []
    while max_pieces is None or len(placements) < max_pieces:
        best_choice = None
        for ang, mask in rot_masks.items():
            pos = _best_fit_position(occupied, mask)
            if pos is None:
                continue
            y, x = pos
            if best_choice is None or (y, x) < (best_choice[0], best_choice[1]):
                best_choice = (y, x, ang)
        if best_choice is None:
            break
        y, x, ang = best_choice
        mask = rot_masks[ang]
        hh, ww = mask.shape
        occupied[y:y+hh, x:x+ww] |= mask
        placements.append({
            "x_pt": x * res_pt_per_px,
            "y_pt": y * res_pt_per_px,
            "rot": ang,
            "w_pt": ww * res_pt_per_px,
            "h_pt": hh * res_pt_per_px,
        })
    return placements

# HÀM repeat_custom_shape_layout (đã có use_grid, giữ nguyên)
def repeat_custom_shape_layout(input_pdf, output_pdf, gap_mm, paper_w_mm, paper_h_mm,
                                shape_mode="custom", allow_rotation=True,
                                res_mm_per_px=0.35, ellipse_w_mm=None, ellipse_h_mm=None,
                                max_pieces_per_page=2000, use_grid=False,
                                oc_type="none", production_text=""):
    gap_pt = mm_to_pt(gap_mm)
    sheet_w_pt = mm_to_pt(paper_w_mm)
    sheet_h_pt = mm_to_pt(paper_h_mm)
    res_pt_per_px = mm_to_pt(res_mm_per_px)
    rotations = (0, 90, 180, 270) if allow_rotation else (0,)

    src_doc = fitz.open(input_pdf)
    dst_doc = fitz.open()

    try:
        for page_index in range(len(src_doc)):
            src_page = src_doc[page_index]

            if shape_mode == "ellipse":
                if not ellipse_w_mm or not ellipse_h_mm:
                    raise ValueError("Cần truyền ellipse_w_mm và ellipse_h_mm khi shape_mode='ellipse'")
                w_pt, h_pt = mm_to_pt(ellipse_w_mm), mm_to_pt(ellipse_h_mm)
                poly = make_ellipse_polygon(w_pt, h_pt)
                page_rect = src_page.rect
                cx, cy = page_rect.width / 2, page_rect.height / 2
                bat_rect = fitz.Rect(cx - w_pt/2, cy - h_pt/2, cx + w_pt/2, cy + h_pt/2)
                source_used = "ellipse"
            else:
                poly, source_used = extract_shape_from_page(src_page)
                if poly is None:
                    print(f"⚠️ Không tìm thấy hình dạng ở trang {page_index + 1}, bỏ qua.")
                    continue
                minx, miny, maxx, maxy = poly.bounds
                bat_rect = fitz.Rect(minx, miny, maxx, maxy)

            # ---- XỬ LÝ LAYOUT ----
            if shape_mode == "custom":
                if use_grid:
                    # Dùng lưới với xoay tối ưu (thử tất cả góc)
                    placements = grid_placements(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px, rotations_deg=rotations)
                else:
                    placements = nest_pieces(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px,
                                             rotations_deg=rotations, max_pieces=max_pieces_per_page)
            else:  # ellipse
                placements = grid_placements(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px, rotations_deg=rotations)

            if not placements:
                print(f"⚠️ Không ghép được hình nào cho trang {page_index + 1}.")
                continue

            minx0, miny0, _, _ = poly.bounds
            poly_norm = translate(poly, xoff=-minx0, yoff=-miny0)

            out_page = dst_doc.new_page(width=sheet_w_pt, height=sheet_h_pt)
            for p in placements:
                target = fitz.Rect(p["x_pt"], p["y_pt"], p["x_pt"] + p["w_pt"], p["y_pt"] + p["h_pt"])
                out_page.show_pdf_page(target, src_doc, page_index, clip=bat_rect, rotate=p["rot"])

            draw_registration_marks(out_page, sheet_w_pt, sheet_h_pt, oc_type)
            insert_production_text(out_page, production_text, sheet_w_pt)

            tmpl_page = dst_doc.new_page(width=sheet_w_pt, height=sheet_h_pt)
            for p in placements:
                rp = _rotate_cw(poly_norm, p["rot"])
                rp = translate(rp, xoff=-rp.bounds[0], yoff=-rp.bounds[1])
                rp = translate(rp, xoff=p["x_pt"], yoff=p["y_pt"])
                pts = [fitz.Point(x, y) for x, y in rp.exterior.coords]
                tmpl_page.draw_polyline(pts, color=(1,0,1), width=0.5, closePath=True)

            info = (f"Trang {page_index+1}: {len(placements)} hinh | Nguon: {source_used} | "
                    f"Xoay: {'Co' if allow_rotation else 'Khong'} | Gap: {gap_mm}mm | Kho: {paper_w_mm}x{paper_h_mm}mm")
            tmpl_page.insert_text(fitz.Point(10, 15), info, fontsize=8, color=(0,0,1))

        dst_doc.save(output_pdf)
        return True, None
    except Exception as e:
        return False, str(e)
    finally:
        dst_doc.close()
        src_doc.close()

def compute_custom_layout(input_pdf, gap_mm, paper_w_mm, paper_h_mm, shape_mode="custom",
                          allow_rotation=True, res_mm_per_px=0.4,
                          ellipse_w_mm=None, ellipse_h_mm=None, use_grid=False):
    gap_pt = mm_to_pt(gap_mm)
    sheet_w_pt = mm_to_pt(paper_w_mm)
    sheet_h_pt = mm_to_pt(paper_h_mm)
    res_pt_per_px = mm_to_pt(res_mm_per_px)
    rotations = (0, 90, 180, 270) if allow_rotation else (0,)

    src_doc = fitz.open(input_pdf)
    all_pages = []

    for idx in range(len(src_doc)):
        src_page = src_doc[idx]

        if shape_mode == "ellipse":
            if not ellipse_w_mm or not ellipse_h_mm:
                raise ValueError("Cần truyền ellipse_w_mm và ellipse_h_mm")
            w_pt, h_pt = mm_to_pt(ellipse_w_mm), mm_to_pt(ellipse_h_mm)
            poly = make_ellipse_polygon(w_pt, h_pt)
            bat_w, bat_h = w_pt, h_pt
        else:
            poly, _ = extract_shape_from_page(src_page)
            if poly is None:
                continue
            minx, miny, maxx, maxy = poly.bounds
            bat_w, bat_h = maxx - minx, maxy - miny

        if shape_mode == "custom":
            if use_grid:
                placements = grid_placements(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px, rotations)
            else:
                placements = nest_pieces(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px, rotations)
        else:  # ellipse
            placements = grid_placements(poly, sheet_w_pt, sheet_h_pt, gap_pt, res_pt_per_px, rotations)

        if not placements:
            continue

        minx0, miny0, _, _ = poly.bounds
        poly_norm = translate(poly, xoff=-minx0, yoff=-miny0)

        all_pages.append({
            "page_index": idx,
            "placements": placements,
            "poly_norm": poly_norm,
            "bat_w": bat_w, "bat_h": bat_h,
            "sheet_w_pt": sheet_w_pt,
            "sheet_h_pt": sheet_h_pt,
            "gap_pt": gap_pt,
            "rotations": rotations,
            "shape_mode": shape_mode,
        })
    src_doc.close()
    return all_pages
