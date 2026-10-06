/* QKD dashboard. Talks to the FastAPI backend (POST /api/run, POST /api/qiskit-demo).
   Open the page from the backend (http://localhost:8000) or pass ?api=http://host:port */
(() => {
  "use strict";

  const API = (new URLSearchParams(location.search).get("api") || window.API_BASE || "").replace(/\/$/, "");
  const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const $ = (sel) => document.querySelector(sel);
  const num = (n) => Number(n).toLocaleString("en-US");
  const pct = (x, d = 1) => `${(x * 100).toFixed(d)}%`;
  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const SVGNS = "http://www.w3.org/2000/svg";

  const el = {
    stage: $("#stage"), status: $("#stageStatus"), sub: $("#stageSub"),
    photons: $("#photons"), eveNode: $("#eveNode"), eveName: $("#eveName"), eveRole: $("#eveRole"),
    qubits: $("#qubits"), noise: $("#noise"), noiseOut: $("#noiseOut"),
    eve: $("#eve"), eveRate: $("#eveRate"), eveRateOut: $("#eveRateOut"), eveMid: $("#eveMid"),
    run: $("#runBtn"), form: $("#controls"),
    steps: $("#steps"), verdict: $("#verdict"), ground: $("#ground"),
    chart: $("#chart"), chartNote: $("#chartNote"),
    recAlice: $("#recAlice"), recWire: $("#recWire"), recBob: $("#recBob"),
    qkBtn: $("#qkBtn"), qkStatus: $("#qkStatus"), qkOut: $("#qkOut"),
    qkSummary: $("#qkSummary"), qkCircuit: $("#qkCircuit"), qkTable: $("#qkTable tbody"),
  };

  /* ---------------------------------------------------------------- controls */
  // Each preset also sets the qubit count: key length depends on it, and the demo
  // scenarios are tuned at 8,192 qubits so they behave the same way every time.
  const PRESETS = {
    clean:  { qubits: 8192, noise: 2, eve: false, rate: 100, mid: false },
    noisy:  { qubits: 8192, noise: 5, eve: false, rate: 100, mid: false },
    attack: { qubits: 8192, noise: 2, eve: true,  rate: 100, mid: false },
  };

  function syncLabels() {
    el.noiseOut.textContent = `${el.noise.value}%`;
    el.eveRateOut.textContent = `${el.eveRate.value}%`;
    el.eveRate.disabled = !el.eve.checked;
    el.eveMid.disabled = !el.eve.checked;
    const on = el.eve.checked;
    el.eveNode.classList.toggle("eve-off", !on);
    el.eveName.textContent = on ? "Eve is listening" : "Eve is off";
    el.eveRole.textContent = on ? `Intercepts ${el.eveRate.value}%` : "Not listening";
  }

  function clearPresetHighlight() {
    document.querySelectorAll("[data-preset]").forEach((b) => b.setAttribute("aria-pressed", "false"));
  }

  function applyPreset(name) {
    const p = PRESETS[name];
    el.qubits.value = p.qubits;
    el.noise.value = p.noise;
    el.eve.checked = p.eve;
    el.eveRate.value = p.rate;
    el.eveMid.checked = p.mid;
    syncLabels();
    document.querySelectorAll("[data-preset]").forEach((b) =>
      b.setAttribute("aria-pressed", String(b.dataset.preset === name)));
  }

  document.querySelectorAll("[data-preset]").forEach((b) =>
    b.addEventListener("click", () => applyPreset(b.dataset.preset)));
  [el.qubits, el.noise, el.eve, el.eveRate, el.eveMid].forEach((c) =>
    c.addEventListener("input", () => { syncLabels(); clearPresetHighlight(); }));

  const params = () => ({
    n_qubits: Number(el.qubits.value),
    noise: Number(el.noise.value) / 100,
    eve: el.eve.checked,
    eve_rate: Number(el.eveRate.value) / 100,
    eve_start: el.eveMid.checked ? 0.5 : 0,
  });

  /* ------------------------------------------------------------ photon stream */
  // Purely illustrative: dots stand for qubits crossing the link. Violet = Z basis,
  // white = X basis. Past Eve, some dots turn red to show a disturbed qubit.
  const WIRE = { x0: 130, x1: 770, y: 120, eveX: 450 };
  let photons = [];
  let streaming = false;
  let raf = 0;
  let last = 0;
  let spawnAcc = 0;
  let streamCfg = { eve: false, rate: 1 };

  function spawnPhoton() {
    const c = document.createElementNS(SVGNS, "circle");
    const z = Math.random() < 0.5;
    c.setAttribute("r", z ? "6" : "5");
    c.setAttribute("class", `photon ${z ? "z" : "x"}`);
    c.setAttribute("cy", WIRE.y + (Math.random() * 10 - 5));
    c.setAttribute("cx", WIRE.x0);
    el.photons.appendChild(c);
    photons.push({ node: c, x: WIRE.x0, v: 260 + Math.random() * 90, passedEve: false });
  }

  function frame(t) {
    const dt = Math.min(0.05, (t - last) / 1000 || 0);
    last = t;
    if (streaming) {
      spawnAcc += dt * 16;
      while (spawnAcc >= 1) { spawnPhoton(); spawnAcc -= 1; }
    }
    photons = photons.filter((p) => {
      p.x += p.v * dt;
      if (!p.passedEve && p.x >= WIRE.eveX) {
        p.passedEve = true;
        if (streamCfg.eve && Math.random() < streamCfg.rate && Math.random() < 0.5) {
          p.node.setAttribute("class", "photon hit");
        }
      }
      if (p.x >= WIRE.x1) { p.node.remove(); return false; }
      p.node.setAttribute("cx", p.x.toFixed(1));
      return true;
    });
    if (streaming || photons.length) raf = requestAnimationFrame(frame);
    else raf = 0;
  }

  function startStream(cfg) {
    if (reduceMotion) return;
    streamCfg = { eve: cfg.eve, rate: cfg.eve_rate };
    streaming = true;
    if (!raf) { last = performance.now(); raf = requestAnimationFrame(frame); }
  }
  function stopStream() { streaming = false; }

  /* ---------------------------------------------------------------- rendering */
  function setStage(state, status, sub) {
    el.stage.dataset.state = state;
    el.status.textContent = status;
    el.sub.textContent = sub;
  }

  function resetResults() {
    el.steps.innerHTML = "";
    el.verdict.hidden = true;
    el.ground.hidden = true;
    el.chart.innerHTML = "";
    setPre(el.recAlice, "Run a session to prepare the record.", "blank");
    setPre(el.recWire, "Nothing yet.", "blank mono wrap");
    setPre(el.recBob, "Nothing yet.", "blank");
  }

  function setPre(node, text, cls) { node.className = cls || ""; node.textContent = text; }

  function stepNode(s) {
    const li = document.createElement("li");
    li.className = "step";
    li.dataset.status = s.status;
    const glyph = s.status === "ok" ? "✓" : s.status === "abort" ? "✕" : "–";
    const facts = s.metrics.length
      ? `<dl class="facts">${s.metrics.map(([k, v]) => `<dt>${k}</dt><dd>${v}</dd>`).join("")}</dl>`
      : "";
    li.innerHTML = `<span class="mark" aria-hidden="true">${glyph}</span>
      <div><h3>${s.title}<span class="sr-only"> (${s.status === "ok" ? "passed" : s.status === "abort" ? "stopped the session" : "skipped"})</span></h3>
      <p class="why">${s.note}</p>${facts}</div>`;
    return li;
  }

  async function revealSteps(stages) {
    for (const s of stages) {
      el.steps.appendChild(stepNode(s));
      if (!reduceMotion) await sleep(s.status === "skipped" ? 120 : 380);
    }
  }

  function renderChart(data) {
    const W = 560, H = 240, L = 44, R = 64, T = 16, B = 44;
    const trace = data.qber_trace;
    const vals = trace.filter((b) => b.qber !== null).map((b) => b.qber);
    const yMax = Math.max(0.3, Math.ceil((Math.max(...vals, 0.12) + 0.02) * 10) / 10);
    const iw = W - L - R, ih = H - T - B;
    const y = (v) => T + ih - (v / yMax) * ih;
    const bw = iw / trace.length;
    const limit = data.stats.threshold;
    let svg = "";

    const ticks = [];
    for (let t = 0; t <= yMax + 1e-9; t += 0.1) ticks.push(t);
    ticks.forEach((t) => {
      svg += `<line class="grid-line" x1="${L}" x2="${W - R}" y1="${y(t)}" y2="${y(t)}"/>`;
      svg += `<text x="${L - 8}" y="${y(t) + 4}" text-anchor="end">${Math.round(t * 100)}%</text>`;
    });
    trace.forEach((b, i) => {
      if (b.qber === null) return;
      const h = Math.max(1.5, (b.qber / yMax) * ih);
      const cls = b.qber > limit ? "hi" : "ok";
      svg += `<rect class="bar ${cls}" x="${L + i * bw + 3}" y="${T + ih - h}" width="${bw - 6}" height="${h}" rx="2">
        <title>Qubits ${num(b.start)} to ${num(b.end)}: ${pct(b.qber)} error rate (${b.n} bits checked)</title></rect>`;
    });
    svg += `<line class="limit" x1="${L}" x2="${W - R + 4}" y1="${y(limit)}" y2="${y(limit)}"/>`;
    svg += `<text class="limit-label" x="${W - R + 8}" y="${y(limit) + 4}" text-anchor="start">11% limit</text>`;
    svg += `<text x="${L}" y="${H - 22}" text-anchor="start">0</text>`;
    svg += `<text x="${L + iw / 2}" y="${H - 22}" text-anchor="middle">${num(data.params.n_qubits / 2)}</text>`;
    svg += `<text x="${W - R}" y="${H - 22}" text-anchor="end">${num(data.params.n_qubits)}</text>`;
    svg += `<text x="${L + iw / 2}" y="${H - 6}" text-anchor="middle">Position in the qubit stream</text>`;
    el.chart.innerHTML = svg;
  }

  function renderRecord(data) {
    const r = data.record;
    setPre(el.recAlice, r.plaintext, "");
    if (r.status === "blocked") {
      setPre(el.recWire, "Nothing was sent.", "blank mono wrap");
      setPre(el.recBob, "Nothing received. With no secure key, Alice never sent the record.", "no");
      return;
    }
    const shown = r.ciphertext_hex.length > 240 ? r.ciphertext_hex.slice(0, 240) + "…" : r.ciphertext_hex;
    setPre(el.recWire, `${shown}\n\n${r.ciphertext_bytes} bytes, AES-256-GCM. Without the key this is noise.`, "sealed mono wrap");
    setPre(el.recBob, r.decrypted === null ? "Decryption failed." : r.decrypted, r.decrypted === null ? "no" : "ok");
  }

  function explain(data) {
    const s = data.stats;
    const qberStage = data.stages.find((x) => x.id === "qber");
    if (data.status === "secure") {
      return {
        state: "secure",
        status: "Secure link: key established",
        sub: `${num(s.final_key_bits)} secret bits from ${num(s.n_sent)} qubits. Bob decrypted the record.`,
        verdict: ["good", `Error rate ${pct(s.qber_est)} is within what noise explains, so nobody was detected on the line.`],
      };
    }
    if (qberStage && qberStage.status === "abort") {
      return {
        state: "breach",
        status: "Eavesdropper detected",
        sub: `Error rate ${pct(s.qber_est)} is above the 11% limit. No key was made and the record stayed with Alice.`,
        verdict: ["bad", "Eve had to measure each qubit, and measuring changes it. That showed up as extra errors Alice and Bob could not explain by noise."],
      };
    }
    return {
      state: "weak",
      status: "Session aborted: not enough secure key",
      sub: `${data.reason} Lower the noise or send more qubits and run again.`,
      verdict: ["weak", `Error rate ${pct(s.qber_est)} passed the 11% limit, but after removing leaked bits and a safety margin too little secret key was left. Noise or a partial eavesdropper can both cause this.`],
    };
  }

  function finish(data) {
    const x = explain(data);
    setStage(x.state, x.status, x.sub);
    el.verdict.className = `verdict ${x.verdict[0]}`;
    el.verdict.textContent = x.verdict[1];
    el.verdict.hidden = false;
    if (data.params.eve) {
      el.ground.textContent = `Simulation ground truth, which a real link cannot see: Eve learned ${pct(data.stats.sim_eve_known_fraction, 0)} of the bits left after sampling.`;
      el.ground.hidden = false;
    }
    renderChart(data);
    renderRecord(data);
  }

  /* --------------------------------------------------------------------- run */
  let busy = false;
  function setBusy(b) {
    busy = b;
    el.run.disabled = b;
    el.run.textContent = b ? "Running…" : "Run session";
  }

  async function postJSON(path, body) {
    const res = await fetch(API + path, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    });
    if (!res.ok) throw new Error(`${res.status} ${await res.text()}`);
    return res.json();
  }

  function showFailure(err) {
    stopStream();
    setStage("breach", "Cannot reach the backend",
      "Start it from the project folder with: uvicorn backend.main:app, then reload this page.");
    el.verdict.className = "verdict bad";
    el.verdict.textContent = `Request failed: ${String(err.message || err).slice(0, 160)}`;
    el.verdict.hidden = false;
  }

  el.form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (busy) return;
    const p = params();
    setBusy(true);
    resetResults();
    setStage("running", "Sending qubits…", "Alice encodes each bit in a random basis. Bob measures in a random basis.");
    startStream(p);
    try {
      const [data] = await Promise.all([postJSON("/api/run", p), sleep(reduceMotion ? 0 : 1600)]);
      await revealSteps(data.stages);
      finish(data);
    } catch (err) {
      showFailure(err);
    } finally {
      stopStream();
      setBusy(false);
    }
  });

  /* ------------------------------------------------------------------ qiskit */
  el.qkBtn.addEventListener("click", async () => {
    el.qkBtn.disabled = true;
    el.qkStatus.textContent = "Running circuits…";
    try {
      const data = await postJSON("/api/qiskit-demo", {
        n: 12, eve: el.eve.checked, noise: Number(el.noise.value) / 100,
      });
      el.qkCircuit.textContent = data.circuit_ascii;
      el.qkSummary.textContent = data.kept
        ? `${data.kept} of ${data.n} qubits kept after sifting. Error rate on kept qubits: ${pct(data.qber, 0)}. ` +
          (data.eve ? "Eve was on, so errors can appear." : "")
        : "No qubits matched bases this time. Run it again.";
      el.qkTable.innerHTML = data.rows.map((r) => {
        const outcome = !r.kept ? ["out-drop", "dropped"] : r.error ? ["out-err", "error"] : ["out-kept", "kept"];
        return `<tr><td>${r.i}</td><td>${r.alice_bit} in ${r.alice_basis}</td>
          <td>${r.eve_basis ? `basis ${r.eve_basis}` : "none"}</td>
          <td>${r.bob_bit} in ${r.bob_basis}</td><td class="${outcome[0]}">${outcome[1]}</td></tr>`;
      }).join("");
      el.qkOut.hidden = false;
      el.qkStatus.textContent = "";
    } catch (err) {
      el.qkStatus.textContent = `Qiskit run failed: ${String(err.message || err).slice(0, 140)}`;
    } finally {
      el.qkBtn.disabled = false;
    }
  });

  syncLabels();
  applyPreset("clean");
})();
