import "https://cdn.jsdelivr.net/npm/emoji-picker-element@^1/index.js";

function insertTextAtCaret(textarea, insertText) {
  const max = textarea.maxLength > 0 ? textarea.maxLength : Number.POSITIVE_INFINITY;
  const start = textarea.selectionStart;
  const end = textarea.selectionEnd;
  const before = textarea.value.slice(0, start);
  const after = textarea.value.slice(end);
  const room = max - before.length - after.length;
  if (room <= 0) {
    return;
  }
  let chunk = insertText;
  if (chunk.length > room) {
    chunk = chunk.slice(0, room);
  }
  const next = before + chunk + after;
  textarea.value = next;
  const caret = start + chunk.length;
  textarea.selectionStart = textarea.selectionEnd = caret;
  textarea.dispatchEvent(new Event("input", { bubbles: true }));
}

function setEmojiWcOpen(open) {
  const popover = document.getElementById("emoji-wc-popover");
  const toggle = document.getElementById("emoji-wc-toggle");
  if (!popover || !toggle) {
    return;
  }
  popover.hidden = !open;
  toggle.setAttribute("aria-expanded", open ? "true" : "false");
}

function syncEmojiPickerTheme(picker) {
  if (!picker) {
    return;
  }
  const dark = document.documentElement.classList.contains("dark-mode");
  picker.classList.toggle("dark", dark);
  picker.classList.toggle("light", !dark);
}

function initEmojiWc() {
  const picker = document.getElementById("emoji-wc-picker");
  const contentInput = document.getElementById("content");
  const wcToggle = document.getElementById("emoji-wc-toggle");
  const popover = document.getElementById("emoji-wc-popover");
  if (!picker || !contentInput || !wcToggle || !popover || popover.dataset.wcInit === "1") {
    return;
  }
  popover.dataset.wcInit = "1";

  syncEmojiPickerTheme(picker);
  const mo = new MutationObserver(() => syncEmojiPickerTheme(picker));
  mo.observe(document.documentElement, { attributes: true, attributeFilter: ["class"] });

  picker.addEventListener("emoji-click", (event) => {
    const unicode = event.detail?.unicode;
    if (typeof unicode !== "string" || !unicode) {
      return;
    }
    contentInput.focus();
    insertTextAtCaret(contentInput, unicode);
  });

  wcToggle.addEventListener("click", (event) => {
    event.stopPropagation();
    const open = popover.hidden;
    setEmojiWcOpen(open);
  });

  popover.addEventListener("click", (event) => {
    event.stopPropagation();
  });
}

customElements.whenDefined("emoji-picker").then(() => {
  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initEmojiWc, { once: true });
  } else {
    initEmojiWc();
  }
});

window.closeEmojiWcPopover = () => setEmojiWcOpen(false);
