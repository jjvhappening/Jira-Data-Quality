## [Unreleased]

### Added
- `SKILL.md`: Squad Inference from Assignee (Tier 3 fallback) — batch assignee lookup via JQL, parent epic team chain, and hard-floor guidance for unassigned+no-team bugs; prompted by 61 no-team bugs in Player Area bug fix session

### Added
- `SKILL.md`: New `## Scope` section at the top distinguishing Initiative vs Bug issue types, with the JQL for open bugs with Squad empty, and explicit exclusions for GAM and Fraud Investigation team
- `SKILL.md`: Expanded Squad Auto-fill section with confirmed team→squad mapping table (16 team names, verified against Notion Player Org 2026-05-29), suffix-stripping rules for both paren and dash patterns, and a note on missing Gamification Squad option
- `SKILL.md`: Updated skill `description` frontmatter to include Bug issue type and Player Area projects (BCN, PLAYER, FPT, TRX, MANAGE)

### Changed
- `SKILL.md`: Squad Auto-fill algorithm now applies the confirmed mapping table *before* fuzzy-matching — avoids ambiguous matches for well-known teams
- `SKILL.md`: `getJiraIssueTypeMetaWithFields` call now targets Bug issue type (ID: `10004`) for bug workflows, not Initiative (ID: `10366`)
