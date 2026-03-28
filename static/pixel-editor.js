/**
 * 8×8 pixel art editor (shared: profile avatar + compose attachment).
 */
(function () {
  const SIZE = 8;
  const SCALE = 32;

  const modal = document.getElementById("pixel-editor-modal");
  const canvas = document.getElementById("pixel-editor-canvas");
  const colorInput = document.getElementById("pixel-editor-color");
  const btnPen = document.getElementById("pixel-editor-tool-pen");
  const btnEraser = document.getElementById("pixel-editor-tool-eraser");
  const btnClear = document.getElementById("pixel-editor-clear");
  const btnSave = document.getElementById("pixel-editor-save");
  const btnCancel = document.getElementById("pixel-editor-cancel");
  const avatarForm = document.getElementById("avatar-upload-form");
  const avatarFileInput = document.getElementById("avatar-file-input");

  if (!modal || !canvas || !colorInput) {
    return;
  }

  const ctx = canvas.getContext("2d");
  /** Active 8×8 RGBA buffer (what you paint on). */
  const data = new Uint8ClampedArray(SIZE * SIZE * 4);
  /** Separate draft for “Draw 8×8” in compose — not shared with avatar edits. */
  const composeBuffer = new Uint8ClampedArray(SIZE * SIZE * 4);
  let tool = "pen";
  let saveTarget = "avatar";
  let drawing = false;

  canvas.width = SIZE * SCALE;
  canvas.height = SIZE * SCALE;
  ctx.imageSmoothingEnabled = false;

  function idx(x, y) {
    return (y * SIZE + x) * 4;
  }

  function clearAll() {
    data.fill(0);
    render();
  }

  function render() {
    ctx.clearRect(0, 0, canvas.width, canvas.height);
    for (let y = 0; y < SIZE; y += 1) {
      for (let x = 0; x < SIZE; x += 1) {
        const i = idx(x, y);
        const r = data[i];
        const g = data[i + 1];
        const b = data[i + 2];
        const a = data[i + 3] / 255;
        ctx.fillStyle = `rgba(${r},${g},${b},${a})`;
        ctx.fillRect(x * SCALE, y * SCALE, SCALE, SCALE);
      }
    }
    ctx.strokeStyle = "rgba(127,127,127,0.35)";
    ctx.lineWidth = 1;
    for (let g = 1; g < SIZE; g += 1) {
      ctx.beginPath();
      ctx.moveTo(g * SCALE, 0);
      ctx.lineTo(g * SCALE, canvas.height);
      ctx.stroke();
      ctx.beginPath();
      ctx.moveTo(0, g * SCALE);
      ctx.lineTo(canvas.width, g * SCALE);
      ctx.stroke();
    }
  }

  function setPixel(x, y, r, g, b, a) {
    const i = idx(x, y);
    data[i] = r;
    data[i + 1] = g;
    data[i + 2] = b;
    data[i + 3] = a;
  }

  function paintAtCell(x, y) {
    if (tool === "eraser") {
      setPixel(x, y, 0, 0, 0, 0);
    } else {
      const hex = colorInput.value;
      const r = parseInt(hex.slice(1, 3), 16);
      const g = parseInt(hex.slice(3, 5), 16);
      const b = parseInt(hex.slice(5, 7), 16);
      setPixel(x, y, r, g, b, 255);
    }
    render();
  }

  function eventToCell(ev) {
    const rect = canvas.getBoundingClientRect();
    const rx = ((ev.clientX - rect.left) / rect.width) * canvas.width;
    const ry = ((ev.clientY - rect.top) / rect.height) * canvas.height;
    let x = Math.floor(rx / SCALE);
    let y = Math.floor(ry / SCALE);
    x = Math.max(0, Math.min(SIZE - 1, x));
    y = Math.max(0, Math.min(SIZE - 1, y));
    return { x, y };
  }

  function onPointerDown(ev) {
    ev.preventDefault();
    drawing = true;
    canvas.setPointerCapture(ev.pointerId);
    const { x, y } = eventToCell(ev);
    paintAtCell(x, y);
  }

  function onPointerMove(ev) {
    if (!drawing) {
      return;
    }
    ev.preventDefault();
    const { x, y } = eventToCell(ev);
    paintAtCell(x, y);
  }

  function onPointerUp(ev) {
    if (!drawing) {
      return;
    }
    drawing = false;
    try {
      canvas.releasePointerCapture(ev.pointerId);
    } catch (_) {
      /* ignore */
    }
  }

  canvas.addEventListener("pointerdown", onPointerDown);
  canvas.addEventListener("pointermove", onPointerMove);
  canvas.addEventListener("pointerup", onPointerUp);
  canvas.addEventListener("pointercancel", onPointerUp);

  function setTool(next) {
    tool = next;
    if (btnPen && btnEraser) {
      btnPen.classList.toggle("is-active", tool === "pen");
      btnEraser.classList.toggle("is-active", tool === "eraser");
    }
  }

  if (btnPen) {
    btnPen.addEventListener("click", () => setTool("pen"));
  }
  if (btnEraser) {
    btnEraser.addEventListener("click", () => setTool("eraser"));
  }
  if (btnClear) {
    btnClear.addEventListener("click", () => clearAll());
  }

  function exportPngBlob() {
    return new Promise((resolve, reject) => {
      const out = document.createElement("canvas");
      out.width = SIZE;
      out.height = SIZE;
      const octx = out.getContext("2d");
      const imgData = new ImageData(new Uint8ClampedArray(data), SIZE, SIZE);
      octx.putImageData(imgData, 0, 0);
      out.toBlob(
        (blob) => {
          if (!blob) {
            reject(new Error("Could not export PNG"));
            return;
          }
          resolve(blob);
        },
        "image/png",
        1
      );
    });
  }

  function openModal() {
    modal.hidden = false;
    setTool("pen");
  }

  function closeModal() {
    if (saveTarget === "compose") {
      composeBuffer.set(data);
    }
    modal.hidden = true;
    drawing = false;
  }

  const scratch8 = document.createElement("canvas");
  scratch8.width = SIZE;
  scratch8.height = SIZE;

  function getAvatarImageUrl() {
    const btn = document.getElementById("open-avatar-pixel-editor");
    const fromBtn = btn && btn.dataset && btn.dataset.avatarSrc;
    if (fromBtn && String(fromBtn).trim()) {
      return String(fromBtn).trim();
    }
    const img = document.querySelector(".sidebar-avatar-img");
    return img && img.src ? img.src : null;
  }

  /**
   * Decodes current profile image into `data` (nearest-neighbor to 8×8).
   * No image / load error → transparent canvas.
   */
  function loadCurrentAvatarIntoData() {
    return new Promise((resolve) => {
      const url = getAvatarImageUrl();
      if (!url) {
        clearAll();
        resolve();
        return;
      }
      const img = new Image();
      img.onload = () => {
        try {
          const tctx = scratch8.getContext("2d");
          tctx.imageSmoothingEnabled = false;
          tctx.clearRect(0, 0, SIZE, SIZE);
          tctx.drawImage(img, 0, 0, SIZE, SIZE);
          const imageData = tctx.getImageData(0, 0, SIZE, SIZE);
          data.set(imageData.data);
          render();
        } catch (_) {
          clearAll();
        }
        resolve();
      };
      img.onerror = () => {
        clearAll();
        resolve();
      };
      img.decoding = "async";
      img.src = url;
    });
  }

  window.openPixelEditor = async function (options) {
    saveTarget = options && options.target === "compose" ? "compose" : "avatar";
    if (saveTarget === "compose") {
      data.set(composeBuffer);
      render();
      openModal();
      return;
    }
    await loadCurrentAvatarIntoData();
    openModal();
  };

  if (btnCancel) {
    btnCancel.addEventListener("click", () => closeModal());
  }

  modal.addEventListener("click", (ev) => {
    if (ev.target === modal) {
      closeModal();
    }
  });

  document.addEventListener(
    "keydown",
    (ev) => {
      if (ev.key === "Escape" && !modal.hidden) {
        ev.stopPropagation();
        closeModal();
      }
    },
    true
  );

  if (btnSave) {
    btnSave.addEventListener("click", async () => {
      try {
        const blob = await exportPngBlob();
        const file = new File([blob], "pixel.png", { type: "image/png" });
        const dt = new DataTransfer();
        dt.items.add(file);

        if (saveTarget === "avatar" && avatarFileInput && avatarForm) {
          avatarFileInput.files = dt.files;
          closeModal();
          avatarForm.submit();
          return;
        }

        if (saveTarget === "compose") {
          if (typeof window.addComposeGalleryItem === "function") {
            window.addComposeGalleryItem(file);
          }
          clearAll();
          closeModal();
          return;
        }
      } catch (e) {
        window.alert("Could not save pixel image.");
      }
    });
  }

  const openAvatarBtn = document.getElementById("open-avatar-pixel-editor");
  if (openAvatarBtn) {
    openAvatarBtn.addEventListener("click", () => window.openPixelEditor({ target: "avatar" }));
  }

  const openComposeBtn = document.getElementById("open-compose-pixel-editor");
  if (openComposeBtn) {
    openComposeBtn.addEventListener("click", () => window.openPixelEditor({ target: "compose" }));
  }
})();
