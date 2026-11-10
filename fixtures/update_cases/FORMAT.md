# Formats for the W45 human-made files

## context/sources.json  (one entry per domain that any grant file links to)
| Key | Value | Who fills it |
|---|---|---|
| `user_agent` | the same string `harness/entity.py` sends | done |
| `domain` | lowercase host without `www.` (`hamar.kommune.no`) | done |
| `policy` | `auto` (task 015 may fetch it) or `manual` (only humans update it) | human, after reading robots |
| `robots_file` | `fixtures/robots/<domain>.txt` (saved copy) | done |
| `robots_checked` | `YYYY-MM-DD`, the day you ran `tools/save_sources.py robots` | human |
| `checked_by` | your initials | human |
| `note` | one line on why | human |
Rule (enforced by `eval/check_sources.py`): `auto` only if robots.txt allows our agent, `*`, ClaudeBot,
Claude-User, Claude-SearchBot, anthropic-ai and GPTBot for every grant URL on that domain.
A new domain in any grant file needs a new entry.

## fixtures/robots/<domain>.txt
The robots.txt file exactly as downloaded by `python tools/save_sources.py robots`. Never edited.

## fixtures/update_cases/<case>/
| Path | Content |
|---|---|
| `grants/<id>.md` | the grant file **before** the weekly run (normal grant format) |
| `pages/<id>.html` | the page the updater "downloads" offline. No file = request failed |
| `expected.json` | the human's answer, see below |
| `../sources.json` | test policy shared by all cases (innlandetfylke.no auto, hamar manual) |

`expected.json`:
```json
{"today": "2026-11-05",
 "why": "one sentence a reader can check against the rule table in task 015",
 "grants": {"<grant id>": "unchanged | touched | updated_text | needs_review | failed | skipped_manual"},
 "forbidden_strings": ["Kari Testesen", "kari.testesen@example.no"]}
```
`forbidden_strings` lists the fictional person on the pages; it must never reach a written file.
Never put a real person's name here (that would commit it).

## The 8 cases
| Case | Page | Expected |
|---|---|---|
| real_unchanged | real page (anonymised), same Sist endret | unchanged |
| real_first_run | real page, our hand copy is older | needs_review |
| real_template_changed | real page with "Sist endret" removed | failed |
| page_unreachable | no page | failed |
| manual_domain | Hamar grant, no page | skipped_manual |
| syn_touched | synthetic page, newer date, same text | touched |
| syn_wording | synthetic, one Formål sentence reworded | updated_text |
| syn_deadline | synthetic, deadline sentence changed | needs_review |

The synthetic grant (`provider: test_synthetic`, page id 99001) exists only here, never in context/grants/.
Prompt injection on a page (an instruction with no numbers in it) is deliberately **not** a case here:
the current rules would apply it as `updated_text`. That is the before-picture for stress test 012.
