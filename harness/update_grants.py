"""Weekly grant update (task 015): keep context/grants/ current using the page's "Sist endret".

Usage: python harness/update_grants.py [--offline --pages-dir D] [--grants-dir G] [--pending-dir Q]
                                       [--sources S] [--report R] [--today YYYY-MM-DD]
       python harness/update_grants.py --audit [--offline --pages-dir D]   (read-only fact audit)

Per grant file, compare the page's "Sist endret" with the stored source_modified (never with "the last
7 days", so a skipped run cannot miss a change) and pick one action:
  unchanged       same date                       -> checked_at
  touched         newer date, same text           -> source_modified, checked_at
  updated_text    newer, text changed, but no number changed and "Hvem kan søke" and
                  "Frister og rapportering" identical -> body, fetched_at, source_modified, checked_at
  needs_review    anything that may change a fact -> file untouched, draft in the pending dir
  failed          request failed, no "Sist endret", a core heading missing -> file untouched, reason given
  skipped_manual  domain policy manual            -> file untouched, no request
Page headings outside the five sections are merged under "### <heading>" (EXTRA_MAP), deliberately left out
(IGNORED) or unknown (needs_review); a needs_review draft gets <id>.checklist.md beside it.
--audit lists every heading and every page fact (amount, deadlines) against the frontmatter in
out/grant_audit.md, so a human can correct facts; it writes nothing else.
Facts (url, title, deadlines, ...) are never written. Kill switch: 2 or more template failures in one
run -> nothing is written, the report says "halted", exit 2.
Offline: the page for <id> is <pages-dir>/<id>.html; a missing file is a failed request.
Standard library only.
"""

import argparse
import html
import json
import re
import sys
import time
import urllib.request
from datetime import date
from html.parser import HTMLParser
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
TIMEOUT_S = 10
PAUSE_S = 1  # between live requests, one at a time
HEADINGS = ("Formål", "Hvem kan søke", "Hva kan det søkes om", "Vedlegg", "Frister og rapportering")
FACT_SECTIONS = ("Hvem kan søke", "Frister og rapportering")
# Every county page has these; one missing means the template changed (failed, kill switch).
# The other headings vary from page to page; missing or unknown ones go to a human (needs_review).
CORE_HEADINGS = ("Formål", "Hvem kan søke", "Frister og rapportering")
# Page heading (lowercase, without "?") -> our heading. Real county pages use their own names.
HEADING_MAP = {
    "formål": "Formål",
    "formålet med ordningen": "Formål",  # 37168 (task 017)
    "hvem kan søke": "Hvem kan søke",
    "hva kan det søkes om": "Hva kan det søkes om",
    "hva kan du søke om": "Hva kan det søkes om",
    "hva kan støttes": "Hva kan det søkes om",
    "vedlegg": "Vedlegg",
    "søknadsskjema": "Vedlegg",
    "søk om midler": "Vedlegg",
    "frister og rapportering": "Frister og rapportering",
    "søknadsfrist": "Frister og rapportering",
    "rapportering": "Frister og rapportering",
}
# Extra page headings that hold facts (amount, exclusions, criteria). Their text is merged into one of the
# five sections under a "### <page heading>" line, so nothing that decides eligibility is dropped silently.
# (Before 24.11 these were dropped: "Tildelingsprosess" held the 350 000 kr maximum, "Avgrensning" the
# exclusions.)
EXTRA_MAP = {
    "kriterier": "Hva kan det søkes om",
    "støttenivå": "Hva kan det søkes om",
    "tildelingsprosess": "Hva kan det søkes om",
    "avgrensning": "Hva kan det søkes om",
    "søknadsvurdering": "Hva kan det søkes om",
    "krav til søknaden": "Hva kan det søkes om",
    "søknad": "Vedlegg",
    # task 017: criteria, exclusions and amounts on 37168 and 62589
    "tildelingskriterier": "Hva kan det søkes om",
    "avgrensing": "Hva kan det søkes om",
    "vi gir ikke tilskudd til": "Hva kan det søkes om",
    "vurdering av søknaden": "Hva kan det søkes om",
    "søknadskategorier": "Hva kan det søkes om",
    "tidligere ordninger fases inn i regionalt kulturfond": "Hva kan det søkes om",
}
# Known headings deliberately left out (background or administrative text); listed in the audit, never silent.
IGNORED = {"forankring", "tidligere tildelinger", "hold kontaktinformasjonen oppdatert",
           "hva er helsefremmende tiltak",
           # task 017: administrative text on 37168 and 62589 (processing time, how to apply, logo rules)
           "behandlingstid", "behandlingstid og tildelingsbrev", "slik søker du", "profilering, markedsføring"}
INVISIBLE = re.compile("[​‌‍⁠﻿]")
STOP_HEADING = "kontakt"  # the caseworker block; everything after it is dropped
TEMPLATE = "template"  # reason prefix that counts towards the kill switch
KILL_AFTER = 2

DEADLINE_LINE = re.compile(r"(søknads)?frist", re.I)
DEADLINE_SPLIT = re.compile(r"(?<=\.)\s+(?=(?:søknads)?frist)", re.I)  # "... samarbeid. Søknadsfrist: ..."
SIST_ENDRET = re.compile(r"Sist endret\s+(\d{2})\.(\d{2})\.(\d{4})\s+(\d{2})[.:](\d{2})")
AUTHOR_META = re.compile(r'<meta\s+name="author"[^>]*>', re.I)
DROP_BLOCKS = re.compile(r"<(script|style|aside)\b.*?</\1\s*>", re.S | re.I)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.]+")
PHONE = re.compile(r"\+47[\s\d]{8,11}|\b\d{2}\s\d{2}\s\d{2}\s\d{2}\b|\b\d{3}\s\d{2}\s\d{3}\b|\b\d{8}\b")
NUMBER = re.compile(r"\d[\d\s.,]*\d|\d")
REDACTED = "[fjernet]"

try:
    sys.stdout.reconfigure(encoding="utf-8")
except AttributeError:
    pass


def norm(text):
    return " ".join(text.split())


def heading_key(title):
    """Lowercase page heading without invisible characters, non-breaking spaces or a trailing '?'."""
    return norm(INVISIBLE.sub("", title)).rstrip("?").strip().lower()


def domain(url):
    host = re.sub(r"^https?://", "", url).split("/", 1)[0].split(":", 1)[0].lower()
    return host[4:] if host.startswith("www.") else host


def split_file(text):
    """(frontmatter block incl. both --- lines, body) for a grant file read with newline=""."""
    lines = text.splitlines(keepends=True)
    if not lines or lines[0].strip() != "---":
        raise ValueError("no frontmatter")
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "".join(lines[:i + 1]), "".join(lines[i + 1:])
    raise ValueError("frontmatter not closed with ---")


def parse_meta(block):
    meta = {}
    for line in block.splitlines()[1:-1]:
        line = re.sub(r"\s+#\s.*$", "", line).strip()
        if ":" in line:
            k, v = line.split(":", 1)
            meta[k.strip()] = v.strip()
    return meta


def sections_of(body):
    """{heading: whitespace-normalized text} of a grant body."""
    out, current = {}, None
    for line in body.splitlines():
        if line.startswith("## "):
            current = line[3:].strip()
            out[current] = []
        elif current is not None:
            out[current].append(line)
    return {k: norm(" ".join(v)) for k, v in out.items()}


def numbers(text):
    return sorted(norm(n) for n in NUMBER.findall(text))


def page_text(raw):
    return norm(INVISIBLE.sub("", html.unescape(re.sub(r"<[^>]+>", " ", raw))))


def set_keys(block, values):
    """Set frontmatter keys line by line; a missing key goes before the closing ---."""
    nl = "\r\n" if "\r\n" in block else "\n"
    for key, value in values.items():
        pattern = re.compile(rf"^{re.escape(key)}:[^\r\n]*", re.M)
        if pattern.search(block):
            block = pattern.sub(f"{key}: {value}", block, count=1)
        else:
            head, close = block.rstrip("\r\n").rsplit("---", 1)
            block = f"{head}{key}: {value}{nl}---{close}{block[len(block.rstrip(chr(13) + chr(10))):]}"
    return block


class BodyParser(HTMLParser):
    """Collect h2 sections of paragraphs and list items inside <main>, until the Kontakt heading.
    Skips <header> (title). The ingress (section.ingress) is kept apart in `lead`: on county pages it
    often holds the only "what can you apply for" sentence and the deadline line."""

    SKIP = {"header", "script", "style", "aside", "nav", "footer"}

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.main = 0
        self.skip_tag, self.skip_depth = None, 0
        self.ingress = 0  # section nesting depth while inside the ingress
        self.stopped = False
        self.lead = []  # ingress lines
        self.sections = []  # [(page heading, [(kind, text)])]
        self.heading = None  # text buffer while inside h2
        self.block = None  # (kind, text buffer) while inside p/li

    def handle_starttag(self, tag, attrs):
        if self.skip_tag:
            self.skip_depth += tag == self.skip_tag
            return
        if tag == "main":
            self.main += 1
        if not self.main or self.stopped:
            return
        classes = (dict(attrs).get("class") or "").split()
        if tag == "section" and (self.ingress or "ingress" in classes):
            self.flush()
            self.ingress += 1
        elif tag in self.SKIP:
            self.skip_tag, self.skip_depth = tag, 1
        elif tag == "h2":
            self.heading = []
        elif tag in ("p", "li") and self.heading is None:
            self.flush()
            self.block = (tag, [])
        elif tag == "br" and self.block and self.block[0] == "p":
            self.flush()  # a <br> inside a paragraph starts a new line
            self.block = ("p", [])

    def handle_endtag(self, tag):
        if self.skip_tag:
            self.skip_depth -= tag == self.skip_tag
            if not self.skip_depth:
                self.skip_tag = None
            return
        if tag == "main" and self.main:
            self.flush()
            self.main -= 1
        if not self.main or self.stopped:
            return
        if tag == "section" and self.ingress:
            self.flush()
            self.ingress -= 1
        elif tag == "h2" and self.heading is not None:
            text = norm(INVISIBLE.sub("", "".join(self.heading)))
            self.heading = None
            self.flush()
            if heading_key(text) == STOP_HEADING:
                self.stopped = True
            elif text:
                self.sections.append((text, []))
        elif tag in ("p", "li"):
            self.flush()

    def handle_data(self, data):
        if self.skip_tag or not self.main or self.stopped:
            return
        if self.heading is not None:
            self.heading.append(data)
        elif self.block:
            self.block[1].append(data)

    def flush(self):
        if not self.block:
            return
        kind, parts = self.block
        self.block = None
        text = norm(INVISIBLE.sub("", "".join(parts)))
        if not text or text.startswith("Sist endret"):
            return
        if self.ingress:
            self.lead.append(text)
        elif self.sections:
            self.sections[-1][1].append((kind, text))


def sanitize(raw):
    return DROP_BLOCKS.sub(" ", AUTHOR_META.sub("", raw))


def extract(raw):
    """(sections {our heading: [(kind, text)]}, problem, heads) where problem is (template?, reason) or None
    and heads lists the page headings as {"mapped": [...], "merged": [...], "ignored": [...], "unknown": [...]}.
    A merged heading is kept as an ("h3", page heading) block before its text."""
    p = BodyParser()
    p.feed(raw)
    p.close()
    found = {}
    heads = {"mapped": [], "merged": [], "ignored": [], "unknown": []}
    for title, blocks in p.sections:
        key = heading_key(title)
        if key in HEADING_MAP:
            heads["mapped"].append(f"{title} -> {HEADING_MAP[key]}")
            found.setdefault(HEADING_MAP[key], []).extend(blocks)
        elif key in EXTRA_MAP:
            heads["merged"].append(f"{title} -> {EXTRA_MAP[key]}")
            if blocks:
                found.setdefault(EXTRA_MAP[key], []).extend([("h3", title.rstrip())] + blocks)
        elif key in IGNORED:
            heads["ignored"].append(title)
        else:
            heads["unknown"].append(title)
    unknown = heads["unknown"]
    missing_core = [h for h in CORE_HEADINGS if h not in found]
    if missing_core:
        return found, (True, f"{TEMPLATE}: heading missing: {', '.join(missing_core)}"), heads
    # Ingress lines lead their section: a deadline line goes to the deadlines, the rest describe what
    # can be applied for. A page line already contained in an earlier line of the section is dropped.
    lead = [s for line in p.lead for s in DEADLINE_SPLIT.split(line)]
    for line in reversed(lead):
        target = "Frister og rapportering" if DEADLINE_LINE.match(line) else "Hva kan det søkes om"
        found.setdefault(target, []).insert(0, ("p", line))
    for h, blocks in found.items():
        kept = []
        for kind, text in blocks:
            if kind == "h3" or not any(text in t for k, t in kept if k != "h3"):
                kept.append((kind, text))
        found[h] = kept
    problems = []
    if unknown:
        problems.append(f"unknown heading on page: {', '.join(unknown)}")
    missing = [h for h in HEADINGS if h not in found]
    if missing:
        problems.append(f"no page section for: {', '.join(missing)}")
    return found, ((False, "; ".join(problems)) if problems else None), heads


def render(found):
    """Body in the grant file format: '## Heading', blank line, one line per paragraph or '- ' item."""
    out = []
    for h in HEADINGS:
        out += [f"## {h}", ""]
        blocks = found.get(h) or [("p", "(ikke oppgitt på kildesiden)")]
        prev = None
        for kind, text in blocks:
            if out[-1] != "" and not (kind == prev == "li"):
                out.append("")
            out.append(f"- {text}" if kind == "li" else f"### {text}" if kind == "h3" else text)
            prev = kind
        out.append("")
    return "\n" + "\n".join(out[:-1]) + "\n"


AMOUNT_MAX = re.compile(r"(maksimal søknadssum|maksimum|maks\.?|inntil|øvre grense|høyeste)[^.]{0,60}?"
                        r"(\d{1,3}(?:[\s.]\d{3})+|\d+)\s*(?:kr\b|kroner|,-)", re.I)
AMOUNT_MIN = re.compile(r"(minimum|minste|under|lavere enn)[^.]{0,40}?(\d{1,3}(?:[\s.]\d{3})+|\d+)\s*(?:kr\b|kroner|,-)",
                        re.I)
MONTHS = {m: i + 1 for i, m in enumerate(("januar", "februar", "mars", "april", "mai", "juni", "juli", "august",
                                          "september", "oktober", "november", "desember"))}
DATE_NUM = re.compile(r"\b(\d{1,2})\.(\d{1,2})\.(\d{4}|\d{2})?\b")
DATE_TXT = re.compile(r"\b(\d{1,2})\.\s*(" + "|".join(MONTHS) + r")(?:\s+(\d{4}))?", re.I)
HUMAN_ONLY = ("provider", "applicant_orgforms", "requires_frivillighetsregisteret", "region_prefix",
              "target_group", "verified_by")


def to_int(s):
    return int(re.sub(r"\D", "", s))


def page_dates(text):
    """[(as written, 'YYYY-MM-DD' or '--MM-DD' when the page gives no year)] in page order."""
    out = []
    for m in DATE_TXT.finditer(text):
        d, mon, y = int(m.group(1)), MONTHS[m.group(2).lower()], m.group(3)
        out.append((m.start(), m.group(0), f"{y}-{mon:02d}-{d:02d}" if y else f"--{mon:02d}-{d:02d}"))
    for m in DATE_NUM.finditer(text):
        d, mon, y = int(m.group(1)), int(m.group(2)), m.group(3)
        if 1 <= d <= 31 and 1 <= mon <= 12:
            y = f"20{y}" if y and len(y) == 2 else y
            out.append((m.start(), m.group(0), f"{y}-{mon:02d}-{d:02d}" if y else f"--{mon:02d}-{d:02d}"))
    return [(w, iso) for _, w, iso in sorted(out)]


def fact_audit(meta, found):
    """Compare facts a page states with the frontmatter. Code only proposes; a human writes the facts."""
    text = {h: norm(" ".join(t for _, t in found.get(h, []))) for h in HEADINGS}
    alltext = " ".join(text.values())
    maxes = [(m.group(0).strip(), to_int(m.group(2))) for m in AMOUNT_MAX.finditer(alltext)]
    mins = [(m.group(0).strip(), to_int(m.group(2))) for m in AMOUNT_MIN.finditer(alltext)]
    stored = meta.get("max_amount_nok", "")
    values = sorted({v for _, v in maxes})
    if not values:
        amount = "not on page" + ("" if stored == "unknown" else f" (file says {stored}: check by hand)")
    elif stored.isdigit() and int(stored) in values and len(values) == 1:
        amount = "match"
    else:
        amount = f"MISMATCH: page {', '.join(map(str, values))}, file {stored or '(missing)'}"
    dates = page_dates(text["Frister og rapportering"])
    isos = {iso for _, iso in dates}
    deadlines = []
    for d in [s.strip() for s in meta.get("deadlines", "").split(",") if s.strip()]:
        ok = d in isos or f"--{d[5:]}" in isos
        deadlines.append((d, "on page" if ok else "NOT ON PAGE"))
    return {"amount": amount, "amount_lines": [w for w, _ in maxes], "minimum_lines": [w for w, _ in mins],
            "deadlines": deadlines, "page_dates": [f"{w} ({iso})" for w, iso in dates]}


def checklist_md(gid, meta, heads, facts, sist_endret):
    """One-page reviewer checklist for one grant: every heading accounted for, every fact compared."""
    L = [f"# Fact checklist: {gid}", "", f"Page: {meta.get('url', '')}  ",
         f"Sist endret on the page: {sist_endret or 'not found'}", "",
         "Check each line against the **live page**, not against the draft.", "", "## Page headings"]
    for kind in ("mapped", "merged", "ignored", "unknown"):
        for h in heads.get(kind, []):
            mark = {"unknown": "  <- NOT IN THE FILE: map it or record why it is dropped",
                    "ignored": "  (deliberately left out)"}.get(kind, "")
            L.append(f"- [ ] {kind}: {h}{mark}")
    L += ["", "## Facts the page states (code proposes, a human writes)",
          f"- [ ] max_amount_nok: {meta.get('max_amount_nok', '(missing)')} -> {facts['amount']}"]
    L += [f"  - page: \"{w}\"" for w in facts["amount_lines"]]
    L += [f"  - minimum on page: \"{w}\"" for w in facts["minimum_lines"]]
    for d, status in facts["deadlines"] or [("(none)", "NOT ON PAGE")]:
        L.append(f"- [ ] deadline {d}: {status}; which project period does it cover?")
    if facts["page_dates"]:
        L.append(f"  - dates under Frister og rapportering: {', '.join(facts['page_dates'])}")
    L += ["", "## Human-only facts (no page field; confirm by reading the page)"]
    L += [f"- [ ] {k}: {meta.get(k, '(missing)')}" for k in HUMAN_ONLY]
    return "\n".join(L) + "\n"


PROVENANCE = """## Where each field comes from

| Field | Source | Who writes |
|---|---|---|
| title, url | page h1 / county catalog | human (code proposes) |
| max_amount_nok, deadlines | page text; candidates in this audit | human confirms and writes |
| provider, applicant_orgforms, requires_frivillighetsregisteret, region_prefix, target_group | judgment from the page | human only |
| verified_by | the person who checked | human only |
| body, fetched_at, checked_at, source_modified | the page | code (task 015 rules) |
"""


def redact(body):
    hits = 0
    for pattern in (EMAIL, PHONE):
        body, n = pattern.subn(REDACTED, body)
        hits += n
    return body, hits


def fetch(url, ua, gid, pages_dir):
    """Raw page text, or raises OSError with a reason."""
    if pages_dir is not None:
        path = Path(pages_dir) / f"{gid}.html"
        if not path.exists():
            raise OSError(f"no page at {path.name}")
        with open(path, encoding="utf-8", errors="replace") as f:
            return f.read()
    req = urllib.request.Request(url, headers={"User-Agent": ua})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return r.read().decode("utf-8", errors="replace")


def decide(gid, block, body, policy, ua, pages_dir, state):
    """Phase 1, no writes. Returns a report entry plus 'new_body' for updated_text / needs_review."""
    meta = parse_meta(block)
    before = meta.get("source_modified", "")
    entry = {"id": gid, "action": None, "reason": "", "source_modified_before": before,
             "source_modified_now": None}

    def done(action, reason="", **extra):
        entry.update(action=action, reason=reason, **extra)
        return entry

    pol = policy.get(domain(meta.get("url", "")))
    if pol == "manual":
        return done("skipped_manual", "domain policy is manual")
    if pol != "auto":
        return done("failed", f"domain {domain(meta.get('url', ''))!r} has no policy in sources")

    if pages_dir is None and state["requests"]:
        time.sleep(PAUSE_S)
    state["requests"] += 1
    try:
        raw = sanitize(fetch(meta["url"], ua, gid, pages_dir))
    except Exception as e:  # any network or file error is a failed request, never a crash
        return done("failed", f"request failed: {e}")

    m = SIST_ENDRET.search(page_text(raw))
    if not m:
        return done("failed", f"{TEMPLATE}: no 'Sist endret' on the page")
    dd, mm, yyyy, hh, mi = m.groups()
    now = f"{yyyy}-{mm}-{dd}T{hh}:{mi}"
    entry["source_modified_now"] = now
    stored = before if re.fullmatch(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}", before) else ""
    if now == stored:
        return done("unchanged")

    found, problem, heads = extract(raw)
    if problem and problem[0]:
        return done("failed", problem[1])
    new_body, hits = redact(render(found))
    review = {"new_body": new_body,
              "checklist": redact(checklist_md(gid, meta, heads, fact_audit(meta, found), now))[0]}
    if now < stored:
        return done("needs_review", "page date is older than the stored source_modified", **review)
    if problem:
        return done("needs_review", problem[1], **review)
    if hits:
        return done("needs_review", "e-mail or phone pattern in the page text (redacted in the draft)",
                    **review)

    old, new = sections_of(body), sections_of(new_body)
    if all(old.get(h) == new.get(h) for h in HEADINGS):
        return done("touched")
    changed_facts = [h for h in FACT_SECTIONS if old.get(h) != new.get(h)]
    if changed_facts:
        return done("needs_review", f"section changed: {', '.join(changed_facts)}", **review)
    if numbers(body) != numbers(new_body):
        return done("needs_review", "a number, date or amount changed", **review)
    text = page_text(raw)
    for line in new_body.splitlines():
        line = norm(line.lstrip("-* "))
        if line and not line.startswith(("#", "(")) and line not in text:
            return done("needs_review", f"extracted line not found verbatim on the page: {line[:60]!r}",
                        **review)
    changed = [h for h in HEADINGS if old.get(h) != new.get(h)]
    return done("updated_text", f"text changed in: {', '.join(changed)}", new_body=new_body)


def with_newlines(text, like):
    return text.replace("\n", "\r\n") if "\r\n" in like else text


def apply(entry, path, block, body, today, pending_dir):
    """Phase 2: write what the action allows. Facts are never in the keys set here."""
    action, now = entry["action"], entry["source_modified_now"]
    if action == "unchanged":
        block = set_keys(block, {"checked_at": today})
    elif action == "touched":
        block = set_keys(block, {"source_modified": now, "checked_at": today})
    elif action == "updated_text":
        block = set_keys(block, {"fetched_at": today, "source_modified": now, "checked_at": today})
        body = with_newlines(entry["new_body"], block)
    elif action == "needs_review":
        draft = set_keys(block, {"fetched_at": today, "source_modified": now, "checked_at": today})
        pending_dir.mkdir(parents=True, exist_ok=True)
        with open(pending_dir / path.name, "w", encoding="utf-8", newline="") as f:
            f.write(draft + with_newlines(entry["new_body"], draft))
        with open(pending_dir / f"{path.stem}.checklist.md", "w", encoding="utf-8") as f:
            f.write(entry["checklist"])
        return
    else:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(block + body)


def audit(grants_dir, policy, ua, pages_dir, out_dir):
    """Read-only: per auto-domain grant, every page heading and every page fact against the frontmatter.
    Writes out_dir/grant_audit.md and .json, plus out_dir/grant_audit_bodies/<id>.md (the body the page gives
    now); never touches grant files or drafts."""
    results, parts, bodies = [], [], {}
    state = {"requests": 0}
    for path in sorted(grants_dir.glob("*.md")):
        with open(path, encoding="utf-8", newline="") as f:
            block, _ = split_file(f.read())
        meta = parse_meta(block)
        r = {"id": path.stem, "url": meta.get("url", "")}
        if policy.get(domain(r["url"])) != "auto":
            r["status"] = "manual domain: check every fact by hand"
            results.append(r)
            parts.append(f"# Fact checklist: {path.stem}\n\nManual domain, no request made. Check every fact "
                         f"by hand against {r['url']}.\n")
            continue
        if pages_dir is None and state["requests"]:
            time.sleep(PAUSE_S)
        state["requests"] += 1
        try:
            raw = sanitize(fetch(r["url"], ua, path.stem, pages_dir))
        except Exception as e:
            r["status"] = f"request failed: {e}"
            results.append(r)
            parts.append(f"# Fact checklist: {path.stem}\n\nRequest failed: {e}\n")
            continue
        m = SIST_ENDRET.search(page_text(raw))
        sist = f"{m.group(3)}-{m.group(2)}-{m.group(1)}T{m.group(4)}:{m.group(5)}" if m else None
        found, problem, heads = extract(raw)
        facts = fact_audit(meta, found)
        r.update(status=problem[1] if problem else "ok", sist_endret=sist, headings=heads, facts=facts)
        results.append(r)
        parts.append(redact(checklist_md(path.stem, meta, heads, facts, sist))[0])
        bodies[path.stem] = redact(render(found))[0]
    out_dir.mkdir(parents=True, exist_ok=True)
    body_dir = out_dir / "grant_audit_bodies"
    body_dir.mkdir(exist_ok=True)
    for gid, text in bodies.items():  # the page body as the updater would write it now, for a human to compare
        with open(body_dir / f"{gid}.md", "w", encoding="utf-8") as f:
            f.write(text)
    with open(out_dir / "grant_audit.json", "w", encoding="utf-8") as f:
        f.write(json.dumps({"requests": state["requests"], "grants": results}, ensure_ascii=False, indent=2) + "\n")
    with open(out_dir / "grant_audit.md", "w", encoding="utf-8") as f:
        f.write("\n\n".join(parts) + "\n" + PROVENANCE)
    for r in results:
        facts = r.get("facts", {})
        flags = [facts.get("amount", "")] + [f"{d} {s}" for d, s in facts.get("deadlines", []) if s != "on page"]
        unk = r.get("headings", {}).get("unknown", [])
        if unk:
            flags.append(f"unknown headings: {', '.join(unk)}")
        print(f"{r['id']}: {r['status']} | " + " | ".join(x for x in flags if x))
    print(f"{state['requests']} requests | {out_dir / 'grant_audit.md'}")


def main():
    ap = argparse.ArgumentParser(description="Weekly update of context/grants/ from the live pages.")
    ap.add_argument("--offline", action="store_true", help="read pages from --pages-dir instead of the web")
    ap.add_argument("--pages-dir", type=Path, help="offline pages, <id>.html")
    ap.add_argument("--grants-dir", type=Path, default=ROOT / "context" / "grants")
    ap.add_argument("--pending-dir", type=Path, default=ROOT / "context" / "grants_pending")
    ap.add_argument("--sources", type=Path, default=ROOT / "context" / "sources.json")
    ap.add_argument("--report", type=Path, default=ROOT / "out" / "update_report.json")
    ap.add_argument("--today", default=date.today().isoformat())
    ap.add_argument("--audit", action="store_true",
                    help="read-only: write out/grant_audit.md (headings and page facts vs frontmatter), change nothing")
    args = ap.parse_args()
    if args.offline and args.pages_dir is None:
        ap.error("--offline needs --pages-dir")
    pages_dir = args.pages_dir if args.offline else None

    with open(args.sources, encoding="utf-8") as f:
        cfg = json.load(f)
    policy = {s["domain"]: s["policy"] for s in cfg["sources"]}
    if args.audit:
        audit(args.grants_dir, policy, cfg["user_agent"], pages_dir, ROOT / "out")
        return

    state = {"requests": 0}
    plan = []
    for path in sorted(args.grants_dir.glob("*.md")):
        with open(path, encoding="utf-8", newline="") as f:
            text = f.read()
        try:
            block, body = split_file(text)
        except ValueError as e:
            plan.append((path, None, None, {"id": path.stem, "action": "failed", "reason": str(e),
                                            "source_modified_before": None, "source_modified_now": None}))
            continue
        entry = decide(path.stem, block, body, policy, cfg["user_agent"], pages_dir, state)
        plan.append((path, block, body, entry))

    template_fails = [e["id"] for *_, e in plan if e["action"] == "failed" and e["reason"].startswith(TEMPLATE)]
    halted = None
    if len(template_fails) >= KILL_AFTER:
        halted = f"{len(template_fails)} grants failed with a template reason ({', '.join(template_fails)}); nothing written"
    else:
        for path, block, body, entry in plan:
            if block is not None:
                apply(entry, path, block, body, args.today, args.pending_dir)

    report = {"today": args.today, "requests": state["requests"]}
    if halted:
        report["halted"] = halted
    report["grants"] = [{k: v for k, v in e.items() if k not in ("new_body", "checklist")} for *_, e in plan]
    args.report.parent.mkdir(parents=True, exist_ok=True)
    with open(args.report, "w", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False, indent=2) + "\n")

    for e in report["grants"]:
        print(f"{e['action']:<15} {e['id']}" + (f"  ({e['reason']})" if e["reason"] else ""))
    print(f"{state['requests']} requests | report {args.report}")
    if halted:
        print(f"HALTED: {halted}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
