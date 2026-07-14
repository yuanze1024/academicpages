const wechatButton = document.querySelector("[data-wechat]");
const copyStatus = document.querySelector("#wechat-status");
let statusTimer;

async function copyText(text) {
  if (navigator.clipboard && window.isSecureContext) {
    await navigator.clipboard.writeText(text);
    return;
  }

  const input = document.createElement("textarea");
  input.value = text;
  input.setAttribute("readonly", "");
  input.style.position = "fixed";
  input.style.opacity = "0";
  document.body.appendChild(input);
  input.select();
  const copied = document.execCommand("copy");
  input.remove();
  if (!copied) throw new Error("Copy command failed");
}

if (wechatButton && copyStatus) {
  wechatButton.addEventListener("click", async () => {
    clearTimeout(statusTimer);
    try {
      await copyText(wechatButton.dataset.wechat);
      copyStatus.textContent = "Copied to clipboard";
      copyStatus.classList.add("copy-toast--visible");
    } catch {
      copyStatus.textContent = `WeChat: ${wechatButton.dataset.wechat}`;
      copyStatus.classList.add("copy-toast--visible");
    }
    statusTimer = setTimeout(() => {
      copyStatus.classList.remove("copy-toast--visible");
      copyStatus.textContent = "";
    }, 2200);
  });
}

function startPreview(container) {
  const preview = container.querySelector(".publication-preview");
  if (!preview) return;
  if (!preview.src) preview.src = preview.dataset.previewSrc;
  container.classList.add("publication-visual--playing");
}

function stopPreview(container) {
  container.classList.remove("publication-visual--playing");
}

document.querySelectorAll(".publication-visual-link").forEach((container) => {
  container.addEventListener("mouseenter", () => startPreview(container));
  container.addEventListener("mouseleave", () => stopPreview(container));
  container.addEventListener("focus", () => startPreview(container));
  container.addEventListener("blur", () => stopPreview(container));
});
