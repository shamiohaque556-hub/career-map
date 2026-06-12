// ============================================================
//  userstore.js — per-user browser storage WITH backend sync.
//
//  Same API as before (get / set / remove / clearMine), so no
//  page code changes. New behaviour:
//    • every set() schedules a debounced snapshot push to
//      POST /api/user/state  (silent if offline / logged out)
//    • userStore.hydrate() pulls the server snapshot down and
//      fills any keys missing locally — index.html calls this
//      right after login, so progress follows the user across
//      devices and browsers.
//
//  Include on every page AFTER config.js:
//      <script src="config.js"></script>
//      <script src="userstore.js"></script>
// ============================================================
(function (global) {
  function currentUserId() {
    var id = localStorage.getItem("current_user_id");
    if (id) return id;
    try {
      var u = JSON.parse(localStorage.getItem("user") || "null");
      if (u && (u.id != null)) return String(u.id);
      if (u && u.email) return u.email;
    } catch (e) {}
    return "guest";
  }

  function k(key) { return "u" + currentUserId() + "::" + key; }

  // Keys that are GLOBAL (shared, not per-user) — auth/session plumbing.
  var GLOBAL_KEYS = ["token", "user", "current_user_id"];

  // ── backend sync ───────────────────────────────────────────
  var pushTimer = null;

  function snapshotMine() {
    var prefix = "u" + currentUserId() + "::";
    var snap = {};
    Object.keys(localStorage).forEach(function (key) {
      if (key.indexOf(prefix) === 0) {
        snap[key.slice(prefix.length)] = localStorage.getItem(key);
      }
    });
    return snap;
  }

  function pushSoon() {
    if (!global.Config || !localStorage.getItem("token")) return;
    if (currentUserId() === "guest") return;
    clearTimeout(pushTimer);
    pushTimer = setTimeout(function () {
      try {
        fetch(global.Config.BACKEND_URL + "/user/state", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + localStorage.getItem("token")
          },
          body: JSON.stringify({ state: snapshotMine() })
        }).catch(function () {});
      } catch (e) {}
    }, 1500);
  }

  var userStore = {
    get: function (key) {
      if (GLOBAL_KEYS.indexOf(key) !== -1) return localStorage.getItem(key);
      return localStorage.getItem(k(key));
    },
    set: function (key, val) {
      if (GLOBAL_KEYS.indexOf(key) !== -1) return localStorage.setItem(key, val);
      localStorage.setItem(k(key), val);
      pushSoon();
    },
    remove: function (key) {
      if (GLOBAL_KEYS.indexOf(key) !== -1) return localStorage.removeItem(key);
      localStorage.removeItem(k(key));
      pushSoon();
    },
    // wipe just THIS user's local data (e.g. on logout)
    clearMine: function () {
      var prefix = "u" + currentUserId() + "::";
      Object.keys(localStorage).forEach(function (key) {
        if (key.indexOf(prefix) === 0) localStorage.removeItem(key);
      });
    },
    // Pull the server snapshot; local values win, server fills the gaps.
    // Returns a promise. Call after login (index.html does this).
    hydrate: function () {
      if (!global.Config || !localStorage.getItem("token")) return Promise.resolve();
      return fetch(global.Config.BACKEND_URL + "/user/state", {
        headers: { "Authorization": "Bearer " + localStorage.getItem("token") }
      })
        .then(function (r) { return r.ok ? r.json() : { state: {} }; })
        .then(function (data) {
          var state = (data && data.state) || {};
          Object.keys(state).forEach(function (key) {
            if (localStorage.getItem(k(key)) === null && typeof state[key] === "string") {
              localStorage.setItem(k(key), state[key]);
            }
          });
        })
        .catch(function () {});
    },
    // Push immediately (used right before page navigation if needed)
    flush: function () { clearTimeout(pushTimer); pushTimer = null;
      if (!global.Config || !localStorage.getItem("token") || currentUserId() === "guest") return;
      try {
        fetch(global.Config.BACKEND_URL + "/user/state", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Authorization": "Bearer " + localStorage.getItem("token")
          },
          body: JSON.stringify({ state: snapshotMine() }),
          keepalive: true
        }).catch(function () {});
      } catch (e) {}
    }
  };

  global.userStore = userStore;
})(window);
