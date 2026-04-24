# AGENTS

Repository-level guidance for GateRail agents.

## Project constraints

All changes in this repository must follow these constraints unless a higher-priority instruction explicitly overrides them.

1. **Backend product surface stays CLI/stdio-first**
   - Implement and expose Python simulation features through command-line or JSON-over-stdio workflows.
   - Do not add browser interfaces.
   - Godot client work is allowed only under `godot/` and must communicate with the Python backend through the documented stdio bridge unless explicitly approved otherwise.
   - Do not duplicate simulation rules in Godot; the Python fixed-tick backend remains authoritative.

2. **No external runtime dependencies without approval**
   - Prefer Python standard library and existing project dependencies.
   - Do not introduce new third-party packages unless explicitly requested.

3. **No prohibited IP references**
   - Use original terminology, names, and lore.
   - Do not reference or imitate protected franchise-specific names, factions, characters, or settings.

4. **Text-first outputs**
   - Keep simulation/report output readable in plain terminal text.
   - Keep bridge contracts JSON-readable and versioned.
   - Godot scene, script, and project files must remain text-serializable.
   - Avoid introducing formats that require proprietary tools to interpret.

## Test-update policy

When you change rules, formulas, validation behavior, CLI contract, or data model assumptions:

- Update or add tests in the same change.
- Prefer narrowly targeted tests that lock expected behavior.
- If expected behavior intentionally changes, update assertions to the new canonical result and document why in commit/PR notes.

## Response format requirement for future coding agents

When a user asks for code modifications and requests full-file output, provide the **entire updated file contents** for each changed file, not partial snippets.
When full-file output is not requested, normal concise diffs/summaries are acceptable.
