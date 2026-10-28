/* TIC MASTER — surveillance d'examen et minuteur */
(function () {
  "use strict";

  var examApp = document.getElementById("exam-app");
  var quizApp = document.getElementById("quiz-app");
  var app = examApp || quizApp;
  if (!app) return;

  var form = document.getElementById("exam-form") || document.getElementById("quiz-form");
  var remaining = parseInt(app.dataset.remaining || "0", 10);
  var timerValue = app.querySelector("[data-timer-value]");
  var timerBox = app.querySelector("[data-timer]");
  var submitted = false;

  /* ------------------------- Minuteur ------------------------- */
  function paintTime() {
    if (!timerValue) return;
    var minutes = Math.floor(Math.max(0, remaining) / 60);
    var seconds = Math.max(0, remaining) % 60;
    timerValue.textContent = minutes + ":" + (seconds < 10 ? "0" : "") + seconds;
    if (timerBox && remaining <= 60) timerBox.classList.add("is-urgent");
  }

  function tick() {
    remaining -= 1;
    paintTime();
    if (remaining <= 0 && !submitted) {
      submitted = true;
      if (form) form.submit();
    }
  }

  paintTime();
  setInterval(tick, 1000);

  /* ------------------------- Compteur de réponses ------------------------- */
  var progress = document.querySelector("[data-progress]");
  if (progress) {
    var total = form ? form.querySelectorAll("[data-answer]").length : 0;
    var update = function () {
      var answered = {};
      form.querySelectorAll("[data-answer]:checked").forEach(function (input) {
        answered[input.name] = true;
      });
      progress.textContent = Object.keys(answered).length + " / " +
        new Set(Array.from(form.querySelectorAll("[data-answer]")).map(function (i) { return i.name; })).size +
        " répondues";
    };
    form.addEventListener("change", update);
    update();
  }

  if (!examApp) return; /* exercice libre : pas de surveillance */

  /* ------------------------- Surveillance ------------------------- */
  var attemptId = examApp.dataset.attempt;
  var limit = parseInt(examApp.dataset.limit || "1", 10);
  var violations = parseInt(examApp.dataset.violations || "0", 10);
  var resultUrl = examApp.dataset.resultUrl;
  var overlay = document.getElementById("exam-eliminated");
  var violationCounter = document.querySelector("[data-violation-count]");
  var sending = false;

  function csrf() {
    return window.TIC_CSRF || "";
  }

  function showEliminated() {
    if (!overlay) return;
    overlay.hidden = false;
    submitted = true;
    if (form) {
      form.querySelectorAll("input, button").forEach(function (el) { el.disabled = true; });
    }
    setTimeout(function () {
      window.removeEventListener("beforeunload", beforeUnload);
      window.location.href = resultUrl;
    }, 2600);
  }

  function report(reason) {
    if (submitted || sending) return;
    sending = true;
    violations += 1;
    if (violationCounter) violationCounter.textContent = violations;

    fetch("/api/exam/" + attemptId + "/violation", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify({ reason: reason, csrf_token: csrf() })
    })
      .then(function (response) { return response.json(); })
      .then(function (data) {
        sending = false;
        if (data && (data.eliminated || data.status === "eliminated")) {
          showEliminated();
        } else if (data && data.limit) {
          limit = data.limit;
          if (window.ticToast) {
            window.ticToast("Avertissement : ne quittez pas l'onglet (" + data.violations + "/" + limit + ").", true);
          }
        }
      })
      .catch(function () { sending = false; });
  }

  function beforeUnload(event) {
    if (submitted) return;
    event.preventDefault();
    event.returnValue = "";
    return "";
  }

  document.addEventListener("visibilitychange", function () {
    if (document.hidden) report("onglet masqué");
  });

  window.addEventListener("blur", function () {
    /* Perte de focus de la fenêtre : signal complémentaire, sans élimination directe */
    if (document.hidden) report("fenêtre inactive");
  });

  document.addEventListener("fullscreenchange", function () {
    if (!document.fullscreenElement && !submitted) report("sortie du plein écran");
  });

  window.addEventListener("pagehide", function () {
    if (submitted) return;
    /* Beacon : le serveur est prévenu même si la page se ferme */
    try {
      var data = new FormData();
      data.append("csrf_token", csrf());
      data.append("reason", "page quittée");
      navigator.sendBeacon("/api/exam/" + attemptId + "/violation", data);
    } catch (e) {}
  });

  window.addEventListener("beforeunload", beforeUnload);

  document.querySelectorAll("a[href]").forEach(function (link) {
    link.addEventListener("click", function (event) {
      event.preventDefault();
      report("clic sur un lien pendant l'examen");
    });
  });

  var fsButton = document.querySelector("[data-fullscreen]");
  if (fsButton) {
    fsButton.addEventListener("click", function () {
      var el = document.documentElement;
      if (!document.fullscreenElement) {
        (el.requestFullscreen || el.webkitRequestFullscreen || function () {}).call(el);
      } else {
        (document.exitFullscreen || document.webkitExitFullscreen || function () {}).call(document);
      }
    });
  }

  form.addEventListener("submit", function () {
    submitted = true;
    window.removeEventListener("beforeunload", beforeUnload);
  });

  /* Battement de cœur : détecte les coupures prolongées côté serveur */
  setInterval(function () {
    if (submitted) return;
    fetch("/api/exam/" + attemptId + "/heartbeat", {
      method: "POST",
      credentials: "same-origin",
      headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf() },
      body: JSON.stringify({ csrf_token: csrf() })
    })
      .then(function (r) { return r.json(); })
      .then(function (data) {
        if (data.eliminated) showEliminated();
        if (data.redirect) {
          submitted = true;
          window.location.href = data.redirect;
        }
      })
      .catch(function () {});
  }, 15000);
})();
