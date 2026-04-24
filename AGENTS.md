# AGENTS

Repository-level guidance for GateRail agents.

## Project constraints

All changes in this repository must follow these constraints unless a higher-priority instruction explicitly overrides them.

1. **CLI-only product surface**
   - Implement and expose features through command-line workflows.
   - Do not add GUI, browser, game-engine, or graphics-rendering interfaces.

2. **No external runtime dependencies without approval**
   - Prefer Python standard library and existing project dependencies.
   - Do not introduce new third-party packages unless explicitly requested.

3. **No prohibited IP references**
   - Use original terminology, names, and lore.
   - Do not reference or imitate protected franchise-specific names, factions, characters, or settings.

4. **Text-first outputs**
   - Keep simulation/report output readable in plain terminal text.
   - Avoid introducing formats that require proprietary tools to interpret.

## Test-update policy

When you change rules, formulas, validation behavior, CLI contract, or data model assumptions:

- Update or add tests in the same change.
- Prefer narrowly targeted tests that lock expected behavior.
- If expected behavior intentionally changes, update assertions to the new canonical result and document why in commit/PR notes.

## Response format requirement for future coding agents

When a user asks for code modifications and requests full-file output, provide the **entire updated file contents** for each changed file, not partial snippets.
When full-file output is not requested, normal concise diffs/summaries are acceptable.
