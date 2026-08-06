"""
Layout ghep co dinh: hinh chu nhat/vuong (luoi deu) va hinh tron (to ong).
Day la thuat toan "nhanh" (cong thuc toan hoc), khac voi nesting.py (dung
mask + FFT cho hinh dang bat ky).
"""
import math
import fitz
from .utils import mm_to_pt, pt_to_mm


# ===== CÁC HÀM TÍNH TOÁN LAYOUT =====

def calculate_optimal_layout(bat_w, bat_h, paper_w, paper_h, gap, margin, is_circle=False):
    """Tính số cột, hàng và hướng giấy tối ưu."""
    usable_w = paper_w - 2 * margin
    usable_h = paper_h - 2 * margin

    if is_circle:
        diameter = bat_w
        h_spacing = diameter + gap
        v_spacing = diameter * 0.8660254 + gap

        def calc_circle(aw, ah):
            if aw < diameter or ah < diameter:
                return 0, 0, 0, 0
            cols_even = int((aw - diameter) // h_spacing) + 1
            remaining = aw - diameter - h_spacing / 2
            cols_odd = (int(remaining // h_spacing) + 1) if remaining >= 0 else 0
            cols_odd = max(0, min(cols_odd, cols_even))
            rows = int((ah - diameter) // v_spacing) + 1
            if rows <= 0 or cols_even <= 0:
                return 0, 0, 0, 0
            rows_even = math.ceil(rows / 2)
            rows_odd = rows - rows_even
            total = rows_even * cols_even + rows_odd * cols_odd
            return cols_even, cols_odd, rows, total

        cols_even_p, cols_odd_p, rows_p, total_p = calc_circle(usable_w, usable_h)
        cols_even_l, cols_odd_l, rows_l, total_l = calc_circle(paper_h - 2 * margin, paper_w - 2 * margin)
        if total_l > total_p:
            return (cols_even_l, cols_odd_l, rows_l, True, paper_h, paper_w)
        else:
            return (cols_even_p, cols_odd_p, rows_p, False, paper_w, paper_h)
    else:
        def calc_rect(aw, ah):
            if gap == 0:
                return int(aw // bat_w), int(ah // bat_h)
            else:
                return int((aw + gap) // (bat_w + gap)), int((ah + gap) // (bat_h + gap))

        cols_p, rows_p = calc_rect(usable_w, usable_h)
        cols_l, rows_l = calc_rect(paper_h - 2 * margin, paper_w - 2 * margin)
        if cols_l * rows_l > cols_p * rows_p:
            return (cols_l, cols_l, rows_l, True, paper_h, paper_w)
        else:
            return (cols_p, cols_p, rows_p, False, paper_w, paper_h)


def compute_fixed_layout(input_pdf, gap_mm, paper_w_mm, paper_h_mm, bleed_on, bleed_mm, is_circle=False):
    """Tính toán vị trí các tem trên từng trang."""
    gap = mm_to_pt(gap_mm)
    bleed = mm_to_pt(bleed_mm) if bleed_on else 0
    max_pw = mm_to_pt(paper_w_mm)
    max_ph = mm_to_pt(paper_h_mm)
    margin = mm_to_pt(7)

    src_doc = fitz.open(input_pdf)
    all_pages = []

    for idx in range(len(src_doc)):
        page = src_doc[idx]
        bat_rect = page.rect
        bat_w = bat_rect.width
        bat_h = bat_rect.height if not is_circle else bat_w

        cols_even, cols_odd, rows, is_landscape, final_pw, final_ph = calculate_optimal_layout(
            bat_w, bat_h, max_pw, max_ph, gap, margin, is_circle
        )
        if cols_even == 0 or rows == 0:
            continue

        usable_w = final_pw - 2 * margin
        usable_h = final_ph - 2 * margin

        # Tính lề căn giữa
        if is_circle:
            diameter = bat_w
            h_spacing = diameter + gap
            v_spacing = diameter * 0.866 + gap
            total_w_even = (cols_even - 1) * h_spacing + diameter
            total_w_odd = ((cols_odd - 1) * h_spacing + diameter + h_spacing / 2) if cols_odd > 0 else 0
            total_w = max(total_w_even, total_w_odd)
            total_h = (rows - 1) * v_spacing + diameter
            mx = margin + (usable_w - total_w) / 2
            my = margin + (usable_h - total_h) / 2
        else:
            cols = cols_even
            total_w = cols * bat_w + (cols - 1) * gap
            total_h = rows * bat_h + (rows - 1) * gap
            mx = margin + (usable_w - total_w) / 2
            my = margin + (usable_h - total_h) / 2

        placements = []
        if is_circle:
            for r in range(rows):
                cols_this_row = cols_even if r % 2 == 0 else cols_odd
                x_offset = 0 if r % 2 == 0 else h_spacing / 2
                for c in range(cols_this_row):
                    cx = mx + c * h_spacing + diameter / 2 + x_offset
                    cy = my + r * v_spacing + diameter / 2
                    placements.append({
                        "x_pt": cx - diameter / 2,
                        "y_pt": cy - diameter / 2,
                        "w_pt": diameter,
                        "h_pt": diameter,
                        "center_x": cx,
                        "center_y": cy
                    })
        else:
            for r in range(rows):
                for c in range(cols_even):
                    placements.append({
                        "x_pt": mx + c * (bat_w + gap),
                        "y_pt": my + r * (bat_h + gap),
                        "w_pt": bat_w,
                        "h_pt": bat_h
                    })

        all_pages.append({
            "page_index": idx,
            "placements": placements,
            "cols": cols_even,
            "cols_odd": cols_odd,
            "rows": rows,
            "final_paper_w": final_pw,
            "final_paper_h": final_ph,
            "margin_x": mx,
            "margin_y": my,
            "bat_w": bat_w,
            "bat_h": bat_h,
            "is_circle": is_circle,
            "gap": gap,
            "bleed": bleed,
            "is_landscape": is_landscape,
        })
    src_doc.close()
    return all_pages


# ===== HÀM VẼ DẤU CẮT (TRIM MARKS) =====

def draw_trim_marks(page, margin_x, margin_y, bat_w, bat_h, gap, rows, cols,
                    is_circle=False, cols_odd=None):
    """Vẽ các dấu cắt xung quanh khối tem (chỉ dùng cho hình chữ nhật/vuông)."""
    mark_len = mm_to_pt(10)
    offset = mm_to_pt(2)
    color = (0, 0, 0)
    width = 0.5

    if is_circle:
        # Không vẽ cho hình tròn (hàm vẫn được định nghĩa nhưng sẽ không gọi)
        return

    total_w = cols * bat_w + (cols - 1) * gap
    total_h = rows * bat_h + (rows - 1) * gap
    start_x, start_y = margin_x, margin_y
    end_x, end_y = margin_x + total_w, margin_y + total_h

    # Dọc
    for i in range(cols + 1):
        x = start_x + i * (bat_w + gap) - (gap / 2 if 0 < i < cols else 0)
        page.draw_line(fitz.Point(x, start_y - offset), fitz.Point(x, start_y - offset - mark_len), color=color, width=width)
        page.draw_line(fitz.Point(x, end_y + offset), fitz.Point(x, end_y + offset + mark_len), color=color, width=width)
    # Ngang
    for j in range(rows + 1):
        y = start_y + j * (bat_h + gap) - (gap / 2 if 0 < j < rows else 0)
        page.draw_line(fitz.Point(start_x - offset, y), fitz.Point(start_x - offset - mark_len, y), color=color, width=width)
        page.draw_line(fitz.Point(end_x + offset, y), fitz.Point(end_x + offset + mark_len, y), color=color, width=width)


def draw_grid_lines_on_page(page, paper_w, paper_h, margin_x, margin_y,
                            bat_w, bat_h, gap, rows, cols, is_circle=False, cols_odd=None):
    """Vẽ lưới (đường viền tem) trên trang template."""
    color = (1, 0, 1)
    width = 0.5

    if is_circle:
        diameter = bat_w
        radius = diameter / 2
        h_spacing = diameter + gap
        v_spacing = diameter * 0.866 + gap
        cols_odd = cols if cols_odd is None else cols_odd
        for r in range(rows):
            cols_this_row = cols if r % 2 == 0 else cols_odd
            x_offset = 0 if r % 2 == 0 else h_spacing / 2
            for c in range(cols_this_row):
                cx = margin_x + c * h_spacing + radius + x_offset
                cy = margin_y + r * v_spacing + radius
                rect = fitz.Rect(cx - radius, cy - radius, cx + radius, cy + radius)
                page.draw_oval(rect, color=color, width=width)
    else:
        total_w = cols * bat_w + (cols - 1) * gap
        total_h = rows * bat_h + (rows - 1) * gap
        for c in range(cols + 1):
            x = margin_x + c * (bat_w + gap) - (gap / 2 if 0 < c < cols else 0)
            page.draw_line(fitz.Point(x, margin_y), fitz.Point(x, margin_y + total_h), color=color, width=width)
        for r in range(rows + 1):
            y = margin_y + r * (bat_h + gap) - (gap / 2 if 0 < r < rows else 0)
            page.draw_line(fitz.Point(margin_x, y), fitz.Point(margin_x + total_w, y), color=color, width=width)


# ===== HÀM TẠO PDF CHÍNH =====

def repeat_fixed_layout(input_pdf, output_pdf, gap_mm, paper_w_mm, paper_h_mm,
                        bleed_on, bleed_mm, is_circle=False):
    """Tạo PDF với layout cố định, mỗi tem được lặp lại."""
    pages_data = compute_fixed_layout(input_pdf, gap_mm, paper_w_mm, paper_h_mm,
                                      bleed_on, bleed_mm, is_circle)
    if not pages_data:
        return False

    src_doc = fitz.open(input_pdf)
    dst_doc = fitz.open()

    for data in pages_data:
        placements = data["placements"]
        pw, ph = data["final_paper_w"], data["final_paper_h"]
        mx, my = data["margin_x"], data["margin_y"]
        gap = data["gap"]
        bleed = data["bleed"]
        cols, rows = data["cols"], data["rows"]
        cols_odd = data.get("cols_odd", cols)
        is_circle = data["is_circle"]
        bat_w, bat_h = data["bat_w"], data["bat_h"]
        total_tem = len(placements)

        # ---- Trang nội dung (chứa tem thực tế) ----
        page = dst_doc.new_page(width=pw, height=ph)
        for p in placements:
            x, y = p["x_pt"], p["y_pt"]
            if bleed > 0:
                clip = fitz.Rect(x - bleed, y - bleed,
                                 x + p["w_pt"] + bleed, y + p["h_pt"] + bleed)
                page.show_pdf_page(clip, src_doc, data["page_index"], clip=src_doc[data["page_index"]].rect)
            else:
                target = fitz.Rect(x, y, x + p["w_pt"], y + p["h_pt"])
                page.show_pdf_page(target, src_doc, data["page_index"])

        # Chỉ vẽ trim marks cho hình chữ nhật/vuông (không vẽ cho hình tròn)
        if not is_circle:
            draw_trim_marks(page, mx, my, bat_w, bat_h, gap, rows, cols, is_circle, cols_odd)

        # ---- Trang khuôn (hiển thị lưới và thông tin) ----
        tmpl = dst_doc.new_page(width=pw, height=ph)
        draw_grid_lines_on_page(tmpl, pw, ph, mx, my, bat_w, bat_h, gap, rows, cols, is_circle, cols_odd)
        # Không vẽ trim marks trên trang template

        # ---- Thông tin in trên template (đã lược bỏ các mục không cần thiết) ----
        orient = "NGANG" if data["is_landscape"] else "DOC"
        layout_type = "TRON" if is_circle else "CHU NHAT"
        cols_label = f"{cols}/{cols_odd}" if is_circle and cols_odd != cols else f"{cols}"

        # Dòng 1: số tem, hướng, loại layout
        tmpl.insert_text(
            fitz.Point(mx, my - mm_to_pt(2)),
            f"Trang {data['page_index']+1}: {cols_label}x{rows} = {total_tem} tem/to | {orient} | {layout_type}",
            fontsize=8, color=(0, 0, 1)
        )
        # Dòng 2: khổ giấy
        tmpl.insert_text(
            fitz.Point(mx, my - mm_to_pt(5)),
            f"Kho giay: {pt_to_mm(pw):.0f} x {pt_to_mm(ph):.0f} mm",
            fontsize=8, color=(0, 0, 1)
        )
        # Dòng 3: kích thước tem (chỉ hiển thị với layout chữ nhật)
        if not is_circle:
            tmpl.insert_text(
                fitz.Point(mx, my - mm_to_pt(8)),
                f"Kich thuoc bat: {pt_to_mm(bat_w):.1f} x {pt_to_mm(bat_h):.1f} mm",
                fontsize=8, color=(1, 0, 0)
            )
        # Đối với hình tròn, không hiển thị thêm gì

    dst_doc.save(output_pdf)
    dst_doc.close()
    src_doc.close()
    return True
