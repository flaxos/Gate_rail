extends Node

signal snapshot_received(snapshot: Dictionary)
signal bridge_error(message: String)
signal bridge_status_changed(running: bool)
signal auto_run_changed(running: bool)

const DEFAULT_FIXTURE := "res://fixtures/sprint9_snapshot.json"
const DEFAULT_BRIDGE_COMMAND_TEMPLATE := "cd %s && PYTHONPATH=src python3 -m gaterail.main --stdio"
const DEFAULT_AUTO_STEP_INTERVAL := 1.75
const DEFAULT_SAVE_PATH := "saves/godot_playtest.json"

var last_snapshot: Dictionary = {}
var last_save_path: String = DEFAULT_SAVE_PATH
var auto_step_interval: float = DEFAULT_AUTO_STEP_INTERVAL

var _stdio: FileAccess
var _stderr: FileAccess
var _reader_thread: Thread
var _write_mutex := Mutex.new()
var _pid := -1
var _running := false
var _stopping := false
var _auto_timer: Timer
var _auto_running := false
var _auto_step_pending := false


func _ready() -> void:
	_auto_timer = Timer.new()
	_auto_timer.wait_time = auto_step_interval
	_auto_timer.one_shot = false
	_auto_timer.timeout.connect(_on_auto_step_timeout)
	add_child(_auto_timer)


func load_fixture_snapshot(path: String = DEFAULT_FIXTURE) -> Dictionary:
	if not FileAccess.file_exists(path):
		_emit_error("missing snapshot fixture: %s" % path)
		return {}

	var text := FileAccess.get_file_as_string(path)
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		_emit_error("snapshot fixture is not a JSON object: %s" % path)
		return {}

	last_snapshot = parsed
	return parsed


func is_bridge_running() -> bool:
	return _running and _stdio != null and not _stopping


func is_auto_running() -> bool:
	return _auto_running


func is_auto_step_pending() -> bool:
	return _auto_step_pending


func set_auto_running(running: bool) -> void:
	if running == _auto_running:
		return
	_auto_running = running
	_auto_step_pending = false
	if _auto_running:
		if not is_bridge_running() and not start_bridge():
			_auto_running = false
			auto_run_changed.emit(false)
			return
		if _auto_timer != null:
			_auto_timer.wait_time = auto_step_interval
			_auto_timer.start()
	else:
		if _auto_timer != null:
			_auto_timer.stop()
	auto_run_changed.emit(_auto_running)


func start_bridge(command: String = "") -> bool:
	if is_bridge_running():
		return true
	if not OS.has_method("execute_with_pipe"):
		_emit_error("Godot build does not expose OS.execute_with_pipe")
		return false

	var bridge_command := command
	if bridge_command.is_empty():
		bridge_command = OS.get_environment("GATERAIL_BRIDGE_COMMAND")
	if bridge_command.is_empty():
		bridge_command = _default_bridge_command()

	var result: Variant = OS.execute_with_pipe("bash", PackedStringArray(["-lc", bridge_command]), false)
	if typeof(result) != TYPE_DICTIONARY:
		_emit_error("failed to start bridge process")
		return false

	var process: Dictionary = result
	_stdio = process.get("stdio")
	_stderr = process.get("stderr")
	_pid = int(process.get("pid", -1))
	if _stdio == null:
		_reset_bridge_handles()
		_emit_error("bridge process started without stdio pipe")
		return false

	_running = true
	_stopping = false
	_reader_thread = Thread.new()
	var err: Error = _reader_thread.start(_reader_loop)
	if err != OK:
		_running = false
		_reset_bridge_handles()
		_emit_error("failed to start bridge reader thread: %s" % err)
		return false
	bridge_status_changed.emit(true)
	return true


func stop_bridge() -> void:
	if not _running and _stdio == null:
		return
	set_auto_running(false)
	_stopping = true
	_running = false
	if _pid > 0:
		OS.kill(_pid)
	if _reader_thread != null and _reader_thread.is_started():
		_reader_thread.wait_to_finish()
	_reset_bridge_handles()
	bridge_status_changed.emit(false)


func send_message(message: Dictionary) -> bool:
	if not is_bridge_running() and not start_bridge():
		return false

	_write_mutex.lock()
	if not is_bridge_running():
		_write_mutex.unlock()
		_emit_error("bridge is not running")
		return false
	var line: String = JSON.stringify(message) + "\n"
	_stdio.store_string(line)
	_stdio.flush()
	_write_mutex.unlock()
	return true


func request_snapshot() -> bool:
	return send_message({"ticks": 0})


func step_ticks(ticks: int = 1) -> bool:
	return send_message({"ticks": max(0, ticks)})


func normalize_save_path(path: String) -> String:
	var text := path.strip_edges()
	if text.is_empty():
		return DEFAULT_SAVE_PATH
	if text.begins_with("res://") or text.begins_with("user://"):
		return ProjectSettings.globalize_path(text)
	if text.begins_with("/") or (text.length() >= 3 and text.substr(1, 2) == ":/"):
		return text
	if text.find("/") == -1 and text.find("\\") == -1:
		text = "saves/" + text
	if not text.ends_with(".json"):
		text += ".json"
	return text


func save_game(path: String, ticks: int = 0) -> bool:
	var resolved_path := normalize_save_path(path)
	last_save_path = resolved_path
	return send_message({
		"save_path": resolved_path,
		"ticks": max(0, ticks)
	})


func load_game(path: String, ticks: int = 0) -> bool:
	var resolved_path := normalize_save_path(path)
	last_save_path = resolved_path
	return send_message({
		"load_path": resolved_path,
		"ticks": max(0, ticks)
	})


func load_scenario(scenario_id: String, ticks: int = 0) -> bool:
	return send_message({
		"scenario": scenario_id,
		"ticks": max(0, ticks)
	})


func _on_auto_step_timeout() -> void:
	if not _auto_running or _auto_step_pending:
		return
	if step_ticks(1):
		_auto_step_pending = true
	else:
		set_auto_running(false)


func set_schedule_enabled(schedule_id: String, enabled: bool, ticks: int = 0) -> bool:
	return send_message({
		"commands": [
			{
				"type": "SetScheduleEnabled",
				"schedule_id": schedule_id,
				"enabled": enabled
			}
		],
		"ticks": max(0, ticks)
	})


func preview_update_schedule(schedule_id: String, fields: Dictionary, ticks: int = 0) -> bool:
	var command := fields.duplicate(true)
	command["type"] = "PreviewUpdateSchedule"
	command["schedule_id"] = schedule_id
	return send_message({
		"commands": [command],
		"ticks": max(0, ticks)
	})


func update_schedule(schedule_id: String, fields: Dictionary, ticks: int = 0) -> bool:
	var command := fields.duplicate(true)
	command["type"] = "UpdateSchedule"
	command["schedule_id"] = schedule_id
	return send_message({
		"commands": [command],
		"ticks": max(0, ticks)
	})


func delete_schedule(schedule_id: String, ticks: int = 0) -> bool:
	return send_message({
		"commands": [
			{
				"type": "DeleteSchedule",
				"schedule_id": schedule_id
			}
		],
		"ticks": max(0, ticks)
	})


func dispatch_order(
	order_id: String,
	train_id: String,
	origin: String,
	destination: String,
	cargo_type: String,
	requested_units: int,
	priority: int = 100,
	ticks: int = 0
) -> bool:
	return send_message({
		"commands": [
			{
				"type": "DispatchOrder",
				"order_id": order_id,
				"train_id": train_id,
				"origin": origin,
				"destination": destination,
				"cargo_type": cargo_type,
				"requested_units": requested_units,
				"priority": priority
			}
		],
		"ticks": max(0, ticks)
	})


func cancel_order(order_id: String, ticks: int = 0) -> bool:
	return send_message({
		"commands": [
			{
				"type": "CancelOrder",
				"order_id": order_id
			}
		],
		"ticks": max(0, ticks)
	})


func _reader_loop() -> void:
	while _running and _stdio != null:
		var line: String = _stdio.get_line()
		if not line.is_empty():
			call_deferred("_handle_bridge_line", line)
	if not _stopping:
		call_deferred("_handle_bridge_stopped")


func _handle_bridge_line(line: String) -> void:
	var parsed: Variant = JSON.parse_string(line)
	if typeof(parsed) != TYPE_DICTIONARY:
		_emit_error("bridge returned non-object JSON")
		return
	var frame: Dictionary = parsed
	if frame.has("bridge") and frame["bridge"].has("ok") and not frame["bridge"]["ok"]:
		_emit_error(str(frame["bridge"].get("error", "bridge error")))
		return
	if int(frame.get("snapshot_version", 0)) != 1:
		_emit_error("unsupported snapshot version: %s" % frame.get("snapshot_version", "missing"))
		return
	last_snapshot = frame
	_auto_step_pending = false
	snapshot_received.emit(frame)


func _handle_bridge_stopped() -> void:
	set_auto_running(false)
	_running = false
	_reset_bridge_handles()
	bridge_status_changed.emit(false)
	_emit_error("bridge process stopped")


func _reset_bridge_handles() -> void:
	_stdio = null
	_stderr = null
	_pid = -1
	_stopping = false


func _emit_error(message: String) -> void:
	if _auto_running:
		set_auto_running(false)
	bridge_error.emit(message)


func _default_bridge_command() -> String:
	var repo_root := ProjectSettings.globalize_path("res://../")
	return DEFAULT_BRIDGE_COMMAND_TEMPLATE % _shell_quote(repo_root)


func _shell_quote(value: String) -> String:
	return "'" + value.replace("'", "'\"'\"'") + "'"


func _exit_tree() -> void:
	stop_bridge()
