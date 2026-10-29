/* TIC MASTER — messagerie (polling) */
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

  function csrf() {
    return window.TIC_CSRF || "";
  }

  function timeLabel(iso) {
    if (!iso) return "";
    var date = new Date(iso);
    if (isNaN(date.getTime())) return iso;
    return date.toLocaleTimeString("fr-FR", { hour: "2-digit", minute: "2-digit" });
  }

  var total = 0;          // destinataires du salon (0 = pas d'accusé affiché)

  function receiptLabel(count) {
    if (!total) return "";
    if (!count) return "Envoyé";
    if (total === 1) return "Lu";
    return "Lu par " + count + (count < total ? "/" + total : "");
  }

  function setReceipt(wrapper, count) {
    var el = wrapper.querySelector(".bubble-receipt");
    if (!el) return;
    el.textContent = receiptLabel(count);
    el.classList.toggle("is-read", count > 0);
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
    b.textContent = message.body;

    var meta = document.createElement("span");
    meta.className = "bubble-meta";
    meta.textContent = (message.mine ? "Vous" : message.sender.name) + " · " + timeLabel(message.at);

    content.appendChild(b);
    content.appendChild(meta);
    if (message.mine) {
      var receipt = document.createElement("span");
      receipt.className = "bubble-receipt" + (message.reads ? " is-read" : "");
      receipt.textContent = receiptLabel(message.reads || 0);
      content.appendChild(receipt);
    }
    wrapper.appendChild(content);
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
        if (data.receipts) {
          Object.keys(data.receipts).forEach(function (id) {
            var node = body.querySelector('.msg[data-id="' + id + '"]');
            if (node) setReceipt(node, data.receipts[id]);
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
            if (window.ticToast) window.ticToast((data && data.error) || "Envoi impossible.", true);
            input.value = value;
          }
        })
        .catch(function () {
          if (window.ticToast) window.ticToast("Connexion perdue. Réessayez.", true);
        });
    });
  }

  // Sur téléphone, la bande des conversations défile : on amène la
  // conversation ouverte sous les yeux de l'utilisateur (sans déplacer la page).
  var strip = document.querySelector(".chat-rooms");
  var activeRoom = document.querySelector(".chat-room.is-active");
  if (strip && activeRoom && strip.scrollWidth > strip.clientWidth + 4) {
    strip.scrollLeft = Math.max(0, activeRoom.offsetLeft - strip.clientWidth / 2 + activeRoom.offsetWidth / 2);
  }

  load(true);
  setInterval(function () { load(false); }, 4000);
  // Les accusés de lecture évoluent même sans nouveau message : on les relit
  // toutes les 12 secondes (requête légère, uniquement le salon ouvert).
  setInterval(function () {
    fetch(api + "?room=" + encodeURIComponent(room) + "&after=0", { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (!data || !data.ok) return;
        if (typeof data.total === "number") total = data.total;
        Object.keys(data.receipts || {}).forEach(function (id) {
          var node = body.querySelector('.msg[data-id="' + id + '"]');
          if (node) setReceipt(node, data.receipts[id]);
        });
      })
      .catch(function () {});
  }, 12000);
})();
