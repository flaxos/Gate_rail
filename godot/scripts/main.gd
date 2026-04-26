extends Node2D

const WORLD_RADIUS := 48.0
const NODE_RADIUS := 8.0
const ASSET_DIR := "res://assets/placeholders/"
const UI_MARGIN := 16.0
const UI_GAP := 14.0
const LEFT_PANEL_WIDTH := 560.0
const RIGHT_PANEL_WIDTH := 500.0
const CONTROL_PANEL_HEIGHT := 320.0
const ALERT_STRIP_HEIGHT := 46.0
const MIN_CENTER_MAP_WIDTH := 360.0
const MAP_INSET := Vector2(92, 96)
const MAX_ALERT_HISTORY := 8
const MAX_ALERT_MESSAGE_LENGTH := 86
const AUTO_STEP_INTERVAL := 0.75
const TRAIN_PICK_RADIUS := 18.0
const NODE_PICK_RADIUS := 18.0
const WORLD_PICK_RADIUS := 52.0
const LINK_PICK_DISTANCE := 10.0
const PLACEHOLDER_ASSETS := [
	"world_core.svg",
	"world_frontier.svg",
	"world_outpost.svg",
	"node_depot.svg",
	"node_settlement.svg",
	"node_extractor.svg",
	"node_industry.svg",
	"node_gate_hub.svg",
	"train_freight.svg",
	"train_passenger.svg",
	"train_blocked.svg",
	"cargo_food.svg",
	"cargo_ore.svg",
	"cargo_construction_materials.svg",
	"cargo_medical_supplies.svg",
	"cargo_parts.svg",
	"cargo_research_equipment.svg",
	"ui_cancel.svg",
	"ui_cash.svg",
	"ui_contract.svg",
	"ui_dispatch.svg",
	"ui_pause.svg",
	"ui_play.svg",
	"ui_refresh.svg",
	"ui_reputation.svg",
	"ui_schedule_off.svg",
	"ui_schedule_on.svg",
	"ui_step.svg",
	"ui_warning.svg",
]

var snapshot: Dictionary = {}
var world_positions: Dictionary = {}
var node_positions: Dictionary = {}
var _textures: Dictionary = {}

var _control_panel: PanelContainer
var _operations_panel: PanelContainer
var _inspector_panel: PanelContainer
var _alert_panel: PanelContainer
var _schedule_scroll: ScrollContainer
var _contract_scroll: ScrollContainer
var _order_scroll: ScrollContainer
var _alert_scroll: ScrollContainer
var _hud_tick_value: Label
var _hud_cash_value: Label
var _hud_reputation_value: Label
var _bridge_status_value: Label
var _bridge_source_value: Label
var _schedule_filter: LineEdit
var _schedule_sort: OptionButton
var _error_label: Label
var _play_button: Button
var _run_status_label: Label
var _inspector_label: Label
var _view_local_region_button: Button
var _schedule_list: VBoxContainer
var _finance_label: Label
var _contract_list: VBoxContainer
var _order_list: VBoxContainer
var _alert_strip: HBoxContainer
var _dispatch_order_id: LineEdit
var _dispatch_train: OptionButton
var _dispatch_origin: OptionButton
var _dispatch_destination: OptionButton
var _dispatch_cargo: OptionButton
var _dispatch_units: SpinBox
var _dispatch_priority: SpinBox
var _alert_history: Array = []
var _auto_step_timer: Timer
var _auto_running := false
var _auto_step_pending := false
var _bridge_running := false
var _manual_order_sequence := 1
var _last_command_signature := ""
var _selected_kind := ""
var _selected_id := ""
var _map_rect := Rect2(Vector2(600, 76), Vector2(620, 520))
var _node_orbit_radius := 82.0
var _camera: Camera2D
var _is_panning := false


func _ready() -> void:
	_camera = Camera2D.new()
	add_child(_camera)
	RenderingServer.set_default_clear_color(Color(0.055, 0.075, 0.08, 1.0))
	_load_placeholder_assets()
	_build_ui()
	_build_auto_step_timer()
	get_viewport().size_changed.connect(_on_viewport_size_changed)
	GateRailBridge.snapshot_received.connect(_on_snapshot_received)
	GateRailBridge.bridge_error.connect(_on_bridge_error)
	GateRailBridge.bridge_status_changed.connect(_on_bridge_status_changed)

	var fixture := GateRailBridge.load_fixture_snapshot()
	if not fixture.is_empty():
		_on_snapshot_received(fixture)
	_request_live_snapshot.call_deferred()


func _unhandled_input(event: InputEvent) -> void:
	if event is InputEventMouseButton:
		var mouse_event := event as InputEventMouseButton
		if mouse_event.button_index == MOUSE_BUTTON_WHEEL_UP and mouse_event.pressed:
			_camera.zoom *= 1.1
			get_viewport().set_input_as_handled()
		elif mouse_event.button_index == MOUSE_BUTTON_WHEEL_DOWN and mouse_event.pressed:
			_camera.zoom /= 1.1
			get_viewport().set_input_as_handled()
		elif mouse_event.button_index == MOUSE_BUTTON_RIGHT or mouse_event.button_index == MOUSE_BUTTON_MIDDLE:
			_is_panning = mouse_event.pressed
			get_viewport().set_input_as_handled()
		elif mouse_event.button_index == MOUSE_BUTTON_LEFT and mouse_event.pressed:
			var global_pos = get_global_mouse_position()
			if _select_at_position(global_pos):
				get_viewport().set_input_as_handled()

	elif event is InputEventMouseMotion and _is_panning:
		var motion := event as InputEventMouseMotion
		_camera.position -= motion.relative / _camera.zoom
		get_viewport().set_input_as_handled()


func _build_ui() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)

	_build_control_panel(ui)
	_build_operations_panel(ui)
	_build_inspector_panel(ui)
	_build_alert_strip(ui)
	_layout_ui()


func _build_control_panel(ui: CanvasLayer) -> void:
	_control_panel = PanelContainer.new()
	_control_panel.custom_minimum_size = Vector2(LEFT_PANEL_WIDTH, CONTROL_PANEL_HEIGHT)
	ui.add_child(_control_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	_control_panel.add_child(margin)

	var box := VBoxContainer.new()
	margin.add_child(box)

	var top_panel = PanelContainer.new()
	var top_style = StyleBoxFlat.new()
	top_style.bg_color = Color(0.12, 0.14, 0.16)
	top_style.set_border_width_all(1)
	top_style.border_color = Color(0.2, 0.25, 0.3)
	top_style.set_corner_radius_all(6)
	top_panel.add_theme_stylebox_override("panel", top_style)
	box.add_child(top_panel)

	var top_margin = MarginContainer.new()
	top_margin.add_theme_constant_override("margin_left", 8)
	top_margin.add_theme_constant_override("margin_top", 8)
	top_margin.add_theme_constant_override("margin_right", 8)
	top_margin.add_theme_constant_override("margin_bottom", 8)
	top_panel.add_child(top_margin)

	var top_grid = GridContainer.new()
	top_grid.columns = 4
	top_grid.add_theme_constant_override("h_separation", 16)
	top_grid.add_theme_constant_override("v_separation", 4)
	top_margin.add_child(top_grid)

	var add_hud_item = func(label_text: String) -> Label:
		var lbl = Label.new()
		lbl.text = label_text
		lbl.modulate = Color(0.6, 0.7, 0.75)
		top_grid.add_child(lbl)
		var val = Label.new()
		val.text = "-"
		top_grid.add_child(val)
		return val

	_hud_tick_value = add_hud_item.call("Tick:")
	_hud_cash_value = add_hud_item.call("Cash:")
	_hud_reputation_value = add_hud_item.call("Reputation:")
	_bridge_status_value = add_hud_item.call("Bridge:")
	_bridge_source_value = add_hud_item.call("Source:")

	var row := HBoxContainer.new()
	box.add_child(row)

	var refresh_button := Button.new()
	refresh_button.text = "Refresh live snapshot"
	_set_button_icon(refresh_button, "ui_refresh.svg")
	refresh_button.pressed.connect(_on_refresh_pressed)
	row.add_child(refresh_button)

	var step_button := Button.new()
	step_button.text = "Step 1 tick"
	_set_button_icon(step_button, "ui_step.svg")
	step_button.pressed.connect(_on_step_pressed)
	row.add_child(step_button)

	_play_button = Button.new()
	_play_button.text = "Play"
	_set_button_icon(_play_button, "ui_play.svg")
	_play_button.pressed.connect(_on_play_pause_pressed)
	row.add_child(_play_button)

	_error_label = Label.new()
	_error_label.text = "Fixture snapshot loaded until live bridge responds."
	box.add_child(_error_label)

	_run_status_label = Label.new()
	_run_status_label.text = "Auto-run stopped."
	_run_status_label.modulate = Color(0.72, 0.82, 0.84)
	box.add_child(_run_status_label)

	var sched_header = HBoxContainer.new()
	sched_header.add_theme_constant_override("separation", 16)

	var schedule_title := Label.new()
	schedule_title.text = "Schedules"
	sched_header.add_child(schedule_title)

	_schedule_filter = LineEdit.new()
	_schedule_filter.placeholder_text = "Filter..."
	_schedule_filter.custom_minimum_size = Vector2(120, 0)
	_schedule_filter.text_changed.connect(func(_text): _rebuild_schedule_list())
	sched_header.add_child(_schedule_filter)

	_schedule_sort = OptionButton.new()
	_schedule_sort.add_item("Sort: Next Tick")
	_schedule_sort.add_item("Sort: ID")
	_schedule_sort.add_item("Sort: Origin")
	_schedule_sort.item_selected.connect(func(_idx): _rebuild_schedule_list())
	sched_header.add_child(_schedule_sort)

	box.add_child(sched_header)

	_schedule_scroll = ScrollContainer.new()
	_schedule_scroll.custom_minimum_size = Vector2(520, 160)
	box.add_child(_schedule_scroll)

	_schedule_list = VBoxContainer.new()
	_schedule_scroll.add_child(_schedule_list)


func _build_operations_panel(ui: CanvasLayer) -> void:
	_operations_panel = PanelContainer.new()
	_operations_panel.custom_minimum_size = Vector2(RIGHT_PANEL_WIDTH, 640)
	ui.add_child(_operations_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	_operations_panel.add_child(margin)

	var box := VBoxContainer.new()
	margin.add_child(box)

	var finance_title := Label.new()
	finance_title.text = "Finance and Reputation"
	box.add_child(finance_title)

	_finance_label = Label.new()
	_finance_label.text = "Waiting for snapshot..."
	box.add_child(_finance_label)

	var contract_title := Label.new()
	contract_title.text = "Contracts"
	box.add_child(contract_title)

	_contract_scroll = ScrollContainer.new()
	_contract_scroll.custom_minimum_size = Vector2(460, 125)
	box.add_child(_contract_scroll)

	_contract_list = VBoxContainer.new()
	_contract_scroll.add_child(_contract_list)

	var dispatch_title := Label.new()
	dispatch_title.text = "Dispatch One-Shot Order"
	box.add_child(dispatch_title)

	var form := GridContainer.new()
	form.columns = 2
	box.add_child(form)

	_dispatch_order_id = _add_line_edit_row(form, "Order id", "blank = auto")
	_dispatch_train = _add_option_row(form, "Train")
	_dispatch_origin = _add_option_row(form, "Origin")
	_dispatch_destination = _add_option_row(form, "Destination")
	_dispatch_cargo = _add_option_row(form, "Cargo")
	_dispatch_units = _add_spin_row(form, "Units", 1, 200, 1, 4)
	_dispatch_priority = _add_spin_row(form, "Priority", 1, 999, 1, 100)

	var dispatch_button := Button.new()
	dispatch_button.text = "Queue DispatchOrder"
	_set_button_icon(dispatch_button, "ui_dispatch.svg")
	dispatch_button.pressed.connect(_on_dispatch_pressed)
	box.add_child(dispatch_button)

	var order_title := Label.new()
	order_title.text = "Pending Orders"
	box.add_child(order_title)

	_order_scroll = ScrollContainer.new()
	_order_scroll.custom_minimum_size = Vector2(460, 145)
	box.add_child(_order_scroll)

	_order_list = VBoxContainer.new()
	_order_scroll.add_child(_order_list)


func _build_inspector_panel(ui: CanvasLayer) -> void:
	_inspector_panel = PanelContainer.new()
	_inspector_panel.custom_minimum_size = Vector2(LEFT_PANEL_WIDTH, 296)
	ui.add_child(_inspector_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	_inspector_panel.add_child(margin)

	var box := VBoxContainer.new()
	margin.add_child(box)

	var title := Label.new()
	title.text = "Inspector"
	box.add_child(title)

	_inspector_label = Label.new()
	_inspector_label.text = "Click a world, node, link, or train on the map."
	_inspector_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_inspector_label.custom_minimum_size = Vector2(520, 230)
	box.add_child(_inspector_label)

	_view_local_region_button = Button.new()
	_view_local_region_button.text = "View Local Region"
	_view_local_region_button.visible = false
	_view_local_region_button.pressed.connect(_on_view_local_region_pressed)
	box.add_child(_view_local_region_button)


func _build_alert_strip(ui: CanvasLayer) -> void:
	_alert_panel = PanelContainer.new()
	_alert_panel.custom_minimum_size = Vector2(1248, ALERT_STRIP_HEIGHT)
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.035, 0.055, 0.07, 0.94)
	panel_style.border_color = Color(0.24, 0.38, 0.42)
	panel_style.set_border_width_all(1)
	panel_style.set_corner_radius_all(10)
	_alert_panel.add_theme_stylebox_override("panel", panel_style)
	ui.add_child(_alert_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_top", 7)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_bottom", 7)
	_alert_panel.add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	margin.add_child(row)

	var title := Label.new()
	title.text = "Status"
	title.custom_minimum_size = Vector2(58, 0)
	title.modulate = Color(0.70, 0.88, 0.86)
	row.add_child(title)

	_alert_scroll = ScrollContainer.new()
	_alert_scroll.custom_minimum_size = Vector2(1158, 32)
	_alert_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(_alert_scroll)

	_alert_strip = HBoxContainer.new()
	_alert_strip.add_theme_constant_override("separation", 6)
	_alert_scroll.add_child(_alert_strip)
	_rebuild_alert_strip()


func _build_auto_step_timer() -> void:
	_auto_step_timer = Timer.new()
	_auto_step_timer.wait_time = AUTO_STEP_INTERVAL
	_auto_step_timer.one_shot = false
	_auto_step_timer.timeout.connect(_on_auto_step_timeout)
	add_child(_auto_step_timer)


func _on_viewport_size_changed() -> void:
	_layout_ui()
	_rebuild_positions()
	queue_redraw()


func _layout_ui() -> void:
	var view_size := get_viewport_rect().size
	var left_width: float = clampf(view_size.x * 0.30, 420.0, LEFT_PANEL_WIDTH)
	var right_width: float = clampf(view_size.x * 0.28, 360.0, RIGHT_PANEL_WIDTH)
	var alert_width: float = max(480.0, view_size.x - (UI_MARGIN * 2.0))
	var alert_y: float = max(UI_MARGIN, view_size.y - UI_MARGIN - ALERT_STRIP_HEIGHT)
	var full_side_layout := view_size.x >= (
		left_width + right_width + MIN_CENTER_MAP_WIDTH + (UI_MARGIN * 2.0) + (UI_GAP * 2.0)
	)

	if _alert_panel != null:
		_alert_panel.position = Vector2(UI_MARGIN, alert_y)
		_alert_panel.size = Vector2(alert_width, ALERT_STRIP_HEIGHT)
		_alert_panel.custom_minimum_size = Vector2(alert_width, ALERT_STRIP_HEIGHT)
	if _alert_scroll != null:
		_alert_scroll.custom_minimum_size = Vector2(max(240.0, alert_width - 90.0), 32.0)

	if full_side_layout:
		var available_height: float = max(300.0, alert_y - UI_MARGIN - UI_GAP)
		var left_x := UI_MARGIN
		var top_y := UI_MARGIN
		var inspector_y := top_y + CONTROL_PANEL_HEIGHT + UI_GAP

		_place_panel(_control_panel, Vector2(left_x, top_y), Vector2(left_width, CONTROL_PANEL_HEIGHT))

		var inspector_height: float = max(220.0, alert_y - inspector_y - UI_GAP)
		var right_height: float = available_height
		var right_x: float = view_size.x - UI_MARGIN - right_width

		_place_panel(_inspector_panel, Vector2(left_x, inspector_y), Vector2(left_width, inspector_height))
		_place_panel(_operations_panel, Vector2(right_x, top_y), Vector2(right_width, right_height))
		_map_rect = Rect2(
			Vector2(left_x + left_width + UI_GAP, UI_MARGIN),
			Vector2(max(MIN_CENTER_MAP_WIDTH, right_x - (left_x + left_width) - (UI_GAP * 2.0)), max(260.0, alert_y - UI_MARGIN - UI_GAP))
		)
	else:
		var fallback_right_x: float = max(UI_MARGIN, view_size.x - UI_MARGIN - right_width)
		if view_size.x >= 1280.0:
			fallback_right_x = min(760.0, fallback_right_x)
		_place_panel(_control_panel, Vector2(UI_MARGIN, UI_MARGIN), Vector2(left_width, CONTROL_PANEL_HEIGHT))

		var inspector_y := UI_MARGIN + CONTROL_PANEL_HEIGHT + UI_GAP

		_place_panel(_inspector_panel, Vector2(UI_MARGIN, inspector_y), Vector2(left_width, max(220.0, alert_y - inspector_y - UI_GAP)))
		_place_panel(_operations_panel, Vector2(fallback_right_x, UI_MARGIN), Vector2(right_width, max(420.0, alert_y - UI_MARGIN - UI_GAP)))
		_map_rect = Rect2(
			Vector2(left_width + (UI_MARGIN * 2.0) + UI_GAP, UI_MARGIN),
			Vector2(max(280.0, fallback_right_x - left_width - (UI_MARGIN * 3.0) - (UI_GAP * 2.0)), max(260.0, alert_y - UI_MARGIN - UI_GAP))
		)

	if _schedule_scroll != null:
		_schedule_scroll.custom_minimum_size = Vector2(left_width - 40.0, 160.0)
	if _inspector_label != null:
		_inspector_label.custom_minimum_size = Vector2(left_width - 40.0, max(140.0, _panel_height(_inspector_panel) - 58.0))
	if _contract_scroll != null:
		_contract_scroll.custom_minimum_size = Vector2(right_width - 40.0, 125.0)
	if _order_scroll != null:
		_order_scroll.custom_minimum_size = Vector2(right_width - 40.0, 145.0)


func _place_panel(panel: PanelContainer, position: Vector2, size: Vector2) -> void:
	if panel == null:
		return
	panel.position = position
	panel.size = size
	panel.custom_minimum_size = size


func _panel_height(panel: PanelContainer) -> float:
	if panel == null:
		return 0.0
	return panel.size.y


func _add_line_edit_row(form: GridContainer, label_text: String, placeholder: String) -> LineEdit:
	var label := Label.new()
	label.text = label_text
	form.add_child(label)

	var edit := LineEdit.new()
	edit.placeholder_text = placeholder
	form.add_child(edit)
	return edit


func _add_option_row(form: GridContainer, label_text: String) -> OptionButton:
	var label := Label.new()
	label.text = label_text
	form.add_child(label)

	var option := OptionButton.new()
	option.custom_minimum_size = Vector2(250, 0)
	form.add_child(option)
	return option


func _add_spin_row(
	form: GridContainer,
	label_text: String,
	minimum: float,
	maximum: float,
	step: float,
	value: float
) -> SpinBox:
	var label := Label.new()
	label.text = label_text
	form.add_child(label)

	var spin := SpinBox.new()
	spin.min_value = minimum
	spin.max_value = maximum
	spin.step = step
	spin.value = value
	form.add_child(spin)
	return spin


func _on_snapshot_received(next_snapshot: Dictionary) -> void:
	snapshot = next_snapshot
	_auto_step_pending = false
	_ingest_bridge_command_results()
	_rebuild_positions()
	_update_hud()
	_update_bridge_label()
	_update_play_controls()
	_rebuild_schedule_list()
	_update_finance_panel()
	_rebuild_contract_list()
	_rebuild_dispatch_options()
	_rebuild_order_list()
	_rebuild_alert_strip()
	_update_inspector()
	_error_label.text = _bridge_message()
	queue_redraw()


func _on_bridge_error(message: String) -> void:
	_error_label.text = "Bridge: %s" % message
	_auto_step_pending = false
	if _auto_running:
		_auto_running = false
		if _auto_step_timer != null:
			_auto_step_timer.stop()
		_update_play_controls()
	_push_alert("bridge_error", message)


func _on_bridge_status_changed(running: bool) -> void:
	_bridge_running = running
	_update_bridge_label()
	if running:
		_error_label.text = "Bridge running; waiting for snapshot..."


func _request_live_snapshot() -> void:
	_error_label.text = "Requesting live backend snapshot..."
	if not GateRailBridge.request_snapshot():
		_error_label.text = "Using fixture snapshot; live backend unavailable."


func _on_step_pressed() -> void:
	_error_label.text = "Sending {\"ticks\":1} to live bridge..."
	GateRailBridge.step_ticks(1)


func _on_play_pause_pressed() -> void:
	_auto_running = not _auto_running
	_auto_step_pending = false
	if _auto_running:
		_error_label.text = "Auto-run started."
		if _auto_step_timer != null:
			_auto_step_timer.start()
	else:
		_error_label.text = "Auto-run paused."
		if _auto_step_timer != null:
			_auto_step_timer.stop()
	_update_play_controls()


func _on_auto_step_timeout() -> void:
	if not _auto_running or _auto_step_pending:
		return
	_error_label.text = "Auto-running tick %s..." % [int(snapshot.get("tick", 0)) + 1]
	if GateRailBridge.step_ticks(1):
		_auto_step_pending = true
	else:
		_auto_running = false
		_auto_step_pending = false
		if _auto_step_timer != null:
			_auto_step_timer.stop()
		_update_play_controls()


func _on_refresh_pressed() -> void:
	_request_live_snapshot()


func _on_schedule_toggle_pressed(schedule_id: String, enabled: bool) -> void:
	_error_label.text = "Setting %s to %s..." % [schedule_id, "enabled" if enabled else "disabled"]
	GateRailBridge.set_schedule_enabled(schedule_id, enabled, 1)


func _on_dispatch_pressed() -> void:
	var train_id := _selected_option_text(_dispatch_train)
	var origin := _selected_option_text(_dispatch_origin)
	var destination := _selected_option_text(_dispatch_destination)
	var cargo := _selected_option_text(_dispatch_cargo)
	var order_id := _dispatch_order_id.text.strip_edges()
	if order_id.is_empty():
		order_id = "manual_order_%s_%s" % [snapshot.get("tick", 0), _manual_order_sequence]
		_manual_order_sequence += 1
	if train_id.is_empty() or origin.is_empty() or destination.is_empty() or cargo.is_empty():
		_error_label.text = "Dispatch requires train, origin, destination, and cargo."
		return
	if origin == destination:
		_error_label.text = "Dispatch origin and destination must differ."
		return
	var units := int(_dispatch_units.value)
	var priority := int(_dispatch_priority.value)
	_error_label.text = "Queueing %s..." % order_id
	if GateRailBridge.dispatch_order(order_id, train_id, origin, destination, cargo, units, priority, 0):
		_dispatch_order_id.text = ""


func _on_cancel_order_pressed(order_id: String) -> void:
	_error_label.text = "Cancelling %s..." % order_id
	GateRailBridge.cancel_order(order_id, 0)


func _select_at_position(point: Vector2) -> bool:
	var train_id := _hit_train(point)
	if not train_id.is_empty():
		_select_entity("train", train_id)
		return true

	var node_id := _hit_node(point)
	if not node_id.is_empty():
		_select_entity("node", node_id)
		return true

	var world_id := _hit_world(point)
	if not world_id.is_empty():
		_select_entity("world", world_id)
		return true

	var link_id := _hit_link(point)
	if not link_id.is_empty():
		_select_entity("link", link_id)
		return true

	return false


func _select_entity(kind: String, entity_id: String) -> void:
	_selected_kind = kind
	_selected_id = entity_id
	_update_inspector()
	queue_redraw()


func _hit_train(point: Vector2) -> String:
	for train in _array(snapshot.get("trains", [])):
		if typeof(train) != TYPE_DICTIONARY:
			continue
		var train_data: Dictionary = train
		var train_id := str(train_data.get("id", ""))
		if point.distance_to(_train_position(train_data)) <= TRAIN_PICK_RADIUS:
			return train_id
	return ""


func _hit_node(point: Vector2) -> String:
	for node_id in node_positions.keys():
		if point.distance_to(node_positions[node_id]) <= NODE_PICK_RADIUS:
			return str(node_id)
	return ""


func _hit_world(point: Vector2) -> String:
	for world_id in world_positions.keys():
		if point.distance_to(world_positions[world_id]) <= WORLD_PICK_RADIUS:
			return str(world_id)
	return ""


func _hit_link(point: Vector2) -> String:
	var best_id := ""
	var best_distance := LINK_PICK_DISTANCE
	for link in _array(snapshot.get("links", [])):
		if typeof(link) != TYPE_DICTIONARY:
			continue
		var link_data: Dictionary = link
		var origin := str(link_data.get("origin", ""))
		var destination := str(link_data.get("destination", ""))
		if not node_positions.has(origin) or not node_positions.has(destination):
			continue
		var distance := _distance_to_segment(point, node_positions[origin], node_positions[destination])
		if distance <= best_distance:
			best_distance = distance
			best_id = str(link_data.get("id", ""))
	return best_id


func _update_inspector() -> void:
	if _inspector_label == null:
		return
	if _selected_kind.is_empty() or _selected_id.is_empty():
		_inspector_label.text = "Click a world, node, link, or train on the map."
		if _view_local_region_button != null:
			_view_local_region_button.visible = false
		return

	var details := _selected_details()
	if details.is_empty():
		_inspector_label.text = "Selection no longer exists: %s %s" % [_selected_kind, _selected_id]
	else:
		_inspector_label.text = details

	if _view_local_region_button != null:
		_view_local_region_button.visible = (_selected_kind == "world" and not _selected_id.is_empty())


func _on_view_local_region_pressed() -> void:
	if _selected_kind != "world" or _selected_id.is_empty():
		return
	if Engine.has_singleton("SceneNav") or get_node_or_null("/root/SceneNav") != null:
		var nav := get_node("/root/SceneNav")
		nav.selected_world_id = _selected_id
		nav.return_scene = "res://scenes/main.tscn"
	get_tree().change_scene_to_file("res://scenes/local_region.tscn")


func _selected_details() -> String:
	match _selected_kind:
		"world":
			var world := _world_by_id(_selected_id)
			if world.is_empty():
				return ""
			var power: Dictionary = world.get("power", {})
			var progression: Dictionary = world.get("progression", {})
			return "%s\nWorld: %s\nTier: %s | Pop: %s | Stability: %s\nPower: %s available / %s used / margin %s\nTrend: %s | Progress: %s | Support streak: %s" % [
				world.get("name", _selected_id),
				_selected_id,
				world.get("tier_name", "?"),
				world.get("population", 0),
				world.get("stability", "?"),
				power.get("available", 0),
				power.get("used", 0),
				power.get("margin", 0),
				progression.get("trend", "?"),
				progression.get("progress", 0),
				progression.get("support_streak", 0)
			]
		"node":
			var node := _node_by_id(_selected_id)
			if node.is_empty():
				return ""
			var storage: Dictionary = node.get("storage", {})
			return "%s\nNode: %s | %s | world %s\nStorage: %s/%s\nInventory: %s\nDemand: %s\nProduction: %s" % [
				node.get("name", _selected_id),
				_selected_id,
				node.get("kind", "?"),
				node.get("world_id", "?"),
				storage.get("used", 0),
				storage.get("capacity", 0),
				_format_mapping(node.get("inventory", {})),
				_format_mapping(node.get("demand", {})),
				_format_mapping(node.get("production", {}))
			]
		"link":
			var link := _link_by_id(_selected_id)
			if link.is_empty():
				return ""
			var reasons := _array(link.get("disruption_reasons", []))
			var disruption_text := "none" if reasons.is_empty() else _join_values(reasons, ", ")
			return "%s\nLink: %s | %s\nRoute: %s -> %s | travel %s tick(s)\nCapacity: %s/%s | slots %s | powered %s\nDisruption: %s" % [
				_selected_id,
				_selected_id,
				link.get("mode", "?"),
				link.get("origin", "?"),
				link.get("destination", "?"),
				link.get("travel_ticks", 0),
				link.get("capacity", 0),
				link.get("base_capacity", 0),
				link.get("slots_used", 0),
				link.get("powered", "n/a"),
				disruption_text
			]
		"train":
			var train := _train_by_id(_selected_id)
			if train.is_empty():
				return ""
			return "%s\nTrain: %s | %s\nAt: %s | Destination: %s | Remaining: %s\nCargo: %s x%s/%s | Order: %s\nRoute: %s\nBlocked: %s" % [
				train.get("name", _selected_id),
				_selected_id,
				train.get("status", "?"),
				train.get("node_id", "?"),
				train.get("destination", "none"),
				train.get("remaining_ticks", 0),
				train.get("cargo", "empty"),
				train.get("cargo_units", 0),
				train.get("capacity", 0),
				train.get("order_id", "none"),
				_join_values(_array(train.get("route_node_ids", [])), " -> "),
				train.get("blocked_reason", "none")
			]
	return ""


func _update_hud() -> void:
	if _hud_tick_value == null:
		return
	var finance: Dictionary = snapshot.get("finance", {})
	_hud_tick_value.text = str(snapshot.get("tick", 0))
	_hud_cash_value.text = str(finance.get("cash", 0))
	_hud_reputation_value.text = str(snapshot.get("reputation", 0))


func _update_play_controls() -> void:
	if _play_button != null:
		_play_button.text = "Pause" if _auto_running else "Play"
		_set_button_icon(_play_button, "ui_pause.svg" if _auto_running else "ui_play.svg")
	if _run_status_label != null:
		var state_text := "running" if _auto_running else "stopped"
		var pending_text := " | waiting for snapshot" if _auto_step_pending else ""
		_run_status_label.text = "Auto-run %s | %ss cadence%s" % [
			state_text,
			AUTO_STEP_INTERVAL,
			pending_text
		]


func _update_finance_panel() -> void:
	if _finance_label == null:
		return
	var finance: Dictionary = snapshot.get("finance", {})
	_finance_label.text = "Cash %s | Net %s | Revenue %s | Costs %s | Reputation %s" % [
		finance.get("cash", 0),
		finance.get("net", 0),
		finance.get("revenue", 0),
		finance.get("costs", 0),
		snapshot.get("reputation", 0)
	]


func _update_bridge_label() -> void:
	if _bridge_status_value == null:
		return
	_bridge_status_value.text = "Running" if _bridge_running else "Stopped"
	_bridge_source_value.text = "Live" if snapshot.has("bridge") else "Fixture"


func _bridge_message() -> String:
	if not snapshot.has("bridge"):
		return "Fixture snapshot loaded; waiting for live bridge."
	var bridge: Dictionary = snapshot.get("bridge", {})
	var results := _array(bridge.get("command_results", []))
	if results.is_empty():
		return "Live snapshot loaded; stepped %s tick(s)." % bridge.get("stepped_ticks", 0)
	var last_result: Dictionary = results[results.size() - 1]
	return "Live command result: %s" % last_result.get("message", "ok")


func _ingest_bridge_command_results() -> void:
	if not snapshot.has("bridge"):
		return
	var bridge: Dictionary = snapshot.get("bridge", {})
	for result in _array(bridge.get("command_results", [])):
		if typeof(result) != TYPE_DICTIONARY:
			continue
		var command_result: Dictionary = result
		var signature := "%s|%s|%s|%s|%s" % [
			snapshot.get("tick", 0),
			command_result.get("type", ""),
			command_result.get("target_id", ""),
			command_result.get("message", ""),
			command_result.get("ok", false)
		]
		if signature == _last_command_signature:
			continue
		_last_command_signature = signature
		var kind := "command_ok" if bool(command_result.get("ok", false)) else "command_error"
		_push_alert(kind, str(command_result.get("message", "command result")))


func _push_alert(kind: String, message: String) -> void:
	var text := message.strip_edges()
	if text.is_empty():
		return
	_alert_history.append({
		"kind": kind,
		"message": _shorten_alert(text),
	})
	while _alert_history.size() > MAX_ALERT_HISTORY:
		_alert_history.pop_front()
	_rebuild_alert_strip()


func _rebuild_alert_strip() -> void:
	if _alert_strip == null:
		return
	for child in _alert_strip.get_children():
		child.queue_free()

	var rendered := 0
	for alert in _alert_history:
		if typeof(alert) != TYPE_DICTIONARY:
			continue
		_alert_strip.add_child(_build_alert_chip(alert))
		rendered += 1

	for alert in _current_link_alerts():
		_alert_strip.add_child(_build_alert_chip(alert))
		rendered += 1

	if rendered == 0:
		_alert_strip.add_child(_build_alert_chip({
			"kind": "info",
			"message": "No active alerts. Command history, bridge errors, disruptions, and congestion will appear here.",
		}))


func _current_link_alerts() -> Array:
	var alerts: Array = []
	for link in _array(snapshot.get("links", [])):
		if typeof(link) != TYPE_DICTIONARY:
			continue
		var link_data: Dictionary = link
		var link_id := str(link_data.get("id", "?"))
		if bool(link_data.get("disrupted", false)):
			var reasons := _array(link_data.get("disruption_reasons", []))
			var reason_text := "disrupted"
			if not reasons.is_empty():
				reason_text = _join_values(reasons, ", ")
			alerts.append({
				"kind": "disruption",
				"message": "%s: %s" % [link_id, reason_text],
			})

		var capacity := int(link_data.get("capacity", 0))
		var base_capacity := int(link_data.get("base_capacity", capacity))
		var slots_used := int(link_data.get("slots_used", 0))
		if capacity <= 0 and bool(link_data.get("active", true)):
			alerts.append({
				"kind": "congestion",
				"message": "%s: no effective capacity" % link_id,
			})
		elif slots_used > 0 and capacity > 0 and float(slots_used) / float(capacity) >= 0.80:
			alerts.append({
				"kind": "congestion",
				"message": "%s: %s/%s gate slots" % [link_id, slots_used, capacity],
			})
		elif capacity < base_capacity:
			alerts.append({
				"kind": "warning",
				"message": "%s: capacity %s/%s" % [link_id, capacity, base_capacity],
			})
	return alerts


func _build_alert_chip(alert: Dictionary) -> Control:
	var panel := PanelContainer.new()
	var style := StyleBoxFlat.new()
	var kind := str(alert.get("kind", "info"))
	style.bg_color = _alert_fill_color(kind)
	style.border_color = _alert_border_color(kind)
	style.set_border_width_all(1)
	style.set_corner_radius_all(9)
	panel.add_theme_stylebox_override("panel", style)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 8)
	margin.add_theme_constant_override("margin_top", 4)
	margin.add_theme_constant_override("margin_right", 8)
	margin.add_theme_constant_override("margin_bottom", 4)
	panel.add_child(margin)

	var label := Label.new()
	label.text = "%s %s" % [_alert_prefix(kind), str(alert.get("message", ""))]
	label.add_theme_font_size_override("font_size", 12)
	label.modulate = Color(0.94, 0.97, 0.95)
	margin.add_child(label)
	return panel


func _alert_prefix(kind: String) -> String:
	match kind:
		"command_ok":
			return "CMD"
		"command_error":
			return "CMD ERR"
		"bridge_error":
			return "BRIDGE"
		"disruption":
			return "DISRUPT"
		"congestion":
			return "CONGEST"
		"warning":
			return "WARN"
		_:
			return "INFO"


func _alert_fill_color(kind: String) -> Color:
	match kind:
		"command_ok":
			return Color(0.05, 0.24, 0.16, 0.96)
		"command_error", "bridge_error":
			return Color(0.34, 0.08, 0.07, 0.96)
		"disruption":
			return Color(0.42, 0.16, 0.06, 0.96)
		"congestion":
			return Color(0.36, 0.26, 0.06, 0.96)
		"warning":
			return Color(0.24, 0.20, 0.08, 0.96)
		_:
			return Color(0.09, 0.14, 0.17, 0.96)


func _alert_border_color(kind: String) -> Color:
	match kind:
		"command_ok":
			return Color(0.25, 0.72, 0.43)
		"command_error", "bridge_error":
			return Color(0.92, 0.34, 0.24)
		"disruption":
			return Color(0.98, 0.48, 0.22)
		"congestion":
			return Color(0.95, 0.74, 0.25)
		"warning":
			return Color(0.78, 0.68, 0.28)
		_:
			return Color(0.30, 0.48, 0.54)


func _shorten_alert(text: String) -> String:
	if text.length() <= MAX_ALERT_MESSAGE_LENGTH:
		return text
	return text.substr(0, MAX_ALERT_MESSAGE_LENGTH - 3) + "..."


func _join_values(values: Array, separator: String) -> String:
	var parts: Array = []
	for value in values:
		parts.append(str(value))
	return separator.join(parts)


func _rebuild_schedule_list() -> void:
	if _schedule_list == null:
		return
	for child in _schedule_list.get_children():
		child.queue_free()

	var schedules := _array(snapshot.get("schedules", []))
	if schedules.is_empty():
		var empty_label := Label.new()
		empty_label.text = "No schedules in snapshot."
		_schedule_list.add_child(empty_label)
		return

	var filter_text = _schedule_filter.text.to_lower()
	var sort_mode = _schedule_sort.selected
	var filtered_schedules = []
	for schedule in schedules:
		if typeof(schedule) != TYPE_DICTIONARY:
			continue
		var s_id = str(schedule.get("id", "")).to_lower()
		var s_orig = str(schedule.get("origin", "")).to_lower()
		var s_dest = str(schedule.get("destination", "")).to_lower()
		var s_cargo = str(schedule.get("cargo", "")).to_lower()
		if filter_text.is_empty() or filter_text in s_id or filter_text in s_orig or filter_text in s_dest or filter_text in s_cargo:
			filtered_schedules.append(schedule)

	if sort_mode == 0:
		filtered_schedules.sort_custom(func(a, b): return int(a.get("next_departure_tick", 0)) < int(b.get("next_departure_tick", 0)))
	elif sort_mode == 1:
		filtered_schedules.sort_custom(func(a, b): return str(a.get("id", "")) < str(b.get("id", "")))
	elif sort_mode == 2:
		filtered_schedules.sort_custom(func(a, b): return str(a.get("origin", "")) < str(b.get("origin", "")))

	for schedule in filtered_schedules:
		_schedule_list.add_child(_build_schedule_row(schedule))


func _build_schedule_row(schedule: Dictionary) -> Control:
	var panel = PanelContainer.new()
	var style = StyleBoxFlat.new()
	style.bg_color = Color(0.15, 0.17, 0.20)
	style.set_corner_radius_all(4)
	panel.add_theme_stylebox_override("panel", style)

	var row := HBoxContainer.new()
	row.custom_minimum_size = Vector2(500, 32)
	row.add_theme_constant_override("separation", 8)
	panel.add_child(row)

	var enabled := bool(schedule.get("active", false))
	var status_label := Label.new()
	status_label.custom_minimum_size = Vector2(36, 0)
	status_label.text = "ON" if enabled else "OFF"
	status_label.modulate = Color(0.50, 0.90, 0.55) if enabled else Color(0.95, 0.45, 0.35)
	status_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	row.add_child(status_label)

	var cargo_icon := TextureRect.new()
	cargo_icon.custom_minimum_size = Vector2(24, 24)
	cargo_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	cargo_icon.texture = _texture(_cargo_asset(str(schedule.get("cargo", ""))))
	row.add_child(cargo_icon)

	var id_label := Label.new()
	id_label.custom_minimum_size = Vector2(90, 0)
	id_label.text = str(schedule.get("id", "?"))
	id_label.clip_text = true
	row.add_child(id_label)

	var route_label := Label.new()
	route_label.custom_minimum_size = Vector2(170, 0)
	route_label.text = "%s \u2192 %s" % [schedule.get("origin", "?"), schedule.get("destination", "?")]
	route_label.clip_text = true
	row.add_child(route_label)

	var units_label := Label.new()
	units_label.custom_minimum_size = Vector2(40, 0)
	units_label.text = "%su" % schedule.get("units_per_departure", 0)
	units_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	row.add_child(units_label)

	var next_tick_label := Label.new()
	next_tick_label.custom_minimum_size = Vector2(50, 0)
	next_tick_label.text = "T%s" % schedule.get("next_departure_tick", "?")
	next_tick_label.horizontal_alignment = HORIZONTAL_ALIGNMENT_RIGHT
	row.add_child(next_tick_label)

	var toggle_button := Button.new()
	toggle_button.custom_minimum_size = Vector2(32, 32)
	_set_button_icon(toggle_button, "ui_schedule_off.svg" if enabled else "ui_schedule_on.svg")
	toggle_button.pressed.connect(_on_schedule_toggle_pressed.bind(str(schedule.get("id", "")), not enabled))
	row.add_child(toggle_button)

	return panel


func _rebuild_contract_list() -> void:
	if _contract_list == null:
		return
	for child in _contract_list.get_children():
		child.queue_free()

	var contracts := _array(snapshot.get("contracts", []))
	if contracts.is_empty():
		var empty_label := Label.new()
		empty_label.text = "No contracts in snapshot."
		_contract_list.add_child(empty_label)
		return

	for contract in contracts:
		if typeof(contract) != TYPE_DICTIONARY:
			continue
		var label := Label.new()
		var row := HBoxContainer.new()
		var icon := TextureRect.new()
		icon.custom_minimum_size = Vector2(22, 22)
		icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
		icon.texture = _texture("ui_contract.svg")
		row.add_child(icon)
		label.text = "%s | %s/%s %s | due %s | %s" % [
			contract.get("id", "?"),
			contract.get("progress", 0),
			contract.get("target", 0),
			contract.get("cargo", "?"),
			contract.get("due_tick", "?"),
			contract.get("status", "?")
		]
		if contract.get("status", "") == "fulfilled":
			label.modulate = Color(0.50, 0.90, 0.55)
		elif contract.get("status", "") == "failed":
			label.modulate = Color(0.95, 0.45, 0.35)
		row.add_child(label)
		_contract_list.add_child(row)


func _rebuild_order_list() -> void:
	if _order_list == null:
		return
	for child in _order_list.get_children():
		child.queue_free()

	var active_orders: Array = []
	for order in _array(snapshot.get("orders", [])):
		if typeof(order) == TYPE_DICTIONARY and bool(order.get("active", false)):
			active_orders.append(order)

	if active_orders.is_empty():
		var empty_label := Label.new()
		empty_label.text = "No pending one-shot orders."
		_order_list.add_child(empty_label)
		return

	for order in active_orders:
		_order_list.add_child(_build_order_row(order))


func _build_order_row(order: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.custom_minimum_size = Vector2(440, 28)

	var label := Label.new()
	label.custom_minimum_size = Vector2(315, 0)
	label.text = "%s | %s/%s %s | %s -> %s" % [
		order.get("id", "?"),
		order.get("delivered_units", 0),
		order.get("requested_units", 0),
		order.get("cargo", "?"),
		order.get("origin", "?"),
		order.get("destination", "?")
	]
	row.add_child(label)

	var cancel_button := Button.new()
	cancel_button.text = "Cancel"
	_set_button_icon(cancel_button, "ui_cancel.svg")
	cancel_button.pressed.connect(_on_cancel_order_pressed.bind(str(order.get("id", ""))))
	row.add_child(cancel_button)
	return row


func _rebuild_dispatch_options() -> void:
	_refill_option(_dispatch_train, _train_ids())
	_refill_option(_dispatch_origin, _node_ids())
	_refill_option(_dispatch_destination, _node_ids())
	_refill_option(_dispatch_cargo, _cargo_ids())


func _train_ids() -> Array:
	var ids: Array = []
	for train in _array(snapshot.get("trains", [])):
		if typeof(train) == TYPE_DICTIONARY:
			ids.append(str(train.get("id", "")))
	return _sorted_strings(ids)


func _node_ids() -> Array:
	var ids: Array = []
	for node in _array(snapshot.get("nodes", [])):
		if typeof(node) == TYPE_DICTIONARY:
			ids.append(str(node.get("id", "")))
	return _sorted_strings(ids)


func _cargo_ids() -> Array:
	var cargo: Dictionary = {}
	for schedule in _array(snapshot.get("schedules", [])):
		if typeof(schedule) == TYPE_DICTIONARY:
			cargo[str(schedule.get("cargo", ""))] = true
	for contract in _array(snapshot.get("contracts", [])):
		if typeof(contract) == TYPE_DICTIONARY:
			cargo[str(contract.get("cargo", ""))] = true
	for node in _array(snapshot.get("nodes", [])):
		if typeof(node) != TYPE_DICTIONARY:
			continue
		for key in _dictionary_keys(node.get("inventory", {})):
			cargo[key] = true
		for key in _dictionary_keys(node.get("demand", {})):
			cargo[key] = true
	var ids: Array = []
	for key in cargo.keys():
		if not str(key).is_empty() and str(key) != "support" and str(key) != "powered":
			ids.append(str(key))
	return _sorted_strings(ids)


func _refill_option(option: OptionButton, values: Array) -> void:
	if option == null:
		return
	var previous := _selected_option_text(option)
	option.clear()
	for value in values:
		option.add_item(str(value))
	var selected_index := 0
	for index in range(option.item_count):
		if option.get_item_text(index) == previous:
			selected_index = index
			break
	if option.item_count > 0:
		option.select(selected_index)


func _selected_option_text(option: OptionButton) -> String:
	if option == null or option.item_count <= 0 or option.selected < 0:
		return ""
	return option.get_item_text(option.selected)


func _dictionary_keys(value: Variant) -> Array:
	if typeof(value) != TYPE_DICTIONARY:
		return []
	var keys: Array = []
	var dictionary: Dictionary = value
	for key in dictionary.keys():
		keys.append(str(key))
	return keys


func _sorted_strings(values: Array) -> Array:
	var clean: Array = []
	for value in values:
		var text := str(value)
		if not text.is_empty():
			clean.append(text)
	clean.sort()
	return clean


func _world_by_id(world_id: String) -> Dictionary:
	for world in _array(snapshot.get("worlds", [])):
		if typeof(world) == TYPE_DICTIONARY and str(world.get("id", "")) == world_id:
			return world
	return {}


func _node_by_id(node_id: String) -> Dictionary:
	for node in _array(snapshot.get("nodes", [])):
		if typeof(node) == TYPE_DICTIONARY and str(node.get("id", "")) == node_id:
			return node
	return {}


func _link_by_id(link_id: String) -> Dictionary:
	for link in _array(snapshot.get("links", [])):
		if typeof(link) == TYPE_DICTIONARY and str(link.get("id", "")) == link_id:
			return link
	return {}


func _train_by_id(train_id: String) -> Dictionary:
	for train in _array(snapshot.get("trains", [])):
		if typeof(train) == TYPE_DICTIONARY and str(train.get("id", "")) == train_id:
			return train
	return {}


func _format_mapping(value: Variant) -> String:
	if typeof(value) != TYPE_DICTIONARY:
		return "none"
	var dictionary: Dictionary = value
	if dictionary.is_empty():
		return "none"
	var parts: Array = []
	var keys := _sorted_strings(dictionary.keys())
	for key in keys:
		parts.append("%s:%s" % [key, dictionary.get(key, 0)])
	return ", ".join(parts)


func _distance_to_segment(point: Vector2, start: Vector2, end: Vector2) -> float:
	var segment := end - start
	var length_squared := segment.length_squared()
	if length_squared <= 0.0:
		return point.distance_to(start)
	var t := clampf((point - start).dot(segment) / length_squared, 0.0, 1.0)
	return point.distance_to(start + (segment * t))


func _train_position(train: Dictionary) -> Vector2:
	var fallback_node := str(train.get("node_id", ""))
	var fallback := Vector2.ZERO
	if node_positions.has(fallback_node):
		fallback = node_positions[fallback_node] + Vector2(12, -12)

	if str(train.get("status", "")) != "in_transit":
		return fallback

	var route_nodes := _array(train.get("route_node_ids", []))
	var route_links := _array(train.get("route_link_ids", []))
	if route_nodes.size() < 2 or route_links.is_empty():
		return fallback

	var link_ticks: Array = []
	var total_ticks := 0
	for link_id in route_links:
		var link := _link_by_id(str(link_id))
		var ticks: int = max(1, int(link.get("travel_ticks", 1)))
		link_ticks.append(ticks)
		total_ticks += ticks
	if total_ticks <= 0:
		return fallback

	var remaining: int = clampi(int(train.get("remaining_ticks", 0)), 0, total_ticks)
	var elapsed: int = clampi(total_ticks - remaining, 0, total_ticks)
	var traversed := 0
	var segment_count: int = min(route_links.size(), route_nodes.size() - 1)
	for index in range(segment_count):
		var from_node := str(route_nodes[index])
		var to_node := str(route_nodes[index + 1])
		if not node_positions.has(from_node) or not node_positions.has(to_node):
			continue
		var segment_ticks: int = int(link_ticks[index])
		if elapsed <= traversed + segment_ticks:
			var progress := float(elapsed - traversed) / float(segment_ticks)
			return node_positions[from_node].lerp(node_positions[to_node], progress) + Vector2(12, -12)
		traversed += segment_ticks

	var destination := str(train.get("destination", ""))
	if node_positions.has(destination):
		return node_positions[destination] + Vector2(12, -12)
	return fallback


func _load_placeholder_assets() -> void:
	for filename in PLACEHOLDER_ASSETS:
		var path: String = ASSET_DIR + str(filename)
		if ResourceLoader.exists(path):
			var texture: Resource = load(path)
			if texture is Texture2D:
				_textures[filename] = texture


func _set_button_icon(button: Button, filename: String) -> void:
	var texture := _texture(filename)
	if texture != null:
		button.icon = texture
		button.expand_icon = true


func _texture(filename: String) -> Texture2D:
	if _textures.has(filename) and _textures[filename] is Texture2D:
		return _textures[filename]
	return null


func _draw_texture_centered(filename: String, center: Vector2, size: Vector2) -> bool:
	var texture := _texture(filename)
	if texture == null:
		return false
	draw_texture_rect(texture, Rect2(center - size * 0.5, size), false)
	return true


func _world_asset(world: Dictionary) -> String:
	var world_id := str(world.get("id", ""))
	if world_id == "core" or int(world.get("tier", 0)) >= 3:
		return "world_core.svg"
	if world_id == "outer" or str(world.get("specialization", "")) == "survey_outpost":
		return "world_outpost.svg"
	return "world_frontier.svg"


func _node_asset(kind: String) -> String:
	match kind:
		"depot":
			return "node_depot.svg"
		"settlement":
			return "node_settlement.svg"
		"extractor":
			return "node_extractor.svg"
		"industry":
			return "node_industry.svg"
		"gate_hub":
			return "node_gate_hub.svg"
		_:
			return "node_depot.svg"


func _train_asset(train: Dictionary) -> String:
	if str(train.get("status", "")) == "blocked" or str(train.get("blocked_reason", "")).length() > 0:
		return "train_blocked.svg"
	return "train_freight.svg"


func _cargo_asset(cargo: String) -> String:
	match cargo:
		"food":
			return "cargo_food.svg"
		"ore":
			return "cargo_ore.svg"
		"construction_materials":
			return "cargo_construction_materials.svg"
		"medical_supplies":
			return "cargo_medical_supplies.svg"
		"parts":
			return "cargo_parts.svg"
		"research_equipment":
			return "cargo_research_equipment.svg"
		_:
			return "ui_dispatch.svg"


func _rebuild_positions() -> void:
	world_positions.clear()
	node_positions.clear()

	var raw_positions: Dictionary = {}
	var min_position := Vector2(INF, INF)
	var max_position := Vector2(-INF, -INF)
	for world in _array(snapshot.get("worlds", [])):
		var position: Dictionary = world.get("position", {})
		var world_id := str(world.get("id", ""))
		var raw_position := Vector2(
			float(position.get("x", 0)),
			float(position.get("y", 0))
		)
		raw_positions[world_id] = raw_position
		min_position = Vector2(min(min_position.x, raw_position.x), min(min_position.y, raw_position.y))
		max_position = Vector2(max(max_position.x, raw_position.x), max(max_position.y, raw_position.y))

	if raw_positions.is_empty():
		return

	var span := max_position - min_position
	var map_scale: float = 1.0
	_node_orbit_radius = 82.0

	for world_id in raw_positions.keys():
		var raw: Vector2 = raw_positions[world_id]
		var x: float = (raw.x - (min_position.x + span.x * 0.5)) * map_scale
		var y: float = (raw.y - (min_position.y + span.y * 0.5)) * map_scale
		world_positions[world_id] = Vector2(x, y)

	var nodes_by_world: Dictionary = {}
	for node in _array(snapshot.get("nodes", [])):
		var world_id := str(node.get("world_id", ""))
		if not nodes_by_world.has(world_id):
			nodes_by_world[world_id] = []
		nodes_by_world[world_id].append(node)

	for world_id in nodes_by_world.keys():
		var nodes: Array = nodes_by_world[world_id]
		var center: Vector2 = world_positions.get(world_id, _map_rect.get_center())
		var count: int = max(1, nodes.size())
		for index in range(nodes.size()):
			var angle := TAU * float(index) / float(count)
			var local := Vector2(cos(angle), sin(angle)) * _node_orbit_radius
			node_positions[nodes[index].get("id", "")] = center + local


func _draw() -> void:
	if snapshot.is_empty():
		return

	var font := ThemeDB.fallback_font

	for link in _array(snapshot.get("links", [])):
		var origin := str(link.get("origin", ""))
		var destination := str(link.get("destination", ""))
		if not node_positions.has(origin) or not node_positions.has(destination):
			continue
		var color := Color(0.36, 0.56, 0.72)
		if link.get("mode", "") == "gate":
			color = Color(0.98, 0.68, 0.25)
		if bool(link.get("disrupted", false)):
			color = Color(0.95, 0.25, 0.18)
		elif int(link.get("capacity", 0)) < int(link.get("base_capacity", 0)):
			color = Color(0.96, 0.82, 0.30)
		var width := 5.0 if link.get("mode", "") == "gate" else 4.0
		if _selected_kind == "link" and _selected_id == str(link.get("id", "")):
			width += 4.0
		draw_line(node_positions[origin], node_positions[destination], color, width)
		var midpoint: Vector2 = node_positions[origin].lerp(node_positions[destination], 0.5)
		var link_label := "%s %s/%s" % [
			str(link.get("mode", "?")).to_upper(),
			link.get("capacity", 0),
			link.get("base_capacity", 0)
		]
		draw_string(font, midpoint + Vector2(6, -7), link_label, HORIZONTAL_ALIGNMENT_LEFT, -1, 11, Color(0.84, 0.90, 0.88))

	for world in _array(snapshot.get("worlds", [])):
		var world_id := str(world.get("id", ""))
		var center: Vector2 = world_positions.get(world_id, _map_rect.get_center())
		if not _draw_texture_centered(_world_asset(world), center, Vector2(76, 76)):
			draw_circle(center, WORLD_RADIUS, Color(0.12, 0.20, 0.24))
		var ring_color := Color(0.56, 0.83, 0.78)
		var ring_width := 3.0
		if _selected_kind == "world" and _selected_id == world_id:
			ring_color = Color(1.0, 0.86, 0.32)
			ring_width = 6.0
		draw_arc(center, WORLD_RADIUS, 0.0, TAU, 96, ring_color, ring_width)
		draw_string(font, center + Vector2(-58, -64), str(world.get("name", world_id)), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color.WHITE)

	for node in _array(snapshot.get("nodes", [])):
		var node_id := str(node.get("id", ""))
		var point: Vector2 = node_positions.get(node_id, _map_rect.get_center())
		var color := Color(0.76, 0.86, 0.92)
		if node.get("kind", "") == "gate_hub":
			color = Color(1.0, 0.72, 0.32)
		elif node.get("kind", "") == "settlement":
			color = Color(0.52, 0.88, 0.52)
		if not _draw_texture_centered(_node_asset(str(node.get("kind", ""))), point, Vector2(28, 28)):
			draw_circle(point, NODE_RADIUS, color)
		if _selected_kind == "node" and _selected_id == node_id:
			draw_arc(point, 18.0, 0.0, TAU, 48, Color(1.0, 0.86, 0.32), 4.0)

	for train in _array(snapshot.get("trains", [])):
		var point := _train_position(train)
		if str(train.get("status", "")) == "in_transit":
			var route_nodes := _array(train.get("route_node_ids", []))
			if route_nodes.size() >= 2:
				var origin_node := str(route_nodes[0])
				var destination_node := str(route_nodes[route_nodes.size() - 1])
				if node_positions.has(origin_node) and node_positions.has(destination_node):
					draw_line(node_positions[origin_node], node_positions[destination_node], Color(0.72, 0.92, 0.95, 0.45), 2.0)
		if not _draw_texture_centered(_train_asset(train), point, Vector2(30, 30)):
			draw_rect(Rect2(point - Vector2(6, 6), Vector2(12, 12)), Color(0.95, 0.95, 0.72))
		var train_id := str(train.get("id", ""))
		var label := "%s %s" % [train_id, train.get("status", "?")]
		draw_string(font, point + Vector2(16, -12), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.96, 0.96, 0.80))
		if _selected_kind == "train" and _selected_id == train_id:
			draw_arc(point, 20.0, 0.0, TAU, 48, Color(1.0, 0.86, 0.32), 4.0)


func _array(value: Variant) -> Array:
	if typeof(value) == TYPE_ARRAY:
		return value
	return []
