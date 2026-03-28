const createPostForm = document.getElementById("create-post-form");
const contentInput = document.getElementById("content");
const composeCharCount = document.getElementById("compose-char-count");
const formMessage = document.getElementById("form-message");
const composeModal = document.getElementById("compose-modal");
const openComposeButton = document.getElementById("open-compose");
const closeComposeButton = document.getElementById("close-compose");
const themeToggleButton = document.getElementById("theme-toggle");

const THEME_KEY = "minisocial-theme";
const MAX_IMAGE_BYTES = 300 * 1024;
const MAX_GALLERY_IMAGES = 4;

const composeGalleryList = document.getElementById("compose-gallery-list");
const composeAddFile = document.getElementById("compose-add-file");
const composeAddFileBtn = document.getElementById("compose-add-file-btn");
const composeAddUrlInput = document.getElementById("compose-add-url-input");
const composeAddUrlBtn = document.getElementById("compose-add-url-btn");

/** @type {{ kind: "file" | "url", file?: File, url?: string, thumbUrl?: string }[]} */
let composeGalleryItems = [];

function clearComposeGallery() {
  composeGalleryItems.forEach((item) => {
    if (item.kind === "file" && item.thumbUrl) {
      URL.revokeObjectURL(item.thumbUrl);
    }
  });
  composeGalleryItems = [];
  if (composeGalleryList) {
    composeGalleryList.innerHTML = "";
  }
  updateComposeGalleryActionsDisabled();
}

function updateComposeGalleryActionsDisabled() {
  const full = composeGalleryItems.length >= MAX_GALLERY_IMAGES;
  if (composeAddFileBtn) {
    composeAddFileBtn.disabled = full;
  }
  if (composeAddUrlBtn) {
    composeAddUrlBtn.disabled = full;
  }
  const px = document.getElementById("open-compose-pixel-editor");
  if (px) {
    px.disabled = full;
  }
}

function renderComposeGallery() {
  if (!composeGalleryList) {
    return;
  }
  composeGalleryList.innerHTML = "";
  composeGalleryItems.forEach((item, index) => {
    const wrap = document.createElement("div");
    wrap.className = "compose-gallery-item";

    const thumb = document.createElement("div");
    thumb.className = "compose-gallery-thumb-wrap";

    const img = document.createElement("img");
    img.className = "compose-gallery-thumb";
    img.alt = "";
    if (item.kind === "file" && item.file && item.thumbUrl) {
      img.src = item.thumbUrl;
    } else if (item.kind === "url" && item.url) {
      img.src = item.url;
      img.referrerPolicy = "no-referrer";
    }
    thumb.appendChild(img);

    const cap = document.createElement("span");
    cap.className = "compose-gallery-item-cap";
    cap.textContent = item.kind === "file" ? "File" : "URL";

    const rm = document.createElement("button");
    rm.type = "button";
    rm.className = "compose-gallery-remove";
    rm.setAttribute("aria-label", "Remove image");
    rm.textContent = "×";
    rm.addEventListener("click", () => {
      if (item.kind === "file" && item.thumbUrl) {
        URL.revokeObjectURL(item.thumbUrl);
      }
      composeGalleryItems.splice(index, 1);
      renderComposeGallery();
      updateComposeGalleryActionsDisabled();
    });

    wrap.appendChild(thumb);
    wrap.appendChild(cap);
    wrap.appendChild(rm);
    composeGalleryList.appendChild(wrap);
  });
  updateComposeGalleryActionsDisabled();
}

window.addComposeGalleryItem = function (file) {
  if (!file || composeGalleryItems.length >= MAX_GALLERY_IMAGES) {
    return;
  }
  const thumbUrl = URL.createObjectURL(file);
  composeGalleryItems.push({
    kind: "file",
    file,
    thumbUrl,
  });
  renderComposeGallery();
};

function tryAddComposeGalleryUrl() {
  const raw = composeAddUrlInput ? composeAddUrlInput.value.trim() : "";
  if (!raw) {
    return;
  }
  if (composeGalleryItems.length >= MAX_GALLERY_IMAGES) {
    return;
  }
  const ok = /^https?:\/\/\S+$/i.test(raw);
  if (!ok) {
    if (formMessage) {
      formMessage.textContent = "URL must start with http:// or https://";
    }
    return;
  }
  composeGalleryItems.push({ kind: "url", url: raw });
  if (composeAddUrlInput) {
    composeAddUrlInput.value = "";
  }
  renderComposeGallery();
}

if (composeAddFileBtn && composeAddFile) {
  composeAddFileBtn.addEventListener("click", () => {
    if (composeGalleryItems.length >= MAX_GALLERY_IMAGES) {
      return;
    }
    composeAddFile.click();
  });
  composeAddFile.addEventListener("change", () => {
    const file = composeAddFile.files && composeAddFile.files[0];
    composeAddFile.value = "";
    if (!file) {
      return;
    }
    if (file.size > MAX_IMAGE_BYTES) {
      if (formMessage) {
        formMessage.textContent = `Each file must be at most ${MAX_IMAGE_BYTES / 1024} KB.`;
      }
      return;
    }
    window.addComposeGalleryItem(file);
  });
}

if (composeAddUrlBtn) {
  composeAddUrlBtn.addEventListener("click", () => tryAddComposeGalleryUrl());
}

if (composeAddUrlInput) {
  composeAddUrlInput.addEventListener("keydown", (event) => {
    if (event.key === "Enter") {
      event.preventDefault();
      tryAddComposeGalleryUrl();
    }
  });
}

updateComposeGalleryActionsDisabled();

function tryCloseEmojiWcPopover() {
  if (typeof window.closeEmojiWcPopover === "function") {
    window.closeEmojiWcPopover();
  }
}

document.addEventListener("click", (event) => {
  const wrap = document.querySelector(".compose-emoji-wrap");
  const emojiWcPopover = document.getElementById("emoji-wc-popover");
  if (emojiWcPopover && !emojiWcPopover.hidden && wrap && !wrap.contains(event.target)) {
    tryCloseEmojiWcPopover();
  }
});

function updateComposeCharCount() {
  if (!contentInput || !composeCharCount) {
    return;
  }
  const max = contentInput.maxLength > 0 ? contentInput.maxLength : 280;
  const len = contentInput.value.length;
  composeCharCount.textContent = `${len} / ${max}`;
  composeCharCount.classList.toggle("is-near-limit", len >= max - 20 && len < max);
  composeCharCount.classList.toggle("is-at-limit", len >= max);
}

function resizeComposeTextarea() {
  if (!contentInput || !contentInput.classList.contains("compose-textarea")) {
    return;
  }
  const maxHeight = Math.min(window.innerHeight * 0.5, 352);
  contentInput.style.height = "auto";
  const target = Math.min(contentInput.scrollHeight, maxHeight);
  contentInput.style.height = `${target}px`;
  contentInput.style.overflowY = contentInput.scrollHeight > maxHeight ? "auto" : "hidden";
}

function applyTheme(theme) {
  const isDark = theme === "dark";
  document.documentElement.classList.toggle("dark-mode", isDark);
  if (themeToggleButton) {
    themeToggleButton.setAttribute("aria-checked", isDark ? "true" : "false");
  }
}

const savedTheme = window.localStorage.getItem(THEME_KEY) || "light";
applyTheme(savedTheme);

if (themeToggleButton) {
  themeToggleButton.addEventListener("click", () => {
    const isDark = document.documentElement.classList.contains("dark-mode");
    const nextTheme = isDark ? "light" : "dark";
    window.localStorage.setItem(THEME_KEY, nextTheme);
    applyTheme(nextTheme);
  });
}

if (openComposeButton && composeModal) {
  openComposeButton.addEventListener("click", () => {
    composeModal.hidden = false;
    clearComposeGallery();
    tryCloseEmojiWcPopover();
    if (contentInput) {
      contentInput.focus();
      resizeComposeTextarea();
      updateComposeCharCount();
    }
  });
}

if (closeComposeButton && composeModal) {
  closeComposeButton.addEventListener("click", () => {
    composeModal.hidden = true;
    tryCloseEmojiWcPopover();
  });
}

if (composeModal) {
  composeModal.addEventListener("click", (event) => {
    if (event.target === composeModal) {
      composeModal.hidden = true;
      tryCloseEmojiWcPopover();
    }
  });
}

const imageLightbox = document.getElementById("image-lightbox");
const imageLightboxImg = document.getElementById("image-lightbox-img");
const imageLightboxPrev = document.getElementById("image-lightbox-prev");
const imageLightboxNext = document.getElementById("image-lightbox-next");
const imageLightboxClose = document.getElementById("image-lightbox-close");
const imageLightboxScrim = document.getElementById("image-lightbox-scrim");
const imageLightboxCounter = document.getElementById("image-lightbox-counter");

/** @type {{ src: string, isBlob: boolean }[] | null} */
let lightboxSlides = null;
let lightboxIndex = 0;

function closeImageLightbox() {
  if (!imageLightbox || imageLightbox.hidden) {
    return;
  }
  imageLightbox.hidden = true;
  document.body.style.overflow = "";
  lightboxSlides = null;
  lightboxIndex = 0;
  if (imageLightboxImg) {
    imageLightboxImg.removeAttribute("src");
    imageLightboxImg.classList.remove("post-image--blob");
  }
}

function showLightboxSlide() {
  if (!lightboxSlides || !imageLightboxImg) {
    return;
  }
  const slide = lightboxSlides[lightboxIndex];
  imageLightboxImg.src = slide.src;
  imageLightboxImg.classList.toggle("post-image--blob", slide.isBlob);
  if (imageLightboxCounter) {
    if (lightboxSlides.length > 1) {
      imageLightboxCounter.hidden = false;
      imageLightboxCounter.textContent = `${lightboxIndex + 1} / ${lightboxSlides.length}`;
    } else {
      imageLightboxCounter.hidden = true;
    }
  }
  if (imageLightboxPrev) {
    imageLightboxPrev.hidden = lightboxSlides.length <= 1;
  }
  if (imageLightboxNext) {
    imageLightboxNext.hidden = lightboxSlides.length <= 1;
  }
}

function openImageLightbox(slides, startIndex) {
  if (!slides.length || !imageLightbox) {
    return;
  }
  lightboxSlides = slides;
  lightboxIndex = Math.max(0, Math.min(startIndex, slides.length - 1));
  imageLightbox.hidden = false;
  document.body.style.overflow = "hidden";
  showLightboxSlide();
}

document.addEventListener("click", (event) => {
  const thumb = event.target.closest && event.target.closest(".post-gallery-img");
  if (!thumb) {
    return;
  }
  const gallery = thumb.closest(".post-gallery");
  if (!gallery) {
    return;
  }
  const imgs = Array.from(gallery.querySelectorAll(".post-gallery-img"));
  const slides = imgs.map((img) => ({
    src: img.currentSrc || img.src,
    isBlob: img.classList.contains("post-image--blob"),
  }));
  const idx = imgs.indexOf(thumb);
  openImageLightbox(slides, idx >= 0 ? idx : 0);
});

if (imageLightboxClose) {
  imageLightboxClose.addEventListener("click", () => closeImageLightbox());
}

if (imageLightboxScrim) {
  imageLightboxScrim.addEventListener("click", () => closeImageLightbox());
}

if (imageLightboxPrev) {
  imageLightboxPrev.addEventListener("click", () => {
    if (!lightboxSlides || lightboxSlides.length <= 1) {
      return;
    }
    lightboxIndex = (lightboxIndex - 1 + lightboxSlides.length) % lightboxSlides.length;
    showLightboxSlide();
  });
}

if (imageLightboxNext) {
  imageLightboxNext.addEventListener("click", () => {
    if (!lightboxSlides || lightboxSlides.length <= 1) {
      return;
    }
    lightboxIndex = (lightboxIndex + 1) % lightboxSlides.length;
    showLightboxSlide();
  });
}

document.addEventListener("keydown", (event) => {
  if (imageLightbox && !imageLightbox.hidden) {
    if (event.key === "Escape") {
      event.preventDefault();
      closeImageLightbox();
      return;
    }
    if (event.key === "ArrowLeft" && lightboxSlides && lightboxSlides.length > 1) {
      event.preventDefault();
      lightboxIndex = (lightboxIndex - 1 + lightboxSlides.length) % lightboxSlides.length;
      showLightboxSlide();
      return;
    }
    if (event.key === "ArrowRight" && lightboxSlides && lightboxSlides.length > 1) {
      event.preventDefault();
      lightboxIndex = (lightboxIndex + 1) % lightboxSlides.length;
      showLightboxSlide();
      return;
    }
  }

  if (event.key !== "Escape") {
    return;
  }
  const pixelEditorModal = document.getElementById("pixel-editor-modal");
  if (pixelEditorModal && !pixelEditorModal.hidden) {
    return;
  }
  if (!composeModal || composeModal.hidden) {
    return;
  }
  const emojiWcPopover = document.getElementById("emoji-wc-popover");
  if (emojiWcPopover && !emojiWcPopover.hidden) {
    event.preventDefault();
    tryCloseEmojiWcPopover();
    return;
  }
  tryCloseEmojiWcPopover();
  composeModal.hidden = true;
});

if (contentInput && contentInput.classList.contains("compose-textarea")) {
  contentInput.addEventListener("input", () => {
    resizeComposeTextarea();
    updateComposeCharCount();
  });
}

if (createPostForm && contentInput && formMessage) {
  createPostForm.addEventListener("submit", (event) => {
    const content = contentInput.value.trim();
    const maxLen = contentInput.maxLength > 0 ? contentInput.maxLength : 280;
    if (!content) {
      event.preventDefault();
      formMessage.textContent = "Please write something before publishing.";
      return;
    }
    if (content.length > maxLen) {
      event.preventDefault();
      formMessage.textContent = `Posts are limited to ${maxLen} characters.`;
      return;
    }
    for (let i = 0; i < composeGalleryItems.length; i += 1) {
      const item = composeGalleryItems[i];
      if (item.kind === "file" && item.file && item.file.size > MAX_IMAGE_BYTES) {
        event.preventDefault();
        formMessage.textContent = `Each file must be at most ${MAX_IMAGE_BYTES / 1024} KB.`;
        return;
      }
      if (item.kind === "url" && item.url && !/^https?:\/\/\S+$/i.test(item.url)) {
        event.preventDefault();
        formMessage.textContent = "Each image URL must start with http:// or https://";
        return;
      }
    }

    event.preventDefault();
    createPostForm.querySelectorAll('[data-dynamic-gallery="1"]').forEach((node) => node.remove());

    const countInput = document.createElement("input");
    countInput.type = "hidden";
    countInput.name = "gallery_count";
    countInput.value = String(composeGalleryItems.length);
    countInput.setAttribute("data-dynamic-gallery", "1");
    createPostForm.appendChild(countInput);

    composeGalleryItems.forEach((item, i) => {
      const kindInput = document.createElement("input");
      kindInput.type = "hidden";
      kindInput.name = `gallery_slot_${i}_kind`;
      kindInput.value = item.kind === "file" ? "file" : "url";
      kindInput.setAttribute("data-dynamic-gallery", "1");
      createPostForm.appendChild(kindInput);
      if (item.kind === "url" && item.url) {
        const urlInput = document.createElement("input");
        urlInput.type = "hidden";
        urlInput.name = `gallery_url_${i}`;
        urlInput.value = item.url;
        urlInput.setAttribute("data-dynamic-gallery", "1");
        createPostForm.appendChild(urlInput);
      } else if (item.kind === "file" && item.file) {
        const fileInput = document.createElement("input");
        fileInput.type = "file";
        fileInput.name = `gallery_file_${i}`;
        const dt = new DataTransfer();
        dt.items.add(item.file);
        fileInput.files = dt.files;
        fileInput.setAttribute("data-dynamic-gallery", "1");
        fileInput.className = "sr-only";
        fileInput.tabIndex = -1;
        fileInput.setAttribute("aria-hidden", "true");
        createPostForm.appendChild(fileInput);
      }
    });

    formMessage.textContent = "";
    tryCloseEmojiWcPopover();
    if (composeModal) {
      composeModal.hidden = true;
    }
    createPostForm.submit();
  });
}

window.addEventListener("resize", () => {
  if (composeModal && !composeModal.hidden && contentInput) {
    resizeComposeTextarea();
  }
});

const confirmDeletePostForms = document.querySelectorAll(".confirm-delete-post-form");
confirmDeletePostForms.forEach((form) => {
  form.addEventListener("submit", (event) => {
    const confirmed = window.confirm("Are you sure you want to delete this post?");
    if (!confirmed) {
      event.preventDefault();
    }
  });
});

const confirmDeleteUserForms = document.querySelectorAll(".confirm-delete-user-form");
confirmDeleteUserForms.forEach((form) => {
  form.addEventListener("submit", (event) => {
    const confirmed = window.confirm(
      "Are you sure you want to permanently delete this user?"
    );
    if (!confirmed) {
      event.preventDefault();
    }
  });
});

const likeForms = document.querySelectorAll(".like-form");
likeForms.forEach((form) => {
  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    const postId = form.dataset.postId;
    if (!postId) return;

    const likeButton = form.querySelector(".like-button");
    const likeCount = form.querySelector(".like-count");
    const likeLabel = form.querySelector(".like-label");
    if (!likeButton || !likeCount || !likeLabel) return;

    try {
      likeButton.disabled = true;
      const response = await fetch(`/api/posts/${postId}/like`, {
        method: "POST",
        headers: {
          "X-Requested-With": "XMLHttpRequest",
        },
      });
      const data = await response.json();

      if (response.ok && data.ok) {
        likeCount.textContent = String(data.likes);
        likeLabel.textContent = data.liked ? "Liked" : "Like";
        return;
      }
    } catch (error) {
      form.submit();
      return;
    } finally {
      likeButton.disabled = false;
    }
  });
});

const registrationSwitch = document.getElementById("registration-switch");
const registrationToggleForm = document.getElementById("registration-toggle-form");
const registrationActionInput = document.getElementById("registration-action-input");

if (registrationSwitch && registrationToggleForm && registrationActionInput) {
  registrationSwitch.addEventListener("click", () => {
    const enabled = registrationSwitch.getAttribute("aria-checked") === "true";
    registrationActionInput.value = enabled ? "off" : "on";
    registrationToggleForm.submit();
  });
}
