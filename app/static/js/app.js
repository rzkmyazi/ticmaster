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
  // Ancien nom utilisé par battle.js / chat.js / exam.js : conservé pour que
  // les messages d'erreur s'affichent enfin (ils étaient silencieux).
  window.ticToast = function (message, isError) {
    toast(message, isError ? "error" : "success");
  };

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

  /* ---------- Confirmations (boîte de dialogue intégrée) ----------
     Les navigateurs Android peuvent supprimer définitivement window.confirm()
     (case « Empêcher cette page de créer d'autres boîtes de dialogue ») : le
     formulaire ne partait alors plus jamais — « Suspendre », « Réinitialiser »
     et « Supprimer » semblaient cassés. On dessine donc la confirmation dans
     la page : elle ne peut pas être bloquée, elle est accessible et lisible
     sur téléphone. */
  var confirmBox = null;
  var confirmCallback = null;
  var confirmPreviousFocus = null;

  function buildConfirmBox() {
    var box = document.createElement("div");
    box.className = "confirm-backdrop";
    box.setAttribute("hidden", "");
    box.innerHTML =
      '<div class="confirm-dialog" role="dialog" aria-modal="true" ' +
        'aria-labelledby="confirm-title" aria-describedby="confirm-text">' +
        '<span class="confirm-icon" aria-hidden="true">' +
          '<svg class="ic" width="22" height="22"><use href="#i-alert-triangle"></use></svg>' +
        '</span>' +
        '<h2 class="confirm-title" id="confirm-title">Confirmation</h2>' +
        '<p class="confirm-text" id="confirm-text"></p>' +
        '<div class="confirm-actions">' +
          '<button type="button" class="btn btn-outline" data-confirm-cancel>Annuler</button>' +
          '<button type="button" class="btn btn-primary" data-confirm-ok>Confirmer</button>' +
        '</div>' +
      '</div>';
    document.body.appendChild(box);

    on(box.querySelector("[data-confirm-cancel]"), "click", function () { closeConfirm(false); });
    on(box.querySelector("[data-confirm-ok]"), "click", function () { closeConfirm(true); });
    on(box, "click", function (e) { if (e.target === box) closeConfirm(false); });
    on(document, "keydown", function (e) {
      if (box.hasAttribute("hidden")) return;
      if (e.key === "Escape") { e.preventDefault(); closeConfirm(false); }
      if (e.key === "Tab") {
        var focusables = [box.querySelector("[data-confirm-cancel]"), box.querySelector("[data-confirm-ok]")];
        var index = focusables.indexOf(document.activeElement);
        e.preventDefault();
        var next = e.shiftKey ? index - 1 : index + 1;
        if (next < 0) next = focusables.length - 1;
        if (next >= focusables.length) next = 0;
        focusables[next].focus();
      }
    });
    return box;
  }

  function closeConfirm(accepted) {
    if (!confirmBox || confirmBox.hasAttribute("hidden")) return;
    confirmBox.classList.remove("is-open");
    confirmBox.setAttribute("hidden", "");
    document.body.classList.remove("confirm-open");
    var callback = confirmCallback;
    confirmCallback = null;
    if (confirmPreviousFocus && confirmPreviousFocus.focus) {
      try { confirmPreviousFocus.focus({ preventScroll: true }); } catch (e) {}
    }
    confirmPreviousFocus = null;
    if (accepted && typeof callback === "function") callback();
  }

  function askConfirm(question, options, callback) {
    options = options || {};
    try {
      if (!confirmBox) confirmBox = buildConfirmBox();
      confirmBox.querySelector(".confirm-text").textContent = question;
      confirmBox.querySelector(".confirm-title").textContent = options.title || "Confirmation";
      var ok = confirmBox.querySelector("[data-confirm-ok]");
      ok.textContent = options.ok || "Confirmer";
      ok.className = "btn " + (options.danger ? "btn-danger" : "btn-primary");
      confirmBox.querySelector(".confirm-icon").className =
        "confirm-icon" + (options.danger ? " confirm-icon--danger" : "");
      confirmCallback = callback;
      confirmPreviousFocus = document.activeElement;
      confirmBox.removeAttribute("hidden");
      document.body.classList.add("confirm-open");
      // petit délai : l'animation d'ouverture doit être déclenchée après l'affichage
      window.setTimeout(function () { confirmBox.classList.add("is-open"); }, 16);
      confirmBox.querySelector("[data-confirm-cancel]").focus();
      return true;
    } catch (err) {
      // Environnement très ancien : on retombe sur la boîte native
      var fallback = window.confirm ? window.confirm(question) : true;
      if (fallback && typeof callback === "function") callback();
      return false;
    }
  }
  TIC.askConfirm = askConfirm;

  function optionsFor(el, suffix) {
    return {
      title: el.getAttribute("data-confirm-title" + suffix) || "Confirmation",
      ok: el.getAttribute("data-confirm-ok" + suffix) || "Confirmer",
      danger: el.getAttribute("data-confirm-danger") === "1"
    };
  }

  function initConfirm() {
    // Formulaires : on intercepte avant l'envoi.
    document.addEventListener("submit", function (e) {
      var form = e.target;
      var question = form.getAttribute("data-confirm");
      if (!question || form.dataset.confirmed === "1") return;
      e.preventDefault();
      e.stopPropagation();
      askConfirm(question, optionsFor(form, ""), function () {
        form.dataset.confirmed = "1";
        if (typeof form.requestSubmit === "function") {
          form.requestSubmit();
        } else {
          form.submit();
        }
      });
    }, true);

    // Liens : même boîte de dialogue.
    document.addEventListener("click", function (e) {
      var link = e.target.closest("a[data-confirm]");
      if (!link || link.dataset.confirmed === "1") return;
      e.preventDefault();
      e.stopPropagation();
      askConfirm(link.getAttribute("data-confirm"), optionsFor(link, ""), function () {
        link.dataset.confirmed = "1";
        link.click();
      });
    });
  }

  /* ---------- État de chargement des formulaires ---------- */
  function resetFormButtons() {
    // Android : au retour depuis l'historique (bfcache), un bouton déjà cliqué
    // resterait grisé — on le réactive systématiquement.
    $$("form .btn.is-loading, form button[type=submit][disabled]").forEach(function (btn) {
      btn.disabled = false;
      btn.classList.remove("is-loading");
      btn.removeAttribute("aria-busy");
      var label = btn.querySelector(".btn-label");
      if (label && btn.dataset.labelInitial) {
        label.textContent = btn.dataset.labelInitial;
        delete btn.dataset.labelInitial;
      }
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
            btn.setAttribute("aria-busy", "true");
            // Indicateur de chargement : le libellé laisse place à « Connexion en cours… »
            var label = btn.querySelector(".btn-label");
            if (label && btn.dataset.loading && !btn.dataset.labelInitial) {
              btn.dataset.labelInitial = label.textContent;
              label.textContent = btn.dataset.loading;
            }
            window.setTimeout(function () {
              btn.disabled = false;
              btn.classList.remove("is-loading");
              btn.removeAttribute("aria-busy");
              if (label && btn.dataset.labelInitial) {
                label.textContent = btn.dataset.labelInitial;
                delete btn.dataset.labelInitial;
              }
            }, 9000);
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
        var cible = del.getAttribute("data-post-delete");
        askConfirm("Supprimer définitivement cette publication ?", { danger: true, ok: "Supprimer" },
          function () {
            postJson("/api/posts/" + cible + "/delete", {})
              .then(function (result) {
                if (!result.ok) { toast((result.data && result.data.error) || "Suppression impossible.", "error"); return; }
                toast("Publication supprimée.", "success");
                return refreshFeed(feed);
              });
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

  /* ---------- Notifications en temps réel ----------
     Le serveur rend la cloche et son panneau ; ici on rafraîchit le compteur
     toutes les 25 s (pause automatique quand l'onglet est en arrière-plan) et
     on affiche une bannière discrète à chaque nouveauté. */
  var notifState = { latest: 0, timer: null, ouverte: false, premier: true,
                     initialise: false, items: null };

  function notifPanel() { return $("#notif-panel"); }

  function setNotifBadge(count) {
    var badge = $("#notif-badge");
    var toggle = $("#notif-toggle");
    if (!badge) return;
    if (count > 0) {
      badge.textContent = count > 99 ? "99+" : String(count);
      badge.removeAttribute("hidden");
      if (toggle) toggle.setAttribute("aria-label", "Notifications (" + count + " non lues)");
    } else {
      badge.setAttribute("hidden", "");
      if (toggle) toggle.setAttribute("aria-label", "Notifications");
    }
    document.querySelectorAll(".nav-count").forEach(function (el) {
      if (count > 0) { el.textContent = count > 99 ? "99+" : String(count); el.removeAttribute("hidden"); }
      else el.setAttribute("hidden", "");
    });
  }

  function notifIcon(name) {
    var safe = String(name || "bell").toLowerCase().replace(/[^a-z0-9-]/g, "") || "bell";
    var svg = document.createElementNS("http://www.w3.org/2000/svg", "svg");
    svg.setAttribute("class", "ic");
    svg.setAttribute("width", "17");
    svg.setAttribute("height", "17");
    svg.setAttribute("aria-hidden", "true");
    var use = document.createElementNS("http://www.w3.org/2000/svg", "use");
    use.setAttribute("href", "#i-" + safe);
    svg.appendChild(use);
    return svg;
  }

  function renderNotifList(items) {
    var list = $("#notif-list");
    if (!list) return;
    list.textContent = "";
    if (!items.length) {
      var vide = document.createElement("li");
      vide.className = "notif-empty";
      vide.appendChild(notifIcon("bell"));
      var txt = document.createElement("span");
      txt.textContent = "Aucune notification pour le moment.";
      vide.appendChild(txt);
      list.appendChild(vide);
      return;
    }
    items.forEach(function (item) {
      var li = document.createElement("li");
      li.className = "notif-item" + (item.read ? " is-read" : "");
      li.dataset.id = item.id;

      var a = document.createElement("a");
      a.setAttribute("href", item.url || "/notifications");
      a.setAttribute("data-notif-open", "");

      var ic = document.createElement("span");
      ic.className = "notif-ic notif-ic--" + (item.kind || "system");
      ic.appendChild(notifIcon(item.icon));

      var boite = document.createElement("span");
      boite.className = "notif-txt";
      var titre = document.createElement("strong");
      titre.textContent = item.title;
      boite.appendChild(titre);
      if (item.body) {
        var corps = document.createElement("span");
        corps.className = "notif-body";
        corps.textContent = item.body;
        boite.appendChild(corps);
      }
      var heure = document.createElement("time");
      heure.textContent = item.at || "";
      boite.appendChild(heure);

      a.appendChild(ic);
      a.appendChild(boite);
      li.appendChild(a);
      list.appendChild(li);
    });
  }

  function markAllRead() {
    fetch("/api/notifications/tout-lire", {
      method: "POST",
      headers: { "X-CSRF-Token": csrf(), "Content-Type": "application/json" },
      body: "{}"
    }).then(function (r) { return r.json(); })
      .then(function (data) { if (data && data.ok) setNotifBadge(0); })
      .catch(function () {});
  }

  function markOneRead(id) {
    if (!id) return;
    fetch("/api/notifications/" + id + "/lue", {
      method: "POST",
      headers: { "X-CSRF-Token": csrf(), "Content-Type": "application/json" },
      body: "{}"
    }).catch(function () {});
  }

  function openNotifPanel(open) {
    var panel = notifPanel();
    var toggle = $("#notif-toggle");
    if (!panel || !toggle) return;
    notifState.ouverte = open;
    if (open) {
      panel.removeAttribute("hidden");
      toggle.setAttribute("aria-expanded", "true");
      window.setTimeout(function () { panel.classList.add("is-open"); }, 10);
      // On affiche tout de suite les dernières données connues, puis on
      // interroge le serveur : le panneau n'est jamais en retard d'un cycle.
      if (notifState.items) renderNotifList(notifState.items);
      pollNotifications();
      // Ce qui est affiché est considéré comme vu : le compteur retombe.
      window.setTimeout(function () {
        if (!notifState.ouverte) return;
        markAllRead();
        panel.querySelectorAll(".notif-item").forEach(function (el) {
          el.classList.add("is-read");
        });
      }, 900);
    } else {
      panel.classList.remove("is-open");
      toggle.setAttribute("aria-expanded", "false");
      window.setTimeout(function () {
        if (!notifState.ouverte) panel.setAttribute("hidden", "");
      }, 160);
    }
  }

  function pollNotifications() {
    if (document.hidden) return;
    var url = "/api/notifications";
    // Premier appel : sans « since » (aucune bannière). Ensuite on demande les
    // nouveautés, même quand le compteur est à zéro.
    if (notifState.initialise) url += "?since=" + notifState.latest;
    fetch(url, { headers: { "Accept": "application/json" } })
      .then(function (r) { return r.ok ? r.json() : null; })
      .then(function (data) {
        if (!data || !data.ok) return;
        setNotifBadge(data.count || 0);
        notifState.latest = data.latest_id || 0;
        notifState.items = data.items || notifState.items;

        var panelVisible = notifState.ouverte;
        if (panelVisible) renderNotifList(data.items || []);

        // Bannière discrète pour les nouveautés (jamais au premier chargement)
        if (!notifState.premier && data.new && data.new.length) {
          data.new.slice(0, 3).forEach(function (item) {
            var deja = item.actor && item.title.indexOf(item.actor) !== -1;
            toast(deja || !item.actor ? item.title : item.actor + " — " + item.title, "info", 6000);
          });
        }
        notifState.premier = false;
        notifState.initialise = true;
      })
      .catch(function () {});
  }

  function initNotifications() {
    var root = $("#notif-root");
    if (!root) return;

    var toggle = $("#notif-toggle");
    on(toggle, "click", function (e) {
      e.stopPropagation();
      openNotifPanel(!notifState.ouverte);
    });

    var tout = $("#notif-read-all");
    on(tout, "click", function (e) {
      e.stopPropagation();
      markAllRead();
      root.querySelectorAll(".notif-item").forEach(function (el) { el.classList.add("is-read"); });
    });

    // Un clic sur une notification la marque comme lue puis suit son lien.
    root.addEventListener("click", function (e) {
      var lien = e.target.closest("[data-notif-open]");
      if (!lien) return;
      var item = lien.closest(".notif-item");
      markOneRead(item ? item.dataset.id : null);
    });

    on(document, "click", function (e) {
      if (notifState.ouverte && !e.target.closest("#notif-root")) openNotifPanel(false);
    });
    on(document, "keydown", function (e) {
      if (e.key === "Escape" && notifState.ouverte) openNotifPanel(false);
    });

    pollNotifications();                       // premier état (sans bannière)
    notifState.timer = window.setInterval(pollNotifications, 25000);
    on(document, "visibilitychange", function () {
      if (!document.hidden) pollNotifications();   // retour sur l'onglet : mise à jour immédiate
    });
    on(window, "focus", pollNotifications);
  }

  /* Actions inline remplacées par des attributs (CSP sans « unsafe-inline ») */
  function initInlineActions() {
    $$("[data-auto-submit]").forEach(function (el) {
      on(el, "change", function () { if (el.form) el.form.requestSubmit ? el.form.requestSubmit() : el.form.submit(); });
    });
    $$("[data-reload]").forEach(function (btn) {
      on(btn, "click", function () { window.location.reload(); });
    });
    $$("[data-back]").forEach(function (btn) {
      on(btn, "click", function () { window.history.back(); });
    });
  }

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
    initNotifications();
    initInlineActions();

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
