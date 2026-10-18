/* Check-in scanner (CHK-01, CHK-03, CHK-07).
 *
 * Scans with the browser's BarcodeDetector where available, or jsQR otherwise.
 * When the network drops, scans are queued in this browser and sent later with
 * their original time and an id, so the server records each one exactly once.
 */
(function () {
  "use strict";

  var root = document.querySelector("[data-scan-url]");
  if (!root) return;

  var scanUrl = root.getAttribute("data-scan-url");
  var csrf = root.getAttribute("data-csrf");
  var eventId = root.getAttribute("data-event");
  var queueKey = "ocp-queue-" + eventId;
  var JSQR_URL = "https://cdn.jsdelivr.net/npm/jsqr@1.4.0/dist/jsQR.js";

  var resultEl = document.getElementById("result");
  var video = document.getElementById("video");
  var startButton = document.getElementById("start-camera");
  var hint = document.getElementById("camera-hint");
  var laneInput = document.getElementById("lane");
  var laneLabel = document.getElementById("lane-label");
  var net = document.getElementById("net");
  var netText = document.getElementById("net-text");
  var offlineNote = document.getElementById("offline-note");
  var queueText = document.getElementById("queue-text");

  var paused = false;
  var lastCode = "";
  var lastAt = 0;
  var resumeTimer = null;

  function store(key, value) {
    try { if (value === undefined) { return localStorage.getItem(key); } localStorage.setItem(key, value); } catch (e) { return null; }
    return null;
  }

  function uuid() {
    if (window.crypto && crypto.randomUUID) return crypto.randomUUID();
    return "s" + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  var deviceId = store("ocp-device-id") || uuid();
  store("ocp-device-id", deviceId);
  laneInput.value = store("ocp-lane") || "";
  function showLane() { laneLabel.textContent = laneInput.value ? "· " + laneInput.value : ""; }
  showLane();
  laneInput.addEventListener("change", function () { store("ocp-lane", laneInput.value.trim()); showLane(); });

  function readQueue() { try { return JSON.parse(store(queueKey) || "[]"); } catch (e) { return []; } }
  function writeQueue(items) { store(queueKey, JSON.stringify(items)); showQueue(); }
  function showQueue() {
    var n = readQueue().length;
    queueText.textContent = n ? n + " waiting to sync" : "";
    netText.textContent = navigator.onLine ? "Online" : "Offline" + (n ? " · " + n + " saved" : "");
  }

  function setOnline() {
    var online = navigator.onLine;
    net.classList.toggle("is-offline", !online);
    offlineNote.hidden = online;
    showQueue();
    if (online) flush();
  }
  window.addEventListener("online", setOnline);
  window.addEventListener("offline", setOnline);

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text) node.textContent = text;
    return node;
  }

  var ICONS = {
    admitted: '<svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12.5l4.5 4.5L19 7.5"></path></svg>',
    duplicate: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.6" stroke-linecap="round"><path d="M12 7v6"></path><path d="M12 17v.01"></path></svg>',
    invalid: '<svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round"><path d="M7 7l10 10M17 7L7 17"></path></svg>'
  };

  function render(data) {
    resultEl.innerHTML = "";
    resultEl.className = "result result-" + data.result;
    var head = el("div", "row");
    head.style.flexWrap = "nowrap";
    if (ICONS[data.result]) {
      var icon = el("span", "result-icon");
      icon.setAttribute("aria-hidden", "true");
      icon.innerHTML = ICONS[data.result];
      head.appendChild(icon);
    }
    head.appendChild(el("p", "result-title", data.label));
    resultEl.appendChild(head);
    if (data.name) resultEl.appendChild(el("p", "result-name", data.name));
    if (data.ticket_type) {
      var line = data.ticket_type + (data.sessions && data.sessions.length ? " · " + data.sessions.join(", ") : "");
      resultEl.appendChild(el("p", "", line));
    }
    if (data.first_scan) {
      var first = data.first_scan;
      resultEl.appendChild(el("p", "mono small", "First scan " + first.time + (first.lane ? " · " + first.lane : "") + (first.by ? " · " + first.by : "")));
      resultEl.appendChild(el("p", "small", "Don't admit again. Send them to the help desk if something's not right."));
    }
    if (data.reason) resultEl.appendChild(el("p", "", data.reason));
    if (data.result === "invalid") resultEl.appendChild(el("p", "small", "Don't admit. Send them to the help desk."));
    if (data.result === "admitted") resultEl.appendChild(el("p", "mono small", data.scanned_at + (laneInput.value ? " · " + laneInput.value : "")));
    if (navigator.vibrate) navigator.vibrate(data.result === "admitted" ? 80 : [120, 80, 120]);
  }

  function renderSaved() {
    resultEl.innerHTML = "";
    resultEl.className = "result result-saved";
    resultEl.appendChild(el("p", "result-title", "Saved offline"));
    resultEl.appendChild(el("p", "", "This scan is stored on this phone. It's checked against the ticket list as soon as you're back online."));
    resultEl.appendChild(el("p", "small", "If the door policy allows, let them in and keep going."));
  }

  function updateStats(stats) {
    if (!stats) return;
    document.getElementById("stat-in").textContent = stats.checked_in;
    document.getElementById("stat-left").textContent = stats.to_go;
  }

  function post(body) {
    return fetch(scanUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json", "X-CSRFToken": csrf },
      credentials: "same-origin",
      body: JSON.stringify(body)
    }).then(function (response) {
      if (!response.ok) throw new Error("HTTP " + response.status);
      return response.json();
    });
  }

  function submit(code) {
    code = (code || "").trim();
    if (!code) return;
    var now = Date.now();
    if (code === lastCode && now - lastAt < 4000) return;
    lastCode = code;
    lastAt = now;
    pause();
    var scan = { code: code, client_scan_id: uuid(), scanned_at: new Date().toISOString(), lane: laneInput.value.trim(), device_id: deviceId };
    if (!navigator.onLine) { queue(scan); return; }
    post(scan).then(function (data) {
      if (data.results && data.results[0]) render(data.results[0]);
      updateStats(data.stats);
      if (data.results && data.results[0] && data.results[0].result === "admitted") scheduleResume(3500);
    }).catch(function () { queue(scan); });
  }

  function queue(scan) {
    scan.offline = true;
    var items = readQueue();
    items.push(scan);
    writeQueue(items);
    renderSaved();
    scheduleResume(2500);
  }

  var flushing = false;
  function flush() {
    var items = readQueue();
    if (!items.length || flushing || !navigator.onLine) return;
    flushing = true;
    post({ scans: items }).then(function (data) {
      var done = {};
      var problems = 0;
      (data.results || []).forEach(function (r) { done[r.client_scan_id] = true; if (r.result !== "admitted") problems += 1; });
      writeQueue(readQueue().filter(function (s) { return !done[s.client_scan_id]; }));
      updateStats(data.stats);
      queueText.textContent = "Synced " + items.length + (problems ? ", " + problems + " to check" : "");
    }).catch(function () { /* still offline; try again later */ }).then(function () { flushing = false; });
  }
  setInterval(flush, 15000);

  function pause() { paused = true; if (resumeTimer) clearTimeout(resumeTimer); }
  function resume() {
    paused = false;
    resultEl.className = "result result-idle";
    resultEl.innerHTML = '<p style="font-weight: 600">Ready to scan</p>';
  }
  function scheduleResume(ms) { resumeTimer = setTimeout(resume, ms); }
  document.getElementById("next").addEventListener("click", function () { lastCode = ""; resume(); document.getElementById("manual-code").focus(); });

  document.getElementById("manual").addEventListener("submit", function (event) {
    event.preventDefault();
    var input = document.getElementById("manual-code");
    var value = input.value;
    input.value = "";
    lastCode = "";
    submit(value.indexOf("/t/") >= 0 ? value.split("/t/")[1].replace(/\/$/, "") : value);
  });

  // Camera -------------------------------------------------------------------------------

  function loadJsQR() {
    return new Promise(function (resolve, reject) {
      if (window.jsQR) return resolve(window.jsQR);
      var script = document.createElement("script");
      script.src = JSQR_URL;
      script.onload = function () { resolve(window.jsQR); };
      script.onerror = reject;
      document.head.appendChild(script);
    });
  }

  function startCamera() {
    if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
      hint.textContent = "This browser can't use the camera. Type codes or use Find by name.";
      return;
    }
    navigator.mediaDevices.getUserMedia({ video: { facingMode: "environment" }, audio: false }).then(function (stream) {
      video.srcObject = stream;
      video.hidden = false;
      startButton.hidden = true;
      return video.play();
    }).then(function () {
      if ("BarcodeDetector" in window) {
        var detector = new window.BarcodeDetector({ formats: ["qr_code"] });
        loop(function () {
          return detector.detect(video).then(function (codes) { return codes.length ? codes[0].rawValue : null; });
        });
      } else {
        loadJsQR().then(function (jsQR) {
          var canvas = document.createElement("canvas");
          var context = canvas.getContext("2d", { willReadFrequently: true });
          loop(function () {
            if (!video.videoWidth) return Promise.resolve(null);
            canvas.width = video.videoWidth;
            canvas.height = video.videoHeight;
            context.drawImage(video, 0, 0);
            var image = context.getImageData(0, 0, canvas.width, canvas.height);
            var found = jsQR(image.data, image.width, image.height, { inversionAttempts: "dontInvert" });
            return Promise.resolve(found ? found.data : null);
          });
        }).catch(function () { hint.textContent = "Couldn't load the QR reader. Type codes or use Find by name."; });
      }
    }).catch(function () {
      hint.textContent = "Camera access was blocked. Allow it in the browser settings, or type codes.";
    });
  }

  function loop(read) {
    function tick() {
      if (paused || video.readyState < 2) { setTimeout(tick, 250); return; }
      read().then(function (value) {
        if (value) {
          var code = value.indexOf("/t/") >= 0 ? value.split("/t/")[1].replace(/\/$/, "") : value;
          submit(code);
        }
      }).catch(function () {}).then(function () { setTimeout(tick, 250); });
    }
    tick();
  }

  startButton.addEventListener("click", startCamera);
  setOnline();
})();
