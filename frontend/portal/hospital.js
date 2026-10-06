/* Hospital portal. One script serves both hospitals: /api/node says which one this is.
   Everything that comes from the server is put on the page with textContent (through h()),
   never as HTML, so record text cannot run as script. */
"use strict";
(() => {
  // ------------------------------------------------------------------ helpers
  const app = document.getElementById("app");

  function h(tag, attrs, ...kids) {
    const el = document.createElement(tag);
    for (const [k, v] of Object.entries(attrs || {})) {
      if (v === false || v == null) continue;
      if (k === "class") el.className = v;
      else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
      else el.setAttribute(k, v === true ? "" : v);
    }
    for (const kid of kids.flat(Infinity)) {
      if (kid == null || kid === false) continue;
      el.append(kid instanceof Node ? kid : document.createTextNode(String(kid)));
    }
    return el;
  }

  let memoryToken = null;
  const tokenStore = {
    get() { try { return sessionStorage.getItem("mediqkd.token") || memoryToken; } catch { return memoryToken; } },
    set(v) {
      memoryToken = v;
      try { v ? sessionStorage.setItem("mediqkd.token", v) : sessionStorage.removeItem("mediqkd.token"); } catch { /* storage blocked */ }
    },
  };

  async function api(path, { method = "GET", body } = {}) {
    const headers = {};
    const token = tokenStore.get();
    if (token) headers.Authorization = "Bearer " + token;
    if (body !== undefined) headers["Content-Type"] = "application/json";
    let res;
    try {
      res = await fetch(path, { method, headers, body: body === undefined ? undefined : JSON.stringify(body) });
    } catch {
      return { ok: false, status: 0, data: { detail: "Cannot reach this service. Check that it is running." } };
    }
    let data = null;
    try { data = await res.json(); } catch { /* empty body */ }
    if (res.status === 401 && token && !path.startsWith("/api/auth/login")) {
      signedOut("Your session ended. Sign in again.");
    }
    return { ok: res.ok, status: res.status, data, retry: res.headers.get("Retry-After") };
  }

  function errText(r) {
    const d = r.data && (r.data.detail ?? r.data.error);
    if (typeof d === "string") return d;
    if (Array.isArray(d) && d[0]) {
      const where = (d[0].loc || []).filter((x) => x !== "body").join(" ");
      return where ? `${where}: ${d[0].msg}` : d[0].msg || "Check the form and try again.";
    }
    if (d && d.message) return d.message;
    return `Something went wrong (${r.status}).`;
  }

  const fmtTime = (ts) => (ts ? new Date(ts * 1000).toLocaleString([], { dateStyle: "medium", timeStyle: "short" }) : "–");
  const fmtSeconds = (ms) => (ms == null ? "–" : (ms / 1000).toFixed(1) + " s");
  const pct = (x) => (x == null ? "–" : (x * 100).toFixed(1) + "%");
  function inWords(ts) {
    const s = Math.round(ts - Date.now() / 1000);
    if (s <= 0) return "now";
    if (s < 90) return `${s} s`;
    if (s < 5400) return `${Math.round(s / 60)} min`;
    return `${(s / 3600).toFixed(1)} h`;
  }
  const humanEvent = (e) => e.replace(/_/g, " ").replace(/^./, (c) => c.toUpperCase()).replace(/\bqkd\b/gi, "QKD");

  // ------------------------------------------------------------------- state
  let node = null;      // {role, name, peer_name, key_source, key_ttl}
  let user = null;      // {username, role}
  let railTimer = null;
  let viewTimer = null;
  let railEls = null;
  let currentTab = null;

  const isAlice = () => node && node.role === "alice";

  // ------------------------------------------------------------------- boot
  async function boot() {
    const r = await api("/api/node");
    if (!r.ok) {
      app.replaceChildren(h("p", { class: "empty", style: "padding:32px" }, "This service is not responding. Start it, then reload."));
      return;
    }
    node = r.data;
    document.body.dataset.node = node.role;
    document.title = `${node.name} – MediQKD`;
    if (tokenStore.get()) {
      const me = await api("/api/auth/me");
      if (me.ok) { user = me.data; return enter(); }
      tokenStore.set(null);
    }
    showLogin();
  }

  function signedOut(message) {
    tokenStore.set(null);
    user = null;
    clearInterval(railTimer); clearInterval(viewTimer);
    showLogin(message);
  }

  // ------------------------------------------------------------------ login
  function showLogin(message) {
    const sends = isAlice();
    const side = h("div", { class: "login-side" },
      h("h1", {}, node.name),
      h("p", {}, sends
        ? `Send patient records to ${node.peer_name}. Each record is encrypted with a one-time key made by quantum key distribution.`
        : `Receive patient records from ${node.peer_name}. Each record arrives encrypted with a one-time key that only the two hospitals share.`),
      h("p", {}, node.key_source === "etsi014"
        ? "Keys come from a key management server using the ETSI GS QKD 014 interface."
        : "The quantum link in this build is simulated. Use synthetic patient data only."));
    const err = h("div", { role: "alert" });
    if (message) err.append(h("div", { class: "notice warn" }, message));
    const form = h("form", { class: "login-form", autocomplete: "on" },
      h("h2", {}, "Sign in"),
      err,
      h("div", { class: "field" }, h("label", { for: "u" }, "Username"), h("input", { id: "u", type: "text", name: "username", autocomplete: "username", required: true, autocapitalize: "none", spellcheck: "false" })),
      h("div", { class: "field" }, h("label", { for: "p" }, "Password"), h("input", { id: "p", type: "password", name: "password", autocomplete: "current-password", required: true })),
      h("button", { class: "btn", type: "submit" }, "Sign in"));
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const btn = form.querySelector("button");
      btn.disabled = true;
      const r = await api("/api/auth/login", { method: "POST", body: { username: form.username.value.trim(), password: form.password.value } });
      btn.disabled = false;
      if (!r.ok) {
        err.replaceChildren(h("div", { class: "notice bad" }, r.status === 429 && r.retry ? `${errText(r)} Try again in ${r.retry} s.` : errText(r)));
        form.password.value = "";
        form.password.focus();
        return;
      }
      tokenStore.set(r.data.token);
      user = r.data.user;
      enter();
    });
    app.replaceChildren(h("div", { class: "login" }, side, form));
    form.username.focus();
  }

  // -------------------------------------------------------------- app shell
  function tabsFor() {
    const keys = { id: "keys", label: "Keys and sessions", render: viewKeys };
    const audit = { id: "audit", label: "Audit log", render: viewAudit };
    if (user.role === "clinician") return [isAlice() ? { id: "records", label: "Records", render: viewRecords } : { id: "inbox", label: "Inbox", render: viewInbox }, keys];
    if (user.role === "auditor") return [audit, keys];
    return [keys, { id: "users", label: "Users", render: viewUsers }, audit];
  }

  function enter() {
    const tabs = tabsFor();
    railEls = buildRail();
    const tabBar = h("div", { class: "tabs", role: "tablist", "aria-label": "Sections" },
      tabs.map((t) => h("button", { class: "tab", role: "tab", id: "tab-" + t.id, "aria-selected": "false", "aria-controls": "view", type: "button",
        onclick: () => openTab(t.id) }, t.label)));
    tabBar.addEventListener("keydown", (ev) => {
      if (ev.key !== "ArrowRight" && ev.key !== "ArrowLeft") return;
      const i = tabs.findIndex((t) => t.id === currentTab);
      const next = tabs[(i + (ev.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length];
      openTab(next.id);
      document.getElementById("tab-" + next.id).focus();
    });
    app.replaceChildren(h("div", { class: "shell" },
      railEls.root,
      h("main", { class: "main" },
        h("h1", { id: "page-title" }),
        tabBar,
        h("div", { id: "notices", role: "status", "aria-live": "polite" }),
        h("div", { id: "view", role: "tabpanel", tabindex: "-1" }))));
    openTab(tabs[0].id);
    refreshRail();
    clearInterval(railTimer);
    railTimer = setInterval(() => { if (!document.hidden) refreshRail(); }, 5000);
  }

  function openTab(id, keepNotice = false) {
    const t = tabsFor().find((x) => x.id === id);
    if (!t) return;
    clearInterval(viewTimer);
    currentTab = id;
    document.querySelectorAll(".tab").forEach((b) => b.setAttribute("aria-selected", String(b.id === "tab-" + id)));
    document.getElementById("page-title").textContent = t.label;
    if (!keepNotice) document.getElementById("notices").replaceChildren();
    const view = document.getElementById("view");
    view.replaceChildren();
    t.render(view);
  }

  function say(kind, title, text) {
    document.getElementById("notices").replaceChildren(h("div", { class: "notice " + kind }, h("strong", {}, title), text || ""));
  }

  // --------------------------------------------------------------- the rail
  function buildRail() {
    const els = {
      linkDot: h("span", { class: "dot" }), linkText: h("span", {}, "Checking the link"),
      linkNote: h("p", { class: "fine" }), count: h("div", { class: "big" }), cells: h("div", { class: "cells", role: "img" }),
      poolNote: h("p", { class: "fine" }), expiry: h("p", { class: "fine" }), auth: h("div", { class: "fine" }),
    };
    els.summary = h("span", {}, "Link and keys");
    const more = h("details", { class: "rail-more" }, h("summary", {}, els.summary));
    const head = h("div", {}, h("h2", {}, node.name), h("p", { class: "role-line" }, isAlice() ? `Sends records to ${node.peer_name}` : `Receives records from ${node.peer_name}`));
    const sections = [
      h("section", { "aria-label": "Link status" }, h("h3", {}, "Secure link"), h("div", { class: "link-state" }, els.linkDot, els.linkText), els.linkNote),
      h("section", { "aria-label": "Key pool" }, h("h3", {}, "One-time keys"), els.count, els.cells, els.poolNote, els.expiry),
      h("section", { "aria-label": "Channel signing key" }, h("h3", {}, "Channel signing key"), els.auth),
    ];
    if (isAlice() && (user.role === "clinician" || user.role === "admin")) {
      els.make = h("button", { class: "btn small", type: "button", onclick: makeKeys }, "Make keys now");
      sections.push(h("div", {}, els.make));
    }
    more.append(h("div", { class: "rail-body" }, sections));
    const narrow = window.matchMedia("(max-width: 960px)");
    const fit = () => { more.open = !narrow.matches; };  // open on wide screens, folded on phones
    fit();
    narrow.addEventListener("change", fit);
    const out = [head, more];
    out.push(h("div", { class: "who" },
      h("p", {}, "Signed in as ", h("strong", {}, user.username), h("span", { class: "fine" }, ` (${user.role})`)),
      h("button", { class: "btn small", type: "button", onclick: async () => { await api("/api/auth/logout", { method: "POST" }); signedOut(); } }, "Sign out")));
    els.root = h("aside", { class: "rail", "aria-label": "Link and keys" }, out);
    return els;
  }

  const cellStates = ["available", "reserved", "used", "expired"];
  function paintRail(keys, link) {
    const e = railEls;
    if (!e) return;
    if (link) {
      const up = !!link.reachable;
      e.linkDot.className = "dot " + (up ? "up" : "down");
      e.linkUp = up;
      e.linkText.textContent = link.source === "etsi014"
        ? (up ? "Key server reachable" : "Key server not reachable")
        : (up ? `Link to ${node.peer_name} is up` : "Link service not responding");
      const last = link.last_session;
      e.linkNote.textContent = link.reason ? link.reason
        : last ? `Last key session: ${last.status === "ok" ? "keys made" : last.status} in ${fmtSeconds(last.elapsed_ms)}${last.reason ? ". " + last.reason : ""}`
        : link.source === "etsi014" ? `${link.kme_stored_keys ?? "?"} keys waiting at the key server` : "Simulated quantum link";
    }
    if (keys) {
      const p = keys.pool;
      e.count.replaceChildren(String(p.available), h("small", {}, p.available === 1 ? "key ready" : "keys ready"));
      const order = [];
      for (const s of cellStates) for (let i = 0; i < (p[s] || 0); i++) order.push(s);
      const shown = order.slice(0, 24);
      e.cells.replaceChildren(...(shown.length ? shown : Array(8).fill("empty")).map((s) => h("span", { class: "cell " + s })));
      e.cells.setAttribute("aria-label", `${p.available} ready, ${p.reserved} reserved, ${p.used} used, ${p.expired} expired`);
      e.poolNote.textContent = `${p.used} used · ${p.expired} expired. One key encrypts one record, then is destroyed.`;
      e.expiry.textContent = p.next_expiry ? `Next key expires in ${inWords(p.next_expiry)}.` : "";
      e.keysReady = p.available;
      e.auth.textContent = p.auth_key_version > 1
        ? `Version ${p.auth_key_version}. Renewed from quantum key material after each key session.`
        : "Version 1. Starting secret, replaced after the first key session.";
    }
  }

  async function refreshRail() {
    const [k, l] = await Promise.all([api("/api/keys"), api("/api/link")]);
    paintRail(k.ok ? k.data : null, l.ok ? l.data : null);
    if (railEls && railEls.keysReady != null) {
      railEls.summary.textContent = `${railEls.linkUp ? "Link up" : "Link down"} · ${railEls.keysReady} ${railEls.keysReady === 1 ? "key" : "keys"} ready`;
    }
  }

  async function makeKeys() {
    const btn = railEls.make;
    btn.disabled = true; btn.textContent = "Making keys…";
    const r = await api("/api/keys/refill", { method: "POST" });
    btn.disabled = false; btn.textContent = "Make keys now";
    if (!r.ok) return say("bad", "Could not make keys", errText(r));
    if (r.data.status === "ok") say("ok", "New keys ready", `${r.data.keys_added} one-time keys added.`);
    else say(r.data.status === "aborted" ? "warn" : "bad", "No keys were made", r.data.reason || "");
    refreshRail();
    if (currentTab === "keys") openTab("keys", true);
  }

  // ----------------------------------------------- key session, stage by stage
  function gauge(stats) {
    const limit = stats.threshold ?? 0.11, max = 0.3, q = stats.qber;
    const g = h("div", { class: "gauge" + (q > limit ? " hot" : "") },
      h("div", { class: "gauge-track", role: "img", "aria-label": `Error rate ${pct(q)}, abort limit ${pct(limit)}` },
        h("span", { class: "gauge-limit" }), h("span", { class: "gauge-value" })),
      h("div", { class: "gauge-scale" }, h("span", {}, "0%"), h("span", {}, `Abort limit ${pct(limit)}`), h("span", {}, `${max * 100}%`)),
      h("p", { class: "gauge-caption" }, q > limit
        ? "Above the limit: more errors than a quiet fibre produces, so someone may be listening."
        : "Below the limit: consistent with ordinary fibre noise."));
    const track = g.querySelector(".gauge-track");
    track.style.setProperty("--limit", (limit / max * 100) + "%");
    track.style.setProperty("--at", (Math.min(q, max) / max * 100) + "%");
    return g;
  }

  function stageList(result) {
    const mark = { ok: "✓", abort: "!", skipped: "" };
    return h("ol", { class: "stages" }, (result.stages || []).map((s) =>
      h("li", { class: "stage " + s.status },
        h("span", { class: "mark", "aria-hidden": "true" }, mark[s.status] ?? ""),
        h("div", {},
          h("h3", {}, s.title, s.status === "skipped" ? h("span", { class: "muted" }, " (not reached)") : ""),
          s.status !== "skipped" && s.note ? h("p", { class: "note" }, s.note) : "",
          s.id === "qber" && result.stats && result.stats.qber != null ? gauge(result.stats) : "",
          s.metrics && s.metrics.length && s.status !== "skipped"
            ? h("dl", {}, s.metrics.map(([k, v]) => h("div", {}, h("dt", {}, k), h("dd", {}, v)))) : ""))));
  }

  function sessionSummary(result) {
    const kind = result.status === "ok" ? "ok" : result.status === "aborted" ? "warn" : "bad";
    const title = result.status === "ok" ? `Keys made in ${fmtSeconds(result.elapsed_ms)}`
      : result.status === "aborted" ? "The protocol refused to make a key" : "The key session failed";
    return h("div", { class: "notice " + kind }, h("strong", {}, title), result.reason || `${result.keys_added} new one-time keys added to the pool.`);
  }

  // --------------------------------------------------------- records (sender)
  async function viewRecords(view) {
    const transfer = h("div", { class: "transfer", hidden: true });
    const list = h("div", {});
    const formMsg = h("div", { role: "alert" });
    const f = h("form", {},
      h("h2", { style: "margin-bottom:14px" }, "New record"),
      formMsg,
      h("div", { class: "field" }, h("label", { for: "pref" }, "Patient reference"), h("input", { id: "pref", name: "patient_ref", type: "text", required: true, maxlength: "64", autocomplete: "off", spellcheck: "false", placeholder: "P-1001" }), h("span", { class: "hint" }, "A code, not a name. Letters, numbers, dot, dash, underscore.")),
      h("div", { class: "field" }, h("label", { for: "title" }, "Title"), h("input", { id: "title", name: "title", type: "text", required: true, maxlength: "200", autocomplete: "off" })),
      h("div", { class: "field" }, h("label", { for: "body" }, "Record"), h("textarea", { id: "body", name: "body", required: true, maxlength: "20000" }), h("span", { class: "hint" }, "Use synthetic data only. This build is not certified for real patient data.")),
      h("button", { class: "btn", type: "submit" }, "Save as draft"));
    f.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const r = await api("/api/records", { method: "POST", body: { patient_ref: f.patient_ref.value.trim(), title: f.title.value.trim(), body: f.body.value } });
      if (!r.ok) return formMsg.replaceChildren(h("div", { class: "notice bad" }, errText(r)));
      formMsg.replaceChildren();
      f.reset();
      say("ok", "Draft saved", `${r.data.title} is ready to send.`);
      load();
    });

    async function load() {
      const r = await api("/api/records");
      if (!r.ok) return list.replaceChildren(h("div", { class: "notice bad" }, errText(r)));
      if (!r.data.records.length) {
        list.replaceChildren(h("p", { class: "empty" }, `No records yet. Save a draft on the left, then send it to ${node.peer_name}.`));
        return;
      }
      list.replaceChildren(h("ul", { class: "rows" }, r.data.records.map(recordRow)));
    }

    function recordRow(rec) {
      const body = h("div", {});
      const sent = rec.status === "sent";
      const open = h("button", { class: "btn quiet small", type: "button", "aria-expanded": "false" }, "Open");
      open.addEventListener("click", async () => {
        if (open.getAttribute("aria-expanded") === "true") { body.replaceChildren(); open.setAttribute("aria-expanded", "false"); open.textContent = "Open"; return; }
        const r = await api("/api/records/" + rec.id);
        if (!r.ok) return say("bad", "Could not open the record", errText(r));
        body.replaceChildren(h("pre", { class: "record-body", style: "font-family:inherit;margin:12px 0 0" }, r.data.body));
        open.setAttribute("aria-expanded", "true"); open.textContent = "Close";
      });
      const send = h("button", { class: "btn small", type: "button" }, "Send securely");
      send.addEventListener("click", () => sendRecord(rec, send));
      return h("li", { class: "row" },
        h("div", { class: "row-main" },
          h("div", {},
            h("div", { class: "row-title" }, rec.title),
            h("div", { class: "row-meta" }, `${rec.patient_ref} · ${rec.created_by} · ${fmtTime(rec.created)}`,
              sent ? h("span", {}, ` · sent ${fmtTime(rec.sent_at)} with key `, h("span", { class: "mono" }, rec.key_id || "")) : "")),
          h("div", { class: "row-actions" },
            h("span", { class: "chip " + (sent ? "ok" : "") }, sent ? "Sent" : "Draft"), open, sent ? "" : send)),
        body);
    }

    async function sendRecord(rec, btn) {
      document.querySelectorAll(".row-actions .btn").forEach((b) => (b.disabled = true));
      const before = await api("/api/sessions/last");
      const priorSid = before.ok ? before.data.sid : null;
      transfer.hidden = false;
      transfer.replaceChildren(
        h("h2", {}, `Sending “${rec.title}”`),
        h("p", { class: "muted" }, `Securing a one-time key with ${node.peer_name}. This takes a few seconds when the pool is empty.`),
        h("div", { class: "bar", "aria-hidden": "true" }, h("i")));
      transfer.scrollIntoView({ block: "nearest", behavior: "smooth" });
      const r = await api(`/api/records/${rec.id}/send`, { method: "POST" });
      const after = await api("/api/sessions/last");
      const ran = after.ok && after.data.sid && after.data.sid !== priorSid ? after.data : null;
      const out = [h("h2", {}, `“${rec.title}”`)];
      if (r.ok) {
        out.push(h("div", { class: "notice ok" }, h("strong", {}, `Sent to ${node.peer_name}`),
          "Encrypted with one-time key ", h("span", { class: "mono" }, r.data.key_id), " (fingerprint ", h("span", { class: "mono" }, r.data.key_fingerprint),
          "). The key has been wiped and cannot be used again."));
      } else {
        const d = r.data && r.data.detail;
        const code = d && d.code;
        const session = (d && d.session) || ran;
        out.push(h("div", { class: "notice bad" },
          h("strong", {}, code === "no_secure_key" ? "Not sent: no secure key" : code === "peer_error" ? `Not sent: ${node.peer_name} refused the message` : "Not sent"),
          errText(r), " The record is still a draft.",
          h("div", { style: "margin-top:10px" }, h("button", { class: "btn small", type: "button", onclick: () => sendRecord(rec, btn) }, "Try again"))));
        if (session && session.stages) out.push(h("h3", { style: "margin:20px 0 12px" }, "What happened in the key session"), stageList(session));
        transfer.replaceChildren(...out);
        document.querySelectorAll(".row-actions .btn").forEach((b) => (b.disabled = false));
        load(); refreshRail();
        return;
      }
      if (ran) out.push(h("h3", { style: "margin:20px 0 12px" }, "A new key session ran first"), stageList(ran));
      else out.push(h("p", { class: "muted" }, "A key already in the pool was used, so no new key session was needed."));
      transfer.replaceChildren(...out);
      load(); refreshRail();
    }

    view.append(h("div", { class: "split" }, f, h("div", {}, transfer, h("div", { class: "section-head" }, h("h2", {}, "Outbox")), list)));
    load();
  }

  // ---------------------------------------------------------- inbox (receiver)
  async function viewInbox(view) {
    const list = h("div", {});
    const reader = h("div", {});
    let known = null;

    async function load() {
      const r = await api("/api/inbox");
      if (!r.ok) return list.replaceChildren(h("div", { class: "notice bad" }, errText(r)));
      const fresh = known ? r.data.records.filter((x) => !known.has(x.id)).map((x) => x.id) : [];
      known = new Set(r.data.records.map((x) => x.id));
      if (!r.data.records.length) {
        list.replaceChildren(h("p", { class: "empty" }, `Nothing received yet. Records sent by ${node.peer_name} appear here as soon as they arrive.`));
        return;
      }
      list.replaceChildren(h("ul", { class: "rows" }, r.data.records.map((rec) => {
        const open = h("button", { class: "btn quiet small", type: "button" }, "Open");
        open.addEventListener("click", async () => {
          const d = await api("/api/inbox/" + rec.id);
          if (!d.ok) return say("bad", "Could not open the record", errText(d));
          reader.replaceChildren(
            h("div", { class: "section-head" }, h("h2", {}, d.data.title), h("button", { class: "btn quiet small", type: "button", onclick: () => reader.replaceChildren() }, "Close")),
            h("p", { class: "row-meta" }, `Patient ${d.data.patient_ref} · from ${d.data.from}, sent by ${d.data.sent_by} · received ${fmtTime(d.data.received)}`),
            h("pre", { class: "record-body", style: "font-family:inherit" }, d.data.body),
            h("p", { class: "row-meta", style: "margin-top:10px" }, "Decrypted with one-time key ", h("span", { class: "mono" }, d.data.key_id), ", now wiped."));
          reader.scrollIntoView({ block: "nearest", behavior: "smooth" });
        });
        return h("li", { class: "row" + (fresh.includes(rec.id) ? " fresh" : "") },
          h("div", { class: "row-main" },
            h("div", {}, h("div", { class: "row-title" }, rec.title),
              h("div", { class: "row-meta" }, `${rec.patient_ref} · from ${rec.from}, sent by ${rec.sent_by} · ${fmtTime(rec.received)}`)),
            h("div", { class: "row-actions" }, h("span", { class: "chip ok" }, "Decrypted"), open)));
      })));
    }
    view.append(h("div", { class: "stack" }, reader, h("div", {}, h("div", { class: "section-head" }, h("h2", {}, "Received records"), h("span", { class: "muted" }, "Updates every few seconds")), list)));
    await load();
    viewTimer = setInterval(() => { if (!document.hidden) load(); }, 4000);
  }

  // ----------------------------------------------------- keys and sessions
  const sessionChip = (s) => ({ ok: ["ok", "Keys made"], aborted: ["warn", "Refused"], failed: ["bad", "Failed"], running: ["", "Running"] }[s] || ["", s]);

  async function viewKeys(view) {
    const [k, s, last] = await Promise.all([api("/api/keys"), api("/api/sessions"), isAlice() ? api("/api/sessions/last") : Promise.resolve(null)]);
    if (!k.ok) return view.append(h("div", { class: "notice bad" }, errText(k)));
    const p = k.data.pool;
    const parts = [];

    const facts = h("dl", { style: "display:flex;flex-wrap:wrap;gap:8px 40px;margin:0 0 16px" },
      [["Ready", p.available], ["Used", p.used], ["Expired", p.expired], ["Key size", `${p.key_bits} bits`], ["Lifetime", `${Math.round(k.data.ttl / 60)} min`],
        ["Source", k.data.source === "etsi014" ? "Key server (ETSI 014)" : "Simulated BB84 link"]]
        .map(([a, b]) => h("div", {}, h("dt", { class: "muted", style: "font-size:15px" }, a), h("dd", { style: "margin:0;font-weight:700;font-size:20px" }, String(b)))));
    const actions = h("div", { style: "display:flex;gap:8px;flex-wrap:wrap;align-items:center" });
    const confirmBox = h("div", {});
    if (isAlice() && user.role === "admin") {
      actions.append(h("button", { class: "btn quiet", type: "button", onclick: () => {
        confirmBox.replaceChildren(h("div", { class: "confirm", role: "alert" },
          h("span", {}, `Wipe all ${p.available + p.reserved} unused keys on both hospitals? Do this after a suspected eavesdropper or a staff change.`),
          h("button", { class: "btn danger small", type: "button", onclick: async () => {
            const r = await api("/api/keys/rotate", { method: "POST" });
            if (!r.ok) return say("bad", "Could not rotate keys", errText(r));
            say("ok", "Keys rotated", `${r.data.expired} unused keys wiped. ${r.data.peer_notified ? node.peer_name + " wiped its copies too." : node.peer_name + " was not reachable and will drop its copies when they expire."}`);
            openTab("keys", true); refreshRail();
          } }, "Rotate keys"),
          h("button", { class: "btn quiet small", type: "button", onclick: () => confirmBox.replaceChildren() }, "Cancel")));
      } }, "Rotate keys…"));
    }
    parts.push(h("section", {}, h("div", { class: "section-head" }, h("h2", {}, "Key pool")), facts, actions, confirmBox));

    if (last && last.ok && last.data.stages && last.data.stages.length) {
      parts.push(h("section", {}, h("h2", { style: "margin-bottom:12px" }, "Last key session"), sessionSummary(last.data), stageList(last.data)));
    }

    const sess = s.ok ? s.data.sessions : [];
    parts.push(h("section", {}, h("div", { class: "section-head" }, h("h2", {}, "Recent key sessions")),
      sess.length ? h("div", { class: "table-wrap" }, h("table", {},
        h("thead", {}, h("tr", {}, ["Started", "Result", "Error rate", "Secret bits", "Keys", "Took"].map((c) => h("th", {}, c)))),
        h("tbody", {}, sess.map((x) => { const [cls, label] = sessionChip(x.status); return h("tr", {},
          h("td", {}, fmtTime(x.started)),
          h("td", {}, h("span", { class: "chip " + cls }, label), x.reason ? h("div", { class: "row-meta" }, x.reason) : ""),
          h("td", {}, pct(x.qber)), h("td", {}, x.key_bits ?? "–"), h("td", {}, x.keys_added ?? "–"), h("td", {}, fmtSeconds(x.elapsed_ms))); }))))
        : h("p", { class: "empty" }, "No key sessions yet. The first record you send starts one.")));

    if (k.data.keys) {
      parts.push(h("section", {}, h("div", { class: "section-head" }, h("h2", {}, "Keys"), h("span", { class: "muted" }, "Identifiers and fingerprints only. The keys themselves are never shown.")),
        k.data.keys.length ? h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, ["Key", "State", "Fingerprint", "Made", "Expires", "Used"].map((c) => h("th", {}, c)))),
          h("tbody", {}, k.data.keys.map((x) => h("tr", {},
            h("td", { class: "mono" }, x.key_id), h("td", {}, h("span", { class: "chip " + (x.status === "available" ? "ok" : "") }, x.status)),
            h("td", { class: "mono" }, x.fingerprint || "–"), h("td", {}, fmtTime(x.created)), h("td", {}, fmtTime(x.expires_at)), h("td", {}, fmtTime(x.used_at)))))))
          : h("p", { class: "empty" }, "The pool has no keys yet.")));
    }
    view.append(h("div", { class: "stack" }, parts));
  }

  // ------------------------------------------------------------------ audit
  const ALERT = new Set(["eavesdropper_suspected", "auth_failure", "transfer_blocked", "transfer_failed", "message_rejected", "decrypt_failed", "login_failed", "login_throttled", "qkd_session_failed"]);
  const NOTE = new Set(["keys_rotated", "keys_expired", "user_disabled", "user_created", "qkd_session_aborted"]);
  const listText = (v) => (v.length > 3 ? `${v.slice(0, 3).join(", ")} and ${v.length - 3} more` : v.join(", "));
  const detailText = (d) => Object.entries(d || {}).map(([k, v]) => `${k}: ${Array.isArray(v) ? listText(v) : v}`).join("  ·  ");

  async function viewAudit(view) {
    const body = h("tbody", {});
    const verdict = h("div", { role: "status", "aria-live": "polite" });
    const more = h("button", { class: "btn quiet", type: "button", hidden: true }, "Load older entries");
    let before = null;

    async function load() {
      const r = await api("/api/audit?limit=100" + (before ? "&before=" + before : ""));
      if (!r.ok) return say("bad", "Could not load the audit log", errText(r));
      body.append(...r.data.entries.map((e) => h("tr", { class: ALERT.has(e.event) ? "alert" : NOTE.has(e.event) ? "note" : "" },
        h("td", {}, String(e.id)), h("td", {}, fmtTime(e.ts)), h("td", {}, humanEvent(e.event)), h("td", {}, e.actor), h("td", { class: "detail" }, detailText(e.detail)))));
      before = r.data.next_before;
      more.hidden = !before;
    }
    const verify = h("button", { class: "btn", type: "button" }, "Check the log has not been altered");
    verify.addEventListener("click", async () => {
      verify.disabled = true;
      const r = await api("/api/audit/verify");
      verify.disabled = false;
      if (!r.ok) return verdict.replaceChildren(h("div", { class: "notice bad" }, errText(r)));
      verdict.replaceChildren(r.data.ok
        ? h("div", { class: "notice ok" }, h("strong", {}, "Log is intact"), `All ${r.data.checked} entries chain correctly and the signed head matches.`)
        : h("div", { class: "notice bad" }, h("strong", {}, "Log was altered"), r.data.problem));
      body.replaceChildren(); before = null; load();
    });
    more.addEventListener("click", load);
    view.append(h("div", {},
      h("div", { class: "section-head" }, h("p", { class: "muted", style: "max-width:60ch" }, "Every sign-in, record, key and security event is written to a chain of signed entries. Changing or deleting one breaks the chain."), verify),
      verdict,
      h("div", { class: "table-wrap" }, h("table", {}, h("thead", {}, h("tr", {}, ["#", "Time", "Event", "Who", "Details"].map((c) => h("th", {}, c)))), body)),
      h("div", { style: "margin-top:16px" }, more)));
    load();
  }

  // ------------------------------------------------------------------ users
  async function viewUsers(view) {
    const r = await api("/api/users");
    if (!r.ok) return view.append(h("div", { class: "notice bad" }, errText(r)));
    const msg = h("div", { role: "alert" });
    const form = h("form", { class: "inline-form" },
      h("div", { class: "field" }, h("label", { for: "nu" }, "Username"), h("input", { id: "nu", name: "username", type: "text", required: true, minlength: "3", maxlength: "64", autocomplete: "off", autocapitalize: "none" })),
      h("div", { class: "field" }, h("label", { for: "np" }, "Password"), h("input", { id: "np", name: "password", type: "password", required: true, autocomplete: "new-password" })),
      h("div", { class: "field" }, h("label", { for: "nr" }, "Role"), h("select", { id: "nr", name: "role" }, r.data.roles.map((x) => h("option", { value: x }, x)))),
      h("button", { class: "btn", type: "submit" }, "Add user"));
    form.addEventListener("submit", async (ev) => {
      ev.preventDefault();
      const c = await api("/api/users", { method: "POST", body: { username: form.username.value.trim(), password: form.password.value, role: form.role.value } });
      if (!c.ok) return msg.replaceChildren(h("div", { class: "notice bad" }, errText(c)));
      say("ok", "User added", `${form.username.value.trim()} can sign in now.`);
      openTab("users", true);
    });
    view.append(h("div", { class: "stack" },
      h("section", {}, h("h2", { style: "margin-bottom:12px" }, "Add a user"), msg, form,
        h("p", { class: "muted", style: "max-width:62ch" }, "Clinicians create and read records. Auditors read the audit log and key activity but cannot see records. Admins manage users and keys but cannot see records.")),
      h("section", {}, h("h2", { style: "margin-bottom:12px" }, "Users"),
        h("div", { class: "table-wrap" }, h("table", {},
          h("thead", {}, h("tr", {}, ["Username", "Role", "Created", "State", ""].map((c) => h("th", {}, c)))),
          h("tbody", {}, r.data.users.map((u) => h("tr", {},
            h("td", {}, u.username), h("td", {}, u.role), h("td", {}, fmtTime(u.created)),
            h("td", {}, h("span", { class: "chip " + (u.disabled ? "bad" : "ok") }, u.disabled ? "Disabled" : "Active")),
            h("td", {}, u.disabled || u.username === user.username ? "" : h("button", { class: "btn quiet small", type: "button", onclick: async () => {
              const d = await api(`/api/users/${encodeURIComponent(u.username)}/disable`, { method: "POST" });
              if (!d.ok) return say("bad", "Could not disable the user", errText(d));
              say("ok", "User disabled", `${u.username} is signed out and cannot sign in.`);
              openTab("users", true);
            } }, "Disable"))))))))));
  }

  boot();
})();
