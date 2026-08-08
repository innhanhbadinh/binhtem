# Ghép PDF Web — In Nhanh Ba Đình

Phiên bản web của công cụ ghép PDF (tem/nhãn/decal...) lên khổ giấy in tối ưu.
Hỗ trợ 4 kiểu ghép: **Chữ nhật**, **Tròn (tổ ong)**, **Elip**, **Hình dạng bất kỳ**
(tự đọc đường bế/die-line từ file PDF và ghép khít bằng thuật toán nesting).

Kiến trúc 2 phần độc lập:

```
ghep-pdf-web/
├── .github/
│   └── workflows/
│       └── deploy-pages.yml # Tu dong deploy frontend/ len GitHub Pages khi push
├── backend/            # FastAPI (Python) - xu ly ghep PDF that su
│   ├── app/
│   │   ├── main.py         # POST /api/ghep (gui email dinh kem) + POST /api/preview (tra JSON toa do)
│   │   ├── customer_sheet.py # Quan ly danh sach khach hang qua Google Sheets (khoa/theo doi)
│   │   ├── nesting.py      # Elip + Hinh dang bat ky (mask/FFT nesting)
│   │   ├── fixed_layout.py # Chu nhat (luoi) + Tron (to ong)
│   │   └── utils.py
│   ├── tests/
│   │   ├── fixtures/       # File PDF mau de test
│   │   └── test_api.py
│   ├── requirements.txt
│   └── render.yaml         # Cau hinh deploy Render.com (tuy chon)
└── frontend/            # HTML/CSS/JS thuan (khong can build) - deploy GitHub Pages
    ├── index.html
    ├── style.css
    ├── script.js           # Nut "Xem truoc" goi /api/preview va tu ve SVG
    └── config.js            # <-- CHINH URL BACKEND O DAY
```

Nút **"👁️ Xem trước"** gọi `/api/preview` — endpoint này chỉ *tính toán* layout (không
tạo file PDF thật), trả về toạ độ từng hình dưới dạng JSON để frontend tự vẽ bằng SVG.
Nhờ vậy xem trước rất nhanh, không tốn công sức xuất PDF nếu bạn chỉ muốn ước lượng số
lượng ghép được trước khi bấm "Ghép PDF" thật.

## 1. Chạy thử ở máy local

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate      # Windows: venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

Backend chạy ở `http://localhost:8000`. Kiểm tra nhanh: mở `http://localhost:8000/`
phải thấy `{"status":"ok",...}`.

### Frontend

Mở file `frontend/config.js`, đổi tạm thành:

```js
const BACKEND_URL = "http://localhost:8000";
```

Rồi serve thư mục `frontend/` bằng 1 static server bất kỳ, ví dụ:

```bash
cd frontend
python -m http.server 5500
```

Mở trình duyệt vào `http://localhost:5500`.

> ⚠️ Đừng mở thẳng file `index.html` bằng `file://` — trình duyệt sẽ chặn request
> fetch tới backend (CORS/security). Luôn serve qua HTTP như trên.

### Chạy test tự động (backend)

```bash
cd backend
pip install pytest
pytest tests/ -v
```

## 2. Deploy backend lên Render.com

1. Đẩy thư mục `backend/` lên GitHub (có thể để trong cùng repo với `frontend/`,
   Render cho phép chỉ định "Root Directory").
2. Trên Render.com: **New → Web Service** → chọn repo GitHub của bạn.
3. Cấu hình:
   - **Root Directory**: `backend`
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port $PORT`
   - **Plan**: Free (lưu ý: gói free sẽ "ngủ" sau vài phút không dùng, lần gọi
     đầu tiên có thể mất 30–50 giây để khởi động lại — frontend đã có sẵn thông
     báo này cho người dùng).
4. Sau khi deploy xong, Render cho bạn 1 URL dạng `https://ten-app.onrender.com`.

Repo đã có sẵn `backend/render.yaml` — nếu dùng tính năng "Blueprint" của Render,
nó sẽ tự đọc file này và điền sẵn cấu hình ở trên.

## 2b. Cấu hình gửi email (Gmail)

Sau khi ghép PDF xong, backend sẽ **gửi file đính kèm qua email** cho khách
hàng (không cho tải trực tiếp trên trình duyệt nữa) — mục đích để công cụ chỉ
thực sự "có ích" khi dùng đúng quy trình của bạn, tránh đối thủ vào ghép file
thoải mái mà không để lại dấu vết liên hệ nào.

**Bước 1 — Tạo "Mật khẩu ứng dụng" (App Password) cho Gmail:**

1. Dùng tài khoản Gmail bạn muốn dùng để gửi email (nên dùng 1 tài khoản riêng
   cho việc này, không dùng Gmail cá nhân chính).
2. Vào **myaccount.google.com/security**
3. Bật **"Xác minh 2 bước"** (2-Step Verification) nếu chưa bật — Google **bắt
   buộc** phải bật cái này mới cho tạo Mật khẩu ứng dụng.
4. Tìm mục **"Mật khẩu ứng dụng"** (App passwords) — có thể search "App
   passwords" ở ô tìm kiếm trong trang Security.
5. Tạo mới, đặt tên bất kỳ (ví dụ "Ghep PDF Web"), Google sẽ đưa ra 1 mã 16 ký
   tự dạng `abcd efgh ijkl mnop` — **copy lại mã này** (chỉ hiện 1 lần).

**Bước 2 — Cấu hình trên Render.com:**

1. Vào Render → service backend của bạn → tab **Environment**
2. Thêm 2 biến môi trường:
   - `GMAIL_ADDRESS` = địa chỉ Gmail bạn dùng (ví dụ `innhanhbadinh.tool@gmail.com`)
   - `GMAIL_APP_PASSWORD` = mã 16 ký tự vừa tạo ở Bước 1 (bỏ dấu cách hoặc giữ
     nguyên đều được)
3. Bấm **Save Changes** — Render tự khởi động lại, cấu hình có hiệu lực ngay.

**Nếu chưa cấu hình 2 biến này**: server sẽ báo lỗi rõ ràng (503 - chưa cấu
hình gửi email) thay vì âm thầm thất bại.

**Kiểm tra hoạt động thật:** sau khi cấu hình xong, thử ghép 1 file trên trang
web thật với email của chính bạn — nếu không thấy email đến (kể cả mục Spam),
kiểm tra lại đúng 2 biến môi trường và đảm bảo đã bật "Xác minh 2 bước" cho
tài khoản Gmail đó.

> ⚠️ **Giới hạn của cách này**: bất kỳ ai nhập email nào cũng nhận được file
> (không giới hạn danh sách khách hàng) — mục đích chính là buộc phải để lại
> địa chỉ liên hệ + số điện thoại thật, để bạn có thể **khoá** những
> email/SĐT dùng bất thường (xem mục 2c bên dưới), chứ không chặn được 100%
> ngay từ đầu.
>
> Gmail cá nhân/Workspace thường giới hạn khoảng 500 email/ngày cho tài khoản
> thường — nếu lượng khách hàng dùng nhiều, cân nhắc đổi sang dịch vụ email
> chuyên dụng (SendGrid, Resend, Mailgun...) có hạn mức cao hơn.

## 2c. Danh sách khách hàng + khoá email/SĐT nghi ngờ (Google Sheets)

Mỗi lần khách bấm "Ghép PDF" (không tính "Xem trước"), hệ thống tự động ghi
nhận **email + số điện thoại + số lần đã dùng** vào 1 Google Sheet — bạn mở
lên xem như bảng tính Excel bình thường, và có thể **khoá** bất kỳ ai (tô
`TRUE` vào cột "Bị khoá") nếu nghi ngờ là đối thủ dùng thử liên tục.

**Bước 1 — Tạo Google Sheet:**

1. Tạo 1 Google Sheet mới, đặt tên bất kỳ (ví dụ "Khách hàng Ghép PDF")
2. Ở dòng 1 (hàng tiêu đề), gõ đúng 6 cột theo thứ tự:
   ```
   Email | Số điện thoại | Số lần ghép | Lần đầu dùng | Lần cuối dùng | Bị khoá
   ```
3. Copy lại **ID của Sheet** — nằm trong đường link, giữa `/d/` và `/edit`:
   ```
   https://docs.google.com/spreadsheets/d/ĐÂY_LÀ_SHEET_ID/edit
   ```

**Bước 2 — Tạo Service Account (tài khoản máy để backend tự động đọc/ghi sheet):**

1. Vào **console.cloud.google.com** (dùng chung tài khoản Gmail đã có)
2. Tạo 1 Project mới (hoặc dùng project có sẵn), đặt tên bất kỳ
3. Vào **APIs & Services → Library**, tìm **"Google Sheets API"** → bấm **Enable**
4. Vào **APIs & Services → Credentials** → **Create Credentials → Service Account**
5. Đặt tên bất kỳ (ví dụ "ghep-pdf-sheet-bot") → **Create and Continue** → **Done**
   (bỏ qua phần cấp quyền, không cần thiết)
6. Trong danh sách Service Account vừa tạo, bấm vào nó → tab **Keys** → **Add
   Key → Create new key** → chọn **JSON** → tải file JSON về máy (chỉ tải
   được 1 lần, giữ cẩn thận)
7. Mở file JSON vừa tải bằng Notepad, tìm dòng `"client_email"` — copy đúng
   địa chỉ email dạng `...@...iam.gserviceaccount.com`

**Bước 3 — Chia sẻ Sheet cho Service Account:**

1. Quay lại Google Sheet đã tạo ở Bước 1 → bấm **Share** (Chia sẻ)
2. Dán đúng email Service Account vừa copy vào, chọn quyền **Editor** → Send/Share

**Bước 4 — Cấu hình trên Render.com:**

1. Vào Render → service backend → tab **Environment**
2. Thêm biến `GOOGLE_SHEET_ID` = ID sheet đã copy ở Bước 1
3. Thêm biến `GOOGLE_SHEETS_CREDENTIALS_JSON` = **toàn bộ nội dung** file JSON
   tải về ở Bước 2 (mở file bằng Notepad, chọn hết, copy, dán nguyên vào ô
   giá trị trên Render)
4. Bấm **Save Changes**

**Cách khoá 1 khách hàng:** mở Google Sheet, tìm đúng dòng của khách đó, gõ
`TRUE` vào cột "Bị khoá" — có hiệu lực ngay từ lần ghép tiếp theo, không cần
deploy lại gì cả. Gõ lại thành `FALSE` (hoặc xoá trống) để mở khoá.

**Nếu chưa cấu hình đủ 2 biến trên**: server sẽ từ chối tất cả yêu cầu ghép
PDF với lỗi rõ ràng (503 - chưa cấu hình Google Sheets).

> Lưu ý: hiện tại tính năng 2b/2c (email + Google Sheets) đã được **tạm ẩn**
> (không bắt buộc dùng) theo yêu cầu trước đó — code vẫn còn trong repo, sẵn
> sàng bật lại khi cần. Nếu bạn không dùng 2 mục trên, có thể bỏ qua.

## 2d. Mật khẩu tải file (cố định, tự đổi khi cần)

Mỗi lần bấm "Ghép PDF" (không tính "Xem trước"), khách phải nhập đúng **1 mật
khẩu chung** mới tải được file — khác với mục 2c (mỗi khách 1 mã riêng), đây
chỉ là **1 mật khẩu duy nhất dùng chung cho tất cả**, đơn giản hơn nhiều.

**Cách cấu hình:**

1. Vào Render → service backend → tab **Environment**
2. Thêm biến `DOWNLOAD_PASSWORD` = mật khẩu bạn muốn dùng (ví dụ `Badinh2026`)
3. **Save Changes** — Render tự khởi động lại, mật khẩu mới có hiệu lực ngay

**Đổi mật khẩu sau này:** quay lại đúng chỗ trên, sửa lại giá trị biến
`DOWNLOAD_PASSWORD`, Save — không cần sửa code, không cần deploy lại thủ công.

**Nếu chưa cấu hình `DOWNLOAD_PASSWORD`**: server từ chối toàn bộ yêu cầu ghép
PDF (503 - an toàn mặc định, tránh quên cấu hình mà vô tình mở public).

## 3. Deploy frontend lên GitHub Pages

> ⚠️ **Lỗi 404 thường gặp**: GitHub Pages kiểu "Deploy from a branch" chỉ cho chọn
> thư mục `/ (root)` hoặc `/docs`, **không có tuỳ chọn `/frontend`**. Vì file
> `index.html` nằm trong `frontend/`, nếu chọn `/ (root)` GitHub sẽ không tìm
> thấy file và báo 404. Cách đúng là dùng **GitHub Actions** (đã có sẵn workflow
> trong repo này) — nó tự đóng gói đúng thư mục `frontend/` rồi deploy, không
> quan trọng nó nằm ở thư mục con nào.

1. Mở `frontend/config.js`, đổi `BACKEND_URL` thành URL backend thật đã deploy ở
   bước 2 (ví dụ `https://ghep-pdf-api.onrender.com`).
2. Đẩy toàn bộ code lên GitHub (bao gồm cả thư mục `.github/workflows/`).
3. Vào **Settings → Pages** của repo:
   - Mục **Build and deployment → Source**: chọn **"GitHub Actions"**
     (không chọn "Deploy from a branch").
4. Vào tab **Actions** của repo — workflow "Deploy frontend to GitHub Pages" sẽ
   tự chạy (do đã push code). Nếu chưa thấy chạy, bấm vào workflow đó → **"Run workflow"**
   để chạy thủ công lần đầu.
5. Sau khi workflow chạy xong (dấu ✅ xanh), quay lại **Settings → Pages** sẽ thấy
   URL dạng `https://<ten-user>.github.io/<ten-repo>/` — đó là trang thật.
6. Từ lần sau, cứ push thay đổi vào thư mục `frontend/` là workflow tự chạy lại
   và cập nhật trang.

### Nếu không muốn dùng GitHub Actions

Cách khác đơn giản hơn nhưng phải đổi cấu trúc thư mục: tạo 1 nhánh riêng tên
`gh-pages`, copy toàn bộ **nội dung bên trong** `frontend/` (không phải cả thư
mục `frontend`) ra thư mục gốc của nhánh đó, rồi ở **Settings → Pages → Source**
chọn "Deploy from a branch" → branch `gh-pages` → folder `/ (root)`.

### Nếu muốn deploy frontend qua Vercel/Netlify thay vì GitHub Pages

Cũng được — vì đây chỉ là HTML/CSS/JS tĩnh, không cần build step. Chỉ cần trỏ
"Root Directory" của Vercel/Netlify vào thư mục `frontend/` (2 dịch vụ này cho
chọn thư mục con trực tiếp, không bị giới hạn như GitHub Pages kiểu branch).

## 3b. Thống kê lượt truy cập + khu vực khách hàng (Google Analytics)

Trang web đã có sẵn đoạn mã Google Analytics (GA4) trong `frontend/index.html`
— chỉ cần bạn thay đúng **Measurement ID** của mình vào là bắt đầu ghi nhận số
liệu.

**Bước 1 — Tạo tài khoản/thuộc tính Google Analytics:**

1. Vào **analytics.google.com** (dùng chung tài khoản Gmail đã có)
2. Tạo **Account** mới (nếu chưa có) → đặt tên bất kỳ, ví dụ "In Nhanh Ba Đình"
3. Tạo **Property** mới → đặt tên "Ghép PDF Web" → chọn múi giờ Việt Nam
4. Ở bước "Data collection" → chọn nền tảng **Web**
5. Nhập URL trang web thật của bạn (ví dụ `https://innhanhbadinh.github.io/binhtem/`)
6. Google sẽ cấp cho bạn 1 **Measurement ID** dạng `G-XXXXXXXXXX` — copy lại

**Bước 2 — Dán vào code:**

Mở file `frontend/index.html`, tìm 2 chỗ có chữ `G-XXXXXXXXXX` (nằm ngay đầu
file, trong thẻ `<head>`), thay cả 2 chỗ bằng đúng Measurement ID vừa copy.
Lưu, commit, đợi deploy lại.

**Bước 3 — Xem thống kê:**

Sau khi có khách truy cập thật (có thể mất vài giờ mới lên đủ dữ liệu), vào lại
analytics.google.com → chọn đúng Property → xem các mục:

- **Báo cáo → Thời gian thực (Realtime)**: xem ai đang truy cập ngay lúc này
- **Báo cáo → Vòng đời → Thu hút người dùng (Acquisition)**: tổng số lượt truy cập theo thời gian
- **Báo cáo → Người dùng → Thông tin nhân khẩu học (Demographics) → Khu vực (Geographic details)**:
  xem khách truy cập đến từ tỉnh/thành nào, quốc gia nào

> Miễn phí hoàn toàn, không giới hạn số lượt truy cập cho quy mô 1 trang web nhỏ
> như thế này.

## 4. Bảo mật CORS (khuyến nghị khi lên production)

`backend/app/main.py` hiện đang cho phép **mọi origin** gọi API (`allow_origins=["*"]`)
để dễ test. Khi đã có URL frontend thật, nên sửa lại thành danh sách cụ thể:

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["https://<ten-user>.github.io"],
    ...
)
```

## Lưu ý về "Hình dạng bất kỳ"

- Để chính xác nhất, file PDF nguồn nên có đường die-line vẽ bằng **vector**
  (nét riêng, ví dụ spot color "CutContour"). Nếu không có, backend sẽ tự nhận
  diện theo ảnh raster (kém chính xác hơn).
- Bật "xoay 90°/180°/270°" giúp ghép khít hơn, nhưng với hình bất đối xứng cao
  (logo có chữ) nên tải file kết quả về kiểm tra trước khi in hàng loạt.
- Số lượng hình lớn (>500/trang) sẽ xử lý chậm hơn trên gói free của Render —
  cân nhắc dùng "Xếp thẳng hàng theo lưới" thay vì ghép khít tự do nếu cần
  nhanh hơn.
