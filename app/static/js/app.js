/* ==========================================================================
   TIC MASTER — comportements généraux
   #by_Myazirzk
   ========================================================================== */
(function () {
  "use strict";

  var TIC = (window.TIC = window.TIC || {});

  /* ---------- Utilitaires ---------- */
  function $(sel, root) { return (root || document).querySelector(sel); }
  function $$(sel, root) { return Array.prototype.slice.call((root || document).querySelectorAll(sel)); }
  function on(el, evt, fn, opts) { if (el) el.addEventListener(evt, fn, opts); }

  function csrf() {
    var meta = $('meta[name="csrf-token"]');
    return meta ? meta.getAttribute("content") : "";
  }
  TIC.csrf = csrf;

  /* ---------- Toasts ---------- */
  function toast(message, kind, timeout) {
    var root = $("#toast-root");
    if (!root) return;
    var icons = {
      success: '<svg class="ic" width="17" height="17" aria-hidden="true"><use href="#i-check-circle"></use></svg>',
      error: '<svg class="ic" width="17" height="17" aria-hidden="true"><use href="#i-alert"></use></svg>',
      info: '<svg class="ic" width="17" height="17" aria-hidden="true"><use href="#i-info"></use></svg>'
    };
    var el = document.createElement("div");
    el.className = "toast toast--" + (kind || "info");
    el.setAttribute("role", kind === "error" ? "alert" : "status");
    el.innerHTML = (icons[kind] || icons.info) + "<span></span>";
    el.querySelector("span").textContent = message;
    root.appendChild(el);
    window.setTimeout(function () {
      el.classList.add("is-out");
      window.setTimeout(function () { el.remove(); }, 260);
    }, timeout || 3800);
  }
  TIC.toast = toast;

  /* ---------- Thème clair / sombre ---------- */
  function currentTheme() {
    return document.documentElement.getAttribute("data-theme") === "light" ? "light" : "dark";
  }
  function applyTheme(theme) {
    document.documentElement.setAttribute("data-theme", theme);
    try { localStorage.setItem("tic-theme", theme); } catch (e) {}
    var meta = $('meta[name="theme-color"]');
    if (meta) meta.setAttribute("content", theme === "light" ? "#f4f7fd" : "#060b18");
    $$("[data-theme-toggle]").forEach(function (btn) {
      btn.setAttribute("aria-pressed", theme === "light" ? "true" : "false");
      btn.setAttribute("title", theme === "light" ? "Passer en thème sombre" : "Passer en thème clair");
      var shell = btn.querySelector(".theme-btn-icon");
      if (shell) shell.innerHTML = '<svg class="ic" width="18" height="18" aria-hidden="true"><use href="#i-' + (theme === "light" ? "sun" : "moon") + '"></use></svg>';
    });
  }
  TIC.theme = { get: currentTheme, set: applyTheme, toggle: function () { applyTheme(currentTheme() === "light" ? "dark" : "light"); } };

  /* ---------- Menu latéral (mobile) ---------- */
  function initSidebar() {
    var sidebar = $("#sidebar");
    var overlay = $("#sidebar-overlay");
    var toggle = $("#sidebar-toggle");
    if (!sidebar || !toggle) return;

    function open(openIt) {
      sidebar.classList.toggle("is-open", openIt);
      if (overlay) overlay.classList.toggle("is-open", openIt);
      toggle.setAttribute("aria-expanded", openIt ? "true" : "false");
      document.body.style.overflow = openIt && window.innerWidth < 901 ? "hidden" : "";
      if (openIt) {
        var first = sidebar.querySelector(".nav-link");
        if (first) first.focus();
      }
    }
    on(toggle, "click", function () { open(!sidebar.classList.contains("is-open")); });
    on(overlay, "click", function () { open(false); });
    $$("[data-sidebar-close]").forEach(function (el) { on(el, "click", function () { open(false); }); });
    $$(".nav-link", sidebar).forEach(function (link) {
      on(link, "click", function () { if (window.innerWidth < 901) open(false); });
    });
    on(document, "keydown", function (e) {
      if (e.key === "Escape" && sidebar.classList.contains("is-open")) open(false);
    });
    on(window, "resize", function () {
      if (window.innerWidth > 900 && sidebar.classList.contains("is-open")) open(false);
    });
  }

  /* ---------- Alertes / briques refermables ---------- */
  function initDismiss() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-dismiss]");
      if (!btn) return;
      var box = btn.closest(".alert, .toast");
      if (!box) return;
      box.classList.add("is-out");
      window.setTimeout(function () { box.remove(); }, 200);
    });
    $$(".alert[data-auto-dismiss]").forEach(function (el) {
      window.setTimeout(function () {
        el.classList.add("is-out");
        window.setTimeout(function () { el.remove(); }, 220);
      }, parseInt(el.getAttribute("data-auto-dismiss"), 10) || 7000);
    });
  }

  /* ---------- Afficher / masquer le mot de passe ---------- */
  function initPasswordToggles() {
    $$("[data-pw-toggle]").forEach(function (btn) {
      on(btn, "click", function () {
        var input = document.getElementById(btn.getAttribute("data-pw-toggle"));
        if (!input) return;
        var show = input.type === "password";
        input.type = show ? "text" : "password";
        btn.setAttribute("aria-label", show ? "Masquer le mot de passe" : "Afficher le mot de passe");
        btn.setAttribute("aria-pressed", show ? "true" : "false");
        btn.innerHTML = '<svg class="ic" width="18" height="18" aria-hidden="true"><use href="#i-' + (show ? "eye-off" : "eye") + '"></use></svg>';
        input.focus();
      });
    });
  }

  /* ---------- Copier dans le presse-papiers ---------- */
  function initCopy() {
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-copy]");
      if (!btn) return;
      var value = btn.getAttribute("data-copy");
      var target = btn.getAttribute("data-copy-target");
      if (target) {
        var input = document.getElementById(target);
        if (input) value = input.value || input.textContent;
      }
      if (!value) return;
      var done = function () { toast("Copié dans le presse-papiers.", "success", 2200); };
      if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(value).then(done, function () { toast("Copie impossible sur ce navigateur.", "error"); });
      } else {
        var ta = document.createElement("textarea");
        ta.value = value; ta.style.position = "fixed"; ta.style.opacity = "0";
        document.body.appendChild(ta); ta.select();
        try { document.execCommand("copy"); done(); } catch (err) { toast("Copie impossible.", "error"); }
        ta.remove();
      }
    });
  }

  /* ---------- Confirmations ---------- */
  function initConfirm() {
    document.addEventListener("submit", function (e) {
      var form = e.target;
      var question = form.getAttribute("data-confirm");
      if (question && !form.dataset.confirmed) {
        if (!window.confirm(question)) {
          e.preventDefault();
          return;
        }
        form.dataset.confirmed = "1";
      }
    }, true);

    document.addEventListener("click", function (e) {
      var link = e.target.closest("a[data-confirm]");
      if (!link) return;
      if (!window.confirm(link.getAttribute("data-confirm"))) e.preventDefault();
    });
  }

  /* ---------- État de chargement des formulaires ---------- */
  function resetFormButtons() {
    // Android : au retour depuis l'historique (bfcache), un bouton déjà cliqué
    // resterait grisé — on le réactive systématiquement.
    $$("form .btn.is-loading, form button[type=submit][disabled]").forEach(function (btn) {
      btn.disabled = false;
      btn.classList.remove("is-loading");
    });
  }

  function initForms() {
    window.addEventListener("pageshow", resetFormButtons);
    document.addEventListener("visibilitychange", function () {
      if (document.visibilityState === "visible") resetFormButtons();
    });
    $$("form").forEach(function (form) {
      if (form.hasAttribute("data-no-loading")) return;
      on(form, "submit", function () {
        if (form.dataset.confirmed === "1" || !form.getAttribute("data-confirm")) {
          var btn = form.querySelector('button[type="submit"], input[type="submit"]');
          if (btn && !form.querySelector(".quiz-option")) {
            btn.classList.add("is-loading");
            btn.disabled = true;
            window.setTimeout(function () { btn.disabled = false; btn.classList.remove("is-loading"); }, 9000);
          }
        }
      });
    });
  }

  /* ---------- QCM : sélection visuelle ---------- */
  function initQuiz() {
    document.addEventListener("change", function (e) {
      var input = e.target;
      if (input.type !== "radio" || !input.closest(".quiz-option")) return;
      var name = input.name;
      $$('input[type="radio"][name="' + CSS.escape(name) + '"]').forEach(function (r) {
        var label = r.closest(".quiz-option");
        if (label) label.classList.toggle("is-selected", r.checked);
      });
      var form = input.closest("form");
      if (form) {
        var counter = form.querySelector("[data-answered]");
        if (counter) {
          var total = form.querySelectorAll("input[type=radio]").length
            - form.querySelectorAll("input[type=radio]:checked").length;
          counter.textContent = total === 0 ? "Toutes les questions ont une réponse." : total + " question(s) sans réponse";
        }
      }
    });
    $$(".quiz-option input[type=radio]:checked").forEach(function (r) {
      var label = r.closest(".quiz-option");
      if (label) label.classList.add("is-selected");
    });
  }

  /* ---------- Compteurs animés ---------- */
  function initCounters() {
    var nodes = $$("[data-count-to]");
    if (!nodes.length) return;
    if (!("IntersectionObserver" in window)) {
      nodes.forEach(function (n) { n.textContent = n.getAttribute("data-count-to"); });
      return;
    }
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (!entry.isIntersecting) return;
        var node = entry.target;
        io.unobserve(node);
        var target = parseFloat(node.getAttribute("data-count-to")) || 0;
        var start = performance.now();
        var dur = 900;
        function step(now) {
          var p = Math.min(1, (now - start) / dur);
          var eased = 1 - Math.pow(1 - p, 3);
          node.textContent = Math.round(target * eased).toLocaleString("fr-FR");
          if (p < 1) requestAnimationFrame(step);
        }
        requestAnimationFrame(step);
      });
    }, { threshold: 0.4 });
    nodes.forEach(function (n) { io.observe(n); });
  }

  /* ---------- Apparition au défilement ---------- */
  function initReveal() {
    var nodes = $$(".reveal");
    if (!nodes.length || !("IntersectionObserver" in window)) return;
    nodes.forEach(function (n) { n.style.animationPlayState = "paused"; });
    var io = new IntersectionObserver(function (entries) {
      entries.forEach(function (entry) {
        if (entry.isIntersecting) {
          entry.target.style.animationPlayState = "running";
          io.unobserve(entry.target);
        }
      });
    }, { threshold: 0.08 });
    nodes.forEach(function (n) { io.observe(n); });
  }

  /* ---------- Barre supérieure : ombre au défilement ---------- */
  function initScrollShadow() {
    var bar = $(".topbar");
    if (!bar) return;
    var update = function () {
      bar.classList.toggle("is-scrolled", window.scrollY > 6);
    };
    on(window, "scroll", update, { passive: true });
    update();
  }

  /* ---------- Recherche rapide (raccourci /) ---------- */
  function initShortcuts() {
    on(document, "keydown", function (e) {
      if (e.key !== "/" || e.ctrlKey || e.metaKey || e.altKey) return;
      var tag = (e.target.tagName || "").toLowerCase();
      if (tag === "input" || tag === "textarea" || tag === "select" || e.target.isContentEditable) return;
      var search = $('input[type="search"]');
      if (search) { e.preventDefault(); search.focus(); search.select(); }
    });
  }

  /* ---------- Application installable (Android / iOS) ---------- */
  var deferredPrompt = null;
  function initInstall() {
    window.addEventListener("beforeinstallprompt", function (e) {
      e.preventDefault();
      deferredPrompt = e;
      $$("[data-install-app]").forEach(function (b) { b.hidden = false; });
    });
    document.addEventListener("click", function (e) {
      var btn = e.target.closest("[data-install-app]");
      if (!btn) return;
      if (!deferredPrompt) {
        toast("Utilisez le menu du navigateur « Installer l'application ».", "info", 5200);
        return;
      }
      deferredPrompt.prompt();
      deferredPrompt.userChoice.then(function () {
        deferredPrompt = null;
        btn.hidden = true;
      });
    });
  }

  /* ---------- Service worker (PWA) ---------- */
  function initServiceWorker() {
    if (!("serviceWorker" in navigator)) return;
    var secure = location.protocol === "https:" || location.hostname === "localhost" || location.hostname === "127.0.0.1";
    if (!secure) return;
    window.addEventListener("load", function () {
      navigator.serviceWorker.register("/service-worker.js").catch(function () { /* silencieux */ });
    });
  }

  /* ---------- État hors ligne ---------- */
  function initOffline() {
    on(window, "offline", function () { toast("Connexion perdue — certaines actions seront indisponibles.", "error", 6000); });
    on(window, "online", function () { toast("Connexion rétablie.", "success"); });
  }

  /* ---------- Copie de lien de partage ---------- */
  function initShareLink() {
    on(document, "click", function (e) {
      var btn = e.target.closest("[data-share]");
      if (!btn) return;
      var url = btn.getAttribute("data-share") || location.href;
      if (navigator.share) {
        navigator.share({ title: document.title, url: url }).catch(function () {});
      } else if (navigator.clipboard) {
        navigator.clipboard.writeText(url).then(function () { toast("Lien copié.", "success"); });
      }
    });
  }


  /* ---------- Onglets du profil ---------- */
  function initTabs() {
    var links = $$("[data-tab-link]");
    if (!links.length) return;
    var panels = $$("[data-tab-panel]");
    function show(name) {
      links.forEach(function (link) {
        var active = link.getAttribute("data-tab-link") === name;
        link.classList.toggle("is-active", active);
        link.setAttribute("aria-selected", active ? "true" : "false");
      });
      panels.forEach(function (panel) {
        panel.classList.toggle("is-active", panel.getAttribute("data-tab-panel") === name);
      });
    }
    links.forEach(function (link) {
      on(link, "click", function (e) {
        e.preventDefault();
        var name = link.getAttribute("data-tab-link");
        show(name);
        if (window.history && history.replaceState) history.replaceState(null, "", "#" + name);
      });
    });
    var initial = (window.location.hash || "").replace("#", "");
    show(initial === "fil" ? "fil" : "infos");
  }

  /* ---------- Fil d'actualité : publier, réagir, commenter ---------- */
  function postJson(url, payload) {
    return window.fetch(url, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      credentials: "same-origin",
      body: JSON.stringify(payload || {})
    }).then(function (res) { return res.json().then(function (data) { return { ok: res.ok, data: data }; }); });
  }

  function refreshFeed(feed) {
    var url = feed.getAttribute("data-refresh");
    if (!url) return window.Promise ? window.Promise.resolve() : null;
    return window.fetch(url, { credentials: "same-origin", headers: { "X-Requested-With": "fetch" } })
      .then(function (res) { return res.json(); })
      .then(function (data) { if (data && data.html) feed.innerHTML = data.html; })
      .catch(function () {});
  }

  function initFeed() {
    var feed = $("#feed");
    var form = $("#post-form");
    if (!feed && !form) return;

    /* Publication */
    if (form) {
      var fileInput = $("#post-image");
      var preview = $("#post-preview");
      var fileName = $("#post-file-name");
      var errBox = $("#post-error");
      var submit = $("#post-submit");

      on(fileInput, "change", function () {
        var file = fileInput.files && fileInput.files[0];
        if (!file) {
          if (preview) { preview.hidden = true; preview.querySelector("img").removeAttribute("src"); }
          if (fileName) fileName.textContent = "Aucun fichier sélectionné";
          return;
        }
        if (fileName) fileName.textContent = file.name;
        if (preview && file.type.indexOf("image/") === 0) {
          var url = URL.createObjectURL(file);
          preview.querySelector("img").src = url;
          preview.hidden = false;
        }
      });

      on(form, "submit", function (e) {
        e.preventDefault();
        if (errBox) errBox.hidden = true;
        var body = form.querySelector('textarea[name="body"]');
        var hasFile = fileInput && fileInput.files && fileInput.files.length;
        if ((!body || !body.value.trim()) && !hasFile) {
          if (errBox) { errBox.textContent = "Écrivez un message ou ajoutez une photo."; errBox.hidden = false; }
          return;
        }
        var btn = submit;
        if (btn) { btn.disabled = true; btn.classList.add("is-loading"); }
        window.fetch(form.getAttribute("data-endpoint"), {
          method: "POST",
          headers: { "X-CSRF-Token": csrf() },
          credentials: "same-origin",
          body: new FormData(form)
        }).then(function (res) {
          return res.json().then(function (data) { return { ok: res.ok, data: data }; });
        }).then(function (result) {
          if (!result.ok) {
            if (errBox) { errBox.textContent = (result.data && result.data.error) || "Publication impossible."; errBox.hidden = false; }
            return;
          }
          form.reset();
          if (preview) { preview.hidden = true; preview.querySelector("img").removeAttribute("src"); }
          if (fileName) fileName.textContent = "Aucun fichier sélectionné";
          toast("Publication ajoutée.", "success");
          return refreshFeed(feed);
        }).catch(function () {
          if (errBox) { errBox.textContent = "Erreur réseau, réessayez."; errBox.hidden = false; }
        }).then(function () {
          if (btn) { btn.disabled = false; btn.classList.remove("is-loading"); }
        });
      });
    }

    /* Clics délégués dans le fil (survit aux rafraîchissements) */
    on(document, "click", function (e) {
      var react = e.target.closest ? e.target.closest("[data-react]") : null;
      if (react) {
        var postId = react.getAttribute("data-post");
        postJson("/api/posts/" + postId + "/react", { kind: react.getAttribute("data-react") })
          .then(function (result) {
            if (!result.ok) { toast((result.data && result.data.error) || "Réaction impossible.", "error"); return; }
            var bar = document.querySelector('[data-react-bar="' + postId + '"]');
            if (bar) {
              $$("[data-react]", bar).forEach(function (b) {
                var active = b.getAttribute("data-react") === result.data.current;
                b.classList.toggle("is-active", active);
                b.setAttribute("aria-pressed", active ? "true" : "false");
              });
            }
            var holder = document.querySelector('[data-reaction-summary="' + postId + '"]');
            if (holder) {
              if (!result.data.summary.length) {
                holder.innerHTML = '<span class="text-muted">Aucune réaction</span>';
              } else {
                holder.innerHTML = result.data.summary.map(function (item) {
                  return '<span class="rchip" title="' + item.label + '">' + item.emoji + "<b>" + item.count + "</b></span>";
                }).join("");
              }
            }
          });
        return;
      }

      var toggle = e.target.closest ? e.target.closest("[data-comment-toggle]") : null;
      if (toggle) {
        var box = document.querySelector('[data-comments="' + toggle.getAttribute("data-comment-toggle") + '"]');
        if (box) {
          box.hidden = !box.hidden;
          if (!box.hidden) {
            var field = box.querySelector('input[name="body"]');
            if (field) field.focus();
          }
        }
        return;
      }

      var del = e.target.closest ? e.target.closest("[data-post-delete]") : null;
      if (del) {
        if (!window.confirm("Supprimer définitivement cette publication ?")) return;
        postJson("/api/posts/" + del.getAttribute("data-post-delete") + "/delete", {})
          .then(function (result) {
            if (!result.ok) { toast((result.data && result.data.error) || "Suppression impossible.", "error"); return; }
            toast("Publication supprimée.", "success");
            return refreshFeed(feed);
          });
      }
    });

    /* Commentaires */
    on(document, "submit", function (e) {
      var commentForm = e.target.closest ? e.target.closest("[data-comment-form]") : null;
      if (!commentForm) return;
      e.preventDefault();
      var field = commentForm.querySelector('input[name="body"]');
      var body = field ? field.value.trim() : "";
      if (!body) return;
      var postId = commentForm.getAttribute("data-comment-form");
      field.value = "";
      postJson("/api/posts/" + postId + "/comment", { body: body })
        .then(function (result) {
          if (!result.ok) {
            toast((result.data && result.data.error) || "Commentaire refusé.", "error");
            if (field) field.value = body;
            return;
          }
          refreshFeed(feed).then(function () {
            var box = document.querySelector('[data-comments="' + postId + '"]');
            if (box) box.hidden = false;
          });
        });
    });
  }

  /* ---------- Démarrage ---------- */
  function boot() {
    applyTheme(currentTheme());
    initSidebar();
    initDismiss();
    initPasswordToggles();
    initCopy();
    initConfirm();
    initForms();
    initQuiz();
    initCounters();
    initReveal();
    initScrollShadow();
    initShortcuts();
    initInstall();
    initServiceWorker();
    initOffline();
    initShareLink();
    initTabs();
    initFeed();

    $$("[data-theme-toggle]").forEach(function (btn) {
      on(btn, "click", function () { TIC.theme.toggle(); });
    });

    var flashes = $$(".flash-stack .alert");
    if (flashes.length) {
      window.setTimeout(function () {
        flashes.forEach(function (el) {
          el.classList.add("is-out");
          window.setTimeout(function () { el.remove(); }, 220);
        });
      }, 8000);
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", boot);
  } else {
    boot();
  }
})();
