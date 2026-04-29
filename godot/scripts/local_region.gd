extends Node2D

const TOPBAR_HEIGHT := 56.0
const TOOLRAIL_WIDTH := 64.0
const HUD_WIDTH := 360.0
const STATUSBAR_HEIGHT := 44.0

const CANVAS_PADDING := 10.0
const GRID_MICRO := 24.0
const GRID_MAJOR := 120.0
const SNAP_CELL_HALF := GRID_MICRO * 0.5

const COLOR_BG_0 := Color("#0b1522")
const COLOR_BG_1 := Color("#12233b")
const COLOR_BG_2 := Color("#1e3a5f")
const COLOR_PANEL := Color(0.055, 0.114, 0.188, 0.90)
const COLOR_PANEL_2 := Color(0.078, 0.157, 0.259, 0.94)
const COLOR_HAIR := Color(0.584, 0.647, 0.651, 0.25)
const COLOR_HAIR_2 := Color(0.584, 0.647, 0.651, 0.45)
const COLOR_STEEL := Color("#95a5a6")
const COLOR_STEEL_2 := Color("#bdc3c7")
const COLOR_ICE := Color("#dfe8ef")
const COLOR_AMBER := Color("#f39c12")
const COLOR_AMBER_HOT := Color("#ffc15e")
const COLOR_OK := Color("#2ecc71")
const COLOR_WARN := Color("#e67e22")
const COLOR_ERR := Color("#e74c3c")
const COLOR_CYAN := Color("#58c6d8")
const COLOR_RECIPE_BLOCKED := Color("#ff6f59")

const TOOL_SELECT := "select"
const TOOL_PAN := "pan"
const TOOL_RAIL := "rail"
const TOOL_NODE := "node"
const TOOL_WIRE := "wire"
const TOOL_GATE := "gate"
const TOOL_TRAIN := "train"
const TOOL_DEMOLISH := "demolish"
const TOOL_LAYERS := "layers"

const TOOLS: Array = [
	{"id": TOOL_SELECT, "label": "Select", "key": "V", "group": "cursor"},
	{"id": TOOL_PAN, "label": "Pan", "key": "H", "group": "cursor"},
	{"id": TOOL_RAIL, "label": "Lay Rail", "key": "R", "group": "build"},
	{"id": TOOL_NODE, "label": "Place Node", "key": "N", "group": "build"},
	{"id": TOOL_WIRE, "label": "Wire Ports", "key": "C", "group": "build"},
	{"id": TOOL_GATE, "label": "Gate Hub", "key": "G", "group": "build"},
	{"id": TOOL_TRAIN, "label": "Purchase Train", "key": "T", "group": "build"},
	{"id": TOOL_DEMOLISH, "label": "Demolish", "key": "X", "group": "destroy"},
	{"id": TOOL_LAYERS, "label": "Layer Overlays", "key": "L", "group": "view"},
]

var _canvas_layer: CanvasLayer
var _topbar: PanelContainer
var _toolrail: PanelContainer
var _canvas_panel: Control
var _hud: PanelContainer
var _statusbar: PanelContainer

var _breadcrumb_label: Label
var _credits_value: Label
var _power_value: Label
var _tick_value: Label

var _region_label: Label
var _region_meta: Label

var _planet_name: Label
var _planet_meta: Label
var _planet_stab_fill: ColorRect

var _inventory_list: VBoxContainer
var _inventory_sub: Label
var _overlay_list: VBoxContainer
var _overlay_sub: Label
var _gate_card: Control
var _gate_title_value: Label
var _gate_status_value: Label
var _gate_bars_box: VBoxContainer
var _gate_linked_value: Label
var _gate_activation_value: Label
var _queue_list: VBoxContainer
var _queue_sub: Label

var _tool_buttons: Dictionary = {}
var _active_tool: String = TOOL_SELECT

var _statusbar_mode_chip: Control
var _statusbar_mode_label: Label
var _statusbar_bridge_chip: Control
var _statusbar_bridge_label: Label

var _latest_snapshot: Dictionary = {}
var _world_id: String = ""
var _selected_world: Dictionary = {}
var _world_nodes: Array = []
var _world_links: Array = []
var _node_positions: Dictionary = {}
var _gate_hub_node_id: String = ""

var _canvas_rect: Rect2 = Rect2()

# Layout-coord transform (recomputed each rebuild): screen = canvas_center + (layout - bbox_center) * scale
var _layout_bbox_center: Vector2 = Vector2.ZERO
var _layout_spread_scale: float = 1.0

# View pan + zoom state applied to world content via draw_set_transform.
var _view_offset: Vector2 = Vector2.ZERO
var _view_scale: float = 1.0
var _panning: bool = false
var _pan_button: int = -1
const PAN_KEY_STEP: float = 32.0
const ZOOM_MIN: float = 0.4
const ZOOM_MAX: float = 2.5
const ZOOM_STEP: float = 1.1

# Build-tool state
var _build_node_kind: String = "depot"
var _rail_origin_id: String = ""
var _node_kind_popup: PopupMenu
var _cargo_kind_popup: PopupMenu
var _cargo_popup_options: Array = []
var _route_tuning_popup: PopupPanel
var _route_tuning_meta: Label
var _route_units_spin: SpinBox
var _route_interval_spin: SpinBox
var _build_seq: int = 0
var _pending_node_local_pos: Vector2 = Vector2.ZERO
var _pending_build_command: Dictionary = {}
var _pending_preview_kind: String = ""
var _pending_preview_target_id: String = ""
var _last_preview_result: Dictionary = {}
var _route_train_id: String = ""
var _route_origin_id: String = ""
var _pending_route_dest_id: String = ""
var _pending_route_tuning_train_id: String = ""
var _pending_route_tuning_origin_id: String = ""
var _pending_route_tuning_dest_id: String = ""
var _pending_route_tuning_cargo: String = ""

# Inspection state (TOOL_SELECT)
var _selected_local_kind: String = ""
var _selected_local_id: String = ""

# Facility drill-in / internal wiring state
var _facility_component_boxes: Dictionary = {}
var _facility_port_hitboxes: Dictionary = {}
var _facility_port_centers: Dictionary = {}
var _wire_dragging: bool = false
var _wire_source_endpoint: Dictionary = {}
var _wire_mouse_pos: Vector2 = Vector2.ZERO

const ALL_CARGO_TYPES: Array = [
	"food",
	"water",
	"ore",
	"stone",
	"biomass",
	"fuel",
	"metal",
	"parts",
	"electronics",
	"construction_materials",
	"consumer_goods",
	"medical_supplies",
	"research_equipment",
]

# Terrain / visual state
var _terrain_patches: Array = []  # Array of {pos, size, color, alpha}
var _terrain_zones: Array = []    # Array of {pos, radius, zone_type}
var _show_zone_overlay: bool = false
var _last_terrain_world_id: String = ""

const DEFAULT_TRAIN_CAPACITY: int = 8
const DEFAULT_ROUTE_INTERVAL_TICKS: int = 4
const DEFAULT_GATE_CAPACITY_PER_TICK: int = 4
const DEFAULT_GATE_POWER_REQUIRED: int = 80
const NODE_HIT_RADIUS: float = 30.0
const LINK_HIT_DISTANCE: float = 12.0


func _ready() -> void:
	_world_id = String(SceneNav.selected_world_id)
	_build_ui()
	_build_node_kind_popup()
	_build_cargo_kind_popup()
	_build_route_tuning_popup()
	GateRailBridge.snapshot_received.connect(_on_snapshot_received)
	GateRailBridge.bridge_error.connect(_on_bridge_error)
	GateRailBridge.bridge_status_changed.connect(_on_bridge_status_changed)
	get_viewport().size_changed.connect(_on_viewport_size_changed)

	var fixture := GateRailBridge.load_fixture_snapshot()
	if not fixture.is_empty():
		_apply_snapshot(fixture)
	_update_bridge_chip(GateRailBridge.is_bridge_running())
	GateRailBridge.request_snapshot()


func _build_node_kind_popup() -> void:
	_node_kind_popup = PopupMenu.new()
	_node_kind_popup.add_item("Depot", 0)
	_node_kind_popup.add_item("Warehouse", 1)
	_node_kind_popup.add_item("Settlement", 2)
	_node_kind_popup.add_item("Extractor", 3)
	_node_kind_popup.add_item("Industry", 4)
	_node_kind_popup.id_pressed.connect(_on_node_kind_confirmed)
	add_child(_node_kind_popup)


func _on_node_kind_confirmed(id: int) -> void:
	var kinds := ["depot", "warehouse", "settlement", "extractor", "industry"]
	if id >= 0 and id < kinds.size():
		_build_node_kind = kinds[id]
	_request_node_preview(_build_node_kind, _pending_node_local_pos)


func _build_cargo_kind_popup() -> void:
	_cargo_kind_popup = PopupMenu.new()
	_cargo_kind_popup.id_pressed.connect(_on_cargo_kind_confirmed)
	add_child(_cargo_kind_popup)


func _open_cargo_kind_popup(origin_id: String, destination_id: String) -> void:
	_pending_route_dest_id = destination_id
	_cargo_popup_options = _cargo_options_for_route(origin_id, destination_id)
	if _cargo_popup_options.is_empty():
		_cargo_popup_options = ALL_CARGO_TYPES.duplicate()
	_cargo_kind_popup.clear()
	var suggested := _suggest_cargo_for_route(origin_id, destination_id)
	for i in _cargo_popup_options.size():
		var cargo_id := str(_cargo_popup_options[i])
		var label := cargo_id.replace("_", " ").capitalize()
		if cargo_id == suggested:
			label += "  ★"
		_cargo_kind_popup.add_item(label, i)
	_cargo_kind_popup.position = Vector2i(get_viewport().get_mouse_position())
	_cargo_kind_popup.popup()


func _on_cargo_kind_confirmed(id: int) -> void:
	if id < 0 or id >= _cargo_popup_options.size():
		return
	if _route_train_id.is_empty() or _route_origin_id.is_empty() or _pending_route_dest_id.is_empty():
		return
	var cargo_id := str(_cargo_popup_options[id])
	var origin_id := _route_origin_id
	var dest_id := _pending_route_dest_id
	_pending_route_dest_id = ""
	_open_route_tuning_popup(_route_train_id, origin_id, dest_id, cargo_id)


func _build_route_tuning_popup() -> void:
	_route_tuning_popup = PopupPanel.new()
	_route_tuning_popup.title = "Route Tuning"
	_route_tuning_popup.exclusive = true
	_route_tuning_popup.popup_hide.connect(_on_route_tuning_popup_hidden)
	add_child(_route_tuning_popup)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	_route_tuning_popup.add_child(margin)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 10)
	col.custom_minimum_size = Vector2(280, 0)
	margin.add_child(col)

	var title := Label.new()
	title.text = "ROUTE PARAMETERS"
	title.add_theme_color_override("font_color", COLOR_CYAN)
	title.add_theme_font_size_override("font_size", 12)
	col.add_child(title)

	_route_tuning_meta = Label.new()
	_route_tuning_meta.text = "—"
	_route_tuning_meta.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_route_tuning_meta.add_theme_color_override("font_color", COLOR_STEEL_2)
	_route_tuning_meta.add_theme_font_size_override("font_size", 10)
	col.add_child(_route_tuning_meta)

	_route_units_spin = _make_route_spinbox("Units / departure", col)
	_route_interval_spin = _make_route_spinbox("Interval ticks", col)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	col.add_child(row)

	var preview := _make_hud_button("Preview Route", COLOR_CYAN)
	preview.pressed.connect(_on_route_tuning_preview_pressed)
	row.add_child(preview)

	var cancel := _make_hud_button("Cancel", COLOR_ERR)
	cancel.pressed.connect(_on_route_tuning_cancel_pressed)
	row.add_child(cancel)


func _make_route_spinbox(label_text: String, parent: VBoxContainer) -> SpinBox:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	parent.add_child(row)

	var label := Label.new()
	label.text = label_text
	label.add_theme_color_override("font_color", COLOR_STEEL)
	label.add_theme_font_size_override("font_size", 10)
	label.custom_minimum_size = Vector2(112, 0)
	row.add_child(label)

	var spin := SpinBox.new()
	spin.min_value = 1
	spin.max_value = 999
	spin.step = 1
	spin.value = 1
	spin.rounded = true
	spin.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spin)
	return spin


func _open_route_tuning_popup(train_id: String, origin_id: String, destination_id: String, cargo_id: String) -> void:
	_pending_route_tuning_train_id = train_id
	_pending_route_tuning_origin_id = origin_id
	_pending_route_tuning_dest_id = destination_id
	_pending_route_tuning_cargo = cargo_id

	var capacity := _train_capacity(train_id)
	var suggested_units: int = min(DEFAULT_TRAIN_CAPACITY, capacity)
	if _route_units_spin != null:
		_route_units_spin.min_value = 1
		_route_units_spin.max_value = max(1, capacity)
		_route_units_spin.value = suggested_units
	if _route_interval_spin != null:
		_route_interval_spin.min_value = 1
		_route_interval_spin.max_value = 240
		_route_interval_spin.value = DEFAULT_ROUTE_INTERVAL_TICKS
	if _route_tuning_meta != null:
		_route_tuning_meta.text = "%s\n%s -> %s\nCargo: %s · Train cap: %d" % [
			train_id,
			_node_display_name(origin_id),
			_node_display_name(destination_id),
			cargo_id.replace("_", " "),
			capacity,
		]

	_set_status_text("ROUTE · tune units and interval for %s -> %s" % [origin_id, destination_id], COLOR_CYAN)
	_refresh_construction_hud()
	_route_tuning_popup.position = Vector2i(get_viewport().get_mouse_position())
	_route_tuning_popup.popup()


func _on_route_tuning_preview_pressed() -> void:
	if _pending_route_tuning_train_id.is_empty() or _pending_route_tuning_origin_id.is_empty() or _pending_route_tuning_dest_id.is_empty():
		return
	var units := int(round(_route_units_spin.value)) if _route_units_spin != null else DEFAULT_TRAIN_CAPACITY
	var interval := int(round(_route_interval_spin.value)) if _route_interval_spin != null else DEFAULT_ROUTE_INTERVAL_TICKS
	var train_id := _pending_route_tuning_train_id
	var origin_id := _pending_route_tuning_origin_id
	var destination_id := _pending_route_tuning_dest_id
	var cargo_id := _pending_route_tuning_cargo
	_clear_route_tuning_state()
	_request_schedule_preview(train_id, origin_id, destination_id, cargo_id, units, interval)


func _on_route_tuning_cancel_pressed() -> void:
	_clear_route_tuning_state()
	_set_status_text("ROUTE · tuning cancelled", COLOR_STEEL)
	_refresh_construction_hud()


func _on_route_tuning_popup_hidden() -> void:
	_clear_route_tuning_state(false)


func _clear_route_tuning_state(hide_popup: bool = true) -> void:
	_pending_route_tuning_train_id = ""
	_pending_route_tuning_origin_id = ""
	_pending_route_tuning_dest_id = ""
	_pending_route_tuning_cargo = ""
	if hide_popup and _route_tuning_popup != null and _route_tuning_popup.visible:
		_route_tuning_popup.hide()


func _cargo_options_for_route(origin_id: String, destination_id: String) -> Array:
	var origin := _node_snapshot(origin_id)
	var destination := _node_snapshot(destination_id)
	var inventory: Dictionary = origin.get("inventory", {}) if typeof(origin.get("inventory")) == TYPE_DICTIONARY else {}
	var production: Dictionary = origin.get("production", {}) if typeof(origin.get("production")) == TYPE_DICTIONARY else {}
	var demand: Dictionary = destination.get("demand", {}) if typeof(destination.get("demand")) == TYPE_DICTIONARY else {}
	var combined: Dictionary = {}
	for key in inventory.keys():
		combined[str(key)] = true
	for key in production.keys():
		combined[str(key)] = true
	for key in demand.keys():
		combined[str(key)] = true
	var options: Array = combined.keys()
	options.sort()
	if options.is_empty():
		return ALL_CARGO_TYPES.duplicate()
	return options


func _unhandled_key_input(event: InputEvent) -> void:
	if not (event is InputEventKey):
		return
	var key := event as InputEventKey
	if not key.pressed:
		return
	if key.keycode == KEY_ESCAPE and not key.echo:
		_cancel_all("preview cancelled")
		get_viewport().set_input_as_handled()
		return
	var pan_delta := Vector2.ZERO
	match key.keycode:
		KEY_LEFT, KEY_A:
			pan_delta = Vector2(PAN_KEY_STEP, 0)
		KEY_RIGHT, KEY_D:
			pan_delta = Vector2(-PAN_KEY_STEP, 0)
		KEY_UP, KEY_W:
			pan_delta = Vector2(0, PAN_KEY_STEP)
		KEY_DOWN, KEY_S:
			pan_delta = Vector2(0, -PAN_KEY_STEP)
		KEY_HOME:
			if _view_offset != Vector2.ZERO or not is_equal_approx(_view_scale, 1.0):
				_view_offset = Vector2.ZERO
				_view_scale = 1.0
				if _canvas_panel != null:
					_canvas_panel.queue_redraw()
				get_viewport().set_input_as_handled()
			return
	if pan_delta != Vector2.ZERO:
		_view_offset += pan_delta
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		get_viewport().set_input_as_handled()


func _cancel_all(reason: String = "") -> void:
	var had_state := not (_pending_build_command.is_empty() and _last_preview_result.is_empty()
		and _pending_preview_kind.is_empty() and _rail_origin_id.is_empty()
		and _route_train_id.is_empty() and _selected_local_id.is_empty()
		and _pending_route_dest_id.is_empty() and _pending_route_tuning_train_id.is_empty()
		and _wire_source_endpoint.is_empty())
	_pending_build_command = {}
	_pending_preview_kind = ""
	_pending_preview_target_id = ""
	_last_preview_result = {}
	_rail_origin_id = ""
	_route_train_id = ""
	_route_origin_id = ""
	_pending_route_dest_id = ""
	_clear_route_tuning_state()
	_clear_wire_builder()
	_selected_local_kind = ""
	_selected_local_id = ""
	if _cargo_kind_popup != null and _cargo_kind_popup.visible:
		_cargo_kind_popup.hide()
	if _node_kind_popup != null and _node_kind_popup.visible:
		_node_kind_popup.hide()
	_refresh_construction_hud()
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()
	if had_state and not reason.is_empty():
		_set_status_text("%s · %s" % [_active_tool_label().to_upper(), reason], COLOR_STEEL)
	else:
		_update_status_mode_chip()


func _unhandled_input(event: InputEvent) -> void:
	if _canvas_rect.size.x <= 0 or _canvas_rect.size.y <= 0:
		return

	if event is InputEventMouseMotion:
		if _wire_dragging:
			var wire_motion := event as InputEventMouseMotion
			_wire_mouse_pos = wire_motion.position - _canvas_rect.position
			if _canvas_panel != null:
				_canvas_panel.queue_redraw()
			get_viewport().set_input_as_handled()
			return
		if _panning:
			var motion := event as InputEventMouseMotion
			_view_offset += motion.relative
			if _canvas_panel != null:
				_canvas_panel.queue_redraw()
			get_viewport().set_input_as_handled()
		return

	if not (event is InputEventMouseButton):
		return
	var mb := event as InputEventMouseButton
	var screen_pos := mb.position
	var local_pos := screen_pos - _canvas_rect.position
	var inside := local_pos.x >= 0 and local_pos.y >= 0 and local_pos.x <= _canvas_rect.size.x and local_pos.y <= _canvas_rect.size.y

	# Mouse wheel: zoom around the cursor so the point under the pointer
	# stays under the pointer after the zoom step.
	if mb.pressed and (mb.button_index == MOUSE_BUTTON_WHEEL_UP or mb.button_index == MOUSE_BUTTON_WHEEL_DOWN):
		if not inside:
			return
		var factor: float = ZOOM_STEP if mb.button_index == MOUSE_BUTTON_WHEEL_UP else 1.0 / ZOOM_STEP
		var new_scale := clampf(_view_scale * factor, ZOOM_MIN, ZOOM_MAX)
		if not is_equal_approx(new_scale, _view_scale):
			var world_pt := (local_pos - _view_offset) / _view_scale
			_view_offset = local_pos - world_pt * new_scale
			_view_scale = new_scale
			if _canvas_panel != null:
				_canvas_panel.queue_redraw()
		get_viewport().set_input_as_handled()
		return

	# Middle mouse button: universal pan regardless of tool.
	if mb.button_index == MOUSE_BUTTON_MIDDLE:
		if mb.pressed and inside:
			_panning = true
			_pan_button = MOUSE_BUTTON_MIDDLE
			get_viewport().set_input_as_handled()
		elif not mb.pressed and _panning and _pan_button == MOUSE_BUTTON_MIDDLE:
			_panning = false
			_pan_button = -1
			get_viewport().set_input_as_handled()
		return

	# Pan tool: left-button drag pans the view.
	if _active_tool == TOOL_PAN and mb.button_index == MOUSE_BUTTON_LEFT:
		if mb.pressed and inside:
			_panning = true
			_pan_button = MOUSE_BUTTON_LEFT
			get_viewport().set_input_as_handled()
		elif not mb.pressed and _panning and _pan_button == MOUSE_BUTTON_LEFT:
			_panning = false
			_pan_button = -1
			get_viewport().set_input_as_handled()
		return

	if _active_tool == TOOL_WIRE and mb.button_index == MOUSE_BUTTON_LEFT:
		if mb.pressed and inside:
			var logical_wire_pos := (local_pos - _view_offset) / _view_scale
			_handle_wire_press(local_pos, logical_wire_pos)
			get_viewport().set_input_as_handled()
		elif not mb.pressed and _wire_dragging:
			_handle_wire_release(local_pos)
			get_viewport().set_input_as_handled()
		return

	if not mb.pressed or mb.button_index != MOUSE_BUTTON_LEFT:
		return
	if not inside:
		return

	# Convert pointer to logical world coordinates so hit-testing against
	# _node_positions works at any pan + zoom level.
	var logical_pos := (local_pos - _view_offset) / _view_scale

	match _active_tool:
		TOOL_SELECT:
			_handle_select_click(logical_pos)
			get_viewport().set_input_as_handled()
		TOOL_NODE:
			_handle_place_node_click(_snap_to_grid(logical_pos))
			get_viewport().set_input_as_handled()
		TOOL_RAIL:
			_handle_rail_click(logical_pos)
			get_viewport().set_input_as_handled()
		TOOL_GATE:
			_handle_gate_click(logical_pos)
			get_viewport().set_input_as_handled()
		TOOL_TRAIN:
			_handle_train_click(logical_pos)
			get_viewport().set_input_as_handled()
		TOOL_DEMOLISH:
			_handle_demolish_click(logical_pos)
			get_viewport().set_input_as_handled()


func _next_build_id(prefix: String) -> String:
	_build_seq += 1
	var tick := int(_latest_snapshot.get("tick", 0))
	return "%s_%s_%d_%d" % [_world_id, prefix, tick, _build_seq]


func _hit_node_at(local_pos: Vector2) -> String:
	for node in _world_nodes:
		var nid := str(node.get("id", ""))
		if _node_positions.has(nid):
			if local_pos.distance_to(_node_positions[nid]) <= NODE_HIT_RADIUS:
				return nid
	return ""


func _hit_link_at(local_pos: Vector2) -> String:
	var best_id := ""
	var best_dist := LINK_HIT_DISTANCE
	for link in _world_links:
		var oid := str(link.get("origin", ""))
		var did := str(link.get("destination", ""))
		if not _node_positions.has(oid) or not _node_positions.has(did):
			continue
		var d := _dist_to_segment(local_pos, _node_positions[oid], _node_positions[did])
		if d < best_dist:
			best_dist = d
			best_id = str(link.get("id", ""))
	return best_id


func _dist_to_segment(p: Vector2, a: Vector2, b: Vector2) -> float:
	var seg := b - a
	var len_sq := seg.length_squared()
	if len_sq <= 0.0:
		return p.distance_to(a)
	var t := clampf((p - a).dot(seg) / len_sq, 0.0, 1.0)
	return p.distance_to(a + seg * t)


# --- Grid Snap ---
func _snap_to_grid(pos: Vector2) -> Vector2:
	return Vector2(
		round(pos.x / GRID_MICRO) * GRID_MICRO,
		round(pos.y / GRID_MICRO) * GRID_MICRO,
	)


# --- Place Node ---
func _handle_place_node_click(local_pos: Vector2) -> void:
	if _pending_preview_kind == "node" and not _pending_build_command.is_empty():
		_send_pending_build("Building %s..." % _pending_build_command.get("kind", "node"), COLOR_AMBER_HOT)
		return
	_clear_pending_preview()
	_pending_node_local_pos = _snap_to_grid(local_pos)
	_node_kind_popup.position = Vector2i(get_viewport().get_mouse_position())
	_node_kind_popup.popup()


func _request_node_preview(kind: String, local_pos: Vector2) -> void:
	if _world_id.is_empty():
		_set_status_text("Cannot build without a selected world.", COLOR_ERR)
		return
	var snapped_pos := _snap_to_grid(local_pos)
	var node_id := _next_build_id(kind)
	var node_name := "%s %s" % [_world_id.capitalize(), _kind_display(kind)]
	var command := {
		"type": "PreviewBuildNode",
		"node_id": node_id,
		"world_id": _world_id,
		"kind": kind,
		"name": node_name,
		"layout": _logical_to_layout(snapped_pos),
	}
	_pending_node_local_pos = snapped_pos
	_pending_preview_kind = "node"
	_pending_preview_target_id = node_id
	_pending_build_command = {}
	_last_preview_result = {}
	_set_status_text("PREVIEW · checking %s placement..." % _kind_display(kind), COLOR_AMBER_HOT)
	_refresh_construction_hud()
	GateRailBridge.send_message({
		"commands": [command],
		"ticks": 0
	})


func _kind_display(kind: String) -> String:
	return kind.replace("_", " ").capitalize()


func _send_pending_build(status_text: String, color: Color) -> bool:
	if _pending_build_command.is_empty():
		return false
	var command := _pending_build_command.duplicate(true)
	_clear_pending_preview()
	_set_status_text(status_text, color)
	GateRailBridge.send_message({
		"commands": [command],
		"ticks": 0
	})
	return true


func _clear_pending_preview() -> void:
	_pending_build_command = {}
	_pending_preview_kind = ""
	_pending_preview_target_id = ""
	_last_preview_result = {}
	_refresh_construction_hud()


func _clear_route_builder() -> void:
	_route_train_id = ""
	_route_origin_id = ""
	_clear_route_tuning_state()
	_refresh_construction_hud()


func _clear_wire_builder() -> void:
	_wire_dragging = false
	_wire_source_endpoint = {}
	_wire_mouse_pos = Vector2.ZERO



# --- Lay Rail ---
func _handle_rail_click(local_pos: Vector2) -> void:
	var nid := _hit_node_at(local_pos)
	if nid.is_empty():
		_rail_origin_id = ""
		_clear_pending_preview()
		_set_status_text("RAIL MODE · click a node to start", COLOR_AMBER_HOT)
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return
	if _pending_preview_kind == "rail" and not _pending_build_command.is_empty():
		var pending_dest := str(_pending_build_command.get("destination", ""))
		if nid == pending_dest:
			var pending_origin := str(_pending_build_command.get("origin", _rail_origin_id))
			_send_pending_build("Building rail %s -> %s..." % [pending_origin, pending_dest], COLOR_AMBER_HOT)
			_rail_origin_id = ""
			if _canvas_panel != null:
				_canvas_panel.queue_redraw()
			return
		_clear_pending_preview()
	if _rail_origin_id.is_empty():
		_rail_origin_id = nid
		_set_status_text("RAIL MODE · origin: %s · click destination" % nid, COLOR_AMBER_HOT)
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
	else:
		if nid != _rail_origin_id:
			_request_link_preview(_rail_origin_id, nid)
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()


func _request_link_preview(origin_id: String, destination_id: String) -> void:
	var link_id := _next_build_id("rail")
	_pending_preview_kind = "rail"
	_pending_preview_target_id = link_id
	_pending_build_command = {}
	_last_preview_result = {}
	_set_status_text("PREVIEW · checking rail %s -> %s..." % [origin_id, destination_id], COLOR_AMBER_HOT)
	_refresh_construction_hud()
	GateRailBridge.send_message({
		"commands": [{
			"type": "PreviewBuildLink",
			"link_id": link_id,
			"origin": origin_id,
			"destination": destination_id,
			"mode": "rail",
		}],
		"ticks": 0
	})


# --- Gate Hub ---
func _handle_gate_click(local_pos: Vector2) -> void:
	if _pending_preview_kind == "node" and not _pending_build_command.is_empty():
		_send_pending_build("Building gate hub...", COLOR_AMBER_HOT)
		return
	if _pending_preview_kind == "gate_link" and not _pending_build_command.is_empty():
		_send_pending_build("Building gate link...", COLOR_AMBER_HOT)
		return

	var nid := _hit_node_at(local_pos)
	if not nid.is_empty():
		var node := _node_snapshot(nid)
		if str(node.get("kind", "")) != "gate_hub":
			_clear_pending_preview()
			_set_status_text("GATE · click empty tile to build a gate hub, or click an existing gate hub to link", COLOR_AMBER_HOT)
			return
		_request_gate_link_preview(nid)
		return

	_clear_pending_preview()
	var snapped_pos := _snap_to_grid(local_pos)
	_pending_node_local_pos = snapped_pos
	_request_node_preview("gate_hub", snapped_pos)


func _request_gate_link_preview(origin_id: String) -> void:
	var destination := _suggest_gate_destination(origin_id)
	if destination.is_empty():
		_clear_pending_preview()
		_set_status_text("GATE LINK · no unlinked external gate hub available", COLOR_ERR)
		_refresh_construction_hud()
		return
	var destination_id := str(destination.get("id", ""))
	var link_id := _next_build_id("gate")
	_pending_preview_kind = "gate_link"
	_pending_preview_target_id = link_id
	_pending_build_command = {}
	_last_preview_result = {}
	_set_status_text("PREVIEW · checking gate link %s -> %s..." % [origin_id, destination_id], COLOR_AMBER_HOT)
	_refresh_construction_hud()
	GateRailBridge.send_message({
		"commands": [{
			"type": "PreviewBuildLink",
			"link_id": link_id,
			"origin": origin_id,
			"destination": destination_id,
			"mode": "gate",
			"travel_ticks": 1,
			"capacity_per_tick": DEFAULT_GATE_CAPACITY_PER_TICK,
			"power_required": DEFAULT_GATE_POWER_REQUIRED,
			"power_source_world_id": _world_id,
		}],
		"ticks": 0
	})


func _suggest_gate_destination(origin_id: String) -> Dictionary:
	var candidates: Array = []
	var nodes: Array = _latest_snapshot.get("nodes", []) if typeof(_latest_snapshot.get("nodes")) == TYPE_ARRAY else []
	for node in nodes:
		if typeof(node) != TYPE_DICTIONARY:
			continue
		var candidate_id := str(node.get("id", ""))
		if candidate_id == origin_id:
			continue
		if str(node.get("kind", "")) != "gate_hub":
			continue
		if str(node.get("world_id", "")) == _world_id:
			continue
		if _gate_link_between_exists(origin_id, candidate_id):
			continue
		candidates.append(node)
	candidates.sort_custom(func(a: Dictionary, b: Dictionary) -> bool:
		var a_world := str(a.get("world_id", ""))
		var b_world := str(b.get("world_id", ""))
		if a_world == b_world:
			return str(a.get("id", "")) < str(b.get("id", ""))
		return a_world < b_world
	)
	if candidates.is_empty():
		return {}
	return candidates[0]


func _gate_link_between_exists(a: String, b: String) -> bool:
	var links: Array = _latest_snapshot.get("links", []) if typeof(_latest_snapshot.get("links")) == TYPE_ARRAY else []
	for link in links:
		if typeof(link) != TYPE_DICTIONARY:
			continue
		if str(link.get("mode", "")) != "gate":
			continue
		var origin_id := str(link.get("origin", ""))
		var destination_id := str(link.get("destination", ""))
		if (origin_id == a and destination_id == b) or (origin_id == b and destination_id == a):
			return true
	return false


# --- Purchase Train ---
func _handle_train_click(local_pos: Vector2) -> void:
	var nid := _hit_node_at(local_pos)
	if nid.is_empty():
		_clear_pending_preview()
		_clear_route_builder()
		_set_status_text("TRAIN · click a node to buy train or select idle train", COLOR_CYAN)
		return

	if _pending_preview_kind == "train" and not _pending_build_command.is_empty():
		if nid == str(_pending_build_command.get("node_id", "")):
			_send_pending_build("Purchasing train at %s..." % nid, COLOR_CYAN)
			return
		_clear_pending_preview()

	if _pending_preview_kind == "schedule" and not _pending_build_command.is_empty():
		if nid == str(_pending_build_command.get("destination", "")):
			_send_pending_build("Creating schedule %s..." % _pending_build_command.get("schedule_id", "route"), COLOR_CYAN)
			_clear_route_builder()
			return
		_clear_pending_preview()

	if not _route_train_id.is_empty():
		if nid == _route_origin_id:
			_set_status_text("ROUTE · origin %s selected · click destination node" % nid, COLOR_CYAN)
			_refresh_construction_hud()
			return
		_open_cargo_kind_popup(_route_origin_id, nid)
		_set_status_text("ROUTE · pick cargo for %s -> %s" % [_route_origin_id, nid], COLOR_CYAN)
		return

	var idle_train_id := _idle_train_at_node(nid)
	if not idle_train_id.is_empty():
		_clear_pending_preview()
		_route_train_id = idle_train_id
		_route_origin_id = nid
		_set_status_text("ROUTE · %s from %s · click destination" % [idle_train_id, nid], COLOR_CYAN)
		_refresh_construction_hud()
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return

	_request_train_preview(nid)


func _request_train_preview(node_id: String) -> void:
	var train_id := _next_build_id("train")
	_pending_preview_kind = "train"
	_pending_preview_target_id = train_id
	_pending_build_command = {}
	_last_preview_result = {}
	_clear_route_builder()
	_set_status_text("PREVIEW · checking train purchase at %s..." % node_id, COLOR_CYAN)
	_refresh_construction_hud()
	GateRailBridge.send_message({
		"commands": [{
			"type": "PreviewPurchaseTrain",
			"train_id": train_id,
			"name": train_id,
			"node_id": node_id,
			"capacity": DEFAULT_TRAIN_CAPACITY,
		}],
		"ticks": 0
	})


func _request_schedule_preview(
	train_id: String,
	origin_id: String,
	destination_id: String,
	cargo_type: String = "",
	units_per_departure: int = 0,
	interval_ticks: int = 0
) -> void:
	var schedule_id := _next_build_id("schedule")
	if cargo_type.is_empty():
		cargo_type = _suggest_cargo_for_route(origin_id, destination_id)
	var units: int = units_per_departure
	if units <= 0:
		units = min(DEFAULT_TRAIN_CAPACITY, _train_capacity(train_id))
	var interval := interval_ticks
	if interval <= 0:
		interval = DEFAULT_ROUTE_INTERVAL_TICKS
	_pending_preview_kind = "schedule"
	_pending_preview_target_id = schedule_id
	_pending_build_command = {}
	_last_preview_result = {}
	_set_status_text("PREVIEW · checking route %s -> %s..." % [origin_id, destination_id], COLOR_CYAN)
	_refresh_construction_hud()
	GateRailBridge.send_message({
		"commands": [{
			"type": "PreviewCreateSchedule",
			"schedule_id": schedule_id,
			"train_id": train_id,
			"origin": origin_id,
			"destination": destination_id,
			"cargo_type": cargo_type,
			"units_per_departure": units,
			"interval_ticks": interval,
		}],
		"ticks": 0
	})


func _idle_train_at_node(node_id: String) -> String:
	var trains: Array = _latest_snapshot.get("trains", [])
	for train in trains:
		if typeof(train) != TYPE_DICTIONARY:
			continue
		if str(train.get("node_id", "")) == node_id and str(train.get("status", "")) == "idle":
			return str(train.get("id", ""))
	return ""


func _train_capacity(train_id: String) -> int:
	var trains: Array = _latest_snapshot.get("trains", [])
	for train in trains:
		if typeof(train) == TYPE_DICTIONARY and str(train.get("id", "")) == train_id:
			return max(1, int(train.get("capacity", DEFAULT_TRAIN_CAPACITY)))
	return DEFAULT_TRAIN_CAPACITY


func _node_snapshot(node_id: String) -> Dictionary:
	var nodes: Array = _latest_snapshot.get("nodes", [])
	for node in nodes:
		if typeof(node) == TYPE_DICTIONARY and str(node.get("id", "")) == node_id:
			return node
	return {}


func _suggest_cargo_for_route(origin_id: String, destination_id: String) -> String:
	var origin := _node_snapshot(origin_id)
	var destination := _node_snapshot(destination_id)
	var inventory: Dictionary = origin.get("inventory", {}) if typeof(origin.get("inventory")) == TYPE_DICTIONARY else {}
	var demand: Dictionary = destination.get("demand", {}) if typeof(destination.get("demand")) == TYPE_DICTIONARY else {}
	var keys: Array = inventory.keys()
	keys.sort()
	for key in keys:
		if demand.has(key):
			return str(key)
	if not keys.is_empty():
		return str(keys[0])
	var demand_keys: Array = demand.keys()
	demand_keys.sort()
	if not demand_keys.is_empty():
		return str(demand_keys[0])
	return "food"


# --- Select / Inspect ---
func _handle_select_click(local_pos: Vector2) -> void:
	var nid := _hit_node_at(local_pos)
	if not nid.is_empty():
		_selected_local_kind = "node"
		_selected_local_id = nid
		_set_status_text("INSPECT · node %s" % nid, COLOR_CYAN)
		_refresh_construction_hud()
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return
	var lid := _hit_link_at(local_pos)
	if not lid.is_empty():
		_selected_local_kind = "link"
		_selected_local_id = lid
		_set_status_text("INSPECT · link %s" % lid, COLOR_CYAN)
		_refresh_construction_hud()
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return
	# Empty click clears the inspection.
	_selected_local_kind = ""
	_selected_local_id = ""
	_set_status_text("SELECT · click a node or link to inspect", COLOR_STEEL_2)
	_refresh_construction_hud()
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


# --- Internal Wiring ---
func _facility_port_at(local_pos: Vector2) -> Dictionary:
	for key in _facility_port_hitboxes.keys():
		var hit: Dictionary = _facility_port_hitboxes[key]
		var rect: Rect2 = hit.get("rect", Rect2())
		if rect.has_point(local_pos):
			return hit
	return {}


func _handle_wire_press(local_pos: Vector2, logical_pos: Vector2) -> void:
	var hit := _facility_port_at(local_pos)
	if hit.is_empty():
		_handle_select_click(logical_pos)
		if _selected_local_kind == "node":
			var node := _node_snapshot(_selected_local_id)
			var facility = node.get("facility", null)
			if typeof(facility) == TYPE_DICTIONARY:
				_set_status_text("WIRE · drag an output port to an input port", COLOR_CYAN)
			else:
				_set_status_text("WIRE · selected node has no facility ports", COLOR_AMBER_HOT)
		return
	if str(hit.get("direction", "")) != "output":
		_set_status_text("WIRE · start from an output port", COLOR_AMBER_HOT)
		return
	_wire_source_endpoint = hit.duplicate(true)
	_wire_dragging = true
	_wire_mouse_pos = local_pos
	_clear_pending_preview()
	_set_status_text(
		"WIRE · %s.%s -> drag to input" % [str(hit.get("component_id", "")), str(hit.get("port_id", ""))],
		COLOR_CYAN,
	)
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


func _handle_wire_release(local_pos: Vector2) -> void:
	var source := _wire_source_endpoint.duplicate(true)
	_clear_wire_builder()
	if source.is_empty():
		return
	var hit := _facility_port_at(local_pos)
	if hit.is_empty():
		_set_status_text("WIRE · release on an input port to connect", COLOR_AMBER_HOT)
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return
	if str(hit.get("direction", "")) != "input":
		_set_status_text("WIRE · destination must be an input port", COLOR_AMBER_HOT)
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return
	if str(hit.get("node_id", "")) != str(source.get("node_id", "")):
		_set_status_text("WIRE · internal wires must stay inside one facility", COLOR_ERR)
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return
	_request_internal_connection_preview(source, hit)


func _request_internal_connection_preview(source: Dictionary, destination: Dictionary) -> void:
	var node_id := str(source.get("node_id", ""))
	if node_id.is_empty():
		_set_status_text("WIRE · no selected facility node", COLOR_ERR)
		return
	var connection_id := _next_build_id("wire")
	var command := {
		"type": "PreviewBuildInternalConnection",
		"node_id": node_id,
		"connection_id": connection_id,
		"source_component_id": str(source.get("component_id", "")),
		"source_port_id": str(source.get("port_id", "")),
		"destination_component_id": str(destination.get("component_id", "")),
		"destination_port_id": str(destination.get("port_id", "")),
	}
	_pending_preview_kind = "internal_connection"
	_pending_preview_target_id = connection_id
	_pending_build_command = {}
	_last_preview_result = {}
	_set_status_text("PREVIEW · checking internal wire...", COLOR_CYAN)
	_refresh_construction_hud()
	GateRailBridge.send_message({
		"commands": [command],
		"ticks": 0,
	})
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


# --- Demolish ---
func _handle_demolish_click(local_pos: Vector2) -> void:
	var link_id := _hit_link_at(local_pos)
	if not link_id.is_empty():
		_set_status_text("Demolishing link %s..." % link_id, COLOR_ERR)
		GateRailBridge.send_message({
			"commands": [{"type": "DemolishLink", "link_id": link_id}],
			"ticks": 0
		})
		return
	_set_status_text("DEMOLISH · click on a link to remove it", COLOR_ERR)


func _set_status_text(text: String, color: Color) -> void:
	if _statusbar_mode_label != null:
		_statusbar_mode_label.text = text
		_statusbar_mode_label.add_theme_color_override("font_color", color)


func _build_ui() -> void:
	_canvas_layer = CanvasLayer.new()
	add_child(_canvas_layer)

	_build_topbar()
	_build_toolrail()
	_build_canvas_panel()
	_build_hud()
	_build_statusbar()
	_layout_ui()


# ---------- Topbar ----------

func _build_topbar() -> void:
	_topbar = _make_panel(COLOR_PANEL_2, COLOR_HAIR)
	_canvas_layer.add_child(_topbar)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 16)
	margin.add_theme_constant_override("margin_right", 16)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	_topbar.add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 18)
	row.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	margin.add_child(row)

	var brand := HBoxContainer.new()
	brand.add_theme_constant_override("separation", 10)
	var mk := _make_brand_mark()
	brand.add_child(mk)
	var name_lbl := Label.new()
	name_lbl.text = "GATE · RAIL"
	name_lbl.add_theme_color_override("font_color", COLOR_ICE)
	name_lbl.add_theme_font_size_override("font_size", 14)
	brand.add_child(name_lbl)
	row.add_child(brand)

	_breadcrumb_label = Label.new()
	_breadcrumb_label.text = "GALAXY › SECTOR › LOCAL"
	_breadcrumb_label.add_theme_color_override("font_color", COLOR_STEEL)
	_breadcrumb_label.add_theme_font_size_override("font_size", 11)
	row.add_child(_breadcrumb_label)

	var spacer := Control.new()
	spacer.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(spacer)

	row.add_child(_make_stat_chip("Credits", "₡ —", Color(1, 1, 1), "credits"))
	row.add_child(_make_stat_chip("Power", "— / —", COLOR_OK, "power"))
	row.add_child(_make_stat_chip("Tick", "T+00000", COLOR_ICE, "tick"))

	var back := Button.new()
	back.text = "◄  Galaxy Map"
	back.add_theme_color_override("font_color", COLOR_AMBER_HOT)
	back.add_theme_color_override("font_hover_color", COLOR_ICE)
	back.add_theme_font_size_override("font_size", 12)
	var back_style := StyleBoxFlat.new()
	back_style.bg_color = Color(0.953, 0.612, 0.071, 0.10)
	back_style.border_color = COLOR_AMBER
	back_style.set_border_width_all(1)
	back_style.content_margin_left = 12
	back_style.content_margin_right = 12
	back_style.content_margin_top = 6
	back_style.content_margin_bottom = 6
	back.add_theme_stylebox_override("normal", back_style)
	back.add_theme_stylebox_override("hover", back_style)
	back.add_theme_stylebox_override("pressed", back_style)
	back.pressed.connect(_on_back_pressed)
	row.add_child(back)


func _make_brand_mark() -> Control:
	var mk := Control.new()
	mk.custom_minimum_size = Vector2(28, 28)
	mk.draw.connect(func():
		var center := Vector2(14, 14)
		mk.draw_arc(center, 13, 0, TAU, 48, COLOR_AMBER, 1.5, true)
		mk.draw_arc(center, 9, 0, TAU, 36, COLOR_STEEL, 1.0, true)
		mk.draw_arc(center, 4, 0, TAU, 24, COLOR_AMBER_HOT, 1.0, true)
	)
	return mk


func _make_stat_chip(label: String, value: String, value_color: Color, stat_id: String) -> Control:
	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 2)
	col.custom_minimum_size = Vector2(110, 0)
	var lbl := Label.new()
	lbl.text = label.to_upper()
	lbl.add_theme_color_override("font_color", COLOR_STEEL)
	lbl.add_theme_font_size_override("font_size", 9)
	col.add_child(lbl)
	var val := Label.new()
	val.text = value
	val.add_theme_color_override("font_color", value_color)
	val.add_theme_font_size_override("font_size", 14)
	col.add_child(val)
	match stat_id:
		"credits":
			_credits_value = val
		"power":
			_power_value = val
		"tick":
			_tick_value = val
	return col


func _on_back_pressed() -> void:
	var scene := SceneNav.return_scene if SceneNav.return_scene != "" else "res://scenes/main.tscn"
	get_tree().change_scene_to_file(scene)


# ---------- Tool rail ----------

func _build_toolrail() -> void:
	_toolrail = _make_panel(Color(0.071, 0.137, 0.231, 0.90), COLOR_HAIR)
	_canvas_layer.add_child(_toolrail)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 8)
	margin.add_theme_constant_override("margin_right", 8)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	_toolrail.add_child(margin)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 6)
	margin.add_child(col)

	var last_group := ""
	for tool in TOOLS:
		if last_group != "" and str(tool.get("group", "")) != last_group:
			var sep := ColorRect.new()
			sep.color = COLOR_HAIR
			sep.custom_minimum_size = Vector2(24, 1)
			col.add_child(sep)
		last_group = str(tool.get("group", ""))
		var btn := _make_tool_button(tool)
		col.add_child(btn)
		_tool_buttons[str(tool["id"])] = btn


func _make_tool_button(tool: Dictionary) -> Control:
	var id := str(tool["id"])
	var btn := Button.new()
	btn.custom_minimum_size = Vector2(44, 44)
	btn.focus_mode = Control.FOCUS_NONE
	btn.tooltip_text = "%s (%s)" % [str(tool["label"]), str(tool["key"])]
	btn.text = _tool_glyph(id)
	btn.add_theme_font_size_override("font_size", 14)
	_apply_tool_button_style(btn, id == _active_tool)
	btn.pressed.connect(_on_tool_pressed.bind(id))
	return btn


func _tool_glyph(id: String) -> String:
	match id:
		TOOL_SELECT: return "▲"
		TOOL_PAN: return "✥"
		TOOL_RAIL: return "═"
		TOOL_NODE: return "▣"
		TOOL_WIRE: return "~"
		TOOL_GATE: return "◎"
		TOOL_TRAIN: return "▬"
		TOOL_DEMOLISH: return "✕"
		TOOL_LAYERS: return "▤"
	return "·"


func _apply_tool_button_style(btn: Button, active: bool) -> void:
	var bg := StyleBoxFlat.new()
	bg.set_corner_radius_all(3)
	bg.set_content_margin_all(4)
	if active:
		bg.bg_color = Color(0.953, 0.612, 0.071, 0.18)
		bg.border_color = COLOR_AMBER
		bg.set_border_width_all(1)
		btn.add_theme_color_override("font_color", COLOR_AMBER_HOT)
	else:
		bg.bg_color = Color(0.078, 0.157, 0.259, 0.60)
		bg.border_color = COLOR_HAIR
		bg.set_border_width_all(1)
		btn.add_theme_color_override("font_color", COLOR_STEEL_2)
	btn.add_theme_stylebox_override("normal", bg)
	btn.add_theme_stylebox_override("hover", bg)
	btn.add_theme_stylebox_override("pressed", bg)
	btn.add_theme_stylebox_override("focus", bg)


func _on_tool_pressed(tool_id: String) -> void:
	# Layers is a toggle, not a mode switch
	if tool_id == TOOL_LAYERS:
		_show_zone_overlay = not _show_zone_overlay
		_apply_tool_button_style(_tool_buttons.get(TOOL_LAYERS), _show_zone_overlay)
		var lbl: String = "LAYERS · overlays %s" % ("ON" if _show_zone_overlay else "OFF")
		_set_status_text(lbl, COLOR_CYAN)
		_update_overlay_summary()
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return

	_active_tool = tool_id
	_rail_origin_id = ""
	_pending_route_dest_id = ""
	if tool_id != TOOL_SELECT and tool_id != TOOL_WIRE:
		_selected_local_kind = ""
		_selected_local_id = ""
	if _cargo_kind_popup != null and _cargo_kind_popup.visible:
		_cargo_kind_popup.hide()
	_clear_route_tuning_state()
	_clear_pending_preview()
	_clear_route_builder()
	_clear_wire_builder()
	for key in _tool_buttons.keys():
		_apply_tool_button_style(_tool_buttons[key], key == tool_id)
	_update_status_mode_chip()
	_refresh_construction_hud()
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


# ---------- Canvas ----------

func _build_canvas_panel() -> void:
	_canvas_panel = Control.new()
	_canvas_panel.mouse_filter = Control.MOUSE_FILTER_IGNORE
	_canvas_panel.clip_contents = true
	_canvas_panel.draw.connect(_on_canvas_draw)
	_canvas_layer.add_child(_canvas_panel)

	_region_label = Label.new()
	_region_label.text = "LOCAL REGION · 01 · —"
	_region_label.add_theme_color_override("font_color", COLOR_ICE)
	_region_label.add_theme_font_size_override("font_size", 18)
	_canvas_panel.add_child(_region_label)

	_region_meta = Label.new()
	_region_meta.text = "BIOME: — · GRAV: — · GRID: 24 km²"
	_region_meta.add_theme_color_override("font_color", COLOR_STEEL_2)
	_region_meta.add_theme_font_size_override("font_size", 11)
	_canvas_panel.add_child(_region_meta)


func _on_canvas_draw() -> void:
	var size := _canvas_panel.size
	if size.x <= 0 or size.y <= 0:
		return
	var bg_rect := Rect2(Vector2.ZERO, size)
	_canvas_panel.draw_rect(bg_rect, COLOR_BG_0, true)

	# World content (terrain, zones, grid, links, nodes, trains) pans + zooms
	# with the camera. Viewport chrome (corner brackets, compass, scale bar,
	# region label) stays fixed and is drawn after.
	_canvas_panel.draw_set_transform(_view_offset, 0.0, Vector2.ONE * _view_scale)
	_draw_terrain(size)
	_draw_grid(size)
	_draw_links_and_nodes(size)
	_draw_logistics_overlays(size)
	_draw_trains(size)
	_draw_build_preview(size)
	_draw_snap_cursor(size)
	_canvas_panel.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)

	_draw_facility_drill_in(size)
	_draw_corner_brackets(size)
	_draw_compass(size)
	_draw_scalebar(size)


func _process(_delta: float) -> void:
	# Continuously redraw only when trains are in transit for smooth animation
	if _canvas_panel == null:
		return
	var trains: Array = _latest_snapshot.get("trains", [])
	for t in trains:
		if typeof(t) == TYPE_DICTIONARY and str(t.get("status", "")) == "in_transit":
			_canvas_panel.queue_redraw()
			return


# ---- Slice A: Terrain ----

func _biome_palette(specialization: String, tier: String) -> Array:
	# Returns [base_color, accent_color, zone_colors{farm,industry,water,hazard}]
	match specialization:
		"mineral_rich":
			return [Color(0.12, 0.10, 0.08), Color(0.22, 0.16, 0.10),
				{"farm": Color(0.25, 0.20, 0.12, 0.4), "industry": Color(0.55, 0.42, 0.28, 0.5),
				 "water": Color(0.08, 0.15, 0.30, 0.5), "hazard": Color(0.8, 0.3, 0.05, 0.55)}]
		"agricultural":
			return [Color(0.10, 0.18, 0.08), Color(0.16, 0.28, 0.10),
				{"farm": Color(0.20, 0.55, 0.12, 0.45), "industry": Color(0.35, 0.30, 0.15, 0.4),
				 "water": Color(0.10, 0.28, 0.55, 0.50), "hazard": Color(0.7, 0.25, 0.05, 0.4)}]
		"survey_outpost":
			return [Color(0.12, 0.16, 0.22), Color(0.18, 0.22, 0.32),
				{"farm": Color(0.30, 0.45, 0.55, 0.35), "industry": Color(0.25, 0.32, 0.40, 0.45),
				 "water": Color(0.08, 0.20, 0.45, 0.55), "hazard": Color(0.75, 0.85, 0.95, 0.55)}]
		"industrial", "max_tier", "core":
			return [Color(0.10, 0.10, 0.12), Color(0.16, 0.16, 0.20),
				{"farm": Color(0.20, 0.35, 0.18, 0.3), "industry": Color(0.42, 0.42, 0.48, 0.55),
				 "water": Color(0.08, 0.18, 0.40, 0.50), "hazard": Color(0.70, 0.20, 0.08, 0.45)}]
		_:  # frontier / default
			return [Color(0.08, 0.14, 0.12), Color(0.12, 0.20, 0.18),
				{"farm": Color(0.18, 0.45, 0.22, 0.38), "industry": Color(0.30, 0.30, 0.28, 0.42),
				 "water": Color(0.10, 0.22, 0.48, 0.52), "hazard": Color(0.75, 0.35, 0.08, 0.45)}]


func _generate_terrain(canvas_size: Vector2) -> void:
	if _world_id == _last_terrain_world_id and not _terrain_patches.is_empty():
		return
	_last_terrain_world_id = _world_id
	_terrain_patches.clear()
	_terrain_zones.clear()

	var spec := str(_selected_world.get("specialization", "") if _selected_world.size() > 0 else "")
	var tier := str(_selected_world.get("tier_name", "frontier") if _selected_world.size() > 0 else "frontier")
	var palette := _biome_palette(spec, tier)
	var base_col: Color = palette[0]
	var accent_col: Color = palette[1]
	var zone_cols: Dictionary = palette[2]

	# Seed RNG from world id hash
	var rng := RandomNumberGenerator.new()
	var seed_val: int = 0
	for ch in _world_id:
		seed_val = (seed_val * 31 + ch.unicode_at(0)) & 0x7FFFFFFF
	if seed_val == 0:
		seed_val = 42
	rng.seed = seed_val

	# Cover an extended area around the canvas so pan + zoom-out keeps the
	# colored terrain in view. Origin shifts negative so the canvas sits
	# roughly in the middle of the painted region.
	const TERRAIN_OVERSCAN := 1.0
	var origin := -canvas_size * TERRAIN_OVERSCAN
	var terrain_size := canvas_size * (1.0 + 2.0 * TERRAIN_OVERSCAN)

	# Voronoi approximation: place seed centroids then fill grid cells
	const CELL := 40.0
	var num_seeds: int = 14 * int(round(1.0 + 2.0 * TERRAIN_OVERSCAN) * round(1.0 + 2.0 * TERRAIN_OVERSCAN))
	num_seeds = max(48, num_seeds)
	var seeds_pos: Array = []
	var seeds_col: Array = []
	for i in range(num_seeds):
		seeds_pos.append(Vector2(rng.randf_range(origin.x, origin.x + terrain_size.x), rng.randf_range(origin.y, origin.y + terrain_size.y)))
		var t := rng.randf()
		seeds_col.append(base_col.lerp(accent_col, t))

	var cx := origin.x
	while cx < origin.x + terrain_size.x:
		var cy := origin.y
		while cy < origin.y + terrain_size.y:
			var cell_center := Vector2(cx + CELL * 0.5, cy + CELL * 0.5)
			var best_dist := INF
			var best_col := base_col
			for si in range(num_seeds):
				var d := cell_center.distance_to(seeds_pos[si])
				if d < best_dist:
					best_dist = d
					best_col = seeds_col[si]
			_terrain_patches.append({"pos": Vector2(cx, cy), "size": Vector2(CELL, CELL), "color": best_col})
			cy += CELL
		cx += CELL

	# Generate zone blobs spread across the extended terrain area.
	var zone_types := ["water", "farm", "industry", "hazard", "farm", "water", "industry", "farm", "hazard", "water"]
	for zt in zone_types:
		var zpos := Vector2(
			rng.randf_range(origin.x + 80, origin.x + terrain_size.x - 80),
			rng.randf_range(origin.y + 80, origin.y + terrain_size.y - 80),
		)
		var zrad := rng.randf_range(60, 160)
		_terrain_zones.append({"pos": zpos, "radius": zrad, "type": zt, "color": zone_cols.get(zt, Color.TRANSPARENT)})


func _draw_terrain(size: Vector2) -> void:
	if _terrain_patches.is_empty():
		_generate_terrain(size)

	for patch in _terrain_patches:
		_canvas_panel.draw_rect(Rect2(patch["pos"], patch["size"]), patch["color"], true)

	# Subtle wash on top for depth — span the extended terrain bounds so the
	# wash matches wherever terrain patches are visible after pan + zoom.
	if not _terrain_patches.is_empty():
		var first: Dictionary = _terrain_patches[0]
		var wash_min: Vector2 = first["pos"]
		var wash_max: Vector2 = wash_min + first["size"]
		for patch in _terrain_patches:
			var p: Vector2 = patch["pos"]
			var s: Vector2 = patch["size"]
			wash_min.x = min(wash_min.x, p.x)
			wash_min.y = min(wash_min.y, p.y)
			wash_max.x = max(wash_max.x, p.x + s.x)
			wash_max.y = max(wash_max.y, p.y + s.y)
		_canvas_panel.draw_rect(Rect2(wash_min, wash_max - wash_min), Color(0, 0, 0, 0.28), true)
	else:
		_canvas_panel.draw_rect(Rect2(Vector2.ZERO, size), Color(0, 0, 0, 0.28), true)

	if _show_zone_overlay:
		var font := ThemeDB.fallback_font
		var zone_labels := {"farm": "FARM", "industry": "INDUSTRY", "water": "WATER", "hazard": "HAZARD"}
		for zone in _terrain_zones:
			var col: Color = zone["color"]
			var r: float = float(zone["radius"])
			var pos: Vector2 = zone["pos"]
			_canvas_panel.draw_circle(pos, r, Color(col.r, col.g, col.b, 0.30))
			_canvas_panel.draw_arc(pos, r, 0.0, TAU, 48, Color(col.r, col.g, col.b, 0.65), 1.5, true)
			var lbl: String = zone_labels.get(zone["type"], "")
			if not lbl.is_empty():
				_canvas_panel.draw_string(font, pos + Vector2(-20, 4), lbl, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, Color(col.r, col.g, col.b, 0.9))


# ---- Slice B: Track Art ----

func _draw_track_segment(a: Vector2, b: Vector2, mode: String) -> void:
	var dir := (b - a).normalized()
	if dir == Vector2.ZERO:
		return
	var perp := Vector2(-dir.y, dir.x)
	var length := a.distance_to(b)

	if mode == "gate":
		# Glowing amber gate corridor
		var t_ms: float = float(Time.get_ticks_msec()) / 1000.0
		var pulse: float = 0.5 + 0.5 * sin(t_ms * 2.5)
		_canvas_panel.draw_line(a, b, Color(0.95, 0.61, 0.07, 0.18 + 0.12 * pulse), 18.0)
		_canvas_panel.draw_line(a, b, Color(0.95, 0.61, 0.07, 0.55), 3.0)
		_canvas_panel.draw_line(a + perp * 5, b + perp * 5, Color(1.0, 0.8, 0.3, 0.7), 2.0)
		_canvas_panel.draw_line(a - perp * 5, b - perp * 5, Color(1.0, 0.8, 0.3, 0.7), 2.0)
		# Energy pulse dot
		var pulse_t := fmod(t_ms * 0.5, 1.0)
		var pulse_pos := a.lerp(b, pulse_t)
		_canvas_panel.draw_circle(pulse_pos, 4.0 + 2.0 * pulse, Color(1.0, 0.9, 0.5, 0.8))
		return

	# Sleepers (cross-ties) first so rails draw on top
	var sleeper_spacing := 18.0
	var num_sleepers: int = int(length / sleeper_spacing)
	for i in range(num_sleepers + 1):
		var t: float = float(i) / float(max(1, num_sleepers))
		var sp := a.lerp(b, t)
		var s0 := sp - perp * 7.0
		var s1 := sp + perp * 7.0
		_canvas_panel.draw_line(s0, s1, Color(0.28, 0.20, 0.12, 0.90), 3.5)

	# Left and right rails
	var rail_col := Color(0.58, 0.64, 0.66, 0.95)
	_canvas_panel.draw_line(a + perp * 4, b + perp * 4, rail_col, 2.0)
	_canvas_panel.draw_line(a - perp * 4, b - perp * 4, rail_col, 2.0)
	# Rail highlight
	_canvas_panel.draw_line(a + perp * 4, b + perp * 4, Color(0.8, 0.85, 0.88, 0.35), 1.0)
	_canvas_panel.draw_line(a - perp * 4, b - perp * 4, Color(0.8, 0.85, 0.88, 0.35), 1.0)


# ---- Slice C: Trains on Track ----

func _draw_trains(_size: Vector2) -> void:
	var trains: Array = _latest_snapshot.get("trains", [])
	var all_nodes: Array = _latest_snapshot.get("nodes", [])
	var all_links: Array = _latest_snapshot.get("links", [])

	# Build node→world map
	var node_world: Dictionary = {}
	for n in all_nodes:
		if typeof(n) == TYPE_DICTIONARY:
			node_world[str(n.get("id", ""))] = str(n.get("world_id", ""))

	# Build link lookup
	var link_by_id: Dictionary = {}
	for lnk in all_links:
		if typeof(lnk) == TYPE_DICTIONARY:
			link_by_id[str(lnk.get("id", ""))] = lnk

	for train in trains:
		if typeof(train) != TYPE_DICTIONARY:
			continue
		var status := str(train.get("status", "idle"))
		var train_node := str(train.get("node_id", ""))

		# Only draw if train is on our world
		var train_world: String = str(node_world.get(train_node, ""))
		if train_world != _world_id and status != "in_transit":
			continue

		var draw_pos := Vector2.ZERO
		var draw_dir := Vector2.RIGHT
		var found := false

		if status == "in_transit":
			var route_nodes: Array = train.get("route_node_ids", [])
			var route_links: Array = train.get("route_link_ids", [])
			var total_ticks: int = 0
			var link_ticks: Array = []
			for lid in route_links:
				var ldata: Dictionary = link_by_id.get(str(lid), {})
				var lt: int = max(1, int(ldata.get("travel_ticks", 1)))
				link_ticks.append(lt)
				total_ticks += lt
			var remaining: int = int(train.get("remaining_ticks", 0))
			var elapsed: int = clampi(total_ticks - remaining, 0, total_ticks)
			var traversed: int = 0
			for si in range(min(route_links.size(), route_nodes.size() - 1)):
				var from_id := str(route_nodes[si])
				var to_id := str(route_nodes[si + 1])
				var seg_ticks: int = int(link_ticks[si])
				if node_world.get(from_id, "") != _world_id and node_world.get(to_id, "") != _world_id:
					traversed += seg_ticks
					continue
				if elapsed <= traversed + seg_ticks:
					if _node_positions.has(from_id) and _node_positions.has(to_id):
						var progress: float = float(elapsed - traversed) / float(max(1, seg_ticks))
						var fp: Vector2 = _node_positions[from_id]
						var tp: Vector2 = _node_positions[to_id]
						draw_pos = fp.lerp(tp, progress)
						draw_dir = (tp - fp).normalized()
						found = true
					break
				traversed += seg_ticks

		if not found:
			if _node_positions.has(train_node):
				draw_pos = _node_positions[train_node]
			else:
				continue

		_draw_train_glyph(draw_pos, draw_dir, status)


func _draw_train_glyph(pos: Vector2, direction: Vector2, status: String) -> void:
	var angle := direction.angle()
	var body_col: Color
	match status:
		"in_transit": body_col = COLOR_AMBER
		"blocked": body_col = COLOR_ERR
		_: body_col = COLOR_STEEL

	# Draw rotated locomotive body using a transform
	var xf := Transform2D(angle, pos)
	# Body rectangle (12×6)
	var body := PackedVector2Array([
		xf * Vector2(-7, -3), xf * Vector2(7, -3),
		xf * Vector2(7, 3), xf * Vector2(-7, 3)
	])
	var dark_col := Color(body_col.r * 0.4, body_col.g * 0.4, body_col.b * 0.4, 1.0)
	var cols := PackedColorArray([body_col, body_col, body_col, body_col])
	_canvas_panel.draw_polygon(body, cols)
	# Cab (front circle)
	var cab_center := xf * Vector2(5, 0)
	_canvas_panel.draw_circle(cab_center, 4.0, dark_col)
	_canvas_panel.draw_arc(cab_center, 4.0, 0.0, TAU, 16, body_col, 1.0, true)
	# Outline
	for i in range(4):
		_canvas_panel.draw_line(body[i], body[(i + 1) % 4], dark_col, 1.0)


func _draw_grid(size: Vector2) -> void:
	var micro_color := Color(COLOR_STEEL.r, COLOR_STEEL.g, COLOR_STEEL.b, 0.06)
	var major_color := Color(COLOR_STEEL.r, COLOR_STEEL.g, COLOR_STEEL.b, 0.11)
	# Back-project the viewport rect into logical space so grid lines stay
	# aligned to world coords through pan + zoom.
	var inv_scale: float = 1.0 / max(0.001, _view_scale)
	var min_x: float = -_view_offset.x * inv_scale
	var max_x: float = (size.x - _view_offset.x) * inv_scale
	var min_y: float = -_view_offset.y * inv_scale
	var max_y: float = (size.y - _view_offset.y) * inv_scale
	var x: float = floor(min_x / GRID_MICRO) * GRID_MICRO
	while x < max_x:
		_canvas_panel.draw_line(Vector2(x, min_y), Vector2(x, max_y), micro_color, 1.0)
		x += GRID_MICRO
	var y: float = floor(min_y / GRID_MICRO) * GRID_MICRO
	while y < max_y:
		_canvas_panel.draw_line(Vector2(min_x, y), Vector2(max_x, y), micro_color, 1.0)
		y += GRID_MICRO
	x = floor(min_x / GRID_MAJOR) * GRID_MAJOR
	while x < max_x:
		_canvas_panel.draw_line(Vector2(x, min_y), Vector2(x, max_y), major_color, 1.0)
		x += GRID_MAJOR
	y = floor(min_y / GRID_MAJOR) * GRID_MAJOR
	while y < max_y:
		_canvas_panel.draw_line(Vector2(min_x, y), Vector2(max_x, y), major_color, 1.0)
		y += GRID_MAJOR


func _facility_endpoint_key(node_id: String, component_id: String, port_id: String) -> String:
	return "%s|%s|%s" % [node_id, component_id, port_id]


func _port_label(port: Dictionary) -> String:
	var cargo := str(port.get("cargo", "all"))
	if cargo == "<null>" or cargo == "null" or cargo.is_empty():
		cargo = "all"
	cargo = cargo.replace("_", " ")
	var rate := int(port.get("rate", 0))
	var label := cargo
	if rate > 0:
		label += " /%d" % rate
	var inventory: Dictionary = port.get("inventory", {}) if typeof(port.get("inventory")) == TYPE_DICTIONARY else {}
	if not inventory.is_empty():
		label += " [%s]" % _format_top_cargo(inventory, 1)
	return label


func _draw_facility_drill_in(size: Vector2) -> void:
	_facility_component_boxes.clear()
	_facility_port_hitboxes.clear()
	_facility_port_centers.clear()
	if _selected_local_kind != "node" or _selected_local_id.is_empty():
		return
	var node := _node_snapshot(_selected_local_id)
	if node.is_empty():
		return
	var facility: Dictionary = node.get("facility", {}) if typeof(node.get("facility")) == TYPE_DICTIONARY else {}
	if facility.is_empty():
		return
	var components: Array = facility.get("components", []) if typeof(facility.get("components")) == TYPE_ARRAY else []
	if components.is_empty():
		return

	var panel_w: float = min(640.0, max(280.0, size.x - 44.0))
	var panel_h: float = min(300.0, max(170.0, size.y * 0.42))
	var panel_pos := Vector2(22.0, max(84.0, size.y - panel_h - 18.0))
	var panel_rect := Rect2(panel_pos, Vector2(panel_w, panel_h))
	_canvas_panel.draw_rect(panel_rect, Color(COLOR_PANEL_2.r, COLOR_PANEL_2.g, COLOR_PANEL_2.b, 0.94), true)
	_canvas_panel.draw_rect(panel_rect, COLOR_HAIR_2, false, 1.0)

	var font := ThemeDB.fallback_font
	_canvas_panel.draw_string(
		font,
		panel_pos + Vector2(14, 22),
		"FACILITY DRILL-IN · %s" % str(node.get("name", _selected_local_id)).to_upper(),
		HORIZONTAL_ALIGNMENT_LEFT,
		panel_w - 28,
		11,
		COLOR_STEEL_2,
	)
	var sub := "select Wire Ports, then drag OUT to IN"
	if _active_tool == TOOL_WIRE:
		sub = "drag OUT port to IN port · backend preview required"
	_canvas_panel.draw_string(font, panel_pos + Vector2(panel_w - 260, 22), sub, HORIZONTAL_ALIGNMENT_RIGHT, 246, 10, COLOR_STEEL)

	var columns: int = max(1, min(3, int(floor((panel_w - 32.0) / 170.0))))
	var gap := 12.0
	var box_w: float = (panel_w - 32.0 - gap * float(columns - 1)) / float(columns)
	var box_h := 88.0
	var blocked: Array = node.get("facility_blocked", []) if typeof(node.get("facility_blocked")) == TYPE_ARRAY else []

	for i in components.size():
		var comp = components[i]
		if typeof(comp) != TYPE_DICTIONARY:
			continue
		var component: Dictionary = comp
		var component_id := str(component.get("id", ""))
		var col := i % columns
		var row := int(i / columns)
		var box_pos := panel_pos + Vector2(16.0 + float(col) * (box_w + gap), 42.0 + float(row) * (box_h + gap))
		var box_rect := Rect2(box_pos, Vector2(box_w, box_h))
		_facility_component_boxes[component_id] = box_rect
		var ports: Array = component.get("ports", []) if typeof(component.get("ports")) == TYPE_ARRAY else []
		var input_index := 0
		var output_index := 0
		for item in ports:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var port: Dictionary = item
			var port_id := str(port.get("id", ""))
			var direction := str(port.get("direction", ""))
			var port_y := box_pos.y + 34.0
			var port_x := box_pos.x
			if direction == "output":
				port_y += float(output_index) * 16.0
				port_x = box_pos.x + box_w
				output_index += 1
			else:
				port_y += float(input_index) * 16.0
				input_index += 1
			var center := Vector2(port_x, port_y)
			var key := _facility_endpoint_key(_selected_local_id, component_id, port_id)
			_facility_port_centers[key] = center
			_facility_port_hitboxes[key] = {
				"rect": Rect2(center - Vector2(8, 8), Vector2(16, 16)),
				"node_id": _selected_local_id,
				"component_id": component_id,
				"port_id": port_id,
				"direction": direction,
				"cargo": port.get("cargo", null),
			}

	var connections: Array = facility.get("connections", []) if typeof(facility.get("connections")) == TYPE_ARRAY else []
	for item in connections:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var connection: Dictionary = item
		var source_key := _facility_endpoint_key(
			_selected_local_id,
			str(connection.get("source_component_id", "")),
			str(connection.get("source_port_id", "")),
		)
		var destination_key := _facility_endpoint_key(
			_selected_local_id,
			str(connection.get("destination_component_id", "")),
			str(connection.get("destination_port_id", "")),
		)
		if not _facility_port_centers.has(source_key) or not _facility_port_centers.has(destination_key):
			continue
		var a: Vector2 = _facility_port_centers[source_key]
		var b: Vector2 = _facility_port_centers[destination_key]
		var mid_x := (a.x + b.x) * 0.5
		var points := PackedVector2Array([a, Vector2(mid_x, a.y), Vector2(mid_x, b.y), b])
		_canvas_panel.draw_polyline(points, Color(COLOR_CYAN.r, COLOR_CYAN.g, COLOR_CYAN.b, 0.72), 2.0)

	if _wire_dragging and not _wire_source_endpoint.is_empty():
		var source_key := _facility_endpoint_key(
			str(_wire_source_endpoint.get("node_id", "")),
			str(_wire_source_endpoint.get("component_id", "")),
			str(_wire_source_endpoint.get("port_id", "")),
		)
		if _facility_port_centers.has(source_key):
			var source_center: Vector2 = _facility_port_centers[source_key]
			_canvas_panel.draw_line(source_center, _wire_mouse_pos, COLOR_AMBER_HOT, 2.0)
			_canvas_panel.draw_circle(_wire_mouse_pos, 4.0, COLOR_AMBER_HOT)

	for i in components.size():
		var comp = components[i]
		if typeof(comp) != TYPE_DICTIONARY:
			continue
		var component: Dictionary = comp
		var component_id := str(component.get("id", ""))
		if not _facility_component_boxes.has(component_id):
			continue
		var box_rect: Rect2 = _facility_component_boxes[component_id]
		var is_blocked := component_id in blocked
		var border := COLOR_ERR if is_blocked else COLOR_HAIR_2
		_canvas_panel.draw_rect(box_rect, Color(COLOR_BG_1.r, COLOR_BG_1.g, COLOR_BG_1.b, 0.92), true)
		_canvas_panel.draw_rect(box_rect, border, false, 1.2)
		_canvas_panel.draw_string(font, box_rect.position + Vector2(10, 18), str(component.get("kind", "component")).replace("_", " ").to_upper(), HORIZONTAL_ALIGNMENT_LEFT, box_w - 20, 10, COLOR_STEEL_2)
		_canvas_panel.draw_string(font, box_rect.position + Vector2(10, 34), component_id, HORIZONTAL_ALIGNMENT_LEFT, box_w - 20, 11, COLOR_ICE)
		if is_blocked:
			_canvas_panel.draw_string(font, box_rect.position + Vector2(10, box_h - 10), "BLOCKED", HORIZONTAL_ALIGNMENT_LEFT, box_w - 20, 9, COLOR_ERR)
		var ports: Array = component.get("ports", []) if typeof(component.get("ports")) == TYPE_ARRAY else []
		for item in ports:
			if typeof(item) != TYPE_DICTIONARY:
				continue
			var port: Dictionary = item
			var key := _facility_endpoint_key(_selected_local_id, component_id, str(port.get("id", "")))
			if not _facility_port_centers.has(key):
				continue
			var center: Vector2 = _facility_port_centers[key]
			var direction := str(port.get("direction", ""))
			var port_color := COLOR_CYAN if direction == "output" else COLOR_AMBER_HOT
			_canvas_panel.draw_circle(center, 5.0, port_color)
			_canvas_panel.draw_arc(center, 5.0, 0.0, TAU, 16, COLOR_BG_0, 1.0, true)
			var label_pos := center + Vector2(8, 3)
			var label_width := box_w * 0.5 - 14.0
			if direction == "input":
				label_pos = center + Vector2(-label_width - 8, 3)
			_canvas_panel.draw_string(font, label_pos, _port_label(port), HORIZONTAL_ALIGNMENT_LEFT, label_width, 9, COLOR_STEEL)


func _draw_corner_brackets(size: Vector2) -> void:
	var b := 22.0
	var c := COLOR_HAIR_2
	var w := 1.5
	# top-left
	_canvas_panel.draw_line(Vector2(0, 0), Vector2(b, 0), c, w)
	_canvas_panel.draw_line(Vector2(0, 0), Vector2(0, b), c, w)
	# top-right
	_canvas_panel.draw_line(Vector2(size.x, 0), Vector2(size.x - b, 0), c, w)
	_canvas_panel.draw_line(Vector2(size.x, 0), Vector2(size.x, b), c, w)
	# bottom-left
	_canvas_panel.draw_line(Vector2(0, size.y), Vector2(b, size.y), c, w)
	_canvas_panel.draw_line(Vector2(0, size.y), Vector2(0, size.y - b), c, w)
	# bottom-right
	_canvas_panel.draw_line(Vector2(size.x, size.y), Vector2(size.x - b, size.y), c, w)
	_canvas_panel.draw_line(Vector2(size.x, size.y), Vector2(size.x, size.y - b), c, w)


func _draw_compass(size: Vector2) -> void:
	var c := Vector2(size.x - 56, 42)
	_canvas_panel.draw_arc(c, 28, 0, TAU, 48, COLOR_HAIR_2, 1.0, true)
	var font := ThemeDB.fallback_font
	var fs := 10
	_canvas_panel.draw_string(font, c + Vector2(-4, -20), "N", HORIZONTAL_ALIGNMENT_LEFT, -1, fs, COLOR_AMBER_HOT)
	_canvas_panel.draw_string(font, c + Vector2(20, 4), "E", HORIZONTAL_ALIGNMENT_LEFT, -1, fs, COLOR_STEEL)
	_canvas_panel.draw_string(font, c + Vector2(-4, 26), "S", HORIZONTAL_ALIGNMENT_LEFT, -1, fs, COLOR_STEEL)
	_canvas_panel.draw_string(font, c + Vector2(-26, 4), "W", HORIZONTAL_ALIGNMENT_LEFT, -1, fs, COLOR_STEEL)
	_canvas_panel.draw_line(c, c + Vector2(0, -22), COLOR_AMBER_HOT, 2.0)


func _draw_scalebar(size: Vector2) -> void:
	var origin := Vector2(24, size.y - 28)
	var font := ThemeDB.fallback_font
	_canvas_panel.draw_string(font, origin + Vector2(-6, 6), "0", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, COLOR_STEEL)
	var bar_rect := Rect2(origin + Vector2(8, 0), Vector2(120, 8))
	_canvas_panel.draw_rect(bar_rect, Color(0.118, 0.227, 0.357, 0.3), true)
	_canvas_panel.draw_rect(bar_rect, COLOR_HAIR_2, false, 1.0)
	var seg_w := 15
	for i in range(0, 120, 30):
		_canvas_panel.draw_rect(Rect2(origin + Vector2(8 + i, 0), Vector2(seg_w, 8)), COLOR_STEEL_2, true)
	_canvas_panel.draw_string(font, origin + Vector2(140, 6), "2.4 KM", HORIZONTAL_ALIGNMENT_LEFT, -1, 10, COLOR_STEEL)


func _draw_links_and_nodes(size: Vector2) -> void:
	# Rebuild positions each draw so it reacts to resize.
	_rebuild_node_positions(size)

	# Links — use track art
	for link in _world_links:
		var origin_id := str(link.get("origin", ""))
		var dest_id := str(link.get("destination", ""))
		if not _node_positions.has(origin_id) or not _node_positions.has(dest_id):
			continue
		var a: Vector2 = _node_positions[origin_id]
		var b: Vector2 = _node_positions[dest_id]
		var mode := str(link.get("mode", "rail"))
		_draw_track_segment(a, b, mode)

	# Nodes
	var font := ThemeDB.fallback_font
	for node in _world_nodes:
		var node_id := str(node.get("id", ""))
		if not _node_positions.has(node_id):
			continue
		var pos: Vector2 = _node_positions[node_id]
		var kind := str(node.get("kind", "depot"))
		_draw_node_glyph(pos, kind, node_id == _gate_hub_node_id)
		var label := str(node.get("name", node_id)).to_upper()
		var kind_lbl := kind.to_upper().replace("_", " ")
		_canvas_panel.draw_string(font, pos + Vector2(-50, 44), label, HORIZONTAL_ALIGNMENT_CENTER, 100, 11, COLOR_ICE)
		_canvas_panel.draw_string(font, pos + Vector2(-50, 58), kind_lbl, HORIZONTAL_ALIGNMENT_CENTER, 100, 10, COLOR_STEEL)
		if node.get("construction_project_id") != null and str(node.get("construction_project_id")) != "":
			_canvas_panel.draw_string(font, pos + Vector2(-60, -32), "UNDER CONSTRUCTION", HORIZONTAL_ALIGNMENT_CENTER, 120, 10, COLOR_AMBER_HOT)


func _draw_logistics_overlays(_size: Vector2) -> void:
	if not _show_zone_overlay:
		return
	var font := ThemeDB.fallback_font
	for node in _world_nodes:
		if typeof(node) != TYPE_DICTIONARY:
			continue
		var node_id := str(node.get("id", ""))
		if not _node_positions.has(node_id):
			continue
		var pos: Vector2 = _node_positions[node_id]
		var transfer_pressure := float(node.get("transfer_pressure", 0.0))
		var saturation_streak := int(node.get("saturation_streak", 0))
		_draw_transfer_overlay(pos, transfer_pressure, saturation_streak)
		_draw_inventory_overlay(pos, _node_storage_pressure(node))

		var badges := _node_overlay_badges(node)
		for i in range(badges.size()):
			var badge: Dictionary = badges[i]
			var offset := Vector2(-38 + float(i) * 19.0, -38)
			_draw_overlay_badge(pos + offset, str(badge.get("label", "")), badge.get("color", COLOR_STEEL))

		var note := _node_overlay_note(node)
		if not note.is_empty():
			var note_pos := pos + Vector2(34, -30)
			var note_color := _node_overlay_note_color(node)
			var note_rect := Rect2(note_pos + Vector2(-5, -14), Vector2(112, 20))
			_canvas_panel.draw_rect(note_rect, Color(0.020, 0.043, 0.071, 0.78), true)
			_canvas_panel.draw_rect(note_rect, Color(note_color.r, note_color.g, note_color.b, 0.48), false, 1.0)
			_canvas_panel.draw_string(font, note_pos, note, HORIZONTAL_ALIGNMENT_LEFT, 104, 10, note_color)


func _draw_transfer_overlay(pos: Vector2, pressure: float, saturation_streak: int) -> void:
	if pressure <= 0.0 and saturation_streak <= 0:
		return
	var color := _transfer_pressure_color(pressure, saturation_streak)
	var radius := 35.0 + clampf(pressure, 0.0, 1.0) * 5.0
	var width := 1.4 + clampf(pressure, 0.0, 1.0) * 2.6
	if pressure >= 0.95:
		_canvas_panel.draw_circle(pos, radius + 2.0, Color(color.r, color.g, color.b, 0.10))
	_canvas_panel.draw_arc(pos, radius, 0.0, TAU, 64, Color(color.r, color.g, color.b, 0.88), width, true)


func _draw_inventory_overlay(pos: Vector2, storage_pressure: float) -> void:
	var width := 54.0
	var height := 6.0
	var origin := pos + Vector2(-width * 0.5, 29.0)
	var pct := clampf(storage_pressure, 0.0, 1.0)
	var color := COLOR_CYAN
	if pct >= 0.90:
		color = COLOR_ERR
	elif pct >= 0.70:
		color = COLOR_AMBER_HOT
	_canvas_panel.draw_rect(Rect2(origin, Vector2(width, height)), Color(0.020, 0.043, 0.071, 0.74), true)
	_canvas_panel.draw_rect(Rect2(origin, Vector2(width, height)), Color(color.r, color.g, color.b, 0.42), false, 1.0)
	if pct > 0.0:
		_canvas_panel.draw_rect(Rect2(origin, Vector2(width * pct, height)), Color(color.r, color.g, color.b, 0.78), true)


func _draw_overlay_badge(center: Vector2, label: String, color: Color) -> void:
	_canvas_panel.draw_circle(center, 8.5, Color(color.r, color.g, color.b, 0.92))
	_canvas_panel.draw_arc(center, 8.5, 0.0, TAU, 24, Color(1, 1, 1, 0.35), 1.0, true)
	var font := ThemeDB.fallback_font
	var text_offset := Vector2(-3.2, 3.6)
	if label.length() > 1:
		text_offset.x = -5.5
	_canvas_panel.draw_string(font, center + text_offset, label, HORIZONTAL_ALIGNMENT_LEFT, -1, 8, Color(0.018, 0.035, 0.055, 1.0))


func _node_overlay_badges(node: Dictionary) -> Array:
	var badges: Array = []
	if _dict_positive_total(node.get("shortages", {})) > 0:
		badges.append({"label": "!", "color": COLOR_ERR})
	if _dict_positive_total(node.get("recipe_blocked", {})) > 0:
		badges.append({"label": "R", "color": COLOR_RECIPE_BLOCKED})
	if _node_has_supply(node):
		badges.append({"label": "S", "color": COLOR_OK})
	if _node_has_demand(node):
		badges.append({"label": "D", "color": COLOR_AMBER_HOT})
	if _node_has_inventory(node):
		badges.append({"label": "I", "color": COLOR_CYAN})
	if float(node.get("transfer_pressure", 0.0)) >= 0.75:
		badges.append({"label": "T", "color": _transfer_pressure_color(float(node.get("transfer_pressure", 0.0)), int(node.get("saturation_streak", 0)))})
	return badges


func _node_overlay_note(node: Dictionary) -> String:
	var shortages := _cargo_dict(node.get("shortages", {}))
	if _dict_positive_total(shortages) > 0:
		return "short %s" % _format_top_cargo(shortages, 1)
	var blocked := _cargo_dict(node.get("recipe_blocked", {}))
	if _dict_positive_total(blocked) > 0:
		return "recipe %s" % _format_top_cargo(blocked, 1)
	var transfer_pressure := float(node.get("transfer_pressure", 0.0))
	if transfer_pressure >= 0.95:
		return "xfer %d%%" % int(round(transfer_pressure * 100.0))
	if _node_has_demand(node):
		var demand := _cargo_dict(node.get("demand", {}))
		if demand.is_empty():
			demand = _node_recipe_inputs(node)
		return "needs %s" % _format_top_cargo(demand, 1)
	if _node_has_supply(node):
		var supply := _cargo_dict(node.get("production", {}))
		if supply.is_empty():
			supply = _node_recipe_outputs(node)
		if not supply.is_empty():
			return "makes %s" % _format_top_cargo(supply, 1)
		return "served buffer"
	return ""


func _node_overlay_note_color(node: Dictionary) -> Color:
	if _dict_positive_total(node.get("shortages", {})) > 0:
		return COLOR_ERR
	if _dict_positive_total(node.get("recipe_blocked", {})) > 0:
		return COLOR_RECIPE_BLOCKED
	if float(node.get("transfer_pressure", 0.0)) >= 0.95:
		return COLOR_ERR
	if _node_has_demand(node):
		return COLOR_AMBER_HOT
	if _node_has_supply(node):
		return COLOR_OK
	return COLOR_STEEL_2


func _node_has_inventory(node: Dictionary) -> bool:
	return _dict_positive_total(node.get("inventory", {})) > 0 or _node_storage_used(node) > 0


func _node_has_supply(node: Dictionary) -> bool:
	if _dict_positive_total(node.get("production", {})) > 0:
		return true
	if _dict_positive_total(_node_recipe_outputs(node)) > 0:
		return true
	return _nested_positive_total(node.get("served_last_tick", {})) > 0


func _node_has_demand(node: Dictionary) -> bool:
	if _dict_positive_total(node.get("demand", {})) > 0:
		return true
	return _dict_positive_total(_node_recipe_inputs(node)) > 0


func _node_storage_used(node: Dictionary) -> int:
	var storage = node.get("storage", {})
	if typeof(storage) != TYPE_DICTIONARY:
		return 0
	return int(storage.get("used", 0))


func _node_storage_pressure(node: Dictionary) -> float:
	var storage = node.get("storage", {})
	if typeof(storage) != TYPE_DICTIONARY:
		return 0.0
	var used := int(storage.get("used", 0))
	var capacity := int(storage.get("capacity", 1))
	if capacity < 1:
		capacity = 1
	return float(used) / float(capacity)


func _node_recipe_inputs(node: Dictionary) -> Dictionary:
	var recipe = node.get("recipe", null)
	if typeof(recipe) != TYPE_DICTIONARY:
		return {}
	var inputs = recipe.get("inputs", {})
	return _cargo_dict(inputs)


func _node_recipe_outputs(node: Dictionary) -> Dictionary:
	var recipe = node.get("recipe", null)
	if typeof(recipe) != TYPE_DICTIONARY:
		return {}
	var outputs = recipe.get("outputs", {})
	return _cargo_dict(outputs)


func _cargo_dict(payload) -> Dictionary:
	if typeof(payload) == TYPE_DICTIONARY:
		return payload
	return {}


func _dict_positive_total(payload) -> int:
	if typeof(payload) != TYPE_DICTIONARY:
		return 0
	var total := 0
	for key in payload.keys():
		var units := int(payload[key])
		if units > 0:
			total += units
	return total


func _nested_positive_total(payload) -> int:
	if typeof(payload) != TYPE_DICTIONARY:
		return 0
	var total := 0
	for key in payload.keys():
		var value = payload[key]
		if typeof(value) == TYPE_DICTIONARY:
			total += _dict_positive_total(value)
		else:
			var units := int(value)
			if units > 0:
				total += units
	return total


func _format_top_cargo(payload: Dictionary, max_items: int = 2) -> String:
	var parts: Array = []
	var keys: Array = payload.keys()
	keys.sort()
	for key in keys:
		var units := int(payload[key])
		if units <= 0:
			continue
		parts.append("%s %d" % [str(key).replace("_", " "), units])
		if parts.size() >= max_items:
			break
	if parts.is_empty():
		return "none"
	return ", ".join(parts)


func _transfer_pressure_color(pressure: float, saturation_streak: int = 0) -> Color:
	if pressure >= 0.95 or saturation_streak >= 2:
		return COLOR_ERR
	if pressure >= 0.75 or saturation_streak == 1:
		return COLOR_AMBER_HOT
	if pressure > 0.0:
		return COLOR_OK
	return COLOR_STEEL


func _draw_build_preview(_size: Vector2) -> void:
	var origin_id := ""
	var line_color := COLOR_OK
	var default_text := "click destination for backend preview"
	if _active_tool == TOOL_RAIL:
		origin_id = _rail_origin_id
	elif _active_tool == TOOL_TRAIN:
		origin_id = _route_origin_id
		line_color = COLOR_CYAN
		default_text = "click destination to preview route schedule"
	if origin_id.is_empty():
		return
	if not _node_positions.has(origin_id):
		return
	var origin_pos: Vector2 = _node_positions[origin_id]
	# Highlight the origin node
	_canvas_panel.draw_arc(origin_pos, 28.0, 0.0, TAU, 48, line_color, 3.0, true)
	# Rubber-band line to mouse — mouse must be in the same logical space
	# as _node_positions because the world transform is applied here.
	var mouse_screen := get_viewport().get_mouse_position()
	var mouse_local := (mouse_screen - _canvas_rect.position - _view_offset) / _view_scale
	_canvas_panel.draw_line(origin_pos, mouse_local, Color(line_color.r, line_color.g, line_color.b, 0.5), 3.0)
	var preview_text := default_text
	var preview_color := COLOR_AMBER_HOT
	if not _last_preview_result.is_empty():
		preview_text = _preview_summary(_last_preview_result)
		preview_color = COLOR_OK if bool(_last_preview_result.get("ok", false)) else COLOR_ERR
	var font := ThemeDB.fallback_font
	_canvas_panel.draw_string(font, mouse_local + Vector2(14, -8), preview_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, preview_color)


func _draw_snap_cursor(_size: Vector2) -> void:
	if _active_tool != TOOL_NODE and _active_tool != TOOL_GATE:
		return
	var mouse_screen := get_viewport().get_mouse_position()
	var mouse_local := (mouse_screen - _canvas_rect.position - _view_offset) / _view_scale
	var snapped := _snap_to_grid(mouse_local)
	var cell_rect := Rect2(
		snapped - Vector2(SNAP_CELL_HALF, SNAP_CELL_HALF),
		Vector2(GRID_MICRO, GRID_MICRO),
	)
	_canvas_panel.draw_rect(cell_rect, Color(COLOR_AMBER_HOT.r, COLOR_AMBER_HOT.g, COLOR_AMBER_HOT.b, 0.08), true)
	_canvas_panel.draw_rect(cell_rect, Color(COLOR_AMBER_HOT.r, COLOR_AMBER_HOT.g, COLOR_AMBER_HOT.b, 0.42), false, 1.0)
	var cross_half := 10.0
	var cross_color := Color(COLOR_AMBER_HOT.r, COLOR_AMBER_HOT.g, COLOR_AMBER_HOT.b, 0.6)
	_canvas_panel.draw_line(snapped + Vector2(-cross_half, 0), snapped + Vector2(cross_half, 0), cross_color, 1.0)
	_canvas_panel.draw_line(snapped + Vector2(0, -cross_half), snapped + Vector2(0, cross_half), cross_color, 1.0)
	# Diamond snap indicator
	var d := 5.0
	var diamond := PackedVector2Array([
		snapped + Vector2(0, -d), snapped + Vector2(d, 0),
		snapped + Vector2(0, d), snapped + Vector2(-d, 0),
	])
	_canvas_panel.draw_polyline(diamond, COLOR_AMBER_HOT, 1.5)
	_canvas_panel.draw_line(diamond[3], diamond[0], COLOR_AMBER_HOT, 1.5)
	var layout := _logical_to_layout(snapped)
	var font := ThemeDB.fallback_font
	_canvas_panel.draw_string(
		font,
		snapped + Vector2(12, -14),
		"grid %.0f, %.0f" % [float(layout.get("x", 0.0)), float(layout.get("y", 0.0))],
		HORIZONTAL_ALIGNMENT_LEFT,
		-1,
		10,
		COLOR_STEEL_2,
	)


func _preview_summary(result: Dictionary) -> String:
	if result.is_empty():
		return "backend preview pending"
	if not bool(result.get("ok", false)):
		return "INVALID · %s" % str(result.get("reason", result.get("message", "blocked")))
	var result_type := str(result.get("type", ""))
	if result_type == "PreviewCreateSchedule":
		var route_ticks := int(result.get("route_travel_ticks", 0))
		return "VALID ROUTE · %d ticks · click destination again" % route_ticks
	if result_type == "PreviewBuildLink" and str(result.get("mode", "")) == "gate":
		var power_shortfall := int(result.get("power_shortfall", 0))
		if power_shortfall > 0:
			return "VALID GATE · power short %d MW · confirm to build" % power_shortfall
		return "VALID GATE · powered · confirm to build"
	var cost := int(round(float(result.get("cost", 0.0))))
	var travel_ticks := int(result.get("travel_ticks", 0))
	if travel_ticks > 0:
		return "VALID · %d ticks · $%d · click again to build" % [travel_ticks, cost]
	if result_type == "PreviewPurchaseTrain":
		return "VALID TRAIN · $%d · click node again" % cost
	if result_type == "PreviewBuildInternalConnection":
		return "VALID WIRE · confirm to connect ports"
	return "VALID · $%d · click again to build" % cost


func _draw_node_glyph(pos: Vector2, kind: String, is_gate: bool) -> void:
	if is_gate:
		_draw_gate_hub(pos)
		return
	match kind:
		"extractor":
			_draw_hex(pos, 22, Color(0.10, 0.17, 0.27, 1.0), COLOR_STEEL, 1.6)
			_draw_hex(pos, 14, Color(0, 0, 0, 0), COLOR_STEEL_2, 1.0)
		"industry":
			_canvas_panel.draw_rect(Rect2(pos - Vector2(22, 22), Vector2(44, 44)), Color(0.10, 0.17, 0.27, 1.0), true)
			_canvas_panel.draw_rect(Rect2(pos - Vector2(22, 22), Vector2(44, 44)), COLOR_STEEL, false, 1.6)
			_canvas_panel.draw_arc(pos, 8, 0, TAU, 24, COLOR_CYAN, 1.4, true)
		"depot":
			_canvas_panel.draw_rect(Rect2(pos - Vector2(24, 18), Vector2(48, 36)), Color(0.10, 0.17, 0.27, 1.0), true)
			_canvas_panel.draw_rect(Rect2(pos - Vector2(24, 18), Vector2(48, 36)), COLOR_STEEL, false, 1.6)
			for i in range(3):
				_canvas_panel.draw_line(pos + Vector2(-20, -10 + i * 8), pos + Vector2(20, -10 + i * 8), COLOR_STEEL_2, 1.0)
		"warehouse":
			_canvas_panel.draw_rect(Rect2(pos - Vector2(28, 20), Vector2(56, 40)), Color(0.10, 0.17, 0.27, 1.0), true)
			_canvas_panel.draw_rect(Rect2(pos - Vector2(28, 20), Vector2(56, 40)), COLOR_STEEL, false, 1.6)
			for i in range(4):
				_canvas_panel.draw_line(pos + Vector2(-22, -12 + i * 8), pos + Vector2(22, -12 + i * 8), COLOR_STEEL_2, 1.0)
		"settlement":
			var roof_a := pos + Vector2(-18, 8)
			var roof_b := pos + Vector2(0, -14)
			var roof_c := pos + Vector2(18, 8)
			_canvas_panel.draw_rect(Rect2(pos + Vector2(-18, 8), Vector2(36, 14)), Color(0.10, 0.17, 0.27, 1.0), true)
			_canvas_panel.draw_rect(Rect2(pos + Vector2(-18, 8), Vector2(36, 14)), COLOR_STEEL, false, 1.4)
			_canvas_panel.draw_line(roof_a, roof_b, COLOR_STEEL, 1.4)
			_canvas_panel.draw_line(roof_b, roof_c, COLOR_STEEL, 1.4)
		"spaceport":
			_canvas_panel.draw_rect(Rect2(pos - Vector2(18, 18), Vector2(36, 36)), Color(0.10, 0.17, 0.27, 1.0), true)
			_canvas_panel.draw_rect(Rect2(pos - Vector2(18, 18), Vector2(36, 36)), COLOR_STEEL, false, 1.6)
			_canvas_panel.draw_arc(pos, 26, 0, TAU, 32, COLOR_CYAN, 1.4, false)
			_canvas_panel.draw_arc(pos, 36, 0, TAU, 48, COLOR_STEEL_2, 1.0, true)
		"gate_hub":
			_draw_gate_hub(pos)
		_:
			_canvas_panel.draw_arc(pos, 20, 0, TAU, 36, COLOR_STEEL, 1.6, true)


func _draw_hex(pos: Vector2, radius: float, fill: Color, stroke: Color, width: float) -> void:
	var pts := PackedVector2Array()
	for i in range(6):
		var a := PI / 2 + i * TAU / 6
		pts.append(pos + Vector2(cos(a), sin(a)) * radius)
	pts.append(pts[0])
	if fill.a > 0:
		var colors := PackedColorArray()
		for p in pts:
			colors.append(fill)
		_canvas_panel.draw_polygon(pts, colors)
	for i in range(6):
		_canvas_panel.draw_line(pts[i], pts[i + 1], stroke, width)


func _draw_gate_hub(pos: Vector2) -> void:
	_canvas_panel.draw_arc(pos, 48, 0, TAU, 64, Color(0.953, 0.612, 0.071, 0.20), 1.0, true)
	_canvas_panel.draw_arc(pos, 36, 0, TAU, 64, Color(0.953, 0.612, 0.071, 0.35), 1.2, true)
	_canvas_panel.draw_arc(pos, 26, 0, TAU, 56, COLOR_AMBER, 2.0, true)
	_canvas_panel.draw_arc(pos, 16, 0, TAU, 36, COLOR_AMBER_HOT, 1.4, true)
	_canvas_panel.draw_arc(pos, 6, 0, TAU, 24, Color("#ffe2b0"), 2.0, true)
	for i in range(4):
		var a := i * TAU / 4
		var p := pos + Vector2(cos(a), sin(a)) * 30
		_canvas_panel.draw_rect(Rect2(p - Vector2(4, 4), Vector2(8, 8)), COLOR_AMBER, true)


func _rebuild_node_positions(size: Vector2) -> void:
	_node_positions.clear()
	if _world_nodes.is_empty():
		_layout_bbox_center = Vector2.ZERO
		_layout_spread_scale = 1.0
		return
	var center := size * 0.5
	var fallback_radius: float = min(size.x, size.y) * 0.36
	var count := _world_nodes.size()

	# Collect raw layout points to derive bbox-driven spread.
	var layout_pts: Dictionary = {}
	for node in _world_nodes:
		var layout_data = node.get("layout", null)
		if typeof(layout_data) == TYPE_DICTIONARY:
			var nid := str(node.get("id", ""))
			layout_pts[nid] = Vector2(float(layout_data.get("x", 0.0)), float(layout_data.get("y", 0.0)))

	if layout_pts.is_empty():
		_layout_bbox_center = Vector2.ZERO
		_layout_spread_scale = 1.0
	else:
		var bbox_min := Vector2(INF, INF)
		var bbox_max := Vector2(-INF, -INF)
		for nid in layout_pts:
			var p: Vector2 = layout_pts[nid]
			bbox_min.x = min(bbox_min.x, p.x)
			bbox_min.y = min(bbox_min.y, p.y)
			bbox_max.x = max(bbox_max.x, p.x)
			bbox_max.y = max(bbox_max.y, p.y)
		_layout_bbox_center = (bbox_min + bbox_max) * 0.5
		var src_extent: float = max(bbox_max.x - bbox_min.x, bbox_max.y - bbox_min.y)
		var target_extent: float = min(size.x, size.y) * 0.75
		# Cap the scale so a single isolated node doesn't get blown up to fill the canvas.
		_layout_spread_scale = clampf(target_extent / max(1.0, src_extent), 1.0, 3.5) if src_extent > 1.0 else 1.0

	var idx := 0
	for node in _world_nodes:
		var node_id := str(node.get("id", ""))
		if layout_pts.has(node_id):
			var raw: Vector2 = layout_pts[node_id]
			_node_positions[node_id] = center + (raw - _layout_bbox_center) * _layout_spread_scale
			idx += 1
			continue
		var angle: float = -PI / 2.0 + (TAU * float(idx) / float(max(1, count)))
		var pos := center + Vector2(cos(angle), sin(angle)) * fallback_radius
		if node_id == _gate_hub_node_id:
			pos = center + Vector2(fallback_radius * 0.72, -fallback_radius * 0.05)
		_node_positions[node_id] = pos
		idx += 1


func _logical_to_layout(logical_pos: Vector2) -> Dictionary:
	# Inverse of the spread transform applied in _rebuild_node_positions, so a
	# node placed at click point `logical_pos` displays back at the same spot.
	var center := _canvas_rect.size * 0.5
	var scale: float = _layout_spread_scale if _layout_spread_scale > 0.0 else 1.0
	var raw: Vector2 = _layout_bbox_center + (logical_pos - center) / scale
	return {"x": raw.x, "y": raw.y}


# ---------- HUD ----------

func _build_hud() -> void:
	_hud = _make_panel(COLOR_PANEL_2, COLOR_HAIR)
	_canvas_layer.add_child(_hud)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 14)
	margin.add_theme_constant_override("margin_right", 14)
	margin.add_theme_constant_override("margin_top", 12)
	margin.add_theme_constant_override("margin_bottom", 12)
	_hud.add_child(margin)

	var outer := VBoxContainer.new()
	outer.add_theme_constant_override("separation", 12)
	margin.add_child(outer)

	_build_planet_card(outer)

	var scroll := ScrollContainer.new()
	scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	scroll.horizontal_scroll_mode = ScrollContainer.SCROLL_MODE_DISABLED
	outer.add_child(scroll)

	var scroll_box := VBoxContainer.new()
	scroll_box.add_theme_constant_override("separation", 14)
	scroll_box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	scroll.add_child(scroll_box)

	_build_inventory_section(scroll_box)
	_build_overlay_section(scroll_box)
	_build_gate_section(scroll_box)
	_build_queue_section(scroll_box)


func _build_planet_card(parent: VBoxContainer) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	parent.add_child(row)

	var ball := Control.new()
	ball.custom_minimum_size = Vector2(56, 56)
	ball.draw.connect(func():
		var c := Vector2(28, 28)
		ball.draw_arc(c, 26, 0, TAU, 64, Color(0.075, 0.145, 0.235, 1.0), 26.0, true)
		ball.draw_arc(c, 26, 0, TAU, 64, COLOR_HAIR_2, 1.0, true)
		ball.draw_arc(c, 14, 0, TAU, 48, Color(0.369, 0.525, 0.710, 0.4), 0.0, true)
	)
	row.add_child(ball)

	var info := VBoxContainer.new()
	info.add_theme_constant_override("separation", 2)
	info.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(info)

	_planet_name = Label.new()
	_planet_name.text = "—"
	_planet_name.add_theme_color_override("font_color", COLOR_ICE)
	_planet_name.add_theme_font_size_override("font_size", 16)
	info.add_child(_planet_name)

	_planet_meta = Label.new()
	_planet_meta.text = "TIER — · POP — · STAB —"
	_planet_meta.add_theme_color_override("font_color", COLOR_STEEL)
	_planet_meta.add_theme_font_size_override("font_size", 10)
	info.add_child(_planet_meta)

	var stab_bg := ColorRect.new()
	stab_bg.color = Color(COLOR_STEEL.r, COLOR_STEEL.g, COLOR_STEEL.b, 0.2)
	stab_bg.custom_minimum_size = Vector2(0, 4)
	info.add_child(stab_bg)

	_planet_stab_fill = ColorRect.new()
	_planet_stab_fill.color = COLOR_OK
	_planet_stab_fill.custom_minimum_size = Vector2(0, 4)
	_planet_stab_fill.anchor_left = 0.0
	_planet_stab_fill.anchor_right = 0.0
	stab_bg.add_child(_planet_stab_fill)
	stab_bg.resized.connect(_resize_stab_fill.bind(stab_bg))


func _resize_stab_fill(bg: ColorRect) -> void:
	_update_stab_fill()


func _update_stab_fill() -> void:
	if _planet_stab_fill == null:
		return
	var parent := _planet_stab_fill.get_parent() as ColorRect
	if parent == null:
		return
	var stab := float(_selected_world.get("stability", 0.0)) if _selected_world.size() > 0 else 0.0
	stab = clamp(stab, 0.0, 1.0)
	_planet_stab_fill.size = Vector2(parent.size.x * stab, parent.size.y)


func _build_inventory_section(parent: VBoxContainer) -> void:
	var header := _make_hud_header("Local Inventory", "—")
	parent.add_child(header)
	_inventory_sub = header.get_meta("sub") as Label
	_inventory_list = VBoxContainer.new()
	_inventory_list.add_theme_constant_override("separation", 7)
	parent.add_child(_inventory_list)


func _build_overlay_section(parent: VBoxContainer) -> void:
	var header := _make_hud_header("Local Overlays", "off")
	parent.add_child(header)
	_overlay_sub = header.get_meta("sub") as Label
	_overlay_list = VBoxContainer.new()
	_overlay_list.add_theme_constant_override("separation", 5)
	parent.add_child(_overlay_list)
	_update_overlay_summary()


func _update_overlay_summary() -> void:
	if _overlay_list == null:
		return
	for child in _overlay_list.get_children():
		child.queue_free()

	var counts := _overlay_counts()
	var alert_count := int(counts.get("shortage", 0)) + int(counts.get("recipe_blocked", 0)) + int(counts.get("transfer_hot", 0))
	if _overlay_sub != null:
		_overlay_sub.text = "%s · %d alerts" % ["on" if _show_zone_overlay else "off", alert_count]

	_overlay_list.add_child(_make_overlay_summary_row("Toggle", "L / layer tool", COLOR_CYAN))
	_overlay_list.add_child(_make_overlay_summary_row("Supply", "%d nodes" % int(counts.get("supply", 0)), COLOR_OK))
	_overlay_list.add_child(_make_overlay_summary_row("Demand", "%d nodes" % int(counts.get("demand", 0)), COLOR_AMBER_HOT))
	_overlay_list.add_child(_make_overlay_summary_row("Inventory", "%d stocked" % int(counts.get("inventory", 0)), COLOR_CYAN))
	_overlay_list.add_child(_make_overlay_summary_row("Shortage", "%d blocked" % int(counts.get("shortage", 0)), COLOR_ERR))
	_overlay_list.add_child(_make_overlay_summary_row("Recipe", "%d waiting" % int(counts.get("recipe_blocked", 0)), COLOR_RECIPE_BLOCKED))
	_overlay_list.add_child(_make_overlay_summary_row("Transfer", "%d hot" % int(counts.get("transfer_hot", 0)), _transfer_pressure_color(0.95) if int(counts.get("transfer_hot", 0)) > 0 else COLOR_STEEL))


func _overlay_counts() -> Dictionary:
	var counts := {
		"supply": 0,
		"demand": 0,
		"inventory": 0,
		"shortage": 0,
		"recipe_blocked": 0,
		"transfer_hot": 0,
	}
	for node in _world_nodes:
		if typeof(node) != TYPE_DICTIONARY:
			continue
		if _node_has_supply(node):
			counts["supply"] = int(counts["supply"]) + 1
		if _node_has_demand(node):
			counts["demand"] = int(counts["demand"]) + 1
		if _node_has_inventory(node):
			counts["inventory"] = int(counts["inventory"]) + 1
		if _dict_positive_total(node.get("shortages", {})) > 0:
			counts["shortage"] = int(counts["shortage"]) + 1
		if _dict_positive_total(node.get("recipe_blocked", {})) > 0:
			counts["recipe_blocked"] = int(counts["recipe_blocked"]) + 1
		if float(node.get("transfer_pressure", 0.0)) >= 0.75 or int(node.get("saturation_streak", 0)) > 0:
			counts["transfer_hot"] = int(counts["transfer_hot"]) + 1
	return counts


func _make_overlay_summary_row(label_text: String, value_text: String, color: Color) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 7)

	var dot := ColorRect.new()
	dot.color = color
	dot.custom_minimum_size = Vector2(7, 7)
	dot.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(dot)

	var label := Label.new()
	label.text = label_text
	label.add_theme_color_override("font_color", COLOR_STEEL)
	label.add_theme_font_size_override("font_size", 10)
	label.custom_minimum_size = Vector2(70, 0)
	row.add_child(label)

	var value := Label.new()
	value.text = value_text
	value.add_theme_color_override("font_color", color)
	value.add_theme_font_size_override("font_size", 10)
	value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(value)
	return row


func _build_gate_section(parent: VBoxContainer) -> void:
	var header := _make_hud_header("Gate Throughput", "→ Galaxy")
	parent.add_child(header)

	_gate_card = PanelContainer.new()
	var gate_style := StyleBoxFlat.new()
	gate_style.bg_color = Color(0.953, 0.612, 0.071, 0.06)
	gate_style.border_color = Color(0.953, 0.612, 0.071, 0.35)
	gate_style.set_border_width_all(1)
	gate_style.content_margin_left = 10
	gate_style.content_margin_right = 10
	gate_style.content_margin_top = 8
	gate_style.content_margin_bottom = 8
	_gate_card.add_theme_stylebox_override("panel", gate_style)
	parent.add_child(_gate_card)

	var col := VBoxContainer.new()
	col.add_theme_constant_override("separation", 6)
	_gate_card.add_child(col)

	var title_row := HBoxContainer.new()
	_gate_title_value = Label.new()
	_gate_title_value.text = "NO GATE HUB"
	_gate_title_value.add_theme_color_override("font_color", COLOR_AMBER_HOT)
	_gate_title_value.add_theme_font_size_override("font_size", 11)
	_gate_title_value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	title_row.add_child(_gate_title_value)

	_gate_status_value = Label.new()
	_gate_status_value.text = "—"
	_gate_status_value.add_theme_color_override("font_color", COLOR_STEEL)
	_gate_status_value.add_theme_font_size_override("font_size", 9)
	title_row.add_child(_gate_status_value)
	col.add_child(title_row)

	_gate_bars_box = VBoxContainer.new()
	_gate_bars_box.add_theme_constant_override("separation", 6)
	col.add_child(_gate_bars_box)

	var foot1 := HBoxContainer.new()
	var k1 := Label.new()
	k1.text = "Linked to"
	k1.add_theme_color_override("font_color", COLOR_STEEL)
	k1.add_theme_font_size_override("font_size", 10)
	k1.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	foot1.add_child(k1)
	_gate_linked_value = Label.new()
	_gate_linked_value.text = "—"
	_gate_linked_value.add_theme_color_override("font_color", COLOR_AMBER_HOT)
	_gate_linked_value.add_theme_font_size_override("font_size", 10)
	foot1.add_child(_gate_linked_value)
	col.add_child(foot1)

	var foot2 := HBoxContainer.new()
	var k2 := Label.new()
	k2.text = "Next activation"
	k2.add_theme_color_override("font_color", COLOR_STEEL)
	k2.add_theme_font_size_override("font_size", 10)
	k2.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	foot2.add_child(k2)
	_gate_activation_value = Label.new()
	_gate_activation_value.text = "—"
	_gate_activation_value.add_theme_color_override("font_color", COLOR_ICE)
	_gate_activation_value.add_theme_font_size_override("font_size", 10)
	foot2.add_child(_gate_activation_value)
	col.add_child(foot2)


func _build_queue_section(parent: VBoxContainer) -> void:
	var header := _make_hud_header("Build Planner", "idle")
	parent.add_child(header)
	_queue_sub = header.get_meta("sub") as Label

	_queue_list = VBoxContainer.new()
	_queue_list.add_theme_constant_override("separation", 6)
	parent.add_child(_queue_list)

	_refresh_construction_hud()


func _refresh_construction_hud() -> void:
	if _queue_list == null:
		return
	for child in _queue_list.get_children():
		child.queue_free()

	if _queue_sub != null:
		_queue_sub.text = _planner_state_label()

	_add_planner_line("Tool", _active_tool_label(), COLOR_ICE)
	if _active_tool == TOOL_NODE or _active_tool == TOOL_GATE:
		_add_planner_line("Snap", "%.0f-unit grid" % GRID_MICRO, COLOR_STEEL_2)
	if not _route_train_id.is_empty():
		_add_planner_line("Route Train", _route_train_id, COLOR_CYAN)
		_add_planner_line("Origin", _node_display_name(_route_origin_id), COLOR_ICE)
		if not _pending_route_tuning_train_id.is_empty():
			_add_planner_line("Destination", _node_display_name(_pending_route_tuning_dest_id), COLOR_ICE)
			_add_planner_line("Cargo", _pending_route_tuning_cargo.replace("_", " "), COLOR_AMBER_HOT)
			_add_planner_note("Tune units and interval in the route popup, then preview through the backend.", COLOR_STEEL)
		else:
			_add_planner_note("Click a destination node to pick a cargo and preview a schedule.", COLOR_STEEL)

	if _active_tool == TOOL_SELECT and not _selected_local_id.is_empty():
		_add_select_inspection()
	elif not _last_preview_result.is_empty():
		_add_preview_details(_last_preview_result)
	elif _pending_preview_kind != "":
		_add_planner_line("Preview", _preview_kind_display(_pending_preview_kind), COLOR_AMBER_HOT)
		_add_planner_note("Waiting for backend validation...", COLOR_STEEL)
	else:
		_add_idle_planner_guidance()

	if not _pending_build_command.is_empty():
		_add_preview_actions()


func _planner_state_label() -> String:
	if not _pending_build_command.is_empty():
		return "ready"
	if _active_tool == TOOL_SELECT and not _selected_local_id.is_empty():
		return "inspect"
	if not _last_preview_result.is_empty():
		return "blocked" if not bool(_last_preview_result.get("ok", false)) else "valid"
	if not _pending_route_tuning_train_id.is_empty():
		return "tuning"
	if not _route_train_id.is_empty():
		return "routing"
	if _pending_preview_kind != "":
		return "checking"
	return "idle"


func _active_tool_label() -> String:
	match _active_tool:
		TOOL_RAIL:
			return "Lay Rail"
		TOOL_NODE:
			return "Place Node"
		TOOL_WIRE:
			return "Wire Ports"
		TOOL_GATE:
			return "Gate Hub"
		TOOL_TRAIN:
			return "Train / Route"
		TOOL_DEMOLISH:
			return "Demolish"
		TOOL_LAYERS:
			return "Layer Overlays"
		TOOL_PAN:
			return "Pan"
		_:
			return "Select"


func _preview_kind_display(kind: String) -> String:
	match kind:
		"node":
			return "Node Build"
		"rail":
			return "Rail Link"
		"train":
			return "Train Purchase"
		"schedule":
			return "Route Schedule"
		"gate_link":
			return "Gate Link"
		"internal_connection":
			return "Internal Wire"
		_:
			return kind.capitalize()


func _add_preview_details(result: Dictionary) -> void:
	var ok := bool(result.get("ok", false))
	var color := COLOR_OK if ok else COLOR_ERR
	_add_planner_line("Preview", "VALID" if ok else "INVALID", color)
	_add_planner_note(str(result.get("message", "")), color)
	_add_planner_line("Target", str(result.get("target_id", "—")), COLOR_STEEL_2)

	if result.has("cost"):
		_add_planner_line("Cost", "₡ %s" % _format_commas(float(result.get("cost", 0.0))), COLOR_AMBER_HOT)
	if result.has("build_time"):
		_add_planner_line("Build Time", "%d ticks" % int(result.get("build_time", 0)), COLOR_STEEL_2)
	if result.has("travel_ticks"):
		_add_planner_line("Travel", "%d ticks" % int(result.get("travel_ticks", 0)), COLOR_STEEL_2)
	if result.has("capacity"):
		_add_planner_line("Capacity", "%d units" % int(result.get("capacity", 0)), COLOR_STEEL_2)
	if result.has("storage_capacity"):
		_add_planner_line("Storage", _format_commas(float(result.get("storage_capacity", 0))), COLOR_STEEL_2)
	if result.has("transfer_limit_per_tick"):
		_add_planner_line("Transfer", "%d / tick" % int(result.get("transfer_limit_per_tick", 0)), COLOR_STEEL_2)
	if result.has("route_travel_ticks"):
		_add_planner_line("Route", "%d ticks" % int(result.get("route_travel_ticks", 0)), COLOR_CYAN)
	if result.has("gate_handoffs") or result.has("route_warnings"):
		_add_route_gate_context(result)
	if str(result.get("mode", "")) == "gate":
		_add_gate_preview_context(result)

	var normalized = result.get("normalized_command", {})
	if typeof(normalized) == TYPE_DICTIONARY:
		_add_normalized_command_details(normalized)


func _add_gate_preview_context(result: Dictionary) -> void:
	var origin_world := str(result.get("origin_world_name", result.get("origin_world_id", "—")))
	var destination_world := str(result.get("destination_world_name", result.get("destination_world_id", "—")))
	_add_planner_line("Worlds", "%s -> %s" % [origin_world, destination_world], COLOR_AMBER_HOT)
	_add_planner_line("Power Source", str(result.get("power_source_world_name", result.get("power_source_world_id", "—"))), COLOR_STEEL_2)
	_add_planner_line("Power Draw", "%d MW" % int(result.get("power_required", 0)), COLOR_AMBER_HOT)
	var shortfall := int(result.get("power_shortfall", 0))
	var available := int(result.get("power_available", 0))
	var powered := bool(result.get("powered_if_built", false))
	var power_color := COLOR_OK if powered else COLOR_ERR
	_add_planner_line("Power Check", "%d MW available · short %d" % [available, shortfall], power_color)
	if not powered:
		_add_planner_note("Gate can be built now but will stay offline until the power shortfall is resolved.", COLOR_ERR)


func _add_route_gate_context(result: Dictionary) -> void:
	var gate_ids: Array = result.get("gate_link_ids", []) if typeof(result.get("gate_link_ids", [])) == TYPE_ARRAY else []
	var handoffs: Array = result.get("gate_handoffs", []) if typeof(result.get("gate_handoffs", [])) == TYPE_ARRAY else []
	var warnings: Array = result.get("route_warnings", []) if typeof(result.get("route_warnings", [])) == TYPE_ARRAY else []
	if gate_ids.is_empty() and handoffs.is_empty() and warnings.is_empty():
		return
	if not gate_ids.is_empty():
		_add_planner_line("Gate Route", ", ".join(_string_list(gate_ids)), COLOR_AMBER_HOT)
	for item in handoffs:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var handoff: Dictionary = item
		var label := "%s -> %s" % [
			str(handoff.get("from_world_name", handoff.get("from_world_id", "—"))),
			str(handoff.get("to_world_name", handoff.get("to_world_id", "—"))),
		]
		var powered := bool(handoff.get("powered", false))
		var pressure := float(handoff.get("pressure", 0.0))
		var shortfall := int(handoff.get("power_shortfall", 0))
		var color := COLOR_OK
		var state := "powered"
		if not powered:
			color = COLOR_ERR
			state = "unpowered · short %d MW" % shortfall
		elif pressure >= 1.0:
			color = COLOR_ERR
			state = "slots full"
		elif pressure >= 0.75:
			color = COLOR_AMBER_HOT
			state = "%d%% slots" % int(round(pressure * 100.0))
		elif bool(handoff.get("disrupted", false)):
			color = COLOR_AMBER_HOT
			state = "degraded"
		var slots_text := "%d/%d slots" % [int(handoff.get("slots_used", 0)), int(handoff.get("slot_capacity", 0))]
		_add_planner_line("Handoff", "%s · %s · %s" % [label, state, slots_text], color)
	for item in warnings:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var warning: Dictionary = item
		var severity := str(warning.get("severity", "warning"))
		var warning_color := _route_warning_color(severity)
		var link_id := str(warning.get("link_id", "gate"))
		var reason := str(warning.get("reason", "route warning"))
		_add_planner_note("%s · %s" % [link_id, reason], warning_color)


func _route_warning_color(severity: String) -> Color:
	if severity in ["blocked", "congested"]:
		return COLOR_ERR
	if severity in ["degraded", "hot"]:
		return COLOR_AMBER_HOT
	return COLOR_STEEL_2


func _string_list(values: Array) -> Array:
	var output: Array = []
	for value in values:
		output.append(str(value))
	return output


func _add_normalized_command_details(command: Dictionary) -> void:
	var command_type := str(command.get("type", ""))
	match command_type:
		"BuildNode":
			_add_planner_line("Kind", _kind_display(str(command.get("kind", "node"))), COLOR_ICE)
			var layout = command.get("layout", {})
			if typeof(layout) == TYPE_DICTIONARY:
				_add_planner_line("Layout", "%.0f, %.0f" % [float(layout.get("x", 0.0)), float(layout.get("y", 0.0))], COLOR_STEEL_2)
		"BuildLink":
			_add_planner_line("Mode", str(command.get("mode", "rail")), COLOR_AMBER_HOT)
			_add_planner_line("From", _node_display_name(str(command.get("origin", ""))), COLOR_ICE)
			_add_planner_line("To", _node_display_name(str(command.get("destination", ""))), COLOR_ICE)
			if str(command.get("mode", "")) == "gate":
				_add_planner_line("Power", "%d MW" % int(command.get("power_required", 0)), COLOR_AMBER_HOT)
		"PurchaseTrain":
			_add_planner_line("Node", _node_display_name(str(command.get("node_id", ""))), COLOR_ICE)
		"CreateSchedule":
			_add_planner_line("Train", str(command.get("train_id", "")), COLOR_CYAN)
			_add_planner_line("From", _node_display_name(str(command.get("origin", ""))), COLOR_ICE)
			_add_planner_line("To", _node_display_name(str(command.get("destination", ""))), COLOR_ICE)
			_add_planner_line("Cargo", str(command.get("cargo_type", "")).replace("_", " "), COLOR_AMBER_HOT)
			_add_planner_line("Units", "%d every %d ticks" % [int(command.get("units_per_departure", 0)), int(command.get("interval_ticks", 0))], COLOR_STEEL_2)
		"BuildInternalConnection":
			_add_planner_line("Node", _node_display_name(str(command.get("node_id", ""))), COLOR_ICE)
			_add_planner_line("From", "%s.%s" % [str(command.get("source_component_id", "")), str(command.get("source_port_id", ""))], COLOR_CYAN)
			_add_planner_line("To", "%s.%s" % [str(command.get("destination_component_id", "")), str(command.get("destination_port_id", ""))], COLOR_CYAN)


func _add_idle_planner_guidance() -> void:
	match _active_tool:
		TOOL_NODE:
			_add_planner_note("Click an empty grid tile, choose a node type, then confirm after backend preview.", COLOR_STEEL)
		TOOL_WIRE:
			_add_planner_note("Select a node with a facility, then drag an output port to an input port in the drill-in panel.", COLOR_STEEL)
		TOOL_GATE:
			_add_planner_note("Click an empty grid tile to preview a gate hub. Click an existing gate hub to preview an interworld gate link.", COLOR_STEEL)
		TOOL_RAIL:
			_add_planner_note("Click an origin node, then a destination node. Backend validates same-world rail and cost.", COLOR_STEEL)
		TOOL_TRAIN:
			_add_planner_note("Click a node with no idle train to preview buying one. Click a node with an idle train to start a route.", COLOR_STEEL)
		TOOL_DEMOLISH:
			_add_planner_note("Click a rail link to demolish it. Active train routes block demolition.", COLOR_STEEL)
		TOOL_SELECT:
			_add_planner_note("Click a node or link to inspect it. ESC clears selection.", COLOR_STEEL)
		_:
			_add_planner_note("Select a build tool to preview construction or route actions here.", COLOR_STEEL)


func _add_select_inspection() -> void:
	match _selected_local_kind:
		"node":
			_add_node_inspection(_selected_local_id)
		"link":
			_add_link_inspection(_selected_local_id)
		_:
			_add_planner_note("Nothing selected.", COLOR_STEEL)


func _add_node_inspection(node_id: String) -> void:
	var node := _node_snapshot(node_id)
	if node.is_empty():
		_add_planner_line("Node", node_id, COLOR_ERR)
		_add_planner_note("Node not in current snapshot.", COLOR_ERR)
		return
	_add_planner_line("Node", str(node.get("name", node_id)), COLOR_ICE)
	_add_planner_line("Id", str(node.get("id", node_id)), COLOR_STEEL_2)
	_add_planner_line("Kind", _kind_display(str(node.get("kind", "node"))), COLOR_AMBER_HOT)
	_add_planner_line("World", str(node.get("world_id", "—")), COLOR_STEEL_2)

	var project_id = node.get("construction_project_id")
	if project_id != null and str(project_id) != "":
		_add_planner_line("Status", "Under Construction", COLOR_AMBER_HOT)
		var projects: Array = _latest_snapshot.get("construction_projects", []) if typeof(_latest_snapshot.get("construction_projects")) == TYPE_ARRAY else []
		for proj in projects:
			if typeof(proj) == TYPE_DICTIONARY and str(proj.get("id", "")) == str(project_id):
				var req: Dictionary = proj.get("required_cargo", {}) if typeof(proj.get("required_cargo")) == TYPE_DICTIONARY else {}
				var deliv: Dictionary = proj.get("delivered_cargo", {}) if typeof(proj.get("delivered_cargo")) == TYPE_DICTIONARY else {}
				var ckeys: Array = req.keys()
				ckeys.sort()
				for c in ckeys:
					var r = int(req[c])
					var d = int(deliv.get(c, 0))
					var color = COLOR_OK if d >= r else COLOR_AMBER_HOT
					var ratio = float(d) / float(r) if r > 0 else 1.0
					_add_progress_bar(str(c).replace("_", " "), ratio, color)
					_add_planner_note("  %d / %d units delivered" % [d, r], COLOR_STEEL_2)

	var storage: Dictionary = node.get("storage", {}) if typeof(node.get("storage")) == TYPE_DICTIONARY else {}
	if not storage.is_empty():
		_add_planner_line("Storage", "%d / %d" % [int(storage.get("used", 0)), int(storage.get("capacity", 0))], COLOR_STEEL_2)
	var transfer_limit := int(node.get("transfer_limit", 0))
	var transfer_used := int(node.get("transfer_used", 0))
	var transfer_pressure := float(node.get("transfer_pressure", 0.0))
	var saturation_streak := int(node.get("saturation_streak", 0))
	var pressure_color := COLOR_STEEL_2
	if transfer_pressure >= 0.95:
		pressure_color = COLOR_ERR
	elif transfer_pressure >= 0.75:
		pressure_color = COLOR_AMBER_HOT
	elif transfer_pressure > 0.0:
		pressure_color = COLOR_OK
	_add_planner_line(
		"Transfer",
		"%d / %d (%d%%)" % [transfer_used, transfer_limit, int(round(transfer_pressure * 100.0))],
		pressure_color,
	)
	if saturation_streak >= 2:
		_add_planner_note(
			"SATURATED · %d ticks at limit" % saturation_streak,
			COLOR_ERR,
		)
	elif saturation_streak == 1:
		_add_planner_note("Approaching limit", COLOR_AMBER_HOT)
	_add_inspection_dict_line("Inventory", node.get("inventory", {}))
	_add_inspection_dict_line("Demand", node.get("demand", {}))
	_add_inspection_dict_line("Production", node.get("production", {}))
	var shortages = node.get("shortages", {})
	if typeof(shortages) == TYPE_DICTIONARY and not shortages.is_empty():
		_add_inspection_dict_line("Shortages", shortages)
	var trains_here := _trains_at_node(node_id)
	if not trains_here.is_empty():
		_add_planner_line("Trains", ", ".join(trains_here), COLOR_CYAN)
	var space_sites: Array = _latest_snapshot.get("space_sites", []) if typeof(_latest_snapshot.get("space_sites")) == TYPE_ARRAY else []
	if not space_sites.is_empty() and str(node.get("kind", "")) == "spaceport":
		_add_planner_line("Space Sites", "%d discovered" % space_sites.size(), COLOR_ICE)
		for site in space_sites:
			if typeof(site) != TYPE_DICTIONARY:
				continue
			var site_id := str(site.get("id", ""))
			var sname := str(site.get("name", ""))
			var sres := str(site.get("resource_id", "")).replace("_", " ")
			var dist := int(site.get("travel_ticks", 0))
			var row := HBoxContainer.new()
			var lbl := Label.new()
			lbl.text = "• %s (%s) · %d tk" % [sname, sres, dist]
			lbl.add_theme_color_override("font_color", COLOR_STEEL)
			lbl.add_theme_font_size_override("font_size", 10)
			lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
			row.add_child(lbl)
			var btn := _make_hud_button("Launch", COLOR_CYAN)
			btn.pressed.connect(func():
				GateRailBridge.send_message({
					"commands": [{
						"type": "DispatchMiningMission",
						"mission_id": "m_%d" % Time.get_ticks_msec(),
						"site_id": site_id,
						"launch_node_id": node_id,
						"return_node_id": node_id
					}],
					"ticks": 0
				})
			)
			row.add_child(btn)
			_queue_list.add_child(row)

	var missions: Array = _latest_snapshot.get("mining_missions", []) if typeof(_latest_snapshot.get("mining_missions")) == TYPE_ARRAY else []
	var node_missions: Array = []
	for mission in missions:
		if typeof(mission) != TYPE_DICTIONARY:
			continue
		if str(mission.get("launch_node_id", "")) == node_id or str(mission.get("return_node_id", "")) == node_id:
			node_missions.append(mission)

	if not node_missions.is_empty():
		_add_planner_line("Missions", "%d active" % node_missions.size(), COLOR_CYAN)
		for mission in node_missions:
			var mstatus := str(mission.get("status", "unknown")).replace("_", " ")
			var ms_ticks := int(mission.get("ticks_remaining", 0))
			_add_planner_note("• %s · %s · %dtk left" % [str(mission.get("id", "")), mstatus, ms_ticks], COLOR_STEEL_2)

	var links_here := _link_ids_touching(node_id)
	if not links_here.is_empty():
		_add_planner_line("Links", ", ".join(links_here), COLOR_STEEL_2)

	_add_facility_inspection(node)


func _add_facility_inspection(node: Dictionary) -> void:
	var facility: Dictionary = node.get("facility", {}) if typeof(node.get("facility")) == TYPE_DICTIONARY else {}
	if facility.is_empty():
		return

	_add_planner_line("Facility", "Industrial Complex", COLOR_ICE)
	var power := int(facility.get("power_required", 0))
	if power > 0:
		_add_planner_line("  Power Draw", "%d MW" % power, COLOR_AMBER_HOT)

	var storage := int(facility.get("storage_capacity_override", 0))
	if storage > 0:
		_add_planner_line("  Storage+", "+%d units" % storage, COLOR_OK)

	var components: Array = facility.get("components", []) if typeof(facility.get("components")) == TYPE_ARRAY else []
	var blocked: Array = node.get("facility_blocked", []) if typeof(node.get("facility_blocked")) == TYPE_ARRAY else []

	for comp in components:
		if typeof(comp) != TYPE_DICTIONARY: continue
		var cid := str(comp.get("id", ""))
		var kind := str(comp.get("kind", "")).replace("_", " ").capitalize()
		var is_blocked := cid in blocked

		var color := COLOR_ERR if is_blocked else COLOR_OK
		_add_planner_line("  • " + kind, cid, color)

		var inputs: Dictionary = comp.get("inputs", {}) if typeof(comp.get("inputs")) == TYPE_DICTIONARY else {}
		if not inputs.is_empty():
			var iparts: Array = []
			for k in inputs.keys():
				iparts.append("%s %d" % [str(k).replace("_", " "), int(inputs[k])])
			_add_planner_note("    In: " + ", ".join(iparts), COLOR_STEEL)

		var outputs: Dictionary = comp.get("outputs", {}) if typeof(comp.get("outputs")) == TYPE_DICTIONARY else {}
		if not outputs.is_empty():
			var oparts: Array = []
			for k in outputs.keys():
				oparts.append("%s %d" % [str(k).replace("_", " "), int(outputs[k])])
			_add_planner_note("    Out: " + ", ".join(oparts), COLOR_OK)

		var ports: Array = comp.get("ports", []) if typeof(comp.get("ports")) == TYPE_ARRAY else []
		if not ports.is_empty():
			var pparts: Array = []
			for p in ports:
				if typeof(p) != TYPE_DICTIONARY: continue
				var pd := "IN" if str(p.get("direction")) == "input" else "OUT"
				var pc := str(p.get("cargo", "all")).replace("_", " ")
				var inv: Dictionary = p.get("inventory", {}) if typeof(p.get("inventory")) == TYPE_DICTIONARY else {}
				var inv_text := ""
				if not inv.is_empty():
					inv_text = " [%s]" % _format_top_cargo(inv, 1)
				pparts.append("%s %s%s" % [pd, pc, inv_text])
			_add_planner_note("    Ports: " + ", ".join(pparts), COLOR_STEEL_2)

	var connections: Array = facility.get("connections", []) if typeof(facility.get("connections")) == TYPE_ARRAY else []
	if not connections.is_empty():
		_add_planner_line("  Wires", "%d internal" % connections.size(), COLOR_CYAN)
		for connection in connections:
			if typeof(connection) != TYPE_DICTIONARY:
				continue
			_add_planner_note(
				"    %s.%s -> %s.%s" % [
					str(connection.get("source_component_id", "")),
					str(connection.get("source_port_id", "")),
					str(connection.get("destination_component_id", "")),
					str(connection.get("destination_port_id", "")),
				],
				COLOR_STEEL_2,
			)


func _add_link_inspection(link_id: String) -> void:
	var link := _link_snapshot(link_id)
	if link.is_empty():
		_add_planner_line("Link", link_id, COLOR_ERR)
		_add_planner_note("Link not in current snapshot.", COLOR_ERR)
		return
	_add_planner_line("Link", str(link.get("id", link_id)), COLOR_ICE)
	_add_planner_line("From", _node_display_name(str(link.get("origin", ""))), COLOR_ICE)
	_add_planner_line("To", _node_display_name(str(link.get("destination", ""))), COLOR_ICE)
	_add_planner_line("Mode", str(link.get("mode", "—")), COLOR_AMBER_HOT)
	_add_planner_line("Travel", "%d ticks" % int(link.get("travel_ticks", 0)), COLOR_STEEL_2)
	_add_planner_line("Capacity", "%d / tick" % int(link.get("capacity", 0)), COLOR_STEEL_2)
	var trains_on := int(link.get("trains_on_link", 0))
	if trains_on > 0:
		_add_planner_line("In Transit", "%d trains" % trains_on, COLOR_CYAN)
	if bool(link.get("disrupted", false)):
		var reasons: Array = link.get("disruption_reasons", []) if typeof(link.get("disruption_reasons")) == TYPE_ARRAY else []
		_add_planner_line("Disrupted", ", ".join(reasons) if not reasons.is_empty() else "yes", COLOR_ERR)
	_add_planner_line("Powered", "yes" if bool(link.get("powered", true)) else "no", COLOR_OK if bool(link.get("powered", true)) else COLOR_ERR)
	if float(link.get("build_cost", 0.0)) > 0.0:
		_add_planner_line("Build Cost", "₡ %s" % _format_commas(float(link.get("build_cost", 0.0))), COLOR_AMBER_HOT)


func _add_inspection_dict_line(label_text: String, payload) -> void:
	if typeof(payload) != TYPE_DICTIONARY or payload.is_empty():
		return
	var parts: Array = []
	var keys: Array = payload.keys()
	keys.sort()
	for key in keys:
		parts.append("%s %s" % [str(key).replace("_", " "), str(payload[key])])
	_add_planner_line(label_text, ", ".join(parts), COLOR_STEEL_2)


func _link_snapshot(link_id: String) -> Dictionary:
	var links: Array = _latest_snapshot.get("links", [])
	for link in links:
		if typeof(link) == TYPE_DICTIONARY and str(link.get("id", "")) == link_id:
			return link
	return {}


func _trains_at_node(node_id: String) -> Array:
	var ids: Array = []
	var trains: Array = _latest_snapshot.get("trains", [])
	for train in trains:
		if typeof(train) != TYPE_DICTIONARY:
			continue
		if str(train.get("node_id", "")) == node_id:
			ids.append(str(train.get("id", "")))
	return ids


func _link_ids_touching(node_id: String) -> Array:
	var ids: Array = []
	var links: Array = _latest_snapshot.get("links", [])
	for link in links:
		if typeof(link) != TYPE_DICTIONARY:
			continue
		if str(link.get("origin", "")) == node_id or str(link.get("destination", "")) == node_id:
			ids.append(str(link.get("id", "")))
	return ids


func _add_preview_actions() -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	_queue_list.add_child(row)

	var confirm := _make_hud_button("Confirm", COLOR_OK)
	confirm.pressed.connect(_on_preview_confirm_pressed)
	row.add_child(confirm)

	var cancel := _make_hud_button("Cancel", COLOR_ERR)
	cancel.pressed.connect(_on_preview_cancel_pressed)
	row.add_child(cancel)


func _on_preview_confirm_pressed() -> void:
	if _pending_build_command.is_empty():
		return
	var command_type := str(_pending_build_command.get("type", ""))
	var color := COLOR_CYAN if command_type in ["PurchaseTrain", "CreateSchedule", "BuildInternalConnection"] else COLOR_AMBER_HOT
	_send_pending_build(_pending_commit_status(), color)
	if command_type == "CreateSchedule":
		_clear_route_builder()
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


func _on_preview_cancel_pressed() -> void:
	_clear_pending_preview()
	_clear_route_builder()
	_clear_wire_builder()
	_set_status_text("%s · preview cancelled" % _active_tool_label().to_upper(), COLOR_STEEL)
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


func _pending_commit_status() -> String:
	var command_type := str(_pending_build_command.get("type", ""))
	match command_type:
		"BuildNode":
			return "Building %s..." % _kind_display(str(_pending_build_command.get("kind", "node")))
		"BuildLink":
			if str(_pending_build_command.get("mode", "")) == "gate":
				return "Building gate link %s -> %s..." % [str(_pending_build_command.get("origin", "")), str(_pending_build_command.get("destination", ""))]
			return "Building rail %s -> %s..." % [str(_pending_build_command.get("origin", "")), str(_pending_build_command.get("destination", ""))]
		"PurchaseTrain":
			return "Purchasing train at %s..." % str(_pending_build_command.get("node_id", ""))
		"CreateSchedule":
			return "Creating schedule %s..." % str(_pending_build_command.get("schedule_id", "route"))
		"BuildInternalConnection":
			return "Wiring %s.%s -> %s.%s..." % [
				str(_pending_build_command.get("source_component_id", "")),
				str(_pending_build_command.get("source_port_id", "")),
				str(_pending_build_command.get("destination_component_id", "")),
				str(_pending_build_command.get("destination_port_id", "")),
			]
		_:
			return "Committing preview..."


func _add_planner_line(label_text: String, value_text: String, value_color: Color) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	_queue_list.add_child(row)

	var label := Label.new()
	label.text = label_text
	label.add_theme_color_override("font_color", COLOR_STEEL)
	label.add_theme_font_size_override("font_size", 10)
	label.custom_minimum_size = Vector2(82, 0)
	row.add_child(label)

	var value := Label.new()
	value.text = value_text
	value.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	value.add_theme_color_override("font_color", value_color)
	value.add_theme_font_size_override("font_size", 10)
	value.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(value)


func _add_progress_bar(label_text: String, ratio: float, color: Color) -> void:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	_queue_list.add_child(row)

	var label := Label.new()
	label.text = label_text
	label.add_theme_color_override("font_color", COLOR_STEEL)
	label.add_theme_font_size_override("font_size", 10)
	label.custom_minimum_size = Vector2(82, 0)
	row.add_child(label)

	var bar := ProgressBar.new()
	bar.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	bar.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	bar.custom_minimum_size = Vector2(0, 8)
	bar.show_percentage = false
	bar.max_value = 1.0
	bar.value = ratio

	var bg := StyleBoxFlat.new()
	bg.bg_color = COLOR_BG_1
	var fg := StyleBoxFlat.new()
	fg.bg_color = color
	bar.add_theme_stylebox_override("background", bg)
	bar.add_theme_stylebox_override("fill", fg)
	row.add_child(bar)


func _add_planner_note(text: String, color: Color) -> void:
	if text.strip_edges().is_empty():
		return
	var note := Label.new()
	note.text = text
	note.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	note.add_theme_color_override("font_color", color)
	note.add_theme_font_size_override("font_size", 10)
	_queue_list.add_child(note)


func _make_hud_button(text: String, color: Color) -> Button:
	var button := Button.new()
	button.text = text
	button.focus_mode = Control.FOCUS_NONE
	button.add_theme_font_size_override("font_size", 11)
	button.add_theme_color_override("font_color", color)
	var style := StyleBoxFlat.new()
	style.bg_color = Color(color.r, color.g, color.b, 0.12)
	style.border_color = Color(color.r, color.g, color.b, 0.55)
	style.set_border_width_all(1)
	style.set_corner_radius_all(2)
	style.content_margin_left = 12
	style.content_margin_right = 12
	style.content_margin_top = 5
	style.content_margin_bottom = 5
	button.add_theme_stylebox_override("normal", style)
	button.add_theme_stylebox_override("hover", style)
	button.add_theme_stylebox_override("pressed", style)
	button.add_theme_stylebox_override("focus", style)
	return button


func _node_display_name(node_id: String) -> String:
	if node_id.is_empty():
		return "—"
	var nodes: Array = _latest_snapshot.get("nodes", [])
	for node in nodes:
		if typeof(node) != TYPE_DICTIONARY:
			continue
		if str(node.get("id", "")) == node_id:
			return "%s (%s)" % [str(node.get("name", node_id)), node_id]
	return node_id


func _make_hud_header(title: String, sub: String) -> Control:
	var row := HBoxContainer.new()
	var dot := ColorRect.new()
	dot.color = COLOR_AMBER
	dot.custom_minimum_size = Vector2(6, 6)
	dot.size_flags_vertical = Control.SIZE_SHRINK_CENTER
	row.add_child(dot)
	var spacer := Control.new()
	spacer.custom_minimum_size = Vector2(6, 0)
	row.add_child(spacer)
	var title_lbl := Label.new()
	title_lbl.text = title.to_upper()
	title_lbl.add_theme_color_override("font_color", COLOR_STEEL_2)
	title_lbl.add_theme_font_size_override("font_size", 10)
	title_lbl.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(title_lbl)
	var sub_lbl := Label.new()
	sub_lbl.text = sub
	sub_lbl.add_theme_color_override("font_color", COLOR_STEEL)
	sub_lbl.add_theme_font_size_override("font_size", 10)
	row.add_child(sub_lbl)
	row.set_meta("sub", sub_lbl)
	return row


# ---------- Status bar ----------

func _build_statusbar() -> void:
	_statusbar = _make_panel(Color(0.055, 0.114, 0.188, 0.90), COLOR_HAIR)
	_canvas_layer.add_child(_statusbar)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 16)
	margin.add_theme_constant_override("margin_right", 16)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	_statusbar.add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 12)
	margin.add_child(row)

	_statusbar_mode_chip = _make_chip("RAIL MODE · drag from source node", COLOR_AMBER_HOT)
	_statusbar_mode_label = _statusbar_mode_chip.get_meta("label") as Label
	row.add_child(_statusbar_mode_chip)

	var hotkeys := Label.new()
	hotkeys.text = "  R rail · N node · C wire · G gate · X demolish · WASD/arrows pan · MMB drag · wheel zoom · HOME reset · ESC cancel"
	hotkeys.add_theme_color_override("font_color", COLOR_STEEL)
	hotkeys.add_theme_font_size_override("font_size", 11)
	hotkeys.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(hotkeys)

	_statusbar_bridge_chip = _make_chip("BRIDGE · OFFLINE", COLOR_ERR)
	_statusbar_bridge_label = _statusbar_bridge_chip.get_meta("label") as Label
	row.add_child(_statusbar_bridge_chip)

	_update_status_mode_chip()


func _make_chip(text: String, color: Color) -> Control:
	var chip := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.078, 0.157, 0.259, 0.40)
	style.border_color = Color(color.r, color.g, color.b, 0.45)
	style.set_border_width_all(1)
	style.set_corner_radius_all(2)
	style.content_margin_left = 10
	style.content_margin_right = 10
	style.content_margin_top = 4
	style.content_margin_bottom = 4
	chip.add_theme_stylebox_override("panel", style)
	var lbl := Label.new()
	lbl.text = text
	lbl.add_theme_color_override("font_color", color)
	lbl.add_theme_font_size_override("font_size", 11)
	chip.add_child(lbl)
	chip.set_meta("label", lbl)
	chip.set_meta("color", color)
	return chip


func _update_status_mode_chip() -> void:
	if _statusbar_mode_label == null:
		return
	var text := ""
	var color := COLOR_STEEL_2
	match _active_tool:
		TOOL_SELECT: text = "SELECT · click to inspect"
		TOOL_PAN: text = "PAN · drag to move view"
		TOOL_RAIL: text = "RAIL MODE · drag from source node"; color = COLOR_AMBER_HOT
		TOOL_NODE: text = "PLACE NODE · 24-unit grid snap"; color = COLOR_AMBER_HOT
		TOOL_WIRE: text = "WIRE PORTS · drag output to input"; color = COLOR_CYAN
		TOOL_GATE: text = "GATE HUB · 24-unit grid snap"; color = COLOR_AMBER_HOT
		TOOL_TRAIN: text = "PURCHASE TRAIN · assign to route"; color = COLOR_CYAN
		TOOL_DEMOLISH: text = "DEMOLISH · click node or link"; color = COLOR_ERR
		TOOL_LAYERS: text = "LAYERS · toggle overlays"; color = COLOR_CYAN
	_statusbar_mode_label.text = text
	_statusbar_mode_label.add_theme_color_override("font_color", color)


func _update_bridge_chip(running: bool) -> void:
	if _statusbar_bridge_label == null:
		return
	if running:
		_statusbar_bridge_label.text = "BRIDGE · LIVE"
		_statusbar_bridge_label.add_theme_color_override("font_color", COLOR_OK)
	else:
		_statusbar_bridge_label.text = "BRIDGE · OFFLINE"
		_statusbar_bridge_label.add_theme_color_override("font_color", COLOR_ERR)


# ---------- Layout ----------

func _on_viewport_size_changed() -> void:
	_layout_ui()
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


func _layout_ui() -> void:
	var vs := get_viewport_rect().size
	if _topbar != null:
		_topbar.position = Vector2.ZERO
		_topbar.size = Vector2(vs.x, TOPBAR_HEIGHT)
		_topbar.custom_minimum_size = _topbar.size
	if _toolrail != null:
		_toolrail.position = Vector2(0, TOPBAR_HEIGHT)
		_toolrail.size = Vector2(TOOLRAIL_WIDTH, vs.y - TOPBAR_HEIGHT - STATUSBAR_HEIGHT)
		_toolrail.custom_minimum_size = _toolrail.size
	if _hud != null:
		_hud.position = Vector2(vs.x - HUD_WIDTH, TOPBAR_HEIGHT)
		_hud.size = Vector2(HUD_WIDTH, vs.y - TOPBAR_HEIGHT - STATUSBAR_HEIGHT)
		_hud.custom_minimum_size = _hud.size
	if _statusbar != null:
		_statusbar.position = Vector2(0, vs.y - STATUSBAR_HEIGHT)
		_statusbar.size = Vector2(vs.x, STATUSBAR_HEIGHT)
		_statusbar.custom_minimum_size = _statusbar.size
	if _canvas_panel != null:
		_canvas_panel.position = Vector2(TOOLRAIL_WIDTH, TOPBAR_HEIGHT)
		var sz := Vector2(
			max(240.0, vs.x - TOOLRAIL_WIDTH - HUD_WIDTH),
			max(200.0, vs.y - TOPBAR_HEIGHT - STATUSBAR_HEIGHT)
		)
		_canvas_panel.size = sz
		_canvas_rect = Rect2(_canvas_panel.position, sz)
		if _region_label != null:
			_region_label.position = Vector2(26, 28)
		if _region_meta != null:
			_region_meta.position = Vector2(26, 54)
	_update_stab_fill()


# ---------- Snapshot ----------

func _on_snapshot_received(snapshot: Dictionary) -> void:
	_ingest_command_results(snapshot)
	_apply_snapshot(snapshot)


func _ingest_command_results(snapshot: Dictionary) -> void:
	var bridge = snapshot.get("bridge", {})
	if typeof(bridge) != TYPE_DICTIONARY:
		return
	var results: Array = bridge.get("command_results", [])
	for result in results:
		if typeof(result) == TYPE_DICTIONARY:
			_handle_command_result(result)


func _handle_command_result(result: Dictionary) -> void:
	var command_type := str(result.get("type", ""))
	match command_type:
		"PreviewBuildNode":
			_handle_preview_result(result, "node")
		"PreviewBuildLink":
			var preview_kind := "gate_link" if _pending_preview_kind == "gate_link" or str(result.get("mode", "")) == "gate" else "rail"
			_handle_preview_result(result, preview_kind)
		"PreviewPurchaseTrain":
			_handle_preview_result(result, "train")
		"PreviewCreateSchedule":
			_handle_preview_result(result, "schedule")
		"PreviewBuildInternalConnection":
			_handle_preview_result(result, "internal_connection")
		"BuildNode", "BuildLink":
			var ok := bool(result.get("ok", false))
			if ok:
				var message := str(result.get("message", "construction complete"))
				_clear_pending_preview()
				_set_status_text("BUILT · %s" % message, COLOR_OK)
			else:
				_set_status_text("BUILD FAILED · %s" % str(result.get("message", "unknown")), COLOR_ERR)
		"DemolishLink":
			if bool(result.get("ok", false)):
				_set_status_text("DEMOLISHED · %s" % str(result.get("message", "link removed")), COLOR_OK)
		"PurchaseTrain":
			if bool(result.get("ok", false)):
				_clear_pending_preview()
				_set_status_text("TRAIN · %s" % str(result.get("message", "train purchased")), COLOR_OK)
		"CreateSchedule":
			if bool(result.get("ok", false)):
				_clear_pending_preview()
				_clear_route_builder()
				_set_status_text("ROUTE · %s" % str(result.get("message", "schedule created")), COLOR_OK)
		"BuildInternalConnection":
			if bool(result.get("ok", false)):
				_clear_pending_preview()
				_clear_wire_builder()
				_set_status_text("WIRE · %s" % str(result.get("message", "ports connected")), COLOR_OK)


func _handle_preview_result(result: Dictionary, preview_kind: String) -> void:
	_last_preview_result = result.duplicate(true)
	if not bool(result.get("ok", false)):
		_pending_build_command = {}
		_pending_preview_kind = preview_kind
		_pending_preview_target_id = str(result.get("target_id", ""))
		_set_status_text(_preview_summary(result), COLOR_ERR)
		_refresh_construction_hud()
		return
	var normalized = result.get("normalized_command", {})
	if typeof(normalized) != TYPE_DICTIONARY:
		_clear_pending_preview()
		_set_status_text("INVALID · backend preview missing normalized command", COLOR_ERR)
		return
	_pending_build_command = normalized.duplicate(true)
	_pending_preview_kind = preview_kind
	_pending_preview_target_id = str(result.get("target_id", ""))
	_set_status_text(_preview_summary(result), COLOR_OK)
	_refresh_construction_hud()


func _on_bridge_error(_message: String) -> void:
	_set_status_text("ERROR: %s" % _message, COLOR_ERR)


func _on_bridge_status_changed(running: bool) -> void:
	_update_bridge_chip(running)


func _apply_snapshot(snapshot: Dictionary) -> void:
	_latest_snapshot = snapshot
	var worlds: Array = snapshot.get("worlds", [])
	var prev_world_id := _world_id
	_selected_world = _find_world(worlds, _world_id)
	if _selected_world.is_empty() and not worlds.is_empty():
		_selected_world = worlds[0]
		_world_id = str(_selected_world.get("id", ""))

	# Regenerate terrain when world changes
	if _world_id != prev_world_id:
		_terrain_patches.clear()
		_terrain_zones.clear()
		_last_terrain_world_id = ""

	_world_nodes = []
	var nodes: Array = snapshot.get("nodes", [])
	_gate_hub_node_id = ""
	for n in nodes:
		if typeof(n) != TYPE_DICTIONARY:
			continue
		if str(n.get("world_id", "")) == _world_id:
			_world_nodes.append(n)
			if str(n.get("kind", "")) == "gate_hub" and _gate_hub_node_id == "":
				_gate_hub_node_id = str(n.get("id", ""))

	var node_ids := {}
	for n in _world_nodes:
		node_ids[str(n.get("id", ""))] = true
	_world_links = []
	var gate_link: Dictionary = {}
	var links: Array = snapshot.get("links", [])
	for link in links:
		if typeof(link) != TYPE_DICTIONARY:
			continue
		var origin_in: bool = node_ids.has(str(link.get("origin", "")))
		var dest_in: bool = node_ids.has(str(link.get("destination", "")))
		if origin_in and dest_in and str(link.get("mode", "rail")) == "rail":
			_world_links.append(link)
		if (origin_in or dest_in) and str(link.get("mode", "")) == "gate" and gate_link.is_empty():
			gate_link = link

	_update_topbar_stats(snapshot)
	_update_breadcrumb()
	_update_region_label()
	_update_planet_card()
	_update_inventory_list()
	_update_overlay_summary()
	_update_gate_card(gate_link)
	_refresh_construction_hud()
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


func _find_world(worlds: Array, world_id: String) -> Dictionary:
	for w in worlds:
		if typeof(w) == TYPE_DICTIONARY and str(w.get("id", "")) == world_id:
			return w
	return {}


func _update_topbar_stats(snapshot: Dictionary) -> void:
	var finance: Dictionary = snapshot.get("finance", {}) if typeof(snapshot.get("finance")) == TYPE_DICTIONARY else {}
	if _credits_value != null:
		var cash := float(finance.get("cash", 0.0))
		_credits_value.text = "₡ %s" % _format_commas(cash)
	if _power_value != null:
		var power: Dictionary = _selected_world.get("power", {}) if typeof(_selected_world.get("power")) == TYPE_DICTIONARY else {}
		var used := int(power.get("used", 0)) + int(power.get("gate_used", 0))
		var available := int(power.get("available", 0))
		_power_value.text = "%d / %d" % [used, available]
		var ratio := (float(used) / float(max(1, available)))
		if ratio > 0.9:
			_power_value.add_theme_color_override("font_color", COLOR_ERR)
		elif ratio > 0.7:
			_power_value.add_theme_color_override("font_color", COLOR_WARN)
		else:
			_power_value.add_theme_color_override("font_color", COLOR_OK)
	if _tick_value != null:
		_tick_value.text = "T+%05d" % int(snapshot.get("tick", 0))


func _update_breadcrumb() -> void:
	if _breadcrumb_label == null:
		return
	var world_name := str(_selected_world.get("name", _world_id)).to_upper() if _selected_world.size() > 0 else "—"
	_breadcrumb_label.text = "GALAXY › VESTA SECTOR › %s · LOCAL" % world_name


func _update_region_label() -> void:
	if _region_label == null or _region_meta == null:
		return
	var world_name := str(_selected_world.get("name", _world_id)).to_upper() if _selected_world.size() > 0 else "—"
	_region_label.text = "%s · LOCAL REGION" % world_name
	var tier_name := str(_selected_world.get("tier_name", "—")).to_upper().replace("_", " ")
	var pop := int(_selected_world.get("population", 0))
	_region_meta.text = "TIER: %s · POP: %s · GRID: 24 km²" % [tier_name, _format_commas(float(pop))]


func _update_planet_card() -> void:
	if _planet_name != null:
		_planet_name.text = str(_selected_world.get("name", "—")).to_upper() if _selected_world.size() > 0 else "—"
	if _planet_meta != null:
		var tier := int(_selected_world.get("tier", 0))
		var pop := int(_selected_world.get("population", 0))
		var stab := float(_selected_world.get("stability", 0.0))
		_planet_meta.text = "TIER T%d · POP %s · STAB %.2f" % [tier, _format_commas(float(pop)), stab]
	_update_stab_fill()


func _update_inventory_list() -> void:
	if _inventory_list == null:
		return
	for child in _inventory_list.get_children():
		child.queue_free()

	var totals := {}
	var rates := {}
	for node in _world_nodes:
		var inventory: Dictionary = node.get("inventory", {}) if typeof(node.get("inventory")) == TYPE_DICTIONARY else {}
		for key in inventory.keys():
			totals[key] = int(totals.get(key, 0)) + int(inventory[key])
		var production: Dictionary = node.get("production", {}) if typeof(node.get("production")) == TYPE_DICTIONARY else {}
		var demand: Dictionary = node.get("demand", {}) if typeof(node.get("demand")) == TYPE_DICTIONARY else {}
		for key in production.keys():
			rates[key] = int(rates.get(key, 0)) + int(production[key])
		for key in demand.keys():
			rates[key] = int(rates.get(key, 0)) - int(demand[key])

	var keys: Array = totals.keys()
	keys.sort()
	if _inventory_sub != null:
		_inventory_sub.text = "%d tracked" % keys.size()
	if keys.is_empty():
		var empty := Label.new()
		empty.text = "No cargo on this world yet."
		empty.add_theme_color_override("font_color", COLOR_STEEL)
		empty.add_theme_font_size_override("font_size", 11)
		_inventory_list.add_child(empty)
		return

	for key in keys:
		_inventory_list.add_child(_make_inventory_row(str(key), int(totals[key]), int(rates.get(key, 0))))


func _make_inventory_row(cargo: String, units: int, rate: int) -> Control:
	var row := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = Color(0.118, 0.227, 0.357, 0.22)
	style.border_color = COLOR_HAIR
	style.set_border_width_all(1)
	var accent := COLOR_STEEL
	if rate > 0:
		accent = COLOR_OK
	elif rate < 0:
		accent = COLOR_WARN
	style.border_color = accent
	style.border_width_left = 2
	style.content_margin_left = 8
	style.content_margin_right = 8
	style.content_margin_top = 5
	style.content_margin_bottom = 5
	row.add_theme_stylebox_override("panel", style)

	var h := HBoxContainer.new()
	h.add_theme_constant_override("separation", 10)
	row.add_child(h)

	var body := VBoxContainer.new()
	body.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	body.add_theme_constant_override("separation", 2)
	h.add_child(body)

	var name_lbl := Label.new()
	name_lbl.text = cargo.replace("_", " ").capitalize()
	name_lbl.add_theme_color_override("font_color", COLOR_ICE)
	name_lbl.add_theme_font_size_override("font_size", 12)
	body.add_child(name_lbl)

	var meta := Label.new()
	meta.text = "local · %d" % units
	meta.add_theme_color_override("font_color", COLOR_STEEL)
	meta.add_theme_font_size_override("font_size", 10)
	body.add_child(meta)

	var vals := VBoxContainer.new()
	vals.add_theme_constant_override("separation", 2)
	vals.alignment = BoxContainer.ALIGNMENT_END
	h.add_child(vals)

	var v := Label.new()
	v.text = _format_commas(float(units))
	v.add_theme_color_override("font_color", COLOR_ICE)
	v.add_theme_font_size_override("font_size", 11)
	v.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	vals.add_child(v)

	var d := Label.new()
	var sign := "+" if rate > 0 else ("" if rate < 0 else "±")
	d.text = "%s%d/t" % [sign, rate]
	d.add_theme_color_override("font_color", accent)
	d.add_theme_font_size_override("font_size", 10)
	d.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	vals.add_child(d)

	return row


func _update_gate_card(gate_link: Dictionary) -> void:
	if _gate_title_value == null:
		return
	for child in _gate_bars_box.get_children():
		child.queue_free()

	if _gate_hub_node_id == "":
		_gate_title_value.text = "NO GATE HUB"
		_gate_status_value.text = "offline"
		_gate_status_value.add_theme_color_override("font_color", COLOR_STEEL)
		var msg := Label.new()
		msg.text = "Build a Gate Hub to route cargo into the galaxy network."
		msg.add_theme_color_override("font_color", COLOR_STEEL)
		msg.add_theme_font_size_override("font_size", 10)
		msg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_gate_bars_box.add_child(msg)
		if _gate_linked_value != null:
			_gate_linked_value.text = "—"
		if _gate_activation_value != null:
			_gate_activation_value.text = "—"
		return

	if gate_link.is_empty():
		_gate_title_value.text = "UNLINKED GATE HUB"
		_gate_status_value.text = "ready"
		_gate_status_value.add_theme_color_override("font_color", COLOR_AMBER_HOT)
		var link_msg := Label.new()
		link_msg.text = "Gate hub exists locally. Select the Gate Hub tool and click it to preview an interworld gate link."
		link_msg.add_theme_color_override("font_color", COLOR_STEEL)
		link_msg.add_theme_font_size_override("font_size", 10)
		link_msg.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		_gate_bars_box.add_child(link_msg)
		_gate_bars_box.add_child(_make_gate_bar("Planned slots", 0, DEFAULT_GATE_CAPACITY_PER_TICK, "0 / %d" % DEFAULT_GATE_CAPACITY_PER_TICK))
		_gate_bars_box.add_child(_make_gate_bar("Power draw", DEFAULT_GATE_POWER_REQUIRED, DEFAULT_GATE_POWER_REQUIRED + 20, "%d mw" % DEFAULT_GATE_POWER_REQUIRED))
		if _gate_linked_value != null:
			_gate_linked_value.text = "pick external hub"
		if _gate_activation_value != null:
			_gate_activation_value.text = "preview required"
		return

	var link_id := str(gate_link.get("id", ""))
	var capacity := int(gate_link.get("capacity", 0))
	var base_capacity := int(gate_link.get("base_capacity", capacity))
	var slots_used := int(gate_link.get("slots_used", 0))
	var powered := bool(gate_link.get("powered", false))
	var power_required := int(gate_link.get("power_required", 0))
	var destination_id := str(gate_link.get("destination", ""))
	if destination_id == _gate_hub_node_id:
		destination_id = str(gate_link.get("origin", ""))

	var world_name := str(_selected_world.get("name", _world_id)).to_upper()
	_gate_title_value.text = "%s GATE" % world_name
	if powered and capacity > 0:
		_gate_status_value.text = "POWERED · active"
		_gate_status_value.add_theme_color_override("font_color", COLOR_OK)
	elif capacity > 0:
		_gate_status_value.text = "CHARGING"
		_gate_status_value.add_theme_color_override("font_color", COLOR_AMBER_HOT)
	else:
		_gate_status_value.text = "OFFLINE"
		_gate_status_value.add_theme_color_override("font_color", COLOR_ERR)

	_gate_bars_box.add_child(_make_gate_bar("Slot capacity", slots_used, max(1, capacity), "%d / %d" % [slots_used, capacity]))
	_gate_bars_box.add_child(_make_gate_bar("Link capacity", capacity, max(1, base_capacity), "%d / %d" % [capacity, base_capacity]))
	_gate_bars_box.add_child(_make_gate_bar("Power draw", power_required, max(1, power_required + 20), "%d mw" % power_required))

	if _gate_linked_value != null:
		var dest_world := _find_node_world(destination_id)
		_gate_linked_value.text = dest_world.to_upper() if dest_world != "" else destination_id.to_upper()
	if _gate_activation_value != null:
		var tick := int(_latest_snapshot.get("tick", 0))
		_gate_activation_value.text = "t+%d · queued" % (tick + 1) if powered else "awaiting power"


func _find_node_world(node_id: String) -> String:
	var nodes: Array = _latest_snapshot.get("nodes", []) if typeof(_latest_snapshot.get("nodes")) == TYPE_ARRAY else []
	for n in nodes:
		if typeof(n) == TYPE_DICTIONARY and str(n.get("id", "")) == node_id:
			var wid := str(n.get("world_id", ""))
			var worlds: Array = _latest_snapshot.get("worlds", []) if typeof(_latest_snapshot.get("worlds")) == TYPE_ARRAY else []
			for w in worlds:
				if typeof(w) == TYPE_DICTIONARY and str(w.get("id", "")) == wid:
					return str(w.get("name", wid))
			return wid
	return ""


func _make_gate_bar(label: String, value: int, max_value: int, value_text: String) -> Control:
	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	var lbl := Label.new()
	lbl.text = label
	lbl.add_theme_color_override("font_color", COLOR_STEEL_2)
	lbl.add_theme_font_size_override("font_size", 10)
	lbl.custom_minimum_size = Vector2(90, 0)
	row.add_child(lbl)

	var bar_bg := PanelContainer.new()
	bar_bg.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	var bg_style := StyleBoxFlat.new()
	bg_style.bg_color = Color(0.039, 0.078, 0.133, 0.7)
	bg_style.border_color = Color(0.953, 0.612, 0.071, 0.25)
	bg_style.set_border_width_all(1)
	bg_style.content_margin_top = 0
	bg_style.content_margin_bottom = 0
	bar_bg.add_theme_stylebox_override("panel", bg_style)
	bar_bg.custom_minimum_size = Vector2(0, 8)
	row.add_child(bar_bg)

	var fill := ColorRect.new()
	fill.color = COLOR_AMBER_HOT
	var ratio: float = clamp(float(value) / float(max(1, max_value)), 0.0, 1.0)
	fill.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	fill.anchor_right = ratio
	bar_bg.add_child(fill)

	var val_lbl := Label.new()
	val_lbl.text = value_text
	val_lbl.add_theme_color_override("font_color", COLOR_ICE)
	val_lbl.add_theme_font_size_override("font_size", 10)
	row.add_child(val_lbl)
	return row


# ---------- Helpers ----------

func _make_panel(bg: Color, border: Color) -> PanelContainer:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	style.bg_color = bg
	style.border_color = border
	style.set_border_width_all(1)
	panel.add_theme_stylebox_override("panel", style)
	return panel


func _format_commas(value: float) -> String:
	var n := int(round(value))
	var sign := ""
	if n < 0:
		sign = "-"
		n = -n
	var s := str(n)
	var out := ""
	var count := 0
	for i in range(s.length() - 1, -1, -1):
		out = s[i] + out
		count += 1
		if count == 3 and i > 0:
			out = "," + out
			count = 0
	return sign + out
