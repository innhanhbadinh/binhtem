"""
Layout ghep co dinh: hinh chu nhat/vuong (luoi deu) va hinh tron (to ong).
Day la thuat toan "nhanh" (cong thuc toan hoc), khac voi nesting.py (dung
mask + FFT cho hinh dang bat ky).
"""
import math
import fitz

from .utils import mm_to_pt, pt_to_mm, draw_registration_marks, insert_production_text

def calculate_optimal_layout(bat_w, bat_h, paper_w, paper_h, gap, margin, is_circle=False):
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
        cols_even_l, cols_odd_l, rows_l, total_l = calc_circle(paper_h - 2*margin, paper_w - 2*margin)
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
        cols_l, rows_l = calc_rect(paper_h - 2*margin, paper_w - 2*margin)
        if cols_l * rows_l > cols_p * rows_p:
            return (cols_l, cols_l, rows_l, True, paper_h, paper_w)
        else:
            return (cols_p, cols_p, rows_p, False, paper_w, paper_h)

def draw_trim_marks(page, margin_x, margin_y, bat_w, bat_h, gap, rows, cols, is_circle=False, cols_odd=None):
    mark_len = mm_to_pt(10)
    offset = mm_to_pt(2)
    color = (0,0,0)
    width = 0.5

    if is_circle:
        diameter = bat_w
        h_spacing = diameter + gap
        v_spacing = diameter * 0.866 + gap
        cols_odd = cols if cols_odd is None else cols_odd
        total_w_even = (cols - 1) * h_spacing + diameter
        total_w_odd = ((cols_odd - 1) * h_spacing + diameter + h_spacing/2) if cols_odd > 0 else 0
        total_w = max(total_w_even, total_w_odd)
        total_h = (rows - 1) * v_spacing + diameter

        page.draw_line(fitz.Point(margin_x - offset, margin_y - offset),
                       fitz.Point(margin_x - offset - mark_len, margin_y - offset), color=color, width=width)
        page.draw_line(fitz.Point(margin_x - offset, margin_y - offset),
                       fitz.Point(margin_x - offset, margin_y - offset - mark_len), color=color, width=width)
        page.draw_line(fitz.Point(margin_x + total_w + offset, margin_y - offset),
                       fitz.Point(margin_x + total_w + offset + mark_len, margin_y - offset), color=color, width=width)
        page.draw_line(fitz.Point(margin_x + total_w + offset, margin_y - offset),
                       fitz.Point(margin_x + total_w + offset, margin_y - offset - mark_len), color=color, width=width)
        page.draw_line(fitz.Point(margin_x - offset, margin_y + total_h + offset),
                       fitz.Point(margin_x - offset - mark_len, margin_y + total_h + offset), color=color, width=width)
        page.draw_line(fitz.Point(margin_x - offset, margin_y + total_h + offset),
                       fitz.Point(margin_x - offset, margin_y + total_h + offset + mark_len), color=color, width=width)
        page.draw_line(fitz.Point(margin_x + total_w + offset, margin_y + total_h + offset),
                       fitz.Point(margin_x + total_w + offset + mark_len, margin_y + total_h + offset), color=color, width=width)
        page.draw_line(fitz.Point(margin_x + total_w + offset, margin_y + total_h + offset),
                       fitz.Point(margin_x + total_w + offset, margin_y + total_h + offset + mark_len), color=color, width=width)
    else:
        total_w = cols * bat_w + (cols - 1) * gap
        total_h = rows * bat_h + (rows - 1) * gap
        start_x, start_y = margin_x, margin_y
        end_x, end_y = margin_x + total_w, margin_y + total_h

        for i in range(cols + 1):
            x = start_x + i * (bat_w + gap) - (gap/2 if 0 < i < cols else 0)
            page.draw_line(fitz.Point(x, start_y - offset), fitz.Point(x, start_y - offset - mark_len), color=color, width=width)
            page.draw_line(fitz.Point(x, end_y + offset), fitz.Point(x, end_y + offset + mark_len), color=color, width=width)
        for j in range(rows + 1):
            y = start_y + j * (bat_h + gap) - (gap/2 if 0 < j < rows else 0)
            page.draw_line(fitz.Point(start_x - offset, y), fitz.Point(start_x - offset - mark_len, y), color=color, width=width)
            page.draw_line(fitz.Point(end_x + offset, y), fitz.Point(end_x + offset + mark_len, y), color=color, width=width)

def draw_grid_lines_on_page(page, paper_w, paper_h, margin_x, margin_y,
                            bat_w, bat_h, gap, rows, cols, is_circle=False, cols_odd=None):
    color = (1,0,1)
    width = 0.5
    if is_circle:
        diameter = bat_w
        radius = diameter/2
        h_spacing = diameter + gap
        v_spacing = diameter * 0.866 + gap
        cols_odd = cols if cols_odd is None else cols_odd
        for r in range(rows):
            cols_this_row = cols if r % 2 == 0 else cols_odd
            x_offset = 0 if r % 2 == 0 else h_spacing/2
            for c in range(cols_this_row):
                cx = margin_x + c * h_spacing + radius + x_offset
                cy = margin_y + r * v_spacing + radius
                rect = fitz.Rect(cx - radius, cy - radius, cx + radius, cy + radius)
                page.draw_oval(rect, color=color, width=width)
    else:
        total_w = cols * bat_w + (cols - 1) * gap
        total_h = rows * bat_h + (rows - 1) * gap
        for c in range(cols + 1):
            x = margin_x + c * (bat_w + gap) - (gap/2 if 0 < c < cols else 0)
            page.draw_line(fitz.Point(x, margin_y), fitz.Point(x, margin_y + total_h), color=color, width=width)
        for r in range(rows + 1):
            y = margin_y + r * (bat_h + gap) - (gap/2 if 0 < r < rows else 0)
            page.draw_line(fitz.Point(margin_x, y), fitz.Point(margin_x + total_w, y), color=color, width=width)

# ----- CÁC HÀM TÍNH TOÁN LAYOUT (DÙNG CHUNG) -----

def compute_fixed_layout(input_pdf, gap_mm, paper_w_mm, paper_h_mm, bleed_on, bleed_mm, is_circle=False):
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

        usable_w = final_pw - 2*margin
        usable_h = final_ph - 2*margin

        if is_circle:
            diameter = bat_w
            h_spacing = diameter + gap
            v_spacing = diameter * 0.866 + gap
            total_w_even = (cols_even - 1) * h_spacing + diameter
            total_w_odd = ((cols_odd - 1) * h_spacing + diameter + h_spacing/2) if cols_odd > 0 else 0
            total_w = max(total_w_even, total_w_odd)
            total_h = (rows - 1) * v_spacing + diameter
            mx = margin + (usable_w - total_w)/2
            my = margin + (usable_h - total_h)/2
        else:
            cols = cols_even
            total_w = cols * bat_w + (cols - 1) * gap
            total_h = rows * bat_h + (rows - 1) * gap
            mx = margin + (usable_w - total_w)/2
            my = margin + (usable_h - total_h)/2

        placements = []
        if is_circle:
            for r in range(rows):
                cols_this_row = cols_even if r % 2 == 0 else cols_odd
                x_offset = 0 if r % 2 == 0 else h_spacing/2
                for c in range(cols_this_row):
                    cx = mx + c * h_spacing + diameter/2 + x_offset
                    cy = my + r * v_spacing + diameter/2
                    placements.append({
                        "x_pt": cx - diameter/2, "y_pt": cy - diameter/2,
                        "w_pt": diameter, "h_pt": diameter,
                        "center_x": cx, "center_y": cy
                    })
        else:
            for r in range(rows):
                for c in range(cols):
                    placements.append({
                        "x_pt": mx + c * (bat_w + gap),
                        "y_pt": my + r * (bat_h + gap),
                        "w_pt": bat_w, "h_pt": bat_h
                    })

        all_pages.append({
            "page_index": idx,
            "placements": placements,
            "cols": cols_even, "cols_odd": cols_odd, "rows": rows,
            "final_paper_w": final_pw, "final_paper_h": final_ph,
            "margin_x": mx, "margin_y": my,
            "bat_w": bat_w, "bat_h": bat_h,
            "is_circle": is_circle,
            "gap": gap, "bleed": bleed,
            "is_landscape": is_landscape,
        })
    src_doc.close()
    return all_pages

# ----- HÀM XUẤT PDF (SỬ DỤNG compute_* ) -----

def repeat_fixed_layout(input_pdf, output_pdf, gap_mm, paper_w_mm, paper_h_mm, bleed_on, bleed_mm,
                        is_circle=False, oc_type="none", production_text=""):
    pages_data = compute_fixed_layout(input_pdf, gap_mm, paper_w_mm, paper_h_mm, bleed_on, bleed_mm, is_circle)
    if not pages_data:
        return False

    src_doc = fitz.open(input_pdf)
    dst_doc = fitz.open()

    for data in pages_data:
        placements = data["placements"]
        bat_rect = src_doc[data["page_index"]].rect
        pw, ph = data["final_paper_w"], data["final_paper_h"]
        mx, my = data["margin_x"], data["margin_y"]
        gap = data["gap"]
        bleed = data["bleed"]
        cols, rows = data["cols"], data["rows"]
        cols_odd = data.get("cols_odd", cols)
        is_circle = data["is_circle"]
        bat_w, bat_h = data["bat_w"], data["bat_h"]
        total_tem = len(placements)

        # Trang nội dung
        page = dst_doc.new_page(width=pw, height=ph)
        for p in placements:
            x, y = p["x_pt"], p["y_pt"]
            if bleed > 0:
                clip = fitz.Rect(x - bleed, y - bleed, x + p["w_pt"] + bleed, y + p["h_pt"] + bleed)
                page.show_pdf_page(clip, src_doc, data["page_index"], clip=bat_rect)
            else:
                target = fitz.Rect(x, y, x + p["w_pt"], y + p["h_pt"])
                page.show_pdf_page(target, src_doc, data["page_index"], clip=bat_rect)

        draw_trim_marks(page, mx, my, bat_w, bat_h, gap, rows, cols, is_circle, cols_odd)

        # Ốc bế (dấu định vị máy bế) + Lệnh sản xuất - chèn lên TRANG NỘI DUNG (trang 1)
        draw_registration_marks(page, pw, ph, oc_type)
        insert_production_text(page, production_text, pw)

        # Trang khuôn
        tmpl = dst_doc.new_page(width=pw, height=ph)
        draw_grid_lines_on_page(tmpl, pw, ph, mx, my, bat_w, bat_h, gap, rows, cols, is_circle, cols_odd)
        draw_trim_marks(tmpl, mx, my, bat_w, bat_h, gap, rows, cols, is_circle, cols_odd)

        # Thông tin
        info1 = f"Khoang cach tem: {gap_mm}mm"
        tmpl.insert_text(fitz.Point(mx, my - mm_to_pt(11)), info1, fontsize=8, color=(0,0.5,0))
        info2 = f"Le an toan: 7mm moi canh | Vung in: {pt_to_mm(pw-14):.0f}x{pt_to_mm(ph-14):.0f}mm"
        tmpl.insert_text(fitz.Point(mx, my - mm_to_pt(14)), info2, fontsize=8, color=(0.8,0.4,0))
        orient = "NGANG" if data["is_landscape"] else "DOC"
        layout_type = "TRON" if is_circle else "CHU NHAT"
        cols_label = f"{cols}/{cols_odd}" if is_circle and cols_odd != cols else f"{cols}"
        tmpl.insert_text(fitz.Point(mx, my - mm_to_pt(2)),
                         f"Trang {data['page_index']+1}: {cols_label}x{rows} = {total_tem} tem/to | {orient} | {layout_type}",
                         fontsize=8, color=(0,0,1))
        tmpl.insert_text(fitz.Point(mx, my - mm_to_pt(5)),
                         f"Kho giay: {pt_to_mm(pw):.0f} x {pt_to_mm(ph):.0f} mm",
                         fontsize=8, color=(0,0,1))
        if is_circle:
            tmpl.insert_text(fitz.Point(mx, my - mm_to_pt(8)),
                             f"Duong kinh: {pt_to_mm(bat_w):.1f} mm | Khoang cach ngang: {pt_to_mm(bat_w+gap):.1f}mm | doc: {pt_to_mm(bat_w*0.866+gap):.1f}mm",
                             fontsize=8, color=(0.5,0,0.5))
        else:
            tmpl.insert_text(fitz.Point(mx, my - mm_to_pt(8)),
                             f"Kich thuoc bat: {pt_to_mm(bat_w):.1f} x {pt_to_mm(bat_h):.1f} mm",
                             fontsize=8, color=(1,0,0))

    dst_doc.save(output_pdf)
    dst_doc.close()
    src_doc.close()
    return True
