"""
Test module customer_sheet.py. Gia lap hoan toan Google Sheets API (khong goi
mang that, khong can service account that) bang 1 fake worksheet object mo
phong dung cac phuong thuc gspread dùng den: get_all_records, update_cell,
append_row.
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))

import pytest
from unittest.mock import patch
from fastapi import HTTPException

from app import customer_sheet as cs


class FakeWorksheet:
    """Mo phong 1 worksheet gspread, luu du lieu trong bo nho de kiem tra."""

    def __init__(self, rows=None):
        # rows: list[dict] voi key la ten cot dung HEADER_ROW
        self.rows = rows or []
        self.update_calls = []
        self.append_calls = []

    def get_all_records(self):
        return list(self.rows)

    def update_cell(self, row_idx, col_idx, value):
        self.update_calls.append((row_idx, col_idx, value))
        # row_idx=2 tuong ung self.rows[0], vv.
        data_idx = row_idx - 2
        col_name = cs.HEADER_ROW[col_idx - 1]
        self.rows[data_idx][col_name] = value

    def append_row(self, values):
        self.append_calls.append(values)
        self.rows.append(dict(zip(cs.HEADER_ROW, values)))


def _patch_sheet(fake_ws):
    return patch.object(cs, "get_customer_sheet", return_value=fake_ws)


def test_get_customer_sheet_raises_503_when_not_configured():
    old_creds = os.environ.pop("GOOGLE_SHEETS_CREDENTIALS_JSON", None)
    old_id = os.environ.pop("GOOGLE_SHEET_ID", None)
    try:
        with pytest.raises(HTTPException) as exc_info:
            cs.get_customer_sheet()
        assert exc_info.value.status_code == 503
    finally:
        if old_creds is not None:
            os.environ["GOOGLE_SHEETS_CREDENTIALS_JSON"] = old_creds
        if old_id is not None:
            os.environ["GOOGLE_SHEET_ID"] = old_id


def test_new_customer_not_blocked():
    fake_ws = FakeWorksheet(rows=[])
    with _patch_sheet(fake_ws):
        cs.check_customer_not_blocked("new@example.com", "0912345678")
    # Khong bao loi gi -> khach moi mac dinh khong bi khoa


def test_record_new_customer_appends_row():
    fake_ws = FakeWorksheet(rows=[])
    with _patch_sheet(fake_ws):
        cs.record_customer_usage("new@example.com", "0912345678")

    assert len(fake_ws.append_calls) == 1
    email, phone, count, first_used, last_used, blocked = fake_ws.append_calls[0]
    assert email == "new@example.com"
    assert phone == "0912345678"
    assert count == 1
    assert blocked == "FALSE"


def test_record_existing_customer_increments_count():
    fake_ws = FakeWorksheet(rows=[
        {"Email": "lan@example.com", "Số điện thoại": "0911111111",
         "Số lần ghép": 5, "Lần đầu dùng": "2026-01-01", "Lần cuối dùng": "2026-01-05",
         "Bị khoá": "FALSE"},
    ])
    with _patch_sheet(fake_ws):
        cs.record_customer_usage("lan@example.com", "0911111111")

    assert fake_ws.rows[0]["Số lần ghép"] == 6
    # Da cap nhat lan cuoi dung (khac ngay cu)
    assert fake_ws.rows[0]["Lần cuối dùng"] != "2026-01-05"


def test_blocked_customer_by_email_raises_403():
    fake_ws = FakeWorksheet(rows=[
        {"Email": "doithu@example.com", "Số điện thoại": "0999999999",
         "Số lần ghép": 50, "Lần đầu dùng": "x", "Lần cuối dùng": "y",
         "Bị khoá": "TRUE"},
    ])
    with _patch_sheet(fake_ws):
        with pytest.raises(HTTPException) as exc_info:
            cs.check_customer_not_blocked("doithu@example.com", "0000000000")
    assert exc_info.value.status_code == 403


def test_blocked_customer_by_phone_raises_403():
    """Khoa theo SDT ngay ca khi khach doi email khac de lach."""
    fake_ws = FakeWorksheet(rows=[
        {"Email": "cu@example.com", "Số điện thoại": "0999999999",
         "Số lần ghép": 50, "Lần đầu dùng": "x", "Lần cuối dùng": "y",
         "Bị khoá": "TRUE"},
    ])
    with _patch_sheet(fake_ws):
        with pytest.raises(HTTPException) as exc_info:
            cs.check_customer_not_blocked("email_moi_khac@example.com", "0999999999")
    assert exc_info.value.status_code == 403


def test_blocked_value_case_insensitive():
    for blocked_val in ["true", "True", "TRUE", "1", "x", "X", "khoá", "Khoa"]:
        fake_ws = FakeWorksheet(rows=[
            {"Email": "a@example.com", "Số điện thoại": "01",
             "Số lần ghép": 1, "Lần đầu dùng": "x", "Lần cuối dùng": "y",
             "Bị khoá": blocked_val},
        ])
        with _patch_sheet(fake_ws):
            with pytest.raises(HTTPException):
                cs.check_customer_not_blocked("a@example.com", "01")


def test_not_blocked_value_variants():
    for not_blocked_val in ["", "FALSE", "false", "0", "no"]:
        fake_ws = FakeWorksheet(rows=[
            {"Email": "a@example.com", "Số điện thoại": "01",
             "Số lần ghép": 1, "Lần đầu dùng": "x", "Lần cuối dùng": "y",
             "Bị khoá": not_blocked_val},
        ])
        with _patch_sheet(fake_ws):
            cs.check_customer_not_blocked("a@example.com", "01")  # khong duoc bao loi
