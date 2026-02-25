(function () {
  "use strict";

  const BASE = "http://127.0.0.1:__MERSEA_PORT__";
  const SAVE_URL = BASE + "/save";
  const STATE_URL = BASE + "/state";

  const BTN_STYLE = [
    "padding:10px 20px",
    "font-size:16px",
    "font-weight:bold",
    "color:#fff",
    "border:none",
    "border-radius:8px",
    "cursor:pointer",
    "box-shadow:0 2px 8px rgba(0,0,0,0.3)",
    "transition:opacity 0.2s",
  ].join(";");

  // Intercept Ctrl+S / Cmd+S
  document.addEventListener("keydown", (e) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "s") {
      e.preventDefault();
      saveDiagram();
    }
  });

  // Button container
  const bar = document.createElement("div");
  bar.style.cssText =
    "position:fixed;bottom:20px;right:20px;z-index:99999;display:flex;gap:8px;";
  document.body.appendChild(bar);

  // Save button
  const saveBtn = document.createElement("button");
  saveBtn.textContent = "\u{1F4BE} Save";
  saveBtn.style.cssText = BTN_STYLE + ";background:#4CAF50;";
  saveBtn.onmouseenter = () => (saveBtn.style.opacity = "0.8");
  saveBtn.onmouseleave = () => (saveBtn.style.opacity = "1");
  saveBtn.onclick = saveDiagram;
  bar.appendChild(saveBtn);

  // Save & Close button
  const saveCloseBtn = document.createElement("button");
  saveCloseBtn.textContent = "\u{2714} Save & Close";
  saveCloseBtn.style.cssText = BTN_STYLE + ";background:#2196F3;";
  saveCloseBtn.onmouseenter = () => (saveCloseBtn.style.opacity = "0.8");
  saveCloseBtn.onmouseleave = () => (saveCloseBtn.style.opacity = "1");
  saveCloseBtn.onclick = saveAndClose;
  bar.appendChild(saveCloseBtn);

  // --- File watch: poll for external changes via background service worker ---
  let lastVersion = 0;
  setInterval(async () => {
    try {
      const resp = await chrome.runtime.sendMessage({
        type: "fetch",
        url: STATE_URL,
      });
      if (resp && resp.ok) {
        const data = JSON.parse(resp.text);
        if (data.version > lastVersion) {
          lastVersion = data.version;
          if (window.location.hash.slice(1) !== data.fragment) {
            window.location.hash = data.fragment;
            window.location.reload();
          }
        }
      }
    } catch (e) {}
  }, 1500);

  // --- Save functions (routed through background to bypass page CSP) ---

  async function saveDiagram() {
    const hash = window.location.hash.slice(1);
    if (!hash) {
      toast("No diagram data in URL", true);
      return;
    }
    try {
      const resp = await chrome.runtime.sendMessage({
        type: "fetch",
        url: SAVE_URL,
        method: "POST",
        body: hash,
      });
      if (resp && resp.ok) {
        toast("Saved \u2713");
      } else {
        toast("Save failed: " + (resp ? resp.error || resp.text : "no response"), true);
      }
    } catch (err) {
      toast("Save failed: " + err.message, true);
    }
  }

  async function saveAndClose() {
    const hash = window.location.hash.slice(1);
    if (!hash) {
      toast("No diagram data in URL", true);
      return;
    }
    try {
      const resp = await chrome.runtime.sendMessage({
        type: "fetch",
        url: SAVE_URL,
        method: "POST",
        body: hash,
      });
      if (resp && resp.ok) {
        toast("Saved \u2713");
        setTimeout(() => window.close(), 400);
      } else {
        toast("Save failed: " + (resp ? resp.error || resp.text : "no response"), true);
      }
    } catch (err) {
      toast("Save failed: " + err.message, true);
    }
  }

  function toast(msg, isError) {
    const el = document.createElement("div");
    el.textContent = msg;
    el.style.cssText = [
      "position:fixed",
      "bottom:70px",
      "right:20px",
      "z-index:99999",
      "padding:10px 20px",
      "font-size:14px",
      "background:" + (isError ? "#f44336" : "#333"),
      "color:#fff",
      "border-radius:6px",
      "box-shadow:0 2px 8px rgba(0,0,0,0.3)",
      "opacity:1",
      "transition:opacity 0.5s",
    ].join(";");
    document.body.appendChild(el);
    setTimeout(() => {
      el.style.opacity = "0";
      setTimeout(() => el.remove(), 500);
    }, 2000);
  }
})();
