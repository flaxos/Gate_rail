extends Node2D

const TOPBAR_HEIGHT := 56.0
const TOOLRAIL_WIDTH := 64.0
const HUD_WIDTH := 360.0
const STATUSBAR_HEIGHT := 44.0

const CANVAS_PADDING := 10.0
const GRID_MICRO := 24.0
const GRID_MAJOR := 120.0

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

const TOOL_SELECT := "select"
const TOOL_PAN := "pan"
const TOOL_RAIL := "rail"
const TOOL_NODE := "node"
const TOOL_GATE := "gate"
const TOOL_TRAIN := "train"
const TOOL_DEMOLISH := "demolish"
const TOOL_LAYERS := "layers"

const TOOLS: Array = [
	{"id": TOOL_SELECT, "label": "Select", "key": "V", "group": "cursor"},
	{"id": TOOL_PAN, "label": "Pan", "key": "H", "group": "cursor"},
	{"id": TOOL_RAIL, "label": "Lay Rail", "key": "R", "group": "build"},
	{"id": TOOL_NODE, "label": "Place Node", "key": "N", "group": "build"},
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

# Build-tool state
var _build_node_kind: String = "depot"
var _rail_origin_id: String = ""
var _node_kind_popup: PopupMenu
var _cargo_kind_popup: PopupMenu
var _cargo_popup_options: Array = []
var _build_seq: int = 0
var _pending_node_local_pos: Vector2 = Vector2.ZERO
var _pending_build_command: Dictionary = {}
var _pending_preview_kind: String = ""
var _pending_preview_target_id: String = ""
var _last_preview_result: Dictionary = {}
var _route_train_id: String = ""
var _route_origin_id: String = ""
var _pending_route_dest_id: String = ""

# Inspection state (TOOL_SELECT)
var _selected_local_kind: String = ""
var _selected_local_id: String = ""

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
const NODE_HIT_RADIUS: float = 30.0
const LINK_HIT_DISTANCE: float = 12.0


func _ready() -> void:
	_world_id = String(SceneNav.selected_world_id)
	_build_ui()
	_build_node_kind_popup()
	_build_cargo_kind_popup()
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
	_request_schedule_preview(_route_train_id, origin_id, dest_id, cargo_id)


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
	if not key.pressed or key.echo:
		return
	if key.keycode == KEY_ESCAPE:
		_cancel_all("preview cancelled")
		get_viewport().set_input_as_handled()


func _cancel_all(reason: String = "") -> void:
	var had_state := not (_pending_build_command.is_empty() and _last_preview_result.is_empty()
		and _pending_preview_kind.is_empty() and _rail_origin_id.is_empty()
		and _route_train_id.is_empty() and _selected_local_id.is_empty()
		and _pending_route_dest_id.is_empty())
	_pending_build_command = {}
	_pending_preview_kind = ""
	_pending_preview_target_id = ""
	_last_preview_result = {}
	_rail_origin_id = ""
	_route_train_id = ""
	_route_origin_id = ""
	_pending_route_dest_id = ""
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
	if not (event is InputEventMouseButton):
		return
	var mb := event as InputEventMouseButton
	if not mb.pressed or mb.button_index != MOUSE_BUTTON_LEFT:
		return

	# Convert screen position to canvas-local position
	var screen_pos := mb.position
	if _canvas_rect.size.x <= 0 or _canvas_rect.size.y <= 0:
		return
	var local_pos := screen_pos - _canvas_rect.position
	if local_pos.x < 0 or local_pos.y < 0 or local_pos.x > _canvas_rect.size.x or local_pos.y > _canvas_rect.size.y:
		return

	match _active_tool:
		TOOL_SELECT:
			_handle_select_click(local_pos)
			get_viewport().set_input_as_handled()
		TOOL_NODE:
			_handle_place_node_click(local_pos)
			get_viewport().set_input_as_handled()
		TOOL_RAIL:
			_handle_rail_click(local_pos)
			get_viewport().set_input_as_handled()
		TOOL_GATE:
			_handle_gate_click(local_pos)
			get_viewport().set_input_as_handled()
		TOOL_TRAIN:
			_handle_train_click(local_pos)
			get_viewport().set_input_as_handled()
		TOOL_DEMOLISH:
			_handle_demolish_click(local_pos)
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


# --- Place Node ---
func _handle_place_node_click(local_pos: Vector2) -> void:
	if _pending_preview_kind == "node" and not _pending_build_command.is_empty():
		_send_pending_build("Building %s..." % _pending_build_command.get("kind", "node"), COLOR_AMBER_HOT)
		return
	_clear_pending_preview()
	_pending_node_local_pos = local_pos
	_node_kind_popup.position = Vector2i(get_viewport().get_mouse_position())
	_node_kind_popup.popup()


func _request_node_preview(kind: String, local_pos: Vector2) -> void:
	if _world_id.is_empty():
		_set_status_text("Cannot build without a selected world.", COLOR_ERR)
		return
	var node_id := _next_build_id(kind)
	var node_name := "%s %s" % [_world_id.capitalize(), _kind_display(kind)]
	var command := {
		"type": "PreviewBuildNode",
		"node_id": node_id,
		"world_id": _world_id,
		"kind": kind,
		"name": node_name,
		"layout": {"x": local_pos.x, "y": local_pos.y},
	}
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
	_refresh_construction_hud()



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
	_clear_pending_preview()
	_pending_node_local_pos = local_pos
	_request_node_preview("gate_hub", local_pos)


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


func _request_schedule_preview(train_id: String, origin_id: String, destination_id: String, cargo_type: String = "") -> void:
	var schedule_id := _next_build_id("schedule")
	if cargo_type.is_empty():
		cargo_type = _suggest_cargo_for_route(origin_id, destination_id)
	var units: int = min(DEFAULT_TRAIN_CAPACITY, _train_capacity(train_id))
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
			"interval_ticks": DEFAULT_ROUTE_INTERVAL_TICKS,
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
		if _canvas_panel != null:
			_canvas_panel.queue_redraw()
		return

	_active_tool = tool_id
	_rail_origin_id = ""
	_pending_route_dest_id = ""
	if tool_id != TOOL_SELECT:
		_selected_local_kind = ""
		_selected_local_id = ""
	if _cargo_kind_popup != null and _cargo_kind_popup.visible:
		_cargo_kind_popup.hide()
	_clear_pending_preview()
	_clear_route_builder()
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

	_draw_terrain(size)
	_draw_grid(size)
	_draw_corner_brackets(size)
	_draw_compass(size)
	_draw_scalebar(size)

	_draw_links_and_nodes(size)
	_draw_trains(size)
	_draw_build_preview(size)


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

	# Voronoi approximation: place seed centroids then fill grid cells
	const CELL := 40.0
	var num_seeds := 14
	var seeds_pos: Array = []
	var seeds_col: Array = []
	for i in range(num_seeds):
		seeds_pos.append(Vector2(rng.randf_range(0, canvas_size.x), rng.randf_range(0, canvas_size.y)))
		var t := rng.randf()
		seeds_col.append(base_col.lerp(accent_col, t))

	var cx := 0.0
	while cx < canvas_size.x:
		var cy := 0.0
		while cy < canvas_size.y:
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

	# Generate zone blobs
	var zone_types := ["water", "farm", "industry", "hazard", "farm", "water"]
	for zt in zone_types:
		var zpos := Vector2(rng.randf_range(80, canvas_size.x - 80), rng.randf_range(80, canvas_size.y - 80))
		var zrad := rng.randf_range(60, 140)
		_terrain_zones.append({"pos": zpos, "radius": zrad, "type": zt, "color": zone_cols.get(zt, Color.TRANSPARENT)})


func _draw_terrain(size: Vector2) -> void:
	if _terrain_patches.is_empty():
		_generate_terrain(size)

	for patch in _terrain_patches:
		_canvas_panel.draw_rect(Rect2(patch["pos"], patch["size"]), patch["color"], true)

	# Subtle wash on top for depth
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
	var x := 0.0
	while x < size.x:
		_canvas_panel.draw_line(Vector2(x, 0), Vector2(x, size.y), micro_color, 1.0)
		x += GRID_MICRO
	var y := 0.0
	while y < size.y:
		_canvas_panel.draw_line(Vector2(0, y), Vector2(size.x, y), micro_color, 1.0)
		y += GRID_MICRO
	x = 0.0
	while x < size.x:
		_canvas_panel.draw_line(Vector2(x, 0), Vector2(x, size.y), major_color, 1.0)
		x += GRID_MAJOR
	y = 0.0
	while y < size.y:
		_canvas_panel.draw_line(Vector2(0, y), Vector2(size.x, y), major_color, 1.0)
		y += GRID_MAJOR


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
	# Rubber-band line to mouse
	var mouse_screen := get_viewport().get_mouse_position()
	var mouse_local := mouse_screen - _canvas_rect.position
	_canvas_panel.draw_line(origin_pos, mouse_local, Color(line_color.r, line_color.g, line_color.b, 0.5), 3.0)
	var preview_text := default_text
	var preview_color := COLOR_AMBER_HOT
	if not _last_preview_result.is_empty():
		preview_text = _preview_summary(_last_preview_result)
		preview_color = COLOR_OK if bool(_last_preview_result.get("ok", false)) else COLOR_ERR
	var font := ThemeDB.fallback_font
	_canvas_panel.draw_string(font, mouse_local + Vector2(14, -8), preview_text, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, preview_color)


func _preview_summary(result: Dictionary) -> String:
	if result.is_empty():
		return "backend preview pending"
	if not bool(result.get("ok", false)):
		return "INVALID · %s" % str(result.get("reason", result.get("message", "blocked")))
	var result_type := str(result.get("type", ""))
	if result_type == "PreviewCreateSchedule":
		var route_ticks := int(result.get("route_travel_ticks", 0))
		return "VALID ROUTE · %d ticks · click destination again" % route_ticks
	var cost := int(round(float(result.get("cost", 0.0))))
	var travel_ticks := int(result.get("travel_ticks", 0))
	if travel_ticks > 0:
		return "VALID · %d ticks · $%d · click again to build" % [travel_ticks, cost]
	if result_type == "PreviewPurchaseTrain":
		return "VALID TRAIN · $%d · click node again" % cost
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
		return
	var center := size * 0.5
	var radius: float = min(size.x, size.y) * 0.32
	var count := _world_nodes.size()
	var idx := 0
	for node in _world_nodes:
		var node_id := str(node.get("id", ""))
		var layout_data = node.get("layout", null)
		if typeof(layout_data) == TYPE_DICTIONARY:
			_node_positions[node_id] = Vector2(float(layout_data.get("x", 0.0)), float(layout_data.get("y", 0.0)))
			idx += 1
			continue
		var angle: float = -PI / 2.0 + (TAU * float(idx) / float(max(1, count)))
		var pos := center + Vector2(cos(angle), sin(angle)) * radius
		if node_id == _gate_hub_node_id:
			pos = center + Vector2(radius * 0.72, -radius * 0.05)
		_node_positions[node_id] = pos
		idx += 1


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
	if not _route_train_id.is_empty():
		_add_planner_line("Route Train", _route_train_id, COLOR_CYAN)
		_add_planner_line("Origin", _node_display_name(_route_origin_id), COLOR_ICE)
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

	var normalized = result.get("normalized_command", {})
	if typeof(normalized) == TYPE_DICTIONARY:
		_add_normalized_command_details(normalized)


func _add_normalized_command_details(command: Dictionary) -> void:
	var command_type := str(command.get("type", ""))
	match command_type:
		"BuildNode":
			_add_planner_line("Kind", _kind_display(str(command.get("kind", "node"))), COLOR_ICE)
			var layout = command.get("layout", {})
			if typeof(layout) == TYPE_DICTIONARY:
				_add_planner_line("Layout", "%.0f, %.0f" % [float(layout.get("x", 0.0)), float(layout.get("y", 0.0))], COLOR_STEEL_2)
		"BuildLink":
			_add_planner_line("From", _node_display_name(str(command.get("origin", ""))), COLOR_ICE)
			_add_planner_line("To", _node_display_name(str(command.get("destination", ""))), COLOR_ICE)
		"PurchaseTrain":
			_add_planner_line("Node", _node_display_name(str(command.get("node_id", ""))), COLOR_ICE)
		"CreateSchedule":
			_add_planner_line("Train", str(command.get("train_id", "")), COLOR_CYAN)
			_add_planner_line("From", _node_display_name(str(command.get("origin", ""))), COLOR_ICE)
			_add_planner_line("To", _node_display_name(str(command.get("destination", ""))), COLOR_ICE)
			_add_planner_line("Cargo", str(command.get("cargo_type", "")).replace("_", " "), COLOR_AMBER_HOT)
			_add_planner_line("Units", "%d every %d ticks" % [int(command.get("units_per_departure", 0)), int(command.get("interval_ticks", 0))], COLOR_STEEL_2)


func _add_idle_planner_guidance() -> void:
	match _active_tool:
		TOOL_NODE:
			_add_planner_note("Click an empty local tile, choose a node type, then confirm after backend preview.", COLOR_STEEL)
		TOOL_GATE:
			_add_planner_note("Click a local tile to preview a gate hub. Interworld gate links are deferred.", COLOR_STEEL)
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
	var links_here := _link_ids_touching(node_id)
	if not links_here.is_empty():
		_add_planner_line("Links", ", ".join(links_here), COLOR_STEEL_2)


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
	var color := COLOR_CYAN if command_type in ["PurchaseTrain", "CreateSchedule"] else COLOR_AMBER_HOT
	_send_pending_build(_pending_commit_status(), color)
	if command_type == "CreateSchedule":
		_clear_route_builder()
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


func _on_preview_cancel_pressed() -> void:
	_clear_pending_preview()
	_clear_route_builder()
	_set_status_text("%s · preview cancelled" % _active_tool_label().to_upper(), COLOR_STEEL)
	if _canvas_panel != null:
		_canvas_panel.queue_redraw()


func _pending_commit_status() -> String:
	var command_type := str(_pending_build_command.get("type", ""))
	match command_type:
		"BuildNode":
			return "Building %s..." % _kind_display(str(_pending_build_command.get("kind", "node")))
		"BuildLink":
			return "Building rail %s -> %s..." % [str(_pending_build_command.get("origin", "")), str(_pending_build_command.get("destination", ""))]
		"PurchaseTrain":
			return "Purchasing train at %s..." % str(_pending_build_command.get("node_id", ""))
		"CreateSchedule":
			return "Creating schedule %s..." % str(_pending_build_command.get("schedule_id", "route"))
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
	hotkeys.text = "  R rail · N node · G gate · X demolish · SHIFT straight · ESC cancel"
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
		TOOL_NODE: text = "PLACE NODE · click empty tile"; color = COLOR_AMBER_HOT
		TOOL_GATE: text = "GATE HUB · requires clear platform"; color = COLOR_AMBER_HOT
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
			_handle_preview_result(result, "rail")
		"PreviewPurchaseTrain":
			_handle_preview_result(result, "train")
		"PreviewCreateSchedule":
			_handle_preview_result(result, "schedule")
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

	if gate_link.is_empty() or _gate_hub_node_id == "":
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
