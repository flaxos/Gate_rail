extends Node

## UITheme — design tokens lifted from the GateRail design bundle.
##
## Token names mirror the CSS custom properties in the design HTML
## (`--bg-0`, `--ink-2`, `--accent`, etc.) so swapping a call site over
## from a hardcoded Color literal to a UITheme constant is a mechanical
## edit. Helper factories (panel_style, alert_chip_style, ...) build the
## StyleBox flavours used across the existing panels without changing
## any layout.

# ───────────── Backgrounds ─────────────
const BG_0 := Color("0a0f14")
const BG_1 := Color("0f161d")
const BG_2 := Color("141d27")
const BG_3 := Color("1a2632")
const BG_4 := Color("22313f")

# ───────────── Lines / dividers ─────────────
const LINE := Color("243340")
const LINE_2 := Color("2d4050")
const LINE_HOT := Color("3a5468")

# ───────────── Ink (text) ─────────────
const INK_0 := Color("eaf3f7")
const INK_1 := Color("c5d4dd")
const INK_2 := Color("8a9ba8")
const INK_3 := Color("5d6f7c")
const INK_4 := Color("3e505c")

# ───────────── Status / accents ─────────────
const RAIL := Color("6fb3c8")
const GATE := Color("f0a52a")
const GATE_SOFT := Color("7a5418")
const GOOD := Color("5fcf8b")
const WARN := Color("f3c53a")
const BAD := Color("f06a55")
const INFO := Color("71b6ff")
const VIOLET := Color("b48cff")
const ACCENT := Color("5fb8d4")
const ACCENT_2 := Color("f0a52a")

# ───────────── Cargo dot fills (match design's .cargo-dot.<kind>) ─────────────
const CARGO_FOOD := Color("6cd56b")
const CARGO_ORE := Color("a3a8ad")
const CARGO_CONSTR := Color("f0a52a")
const CARGO_MED := Color("7ec3ff")
const CARGO_PARTS := Color("d8a468")
const CARGO_RESEARCH := Color("b48cff")

# ───────────── Radii / sizes ─────────────
const RADIUS_1 := 4
const RADIUS_2 := 8
const RADIUS_3 := 12
const FONT_SIZE_LABEL := 10
const FONT_SIZE_BODY := 12
const FONT_SIZE_VALUE := 15
const FONT_SIZE_TITLE := 13

# ───────────── Optional custom fonts ─────────────
# If the user drops Sora.ttf / JetBrainsMono.ttf into godot/assets/fonts/
# we pick them up automatically; otherwise the engine default is used.
const SORA_PATH := "res://assets/fonts/Sora.ttf"
const MONO_PATH := "res://assets/fonts/JetBrainsMono.ttf"

var _font_ui: Font = null
var _font_mono: Font = null


func _ready() -> void:
	if ResourceLoader.exists(SORA_PATH):
		_font_ui = load(SORA_PATH)
	if ResourceLoader.exists(MONO_PATH):
		_font_mono = load(MONO_PATH)


func ui_font() -> Font:
	return _font_ui


func mono_font() -> Font:
	return _font_mono


# ───────────── Style factories ─────────────

func panel_style(variant: String = "default") -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	match variant:
		"hud", "topbar":
			style.bg_color = BG_2
			style.border_color = LINE
		"alert":
			style.bg_color = BG_1
			style.border_color = LINE
		"inspector":
			style.bg_color = BG_2
			style.border_color = ACCENT_2
		"tutorial":
			style.bg_color = BG_2
			style.border_color = ACCENT
		_:
			style.bg_color = BG_1
			style.border_color = LINE
	style.set_border_width_all(1)
	style.set_corner_radius_all(RADIUS_2)
	return style


func sched_row_style(variant: String = "default") -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.bg_color = BG_3
	match variant:
		"warn":
			style.border_color = Color("4a3e1a")
		"bad":
			style.border_color = Color("4a2620")
		"ok":
			style.border_color = Color("1a4a30")
		_:
			style.border_color = LINE
	style.set_border_width_all(1)
	style.set_corner_radius_all(7)
	style.content_margin_left = 10.0
	style.content_margin_right = 10.0
	style.content_margin_top = 9.0
	style.content_margin_bottom = 9.0
	return style


func pill_style(state: String) -> StyleBoxFlat:
	# state: on | off | warn | bad | gate
	var style := StyleBoxFlat.new()
	style.set_corner_radius_all(RADIUS_1)
	style.set_border_width_all(1)
	style.content_margin_left = 6.0
	style.content_margin_right = 6.0
	style.content_margin_top = 3.0
	style.content_margin_bottom = 3.0
	match state:
		"on":
			style.bg_color = Color("0d2418")
			style.border_color = Color("1a4a30")
		"warn":
			style.bg_color = Color("2a2410")
			style.border_color = Color("4a3e1a")
		"bad":
			style.bg_color = Color("2a1614")
			style.border_color = Color("4a2620")
		"gate":
			style.bg_color = Color("2a1f10")
			style.border_color = Color("4a3a1c")
		_:
			style.bg_color = Color("1f1a14")
			style.border_color = Color("3a2c1c")
	return style


func pill_text_color(state: String) -> Color:
	match state:
		"on":
			return GOOD
		"warn":
			return WARN
		"bad":
			return BAD
		"gate":
			return GATE
		_:
			return INK_3


func alert_chip_style(kind: String) -> StyleBoxFlat:
	var style := StyleBoxFlat.new()
	style.set_corner_radius_all(6)
	style.set_border_width_all(1)
	style.content_margin_left = 9.0
	style.content_margin_right = 9.0
	style.content_margin_top = 5.0
	style.content_margin_bottom = 5.0
	match kind:
		"command_ok":
			style.bg_color = BG_2
			style.border_color = Color("1a4a30")
		"command_error", "bridge_error":
			style.bg_color = Color("1a0d0c")
			style.border_color = Color("4a2620")
		"disruption":
			style.bg_color = Color("1a0e06")
			style.border_color = Color("5a3614")
		"congestion", "warning":
			style.bg_color = BG_2
			style.border_color = Color("4a3e1a")
		"tutorial":
			style.bg_color = BG_2
			style.border_color = LINE_HOT
		_:
			style.bg_color = BG_2
			style.border_color = LINE
	return style


func alert_chip_accent_color(kind: String) -> Color:
	match kind:
		"command_ok":
			return GOOD
		"command_error", "bridge_error":
			return BAD
		"disruption":
			return GATE
		"congestion", "warning":
			return WARN
		"tutorial":
			return ACCENT
		_:
			return ACCENT


func cargo_dot_color(cargo_id: String) -> Color:
	match cargo_id:
		"food":
			return CARGO_FOOD
		"ore", "stone":
			return CARGO_ORE
		"construction_materials":
			return CARGO_CONSTR
		"medical_supplies":
			return CARGO_MED
		"parts", "metal":
			return CARGO_PARTS
		"research_equipment":
			return CARGO_RESEARCH
		"fuel":
			return GATE
		"electronics":
			return INFO
		"consumer_goods":
			return GOOD
		"biomass":
			return Color("3a8a5c")
		"water":
			return Color("4ec0e8")
		_:
			return INK_2


# ───────────── Label helpers ─────────────

func style_label_caption(label: Label) -> void:
	# small uppercase label, ink-3
	label.modulate = Color(1.0, 1.0, 1.0)
	label.add_theme_color_override("font_color", INK_3)
	label.add_theme_font_size_override("font_size", FONT_SIZE_LABEL)
	if _font_ui != null:
		label.add_theme_font_override("font", _font_ui)


func style_label_value(label: Label, mono: bool = false) -> void:
	label.modulate = Color(1.0, 1.0, 1.0)
	label.add_theme_color_override("font_color", INK_0)
	label.add_theme_font_size_override("font_size", FONT_SIZE_VALUE)
	if mono and _font_mono != null:
		label.add_theme_font_override("font", _font_mono)
	elif _font_ui != null:
		label.add_theme_font_override("font", _font_ui)


func style_label_body(label: Label) -> void:
	label.modulate = Color(1.0, 1.0, 1.0)
	label.add_theme_color_override("font_color", INK_1)
	label.add_theme_font_size_override("font_size", FONT_SIZE_BODY)
	if _font_ui != null:
		label.add_theme_font_override("font", _font_ui)


func style_label_mono(label: Label, color: Color = INK_1) -> void:
	label.modulate = Color(1.0, 1.0, 1.0)
	label.add_theme_color_override("font_color", color)
	label.add_theme_font_size_override("font_size", FONT_SIZE_BODY)
	if _font_mono != null:
		label.add_theme_font_override("font", _font_mono)
