# Task 017: Web interface (live locally, demo on GitHub Pages)

## Goal
A volunteer types an org number and a project idea in a browser and gets the grant action plan.
- **Local, live:** `python web/server.py` serves the page and runs `harness/run.py` for real
  (Brreg online + `claude`), with an "Offline (fixtures)" switch that adds `--offline`.
- **GitHub Pages, demo:** the same page, static. It cannot run the pipeline, so it shows
  pre-computed results of the demo cases from `web/demo/`, with a clear "Demo" banner.

## Context
- One page, `web/index.html` + `web/style.css` + `web/app.js`, no build step, no external scripts.
  The page finds out its mode by calling `GET api/health`: answer → live, no answer → demo.
- Style borrows the layout and colours of innlandetfylke.no (teal top bar, white header with a
  green rule, light grey hero with a big question and a search-style form, teal chips, green-arrow
  lists with grey dividers), but no logo, no county name in the header and no links except grant
  URLs: it must not pass as an official county page.
- UI in Norwegian; all labels switch to English when the plan language is English.
- Inputs = `input_request.json`: orgnr (MOD11 checked in the browser too), project idea
  (counter, max 300), requested amount (optional, whole NOK), plan language (no/en). Example chips
  fill in the demo requests.
- Outputs: progress per stage (6 steps, attempt n/3 for stages 4-5); organisation card
  (name, form, kommunenummer, Frivillighetsregisteret; never an address); one card per grant
  (title + link, deadline dd.mm.yyyy, max amount + note, why, attachment checklist, steps);
  sources date banner; download of `grant_action_plan.md`; a plain message per rejection
  reason and for exit 1 / exit 4; a collapsed "Grants you do not qualify for" with the filter
  rule or matcher reason per grant; run cost.

## Design
- `web/bundle.py` turns `out/` after a run into one JSON bundle (request, exit code, stage log,
  entity, plan, rejection, markdown, excluded grants with titles from `context/grants/`, cost).
  It reads output files and grant data only, never stage code.
- `web/server.py` (stdlib `http.server`, 127.0.0.1 only): `GET api/health`, `POST api/run`,
  `GET api/status` (stage lines so far), `GET api/result`. One run at a time, because
  `run.py` wipes `out/`: a second `POST` gets HTTP 409.
- `web/snapshot.py` runs the demo requests and writes `web/demo/<case>.json` plus
  `web/demo/index.json`. Cases that reach stages 4-5 cost model money, so this is run by a
  person, and the bundles are committed.
- `.github/workflows/pages.yml` deploys `web/` (static files only) on push to `main`.
  Needs repo setting: Settings > Pages > Source: GitHub Actions (admin).

## Constraints
- Do not edit eval/ or harness/. Standard library only in web/*.py; `encoding="utf-8"`; pathlib.
- No personal data in bundles: entity fields as in out/entity.json (no address), no names,
  e-mails or phones from grant pages.
- The server binds to 127.0.0.1 only (each run spends the owner's `claude` budget).

## Acceptance
- `python web/server.py` + browser: a live run of `demo/01_gjovik_ski_event.json` shows the plan;
  a bad orgnr is caught in the browser; `demo/03_outside_innlandet.json` shows the rejection.
- The page opened from a static server (no api) shows the demo cases.
- All existing checks still PASS (nothing in harness/ or eval/ changed).

## Out of scope
Hosting the live pipeline, logins, sending or submitting applications.
