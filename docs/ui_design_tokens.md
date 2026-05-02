# GateRail UI Design Tokens

Reference for visual polish work. Extracted from the Claude Design handoff bundle (GateRail UI.html) on 2026-05-02. The matching Godot autoload is `godot/scripts/ui_theme.gd` — every token below has a constant on `UITheme`.

## Aesthetic in one sentence

Cool steel / charcoal command surface with a **single cyan accent** for active state and a **single amber accent** reserved exclusively for gate-related UI (Power Margin chip, gate icons, gate-link rails). Everything else is monochrome ink on dark backgrounds.

## Color palette

| Token | Hex | Use |
|---|---|---|
| `BG_0` | `#0a0f14` | App background, default clear color |
| `BG_1` | `#0f161d` | Default panels, alert strip background |
| `BG_2` | `#141d27` | HUD, inspector, tutorial panel backgrounds |
| `BG_3` | `#1a2632` | Schedule rows, contract cards, dispatch fields |
| `BG_4` | `#22313f` | Hover/active fill |
| `LINE` | `#243340` | Default panel borders, dividers |
| `LINE_2` | `#2d4050` | Button borders, secondary dividers |
| `LINE_HOT` | `#3a5468` | Hover border, focused chip border |
| `INK_0` | `#eaf3f7` | Primary value text (numbers, names) |
| `INK_1` | `#c5d4dd` | Body text |
| `INK_2` | `#8a9ba8` | Tertiary text, node labels on map |
| `INK_3` | `#5d6f7c` | Captions/labels (uppercase, .14em letter-spacing) |
| `INK_4` | `#3e505c` | Disabled text |
| `RAIL` | `#6fb3c8` | Default rail link colour on map |
| `GATE` | `#f0a52a` | Gate hubs, gate-link rails, gate icon |
| `GOOD` | `#5fcf8b` | ON pill, positive deltas, fulfilled contract |
| `WARN` | `#f3c53a` | DELAY pill, urgent contract, congestion |
| `BAD` | `#f06a55` | BLOCK pill, errors, disrupted links |
| `INFO` | `#71b6ff` | Info chips, T4-tier worlds, medical cargo |
| `VIOLET` | `#b48cff` | Lab nodes, research equipment, Power Margin icon |
| `ACCENT` | `#5fb8d4` | Cyan — primary action, focused fields, active tab |
| `ACCENT_2` | `#f0a52a` | Amber — gate-only accent (do **not** use for non-gate state) |

### Cargo dot fills

`food` `#6cd56b` · `ore`/`stone` `#a3a8ad` · `construction_materials` `#f0a52a` · `medical_supplies` `#7ec3ff` · `parts`/`metal` `#d8a468` · `research_equipment` `#b48cff` · `fuel` `#f0a52a` · `electronics` `#71b6ff` · `consumer_goods` `#5fcf8b` · `biomass` `#3a8a5c` · `water` `#4ec0e8`.

## Typography

- **Sora** (400/500/600/700) for UI labels and captions.
- **JetBrains Mono** (400/500/600) for numbers, IDs, route fragments, schedule meta.
- **Caption** style: 10px, uppercase, letter-spacing 0.14em, color `INK_3`.
- **Value** style: 15px JetBrains Mono, weight 600, color `INK_0`, `font-variant-numeric: tabular-nums`.
- **Body**: 12-13px Sora, color `INK_1`.
- Drop `Sora.ttf` and `JetBrainsMono.ttf` into `godot/assets/fonts/` and `UITheme` will pick them up automatically.

## Component recipes

### Panel
- Background: linear gradient from `BG_2` to `BG_1` (top to bottom). Plain `BG_1` is acceptable.
- Border: 1px solid `LINE`, radius 8px.
- Header bar: gradient `#152230` → `BG_2`, bottom border `LINE`. Title in caption style.

### Pill (status badge)
| State | Bg | Border | Text |
|---|---|---|---|
| `on` | `#0d2418` | `#1a4a30` | `GOOD` |
| `off` | `#1f1a14` | `#3a2c1c` | `INK_3` |
| `warn` / DELAY | `#2a2410` | `#4a3e1a` | `WARN` |
| `bad` / BLOCK | `#2a1614` | `#4a2620` | `BAD` |
| `gate` / GATE | `#2a1f10` | `#4a3a1c` | `GATE` |

Mono font, 9px, weight 600, letter-spacing 0.06em, padding 4×6, radius 4.

### Cargo chip
Pill-shaped (14px radius), `BG_3`, border `LINE`. 14×14 cargo dot on the left filled with the cargo color (table above), single uppercase letter inside in dark ink. Text is mono 11px `INK_1`.

### Alert chip
- Border colors per kind: ok `#1a4a30`, error `#4a2620`, disrupt `#5a3614`, warn `#4a3e1a`, info `LINE`.
- Each chip starts with a 4-letter mono prefix (`CMD`, `WARN`, `INFO`, `DISRUPT`, `CONGEST`, `CMD ERR`) coloured with the matching accent.
- Body text mono 11px `INK_1`, no wrap.

### Button variants
- **Primary**: gradient `#2a8aa8` → `#1d6b85`, border `#2c97b8`, dark ink text, faint cyan glow shadow.
- **Amber** (gate actions): gradient `#d18b20` → `#a26710`, border `#e1a13d`.
- **Ghost**: transparent bg, `LINE_2` border.
- **Danger**: text `BAD`, border `#3a2622`, bg fills to `#2a1614` on hover.

### Map iconography
- Node glyphs are 24-30px filled `#1a2632` with a 1.3-1.5px coloured stroke matching the node's role (depot cyan, settlement green, extractor amber, gate amber, lab violet).
- Trains: 12×6 rounded rect filled cyan `#9adcec`, dark `#031820` wheels. Blocked train uses `BAD` fill with a small `⚠` glyph above.
- Gate hubs: triple concentric circles (radius 5/11/14) in `GATE`, with a slowly-rotating dashed inner ring and a soft amber radial glow.
- Inter-world gate links: amber dashed path with animated `stroke-dashoffset` (4-pixel motion).

## Icon-generation prompt

Use this prompt to generate replacement art for `godot/assets/placeholders/`. Image-gen models will produce closer matches when given the full prompt verbatim.

```
Generate a single icon for a sci-fi logistics game UI named "GateRail".
Visual language:
- Flat 2D vector silhouette, 1.5px stroke, no fill (or single-color fill at 30% opacity behind the stroke).
- Stroke colour is a CSS variable that will be tinted at runtime — output the icon in pure white #FFFFFF on a transparent background.
- Geometric, angular, technical-blueprint style. Lines are crisp, corners are 90° or 45°, no gradients, no shadows, no glow.
- Square 64×64 viewBox for nodes/trains/cargo, 32×32 for UI controls. Include 4px of padding on all sides.
- Reference influences: Mass Effect codex iconography, Returnal HUD glyphs, OpenTTD modern icon packs, Material Design "Outlined" weight at 1.5px.
- Avoid: text, photo-realism, isometric perspective, drop shadows, multi-stroke decoration, mascots, logos.

Subject: <REPLACE — e.g. "warehouse depot building, three stacked storage bins on a rectangular foundation, a single antenna mast on top">

Output a single SVG with viewBox="0 0 64 64", a single <g stroke="white" stroke-width="1.5" fill="none" stroke-linecap="round" stroke-linejoin="round"> wrapping all paths, and no <style> blocks. Do not include comments. Do not output any prose around the SVG.
```

### Subject lines for the existing placeholder set

Paste each `Subject:` line in turn into the prompt above:

- `world_core` → `concentric planet rings, two equatorial bands, a small orbital pip at upper-right, dense cluster of dots inside the inner ring representing a populated core world`
- `world_frontier` → `planet circle with a single thin equatorial band, three small surface markers, a thin atmosphere ring`
- `world_outpost` → `irregular asteroid silhouette, two visible craters, a small docking pip on the upper edge`
- `node_depot` → `three stacked rectangular storage modules, a single antenna mast, a doorway slot on the front face`
- `node_settlement` → `geodesic dome on a rectangular base, two small windows on the base, a single chimney`
- `node_extractor` → `triangular crane silhouette over a horizontal extraction pad, a vertical drill bit between two support pillars`
- `node_industry` → `two factory smokestacks of unequal height on a rectangular plant body, three vent louvers, a square chimney cap`
- `node_gate_hub` → `three concentric circles with a slim cross-bar, a small power node on top, four equally-spaced docking spurs`
- `train_freight` → `three-segment rail freight train silhouette, side profile, two visible wheels per car, blunt prow`
- `train_passenger` → `single sleek rail car, side profile, three windows, two wheels, slightly rounded prow`
- `train_blocked` → `single rail car with a warning triangle overlay above the cabin, two wheels, side profile`
- `cargo_food` → `wheat sheaf, three stalks, bound in the middle, leaves at the base`
- `cargo_ore` → `irregular faceted ore chunk, four visible facets, set on a thin baseline`
- `cargo_construction_materials` → `stack of three I-beams in cross-section, top beam offset slightly`
- `cargo_medical_supplies` → `medical cross inside a circle, four equal arms, single border ring`
- `cargo_parts` → `single hex nut centred over a four-toothed gear wheel`
- `cargo_research_equipment` → `Erlenmeyer flask with two horizontal level marks, a single bubble inside`
- `ui_play` → `right-pointing solid triangle, baseline equal to height`
- `ui_pause` → `two equal vertical bars, gap equal to bar width`
- `ui_step` → `right-pointing triangle followed immediately by a thin vertical bar (skip-forward glyph)`
- `ui_refresh` → `circular arrow with a single arrowhead at the top-right, 270° arc`
- `ui_dispatch` → `paper airplane silhouette pointing up-right, single fold line visible`
- `ui_cancel` → `circle with a diagonal slash from upper-left to lower-right`
- `ui_contract` → `document silhouette with a folded upper-right corner, three horizontal text lines`
- `ui_cash` → `rounded rectangle banknote with a small coin (concentric circle) overlapping the lower-right`
- `ui_reputation` → `five-pointed star, single thin internal pentagon to suggest depth`
- `ui_warning` → `equilateral triangle, single exclamation mark inside (vertical bar plus dot)`
- `ui_schedule_on` → `clock face at 12 o'clock with a small check mark in the lower-right quadrant`
- `ui_schedule_off` → `clock face at 12 o'clock with a small slash through the upper-right`

## What to keep and what to retire

**Keep** (already lifted into `UITheme`):
- Dark cool steel base + cyan/amber accent system.
- Pill / chip / cargo-chip / alert-chip recipes.
- Caption-vs-value text hierarchy.
- Schedule row container styling.

**Retire after Slice 30A lands**:
- Inline `Color(0.x, 0.y, 0.z)` literals for state colors — replace with `UITheme.GOOD/WARN/BAD/INFO`.
- Per-panel `StyleBoxFlat.new()` constructions — replace with `UITheme.panel_style(...)`.
- Bespoke alert chip color match-blocks — `UITheme.alert_chip_style(kind)` covers them.
