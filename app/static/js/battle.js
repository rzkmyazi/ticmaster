/* TIC MASTER — battles (solo / groupe) */
(function () {
  "use strict";

  /* Le jeton vit dans <meta name="csrf-token">. Sans cette lecture, tous les
     appels (créer, rejoindre, lancer, répondre) étaient refusés en 400. */
  function csrf() {
    if (window.TIC && window.TIC.csrf) return window.TIC.csrf();
    var meta = document.querySelector('meta[name="csrf-token"]');
    return (meta && meta.getAttribute("content")) || window.TIC_CSRF || "";
  }

  function post(url, payload) {
    return fetch(url, {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify(Object.assign({ csrf_token: csrf() }, payload || {}))
    }).then(function (response) {
      return response.json().then(function (data) {
        if (!response.ok) throw new Error(data.error || "Erreur.");
        return data;
      });
    });
  }

  function go(code) {
    window.location.href = "/battle/" + code;
  }

  /* ------------------------- Page d'accueil ------------------------- */
  var launcher = document.getElementById("battle-launcher");
  if (launcher) {
    launcher.addEventListener("click", function (event) {
      var createBtn = event.target.closest("[data-battle-create]");
      if (createBtn) {
        var mode = createBtn.dataset.battleCreate;
        var nameInput = document.getElementById("group-name");
        var name = nameInput ? nameInput.value.trim() : "";
        createBtn.disabled = true;
        post("/api/battle/create", { mode: mode, name: name })
          .then(function (data) { go(data.code); })
          .catch(function (error) {
            createBtn.disabled = false;
            if (window.ticToast) window.ticToast(error.message, true);
          });
      }

      if (event.target.closest("[data-battle-join]")) {
        var code = (document.getElementById("join-code").value || "").trim().toUpperCase();
        if (code.length < 4) {
          if (window.ticToast) window.ticToast("Saisissez un code valide.", true);
          return;
        }
        post("/api/battle/join", { code: code })
          .then(function (data) { go(data.code); })
          .catch(function (error) { if (window.ticToast) window.ticToast(error.message, true); });
      }
    });
  }

  /* ------------------------- Salle de battle ------------------------- */
  var room = document.getElementById("battle-room");
  if (!room) return;

  var code = room.dataset.code;
  var mode = room.dataset.mode;
  var isOwner = room.dataset.isOwner === "true";
  var isMember = room.dataset.isMember === "true";

  var statusEl = document.getElementById("battle-status");
  var textEl = document.getElementById("battle-question-text");
  var optionsEl = document.getElementById("battle-options");
  var timerEl = document.getElementById("battle-timer-value");
  var progressEl = document.getElementById("battle-question-progress");
  var waitingEl = document.getElementById("battle-waiting");
  var lobbyActions = document.getElementById("battle-lobby-actions");
  var playersEl = document.getElementById("battle-players");
  var correctionsEl = document.getElementById("battle-corrections");
  var lastIndex = -1;
  var answered = false;
  var finished = false;

  function renderPlayers(members) {
    if (!playersEl) return;
    playersEl.innerHTML = "";
    members.forEach(function (member, index) {
      var row = document.createElement("div");
      row.className = "battle-player" + (member.is_me ? " is-me" : "");

      var avatar = document.createElement("span");
      avatar.className = "avatar avatar-sm";
      avatar.style.setProperty("--hue", (member.id * 47) % 360);
      var initials = document.createElement("span");
      initials.className = "avatar-initials";
      initials.textContent = member.initials || "?";
      avatar.appendChild(initials);

      var name = document.createElement("span");
      name.className = "text-sm";
      name.textContent = (index + 1) + ". " + member.name + (member.answered ? " ✓" : "");

      var score = document.createElement("span");
      score.className = "score";
      score.textContent = member.score;

      row.appendChild(avatar);
      row.appendChild(name);
      row.appendChild(score);
      playersEl.appendChild(row);
    });
  }

  function renderQuestion(state) {
    if (!state.question) {
      if (state.room && state.room.status === "lobby") {
        textEl.textContent = "En attente du lancement…";
        optionsEl.innerHTML = "";
        progressEl.textContent = state.count + " questions prêtes";
      }
      return;
    }
    if (state.index !== lastIndex) {
      lastIndex = state.index;
      answered = false;
      textEl.textContent = state.question.text;
      progressEl.textContent = "Question " + (state.index + 1) + " sur " + state.count;
      optionsEl.innerHTML = "";
      state.question.options.forEach(function (option, index) {
        var label = document.createElement("button");
        label.type = "button";
        label.className = "option";
        label.dataset.optionId = option.id;

        var letter = document.createElement("span");
        letter.className = "option-letter";
        letter.textContent = "ABCDEF"[index] || "?";

        var text = document.createElement("span");
        text.textContent = option.text;

        label.appendChild(letter);
        label.appendChild(text);
        optionsEl.appendChild(label);
      });
    }
    if (waitingEl) {
      waitingEl.hidden = !state.my_answered;
      if (state.my_answered) {
        var restants = typeof state.waiting_for === "number" ? state.waiting_for : 0;
        waitingEl.textContent = restants > 0
          ? "Réponse enregistrée · en attente de " + restants + " joueur" + (restants > 1 ? "s" : "")
          : "Réponse enregistrée · question suivante…";
      }
    }
  }

  function renderFinished(state) {
    if (finished) return;
    finished = true;
    if (statusEl) statusEl.textContent = "Terminée";
    if (textEl) textEl.textContent = "Battle terminée !";
    if (optionsEl) optionsEl.innerHTML = "";
    if (waitingEl) waitingEl.hidden = true;
    if (lobbyActions) lobbyActions.hidden = true;
    if (correctionsEl && state.corrections) {
      correctionsEl.hidden = false;
      correctionsEl.innerHTML = "";
      state.corrections.forEach(function (item, index) {
        var card = document.createElement("section");
        card.className = "card";
        var bodyEl = document.createElement("div");
        bodyEl.className = "card-body";

        var title = document.createElement("strong");
        title.textContent = (index + 1) + ". " + item.text;
        var answer = document.createElement("p");
        answer.className = "text-sm mt-1";
        answer.style.color = "var(--green)";
        answer.textContent = "Bonne réponse : " + item.correct;
        bodyEl.appendChild(title);
        bodyEl.appendChild(answer);

        if (item.explanation) {
          var explanation = document.createElement("p");
          explanation.className = "text-xs text-muted mt-1";
          explanation.textContent = item.explanation;
          bodyEl.appendChild(explanation);
        }
        card.appendChild(bodyEl);
        correctionsEl.appendChild(card);
      });
    }
  }

  function poll() {
    fetch("/api/battle/state?code=" + encodeURIComponent(code), { credentials: "same-origin" })
      .then(function (r) { return r.json(); })
      .then(function (state) {
        if (!state || !state.ok) return;
        if (statusEl) {
          statusEl.textContent = state.room.status === "lobby" ? "Salon d'attente"
            : state.room.status === "pending" ? "En attente de validation"
            : state.room.status === "refused" ? "Refusée"
            : state.room.status === "running" ? "En cours" : "Terminée";
        }
        if (timerEl) timerEl.textContent = state.room.status === "running" ? state.seconds_left + "s" : "—";
        if (state.room.status === "lobby" && lobbyActions) lobbyActions.hidden = false;
        if (state.room.status !== "lobby" && lobbyActions) lobbyActions.hidden = state.room.status !== "lobby";

        // Acceptée entre-temps par le professeur : le bouton devient utilisable
        var startBtn = document.querySelector("[data-battle-start]");
        if (startBtn) startBtn.disabled = state.room.status !== "lobby";

        // La bannière « en attente de validation » disparaît dès l'accord
        var notice = document.getElementById("battle-notice");
        if (notice) notice.hidden = state.room.status !== "pending" && state.room.status !== "refused";
        renderPlayers(state.members || []);
        if (state.room.status === "running") {
          if (lobbyActions) lobbyActions.hidden = true;
          renderQuestion(state);
        }
        if (state.room.status === "finished") renderFinished(state);
      })
      .catch(function () {});
  }

  if (optionsEl) {
    optionsEl.addEventListener("click", function (event) {
      var option = event.target.closest("[data-option-id]");
      if (!option || answered) return;
      answered = true;
      post("/api/battle/answer", { code: code, option_id: option.dataset.optionId })
        .then(function (data) {
          option.classList.add(data.correct ? "is-correct" : "is-wrong");
          if (waitingEl) waitingEl.hidden = false;
        })
        .catch(function (error) {
          answered = false;
          if (window.ticToast) window.ticToast(error.message, true);
        });
    });
  }

  room.addEventListener("click", function (event) {
    if (event.target.closest("[data-battle-start]")) {
      post("/api/battle/start", { code: code })
        .then(function () { poll(); })
        .catch(function (error) { if (window.ticToast) window.ticToast(error.message, true); });
    }

    if (event.target.closest("[data-battle-rename]")) {
      var input = document.getElementById("room-name");
      var name = input ? input.value.trim() : "";
      post("/api/battle/rename", { code: code, name: name })
        .then(function (data) {
          if (window.ticToast) window.ticToast("Groupe renommé : " + data.name);
          var title = document.querySelector(".topbar-title") || document.querySelector(".page-title");
          if (title) title.textContent = data.name;
          var input = document.getElementById("room-name");
          if (input) input.value = data.name;
        })
        .catch(function (error) { if (window.ticToast) window.ticToast(error.message, true); });
    }

    if (event.target.closest("[data-battle-join-inline]")) {
      post("/api/battle/join", { code: code })
        .then(function () { window.location.reload(); })
        .catch(function (error) { if (window.ticToast) window.ticToast(error.message, true); });
    }
  });

  poll();
  setInterval(poll, 2000);
})();
