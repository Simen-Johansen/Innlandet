// Grant navigator web UI (task 017). Live mode talks to web/server.py; demo mode (GitHub Pages)
// shows the bundles in demo/. All data is inserted with textContent, never as HTML: grant text
// and project ideas are untrusted (stress cases 012).
"use strict";

const MAX_IDEA = 300;
const POLL_MS = 1500;
const STAGES = ["entity", "grants", "filter", "matcher", "guide", "render"];

const T = {
  no: {
    brand_sub: "for frivillige lag",
    hero_title: "Hvilke tilskudd kan laget søke?",
    demo_title: "Demo:",
    demo_text: "Dette er forhåndsberegnede eksempler. Velg et eksempel under. Egne søk krever at du kjører tjenesten lokalt.",
    orgnr_label: "Organisasjonsnummer",
    amount_label: "Omsøkt beløp (kr, valgfritt)",
    lang_label: "Språk på planen",
    idea_label: "Beskriv prosjektet med én setning",
    idea_placeholder: "F.eks. Gratis turdager med bål og kano for barn 6–12 år i Hamar",
    offline_label: "Offline (testdata fra fixtures/, ingen oppslag i Brønnøysund)",
    footer: "Tilskuddene er hentet fra de offisielle tilskuddssidene. Sjekk alltid fristen på tilskuddssiden før du søker.",
    submit: "Finn tilskudd",
    examples: "Eksempler",
    mode_live: "Live",
    mode_offline: "Live (offline-data)",
    mode_demo: "Demo",
    orgnr_empty: "Skriv inn organisasjonsnummeret (9 siffer).",
    orgnr_digits: "Organisasjonsnummeret har 9 siffer.",
    orgnr_mod11: "Kontrollsifferet stemmer ikke. Sjekk at du har skrevet nummeret riktig.",
    orgnr_ok: "Gyldig organisasjonsnummer",
    idea_empty: "Beskriv prosjektet.",
    idea_long: "Maks 300 tegn.",
    amount_bad: "Skriv et helt beløp i kroner, for eksempel 60000.",
    progress_title: "Vi sjekker laget og tilskuddene",
    progress_note: "Dette tar vanligvis 2–5 minutter. Du kan la siden stå åpen.",
    stage_entity: "Sjekker organisasjonen i Brønnøysundregistrene",
    stage_grants: "Leser tilskuddsordningene",
    stage_filter: "Sjekker hvem som kan søke",
    stage_matcher: "Vurderer om prosjektet passer",
    stage_guide: "Skriver veiledningen",
    stage_render: "Lager sjekklisten",
    attempt: "forsøk {a}/{n}",
    busy: "En annen kjøring pågår. Vent til den er ferdig og prøv igjen.",
    no_server: "Fikk ikke kontakt med den lokale serveren.",
    org_title: "Organisasjonen",
    org_name: "Navn",
    org_nr: "Organisasjonsnummer",
    org_form: "Organisasjonsform",
    org_kommune: "Kommunenummer",
    org_frivreg: "Frivillighetsregisteret",
    yes_registered: "Registrert",
    not_registered: "Ikke registrert",
    plan_title: "Tilskudd dere kan søke på",
    plan_one: "1 tilskudd passer prosjektet",
    plan_many: "{n} tilskudd passer prosjektet",
    sources: "Kontrollert automatisk mot de offisielle kildene hentet {date}. Sjekk alltid fristen på tilskuddssiden før du søker.",
    download: "Last ned sjekklisten (.md)",
    cost: "Modellkostnad for kjøringen: {usd} USD",
    generated_demo: "Eksempelet ble kjørt {date} med testdata.",
    deadline: "Søknadsfrist",
    max_amount: "Maks beløp",
    amount_unknown: "Ikke oppgitt på tilskuddssiden",
    why: "Hvorfor laget kvalifiserer",
    attachments: "Vedlegg",
    steps: "Slik søker dere",
    excluded_title: "Tilskudd dere ikke kvalifiserer for ({n})",
    excluded_none: "Ingen tilskudd ble valgt bort.",
    org_form_not_allowed: "Organisasjonsformen deres ({form}) kan ikke søke.",
    outside_region: "Tilskuddet gjelder ikke kommunen deres.",
    not_in_frivillighetsregisteret: "Krever at laget er registrert i Frivillighetsregisteret.",
    no_open_deadline: "Ingen åpen søknadsfrist nå.",
    matcher_prefix: "Passer ikke prosjektet: ",
    rej_title: "Vi kunne ikke lage en plan",
    rej_invalid_orgnr: "Organisasjonsnummeret er ikke gyldig. Sjekk at du har skrevet alle 9 sifrene riktig.",
    rej_invalid_request: "Noe i skjemaet mangler eller er feil. Sjekk feltene og prøv igjen.",
    rej_not_found: "Vi fant ikke organisasjonsnummeret i Enhetsregisteret.",
    rej_outside_innlandet: "Laget er ikke registrert i en kommune i Innlandet. Tjenesten dekker bare lag i Innlandet.",
    rej_bankrupt_or_dissolving: "Organisasjonen er konkurs eller under avvikling, og kan ikke søke tilskudd.",
    rej_no_eligible_grants: "Laget oppfyller ikke kravene til noen av tilskuddene vi kjenner til. Se hvorfor under.",
    rej_no_matching_grants: "Ingen av tilskuddene laget kan søke på passer dette prosjektet. Se hvorfor under.",
    rej_server_error: "Det oppsto en feil i den lokale serveren.",
    fail_title: "Tjenesten er midlertidig utilgjengelig",
    fail_upstream: "En tjeneste vi er avhengige av svarer ikke akkurat nå. Prøv igjen om litt.",
    fail_check: "Planen besto ikke den automatiske kontrollen, så vi viser den ikke. Prøv igjen, eller kontakt den som drifter tjenesten.",
    halt_title: "Tjenesten er stoppet av sikkerhetsbryteren",
    halt_text: "Kjøringer er stoppet til en person har sett på årsaken og slettet out/HALTED.",
    reason: "Årsak",
    log: "Vis teknisk logg",
    demo_only: "I demoen kan du bare se eksemplene under. For egne søk: kjør tjenesten lokalt med",
  },
  en: {
    brand_sub: "for volunteer clubs",
    hero_title: "Which grants can your club apply for?",
    demo_title: "Demo:",
    demo_text: "These are pre-computed examples. Pick an example below. Your own searches need the service running locally.",
    orgnr_label: "Organisation number",
    amount_label: "Requested amount (NOK, optional)",
    lang_label: "Plan language",
    idea_label: "Describe the project in one sentence",
    idea_placeholder: "E.g. Free outdoor days with campfire and canoe trips for children aged 6–12 in Hamar",
    offline_label: "Offline (test data from fixtures/, no lookup in Brønnøysund)",
    footer: "Grants are taken from the official grant pages. Always confirm the deadline on the grant page before applying.",
    submit: "Find grants",
    examples: "Examples",
    mode_live: "Live",
    mode_offline: "Live (offline data)",
    mode_demo: "Demo",
    orgnr_empty: "Enter the organisation number (9 digits).",
    orgnr_digits: "The organisation number has 9 digits.",
    orgnr_mod11: "The check digit does not match. Check that the number is typed correctly.",
    orgnr_ok: "Valid organisation number",
    idea_empty: "Describe the project.",
    idea_long: "Max 300 characters.",
    amount_bad: "Enter a whole amount in NOK, for example 60000.",
    progress_title: "Checking your club and the grants",
    progress_note: "This usually takes 2–5 minutes. You can leave the page open.",
    stage_entity: "Checking the organisation in the Brønnøysund registers",
    stage_grants: "Reading the grant schemes",
    stage_filter: "Checking who may apply",
    stage_matcher: "Judging whether the project fits",
    stage_guide: "Writing the guide",
    stage_render: "Making the checklist",
    attempt: "attempt {a}/{n}",
    busy: "Another run is in progress. Wait until it finishes and try again.",
    no_server: "Could not reach the local server.",
    org_title: "The organisation",
    org_name: "Name",
    org_nr: "Organisation number",
    org_form: "Organisation form",
    org_kommune: "Municipality number",
    org_frivreg: "Voluntary Organisations Register",
    yes_registered: "Registered",
    not_registered: "Not registered",
    plan_title: "Grants you can apply for",
    plan_one: "1 grant fits the project",
    plan_many: "{n} grants fit the project",
    sources: "Checked automatically against the official sources fetched on {date}. Always confirm the deadline on the grant page before applying.",
    download: "Download the checklist (.md)",
    cost: "Model cost of this run: {usd} USD",
    generated_demo: "This example was run on {date} with test data.",
    deadline: "Deadline",
    max_amount: "Max amount",
    amount_unknown: "Not stated on the grant page",
    why: "Why your club qualifies",
    attachments: "Attachments",
    steps: "How to apply",
    excluded_title: "Grants you do not qualify for ({n})",
    excluded_none: "No grants were left out.",
    org_form_not_allowed: "Your organisation form ({form}) may not apply.",
    outside_region: "The grant does not cover your municipality.",
    not_in_frivillighetsregisteret: "Requires registration in the Voluntary Organisations Register.",
    no_open_deadline: "No open deadline right now.",
    matcher_prefix: "Does not fit the project: ",
    rej_title: "We could not make a plan",
    rej_invalid_orgnr: "The organisation number is not valid. Check that all 9 digits are typed correctly.",
    rej_invalid_request: "Something in the form is missing or wrong. Check the fields and try again.",
    rej_not_found: "We could not find the organisation number in the Central Coordinating Register.",
    rej_outside_innlandet: "The club is not registered in a municipality in Innlandet. The service only covers clubs in Innlandet.",
    rej_bankrupt_or_dissolving: "The organisation is bankrupt or being dissolved, and cannot apply for grants.",
    rej_no_eligible_grants: "The club does not meet the requirements of any grant we know of. See why below.",
    rej_no_matching_grants: "None of the grants the club may apply for fit this project. See why below.",
    rej_server_error: "An error occurred in the local server.",
    fail_title: "The service is temporarily unavailable",
    fail_upstream: "A service we depend on is not answering right now. Try again in a while.",
    fail_check: "The plan did not pass the automatic check, so we do not show it. Try again, or contact whoever runs the service.",
    halt_title: "The service is stopped by the kill switch",
    halt_text: "Runs are stopped until a person has looked at the cause and deleted out/HALTED.",
    reason: "Reason",
    log: "Show technical log",
    demo_only: "In the demo you can only view the examples below. For your own searches, run the service locally with",
  },
};

const state = { mode: "demo", lang: "no", cases: [], bundles: {}, polling: null };
const $ = (id) => document.getElementById(id);

function t(key, vars = {}) {
  const s = (T[state.lang] && T[state.lang][key]) || T.no[key] || key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? String(vars[k]) : ""));
}

// Element helper: h("p", {class: "x"}, "text", child, ...). Strings become text nodes.
function h(tag, attrs, ...children) {
  const el = document.createElement(tag);
  for (const [k, v] of Object.entries(attrs || {})) {
    if (v === null || v === undefined || v === false) continue;
    if (k === "class") el.className = v;
    else if (k.startsWith("on")) el.addEventListener(k.slice(2), v);
    else el.setAttribute(k, v === true ? "" : v);
  }
  for (const c of children.flat()) {
    if (c === null || c === undefined || c === false) continue;
    el.append(c instanceof Node ? c : document.createTextNode(String(c)));
  }
  return el;
}

// Only https links from the plan ever become anchors.
function safeUrl(url) {
  try {
    const u = new URL(url);
    return u.protocol === "https:" ? u.href : null;
  } catch {
    return null;
  }
}

function fmtDate(iso) {
  const m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
  return m ? `${m[3]}.${m[2]}.${m[1]}` : iso || "";
}

function fmtNok(n) {
  return new Intl.NumberFormat("nb-NO").format(n) + " kr";
}

function fmtOrgnr(s) {
  const d = String(s || "").replace(/\D/g, "");
  return d.length === 9 ? `${d.slice(0, 3)} ${d.slice(3, 6)} ${d.slice(6)}` : String(s || "");
}

// Same rule as harness/entity.py mod11_ok: weights 3,2,7,6,5,4,3,2.
function mod11Ok(orgnr) {
  if (!/^\d{9}$/.test(orgnr)) return false;
  const w = [3, 2, 7, 6, 5, 4, 3, 2];
  const rest = w.reduce((s, wi, i) => s + wi * Number(orgnr[i]), 0) % 11;
  let check = 11 - rest;
  if (check === 11) check = 0;
  return check !== 10 && check === Number(orgnr[8]);
}

/* ---------- i18n ---------- */

function applyLang(lang) {
  state.lang = lang === "en" ? "en" : "no";
  document.documentElement.lang = state.lang;
  $(state.lang === "en" ? "lang-en" : "lang-no").checked = true;
  document.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  document.querySelectorAll("[data-i18n-placeholder]").forEach((el) => {
    el.placeholder = t(el.dataset.i18nPlaceholder);
  });
  $("submit").setAttribute("aria-label", t("submit"));
  $("chips").setAttribute("aria-label", t("examples"));
  renderModeBadge();
  renderChips();
  if (state.lastBundle) renderBundle(state.lastBundle);
}

function renderModeBadge() {
  const badge = $("mode-badge");
  badge.hidden = false;
  if (state.mode === "demo") badge.textContent = t("mode_demo");
  else badge.textContent = $("offline").checked ? t("mode_offline") : t("mode_live");
}

/* ---------- form ---------- */

function readForm() {
  const orgnr = $("orgnr").value.replace(/[\s.]/g, "");
  const idea = $("idea").value.trim();
  const amountRaw = $("amount").value.replace(/[\s.]/g, "").replace(/kr$/i, "");
  return { orgnr, idea, amountRaw, lang: state.lang };
}

function setMsg(id, text, ok = false) {
  const el = $(id);
  el.textContent = text;
  el.classList.toggle("ok", ok && !!text);
}

function validate(showEmpty) {
  const f = readForm();
  let valid = true;

  const orgnrInput = $("orgnr");
  let orgMsg = "";
  if (!f.orgnr) { valid = false; if (showEmpty) orgMsg = t("orgnr_empty"); }
  else if (!/^\d{9}$/.test(f.orgnr)) { valid = false; if (showEmpty || f.orgnr.length >= 9) orgMsg = t("orgnr_digits"); }
  else if (!mod11Ok(f.orgnr)) { valid = false; orgMsg = t("orgnr_mod11"); }
  const orgOk = valid && !!f.orgnr;
  setMsg("orgnr-msg", orgOk ? t("orgnr_ok") : orgMsg, orgOk);
  orgnrInput.setAttribute("aria-invalid", orgMsg ? "true" : "false");

  let ideaMsg = "";
  const len = $("idea").value.length;
  $("idea-count").textContent = `${len} / ${MAX_IDEA}`;
  $("idea-count").classList.toggle("over", len > MAX_IDEA);
  if (!f.idea) { valid = false; if (showEmpty) ideaMsg = t("idea_empty"); }
  else if (len > MAX_IDEA) { valid = false; ideaMsg = t("idea_long"); }
  setMsg("idea-msg", ideaMsg);
  $("idea").closest(".searchbox").classList.toggle("invalid", !!ideaMsg);

  let amountMsg = "";
  if (f.amountRaw && !/^\d+$/.test(f.amountRaw)) { valid = false; amountMsg = t("amount_bad"); }
  setMsg("amount-msg", amountMsg);
  $("amount").setAttribute("aria-invalid", amountMsg ? "true" : "false");

  return valid ? f : null;
}

function toRequest(f) {
  const req = { orgnr: f.orgnr, project_idea: f.idea, output_language: f.lang };
  if (f.amountRaw) req.requested_amount_nok = Number(f.amountRaw);
  return req;
}

// The project box grows with its text, so a long idea is never hidden behind a scrollbar.
function growIdea() {
  const el = $("idea");
  el.style.height = "auto";
  el.style.height = `${el.scrollHeight}px`;
}

function fillForm(req) {
  $("orgnr").value = fmtOrgnr(req.orgnr);
  $("idea").value = req.project_idea || "";
  $("amount").value = req.requested_amount_nok != null ? String(req.requested_amount_nok) : "";
  applyLang(req.output_language);
  validate(false);
  growIdea();
}

async function onSubmit(ev) {
  ev.preventDefault();
  const f = validate(true);
  if (!f) {
    const firstBad = document.querySelector('[aria-invalid="true"]') || ($("idea-msg").textContent ? $("idea") : null);
    if (firstBad) firstBad.focus();
    return;
  }
  const req = toRequest(f);
  if (state.mode === "demo") return demoSubmit(req);
  return liveSubmit(req);
}

/* ---------- demo mode ---------- */

async function loadBundle(id) {
  if (!state.bundles[id]) {
    const r = await fetch(`demo/${encodeURIComponent(id)}.json`);
    if (!r.ok) throw new Error(`demo/${id}.json: HTTP ${r.status}`);
    state.bundles[id] = await r.json();
  }
  return state.bundles[id];
}

async function demoSubmit(req) {
  for (const c of state.cases) {
    const b = await loadBundle(c.id);
    if (b.request.orgnr === req.orgnr && b.request.project_idea.trim() === req.project_idea) {
      return showCase(c.id, false);
    }
  }
  state.lastBundle = null;
  setChipPressed(null);
  results(h("div", { class: "notice warn" },
    h("p", {}, t("demo_only"), " ", h("code", {}, "python web/server.py"), ".")));
}

async function showCase(id, fill = true) {
  const b = await loadBundle(id);
  if (fill) fillForm(b.request);
  setChipPressed(id);
  renderBundle(b, true);
  $("results").scrollIntoView({ behavior: "smooth", block: "start" });
}

function setChipPressed(id) {
  document.querySelectorAll(".chip").forEach((c) => c.setAttribute("aria-pressed", c.dataset.id === id ? "true" : "false"));
}

function renderChips() {
  const box = $("chips");
  box.replaceChildren(...state.cases.map((c) => h("button", {
    type: "button", class: "chip", "data-id": c.id, "aria-pressed": "false",
    onclick: () => (state.mode === "demo" ? showCase(c.id) : loadBundle(c.id).then((b) => fillForm(b.request))),
  }, c.label[state.lang] || c.label.no)));
  if (state.lastBundle && state.lastBundle.case) setChipPressed(state.lastBundle.case);
}

/* ---------- live mode ---------- */

async function liveSubmit(req) {
  const body = { ...req, offline: $("offline").checked };
  let r;
  try {
    r = await fetch("api/run", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
  } catch {
    return results(h("div", { class: "notice error" }, h("p", {}, t("no_server"))));
  }
  if (r.status === 409) return results(h("div", { class: "notice warn" }, h("p", {}, t("busy"))));
  if (!r.ok) {
    const err = await r.json().catch(() => ({}));
    return results(h("div", { class: "notice error" }, h("p", {}, err.error || `HTTP ${r.status}`)));
  }
  state.lastBundle = null;
  setChipPressed(null);
  setBusy(true);
  renderProgress([]);
  poll();
}

function setBusy(busy) {
  $("submit").disabled = busy;
  $("submit").setAttribute("aria-busy", busy ? "true" : "false");
}

async function poll() {
  clearTimeout(state.polling);
  let s;
  try {
    s = await (await fetch("api/status", { cache: "no-store" })).json();
  } catch {
    state.polling = setTimeout(poll, POLL_MS * 2);
    return;
  }
  if (s.running || !s.done) {
    renderProgress(s.stages || []);
    state.polling = setTimeout(poll, POLL_MS);
    return;
  }
  const b = await (await fetch("api/result", { cache: "no-store" })).json();
  b.log = s.log;
  setBusy(false);
  renderBundle(b, true);
}

function renderProgress(done) {
  const byName = Object.fromEntries(done.map((s) => [s.name, s]));
  const items = STAGES.map((name, i) => {
    const s = byName[name];
    const finished = s && s.status === "pass";
    const prevDone = i === 0 || (byName[STAGES[i - 1]] && byName[STAGES[i - 1]].status === "pass");
    const active = !finished && prevDone;
    let extra = null;
    if (active && s && s.status === "fail" && s.attempt) extra = t("attempt", { a: s.attempt + 1, n: s.attempts });
    const icon = finished ? "✓" : active ? h("span", { class: "spinner", "aria-hidden": "true" }) : "·";
    return h("li", { class: finished ? "done" : active ? "active" : "" },
      h("span", { class: "icon", "aria-hidden": "true" }, icon), t(`stage_${name}`),
      extra && h("span", { class: "extra" }, extra));
  });
  results(
    h("h2", {}, t("progress_title")),
    h("p", { class: "meta" }, t("progress_note")),
    h("ol", { class: "steps" }, items),
  );
}

/* ---------- result rendering ---------- */

function results(...nodes) {
  $("results-inner").replaceChildren(...nodes);
}

// adoptLang: a newly shown plan switches the page to the plan's language. A later click on the
// language toggle only re-labels the page.
function renderBundle(b, adoptLang = false) {
  state.lastBundle = b;
  const planLang = b.request && b.request.output_language;
  if (adoptLang && planLang && planLang !== state.lang) {
    return applyLang(planLang); // re-renders with the plan's language
  }
  const nodes = [];
  if (b.exit === 0 && b.plan) {
    nodes.push(...planView(b));
  } else if (b.exit === 3) {
    const reason = (b.rejection && b.rejection.reason) || "";
    nodes.push(notice("error", t("rej_title"), T[state.lang][`rej_${reason}`] || reason, b.rejection && b.rejection.detail));
    if (b.entity) nodes.push(orgView(b.entity));
  } else if (b.exit === 4) {
    nodes.push(notice("warn", t("halt_title"), t("halt_text"), b.halted));
  } else {
    const reason = b.rejection && b.rejection.reason;
    const text = reason === "upstream_unavailable" ? t("fail_upstream")
      : reason === "server_error" ? t("rej_server_error") : t("fail_check");
    nodes.push(notice("error", t("fail_title"), text, b.rejection && b.rejection.detail));
  }
  if (b.exit !== 4 && (b.excluded || []).length) nodes.push(excludedView(b));
  if (b.mode === "demo" && b.generated) nodes.push(h("p", { class: "meta" }, t("generated_demo", { date: fmtDate(b.generated) })));
  if (b.log && b.log.length && b.exit !== 0) {
    nodes.push(h("details", { class: "log" }, h("summary", {}, t("log")), h("pre", {}, b.log.join("\n"))));
  }
  results(...nodes);
}

function notice(kind, title, text, detail) {
  return h("div", { class: `notice ${kind}`, role: kind === "error" ? "alert" : "status" },
    h("h2", {}, title), h("p", {}, text),
    detail && h("p", { class: "detail" }, `${t("reason")}: ${detail}`));
}

function orgView(e) {
  const row = (label, value) => h("div", {}, h("dt", {}, label), h("dd", {}, value));
  return h("section", { "aria-labelledby": "org-h" },
    h("h2", { id: "org-h" }, t("org_title")),
    h("dl", { class: "org" },
      row(t("org_name"), e.navn || "–"),
      row(t("org_nr"), fmtOrgnr(e.organisasjonsnummer)),
      row(t("org_form"), e.organisasjonsform || "–"),
      row(t("org_kommune"), e.kommunenummer || "–"),
      row(t("org_frivreg"), e.registrertIFrivillighetsregisteret ? t("yes_registered") : t("not_registered")),
    ));
}

function planView(b) {
  const plan = b.plan;
  const n = plan.grants.length;
  const nodes = [];
  if (b.entity) nodes.push(orgView(b.entity));
  nodes.push(h("h2", {}, t("plan_title")));
  nodes.push(h("div", { class: "notice" },
    h("p", {}, h("strong", {}, n === 1 ? t("plan_one") : t("plan_many", { n }))),
    b.fetched_at && h("p", {}, t("sources", { date: fmtDate(b.fetched_at) }))));

  const tools = [];
  if (b.markdown) {
    tools.push(h("button", { type: "button", class: "btn", onclick: () => download(b) }, t("download")));
  }
  if (typeof b.cost_usd === "number" && b.mode !== "demo") {
    tools.push(h("span", { class: "meta" }, t("cost", { usd: b.cost_usd.toFixed(2) })));
  }
  if (tools.length) nodes.push(h("div", { class: "toolbar" }, tools));

  plan.grants.forEach((g) => nodes.push(grantView(g)));
  return nodes;
}

function grantView(g) {
  const href = safeUrl(g.url);
  const title = href ? h("a", { href, rel: "noopener noreferrer", target: "_blank" }, g.title) : g.title;
  const amount = typeof g.max_amount_nok === "number" ? fmtNok(g.max_amount_nok) : t("amount_unknown");
  return h("article", { class: "grant" },
    h("h3", { class: "grant-title" }, h("span", { class: "arrow", "aria-hidden": "true" }, "→"), title),
    h("dl", { class: "facts" },
      h("div", {}, h("dt", {}, t("deadline")), h("dd", {}, fmtDate(g.application_deadline))),
      h("div", {}, h("dt", {}, t("max_amount")), h("dd", {}, amount))),
    g.amount_note && h("p", { class: "amount-note" }, g.amount_note),
    h("h3", {}, t("why")),
    h("p", {}, g.why_qualifies),
    (g.attachments || []).length > 0 && [
      h("h3", {}, t("attachments")),
      h("ul", { class: "checklist" }, g.attachments.map((a) => h("li", {}, h("input", { type: "checkbox", "aria-label": a }), h("span", {}, a)))),
    ],
    (g.steps || []).length > 0 && [
      h("h3", {}, t("steps")),
      h("ol", { class: "steps-list" }, g.steps.map((s) => h("li", {}, s))),
    ]);
}

function excludedReason(x, entity) {
  if (x.stage === "matcher") return t("matcher_prefix") + x.reason;
  return t(x.reason, { form: (entity && entity.organisasjonsform) || "?" });
}

function excludedView(b) {
  const items = b.excluded.map((x) => h("li", {},
    h("span", { class: "arrow", "aria-hidden": "true" }, "→"),
    h("span", {}, h("span", { class: "name" }, x.title), h("span", { class: "why" }, excludedReason(x, b.entity)))));
  const open = b.exit === 3 && b.rejection && /^no_(eligible|matching)_grants$/.test(b.rejection.reason);
  return h("details", { class: "excluded", open },
    h("summary", {}, h("span", { class: "arrow", "aria-hidden": "true" }, "→"), t("excluded_title", { n: items.length })),
    h("ul", { class: "arrow-list" }, items));
}

function download(b) {
  const blob = new Blob([b.markdown], { type: "text/markdown;charset=utf-8" });
  const a = h("a", { href: URL.createObjectURL(blob), download: `grant_action_plan_${b.plan.orgnr}.md` });
  document.body.append(a);
  a.click();
  a.remove();
  setTimeout(() => URL.revokeObjectURL(a.href), 1000);
}

/* ---------- start ---------- */

async function detectMode() {
  try {
    const ctrl = new AbortController();
    const timer = setTimeout(() => ctrl.abort(), 1500);
    const r = await fetch("api/health", { signal: ctrl.signal, cache: "no-store" });
    clearTimeout(timer);
    if (r.ok && (await r.json()).ok) return "live";
  } catch { /* no server: static hosting */ }
  return "demo";
}

async function init() {
  $("search").addEventListener("submit", onSubmit);
  ["orgnr", "idea", "amount"].forEach((id) => $(id).addEventListener("input", () => validate(false)));
  $("idea").addEventListener("input", growIdea);
  $("orgnr").addEventListener("blur", () => { if (mod11Ok($("orgnr").value.replace(/\s/g, ""))) $("orgnr").value = fmtOrgnr($("orgnr").value); });
  document.querySelectorAll('input[name="lang"]').forEach((r) => r.addEventListener("change", () => applyLang(r.value)));
  $("offline").addEventListener("change", renderModeBadge);

  state.mode = await detectMode();
  $("demo-banner").hidden = state.mode !== "demo";
  $("offline-row").hidden = state.mode !== "live";
  try {
    const r = await fetch("demo/index.json", { cache: "no-store" });
    if (r.ok) state.cases = await r.json();
  } catch { state.cases = []; }
  applyLang("no");
  validate(false);

  // ?case=<id> opens a demo example directly (shareable links in demo mode).
  const caseId = new URLSearchParams(location.search).get("case");
  if (caseId && state.cases.some((c) => c.id === caseId)) {
    await showCase(caseId).catch(() => {});
  }

  if (state.mode === "live") {
    const s = await (await fetch("api/status", { cache: "no-store" })).json().catch(() => null);
    if (s && s.running) { setBusy(true); poll(); } // a run started before the page was reloaded
  }
}

init();
