# Source survey: Hamar and neighbouring municipalities (task 010)

**Question:** do municipal sites only repeat the county's grants (then we can skip them), or do
they have their own schemes for voluntary organisations (then they are manual sources and the gap
is a known limitation)?

**Method (2026-11-10, Simen + Claude Code):** fetched `robots.txt` with our User-Agent and tested
our UA, `*`, ClaudeBot, Claude-User, Claude-SearchBot, anthropic-ai and GPTBot against a grant path.
Robots.txt allowed Claude-User on all six sites, so one grant overview page per municipality was
opened and only the scheme names and link targets were noted. No names, e-mails or phone numbers
were recorded. Robots copies are not saved in `fixtures/robots/` because none of these domains is in
`sources.json` (Hamar's copy is already there).

| Municipality | Domain | Own schemes for voluntary orgs (names) | Links to county? | robots.txt | Policy |
|---|---|---|---|---|---|
| Hamar | hamar.kommune.no | Tilskudd til kulturarbeid (forskrift) | no | blocks **ClaudeBot**; others allowed | manual (in `sources.json`) |
| Stange | stange.kommune.no | Tilskudd til aktivitet og drift (kulturmidler), kulturarrangementer og kulturprosjekter, fritidskassen | yes, one (kulturarenaer, page 18509) | same file as Hamar: blocks **ClaudeBot** | manual, if added |
| Løten | loten.kommune.no | Kulturtilskudd, tilskudd barn/ungdomsformål, local legater/fond | yes, a whole page ("Tilskudd hos Innlandet fylkeskommune": 23015, 2658, 36453, 36451, 16834) | same file as Hamar: blocks **ClaudeBot** | manual, if added |
| Ringsaker | ringsaker.kommune.no | not found by a plain fetch (menus not in the HTML); **check by hand** | unknown | allows all agents | not decided |
| Elverum | elverum.kommune.no | Tilskudd til drift (kultur og idrett), tilskudd til inkludering av barn og unge | not seen | allows all agents | manual, if added |
| Gjøvik | gjovik.kommune.no | Aktivitetsmidler til lag og foreninger, kulturmidler og driftstilskudd, stimuleringsmidler til frivillige lag, kulturarrangementer, integreringsarbeid, helse- og omsorgsformål (+ more) | not seen | allows all agents | manual, if added |

## Findings
1. **Municipalities add local schemes; they do not just duplicate the county.** Every municipality where we found
   the grant page has its own operating/activity grant for clubs (driftstilskudd/kulturmidler). Only
   Løten and Stange link to county schemes, and those links duplicate grants we already get from
   innlandetfylke.no.
2. **Same grant, different URL.** Løten links to county pages 2658 and 36453 under different slugs
   than the ones in our grant files. This supports keying the catalog on the numeric page id.
3. **Robots stance differs by platform, not by municipality.** Hamar, Stange and Løten serve the
   same 283-line robots.txt (the same CMS) that disallows ClaudeBot; Ringsaker, Elverum and Gjøvik
   allow every agent. Even where robots.txt allows us, each site has its own layout, so one parser
   per municipality would be needed.

## Decision
Keep **innlandetfylke.no as the only `auto` source** (scope decision W45 stands). Municipal schemes
stay manual, one hand-maintained grant file at a time (as with Hamar). **Known limitation:** a club in
Stange, Løten, Elverum, Gjøvik or Ringsaker will not see its own municipality's driftstilskudd/kulturmidler
until someone adds that grant by hand. Adding a municipal domain to `sources.json` is a separate
decision, made when its first grant file is written.
