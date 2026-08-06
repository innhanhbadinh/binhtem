"""
Backend FastAPI cho web app "Ghep PDF" - In Nhanh Ba Dinh.

Endpoints:
    POST /api/ghep     - ghep PDF that su, tra ve file .pdf
    POST /api/preview  - tinh toan layout (khong xuat PDF), tra ve JSON toa do
                         de frontend tu ve hinh xem truoc bang SVG.

Chay cuc bo:
    uvicorn app.main:app --reload

Deploy len Render.com (hoac tuong tu):
    Start command: uvicorn app.main:app --host 0.0.0.0 --port $PORT
"""
import os
import re
import tempfile
import shutil

from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from starlette.background import BackgroundTask
from shapely.affinity import translate

from .utils import pt_to_mm
from .fixed_layout import repeat_fixed_layout, compute_fixed_layout
from .nesting import repeat_custom_shape_layout, compute_custom_layout, _rotate_cw

app = FastAPI(title="Ghep PDF API - In Nhanh Ba Dinh")

# CORS: cho phep frontend (GitHub Pages / Vercel / localhost khi dev) goi API.
# expose_headers=["Content-Disposition"] la BAT BUOC de JavaScript (fetch) o
# trinh duyet doc duoc ten file trong header khi tai PDF ve - mac dinh trinh
# duyet CHAN doc header nay tren request khac domain neu server khong khai
# bao ro rang minh cho phep (khac voi curl/Postman, khong bi CORS chan).
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["Content-Disposition"],
)


@app.get("/")
def health_check():
    return {"status": "ok", "service": "ghep-pdf-api"}


def _validate_common(file: UploadFile, shape: str, paper_w: float, paper_h: float,
                      ellipse_w: float, ellipse_h: float):
    if not file.filename.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="File phai co dinh dang .pdf")
    if paper_w <= 0 or paper_h <= 0:
        raise HTTPException(status_code=400, detail="Kho giay phai lon hon 0")
    if shape not in ("rect", "circle", "ellipse", "custom"):
        raise HTTPException(status_code=400, detail=f"Kieu ghep khong hop le: {shape}")
    if shape == "ellipse" and (not ellipse_w or not ellipse_h or ellipse_w <= 0 or ellipse_h <= 0):
        raise HTTPException(status_code=400, detail="Can nhap kich thuoc Elip (rong/cao) > 0")


FORBIDDEN_FILENAME_CHARS = re.compile(r'[\\/:*?"<>|\r\n\t]')


def _sanitize_filename(name: str, fallback: str) -> str:
    """
    Lam sach ten file goi y tu frontend (filename_hint) truoc khi dung lam ten
    file tai ve that su. KHONG tin tuong hoan toan du lieu tu client - loai bo
    ky tu khong hop le tren Windows/Mac, gioi han do dai, luon fallback ve ten
    mac dinh neu rong/khong hop le sau khi lam sach.
    """
    if not name:
        return fallback
    name = FORBIDDEN_FILENAME_CHARS.sub("", name).strip()
    name = re.sub(r"\s+", " ", name)
    if not name:
        return fallback
    if not name.lower().endswith(".pdf"):
        name = f"{name}.pdf"
    if len(name) > 180:
        name = name[:176].rstrip() + ".pdf"
    return name


@app.post("/api/ghep")
async def ghep_pdf(
    file: UploadFile = File(...),
    shape: str = Form(...),  # "rect" | "circle" | "ellipse" | "custom"
    paper_w: float = Form(...),  # mm
    paper_h: float = Form(...),  # mm
    gap: float = Form(0.0),  # mm
    bleed: bool = Form(False),
    bleed_mm: float = Form(0.0),
    ellipse_w: float = Form(None),  # mm - chi can khi shape == "ellipse"
    ellipse_h: float = Form(None),  # mm - chi can khi shape == "ellipse"
    allow_rotation: bool = Form(True),  # chi ap dung cho ellipse/custom
    res_mm_per_px: float = Form(0.4),  # do chinh xac cho ellipse/custom
    use_grid: bool = Form(False),  # custom: True = xep thang hang, False = ghep khit tu do
    filename_hint: str = Form(""),  # ten file goi y tu frontend (tu noi dung Lenh san xuat)
    oc_type: str = Form("none"),  # "none" | "tron" | "vuong" - oc be cho may be
    production_text: str = Form(""),  # noi dung Lenh san xuat chen len trang 1, cach mep 7mm
):
    if oc_type not in ("none", "tron", "vuong"):
        raise HTTPException(status_code=400, detail=f"Loai oc be khong hop le: {oc_type}")

    _validate_common(file, shape, paper_w, paper_h, ellipse_w, ellipse_h)

    work_dir = tempfile.mkdtemp(prefix="ghep_")
    input_path = os.path.join(work_dir, "input.pdf")
    output_path = os.path.join(work_dir, "output.pdf")

    try:
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        if shape in ("rect", "circle"):
            is_circle = shape == "circle"
            ok = repeat_fixed_layout(
                input_path, output_path, gap, paper_w, paper_h, bleed, bleed_mm,
                is_circle=is_circle, oc_type=oc_type, production_text=production_text,
            )
            if not ok:
                raise HTTPException(
                    status_code=422,
                    detail="Khong the ghep - kiem tra lai kich thuoc file PDF va kho giay (kho giay co the qua nho).",
                )
        else:  # ellipse | custom
            ok, err = repeat_custom_shape_layout(
                input_path, output_path, gap, paper_w, paper_h,
                shape_mode=shape,
                allow_rotation=allow_rotation,
                res_mm_per_px=res_mm_per_px,
                ellipse_w_mm=ellipse_w,
                ellipse_h_mm=ellipse_h,
                use_grid=use_grid,
                oc_type=oc_type,
                production_text=production_text,
            )
            if not ok:
                raise HTTPException(status_code=422, detail=f"Khong the ghep: {err}")

        base_name = os.path.splitext(file.filename)[0]
        fallback_filename = f"{base_name}_ghep_{shape}.pdf"
        out_filename = _sanitize_filename(filename_hint, fallback_filename)

        return FileResponse(
            output_path,
            media_type="application/pdf",
            filename=out_filename,
            background=BackgroundTask(shutil.rmtree, work_dir, ignore_errors=True),
        )
    except HTTPException:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise
    except Exception as e:
        shutil.rmtree(work_dir, ignore_errors=True)
        raise HTTPException(status_code=500, detail=f"Loi khong xac dinh: {str(e)}")


@app.post("/api/preview")
async def preview_ghep(
    file: UploadFile = File(...),
    shape: str = Form(...),
    paper_w: float = Form(...),
    paper_h: float = Form(...),
    gap: float = Form(0.0),
    bleed: bool = Form(False),
    bleed_mm: float = Form(0.0),
    ellipse_w: float = Form(None),
    ellipse_h: float = Form(None),
    allow_rotation: bool = Form(True),
    res_mm_per_px: float = Form(0.4),
    use_grid: bool = Form(False),
):
    """
    Tinh toan layout (khong xuat file PDF) - tra ve JSON mo ta:
      - kich thuoc khay giay that su (mm)
      - danh sach cac hinh da dat, moi hinh la 1 trong 3 dang:
          {"type": "rect", "x_mm", "y_mm", "w_mm", "h_mm"}
          {"type": "circle", "cx_mm", "cy_mm", "r_mm"}
          {"type": "ellipse", "x_mm", "y_mm", "w_mm", "h_mm"}   (bounding box)
          {"type": "polygon", "points_mm": [[x,y], ...]}         (hinh dang bat ky)
    Frontend tu ve SVG tu du lieu nay - khong can server render anh/PDF that.
    """
    _validate_common(file, shape, paper_w, paper_h, ellipse_w, ellipse_h)

    work_dir = tempfile.mkdtemp(prefix="preview_")
    input_path = os.path.join(work_dir, "input.pdf")

    try:
        with open(input_path, "wb") as f:
            shutil.copyfileobj(file.file, f)

        pieces = []

        if shape in ("rect", "circle"):
            is_circle = shape == "circle"
            pages = compute_fixed_layout(input_path, gap, paper_w, paper_h, bleed, bleed_mm, is_circle)
            if not pages:
                raise HTTPException(
                    status_code=422,
                    detail="Khong the ghep - kiem tra lai kich thuoc file PDF va kho giay.",
                )
            data = pages[0]
            if is_circle:
                for p in data["placements"]:
                    pieces.append({
                        "type": "circle",
                        "cx_mm": pt_to_mm(p["center_x"]),
                        "cy_mm": pt_to_mm(p["center_y"]),
                        "r_mm": pt_to_mm(p["w_pt"]) / 2,
                    })
            else:
                for p in data["placements"]:
                    pieces.append({
                        "type": "rect",
                        "x_mm": pt_to_mm(p["x_pt"]),
                        "y_mm": pt_to_mm(p["y_pt"]),
                        "w_mm": pt_to_mm(p["w_pt"]),
                        "h_mm": pt_to_mm(p["h_pt"]),
                    })
            paper_w_mm_out = pt_to_mm(data["final_paper_w"])
            paper_h_mm_out = pt_to_mm(data["final_paper_h"])

        else:  # ellipse | custom
            pages = compute_custom_layout(
                input_path, gap, paper_w, paper_h, shape_mode=shape,
                allow_rotation=allow_rotation, res_mm_per_px=res_mm_per_px,
                ellipse_w_mm=ellipse_w, ellipse_h_mm=ellipse_h, use_grid=use_grid,
            )
            if not pages:
                raise HTTPException(
                    status_code=422,
                    detail="Khong the ghep - kiem tra lai kich thuoc file PDF va kho giay.",
                )
            data = pages[0]
            if shape == "ellipse":
                for p in data["placements"]:
                    pieces.append({
                        "type": "ellipse",
                        "x_mm": pt_to_mm(p["x_pt"]),
                        "y_mm": pt_to_mm(p["y_pt"]),
                        "w_mm": pt_to_mm(p["w_pt"]),
                        "h_mm": pt_to_mm(p["h_pt"]),
                    })
            else:  # custom - can ve dung contour (co the loi/lom)
                poly_norm = data["poly_norm"]
                for p in data["placements"]:
                    rp = _rotate_cw(poly_norm, p["rot"])
                    rp = translate(rp, xoff=-rp.bounds[0], yoff=-rp.bounds[1])
                    rp = translate(rp, xoff=p["x_pt"], yoff=p["y_pt"])
                    pts = [[pt_to_mm(x), pt_to_mm(y)] for x, y in rp.exterior.coords]
                    pieces.append({"type": "polygon", "points_mm": pts})
            paper_w_mm_out = pt_to_mm(data["sheet_w_pt"])
            paper_h_mm_out = pt_to_mm(data["sheet_h_pt"])

        return {
            "shape_mode": shape,
            "paper_w_mm": paper_w_mm_out,
            "paper_h_mm": paper_h_mm_out,
            "count": len(pieces),
            "pieces": pieces,
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Loi khong xac dinh: {str(e)}")
    finally:
        shutil.rmtree(work_dir, ignore_errors=True)
