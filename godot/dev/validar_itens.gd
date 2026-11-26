extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## VALIDADOR DOS COLETÁVEIS E DAS TRAVAS (AJUSTES V2.2 §3.4).
##
## Coletáveis (pilhas, fichas, alicate e pistas): para cada um confere se ele
##   1. está FORA de colisores (ex.: a pilha do palco ficava enterrada dentro da plataforma);
##   2. é VISÍVEL: do olho do vigia até ele não há nenhuma malha no caminho;
##   3. é ALCANÇÁVEL: existe um ponto navegável perto, com caminho desde o início da noite
##      (portas destrancadas para o teste), e o raio de interação do vigia (2,2 m, o mesmo
##      do jogador.tscn) chega na área do item sem bater em parede ou móvel.
## Travas e peças de parede (cadeados, correntes, teclado, botão da porta de aço, disjuntores
## e folhas das portas): não podem estar dentro da parede; cadeado e corrente precisam estar
## numa porta e do lado de FORA (onde o vigia chega); teclado, botão e disjuntores encostados
## na parede (até 1,5 cm).
##
## Rodar sozinho: godot --headless --path godot res://dev/validar_itens.tscn
##   (grava docs/progresso/relatorio_itens.txt; usa o Fácil, que tem todas as pilhas e fichas)
##   ... res://dev/validar_itens.tscn -- cena=res://outra_cena.tscn   (confere outra versão do mapa)
## Usar de outro validador (com um mundo já montado e dentro da árvore):
##   var v: Node = preload("res://dev/validar_itens.gd").new()
##   add_child(v)
##   var r: Dictionary = await v.validar(mundo)   # {"erros": int, "linhas": Array[String]}

const UTIL := preload("res://dev/artes_util.gd")
const CENA := "res://cenas/mundo_v2.tscn"
const PILHA := preload("res://cenas/objetos/pilha.tscn")
## Mesmos números do vigia (cenas/jogador.tscn).
const ALTURA_OLHO := 1.6
const ALTURA_OLHO_AGACHADO := 0.95
const ALCANCE_INTERACAO := 2.2
## Distância máxima (na horizontal) entre o item e o chão navegável mais próximo.
const PERTO_DO_CHAO := 1.3
## Cômodo protegido por cada porta com corrente: a corrente fica do lado de FORA dele.
const COMODO_TRANCADO := {"corrente": "Deposito"}

var _linhas: Array[String] = []
var _erros := 0
var _malhas: Array = []
var _cache := {}
var _mundo: Node3D
var _mapa: RID
var _inicio := Vector3.ZERO
## Pontos de partida para "alcançável": o início da noite e as saídas dos dutos (o vigia se
## teletransporta pelo duto, então o que está depois dele também é alcançável).
var _partidas: Array[Vector3] = []


func _ready() -> void:
	if get_tree().current_scene != self:
		return  # usado por outro validador: ele chama validar()
	Jogo.modo_captura = true
	Jogo.trocar_cena_ao_terminar = false
	var dificuldade_antes: int = Config.dificuldade
	Config.dificuldade = 0  # Fácil: todas as pilhas e fichas ficam no mapa
	var cena := CENA
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("cena="):
			cena = arg.trim_prefix("cena=")  # conferir outra versão do mapa
	var mundo: Node3D = load(cena).instantiate()
	add_child(mundo)
	for i in 10:
		await get_tree().physics_frame
	var r := await validar(mundo)
	var t := Time.get_datetime_dict_from_system()
	var texto: Array[String] = ["RELATÓRIO DOS ITENS E TRAVAS — Turno da Noite (mapa V2)",
		"Gerado em %02d/%02d/%04d %02d:%02d por godot/dev/validar_itens.tscn (dificuldade Fácil: todos os candidatos no mapa)" % [
			t.day, t.month, t.year, t.hour, t.minute], ""]
	texto.append_array(r["linhas"])
	var caminho := ProjectSettings.globalize_path("res://").path_join("../docs/progresso/relatorio_itens.txt").simplify_path()
	var arq := FileAccess.open(caminho, FileAccess.WRITE)
	arq.store_string("\n".join(texto) + "\n")
	arq.close()
	print("\n".join(texto))
	Config.dificuldade = dificuldade_antes
	Jogo.trocar_cena_ao_terminar = true
	get_tree().quit(1 if int(r["erros"]) > 0 else 0)


## Confere um mundo já montado (a cena mundo_v2 dentro da árvore). 'abrir_portas' destranca e abre
## as portas e recalcula a navegação (como o teste_mapa), para medir se cada item é alcançável.
func validar(mundo: Node3D, abrir_portas := true) -> Dictionary:
	_mundo = mundo
	_formas.clear()
	_linhas.clear()
	_erros = 0
	_malhas = mundo.find_children("*", "MeshInstance3D", true, false)
	_inicio = (mundo.get_node("Jogador") as Node3D).global_position
	# As travas são conferidas com as portas FECHADAS (aberta, a corrente gira junto com a folha).
	_linhas.append("== TRAVAS, PORTAS E PEÇAS DE PAREDE (com as portas fechadas) ==")
	_validar_travas()
	_linhas.append("")
	var regiao := mundo.get_node("Navegacao") as NavigationRegion3D
	if abrir_portas:
		for porta in get_tree().get_nodes_in_group("porta"):
			porta.abrir_para_teste()
		# Espera o recálculo que o Mundo faz ao abrir (numa thread) terminar antes de recalcular com as
		# portas abertas; senão a malha antiga (portas fechadas) pode voltar por cima da nova.
		for i in 30:
			await get_tree().physics_frame
		regiao.bake_navigation_mesh(false)
	_mapa = regiao.get_navigation_map()
	# O servidor de navegação só usa a malha nova depois de sincronizar o mapa (alguns quadros).
	for i in 30:
		await get_tree().physics_frame
	_partidas = [_inicio]
	for g: Dictionary in PlantaV2.dados().get("duto_grades", []):
		_partidas.append(PlantaV2.mundo(float(g["x"]), float(g["z"])))
	_linhas.append("== COLETÁVEIS ==")
	_linhas.append("(posição em planta x, z e altura; 'chão' = ponto navegável mais perto; 'olho' = de onde o raio de interação sai)")
	_validar_pilhas()
	_validar_fichas()
	var alicate := mundo.find_child("Item__alicate", true, false) as Node3D
	if alicate:
		var malha := mundo.find_child("Alicate_Corta_Corrente", true, false) as Node3D
		_validar_item("Alicate (Item__alicate)", alicate.global_position, alicate.global_position, 0.35, [malha, alicate])
	else:
		_erro_simples("Item__alicate não existe no mapa")
	for p in mundo.find_children("Pista__*", "", true, false):
		var m := p as Node3D
		_validar_item("Pista (%s)" % m.name, m.global_position, m.global_position, 0.4, [m], false)
	_linhas.append("")
	_linhas.append("== SAÍDAS DOS DUTOS (dá para voltar a pé até o início, com as portas destrancadas?) ==")
	_validar_saidas_dos_dutos()
	_linhas.append("")
	_linhas.append("RESULTADO: %s" % ("SEM ERROS" if _erros == 0 else "%d ERRO(S) — veja as linhas [ERRO]" % _erros))
	return {"erros": _erros, "linhas": _linhas.duplicate()}


# ---------------------------------------------------------------------------
# Coletáveis
# ---------------------------------------------------------------------------

func _validar_pilhas() -> void:
	var pasta := _mundo.get_node_or_null("Pilhas")
	if pasta == null:
		_erro_simples("nó Pilhas não existe")
		return
	for p in pasta.get_children():
		var pilha := p as Node3D
		if pilha.is_queued_for_deletion():
			continue
		var modelo := pilha.get_node_or_null("Modelo") as Node3D
		var centro := pilha.global_position + Vector3(0, 0.12, 0)  # meio da pilha (cenas/objetos/pilha.tscn)
		var area := pilha.global_position + Vector3(0, 0.2, 0)
		_validar_item("Pilha (%s)" % pilha.name, centro, area, 0.45, [pilha, modelo])


func _validar_fichas() -> void:
	var pasta := _mundo.get_node_or_null("Marcadores/Fichas")
	if pasta == null:
		_erro_simples("nó Marcadores/Fichas não existe")
		return
	# Todos os pontos candidatos (as fichas sorteadas aparecem neles, a 2 cm do chão).
	for m in pasta.get_children():
		var ponto := m as Node3D
		var p := ponto.global_position
		var fichas_aqui: Array = get_tree().get_nodes_in_group("ficha").filter(
			func(f: Node) -> bool: return (f as Node3D).global_position.distance_to(p) < 0.1)
		var ignorar: Array = [ponto]
		ignorar.append_array(fichas_aqui)
		_validar_item("Ficha (%s)" % ponto.name, p + Vector3(0, 0.03, 0), p + Vector3(0, 0.17, 0), 0.25, ignorar)


## p_visual = onde o objeto está; p_area = centro da área de interação (raio aproximado 'raio_area').
func _validar_item(nome: String, p_visual: Vector3, p_area: Vector3, raio_area: float, ignorar: Array, checar_colisor := true) -> void:
	var problemas: Array[String] = []
	var espaco := _mundo.get_world_3d().direct_space_state
	# 1. Dentro de algum colisor do mundo?
	if checar_colisor:
		var dentro := _colisores_em(p_visual)
		if not dentro.is_empty():
			problemas.append("DENTRO do colisor " + ", ".join(dentro))
	# 3. Chão navegável perto e caminho desde o começo da noite
	var chao := NavigationServer3D.map_get_closest_point(_mapa, p_area)
	var horiz := Vector2(chao.x - p_area.x, chao.z - p_area.z).length()
	if horiz > PERTO_DO_CHAO:
		problemas.append("chão navegável mais perto está a %.1f m" % horiz)
	var origem_ok := ""
	var mais_perto := INF
	for i in _partidas.size():
		var de := NavigationServer3D.map_get_closest_point(_mapa, _partidas[i])
		var caminho := NavigationServer3D.map_get_path(_mapa, de, chao, true)
		var falta := INF if caminho.is_empty() else caminho[caminho.size() - 1].distance_to(chao)
		mais_perto = minf(mais_perto, falta)
		if falta <= 0.6:
			origem_ok = "a pé" if i == 0 else "pelo duto"
			break
	if origem_ok == "":
		problemas.append("sem caminho a pé nem pelos dutos desde o início da noite (o caminho para a %.1f m)" % mais_perto)
	# 2 e 3. Olho do vigia: em pé e, se não der, agachado
	var resultado := ""
	var melhor_olho := Vector3.ZERO
	for altura in [ALTURA_OLHO, ALTURA_OLHO_AGACHADO]:
		var olho := chao + Vector3(0, altura, 0)
		var d := olho.distance_to(p_area) - raio_area
		if d > ALCANCE_INTERACAO:
			resultado = "longe: %.2f m do olho até a área (alcance %.1f m)" % [d, ALCANCE_INTERACAO]
			continue
		var q := PhysicsRayQueryParameters3D.create(olho, p_area, 1)
		q.exclude = _rids_de(ignorar)
		var hit := espaco.intersect_ray(q)
		if not hit.is_empty() and olho.distance_to(hit["position"]) < olho.distance_to(p_area) - raio_area:
			resultado = "o raio de interação bate em %s antes" % _nome_colisor(hit["collider"])
			continue
		var bloqueio := _malha_no_caminho(olho, p_visual, ignorar)
		if bloqueio != "":
			resultado = "escondido atrás/dentro da malha " + bloqueio
			continue
		resultado = ""
		melhor_olho = olho
		break
	if resultado != "":
		problemas.append(resultado)
	var x := p_visual.x + 30.0
	var z := p_visual.z + 22.5
	var detalhe := "(%.1f, %.1f) alt %.2f m · %s · chão a %.1f m%s%s" % [x, z, p_visual.y, PlantaV2.comodo_em(p_visual), horiz,
		(" · chega " + origem_ok) if origem_ok != "" else "",
		(" · olho %s" % ("em pé" if is_equal_approx(melhor_olho.y - chao.y, ALTURA_OLHO) else "agachado")) if melhor_olho != Vector3.ZERO else ""]
	_registrar(nome, detalhe, problemas)


## Colisores (camada Mundo) que CONTÊM o ponto p.
## As colisões que vêm do Blender ("-colonly") viram malhas de triângulos (ConcavePolygonShape3D),
## e o motor de física não sabe dizer se um ponto está "dentro" de uma malha. Então fazemos o
## teste clássico de Computação Gráfica: um raio saindo do ponto cruza a superfície fechada um
## número ÍMPAR de vezes se o ponto está dentro (e PAR se está fora). Testamos 3 direções e
## a maioria decide (um raio que passa raspando numa aresta pode contar errado).
var _formas: Array = []  # [{nome, caixa (AABB no mundo), tri (PackedVector3Array no mundo)}]


func _colisores_em(p: Vector3) -> Array[String]:
	if _formas.is_empty():
		_ler_formas()
	var nomes: Array[String] = []
	for f: Dictionary in _formas:
		if not (f["caixa"] as AABB).grow(0.001).has_point(p):
			continue
		var dentro := 0
		for d in [Vector3(0.0123, 1, 0.0371).normalized(), Vector3(1, 0.0217, 0.0433).normalized(), Vector3(0.0311, 0.0173, 1).normalized()]:
			var cruzou := 0
			var tri: PackedVector3Array = f["tri"]
			for k in range(0, tri.size(), 3):
				if Geometry3D.ray_intersects_triangle(p, d, tri[k], tri[k + 1], tri[k + 2]) != null:
					cruzou += 1
			if cruzou % 2 == 1:
				dentro += 1
		if dentro >= 2 and not nomes.has(String(f["nome"])):
			nomes.append(String(f["nome"]))
	return nomes


func _ler_formas() -> void:
	for no in _mundo.find_children("*", "CollisionShape3D", true, false):
		var cs := no as CollisionShape3D
		var corpo := cs.get_parent() as CollisionObject3D
		if corpo == null or corpo is PortaV2 or (corpo.collision_layer & 1) == 0 or cs.disabled:
			continue
		var faces := PackedVector3Array()
		if cs.shape is ConcavePolygonShape3D:
			faces = (cs.shape as ConcavePolygonShape3D).get_faces()
		elif cs.shape is BoxShape3D or cs.shape is ConvexPolygonShape3D:
			faces = cs.shape.get_debug_mesh().get_faces()
		if faces.is_empty():
			continue
		var xf := cs.global_transform
		var caixa := AABB(xf * faces[0], Vector3.ZERO)
		for k in faces.size():
			faces[k] = xf * faces[k]
			caixa = caixa.expand(faces[k])
		_formas.append({"nome": _nome_colisor(corpo), "caixa": caixa, "tri": faces})


func _nome_colisor(c: Object) -> String:
	var n := c as Node
	if n == null:
		return "?"
	if n is PortaV2:
		return "porta " + String(n.get_parent().name)
	return String(n.name)


func _rids_de(nos: Array) -> Array[RID]:
	var rids: Array[RID] = []
	for no in nos:
		if no is CollisionObject3D:
			rids.append((no as CollisionObject3D).get_rid())
		if no is Node:
			for filho in (no as Node).find_children("*", "CollisionObject3D", true, false):
				rids.append((filho as CollisionObject3D).get_rid())
	return rids


## Nome da primeira malha VISÍVEL entre 'de' e 'ate' (menos as do próprio item); "" se o caminho está livre.
func _malha_no_caminho(de: Vector3, ate: Vector3, ignorar: Array) -> String:
	var dir := (ate - de)
	var dist := dir.length() - 0.03
	dir = dir.normalized()
	var caixa := AABB(de, Vector3.ZERO).expand(ate).grow(0.05)
	var melhor := INF
	var nome := ""
	for mi in _malhas:
		var m := mi as MeshInstance3D
		if m.mesh == null or not m.is_visible_in_tree() or not (m.global_transform * m.get_aabb()).intersects(caixa):
			continue
		var pular := false
		for no in ignorar:
			if no is Node and ((no as Node) == m or (no as Node).is_ancestor_of(m)):
				pular = true
		if pular:
			continue
		var tri := UTIL.triangulos_perto([m], caixa, null, _cache)
		var d := UTIL.raio(tri, de, dir, dist)
		if d < melhor:
			melhor = d
			nome = String(m.name)
	return nome


## Quem sai do duto num cômodo precisa conseguir voltar andando (senão fica preso lá dentro).
func _validar_saidas_dos_dutos() -> void:
	var inicio := NavigationServer3D.map_get_closest_point(_mapa, _inicio)
	for g: Dictionary in PlantaV2.dados().get("duto_grades", []):
		var saida := NavigationServer3D.map_get_closest_point(_mapa, PlantaV2.mundo(float(g["x"]), float(g["z"])))
		var caminho := NavigationServer3D.map_get_path(_mapa, saida, inicio, true)
		var falta := INF if caminho.is_empty() else caminho[caminho.size() - 1].distance_to(inicio)
		var problemas: Array[String] = []
		if falta > 0.6:
			var fim := caminho[caminho.size() - 1] if not caminho.is_empty() else saida
			problemas.append("sem caminho a pé de volta: o caminho para em (%.1f, %.1f), %s" % [fim.x + 30.0, fim.z + 22.5,
				PlantaV2.comodo_em(fim)])
		_registrar("Duto: saída em %s" % String(g["comodo"]), "(%.1f, %.1f)" % [float(g["x"]), float(g["z"])], problemas)


# ---------------------------------------------------------------------------
# Travas, portas e peças de parede
# ---------------------------------------------------------------------------

func _validar_travas() -> void:
	var cenario := _mundo.get_node("Navegacao/Cenario")
	var planta := PlantaV2.dados()
	for no in cenario.find_children("*", "MeshInstance3D", true, false):
		var m := no as MeshInstance3D
		var nome := String(m.name)
		var tipo := ""
		if (nome.ends_with("_Cadeado") or nome.ends_with("_Corrente")) and not nome.begins_with("Alicate"):
			tipo = "tranca"
		elif nome == "Teclado_Eletrica" or nome == "Botao_Porta_Seguranca" or (nome.begins_with("Disjuntor_") and nome.count("_") == 1):
			tipo = "parede"
		elif nome.begins_with("Porta__") and nome.count("__") == 2:
			tipo = "porta"
		if tipo == "":
			continue
		var problemas: Array[String] = []
		var centro := (m.global_transform * m.get_aabb()).get_center()
		var paredes := _colisores_em(centro).filter(func(c: String) -> bool: return c.contains("Paredes"))
		if not paredes.is_empty():
			problemas.append("centro DENTRO da parede (%s)" % ", ".join(paredes))
		var detalhe := "(%.2f, %.2f) alt %.2f m · %s" % [centro.x + 30.0, centro.z + 22.5, centro.y, PlantaV2.comodo_em(centro)]
		match tipo:
			"tranca":
				var porta := _porta_mais_perto(planta, centro)
				if porta.is_empty() or float(porta["dist"]) > float(porta["largura"]) / 2.0 + 0.5:
					problemas.append("não está em nenhuma porta (a mais perto fica a %.1f m)" % float(porta.get("dist", INF)))
				else:
					detalhe += " · porta %s em %s=%s" % [porta["tipo"], "z" if porta["eixo"] == "z" else "x", str(porta["fixo"])]
					var trancado: String = COMODO_TRANCADO.get(String(porta["tipo"]), "")
					if trancado != "" and PlantaV2.comodo_em(centro) == trancado:
						problemas.append("está do lado de DENTRO (%s): o vigia não vê a tranca de onde chega" % trancado)
			"parede":
				var folga := _folga_da_parede(m)
				detalhe += " · folga até a parede: %s" % ("sem parede atrás" if folga == INF else "%.1f cm" % (folga * 100.0))
				if folga > 0.015:
					problemas.append("solto da parede (%.1f cm)" % (folga * 100.0))
		_registrar(("Tranca " if tipo == "tranca" else ("Porta " if tipo == "porta" else "")) + nome, detalhe, problemas)
	# Vãos de porta: 0,7 m de cada lado do vão tem que estar livre (senão a porta "abre para a parede").
	for porta: Dictionary in planta.get("portas", []):
		if String(porta["tipo"]) == "catraca":
			continue
		var x := float(porta["centro"]) if porta["eixo"] == "z" else float(porta["fixo"])
		var z := float(porta["fixo"]) if porta["eixo"] == "z" else float(porta["centro"])
		var normal := Vector3(0, 0, 1) if porta["eixo"] == "z" else Vector3(1, 0, 0)
		var problemas: Array[String] = []
		for lado in [-1.0, 1.0]:
			for h in [0.3, 1.0, 1.7]:
				var ponto: Vector3 = PlantaV2.mundo(x, z, h) + normal * 0.7 * float(lado)
				var bloqueio := _colisores_em(ponto).filter(func(c: String) -> bool: return not c.begins_with("porta "))
				if not bloqueio.is_empty():
					problemas.append("lado %s do vão bloqueado a %.1f m de altura por %s" % [PlantaV2.comodo_em(ponto), h,
						", ".join(bloqueio)])
					break
		_registrar("Vão da porta %s (%s=%s, %s)" % [porta["tipo"], "z" if porta["eixo"] == "z" else "x", str(porta["fixo"]),
			str(porta["centro"])], "%.1f m de largura" % float(porta["largura"]), problemas)


func _porta_mais_perto(planta: Dictionary, p: Vector3) -> Dictionary:
	var x := p.x + 30.0
	var z := p.z + 22.5
	var melhor := {}
	for porta: Dictionary in planta.get("portas", []):
		var c := Vector2(float(porta["centro"]), float(porta["fixo"])) if porta["eixo"] == "z" \
			else Vector2(float(porta["fixo"]), float(porta["centro"]))
		var d := Vector2(x, z).distance_to(c)
		if melhor.is_empty() or d < float(melhor["dist"]):
			melhor = porta.duplicate()
			melhor["dist"] = d
	return melhor


## Distância entre as costas da peça e a parede (raio para trás, ao longo do -Z local = o "atrás").
func _folga_da_parede(m: MeshInstance3D) -> float:
	var aabb := m.get_aabb()
	var frente := m.global_basis.z.normalized()
	var centro := m.global_transform * aabb.get_center()
	# meia espessura da peça na direção da frente
	var meia := 0.0
	for i in 8:
		meia = maxf(meia, (m.global_transform * aabb.get_endpoint(i) - centro).dot(-frente))
	var q := PhysicsRayQueryParameters3D.create(centro, centro - frente * 0.5, 1)
	var hit := _mundo.get_world_3d().direct_space_state.intersect_ray(q)
	if hit.is_empty():
		return INF
	return maxf(centro.distance_to(hit["position"]) - meia, 0.0)


# ---------------------------------------------------------------------------

func _erro_simples(texto: String) -> void:
	_erros += 1
	_linhas.append("  [ERRO]  " + texto)


func _registrar(nome: String, detalhe: String, problemas: Array[String]) -> void:
	if not problemas.is_empty():
		_erros += 1
	_linhas.append("  %s %s — %s" % ["[ERRO] " if not problemas.is_empty() else "[ok]   ", nome, detalhe])
	for p in problemas:
		_linhas.append("           ERRO: " + p)
