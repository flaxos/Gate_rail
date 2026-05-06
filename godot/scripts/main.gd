extends Node2D

const WORLD_RADIUS := 48.0
const NODE_RADIUS := 8.0
const ASSET_DIR := "res://assets/placeholders/"
const UI_MARGIN := 16.0
const UI_GAP := 14.0
const LEFT_PANEL_WIDTH := 560.0
const RIGHT_PANEL_WIDTH := 500.0
const CONTROL_PANEL_HEIGHT := 392.0
const ALERT_STRIP_HEIGHT := 46.0
const MIN_CENTER_MAP_WIDTH := 360.0
const MAP_INSET := Vector2(92, 96)
const MAX_ALERT_HISTORY := 8
const MAX_ALERT_MESSAGE_LENGTH := 86
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
var _operations_scroll: ScrollContainer
var _schedule_scroll: ScrollContainer
var _contract_scroll: ScrollContainer
var _order_scroll: ScrollContainer
var _alert_scroll: ScrollContainer
var _tutorial_panel: PanelContainer
var _tutorial_summary: Label
var _tutorial_list: VBoxContainer
var _tutorial_action_button: Button
var _hud_tick_value: Label
var _hud_cash_value: Label
var _hud_reputation_value: Label
var _bridge_status_value: Label
var _bridge_source_value: Label
var _save_path_edit: LineEdit
var _scenario_select: OptionButton
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
var _dispatch_status_label: Label
var _alert_history: Array = []
var _tutorial_next_action: Dictionary = {}
var _auto_running := false
var _auto_step_pending := false
var _bridge_running := false
var _manual_order_sequence := 1
var _dispatch_click_stage := "pickup"
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
	RenderingServer.set_default_clear_color(UITheme.BG_0)
	_load_placeholder_assets()
	_build_ui()
	get_viewport().size_changed.connect(_on_viewport_size_changed)
	GateRailBridge.snapshot_received.connect(_on_snapshot_received)
	GateRailBridge.bridge_error.connect(_on_bridge_error)
	GateRailBridge.bridge_status_changed.connect(_on_bridge_status_changed)
	GateRailBridge.auto_run_changed.connect(_on_bridge_auto_run_changed)

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
	_control_panel.add_theme_stylebox_override("panel", UITheme.panel_style())
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
	top_panel.add_theme_stylebox_override("panel", UITheme.panel_style("hud"))
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
		lbl.text = label_text.to_upper()
		UITheme.style_label_caption(lbl)
		top_grid.add_child(lbl)
		var val = Label.new()
		val.text = "-"
		UITheme.style_label_value(val, true)
		top_grid.add_child(val)
		return val

	_hud_tick_value = add_hud_item.call("Tick:")
	_hud_cash_value = add_hud_item.call("Cash:")
	_hud_reputation_value = add_hud_item.call("Standing:")
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

	var scenario_row := HBoxContainer.new()
	scenario_row.add_theme_constant_override("separation", 8)
	box.add_child(scenario_row)

	var scenario_label := Label.new()
	scenario_label.text = "Scenario"
	scenario_label.custom_minimum_size = Vector2(66, 0)
	scenario_row.add_child(scenario_label)

	_scenario_select = OptionButton.new()
	_scenario_select.custom_minimum_size = Vector2(190, 0)
	scenario_row.add_child(_scenario_select)

	var load_scenario_button := Button.new()
	load_scenario_button.text = "Load Scenario"
	load_scenario_button.pressed.connect(_on_load_scenario_pressed)
	scenario_row.add_child(load_scenario_button)

	var save_row := HBoxContainer.new()
	save_row.add_theme_constant_override("separation", 8)
	box.add_child(save_row)

	_save_path_edit = LineEdit.new()
	_save_path_edit.text = GateRailBridge.last_save_path
	_save_path_edit.placeholder_text = "save slot or path"
	_save_path_edit.custom_minimum_size = Vector2(244, 0)
	save_row.add_child(_save_path_edit)

	var save_button := Button.new()
	save_button.text = "Save Game"
	save_button.pressed.connect(_on_save_game_pressed)
	save_row.add_child(save_button)

	var load_button := Button.new()
	load_button.text = "Load Game"
	load_button.pressed.connect(_on_load_game_pressed)
	save_row.add_child(load_button)

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
	_operations_panel.add_theme_stylebox_override("panel", UITheme.panel_style())
	ui.add_child(_operations_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	_operations_panel.add_child(margin)

	_operations_scroll = ScrollContainer.new()
	_operations_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_operations_scroll.size_flags_vertical = Control.SIZE_EXPAND_FILL
	margin.add_child(_operations_scroll)

	var box := VBoxContainer.new()
	box.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	_operations_scroll.add_child(box)

	var finance_title := Label.new()
	finance_title.text = "Finance and Combine Standing"
	box.add_child(finance_title)

	_finance_label = Label.new()
	_finance_label.text = "Waiting for snapshot..."
	box.add_child(_finance_label)

	_build_tutorial_section(box)

	var contract_title := Label.new()
	contract_title.text = "Freight Contracts"
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

	_dispatch_status_label = Label.new()
	_dispatch_status_label.text = "Manual Dispatch"
	_dispatch_status_label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	_dispatch_status_label.add_theme_font_size_override("font_size", 12)
	_dispatch_status_label.modulate = Color(0.70, 0.82, 0.84)
	box.add_child(_dispatch_status_label)

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


func _build_tutorial_section(box: VBoxContainer) -> void:
	_tutorial_panel = PanelContainer.new()
	_tutorial_panel.visible = false
	_tutorial_panel.add_theme_stylebox_override("panel", UITheme.panel_style("tutorial"))
	box.add_child(_tutorial_panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 8)
	margin.add_theme_constant_override("margin_top", 8)
	margin.add_theme_constant_override("margin_right", 8)
	margin.add_theme_constant_override("margin_bottom", 8)
	_tutorial_panel.add_child(margin)

	var content := VBoxContainer.new()
	margin.add_child(content)

	var title := Label.new()
	title.text = "TUTORIAL LOOP"
	title.add_theme_color_override("font_color", UITheme.ACCENT)
	title.add_theme_font_size_override("font_size", 11)
	content.add_child(title)

	_tutorial_summary = Label.new()
	_tutorial_summary.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	UITheme.style_label_body(_tutorial_summary)
	content.add_child(_tutorial_summary)

	_tutorial_list = VBoxContainer.new()
	_tutorial_list.add_theme_constant_override("separation", 3)
	content.add_child(_tutorial_list)

	_tutorial_action_button = Button.new()
	_tutorial_action_button.text = "Advance tutorial"
	_set_button_icon(_tutorial_action_button, "ui_step.svg")
	_tutorial_action_button.pressed.connect(_on_tutorial_action_pressed)
	content.add_child(_tutorial_action_button)


func _build_inspector_panel(ui: CanvasLayer) -> void:
	_inspector_panel = PanelContainer.new()
	_inspector_panel.custom_minimum_size = Vector2(LEFT_PANEL_WIDTH, 296)
	_inspector_panel.add_theme_stylebox_override("panel", UITheme.panel_style("inspector"))
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
	_alert_panel.add_theme_stylebox_override("panel", UITheme.panel_style("alert"))
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
	title.text = "STATUS FEED"
	title.custom_minimum_size = Vector2(96, 0)
	UITheme.style_label_caption(title)
	row.add_child(title)

	_alert_scroll = ScrollContainer.new()
	_alert_scroll.custom_minimum_size = Vector2(1158, 32)
	_alert_scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(_alert_scroll)

	_alert_strip = HBoxContainer.new()
	_alert_strip.add_theme_constant_override("separation", 6)
	_alert_scroll.add_child(_alert_strip)
	_rebuild_alert_strip()


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
	if _operations_scroll != null:
		_operations_scroll.custom_minimum_size = Vector2(right_width - 24.0, max(260.0, _panel_height(_operations_panel) - 24.0))
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
	_auto_running = GateRailBridge.is_auto_running()
	_auto_step_pending = GateRailBridge.is_auto_step_pending()
	_ingest_bridge_command_results()
	_refresh_scenario_select_from_snapshot()
	_rebuild_positions()
	_update_hud()
	_update_bridge_label()
	_update_play_controls()
	_rebuild_schedule_list()
	_update_finance_panel()
	_rebuild_tutorial_panel()
	_rebuild_contract_list()
	_rebuild_dispatch_options()
	_rebuild_order_list()
	_rebuild_alert_strip()
	_update_inspector()
	_error_label.text = _bridge_message()
	queue_redraw()


func _refresh_scenario_select_from_snapshot() -> void:
	if _scenario_select == null:
		return
	var catalog := _array(snapshot.get("scenario_catalog", []))
	if catalog.is_empty():
		return
	var previous := _selected_option_text(_scenario_select)
	_scenario_select.clear()
	for item in catalog:
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var key := str(item.get("key", ""))
		if key.is_empty():
			continue
		_scenario_select.add_item(key)
	if _scenario_select.item_count <= 0:
		return
	if not previous.is_empty():
		_select_option_text(_scenario_select, previous)
		if _selected_option_text(_scenario_select) == previous:
			return
	for index in range(_scenario_select.item_count):
		var entry: Variant = catalog[index] if index < catalog.size() else null
		if typeof(entry) == TYPE_DICTIONARY and _flag(entry.get("default", false), false):
			_scenario_select.select(index)
			return
	_scenario_select.select(0)
	return


func _on_bridge_error(message: String) -> void:
	var friendly_message := _format_save_load_error(message)
	_error_label.text = "Bridge: %s" % friendly_message
	_auto_step_pending = false
	_auto_running = GateRailBridge.is_auto_running()
	_update_play_controls()
	_push_alert("bridge_error", friendly_message)


func _format_save_load_error(message: String) -> String:
	var missing_prefix := "save file not found:"
	if message.begins_with(missing_prefix):
		var path := message.substr(missing_prefix.length()).strip_edges()
		return "Save not found at %s. Press Save Game first, or choose an existing save path." % path
	return message


func _on_bridge_status_changed(running: bool) -> void:
	_bridge_running = running
	_update_bridge_label()
	if running:
		_error_label.text = "Bridge running; waiting for snapshot..."


func _on_bridge_auto_run_changed(running: bool) -> void:
	_auto_running = running
	_auto_step_pending = GateRailBridge.is_auto_step_pending()
	_error_label.text = "Auto-run started." if running else "Auto-run paused."
	_update_play_controls()


func _request_live_snapshot() -> void:
	_error_label.text = "Requesting live backend snapshot..."
	if not GateRailBridge.request_snapshot():
		_error_label.text = "Using fixture snapshot; live backend unavailable."


func _on_step_pressed() -> void:
	_error_label.text = "Sending {\"ticks\":1} to live bridge..."
	GateRailBridge.step_ticks(1)


func _on_tutorial_action_pressed() -> void:
	if _tutorial_next_action.is_empty():
		return
	var kind := str(_tutorial_next_action.get("kind", ""))
	if kind == "step_ticks":
		var ticks: int = int(max(1, int(_tutorial_next_action.get("ticks", 1))))
		var label := str(_tutorial_next_action.get("label", "Running tutorial"))
		_error_label.text = "%s for %s tick(s)..." % [label, ticks]
		GateRailBridge.step_ticks(ticks)
		return
	if kind == "command" or kind == "commands":
		var commands: Array = []
		if kind == "command":
			var command_raw: Variant = _tutorial_next_action.get("command", {})
			if typeof(command_raw) == TYPE_DICTIONARY:
				var command: Dictionary = command_raw
				commands.append(command.duplicate(true))
		else:
			for command_item in _array(_tutorial_next_action.get("commands", [])):
				if typeof(command_item) == TYPE_DICTIONARY:
					var command_payload: Dictionary = command_item
					commands.append(command_payload.duplicate(true))
		if commands.is_empty():
			_error_label.text = "Tutorial action has no backend command."
			return
		var command_ticks: int = int(max(0, int(_tutorial_next_action.get("ticks", 0))))
		var command_label := str(_tutorial_next_action.get("label", "Running tutorial command"))
		_error_label.text = "%s..." % command_label
		GateRailBridge.send_message({"commands": commands, "ticks": command_ticks})
		return
	_error_label.text = "Unsupported tutorial action: %s" % kind


func _on_play_pause_pressed() -> void:
	GateRailBridge.set_auto_running(not GateRailBridge.is_auto_running())
	_auto_running = GateRailBridge.is_auto_running()
	_auto_step_pending = GateRailBridge.is_auto_step_pending()
	_update_play_controls()


func _on_refresh_pressed() -> void:
	_request_live_snapshot()


func _save_path_text() -> String:
	var path := GateRailBridge.last_save_path
	if _save_path_edit != null:
		path = _save_path_edit.text.strip_edges()
	path = GateRailBridge.normalize_save_path(path)
	if _save_path_edit != null:
		_save_path_edit.text = path
	return path


func _on_save_game_pressed() -> void:
	var path := _save_path_text()
	_error_label.text = "Saving game to %s..." % path
	GateRailBridge.save_game(path, 0)


func _on_load_game_pressed() -> void:
	var path := _save_path_text()
	GateRailBridge.set_auto_running(false)
	_error_label.text = "Loading game from %s..." % path
	GateRailBridge.load_game(path, 0)


func _on_load_scenario_pressed() -> void:
	var scenario_id := _selected_option_text(_scenario_select)
	if scenario_id.is_empty():
		_error_label.text = "Choose a scenario first."
		return
	GateRailBridge.set_auto_running(false)
	_error_label.text = "Loading scenario %s..." % scenario_id
	GateRailBridge.load_scenario(scenario_id, 0)


func _on_schedule_toggle_pressed(schedule_id: String, enabled: bool) -> void:
	_error_label.text = "Setting %s to %s..." % [schedule_id, "enabled" if enabled else "disabled"]
	GateRailBridge.set_schedule_enabled(schedule_id, enabled, 1)


func _on_schedule_preview_edit_pressed(
	schedule: Dictionary,
	cargo_option: OptionButton,
	units_spin: SpinBox,
	interval_spin: SpinBox,
	stops_edit: LineEdit,
	active_check: CheckBox
) -> void:
	var schedule_id := str(schedule.get("id", ""))
	if schedule_id.is_empty():
		return
	_error_label.text = "Previewing schedule edit for %s..." % schedule_id
	GateRailBridge.preview_update_schedule(
		schedule_id,
		_schedule_edit_payload(schedule, cargo_option, units_spin, interval_spin, stops_edit, active_check),
		0,
	)


func _on_schedule_apply_edit_pressed(
	schedule: Dictionary,
	cargo_option: OptionButton,
	units_spin: SpinBox,
	interval_spin: SpinBox,
	stops_edit: LineEdit,
	active_check: CheckBox
) -> void:
	var schedule_id := str(schedule.get("id", ""))
	if schedule_id.is_empty():
		return
	_error_label.text = "Applying schedule edit for %s..." % schedule_id
	GateRailBridge.update_schedule(
		schedule_id,
		_schedule_edit_payload(schedule, cargo_option, units_spin, interval_spin, stops_edit, active_check),
		0,
	)


func _on_schedule_delete_pressed(schedule_id: String) -> void:
	if schedule_id.is_empty():
		return
	_error_label.text = "Sending DeleteSchedule for %s..." % schedule_id
	GateRailBridge.delete_schedule(schedule_id, 0)


func _schedule_edit_payload(
	schedule: Dictionary,
	cargo_option: OptionButton,
	units_spin: SpinBox,
	interval_spin: SpinBox,
	stops_edit: LineEdit,
	active_check: CheckBox
) -> Dictionary:
	var next_departure := int(schedule.get("next_departure_tick", int(snapshot.get("tick", 0)) + 1))
	next_departure = max(next_departure, int(snapshot.get("tick", 0)) + 1)
	return {
		"train_id": str(schedule.get("train_id", "")),
		"origin": str(schedule.get("origin", "")),
		"destination": str(schedule.get("destination", "")),
		"cargo_type": _selected_option_text(cargo_option),
		"units_per_departure": int(units_spin.value),
		"interval_ticks": int(interval_spin.value),
		"next_departure_tick": next_departure,
		"priority": int(schedule.get("priority", 100)),
		"active": active_check.button_pressed,
		"return_to_origin": _flag(schedule.get("return_to_origin", true), true),
		"stops": _parse_stop_list(stops_edit.text),
	}


func _parse_stop_list(text: String) -> Array:
	var stops: Array = []
	for raw_part in text.split(",", false):
		var stop_id := str(raw_part).strip_edges()
		if not stop_id.is_empty():
			stops.append(stop_id)
	return stops


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
		_dispatch_click_stage = "pickup"
		_update_dispatch_builder_status()


func _on_cancel_order_pressed(order_id: String) -> void:
	_error_label.text = "Cancelling %s..." % order_id
	GateRailBridge.cancel_order(order_id, 0)


func _apply_selection_to_dispatch_builder(kind: String, entity_id: String) -> void:
	if kind == "train":
		_select_option_text(_dispatch_train, entity_id)
		var train := _train_by_id(entity_id)
		var node_id := str(train.get("node_id", ""))
		if not node_id.is_empty():
			_select_option_text(_dispatch_origin, node_id)
			_select_dispatch_cargo_for_route(node_id, _selected_option_text(_dispatch_destination))
			_dispatch_click_stage = "dropoff"
		_update_dispatch_builder_status()
		return

	if kind != "node":
		return

	var current_origin := _selected_option_text(_dispatch_origin)
	if _dispatch_click_stage == "dropoff" and not current_origin.is_empty() and entity_id != current_origin:
		_select_option_text(_dispatch_destination, entity_id)
		_select_dispatch_cargo_for_route(current_origin, entity_id)
		_dispatch_click_stage = "ready"
	else:
		_select_option_text(_dispatch_origin, entity_id)
		_select_dispatch_cargo_for_route(entity_id, _selected_option_text(_dispatch_destination))
		_dispatch_click_stage = "dropoff"
	_update_dispatch_builder_status()


func _select_dispatch_cargo_for_route(origin_id: String, destination_id: String) -> void:
	var cargo_id := _preferred_cargo_for_route(origin_id, destination_id)
	if cargo_id.is_empty():
		return
	_select_option_text(_dispatch_cargo, cargo_id)
	_select_dispatch_units_for_route(origin_id, cargo_id)


func _preferred_cargo_for_route(origin_id: String, destination_id: String) -> String:
	var origin_node := _node_by_id(origin_id)
	var inventory_raw: Variant = origin_node.get("inventory", {})
	if typeof(inventory_raw) != TYPE_DICTIONARY:
		return ""
	var inventory: Dictionary = inventory_raw
	var candidates: Array = []

	if not destination_id.is_empty():
		var destination_node := _node_by_id(destination_id)
		_append_unique_strings(candidates, _dictionary_keys(destination_node.get("demand", {})))
		var recipe_raw: Variant = destination_node.get("recipe", {})
		if typeof(recipe_raw) == TYPE_DICTIONARY:
			var recipe: Dictionary = recipe_raw
			_append_unique_strings(candidates, _dictionary_keys(recipe.get("inputs", {})))
		for contract_item in _array(snapshot.get("contracts", [])):
			if typeof(contract_item) != TYPE_DICTIONARY:
				continue
			var contract: Dictionary = contract_item
			if str(contract.get("destination", "")) == destination_id and str(contract.get("status", "")) == "active":
				_append_unique_strings(candidates, [str(contract.get("cargo", ""))])

	for candidate in candidates:
		var candidate_id := str(candidate)
		if int(inventory.get(candidate_id, 0)) > 0:
			return candidate_id

	for cargo_id in _sorted_strings(_dictionary_keys(inventory)):
		var stocked_id := str(cargo_id)
		if int(inventory.get(stocked_id, 0)) > 0:
			return stocked_id
	return ""


func _select_dispatch_units_for_route(origin_id: String, cargo_id: String) -> void:
	if _dispatch_units == null or cargo_id.is_empty():
		return
	var suggested := _selected_train_capacity()
	var available := _node_cargo_units(origin_id, cargo_id)
	if available > 0 and available < suggested:
		suggested = available
	if suggested < 1:
		suggested = 1
	_dispatch_units.value = suggested


func _selected_train_capacity() -> int:
	var train_id := _selected_option_text(_dispatch_train)
	var train := _train_by_id(train_id)
	return int(train.get("capacity", 1))


func _node_cargo_units(node_id: String, cargo_id: String) -> int:
	var node := _node_by_id(node_id)
	var inventory_raw: Variant = node.get("inventory", {})
	if typeof(inventory_raw) != TYPE_DICTIONARY:
		return 0
	var inventory: Dictionary = inventory_raw
	return int(inventory.get(cargo_id, 0))


func _update_dispatch_builder_status() -> void:
	if _dispatch_status_label == null:
		return
	_dispatch_status_label.text = "Manual Dispatch | Train %s | Pickup %s | Dropoff %s | %s x%s" % [
		_selected_option_text(_dispatch_train),
		_selected_option_text(_dispatch_origin),
		_selected_option_text(_dispatch_destination),
		_selected_option_text(_dispatch_cargo),
		int(_dispatch_units.value) if _dispatch_units != null else 0,
	]


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
	_apply_selection_to_dispatch_builder(kind, entity_id)
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
			GateRailBridge.auto_step_interval,
			pending_text
		]


func _update_finance_panel() -> void:
	if _finance_label == null:
		return
	var finance: Dictionary = snapshot.get("finance", {})
	_finance_label.text = "Cash %s | Net %s | Revenue %s | Costs %s | Standing %s" % [
		finance.get("cash", 0),
		finance.get("net", 0),
		finance.get("revenue", 0),
		finance.get("costs", 0),
		snapshot.get("reputation", 0)
	]


func _tutorial_snapshot() -> Dictionary:
	var raw: Variant = snapshot.get("tutorial", {})
	if typeof(raw) == TYPE_DICTIONARY:
		var tutorial: Dictionary = raw
		return tutorial
	return {}


func _rebuild_tutorial_panel() -> void:
	if _tutorial_panel == null or _tutorial_list == null:
		return
	var tutorial := _tutorial_snapshot()
	if tutorial.is_empty():
		_tutorial_panel.visible = false
		_tutorial_next_action = {}
		return

	_tutorial_panel.visible = true
	if _tutorial_summary != null:
		_tutorial_summary.text = str(tutorial.get("summary", ""))

	for child in _tutorial_list.get_children():
		child.queue_free()
	for step in _array(tutorial.get("steps", [])):
		if typeof(step) == TYPE_DICTIONARY:
			_tutorial_list.add_child(_build_tutorial_step_row(step))

	var action_raw: Variant = tutorial.get("next_action", {})
	if typeof(action_raw) == TYPE_DICTIONARY:
		var action: Dictionary = action_raw
		_tutorial_next_action = action.duplicate(true)
	else:
		_tutorial_next_action = {}

	if _tutorial_action_button != null:
		var action_kind := str(_tutorial_next_action.get("kind", ""))
		var can_run_action := action_kind in ["step_ticks", "command", "commands"]
		_tutorial_action_button.visible = can_run_action
		_tutorial_action_button.disabled = not can_run_action
		_tutorial_action_button.text = str(_tutorial_next_action.get("label", "Advance tutorial"))


func _build_tutorial_step_row(step: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.custom_minimum_size = Vector2(440, 28)
	row.add_theme_constant_override("separation", 8)

	var status := str(step.get("status", "pending"))
	var status_label := Label.new()
	status_label.custom_minimum_size = Vector2(72, 0)
	status_label.text = status.to_upper()
	status_label.add_theme_font_size_override("font_size", 11)
	status_label.modulate = _tutorial_status_color(status)
	row.add_child(status_label)

	var label := Label.new()
	label.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	label.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	var row_text: String = "%s | %s/%s %s | %s -> %s" % [
		step.get("label", step.get("id", "step")),
		step.get("delivered", 0),
		step.get("target", 0),
		step.get("cargo", "?"),
		step.get("origin", "?"),
		step.get("destination", "?"),
	]
	var reward_cash := float(step.get("reward_cash", 0.0))
	var reward_reputation := int(step.get("reward_reputation", 0))
	if reward_cash > 0.0 or reward_reputation > 0:
		row_text += " | reward %.0f cash / +%s rep" % [reward_cash, reward_reputation]
	label.text = row_text
	row.add_child(label)
	return row


func _tutorial_status_color(status: String) -> Color:
	match status:
		"complete":
			return Color(0.50, 0.90, 0.55)
		"active":
			return Color(0.95, 0.76, 0.32)
		_:
			return Color(0.55, 0.66, 0.70)


func _update_bridge_label() -> void:
	if _bridge_status_value == null:
		return
	_bridge_status_value.text = "Running" if _bridge_running else "Stopped"
	_bridge_source_value.text = "Live" if snapshot.has("bridge") else "Fixture"


func _bridge_message() -> String:
	if not snapshot.has("bridge"):
		return "Fixture snapshot loaded; waiting for live bridge."
	var bridge: Dictionary = snapshot.get("bridge", {})
	if bridge.has("loaded_scenario"):
		return "Loaded scenario %s." % bridge.get("loaded_scenario", "")
	if bridge.has("loaded_path"):
		return "Loaded game from %s." % bridge.get("loaded_path", "")
	if bridge.has("saved_path"):
		return "Saved game to %s." % bridge.get("saved_path", "")
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
		var kind := "command_ok" if _flag(command_result.get("ok", false)) else "command_error"
		_push_alert(kind, str(command_result.get("message", "command result")))
		for route_alert in _route_debug_alerts(command_result):
			_push_alert(str(route_alert.get("kind", kind)), str(route_alert.get("message", "")))


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

	for alert in _current_tutorial_alerts():
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


func _route_debug_alerts(command_result: Dictionary) -> Array:
	var alerts: Array = []
	var command_type := str(command_result.get("type", ""))
	if not (command_type in ["PreviewCreateSchedule", "CreateSchedule", "PreviewUpdateSchedule", "UpdateSchedule"]):
		return alerts
	for item in _array(command_result.get("route_segments", [])):
		if typeof(item) != TYPE_DICTIONARY:
			continue
		var segment: Dictionary = item
		if _flag(segment.get("ok", false), false):
			continue
		var from_node := str(segment.get("from_node_id", "?"))
		var to_node := str(segment.get("to_node_id", "?"))
		alerts.append({
			"kind": "command_error",
			"message": "%s -> %s: %s" % [from_node, to_node, str(segment.get("reason", "blocked"))],
		})
		for blocked_item in _array(segment.get("blocked_links", [])):
			if typeof(blocked_item) != TYPE_DICTIONARY:
				continue
			var blocked: Dictionary = blocked_item
			alerts.append({
				"kind": "command_error",
				"message": "%s: %s" % [str(blocked.get("link_id", "link")), str(blocked.get("reason", "blocked"))],
			})
	return alerts


func _current_tutorial_alerts() -> Array:
	var alerts: Array = []
	var tutorial := _tutorial_snapshot()
	if tutorial.is_empty():
		return alerts
	for alert in _array(tutorial.get("alerts", [])):
		if typeof(alert) == TYPE_DICTIONARY:
			alerts.append(alert)
	for blocker in _array(tutorial.get("blockers", [])):
		if typeof(blocker) == TYPE_DICTIONARY:
			var blocker_data: Dictionary = blocker
			alerts.append({
				"kind": "tutorial_blocker",
				"message": str(blocker_data.get("message", blocker_data.get("code", "Tutorial blocker"))),
			})
	return alerts


func _current_link_alerts() -> Array:
	var alerts: Array = []
	for link in _array(snapshot.get("links", [])):
		if typeof(link) != TYPE_DICTIONARY:
			continue
		var link_data: Dictionary = link
		var link_id := str(link_data.get("id", "?"))
		if _flag(link_data.get("disrupted", false)):
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
		if capacity <= 0 and _flag(link_data.get("active", true), true):
			alerts.append({
				"kind": "congestion",
				"message": "%s: no effective capacity" % link_id,
			})
		elif slots_used > 0 and capacity > 0 and float(slots_used) / float(capacity) >= 0.80:
			alerts.append({
				"kind": "congestion",
				"message": "%s: %s/%s Railgate slots" % [link_id, slots_used, capacity],
			})
		elif capacity < base_capacity:
			alerts.append({
				"kind": "warning",
				"message": "%s: capacity %s/%s" % [link_id, capacity, base_capacity],
			})
	return alerts


func _build_alert_chip(alert: Dictionary) -> Control:
	var kind := str(alert.get("kind", "info"))
	var panel := PanelContainer.new()
	panel.add_theme_stylebox_override("panel", UITheme.alert_chip_style(kind))

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 7)
	panel.add_child(row)

	var prefix := Label.new()
	prefix.text = _alert_prefix(kind)
	UITheme.style_label_mono(prefix, UITheme.alert_chip_accent_color(kind))
	row.add_child(prefix)

	var label := Label.new()
	label.text = str(alert.get("message", ""))
	UITheme.style_label_mono(label, UITheme.INK_1)
	row.add_child(label)
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
		"tutorial":
			return "TUTORIAL"
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
		"tutorial":
			return Color(0.05, 0.20, 0.22, 0.96)
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
		"tutorial":
			return Color(0.24, 0.78, 0.82)
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


func _flag(value: Variant, default_value: bool = false) -> bool:
	match typeof(value):
		TYPE_BOOL:
			return value
		TYPE_INT, TYPE_FLOAT:
			return value != 0
		TYPE_STRING:
			return str(value).to_lower() in ["true", "1", "yes", "on"]
		TYPE_NIL:
			return default_value
		_:
			return default_value


func _schedule_route_label(schedule: Dictionary) -> String:
	var stop_ids := _array(schedule.get("route_stop_ids", []))
	if stop_ids.size() >= 2:
		return _join_values(stop_ids, " \u2192 ")
	return "%s \u2192 %s" % [schedule.get("origin", "?"), schedule.get("destination", "?")]


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
		var s_route = _schedule_route_label(schedule).to_lower()
		if filter_text.is_empty() or filter_text in s_id or filter_text in s_orig or filter_text in s_dest or filter_text in s_cargo or filter_text in s_route:
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
	panel.add_theme_stylebox_override("panel", UITheme.sched_row_style("default"))

	var box := VBoxContainer.new()
	box.add_theme_constant_override("separation", 6)
	panel.add_child(box)

	var row := HBoxContainer.new()
	row.custom_minimum_size = Vector2(500, 32)
	row.add_theme_constant_override("separation", 8)
	box.add_child(row)

	var enabled := _flag(schedule.get("active", false))
	var status_label := Label.new()
	status_label.custom_minimum_size = Vector2(36, 0)
	status_label.text = "ON" if enabled else "OFF"
	UITheme.style_label_mono(status_label, UITheme.GOOD if enabled else UITheme.INK_3)
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
	route_label.text = _schedule_route_label(schedule)
	route_label.tooltip_text = route_label.text
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

	var edit_row := HBoxContainer.new()
	edit_row.custom_minimum_size = Vector2(500, 32)
	edit_row.add_theme_constant_override("separation", 6)
	box.add_child(edit_row)

	var active_check := CheckBox.new()
	active_check.tooltip_text = "Schedule active"
	active_check.button_pressed = enabled
	edit_row.add_child(active_check)

	var cargo_option := OptionButton.new()
	cargo_option.custom_minimum_size = Vector2(102, 0)
	for cargo_id in _cargo_ids():
		cargo_option.add_item(str(cargo_id))
	_select_option_text(cargo_option, str(schedule.get("cargo", "")))
	edit_row.add_child(cargo_option)

	var units_spin := SpinBox.new()
	units_spin.min_value = 1
	units_spin.max_value = 999
	units_spin.step = 1
	units_spin.rounded = true
	units_spin.value = int(schedule.get("units_per_departure", 1))
	units_spin.custom_minimum_size = Vector2(76, 0)
	units_spin.tooltip_text = "Units per departure"
	edit_row.add_child(units_spin)

	var interval_spin := SpinBox.new()
	interval_spin.min_value = 1
	interval_spin.max_value = 999
	interval_spin.step = 1
	interval_spin.rounded = true
	interval_spin.value = int(schedule.get("interval_ticks", 1))
	interval_spin.custom_minimum_size = Vector2(76, 0)
	interval_spin.tooltip_text = "Interval ticks"
	edit_row.add_child(interval_spin)

	var stops_edit := LineEdit.new()
	stops_edit.placeholder_text = "stops"
	stops_edit.text = ",".join(_string_list(_array(schedule.get("stops", []))))
	stops_edit.tooltip_text = "Comma-separated intermediate stop node ids"
	stops_edit.custom_minimum_size = Vector2(96, 0)
	edit_row.add_child(stops_edit)

	var preview_button := Button.new()
	preview_button.text = "Preview"
	preview_button.pressed.connect(func():
		_on_schedule_preview_edit_pressed(schedule, cargo_option, units_spin, interval_spin, stops_edit, active_check)
	)
	edit_row.add_child(preview_button)

	var apply_button := Button.new()
	apply_button.text = "Apply"
	apply_button.pressed.connect(func():
		_on_schedule_apply_edit_pressed(schedule, cargo_option, units_spin, interval_spin, stops_edit, active_check)
	)
	edit_row.add_child(apply_button)

	var delete_button := Button.new()
	delete_button.text = "Delete"
	_set_button_icon(delete_button, "ui_cancel.svg")
	delete_button.pressed.connect(_on_schedule_delete_pressed.bind(str(schedule.get("id", ""))))
	edit_row.add_child(delete_button)

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
		if typeof(order) == TYPE_DICTIONARY and _flag(order.get("active", false)):
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
	_update_dispatch_builder_status()


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
	for item in _array(snapshot.get("cargo_catalog", [])):
		if typeof(item) == TYPE_DICTIONARY:
			cargo[str(item.get("id", ""))] = true
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


func _select_option_text(option: OptionButton, text: String) -> void:
	if option == null:
		return
	for index in range(option.item_count):
		if option.get_item_text(index) == text:
			option.select(index)
			return


func _string_list(values: Array) -> Array:
	var output: Array = []
	for value in values:
		output.append(str(value))
	return output


func _append_unique_strings(target: Array, values: Array) -> void:
	for value in values:
		var text := str(value)
		if text.is_empty():
			continue
		if not target.has(text):
			target.append(text)


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
		if _flag(link.get("disrupted", false)):
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

	_draw_cargo_flows()

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
			_draw_train_route_path(train)
		if not _draw_texture_centered(_train_asset(train), point, Vector2(30, 30)):
			draw_rect(Rect2(point - Vector2(6, 6), Vector2(12, 12)), Color(0.95, 0.95, 0.72))
		var train_id := str(train.get("id", ""))
		var label := "%s %s" % [train_id, train.get("status", "?")]
		draw_string(font, point + Vector2(16, -12), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 12, Color(0.96, 0.96, 0.80))
		if _selected_kind == "train" and _selected_id == train_id:
			draw_arc(point, 20.0, 0.0, TAU, 48, Color(1.0, 0.86, 0.32), 4.0)


func _draw_cargo_flows() -> void:
	var font := ThemeDB.fallback_font
	var flow_index := 0
	for flow in _array(snapshot.get("cargo_flows", [])):
		if typeof(flow) != TYPE_DICTIONARY:
			continue
		var route_nodes := _array(flow.get("route_node_ids", []))
		if route_nodes.size() < 2:
			continue
		var cargo := str(flow.get("cargo", ""))
		var base_color := _cargo_flow_color(cargo)
		var in_transit := int(flow.get("in_transit_units", 0))
		var units := int(flow.get("units_per_departure", 0))
		var width: float = 2.0 + clampf(float(max(in_transit, units)) / 12.0, 0.0, 3.0)
		var alpha := 0.30 if _flag(flow.get("active", true), true) else 0.12
		if in_transit > 0:
			alpha = 0.56
		var color := Color(base_color.r, base_color.g, base_color.b, alpha)
		var marker_color := Color(base_color.r, base_color.g, base_color.b, min(0.88, alpha + 0.24))
		var label_drawn := false
		var offset := float(flow_index % 4) * 2.5
		flow_index += 1
		for index in range(route_nodes.size() - 1):
			var from_node := str(route_nodes[index])
			var to_node := str(route_nodes[index + 1])
			if not node_positions.has(from_node) or not node_positions.has(to_node):
				continue
			var a: Vector2 = node_positions[from_node]
			var b: Vector2 = node_positions[to_node]
			var dir := (b - a).normalized()
			var perp := Vector2(-dir.y, dir.x) * offset
			draw_line(a + perp, b + perp, color, width)
			draw_circle(a.lerp(b, 0.5) + perp, 3.2, marker_color)
			if not label_drawn:
				var label := "%s %s/%s" % [cargo.replace("_", " ").capitalize(), in_transit, units]
				draw_string(font, a.lerp(b, 0.5) + perp + Vector2(5, 13), label, HORIZONTAL_ALIGNMENT_LEFT, -1, 10, marker_color)
				label_drawn = true


func _draw_train_route_path(train: Dictionary) -> void:
	var route_nodes := _array(train.get("route_node_ids", []))
	if route_nodes.size() < 2:
		return
	var route_color := Color(0.72, 0.92, 0.95, 0.38)
	var route_hot := Color(0.95, 0.98, 0.78, 0.58)
	for index in range(route_nodes.size() - 1):
		var from_node := str(route_nodes[index])
		var to_node := str(route_nodes[index + 1])
		if not node_positions.has(from_node) or not node_positions.has(to_node):
			continue
		var a: Vector2 = node_positions[from_node]
		var b: Vector2 = node_positions[to_node]
		draw_line(a, b, route_color, 2.0)
		draw_circle(a.lerp(b, 0.5), 2.5, route_hot)


func _cargo_flow_color(cargo: String) -> Color:
	match cargo:
		"food":
			return Color(0.42, 0.86, 0.42)
		"ore", "stone", "metal":
			return Color(0.74, 0.78, 0.82)
		"construction_materials", "parts", "machinery":
			return Color(0.98, 0.68, 0.25)
		"medical_supplies", "research_equipment":
			return Color(0.50, 0.84, 1.0)
		"water", "fuel":
			return Color(0.38, 0.62, 0.95)
		"electronics", "consumer_goods":
			return Color(0.86, 0.64, 0.94)
		_:
			return Color(0.82, 0.88, 0.78)


func _array(value: Variant) -> Array:
	if typeof(value) == TYPE_ARRAY:
		return value
	return []
