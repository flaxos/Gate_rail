extends SceneTree


func _initialize() -> void:
	call_deferred("_run_smoke")


func _fail(message: String) -> void:
	push_error(message)
	quit(1)


func _count_visible_controls(node: Node) -> int:
	var count: int = 0
	if node is Control:
		var control := node as Control
		if control.visible:
			count += 1
	for child in node.get_children():
		count += _count_visible_controls(child)
	return count


func _run_smoke() -> void:
	var snapshot_path: String = OS.get_environment("GATERAIL_SMOKE_SNAPSHOT")
	if snapshot_path.is_empty():
		_fail("GATERAIL_SMOKE_SNAPSHOT is required")
		return
	if not FileAccess.file_exists(snapshot_path):
		_fail("smoke snapshot not found: %s" % snapshot_path)
		return

	var text: String = FileAccess.get_file_as_string(snapshot_path)
	var parsed: Variant = JSON.parse_string(text)
	if typeof(parsed) != TYPE_DICTIONARY:
		_fail("smoke snapshot is not a JSON object")
		return

	var snapshot: Dictionary = parsed
	var tutorial: Dictionary = snapshot.get("tutorial", {}) if typeof(snapshot.get("tutorial", {})) == TYPE_DICTIONARY else {}
	if str(tutorial.get("id", "")) != "tutorial_local_logistics":
		_fail("smoke snapshot is not tutorial_local_logistics")
		return

	var nav: Node = root.get_node_or_null("SceneNav")
	if nav == null:
		_fail("SceneNav autoload is missing")
		return
	nav.set("selected_world_id", "atlas")

	var bridge: Node = root.get_node_or_null("GateRailBridge")
	if bridge == null:
		_fail("GateRailBridge autoload is missing")
		return
	bridge.set("last_snapshot", snapshot)

	var packed: PackedScene = load("res://scenes/local_region.tscn") as PackedScene
	if packed == null:
		_fail("failed to load local_region.tscn")
		return

	var render_viewport: SubViewport = SubViewport.new()
	render_viewport.size = Vector2i(1280, 720)
	render_viewport.disable_3d = true
	render_viewport.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	root.add_child(render_viewport)

	var scene: Node = packed.instantiate()
	render_viewport.add_child(scene)
	for i in range(6):
		await process_frame

	var world_id: String = str(scene.get("_world_id"))
	if world_id != "atlas":
		_fail("local region selected world %s, expected atlas" % world_id)
		return

	var selected_world_raw: Variant = scene.get("_selected_world")
	if typeof(selected_world_raw) != TYPE_DICTIONARY or selected_world_raw.is_empty():
		_fail("local region did not select an Atlas world payload")
		return

	var entities_raw: Variant = scene.get("_world_operational_entities")
	if typeof(entities_raw) != TYPE_ARRAY:
		_fail("local region operational entities are not an array")
		return
	var entities: Array = entities_raw
	if entities.is_empty():
		_fail("local region operational entities are blank")
		return

	var area_raw: Variant = scene.get("_world_operational_area")
	if typeof(area_raw) != TYPE_DICTIONARY:
		_fail("local region operational area is not a dictionary")
		return
	var area: Dictionary = area_raw
	var grid: Dictionary = area.get("grid", {}) if typeof(area.get("grid", {})) == TYPE_DICTIONARY else {}
	var has_occupancy: bool = grid.get("has_cell_occupancy", false) == true
	if str(grid.get("kind", "")) != "local_grid" or not has_occupancy:
		_fail("local region did not load the persisted local grid")
		return

	var canvas_raw: Variant = scene.get("_canvas_panel")
	if typeof(canvas_raw) != TYPE_OBJECT:
		_fail("local region canvas panel is missing")
		return
	var canvas := canvas_raw as Control
	if canvas == null or not canvas.is_inside_tree() or not canvas.visible:
		_fail("local region canvas panel is not visible in the scene tree")
		return
	if canvas.size.x <= 0.0 or canvas.size.y <= 0.0:
		_fail("local region canvas panel has no drawable area")
		return

	var region_label_raw: Variant = scene.get("_region_label")
	var region_label := region_label_raw as Label
	if region_label == null or not region_label.text.contains("ATLAS"):
		_fail("local region header did not bind the Atlas world")
		return

	var visible_controls: int = _count_visible_controls(scene)
	if visible_controls < 20:
		_fail("local region UI tree is too sparse to be player-visible")
		return

	var visible_entity_positions: int = 0
	for entity in entities:
		if typeof(entity) != TYPE_DICTIONARY:
			continue
		var projected_raw: Variant = scene.call("_operational_entity_position", entity)
		if typeof(projected_raw) != TYPE_VECTOR2:
			continue
		var projected: Vector2 = projected_raw
		if projected.x >= 0.0 and projected.y >= 0.0 and projected.x <= canvas.size.x and projected.y <= canvas.size.y:
			visible_entity_positions += 1
	if visible_entity_positions <= 0:
		_fail("local region operational entities project outside the canvas")
		return

	if OS.get_environment("GATERAIL_SMOKE_REQUIRE_PIXELS") == "1":
		var texture: ViewportTexture = render_viewport.get_texture()
		if texture == null:
			_fail("local region viewport did not produce a texture")
			return
		var image: Image = texture.get_image()
		if image == null or image.is_empty():
			_fail("local region viewport did not produce an image")
			return
		var nonblack_pixels: int = 0
		var sample_step: int = max(1, int(min(image.get_width(), image.get_height()) / 24))
		for y in range(0, image.get_height(), sample_step):
			for x in range(0, image.get_width(), sample_step):
				var pixel: Color = image.get_pixel(x, y)
				if pixel.r > 0.01 or pixel.g > 0.01 or pixel.b > 0.01:
					nonblack_pixels += 1
		if nonblack_pixels <= 0:
			_fail("local region viewport rendered blank pixels")
			return

	print("GateRail local region smoke ok: atlas entities=%d visible=%d controls=%d" % [entities.size(), visible_entity_positions, visible_controls])
	quit(0)
