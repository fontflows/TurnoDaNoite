extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Teste automático do mapa: um "robô" anda com o vigia (física de verdade) até o
## centro de cada cômodo, seguindo a navegação. Confere se chega em todos, se nunca
## cai do mapa e se as paredes bloqueiam (raios de teste).
## Uso: godot --headless --path . res://dev/teste_mapa.tscn

# V2: os destinos são os pontos livres da planta (patrulha, fichas e pilhas), em todos os cômodos.
const CENA := "res://cenas/mundo_v2.tscn"
const PLANTA := "res://assets/dados/planta_v2.json"
var DESTINOS := {}
const TEMPO_MAXIMO_POR_DESTINO := 40.0

var _mundo: Node3D
var _jogador: CharacterBody3D


func _ready() -> void:
	Engine.time_scale = 1.0  # passos pequenos: o robô segue o caminho com precisão
	Jogo.modo_captura = true
	var planta = JSON.parse_string(FileAccess.get_file_as_string(PLANTA))
	for lista in ["patrulha", "fichas", "pilhas"]:
		for i in planta["pontos"][lista].size():
			var p: Array = planta["pontos"][lista][i]
			DESTINOS["%s %d (%.0f, %.0f)" % [lista, i + 1, p[0], p[1]]] = Vector3(p[0] - 30.0, 0.0, p[1] - 22.5)
	_mundo = load(CENA).instantiate()
	add_child(_mundo)
	for i in 5:
		await get_tree().physics_frame
	_jogador = get_tree().get_first_node_in_group("jogador")
	_jogador.set_physics_process(false)  # o robô controla o movimento
	var falhas := 0
	# Este teste confere o MAPA (paredes, móveis, escadas), não a progressão: abre as portas
	# trancadas e recalcula a navegação. A progressão é conferida em teste_cadeia.tscn.
	for porta in get_tree().get_nodes_in_group("porta"):
		porta.abrir_para_teste()
	for i in 30:
		await get_tree().physics_frame  # a física precisa "ver" as portas já giradas antes de recalcular
	_mundo.get_node("Navegacao").bake_navigation_mesh(false)
	for i in 30:
		await get_tree().physics_frame

	falhas += _testar_paredes()

	var regiao: NavigationRegion3D = _mundo.get_node("Navegacao")
	var mapa: RID = regiao.get_navigation_map()
	print("[teste] navmesh: %d polígonos, %d vértices" % [regiao.navigation_mesh.get_polygon_count(), regiao.navigation_mesh.get_vertices().size()])
	var corpos := _mundo.find_children("*", "StaticBody3D", true, false)
	print("[teste] corpos estáticos (colisão): %d" % corpos.size())
	# O servidor de navegação só "enxerga" a navmesh nova depois de sincronizar o mapa.
	for i in 60:
		if NavigationServer3D.map_get_closest_point(mapa, _jogador.global_position) != Vector3.ZERO:
			break
		await get_tree().physics_frame
	print("[teste] regiões no mapa: %d, mapa ativo: %s, regiao habilitada: %s, rid da região no mapa: %s" % [
		NavigationServer3D.map_get_regions(mapa).size(), NavigationServer3D.map_is_active(mapa),
		regiao.enabled, NavigationServer3D.region_get_map(regiao.get_rid()) == mapa])
	print("[teste] mapa sincronizado: iteração %d, ponto navegável mais perto do início: %s" % [
		NavigationServer3D.map_get_iteration_id(mapa),
		NavigationServer3D.map_get_closest_point(mapa, _jogador.global_position)])
	var aabb := AABB()
	for v in regiao.navigation_mesh.get_vertices():
		aabb = aabb.expand(v)
	print("[teste] área da navmesh: ", aabb)
	# Filtro opcional: -- so=pilhas (roda só os destinos que começam com esse texto).
	var filtro := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("so="):
			filtro = arg.trim_prefix("so=")
	for nome in DESTINOS:
		if filtro != "" and not String(nome).begins_with(filtro):
			continue
		# O destino vai para o ponto navegável mais próximo (ex.: em cima do palco).
		var ok := await _andar_ate(mapa, NavigationServer3D.map_get_closest_point(mapa, DESTINOS[nome]))
		print("[teste] ", "ok   " if ok else "FALHA", " chegou em: ", nome, "  pos=", _jogador.global_position.snapped(Vector3.ONE * 0.1))
		if not ok:
			falhas += 1
	print("[teste] %d falha(s)" % falhas)
	Engine.time_scale = 1.0
	get_tree().quit(1 if falhas > 0 else 0)


func _andar_ate(mapa: RID, destino: Vector3) -> bool:
	var tempo := 0.0
	while tempo < TEMPO_MAXIMO_POR_DESTINO:
		var caminho := NavigationServer3D.map_get_path(mapa, _jogador.global_position, destino, true)
		if caminho.is_empty():
			print("[teste]   sem caminho até ", destino)
			return false
		# caminho[0] é só a projeção da posição atual (numa rampa ela pode cair atrás do robô): pula.
		var proximo := caminho[caminho.size() - 1]
		for p in caminho.slice(1):
			if Vector2(p.x - _jogador.global_position.x, p.z - _jogador.global_position.z).length() > 0.15:
				proximo = p
				break
		var dir := proximo - _jogador.global_position
		dir.y = 0
		var plano := Vector2(_jogador.global_position.x - destino.x, _jogador.global_position.z - destino.z)
		if plano.length() < 0.8 and absf(_jogador.global_position.y - destino.y) < 0.4:
			return true
		_jogador.velocity.x = dir.normalized().x * 4.0
		_jogador.velocity.z = dir.normalized().z * 4.0
		_jogador.velocity.y = 0.0 if _jogador.is_on_floor() else _jogador.velocity.y - 9.8 / 60.0
		_jogador.move_and_slide()
		if OS.get_cmdline_user_args().has("debug") and int(tempo * 60) % 60 == 0 and tempo > 3.0:
			var c := _jogador.get_last_slide_collision()
			print("[teste]   t=%.0f pos %s vel %s chao %s toca %s" % [tempo, _jogador.global_position.snapped(Vector3.ONE * 0.01), _jogador.velocity.snapped(Vector3.ONE * 0.01), _jogador.is_on_floor(), (str(c.get_collider().name) + " n=" + str(c.get_normal().snapped(Vector3.ONE * 0.01))) if c else "-"])
		if _jogador.global_position.y < -1.0:
			print("[teste]   CAIU DO MAPA em ", _jogador.global_position)
			return false
		await get_tree().physics_frame
		tempo += 1.0 / 60.0
	var resto := NavigationServer3D.map_get_path(mapa, _jogador.global_position, destino, true)
	print("[teste]   caminho restante: ", resto.slice(0, 6))
	return false


## Raios horizontais que devem bater em paredes (se não baterem, a colisão sumiu).
func _testar_paredes() -> int:
	var espaco := _mundo.get_world_3d().direct_space_state
	# Planta da V2 -> Godot: X = x - 30, Z = z - 22,5. Raios que atravessam paredes sem porta.
	var testes := [
		["parede externa oeste (corredor)", Vector3(-25, 1, -5), Vector3(-35, 1, -5)],
		["parede externa norte (salão)", Vector3(-5, 1, -14.5), Vector3(-5, 1, -27.5)],
		["parede corredor/salão (x=10)", Vector3(-20, 1, -5), Vector3(-20, 1, -9.5)],
		["parede corredor das festas/Estrelas", Vector3(3.5, 1, -2.5), Vector3(7, 1, -2.5)],
		["piso", Vector3(0, 1, 0), Vector3(0, -2, 0)],
	]
	var falhas := 0
	for t in testes:
		var r := espaco.intersect_ray(PhysicsRayQueryParameters3D.create(t[1], t[2], 1))
		var ok := not r.is_empty()
		print("[teste] ", "ok   " if ok else "FALHA", " colisão: ", t[0], ("  bateu em " + str(r.position.snapped(Vector3.ONE * 0.01))) if ok else "")
		if not ok:
			falhas += 1
	return falhas
