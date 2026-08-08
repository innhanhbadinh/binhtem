const shapeHints = {
  rect: "Ghép thẳng",
  circle: "Ghép kiểu tổ ong (so le) — tối ưu hơn ghép vuông thông thường.",
  ellipse: "Ghép lưới elip, có thể xoay để chọn ghép sát nhất.",
  custom: "Tự đọc đường bế từ file PDF và ghép sát bằng thuật toán nesting.",
};

let currentShape = "rect";

const shapeToggle = document.getElementById("shapeToggle");
const shapeHint = document.getElementById("shapeHint");
const ellipseRow = document.getElementById("ellipseRow");
const bleedRow = document.getElementById("bleedRow");
const bleedMmRow = document.getElementById("bleedMmRow");
const rotationRow = document.getElementById("rotationRow");
const gridRow = document.getElementById("gridRow");
const bleedOn = document.getElementById("bleedOn");

const dropzone = document.getElementById("dropzone");

const sampleGuideToggle = document.getElementById("sampleGuideToggle");
const sampleGuidePanel = document.getElementById("sampleGuidePanel");
sampleGuideToggle.addEventListener("click", () => {
  const isHidden = sampleGuidePanel.style.display === "none";
  sampleGuidePanel.style.display = isHidden ? "block" : "none";
  sampleGuideToggle.textContent = isHidden
    ? "📄 Ẩn hướng dẫn chuẩn bị file PDF mẫu"
    : "📄 Xem hướng dẫn chuẩn bị file PDF mẫu";
});
const fileInput = document.getElementById("fileInput");
const dropFilename = document.getElementById("dropFilename");
const dropHint = document.getElementById("dropHint");

const submitBtn = document.getElementById("submitBtn");
const errorText = document.getElementById("errorText");
const resultStatus = document.getElementById("resultStatus");
const coldStartNote = document.getElementById("coldStartNote");
const downloadLink = document.getElementById("downloadLink");
const backendUrlText = document.getElementById("backendUrlText");

backendUrlText.textContent = BACKEND_URL;

// ===== Kho giay co san (danh cho khach hang de chon, khong can nho kich thuoc) =====
// Don vi nhap vao day la CENTIMET (giong quy uoc noi bo cua xuong) - se tu doi
// sang MM khi dien vao o Rong/Cao. Neu can them/sua khong, chi sua trong mang nay.
const PAPER_PRESETS = [
  {
    group: "Decal giấy Oji",
    items: [
      { name: "Decal giấy Oji", w: 32, h: 40 },
      { name: "Decal giấy Oji", w: 32, h: 43 },
      { name: "Decal giấy Oji", w: 33, h: 45 },
      { name: "Decal giấy Oji", w: 33, h: 48 },
    ],
  },
  {
    group: "Decal khổ 32x43",
    items: [
      { name: "Decal đế nhám", w: 32, h: 43 },
      { name: "Amazon chấm đỏ", w: 32, h: 43 },
      { name: "Amazon chấm xanh", w: 32, h: 43 },
      { name: "Decal Fasson", w: 32, h: 43 },
      { name: "Decal Kraft", w: 32, h: 43 },
      { name: "Decal nhựa", w: 32, h: 43 },
      { name: "Decal PP", w: 32, h: 43 },
      { name: "Decal 7 màu", w: 32, h: 43 },
    ],
  },
  {
    group: "Khổ khác",
    items: [
      { name: "Decal Trong", w: 32, h: 48 },
      { name: "Decal Gương", w: 26.5, h: 48 },
      { name: "Vỡ dẻo", w: 26.5, h: 48 },
      { name: "Vỡ giòn", w: 26.5, h: 48 },
      { name: "Vỡ KoanHao", w: 26.5, h: 48 },
      { name: "Decal Bạc", w: 26.5, h: 48 },
      { name: "Gương vàng", w: 26.5, h: 48 },
    ],
  },
];

const paperPresetSelect = document.getElementById("paperPreset");
const paperWInput = document.getElementById("paperW");
const paperHInput = document.getElementById("paperH");

PAPER_PRESETS.forEach((group) => {
  const optgroup = document.createElement("optgroup");
  optgroup.label = group.group;
  group.items.forEach((item) => {
    const opt = document.createElement("option");
    // Luu kich thuoc (cm) ngay trong value, dang "w,h", de doc lai khi chon
    opt.value = `${item.w},${item.h}`;
    opt.textContent = `${item.name} — ${item.w}x${item.h}cm`;
    opt.dataset.materialName = item.name;
    optgroup.appendChild(opt);
  });
  paperPresetSelect.appendChild(optgroup);
});

// Ten chat lieu giay dang chon (null neu khach tu nhap kho giay, khong qua preset)
let selectedMaterialName = null;

paperPresetSelect.addEventListener("change", () => {
  if (!paperPresetSelect.value) {
    selectedMaterialName = null;
    return;
  }
  const [wCm, hCm] = paperPresetSelect.value.split(",").map(Number);
  paperWInput.value = Math.round(wCm * 10); // cm -> mm
  paperHInput.value = Math.round(hCm * 10);
  const selectedOption = paperPresetSelect.selectedOptions[0];
  selectedMaterialName = selectedOption ? selectedOption.dataset.materialName : null;
  scheduleAutoPreview(0);
  updateGiacongIfVisible();
});

// Neu khach tu sua tay Rong/Cao sau khi da chon 1 khổ co san, dua dropdown ve
// "Tu nhap kho giay" de tranh hieu lam la van dang dung dung khổ co san do.
[paperWInput, paperHInput].forEach((el) => {
  el.addEventListener("input", () => {
    paperPresetSelect.value = "";
    selectedMaterialName = null;
    updateGiacongIfVisible();
  });
});

let selectedFile = null;

function updateVisibleFields() {
  ellipseRow.style.display = currentShape === "ellipse" ? "grid" : "none";
  const supportsBleed = currentShape === "rect" || currentShape === "circle";
  bleedRow.style.display = supportsBleed ? "block" : "none";
  bleedMmRow.style.display = supportsBleed && bleedOn.checked ? "block" : "none";
  rotationRow.style.display = (currentShape === "ellipse" || currentShape === "custom") ? "flex" : "none";
  gridRow.style.display = currentShape === "custom" ? "block" : "none";
  shapeHint.textContent = shapeHints[currentShape];
}

shapeToggle.addEventListener("click", (e) => {
  const btn = e.target.closest(".shape-btn");
  if (!btn) return;
  document.querySelectorAll(".shape-btn").forEach((b) => b.classList.remove("active"));
  btn.classList.add("active");
  currentShape = btn.dataset.shape;
  updateVisibleFields();
});

bleedOn.addEventListener("change", updateVisibleFields);

updateVisibleFields();

function setFile(file) {
  if (!file) return;
  if (!file.name.toLowerCase().endsWith(".pdf")) {
    errorText.textContent = "Chỉ chấp nhận file .pdf";
    return;
  }
  errorText.textContent = "";
  selectedFile = file;
  dropFilename.textContent = file.name;
  const kb = (file.size / 1024).toFixed(0);
  dropHint.textContent = `${kb} KB — bấm để chọn file khác`;
}

dropzone.addEventListener("click", () => fileInput.click());
fileInput.addEventListener("change", (e) => setFile(e.target.files[0]));

["dragenter", "dragover"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.add("dragover");
  })
);
["dragleave", "drop"].forEach((evt) =>
  dropzone.addEventListener(evt, (e) => {
    e.preventDefault();
    dropzone.classList.remove("dragover");
  })
);
dropzone.addEventListener("drop", (e) => {
  const file = e.dataTransfer.files[0];
  setFile(file);
});

function numVal(id) {
  return parseFloat(document.getElementById(id).value);
}

/**
 * Kiem tra input hop le va dung FormData de dung chung cho ca preview lan ghep that.
 * Tra ve FormData neu hop le, hoac null neu co loi.
 * silent=true: khong ghi errorText (dung khi tu dong xem truoc, tranh lam phien
 * luc nguoi dung dang go do so lieu).
 */
function buildValidatedFormData(silent = false) {
  if (!silent) errorText.textContent = "";

  if (!selectedFile) {
    if (!silent) errorText.textContent = "Vui lòng chọn file PDF trước.";
    return null;
  }

  const paperW = numVal("paperW");
  const paperH = numVal("paperH");
  const gap = numVal("gap");

  if (!paperW || paperW <= 0 || !paperH || paperH <= 0) {
    if (!silent) errorText.textContent = "Khổ giấy phải lớn hơn 0.";
    return null;
  }

  if (currentShape === "ellipse") {
    const ew = numVal("ellipseW");
    const eh = numVal("ellipseH");
    if (!ew || ew <= 0 || !eh || eh <= 0) {
      if (!silent) errorText.textContent = "Vui lòng nhập kích thước Elip hợp lệ.";
      return null;
    }
  }

  const formData = new FormData();
  formData.append("file", selectedFile);
  formData.append("shape", currentShape);
  formData.append("paper_w", paperW);
  formData.append("paper_h", paperH);
  formData.append("gap", isNaN(gap) ? 0 : gap);

  const supportsBleed = currentShape === "rect" || currentShape === "circle";
  formData.append("bleed", supportsBleed && bleedOn.checked);
  formData.append("bleed_mm", supportsBleed && bleedOn.checked ? numVal("bleedMm") : 0);

  if (currentShape === "ellipse") {
    formData.append("ellipse_w", numVal("ellipseW"));
    formData.append("ellipse_h", numVal("ellipseH"));
  }
  if (currentShape === "ellipse" || currentShape === "custom") {
    formData.append("allow_rotation", document.getElementById("allowRotation").checked);
  }
  if (currentShape === "custom") {
    formData.append("use_grid", document.getElementById("useGrid").checked);
  }

  return formData;
}

/**
 * Tao ten file .pdf goi y tu chinh noi dung Lenh san xuat (khong tinh phan
 * Ghi chu/ten khach hang), de file tai ve de nhan biet ngay thay vi ten chung
 * chung nhu "ghep_pdf_ket_qua.pdf". Loai bo cac ky tu khong hop le trong ten
 * file (\/:*?"<>|), gioi han do dai.
 */
function buildOutputFilename() {
  const raw = buildGiacongAutoText();
  let name = raw
    .replace(/[\n\r]+/g, " - ")
    .replace(/[\\/]/g, " ")
    .replace(/[:*?"<>|]/g, "")
    .replace(/\s+/g, " ")
    .trim();
  if (!name) name = "ghep_pdf_ket_qua";
  if (name.length > 150) name = name.slice(0, 150).trim();
  return `${name}.pdf`;
}

async function submitGhep() {
  const formData = buildValidatedFormData();
  if (!formData) return;

  const downloadPassword = document.getElementById("downloadPassword").value;
  if (!downloadPassword) {
    errorText.textContent = "Vui lòng nhập mật khẩu tải file trước khi ghép.";
    return;
  }

  formData.append("filename_hint", buildOutputFilename());
  formData.append("oc_type", document.getElementById("ocTypeSelect").value);
  const insertProdText = document.getElementById("insertProductionTextOn").checked;
  formData.append("production_text", insertProdText ? buildGiacongAutoText() : "");
  formData.append("download_password", downloadPassword);

  submitBtn.disabled = true;
  previewBtn.disabled = true;
  submitBtn.textContent = "Đang ghép...";
  resultStatus.textContent = "Đang xử lý trên máy chủ...";
  coldStartNote.style.display = "block";
  downloadLink.style.display = "none";

  const coldStartTimer = setTimeout(() => {
    resultStatus.textContent = "Vẫn đang xử lý, máy chủ có thể đang khởi động lại...";
  }, 6000);

  try {
    const res = await fetch(`${BACKEND_URL}/api/ghep`, {
      method: "POST",
      body: formData,
    });

    clearTimeout(coldStartTimer);

    if (!res.ok) {
      let detail = `Lỗi ${res.status}`;
      try {
        const data = await res.json();
        if (data.detail) detail = data.detail;
      } catch (_) {}
      resultStatus.textContent = "Ghép thất bại.";
      coldStartNote.style.display = "none";
      errorText.textContent = detail;
      return;
    }

    const blob = await res.blob();
    const url = URL.createObjectURL(blob);
    downloadLink.href = url;

    const cd = res.headers.get("content-disposition") || "";
    const match = cd.match(/filename\*?=(?:UTF-8''|")?([^";\n]+)"?/i);
    downloadLink.download = match ? decodeURIComponent(match[1]) : "ghep_pdf_ket_qua.pdf";

    resultStatus.textContent = "Ghép thành công!";
    coldStartNote.style.display = "none";
    downloadLink.style.display = "inline-block";
    showGiaCongCard();
  } catch (err) {
    clearTimeout(coldStartTimer);
    resultStatus.textContent = "Không thể kết nối tới máy chủ.";
    coldStartNote.style.display = "none";
    errorText.textContent = String(err);
  } finally {
    submitBtn.disabled = false;
    previewBtn.disabled = false;
    submitBtn.textContent = "Ghép PDF";
  }
}

const giacongCardContainer = document.getElementById("giacongCardContainer");
const laminationSelect = document.getElementById("laminationSelect");
const finishingSelect = document.getElementById("finishingSelect");
let giacongControl = null;

/**
 * Doi mm sang cm, bo so 0 thua (VD 480mm -> "48", 265mm -> "26.5")
 */
/**
 * Sinh noi dung TU DONG cho the Gia cong, dung dinh dang ngan gon:
 *   "{Chat lieu} {Rong}x{Cao}mm, in {so to} tờ, Cán màng - {gia tri}, Gia công - {gia tri}"
 * Neu chua nhap "So luong can in" thi hien "{so tem} tem/tờ" thay cho "in X tờ".
 * Cac phan Cán màng / Gia công chi xuat hien neu co chon. KHONG dung ky tu
 * dac biet (mui ten, dau ->...) de tranh loi khi copy sang phan mem khac.
 * Phan ghi chu (ten hang/khach hang) duoc component tu ghep them vao phia
 * tren, khong nam trong ham nay.
 */
function buildGiacongAutoText() {
  const paperW = numVal("paperW");
  const paperH = numVal("paperH");

  // Luon ghi ro chat lieu decal theo dung khach da chon tu "Khổ giấy có sẵn";
  // neu khach tu nhap tay khong qua preset thi moi dung ten chung "Khổ giấy".
  const materialLine = selectedMaterialName
    ? `${selectedMaterialName} ${paperW}x${paperH}mm`
    : `Khổ giấy ${paperW}x${paperH}mm`;

  const parts = [materialLine];

  const perSheet = lastPreviewData && typeof lastPreviewData.count === "number"
    ? lastPreviewData.count
    : null;

  // Neu khach nhap "So luong can in", tu tinh so to can in (lam tron len) va
  // chi hien gon "in X tờ". Neu chua nhap so luong, hien tem/to de van co
  // thong tin tham khao.
  const quantityNeeded = numVal("quantityNeeded");
  if (quantityNeeded > 0 && perSheet) {
    const sheetsNeeded = Math.ceil(quantityNeeded / perSheet);
    parts.push(`in ${sheetsNeeded} tờ`);
  } else if (perSheet) {
    parts.push(`${perSheet} tem/tờ`);
  }

  if (laminationSelect.value) {
    parts.push(`Cán màng - ${laminationSelect.value}`);
  }
  if (finishingSelect.value) {
    parts.push(`Gia công - ${finishingSelect.value}`);
  }

  return parts.join(", ");
}

/**
 * Hien the "Gia cong" sau khi ghep PDF thanh cong. Neu the da ton tai tu
 * truoc (nguoi dung da go ten hang/khach hang), giu lai dung noi dung do khi
 * cap nhat lai (vi du ghep lai voi thong so khac).
 */
function showGiaCongCard() {
  const existingNote = giacongControl ? giacongControl.getNote() : "";
  hasMergedOnce = true;

  giacongControl = renderGiaCongCard(giacongCardContainer, {
    autoText: buildGiacongAutoText(),
    note: existingNote,
  });
}

/**
 * Cap nhat lai phan tu sinh cua the Gia cong NEU da tung ghep thanh cong it
 * nhat 1 lan - giu cho thong tin luon dung ngay ca khi khach doi thong so sau
 * khi the da hien ra, khong can ghep lai moi thay duoc. Truoc khi ghep lan
 * dau, the chi hien placeholder va KHONG tu dien so lieu (chi dien khi bam
 * "Ghep PDF" nhu yeu cau).
 */
function updateGiacongIfVisible() {
  if (giacongControl && hasMergedOnce) {
    giacongControl.setAutoText(buildGiacongAutoText());
  }
}

[laminationSelect, finishingSelect].forEach((el) => {
  el.addEventListener("change", updateGiacongIfVisible);
});
document.getElementById("quantityNeeded").addEventListener("input", updateGiacongIfVisible);

// Hien san the Gia cong ngay khi tai trang (chi voi noi dung cho san), cac
// thong so thuc te chi duoc tu dong dien vao SAU KHI bam "Ghep PDF" thanh cong.
let hasMergedOnce = false;
giacongControl = renderGiaCongCard(giacongCardContainer, {
  autoText: 'Chưa có thông tin — bấm "Ghép PDF" để tự động điền vào đây.',
  note: "",
});


submitBtn.addEventListener("click", submitGhep);

const previewBtn = document.getElementById("previewBtn");
const previewCard = document.getElementById("previewCard");
const previewCount = document.getElementById("previewCount");
const previewSvg = document.getElementById("previewSvg");

const SVG_NS = "http://www.w3.org/2000/svg";

let lastPreviewData = null;

function renderPreview(data) {
  lastPreviewData = data;
  previewSvg.innerHTML = "";
  previewSvg.setAttribute("viewBox", `0 0 ${data.paper_w_mm} ${data.paper_h_mm}`);

  const outline = document.createElementNS(SVG_NS, "rect");
  outline.setAttribute("x", 0);
  outline.setAttribute("y", 0);
  outline.setAttribute("width", data.paper_w_mm);
  outline.setAttribute("height", data.paper_h_mm);
  outline.setAttribute("class", "paper-outline");
  previewSvg.appendChild(outline);

  for (const piece of data.pieces) {
    let el;
    if (piece.type === "rect") {
      el = document.createElementNS(SVG_NS, "rect");
      el.setAttribute("x", piece.x_mm);
      el.setAttribute("y", piece.y_mm);
      el.setAttribute("width", piece.w_mm);
      el.setAttribute("height", piece.h_mm);
    } else if (piece.type === "circle") {
      el = document.createElementNS(SVG_NS, "circle");
      el.setAttribute("cx", piece.cx_mm);
      el.setAttribute("cy", piece.cy_mm);
      el.setAttribute("r", piece.r_mm);
    } else if (piece.type === "ellipse") {
      el = document.createElementNS(SVG_NS, "ellipse");
      el.setAttribute("cx", piece.x_mm + piece.w_mm / 2);
      el.setAttribute("cy", piece.y_mm + piece.h_mm / 2);
      el.setAttribute("rx", piece.w_mm / 2);
      el.setAttribute("ry", piece.h_mm / 2);
    } else if (piece.type === "polygon") {
      el = document.createElementNS(SVG_NS, "polygon");
      el.setAttribute("points", piece.points_mm.map((p) => `${p[0]},${p[1]}`).join(" "));
    }
    if (el) {
      el.setAttribute("class", "piece");
      previewSvg.appendChild(el);
    }
  }

  previewCount.textContent = `Số lượng ghép được: ${data.count}`;
  previewCard.style.display = "block";
}

async function submitPreview() {
  const formData = buildValidatedFormData();
  if (!formData) return;

  previewBtn.disabled = true;
  submitBtn.disabled = true;
  previewBtn.textContent = "Đang tính...";
  resultStatus.textContent = "Đang tính toán layout xem trước...";
  coldStartNote.style.display = "block";

  const coldStartTimer = setTimeout(() => {
    resultStatus.textContent = "Vẫn đang xử lý, máy chủ có thể đang khởi động lại...";
  }, 6000);

  try {
    const res = await fetch(`${BACKEND_URL}/api/preview`, {
      method: "POST",
      body: formData,
    });

    clearTimeout(coldStartTimer);
    coldStartNote.style.display = "none";

    if (!res.ok) {
      let detail = `Lỗi ${res.status}`;
      try {
        const data = await res.json();
        if (data.detail) detail = data.detail;
      } catch (_) {}
      resultStatus.textContent = "Chưa có file nào được ghép.";
      errorText.textContent = detail;
      previewCard.style.display = "none";
      return;
    }

    const data = await res.json();
    renderPreview(data);
    resultStatus.textContent = "Chưa có file nào được ghép.";
  } catch (err) {
    resultStatus.textContent = "Chưa có file nào được ghép.";
    errorText.textContent = String(err);
    previewCard.style.display = "none";
  } finally {
    previewBtn.disabled = false;
    submitBtn.disabled = false;
    previewBtn.textContent = "👁️ Xem trước";
  }
}

previewBtn.addEventListener("click", submitPreview);

// ===== Tu dong xem truoc (khong can bam nut) =====
// Moi khi file/kieu ghep/so lieu thay doi, tu goi lai /api/preview sau 1 khoang
// debounce ngan (tranh goi lien tuc khi dang go so). Neu co request moi hon
// dang cho, huy request cu (AbortController) de tranh ket qua cu de len sau.

let autoPreviewTimer = null;
let autoPreviewController = null;

function scheduleAutoPreview(delayMs = 450) {
  clearTimeout(autoPreviewTimer);
  autoPreviewTimer = setTimeout(runAutoPreview, delayMs);
}

async function runAutoPreview() {
  if (!selectedFile) {
    previewCard.style.display = "none";
    return;
  }

  const formData = buildValidatedFormData(true); // silent - khong bao loi khi dang go do
  if (!formData) {
    previewCard.style.display = "none";
    return;
  }

  if (autoPreviewController) {
    autoPreviewController.abort();
  }
  autoPreviewController = new AbortController();
  const { signal } = autoPreviewController;

  previewCard.style.display = "block";
  previewCount.textContent = "Đang tính toán layout...";

  try {
    const res = await fetch(`${BACKEND_URL}/api/preview`, {
      method: "POST",
      body: formData,
      signal,
    });

    if (!res.ok) {
      let detail = `Lỗi ${res.status}`;
      try {
        const data = await res.json();
        if (data.detail) detail = data.detail;
      } catch (_) {}
      previewCount.textContent = detail;
      return;
    }

    const data = await res.json();
    renderPreview(data);
  } catch (err) {
    if (err.name === "AbortError") return; // bi huy do co thay doi moi hon, bo qua yen lang
    previewCount.textContent = "Không thể kết nối máy chủ để xem trước (có thể đang khởi động lại, thử lại sau ít giây).";
  }
}

// Gan auto-preview vao moi thay doi lien quan
["paperW", "paperH", "gap", "ellipseW", "ellipseH", "bleedMm"].forEach((id) => {
  document.getElementById(id).addEventListener("input", () => {
    scheduleAutoPreview();
    updateGiacongIfVisible();
  });
});
["allowRotation", "useGrid"].forEach((id) => {
  document.getElementById(id).addEventListener("change", () => scheduleAutoPreview(0));
});
bleedOn.addEventListener("change", () => scheduleAutoPreview(0));
shapeToggle.addEventListener("click", (e) => {
  if (e.target.closest(".shape-btn")) {
    scheduleAutoPreview(0);
    updateGiacongIfVisible();
  }
});
fileInput.addEventListener("change", () => {
  scheduleAutoPreview(0);
  updateGiacongIfVisible();
});
dropzone.addEventListener("drop", () => {
  scheduleAutoPreview(0);
  updateGiacongIfVisible();
});
