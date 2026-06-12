// ============================================================
//  config.js — the ONE place the backend URL lives.
//  Before deploying: replace PROD_BACKEND with your real backend
//  URL (e.g. "https://careermap-api.onrender.com/api").
// ============================================================
const PROD_BACKEND = "https://YOUR-BACKEND.onrender.com/api"; // <-- CHANGE ME

const Config = {
  BACKEND_URL:
    (window.location.hostname === "127.0.0.1" || window.location.hostname === "localhost")
      ? "http://127.0.0.1:5000/api"
      : PROD_BACKEND,

  // Free-tier servers sleep. Ping /health early so the first real request
  // doesn't time out. Fire-and-forget; safe to call anywhere.
  wakeServer: function () {
    try { fetch(Config.BACKEND_URL + "/health").catch(function () {}); } catch (e) {}
  }
};
window.Config = Config;
