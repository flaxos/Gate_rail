extends Node2D

const WORLD_OFFSET := Vector2(180, 360)
const WORLD_RADIUS := 48.0
const NODE_RADIUS := 8.0
const ASSET_DIR := "res://assets/placeholders/"
const MAX_ALERT_HISTORY := 8
const MAX_ALERT_MESSAGE_LENGTH := 86
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

var _hud_label: Label
var _bridge_label: Label
var _error_label: Label
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
var _bridge_running := false
var _manual_order_sequence := 1
var _last_command_signature := ""


func _ready() -> void:
	_load_placeholder_assets()
	_build_ui()
	GateRailBridge.snapshot_received.connect(_on_snapshot_received)
	GateRailBridge.bridge_error.connect(_on_bridge_error)
	GateRailBridge.bridge_status_changed.connect(_on_bridge_status_changed)

	var fixture := GateRailBridge.load_fixture_snapshot()
	if not fixture.is_empty():
		_on_snapshot_received(fixture)
	_request_live_snapshot.call_deferred()


func _build_ui() -> void:
	var ui := CanvasLayer.new()
	add_child(ui)

	_build_control_panel(ui)
	_build_operations_panel(ui)
	_build_alert_strip(ui)


func _build_control_panel(ui: CanvasLayer) -> void:
	var panel := PanelContainer.new()
	panel.position = Vector2(16, 16)
	panel.custom_minimum_size = Vector2(560, 320)
	ui.add_child(panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(margin)

	var box := VBoxContainer.new()
	margin.add_child(box)

	_hud_label = Label.new()
	_hud_label.text = "GateRail Stage 2 scaffold"
	box.add_child(_hud_label)

	_bridge_label = Label.new()
	_bridge_label.text = "Bridge stopped | snapshot source: fixture"
	box.add_child(_bridge_label)

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

	_error_label = Label.new()
	_error_label.text = "Fixture snapshot loaded until live bridge responds."
	box.add_child(_error_label)

	var schedule_title := Label.new()
	schedule_title.text = "Schedules"
	box.add_child(schedule_title)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(520, 160)
	box.add_child(scroll)

	_schedule_list = VBoxContainer.new()
	scroll.add_child(_schedule_list)


func _build_operations_panel(ui: CanvasLayer) -> void:
	var panel := PanelContainer.new()
	panel.position = Vector2(760, 16)
	panel.custom_minimum_size = Vector2(500, 640)
	ui.add_child(panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 12)
	margin.add_theme_constant_override("margin_top", 10)
	margin.add_theme_constant_override("margin_right", 12)
	margin.add_theme_constant_override("margin_bottom", 10)
	panel.add_child(margin)

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

	var contract_scroll := ScrollContainer.new()
	contract_scroll.custom_minimum_size = Vector2(460, 125)
	box.add_child(contract_scroll)

	_contract_list = VBoxContainer.new()
	contract_scroll.add_child(_contract_list)

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

	var order_scroll := ScrollContainer.new()
	order_scroll.custom_minimum_size = Vector2(460, 145)
	box.add_child(order_scroll)

	_order_list = VBoxContainer.new()
	order_scroll.add_child(_order_list)


func _build_alert_strip(ui: CanvasLayer) -> void:
	var panel := PanelContainer.new()
	panel.position = Vector2(16, 660)
	panel.custom_minimum_size = Vector2(1248, 46)
	var panel_style := StyleBoxFlat.new()
	panel_style.bg_color = Color(0.035, 0.055, 0.07, 0.94)
	panel_style.border_color = Color(0.24, 0.38, 0.42)
	panel_style.set_border_width_all(1)
	panel_style.set_corner_radius_all(10)
	panel.add_theme_stylebox_override("panel", panel_style)
	ui.add_child(panel)

	var margin := MarginContainer.new()
	margin.add_theme_constant_override("margin_left", 10)
	margin.add_theme_constant_override("margin_top", 7)
	margin.add_theme_constant_override("margin_right", 10)
	margin.add_theme_constant_override("margin_bottom", 7)
	panel.add_child(margin)

	var row := HBoxContainer.new()
	row.add_theme_constant_override("separation", 8)
	margin.add_child(row)

	var title := Label.new()
	title.text = "Status"
	title.custom_minimum_size = Vector2(58, 0)
	title.modulate = Color(0.70, 0.88, 0.86)
	row.add_child(title)

	var scroll := ScrollContainer.new()
	scroll.custom_minimum_size = Vector2(1158, 32)
	scroll.size_flags_horizontal = Control.SIZE_EXPAND_FILL
	row.add_child(scroll)

	_alert_strip = HBoxContainer.new()
	_alert_strip.add_theme_constant_override("separation", 6)
	scroll.add_child(_alert_strip)
	_rebuild_alert_strip()


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
	_ingest_bridge_command_results()
	_rebuild_positions()
	_update_hud()
	_update_bridge_label()
	_rebuild_schedule_list()
	_update_finance_panel()
	_rebuild_contract_list()
	_rebuild_dispatch_options()
	_rebuild_order_list()
	_rebuild_alert_strip()
	_error_label.text = _bridge_message()
	queue_redraw()


func _on_bridge_error(message: String) -> void:
	_error_label.text = "Bridge: %s" % message
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


func _update_hud() -> void:
	var finance: Dictionary = snapshot.get("finance", {})
	_hud_label.text = "Tick %s | Cash %s | Reputation %s | Snapshot v%s" % [
		snapshot.get("tick", 0),
		finance.get("cash", 0),
		snapshot.get("reputation", 0),
		snapshot.get("snapshot_version", "?")
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
	if _bridge_label == null:
		return
	var state_text := "running" if _bridge_running else "stopped"
	var source_text := "live" if snapshot.has("bridge") else "fixture"
	var schedule_count := _array(snapshot.get("schedules", [])).size()
	_bridge_label.text = "Bridge %s | snapshot source: %s | schedules: %s" % [
		state_text,
		source_text,
		schedule_count
	]


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

	for schedule in schedules:
		if typeof(schedule) != TYPE_DICTIONARY:
			continue
		_schedule_list.add_child(_build_schedule_row(schedule))


func _build_schedule_row(schedule: Dictionary) -> Control:
	var row := HBoxContainer.new()
	row.custom_minimum_size = Vector2(500, 28)

	var enabled := bool(schedule.get("active", false))
	var status_label := Label.new()
	status_label.custom_minimum_size = Vector2(46, 0)
	status_label.text = "ON" if enabled else "OFF"
	status_label.modulate = Color(0.50, 0.90, 0.55) if enabled else Color(0.95, 0.45, 0.35)
	row.add_child(status_label)

	var cargo_icon := TextureRect.new()
	cargo_icon.custom_minimum_size = Vector2(22, 22)
	cargo_icon.stretch_mode = TextureRect.STRETCH_KEEP_ASPECT_CENTERED
	cargo_icon.texture = _texture(_cargo_asset(str(schedule.get("cargo", ""))))
	row.add_child(cargo_icon)

	var route_label := Label.new()
	route_label.custom_minimum_size = Vector2(330, 0)
	route_label.text = "%s | %s %s | %s -> %s | next %s" % [
		schedule.get("id", "?"),
		schedule.get("units_per_departure", 0),
		schedule.get("cargo", "?"),
		schedule.get("origin", "?"),
		schedule.get("destination", "?"),
		schedule.get("next_departure_tick", "?")
	]
	row.add_child(route_label)

	var toggle_button := Button.new()
	toggle_button.text = "Disable" if enabled else "Enable"
	_set_button_icon(toggle_button, "ui_schedule_off.svg" if enabled else "ui_schedule_on.svg")
	toggle_button.pressed.connect(_on_schedule_toggle_pressed.bind(str(schedule.get("id", "")), not enabled))
	row.add_child(toggle_button)

	return row


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

	for world in _array(snapshot.get("worlds", [])):
		var position: Dictionary = world.get("position", {})
		world_positions[world.get("id", "")] = WORLD_OFFSET + Vector2(
			float(position.get("x", 0)),
			float(position.get("y", 0))
		)

	var nodes_by_world: Dictionary = {}
	for node in _array(snapshot.get("nodes", [])):
		var world_id := str(node.get("world_id", ""))
		if not nodes_by_world.has(world_id):
			nodes_by_world[world_id] = []
		nodes_by_world[world_id].append(node)

	for world_id in nodes_by_world.keys():
		var nodes: Array = nodes_by_world[world_id]
		var center: Vector2 = world_positions.get(world_id, WORLD_OFFSET)
		var count: int = max(1, nodes.size())
		for index in range(nodes.size()):
			var angle := TAU * float(index) / float(count)
			var local := Vector2(cos(angle), sin(angle)) * 82.0
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
		draw_line(node_positions[origin], node_positions[destination], color, 4.0)

	for world in _array(snapshot.get("worlds", [])):
		var world_id := str(world.get("id", ""))
		var center: Vector2 = world_positions.get(world_id, WORLD_OFFSET)
		if not _draw_texture_centered(_world_asset(world), center, Vector2(76, 76)):
			draw_circle(center, WORLD_RADIUS, Color(0.12, 0.20, 0.24))
		draw_arc(center, WORLD_RADIUS, 0.0, TAU, 96, Color(0.56, 0.83, 0.78), 3.0)
		draw_string(font, center + Vector2(-58, -64), str(world.get("name", world_id)), HORIZONTAL_ALIGNMENT_LEFT, -1, 16, Color.WHITE)

	for node in _array(snapshot.get("nodes", [])):
		var node_id := str(node.get("id", ""))
		var point: Vector2 = node_positions.get(node_id, WORLD_OFFSET)
		var color := Color(0.76, 0.86, 0.92)
		if node.get("kind", "") == "gate_hub":
			color = Color(1.0, 0.72, 0.32)
		elif node.get("kind", "") == "settlement":
			color = Color(0.52, 0.88, 0.52)
		if not _draw_texture_centered(_node_asset(str(node.get("kind", ""))), point, Vector2(28, 28)):
			draw_circle(point, NODE_RADIUS, color)

	for train in _array(snapshot.get("trains", [])):
		var node_id := str(train.get("node_id", ""))
		if not node_positions.has(node_id):
			continue
		var point: Vector2 = node_positions[node_id] + Vector2(12, -12)
		if not _draw_texture_centered(_train_asset(train), point, Vector2(30, 30)):
			draw_rect(Rect2(point - Vector2(6, 6), Vector2(12, 12)), Color(0.95, 0.95, 0.72))

	var contract_y := 600.0
	for contract in _array(snapshot.get("contracts", [])).slice(0, 3):
		var line := "%s: %s/%s %s (%s)" % [
			contract.get("id", "?"),
			contract.get("progress", 0),
			contract.get("target", 0),
			contract.get("cargo", "?"),
			contract.get("status", "?")
		]
		draw_string(font, Vector2(24, contract_y), line, HORIZONTAL_ALIGNMENT_LEFT, -1, 15, Color(0.92, 0.94, 0.86))
		contract_y += 22.0


func _array(value: Variant) -> Array:
	if typeof(value) == TYPE_ARRAY:
		return value
	return []
