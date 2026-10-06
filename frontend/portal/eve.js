/* Link console: operator controls for the simulated fibre and a live view of the wire.
   Text from the wire is inserted with textContent only. */
"use strict";
(() => {
  const $ = (id) => document.getElementById(id);
  const post = (path, body) => fetch(path, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body || {}) }).then((r) => r.json());
  const PRESETS = {
    clean:  { eve: false, noise: 0.02, tamper: false },
    noisy:  { eve: false, noise: 0.05, tamper: false },
    eve:    { eve: true, eve_rate: 1.0, eve_start: 0.0, noise: 0.02, tamper: false },
    tamper: { eve: false, noise: 0.02, tamper: true },
  };
  let last = 0;
  let cfg = {};
  const groups = new Map(); // sid -> {li, n}: error-correction chatter collapsed into one line per session

  function el(tag, cls, text) {
    const e = document.createElement(tag);
    if (cls) e.className = cls;
    if (text != null) e.textContent = text;
    return e;
  }

  // ---------------------------------------------------------------- controls
  const sliders = { noise: 100, eve_rate: 100, eve_start: 100 };
  function paintControls() {
    $("eve").checked = !!cfg.eve;
    $("tamper").checked = !!cfg.tamper;
    for (const [k, scale] of Object.entries(sliders)) {
      const input = $(k);
      if (document.activeElement !== input) input.value = String(Math.round(cfg[k] * scale * 10) / 10);
      $(k + "_o").textContent = `${(+input.value).toFixed(k === "noise" ? 1 : 0)}%`;
    }
    $("eve_rate").disabled = $("eve_start").disabled = !cfg.eve;
    for (const b of document.querySelectorAll("[data-preset]")) {
      const p = PRESETS[b.dataset.preset];
      b.setAttribute("aria-pressed", String(Object.entries(p).every(([k, v]) => Math.abs((cfg[k] ?? 0) - v) < 1e-9 || cfg[k] === v)
        && (p.eve || !cfg.eve)));
    }
  }

  function paintStats(s) {
    const rows = [["Qubits sent", s.qubits_sent, false], ["Intercepted by Eve", s.qubits_intercepted, s.qubits_intercepted > 0],
      ["Bits Eve knows exactly", s.eve_exact_bits, s.eve_exact_bits > 0], ["Public messages", s.public_messages, false],
      ["Messages altered", s.tampered_messages, s.tampered_messages > 0]];
    $("stats").replaceChildren(...rows.flatMap(([k, v, hot]) => [el("dt", "", k), el("dd", hot ? "hot" : "", v.toLocaleString())]));
  }

  function send(change) {
    post("/api/config", change).then((r) => { cfg = r.config; paintControls(); paintStats(r.stats); });
  }
  $("eve").addEventListener("change", (e) => send({ eve: e.target.checked }));
  $("tamper").addEventListener("change", (e) => send({ tamper: e.target.checked }));
  for (const [k, scale] of Object.entries(sliders)) {
    $(k).addEventListener("input", () => { $(k + "_o").textContent = `${(+$(k).value).toFixed(k === "noise" ? 1 : 0)}%`; });
    $(k).addEventListener("change", () => send({ [k]: +$(k).value / scale }));
  }
  for (const b of document.querySelectorAll("[data-preset]")) b.addEventListener("click", () => send(PRESETS[b.dataset.preset]));
  $("clear").addEventListener("click", () => post("/api/wire/clear").then(() => { $("log").replaceChildren(); groups.clear(); $("empty").hidden = false; }));

  // ------------------------------------------------------------------ wire log
  const time = (t) => new Date(t * 1000).toLocaleTimeString([], { hour12: false });
  function preview(p) {
    if (p == null) return "";
    const s = typeof p === "string" ? p : JSON.stringify(p);
    return s.length > 320 ? s.slice(0, 320) + "…" : s;
  }

  function entryNode(e) {
    const bad = e.tampered || (e.status && e.status >= 400);
    const li = el("li", `entry ${e.type}${bad ? " bad" : ""}`);
    li.append(el("span", "when", time(e.t)));
    if (e.type === "quantum") {
      li.append(el("span", "tag", "Fibre"));
      const w = el("span", "what", `${e.n.toLocaleString()} qubits in flight (session ${String(e.sid).slice(0, 6)}). `);
      w.append(e.eve
        ? el("span", "flag", `Eve intercepted ${e.intercepted.toLocaleString()} and knows ${e.eve_exact.toLocaleString()} bits exactly. `)
        : document.createTextNode("No eavesdropper. "), document.createTextNode(`Noise ${(e.noise * 100).toFixed(1)}%.`));
      li.append(w);
    } else if (e.type === "public") {
      li.append(el("span", "tag", e.dir));
      const w = el("span", "what", `${e.kind || "?"}, ${e.bytes.toLocaleString()} bytes`);
      if (e.status && e.status >= 400) w.append(el("span", "flag", ` · refused (${e.status})`));
      if (e.tampered) w.append(el("span", "flag", " · altered in flight"));
      li.append(w);
      const pv = preview(e.preview);
      if (pv) li.append(el("span", "preview", pv));
    } else {
      li.append(el("span", "tag", "Console"), el("span", "what", e.text || ""));
    }
    return li;
  }

  // Hundreds of parity questions and answers per session would bury the interesting lines.
  // Normal ones are folded into one line per session; altered or refused ones always show.
  const isChatter = (e) => e.type === "public" && String(e.kind || "").startsWith("ec_answer") && !e.tampered && !(e.status && e.status >= 400);
  function fold(e, log) {
    let g = groups.get(e.sid);
    if (!g || !g.li.isConnected) {
      const li = el("li", "entry public");
      li.append(el("span", "when", time(e.t)), el("span", "tag", "Alice \u2194 Bob"), el("span", "what"));
      g = { li, n: 0 };
      groups.set(e.sid, g);
      log.prepend(li);
    }
    g.n += 1;
    g.li.querySelector(".what").textContent = `Error correction: ${g.n} parity questions and answers (session ${String(e.sid).slice(0, 6)}). Parities of random blocks, never the bits themselves.`;
  }

  async function tick() {
    if (document.hidden) return;
    let r;
    try { r = await (await fetch("/api/wire?after=" + last)).json(); } catch { return; }
    cfg = r.config; paintControls(); paintStats(r.stats);
    if ($("pause").checked || !r.entries.length) return;
    last = r.last;
    const log = $("log");
    for (const e of r.entries) {  // oldest first, so each prepend leaves the newest on top
      if ($("showec").checked || !isChatter(e)) log.prepend(entryNode(e)); else fold(e, log);
    }
    while (log.children.length > 300) log.lastChild.remove();
    $("empty").hidden = true;
  }
  tick();
  setInterval(tick, 1000);
})();
