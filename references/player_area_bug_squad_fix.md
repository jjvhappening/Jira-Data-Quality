---
name: Player Area Bug Squad Fix Reference
description: Stable facts for bulk-fixing Squad fields on Player Area bugs — team→squad mapping, Squad option IDs, project field availability, and known exclusions.
type: reference
project: Jira Data Quality
---

# Player Area Bug Squad Fix

## Scope

**In scope:** BCN, PLAYER, FPT, TRX, MANAGE (issue type: Bug, statusCategory != Done)

**Excluded:**
- **GAM** — Gaming is a separate product area, not part of Player
- **Fraud Investigation team** — This is an ops team, not a Player engineering team; FPT-303 is the known example
- **PLT** — Platform; check relevance before including

**JQL (open bugs, Squad empty):**
```
issuetype = Bug AND project in (BCN, PLAYER, FPT, TRX, MANAGE) AND statusCategory != Done AND Squad is EMPTY ORDER BY project ASC
```

---

## Squad Field Availability by Project

As of 2026-05-29, the Squad field (`customfield_11250`) is present on Bug screens for:

| Project | Squad field on Bugs? | Notes |
|---------|---------------------|-------|
| BCN | ✅ | Added 2026-05-29 by Jon |
| FPT | ✅ | Added 2026-05-29 by Jon |
| TRX | ✅ | Added 2026-05-29 by Jon |
| PLAYER | ✅ | Added 2026-05-29 by Jon |
| MANAGE | ✅ | Already present |
| GAM | ✅ | Present but excluded from scope |

---

## Confirmed Team → Squad Mapping

Verified against Notion Player Org page (2026-05-29). Strip tribe suffixes before matching:
- Paren suffix: "Thundercats (Engagement Tribe)" → "Thundercats"
- Dash suffix: "Payment Platform - Transact" → "Payment Platform"

| Team name (raw or stripped) | Squad field value | Squad option ID | Tribe |
|---|---|---|---|
| Engagement Integrations | Engagement Integrations | 19799 | Player Engagement |
| Loyalty | Loyalty | 20518 | Player Engagement |
| Thundercats | Thundercats | 19798 | Player Engagement |
| GraySkull / Grayskull / Bonus Platform | GraySkull (Bonus Platform) | 19797 | Player Engagement |
| Mobius | Mobius Platform | 19800 | Player Engagement |
| Payment Experience | Payment Experience | 19808 | Transact |
| Payment Platform | Payment Platform | 19807 | Transact |
| Wallet Core | Wallet Core | 19805 | Transact |
| Wallet Integrations | Wallet Integrations | 19810 | Transact |
| APM Experience | APM Experience | 19806 | Transact |
| Card Experience | Card Experience | 19809 | Transact |
| Fraud Prevention | Fraud Engineering | 19784 | Fraud Prevention |
| Player Onboarding | Player Onboarding | 19792 | Manage |
| Player Identity | Player Identity | 19793 | Manage |
| Player Account / Player Manage / PAM | Player Account | 19794 | Manage |
| Manage Platform | Manage Platform | 19795 | Manage |
| Player Support | Player Support | 19796 | Manage |

**Skip (no Squad match):**
- Fraud Investigation — ops team, not Player engineering
- TRX-1911 "Player Manage - PAM" → Player Account (confirmed by Jon 2026-05-29)

---

## Known Blocked Cases

**Gamification squad option missing from Jira field (21 BCN bugs):**
Teams affected: "Gamification (Player Engagement Tribe)", "Player Experience - Gamification"

The Squad dropdown does not include "Gamification" or "Player Experience - Gamification" as valid options. A Jira admin needs to add these Squad options to `customfield_11250` before these bugs can be fixed via API.

BCN bugs affected (as of 2026-05-29): BCN-10577, BCN-10560, BCN-10553, BCN-10112, BCN-10110, BCN-10078, BCN-10075, BCN-10012, BCN-9977, BCN-9933, BCN-9515, + ~10 more.

---

## Other Known Squad Option IDs (from MANAGE allowedValues)

| Squad | ID |
|---|---|
| Sb Club Migration | 19802 |
| Player Experience - Growth | 19803 |
| Fraud Ops | 19785 |
| Hunch (F2P) | 20803 |
| Retail Sports Experience | 19786 |
| Retail Gaming Experience | 19787 |
| Retail Operations Experience | 19788 |
| Retail Platform Foundation | 19789 |
| Retail Added Value Experience | 19790 |
| Retail Terminals Platform | 19791 |

---

## API Format

Squad field is a multiselect — always pass as array:
```json
{"customfield_11250": [{"value": "Squad Name"}]}
```

Using the `value` string works reliably; no need to use the numeric `id`.

---

## Session History

- **2026-05-29** — 155 bugs fixed (BCN: 94, TRX: 51, FPT: 8, PLAYER: 2). Squad field added to BCN/FPT/TRX/PLAYER bug screens by Jon during the session.

Last updated: 2026-05-29
