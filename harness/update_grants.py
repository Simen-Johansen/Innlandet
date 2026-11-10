"""Weekly grant update (task 015): keep context/grants/ current using the page's "Sist endret".

Usage: python harness/update_grants.py [--offline --pages-dir D] [--grants-dir G] [--pending-dir Q]
                                       [--sources S] [--report R] [--today YYYY-MM-DD]

Per grant file, compare the page's "Sist endret" with the stored source_modified (never with "the last
7 days", so a skipped run cannot miss a change) and pick one action:
  unchanged       same date                       -> checked_at
  touched         newer date, same text           -> source_modified, checked_at
  updated_text    newer, text changed, but no number changed and "Hvem kan søke" and
                  "Frister og rapportering" identical -> body, fetched_at, source_modified, checked_at
  needs_review    anything that may change a fact -> file untouched, draft in the pending dir
  failed          request failed, no "Sist endret", a core heading missing -> file untouched, reason given
  skipped_manual  domain policy manual            -> file untouched, no request
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
    return norm(html.unescape(re.sub(r"<[^>]+>", " ", raw)))


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
            text = norm("".join(self.heading))
            self.heading = None
            self.flush()
            if text.rstrip("?").strip().lower() == STOP_HEADING:
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
        text = norm("".join(parts))
        if not text or text.startswith("Sist endret"):
            return
        if self.ingress:
            self.lead.append(text)
        elif self.sections:
            self.sections[-1][1].append((kind, text))


def sanitize(raw):
    return DROP_BLOCKS.sub(" ", AUTHOR_META.sub("", raw))


def extract(raw):
    """(sections {our heading: [(kind, text)]}, problem) where problem is (template?, reason) or None."""
    p = BodyParser()
    p.feed(raw)
    p.close()
    found, unknown = {}, []
    for title, blocks in p.sections:
        target = HEADING_MAP.get(title.rstrip("?").strip().lower())
        if target is None:
            unknown.append(title)
            continue
        found.setdefault(target, []).extend(blocks)
    missing_core = [h for h in CORE_HEADINGS if h not in found]
    if missing_core:
        return found, (True, f"{TEMPLATE}: heading missing: {', '.join(missing_core)}")
    # Ingress lines lead their section: a deadline line goes to the deadlines, the rest describe what
    # can be applied for. A page line already contained in an earlier line of the section is dropped.
    lead = [s for line in p.lead for s in DEADLINE_SPLIT.split(line)]
    for line in reversed(lead):
        target = "Frister og rapportering" if DEADLINE_LINE.match(line) else "Hva kan det søkes om"
        found.setdefault(target, []).insert(0, ("p", line))
    for h, blocks in found.items():
        kept = []
        for kind, text in blocks:
            if not any(text in t for _, t in kept):
                kept.append((kind, text))
        found[h] = kept
    problems = []
    if unknown:
        problems.append(f"unknown heading on page: {', '.join(unknown)}")
    missing = [h for h in HEADINGS if h not in found]
    if missing:
        problems.append(f"no page section for: {', '.join(missing)}")
    return found, (False, "; ".join(problems)) if problems else None


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
            out.append(f"- {text}" if kind == "li" else text)
            prev = kind
        out.append("")
    return "\n" + "\n".join(out[:-1]) + "\n"


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

    found, problem = extract(raw)
    if problem and problem[0]:
        return done("failed", problem[1])
    new_body, hits = redact(render(found))
    if now < stored:
        return done("needs_review", "page date is older than the stored source_modified", new_body=new_body)
    if problem:
        return done("needs_review", problem[1], new_body=new_body)
    if hits:
        return done("needs_review", "e-mail or phone pattern in the page text (redacted in the draft)",
                    new_body=new_body)

    old, new = sections_of(body), sections_of(new_body)
    if all(old.get(h) == new.get(h) for h in HEADINGS):
        return done("touched")
    changed_facts = [h for h in FACT_SECTIONS if old.get(h) != new.get(h)]
    if changed_facts:
        return done("needs_review", f"section changed: {', '.join(changed_facts)}", new_body=new_body)
    if numbers(body) != numbers(new_body):
        return done("needs_review", "a number, date or amount changed", new_body=new_body)
    text = page_text(raw)
    for line in new_body.splitlines():
        line = norm(line.lstrip("-* "))
        if line and not line.startswith(("#", "(")) and line not in text:
            return done("needs_review", f"extracted line not found verbatim on the page: {line[:60]!r}",
                        new_body=new_body)
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
        return
    else:
        return
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(block + body)


def main():
    ap = argparse.ArgumentParser(description="Weekly update of context/grants/ from the live pages.")
    ap.add_argument("--offline", action="store_true", help="read pages from --pages-dir instead of the web")
    ap.add_argument("--pages-dir", type=Path, help="offline pages, <id>.html")
    ap.add_argument("--grants-dir", type=Path, default=ROOT / "context" / "grants")
    ap.add_argument("--pending-dir", type=Path, default=ROOT / "context" / "grants_pending")
    ap.add_argument("--sources", type=Path, default=ROOT / "context" / "sources.json")
    ap.add_argument("--report", type=Path, default=ROOT / "out" / "update_report.json")
    ap.add_argument("--today", default=date.today().isoformat())
    args = ap.parse_args()
    if args.offline and args.pages_dir is None:
        ap.error("--offline needs --pages-dir")
    pages_dir = args.pages_dir if args.offline else None

    with open(args.sources, encoding="utf-8") as f:
        cfg = json.load(f)
    policy = {s["domain"]: s["policy"] for s in cfg["sources"]}

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
    report["grants"] = [{k: v for k, v in e.items() if k != "new_body"} for *_, e in plan]
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
