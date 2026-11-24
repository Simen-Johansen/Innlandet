# Known failure: the deadline does not say which project period it covers (2026-11-24)

**Request** (`request.json`): Hamar og Hedemarken Turistforening (registered in Frivillighetsregisteret),
"a two-day regional mountain running event for youth and adults in Hamar in **June 2027**", 80 000 NOK.
Run: `python harness/run.py docs/stress/date-gap/request.json --offline`, exit 0, all checks PASS,
model cost 0.20 USD. Output saved here: `matches.json`, `plan.json`, `grant_action_plan.md`, `run_stdout.txt`.

**What the plan says:** Arrangementsutvikling innen idrett, deadline **01.04.2027**, max 350 000 NOK.

**What the grant page says:** "Søknadsfrist: 1. april for arrangement i perioden juli til og med desember i
søknadsåret" and "1. november for arrangement i perioden januar til og med juni i påfølgende år". A June 2027
event belongs to the **1 November 2026** round, which closed before this run. The 1 April 2027 deadline only
covers July–December 2027. A club that follows the plan applies in the wrong round and is turned down.

**Why every check passed:** the frontmatter stores only the next deadline date (`deadlines: 2027-04-01`), not
the project period it covers, and the request has no project date. The code checks are right about what they
can see; the information needed to catch this is not in the data. The full deadline text is in the grant body
(`## Frister og rapportering`), but the guide writer does not compare it with the date in the project idea.

**Fix (future work, not built):** a `project_start` field in the request, and each deadline stored with the
project period it covers; when the right round has closed, say "next round not announced yet" instead of
showing a later deadline. See ROADMAP, "Future work".

## Second failure in the same run: eligibility the filter cannot see (found 2026-11-24)
"Hvem kan søke" for Arrangementsutvikling innen idrett requires an applicant affiliated with Norges idrettsforbund,
Det frivillige skyttervesen or Norges bilsportforbund. Hamar og Hedemarken Turistforening is **not** affiliated with any
of them: it is a member association of Den Norske Turistforening, which is a member of Norsk Friluftsliv (checked by
Simen, 24.11). The matcher still marked the grant as a match for HHT, and every check passed. The hard filter checks only
org form, region, Frivillighetsregisteret and deadline. Federation membership is not in Brreg data, so only the matcher
can catch this, and here it did not. A club that followed this plan would apply for a grant it cannot receive.
**Fix (future work, not built):** a frontmatter field for required federation membership, plus an explicit question
in the plan ("Is your club a member of NIF, DFS or NBF?") instead of an assumed yes.
