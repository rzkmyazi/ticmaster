/* TIC MASTER — messagerie (polling, accusés, transfert) */
(function () {
  "use strict";

  var chat = document.getElementById("chat");
  if (!chat) return;

  var body = document.getElementById("chat-body");
  var form = document.getElementById("chat-form");
  var input = document.getElementById("chat-input");
  var room = chat.dataset.room || "general";
  var api = chat.dataset.api;
  var sendUrl = chat.dataset.send;
  var lastId = 0;
  var loading = false;

  /* Le jeton de sécurité vit dans la balise <meta name="csrf-token"> : on le
     lit ici pour que l'envoi fonctionne sur toutes les pages (battle, chat…). */
  function csrf() {
    if (window.TIC && window.TIC.csrf) return window.TIC.csrf();
    var meta = document.querySelector('meta[name="csrf-token"]');
    return (meta && meta.getAttribute("content")) || window.TIC_CSRF || "";
  }

  function toast(message, isError) {
    if (window.TIC && window.TIC.toast) {
      window.TIC.toast(message, isError ? "error" : "success");
    } else if (window.ticToast) {
      window.ticToast(message, isError);
    }
  }

  function timeLabel(iso) {
    if (!iso) return "";
    var date = new Date(iso);
    if (isNaN(date.getTime())) return iso;
    return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }

  var total = 0;          // destinataires du salon (0 = pas d'accusé affiché)

  /* Envoyé → Reçu (arrivé au destinataire) → Lu (le destinataire l'a ouvert). */
  function receiptLabel(message) {
    if (!total) return "";
    var reads = message.reads || 0;
    if (total === 1) {
      if (reads) return "Lu";
      return message.delivered ? "Reçu" : "Envoyé";
    }
    if (!reads) return "Envoyé";
    return "Lu par " + reads + (reads < total ? "/" + total : "");
  }

  function drawReceipt(node, message) {
    var el = node.querySelector(".bubble-receipt");
    if (!el) return;
    el.textContent = receiptLabel(message);
    el.classList.toggle("is-read", (message.reads || 0) > 0);
    el.classList.toggle("is-delivered", !message.reads && !!message.delivered);
  }

  function setReceipt(node, info) {
    drawReceipt(node, { reads: info.reads, delivered: info.delivered });
  }

  function forwardButton(message) {
    var action = document.createElement("button");
    action.type = "button";
    action.className = "bubble-forward";
    action.dataset.forwardId = message.id;
    action.title = "Transférer ce message";
    action.setAttribute("aria-label", "Transférer ce message");
    action.innerHTML =
      '<svg class="ic" width="14" height="14" aria-hidden="true" focusable="false">' +
      '<use href="#i-forward"></use></svg>';
    return action;
  }

  function bubble(message) {
    var wrapper = document.createElement("div");
    wrapper.className = "msg" + (message.mine ? " is-mine" : "");
    if (message.id) wrapper.dataset.id = message.id;

    if (!message.mine) {
      var avatar = document.createElement("span");
      avatar.className = "avatar avatar-sm";
      avatar.style.setProperty("--hue", (message.sender.id * 47) % 360);
      var initials = document.createElement("span");
      initials.className = "avatar-initials";
      initials.textContent = message.sender.initials || "?";
      avatar.appendChild(initials);
      wrapper.appendChild(avatar);
    }

    var content = document.createElement("div");
    var b = document.createElement("div");
    b.className = "bubble";

    if (message.forwarded) {
      var tag = document.createElement("span");
      tag.className = "bubble-forwarded";
      tag.textContent = "Message transféré de " + message.forwarded.author +
        (message.forwarded.at ? " · " + message.forwarded.at : "");
      b.appendChild(tag);
    }

    var text = document.createElement("span");
    text.className = "bubble-text";
    text.textContent = message.body;
    b.appendChild(text);

    var meta = document.createElement("span");
    meta.className = "bubble-meta";
    meta.textContent = (message.mine ? "Vous" : message.sender.name) + " · " + timeLabel(message.at);

    content.appendChild(b);

    // Une seule ligne sous la bulle : auteur · heure, accusé, bouton de transfert
    var foot = document.createElement("div");
    foot.className = "bubble-foot";
    foot.appendChild(meta);
    if (message.mine) {
      var receipt = document.createElement("span");
      receipt.className = "bubble-receipt";
      foot.appendChild(receipt);
    }
    if (message.id) {
      var tools = document.createElement("div");
      tools.className = "bubble-tools";
      tools.appendChild(forwardButton(message));
      foot.appendChild(tools);
    }
    content.appendChild(foot);
    wrapper.appendChild(content);
    if (message.mine) drawReceipt(wrapper, message);
    return wrapper;
  }

  function scrollDown() {
    body.scrollTop = body.scrollHeight;
  }

  function load(initial) {
    if (loading) return;
    loading = true;
    fetch(api + "?room=" + encodeURIComponent(room) + "&after=" + (initial ? 0 : lastId), {
      credentials: "same-origin",
      headers: { "X-Requested-With": "XMLHttpRequest" }
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        loading = false;
        if (!data || !data.ok) return;
        if (typeof data.total === "number") total = data.total;
        if (data.receipts || data.delivery) {
          var ids = Object.keys(Object.assign({}, data.receipts || {}, data.delivery || {}));
          ids.forEach(function (id) {
            var node = body.querySelector('.msg[data-id="' + id + '"]');
            if (node) setReceipt(node, {
              reads: (data.receipts || {})[id] || 0,
              delivered: !!(data.delivery || {})[id]
            });
          });
        }
        if (initial) {
          body.innerHTML = "";
          if (!data.messages.length) {
            var empty = document.createElement("div");
            empty.className = "chat-empty";
            empty.textContent = "Aucun message pour le moment. Lancez la conversation !";
            body.appendChild(empty);
          }
        } else {
          var placeholder = body.querySelector(".chat-empty");
          if (placeholder && data.messages.length) placeholder.remove();
        }
        data.messages.forEach(function (message) {
          if (message.id > lastId) lastId = message.id;
          body.appendChild(bubble(message));
        });
        if (data.messages.length) scrollDown();
      })
      .catch(function () { loading = false; });
  }

  if (form) {
    form.addEventListener("submit", function (event) {
      event.preventDefault();
      var value = (input.value || "").trim();
      if (!value) return;
      input.value = "";
      fetch(sendUrl, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
        body: JSON.stringify({ room: room, body: value, csrf_token: csrf() })
      })
        .then(function (r) { return r.json(); })
        .then(function (data) {
          if (data && data.ok) {
            var placeholder = body.querySelector(".chat-empty");
            if (placeholder) placeholder.remove();
            body.appendChild(bubble(data.message));
            lastId = Math.max(lastId, data.message.id);
            scrollDown();
          } else {
            toast((data && data.error) || "Envoi impossible.", true);
            input.value = value;
          }
        })
        .catch(function () {
          toast("Connexion perdue. Réessayez.", true);
        });
    });
  }

  /* ------------------------- Transfert d'un message ------------------------- */
  var dialog = document.getElementById("forward-dialog");
  var dialogSelect = document.getElementById("forward-target");
  var dialogPreview = document.getElementById("forward-preview");
  var pendingId = null;

  function openForward(id) {
    if (!dialog || !dialogSelect) return;
    var node = body.querySelector('.msg[data-id="' + id + '"]');
    var text = node ? node.querySelector(".bubble-text") : null;
    pendingId = id;
    if (dialogPreview) dialogPreview.textContent = text ? "« " + text.textContent.slice(0, 120) + " »" : "";
    dialog.hidden = false;
    dialog.classList.add("is-open");
    document.body.classList.add("confirm-open");
    var first = dialogSelect.querySelector('option:not([disabled])');
    if (first) first.selected = true;
    dialogSelect.focus();
  }

  function closeForward() {
    if (dialog) {
      dialog.classList.remove("is-open");
      dialog.hidden = true;
    }
    document.body.classList.remove("confirm-open");
    pendingId = null;
  }

  if (dialog) {
    dialog.addEventListener("click", function (event) {
      if (event.target === dialog || event.target.closest("[data-forward-close]")) closeForward();
      if (event.target.closest("[data-forward-send]")) {
        if (!pendingId || !dialogSelect) return;
        var target = dialogSelect.value;
        if (!target) return toast("Choisissez une destination.", true);
        fetch("/api/messages/forward", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
          body: JSON.stringify({ message_id: pendingId, room: target, csrf_token: csrf() })
        })
          .then(function (r) { return r.json(); })
          .then(function (data) {
            if (!data || !data.ok) return toast((data && data.error) || "Transfert impossible.", true);
            closeForward();
            toast("Message transféré.");
            if (data.room === room) {
              var placeholder = body.querySelector(".chat-empty");
              if (placeholder) placeholder.remove();
              body.appendChild(bubble(data.message));
              lastId = Math.max(lastId, data.message.id);
              scrollDown();
            }
          })
          .catch(function () { toast("Connexion perdue. Réessayez.", true); });
      }
    });
    document.addEventListener("keydown", function (event) {
      if (event.key === "Escape" && !dialog.hidden) closeForward();
    });
  }

  body.addEventListener("click", function (event) {
    var button = event.target.closest("[data-forward-id]");
    if (button) {
      event.preventDefault();
      openForward(button.dataset.forwardId);
    }
  });

  // Sur téléphone, la bande des conversations défile : on amène la
  // conversation ouverte sous les yeux de l'utilisateur (sans déplacer la page).
  var strip = document.querySelector(".chat-rooms");
  var activeRoom = document.querySelector(".chat-room.is-active");
  if (strip && activeRoom && strip.scrollWidth > strip.clientWidth + 4) {
    strip.scrollLeft = Math.max(0, activeRoom.offsetLeft - strip.clientWidth / 2 + activeRoom.offsetWidth / 2);
  }

  load(true);
  setInterval(function () { load(false); }, 4000);
  // Les accusés évoluent même sans nouveau message : on les relit toutes les
  // 12 secondes (requête légère, uniquement le salon ouvert).
  setInterval(function () {
    fetch(api + "?room=" + encodeURIComponent(room) + "&after=0", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.ok) return;
        if (typeof data.total === "number") total = data.total;
        var ids = Object.keys(Object.assign({}, data.receipts || {}, data.delivery || {}));
        ids.forEach(function (id) {
          var node = body.querySelector('.msg[data-id="' + id + '"]');
          if (node) setReceipt(node, {
            reads: (data.receipts || {})[id] || 0,
            delivered: !!(data.delivery || {})[id]
          });
        });
      })
      .catch(function () {});
  }, 12000);
})();
