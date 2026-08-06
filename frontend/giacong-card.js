/**
 * renderGiaCongCard(container, options)
 *
 * Component doc lap, khong phu thuoc framework nao.
 *
 * options:
 *   autoText     {string}   Phan noi dung TU SINH (ten file, chat lieu, so luong,
 *                            gia cong...). Dung "\n" de xuong dong.
 *   note         {string}   Ghi chu ban dau - vi du ten hang/ten khach hang
 *                            (mac dinh: ""). Ghi chu se duoc GHEP TRUC TIEP len
 *                            tren autoText trong phan hien thi (khong chi luc copy).
 *   printByTo    {boolean}  Trang thai checkbox "In theo tờ" ban dau (mac dinh: false)
 *   onNoteChange {function(note)}  Goi moi khi nguoi dung go ghi chu (tuy chon)
 *   onCopy       {function(fullText)} Goi sau khi copy thanh cong (tuy chon)
 *
 * Tra ve 1 object dieu khien:
 *   { getNote(), setNote(text), setAutoText(text), getFullText(), copy() }
 */
function renderGiaCongCard(container, options) {
  const opts = Object.assign(
    {
      autoText: "",
      note: "",
      printByTo: false,
      onNoteChange: null,
      onCopy: null,
    },
    options || {}
  );

  container.innerHTML = "";

  const card = document.createElement("div");
  card.className = "giacong-card";

  card.innerHTML = `
    <div class="giacong-header">
      <span class="giacong-title">Lệnh sản xuất</span>
      <label class="giacong-checkbox">
        <input type="checkbox" class="giacong-print-checkbox" ${opts.printByTo ? "checked" : ""} />
        In theo tờ
      </label>
    </div>
    <div class="giacong-body">
      <div class="giacong-text-row">
        <p class="giacong-text"></p>
        <button type="button" class="giacong-copy-btn" title="Sao chép nội dung gia công">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <rect x="9" y="9" width="13" height="13" rx="2"></rect>
            <path d="M5 15H4a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2h9a2 2 0 0 1 2 2v1"></path>
          </svg>
          <span class="giacong-copy-toast">Đã copy!</span>
        </button>
      </div>
      <div class="giacong-note-section">
        <label class="giacong-note-label">Tên hàng / Tên khách hàng</label>
        <textarea class="giacong-note-input" placeholder="Ví dụ: Tem hoa quả - Chị Lan"></textarea>
      </div>
    </div>
  `;

  container.appendChild(card);

  const textEl = card.querySelector(".giacong-text");
  const noteInput = card.querySelector(".giacong-note-input");
  const copyBtn = card.querySelector(".giacong-copy-btn");
  const copyToast = card.querySelector(".giacong-copy-toast");

  noteInput.value = opts.note;

  // Dung textContent (khong phai innerHTML) de tranh nguy co injection vi
  // noi dung lay tu du lieu don hang / nguoi dung tu go.
  function updateDisplay() {
    const note = noteInput.value.trim();
    textEl.textContent = note ? `${note}\n${opts.autoText}` : opts.autoText;
  }

  updateDisplay();

  noteInput.addEventListener("input", () => {
    updateDisplay();
    if (typeof opts.onNoteChange === "function") {
      opts.onNoteChange(noteInput.value);
    }
  });

  function getFullText() {
    return textEl.textContent;
  }

  async function doCopy() {
    const fullText = getFullText();
    try {
      await navigator.clipboard.writeText(fullText);
    } catch (err) {
      // Fallback cho trinh duyet/moi truong khong ho tro Clipboard API truc tiep
      const ta = document.createElement("textarea");
      ta.value = fullText;
      ta.style.position = "fixed";
      ta.style.opacity = "0";
      document.body.appendChild(ta);
      ta.select();
      document.execCommand("copy");
      document.body.removeChild(ta);
    }

    copyToast.classList.add("show");
    setTimeout(() => copyToast.classList.remove("show"), 1400);

    if (typeof opts.onCopy === "function") {
      opts.onCopy(fullText);
    }
  }

  copyBtn.addEventListener("click", doCopy);

  return {
    getNote: () => noteInput.value,
    setNote: (text) => {
      noteInput.value = text;
      updateDisplay();
    },
    setAutoText: (text) => {
      opts.autoText = text;
      updateDisplay();
    },
    getFullText,
    copy: doCopy,
  };
}
