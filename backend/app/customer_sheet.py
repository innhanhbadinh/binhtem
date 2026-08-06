"""
Quan ly danh sach khach hang (email + so dien thoai + so lan dung + trang thai
khoa) bang Google Sheets - de chu shop tu xem/sua/khoa truc tiep nhu 1 bang
tinh Excel, khong can giao dien admin rieng.

Cau truc sheet (dong 1 la tieu de, dung nguyen chu nhu duoi day - phan biet
hoa/thuong khong quan trong nhung nen giu dung de de doc):
    Email | Số điện thoại | Số lần ghép | Lần đầu dùng | Lần cuối dùng | Bị khoá

Can 2 bien moi truong:
    GOOGLE_SHEETS_CREDENTIALS_JSON - toan bo noi dung file JSON cua Service
        Account (dang 1 chuoi), xem huong dan tao trong README.
    GOOGLE_SHEET_ID - ID cua Google Sheet (nam giua "/d/" va "/edit" trong URL)
"""
import os
import json
from datetime import datetime, timezone

import gspread
from google.oauth2.service_account import Credentials
from fastapi import HTTPException

SHEET_SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]

COL_EMAIL = 1
COL_PHONE = 2
COL_COUNT = 3
COL_FIRST_USED = 4
COL_LAST_USED = 5
COL_BLOCKED = 6

HEADER_ROW = ["Email", "Số điện thoại", "Số lần ghép", "Lần đầu dùng", "Lần cuối dùng", "Bị khoá"]

# Gia tri o cot "Bi khoa" duoc coi la TRUE (khong phan biet hoa/thuong, co the
# go tay tren Google Sheets kieu nao cung duoc)
BLOCKED_TRUE_VALUES = {"true", "1", "có", "co", "x", "yes", "khoá", "khoa"}


def _now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def get_customer_sheet():
    """
    Mo ket noi toi Google Sheet cau hinh san. Neu chua cau hinh du 2 bien moi
    truong can thiet, bao 503 ro rang thay vi am tham bo qua viec theo doi
    khach hang (day la yeu cau bat buoc theo thiet ke, khong phai tuy chon).
    """
    creds_json = os.environ.get("GOOGLE_SHEETS_CREDENTIALS_JSON")
    sheet_id = os.environ.get("GOOGLE_SHEET_ID")

    if not creds_json or not sheet_id:
        raise HTTPException(
            status_code=503,
            detail="Server chưa được cấu hình Google Sheets (thiếu GOOGLE_SHEETS_CREDENTIALS_JSON/GOOGLE_SHEET_ID).",
        )

    try:
        creds_dict = json.loads(creds_json)
    except Exception:
        raise HTTPException(
            status_code=503,
            detail="GOOGLE_SHEETS_CREDENTIALS_JSON không phải JSON hợp lệ.",
        )

    try:
        creds = Credentials.from_service_account_info(creds_dict, scopes=SHEET_SCOPES)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"Không kết nối được Google Sheets: {str(e)}")

    return sheet


def _find_customer_row(sheet, email: str, phone: str):
    """
    Tim dong khop voi email HOAC so dien thoai da cho (khong phan biet hoa
    thuong, bo khoang trang thua). Tra ve (row_index, row_dict) neu tim thay,
    nguoc lai (None, None). row_index la so dong THAT SU tren Google Sheets
    (dong 1 la tieu de, nen du lieu bat dau tu dong 2).
    """
    records = sheet.get_all_records()  # list[dict], tu dong dung dong 1 lam key
    email_norm = (email or "").strip().lower()
    phone_norm = (phone or "").strip()

    for i, row in enumerate(records, start=2):
        row_email = str(row.get("Email", "")).strip().lower()
        row_phone = str(row.get("Số điện thoại", "")).strip()
        if (email_norm and row_email == email_norm) or (phone_norm and row_phone == phone_norm):
            return i, row
    return None, None


def check_customer_not_blocked(email: str, phone: str):
    """
    Kiem tra khach hang (theo email hoac SDT) co dang bi khoa khong. Bao 403
    neu bi khoa. Khong lam gi them (khong tang so dem o day - chi kiem tra).
    """
    sheet = get_customer_sheet()
    _, row = _find_customer_row(sheet, email, phone)
    if row is not None:
        blocked_value = str(row.get("Bị khoá", "")).strip().lower()
        if blocked_value in BLOCKED_TRUE_VALUES:
            raise HTTPException(
                status_code=403,
                detail="Email hoặc số điện thoại này đã bị khoá. Vui lòng liên hệ In Nhanh Ba Đình nếu có thắc mắc.",
            )


def record_customer_usage(email: str, phone: str):
    """
    Ghi nhan 1 lan su dung thanh cong: neu khach da co trong danh sach thi
    tang "So lan ghep" len 1 va cap nhat "Lan cuoi dung"; neu chua co thi them
    dong moi voi so lan = 1, chua bi khoa.
    """
    sheet = get_customer_sheet()
    row_idx, row = _find_customer_row(sheet, email, phone)
    now = _now_iso()

    if row_idx is not None:
        current_count = row.get("Số lần ghép", 0)
        try:
            current_count = int(current_count)
        except (TypeError, ValueError):
            current_count = 0
        sheet.update_cell(row_idx, COL_COUNT, current_count + 1)
        sheet.update_cell(row_idx, COL_LAST_USED, now)
    else:
        sheet.append_row([email, phone, 1, now, now, "FALSE"])
