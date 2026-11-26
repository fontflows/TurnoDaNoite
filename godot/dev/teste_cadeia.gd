extends Node
## FERRAMENTA DE DESENVOLVIMENTO: joga a CADEIA DE PROGRESSÃO inteira do mapa da V2, sem inimigos.
## Em cada passo confere, pela navegação, que o vigia CONSEGUE ANDAR até o próximo objetivo
## (com as portas como estão naquele momento) e depois faz a interação (E) por código.
## Os minigames são vencidos com vencer_agora() (o mesmo que o F7 do debug).
##
## Rodar: godot --headless --path godot res://dev/teste_cadeia.tscn
## Opções:  -- dificuldade=0|1|2

const CENA := "res://cenas/mundo_v2.tscn"

var _mundo: Node3D
var _jogador: CharacterBody3D
var _prog: ProgressaoV2
var _mapa: RID
var _falhas := 0
var _venceu := false


func _ready() -> void:
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("dificuldade="):
			Config.dificuldade = int(arg.trim_prefix("dificuldade="))
	Jogo.modo_captura = false
	_mundo = load(CENA).instantiate()
	_mundo.get_node("Montador").codigo_fixo = ""  # sorteada, como no jogo
	add_child(_mundo)
	Jogo.ia_ativa = false
	Jogo.invencivel = true
	Jogo.vitoria.connect(func() -> void: _venceu = true)
	_jogador = _mundo.get_node("Jogador")
	_prog = _mundo.get_node("Montador/ProgressaoV2")
	_mapa = _mundo.get_node("Navegacao").get_navigation_map()
	for i in 30:
		await get_tree().physics_frame
	print("[cadeia] dificuldade %s, senha sorteada %s, fichas no mapa %d" % [Jogo.dificuldade.nome, Jogo.codigo,
		get_tree().get_nodes_in_group("ficha").size()])
	await _rodar()
	print("[cadeia] %d falha(s)" % _falhas)
	Config.dificuldade = 1
	get_tree().quit(1 if _falhas > 0 else 0)


func _conferir(ok: bool, texto: String) -> void:
	if ok:
		print("[cadeia] ok    ", texto)
	else:
		_falhas += 1
		print("[cadeia] FALHA ", texto)


## O vigia consegue ANDAR de onde está até perto do alvo?
func _alcanca(alvo: Vector3, folga := 1.6, mostrar := false) -> bool:
	var de := NavigationServer3D.map_get_closest_point(_mapa, _jogador.global_position)
	var ate := NavigationServer3D.map_get_closest_point(_mapa, alvo)
	var caminho := NavigationServer3D.map_get_path(_mapa, de, ate, true)
	var fim: Vector3 = caminho[caminho.size() - 1] if not caminho.is_empty() else de
	var ok := Vector2(fim.x - alvo.x, fim.z - alvo.z).length() <= folga and Vector2(ate.x - alvo.x, ate.z - alvo.z).length() <= folga
	if mostrar and not ok:
		print("[cadeia]       de %s (%s) -> alvo %s (%s); ponto da navegação mais perto %s; caminho termina em %s (%s)" % [
			_planta(de), PlantaV2.comodo_em(de), _planta(alvo), PlantaV2.comodo_em(alvo), _planta(ate), _planta(fim), PlantaV2.comodo_em(fim)])
	return ok


func _diagnosticar_vao(a: Vector3, b: Vector3) -> void:
	var q := PhysicsRayQueryParameters3D.create(a, b, 1)
	var r := _mundo.get_world_3d().direct_space_state.intersect_ray(q)
	print("[cadeia]       raio no vão %s -> %s: %s" % [_planta(a), _planta(b),
		(str(r.collider.get_parent().name) + "/" + str(r.collider.name) + " em " + _planta(r.position)) if r else "livre"])


func _planta(v: Vector3) -> String:
	return "(%.1f, %.1f)" % [v.x + 30.0, v.z + 22.5]


## Anda até o alvo (confere o caminho e teleporta para perto dele).
func _ir_ate(alvo: Vector3, texto: String) -> bool:
	var ok := _alcanca(alvo, 1.6, true)
	_conferir(ok, "caminho até " + texto)
	var ponto := NavigationServer3D.map_get_closest_point(_mapa, alvo)
	_jogador.global_position = ponto + Vector3(0, 0.05, 0)
	await get_tree().physics_frame
	return ok


## Espera o recálculo AUTOMÁTICO da navegação que o jogo faz quando uma porta termina de girar
## (mundo.pedir_reassar_navegacao). Assim o teste confere o sistema de verdade.
func _recalcular_navegacao() -> void:
	var nav: NavigationRegion3D = _mundo.get_node("Navegacao")
	var antes := nav.navigation_mesh.get_polygon_count()
	var limite := Time.get_ticks_msec() + 8000
	var terminou := [false]
	var ao_terminar := func() -> void: terminou[0] = true
	nav.bake_finished.connect(ao_terminar)
	while not terminou[0] and Time.get_ticks_msec() < limite:
		await get_tree().process_frame
	nav.bake_finished.disconnect(ao_terminar)
	for i in 4:
		await get_tree().physics_frame
	_conferir(terminou[0], "navegação recalculada sozinha (%d -> %d polígonos)" % [antes, nav.navigation_mesh.get_polygon_count()])


func _interagir(no: Node, texto: String) -> void:
	if no == null:
		_conferir(false, "objeto para interagir: " + texto)
		return
	var dica: String = no.texto_dica() if no.has_method("texto_dica") else ""
	print("[cadeia]       dica: ", dica)
	no.interagir(_jogador)
	await get_tree().process_frame


func _area(nome_modelo: String) -> Node:
	return _mundo.find_child("Interacao_" + nome_modelo, true, false)


## Vence o minigame aberto. Devolve false se ele não abriu (ex.: a cena ainda não existe).
func _vencer_minigame(nome: String) -> bool:
	await get_tree().process_frame
	if Jogo.minigame_aberto == "" and not ResourceLoader.exists("res://cenas/minigames/%s.tscn" % nome):
		print("[cadeia] AVISO minigame '%s' ainda não existe: resultado simulado" % nome)
		return false
	_conferir(Jogo.minigame_aberto == nome, "minigame aberto: %s (aberto: '%s')" % [nome, Jogo.minigame_aberto])
	for i in 20:
		await get_tree().process_frame
	_prog.vencer_minigame_aberto()
	await get_tree().create_timer(0.2).timeout
	return true


func _disjuntor(area: String) -> Node:
	return _mundo.get_node("Disjuntores/Disjuntor_" + area)


func _rodar() -> void:
	var spawn := _jogador.global_position
	_conferir(PlantaV2.comodo_em(spawn) == "Sala_Seguranca", "começa na sala de segurança")
	_conferir(Jogo.objetivo_atual().contains("Cozinha"), "primeiro objetivo: " + Jogo.objetivo_atual())

	# 1. Disjuntor da cozinha (minigame dos fios).
	var dc := _disjuntor("Cozinha")
	await _ir_ate(dc.global_position, "disjuntor da cozinha")
	await _interagir(dc, "disjuntor da cozinha")
	if not await _vencer_minigame("conserto"):
		dc.consertado = true
		dc.ligar()
	_conferir(dc.ligado, "disjuntor da cozinha ligado")

	# 2. Fichas (todas as que dá para alcançar).
	var pegas := 0
	for f in get_tree().get_nodes_in_group("ficha"):
		var pos: Vector3 = (f as Node3D).global_position
		if _alcanca(pos):
			_jogador.global_position = NavigationServer3D.map_get_closest_point(_mapa, pos)
			await _interagir(f.get_node("Interacao_Ficha"), "ficha")
			pegas += 1
		else:
			print("[cadeia]       ficha fora de alcance agora em ", PlantaV2.comodo_em(pos))
	_conferir(Jogo.fichas >= 2, "fichas pegas: %d (no bolso: %d)" % [pegas, Jogo.fichas])

	# 3. Garra -> chave do gerente.
	var garra := _mundo.find_child("Maquina_Garra", true, false) as Node3D
	await _ir_ate(garra.global_position + garra.global_basis.z * 1.0, "máquina de garra")
	await _interagir(_area("Maquina_Garra"), "garra")
	if not await _vencer_minigame("garra"):
		Jogo.dar_item("chave_gerente")
	_conferir(Jogo.tem_item("chave_gerente"), "ganhou a chave do gerente")

	# 4. TITO KART -> 2 primeiros dígitos.
	var kart := _mundo.find_child("Arcade_Tito_Kart", true, false) as Node3D
	await _ir_ate(kart.global_position + kart.global_basis.z * 1.0, "TITO KART")
	await _interagir(_area("Arcade_Tito_Kart"), "kart")
	if not await _vencer_minigame(Jogo.minigame_aberto if Jogo.minigame_aberto != "" else "kart"):
		Jogo.revelar_digitos(0, 2)
	_conferir(Jogo.digitos_conhecidos[0] and Jogo.digitos_conhecidos[1], "kart revelou os 2 primeiros dígitos")

	# 5. Pôster da festa (V2.2: só ambientação, não dá dígito).
	var poster := _mundo.find_child("Pista__aniversario", true, false) as Node3D
	await _ir_ate(poster.global_position, "pôster da festa")
	await _interagir(poster.get_node("Interacao_Pista_aniversario"), "pôster")
	_prog.ui.fechar()
	_conferir(not Jogo.digitos_conhecidos[2], "pôster é só ambientação (não revela dígito)")

	# 6. Sala do gerente: porta com chave, disjuntor com fusível, recado.
	var porta_gerente: PortaV2 = _prog._portas["gerente"]
	_conferir(not _alcanca(_disjuntor("Gerente").global_position), "sala do gerente fechada antes da chave")
	await _ir_ate(PlantaV2.mundo(57, 18.2), "porta do gerente (lado do corredor)")
	await _interagir(porta_gerente, "porta do gerente")
	_conferir(porta_gerente.aberta, "porta do gerente aberta")
	await _recalcular_navegacao()
	var dg := _disjuntor("Gerente")
	await _ir_ate(dg.global_position, "disjuntor do gerente")
	await _interagir(dg, "disjuntor do gerente")
	if not await _vencer_minigame("conserto"):
		dg.consertado = true
		dg.ligar()
	_conferir(dg.ligado, "disjuntor do gerente ligado")
	var recado := _mundo.find_child("Pista__recado_gerente", true, false)
	await _interagir(recado.get_node("Interacao_Pista_recado_gerente"), "recado")
	_prog.ui.fechar()
	_conferir(Jogo.codigo_conhecido() == Jogo.codigo, "kart + bilhete do gerente = senha completa: " + Jogo.codigo_conhecido())
	_conferir(Jogo.diario.size() >= 3, "diário do vigia com %d anotações" % Jogo.diario.size())

	# 7. Quadro de avisos da copa (só ambientação).
	var quadro := _mundo.find_child("Pista__quadro_avisos", true, false) as Node3D
	await _ir_ate(quadro.global_position, "quadro de avisos")
	await _interagir(quadro.get_node("Interacao_Pista_quadro_avisos"), "quadro")
	_prog.ui.fechar()

	# 8. Duto: da sala dos piratas até a oficina (a porta da oficina é emperrada).
	_conferir(not _alcanca(_mundo.find_child("Item__alicate", true, false).global_position), "oficina fechada antes do duto")
	var piratas := _prog.get_node("Duto_Entrada_Festa_Piratas") as Node3D
	await _ir_ate(piratas.global_position, "duto da sala dos piratas")
	_prog.rastejar("Festa_Piratas", "Oficina")
	await get_tree().create_timer(6.0).timeout
	_conferir(PlantaV2.comodo_em(_jogador.global_position) == "Oficina", "saiu do duto na oficina (" + PlantaV2.comodo_em(_jogador.global_position) + ")")
	var alicate := _mundo.find_child("Item__alicate", true, false) as Node3D
	await _ir_ate(alicate.global_position, "alicate (dentro da oficina)")
	await _interagir(alicate.get_node("Interacao_Alicate"), "alicate")
	_conferir(Jogo.tem_item("alicate"), "pegou o alicate")
	# Sai pela porta de mão única até o palco.
	var unica: PortaV2 = _prog._portas["oficina_1"]
	await _ir_ate(PlantaV2.mundo(13.2, 3), "porta de mão única (lado da oficina)")
	await _interagir(unica, "porta única")
	_conferir(unica.aberta, "atalho da oficina aberto")
	await _recalcular_navegacao()
	await _ir_ate(PlantaV2.mundo(18, 10), "salão, saindo pela oficina")

	# 9. Depósito: cortar a corrente, religar o disjuntor.
	var porta_dep: PortaV2 = _prog._portas["deposito"]
	_conferir(not _alcanca(_disjuntor("Deposito").global_position), "depósito fechado antes da corrente")
	await _ir_ate(PlantaV2.mundo(7, 18.2), "porta do depósito (lado do corredor)")
	await _interagir(porta_dep, "corrente")
	_conferir(not porta_dep.trancada, "corrente cortada")
	await _interagir(porta_dep, "porta do depósito")
	await _recalcular_navegacao()
	var dd := _disjuntor("Deposito")
	await _ir_ate(dd.global_position, "disjuntor do depósito")
	await _interagir(dd, "disjuntor do depósito")
	_conferir(dd.ligado, "disjuntor do depósito ligado")

	# 10. Teclado da sala elétrica.
	var porta_el: PortaV2 = _prog._portas["eletrica"]
	_conferir(not _alcanca(_disjuntor("Eletrica").global_position), "sala elétrica fechada antes da senha")
	var teclado := _mundo.find_child("Teclado_Eletrica", true, false) as Node3D
	await _ir_ate(teclado.global_position, "teclado da sala elétrica")
	await _interagir(_area("Teclado_Eletrica"), "teclado")
	_prog.ui.digitar_senha_teste("0000" if Jogo.codigo != "0000" else "1111")
	await get_tree().create_timer(0.8).timeout
	_conferir(porta_el.trancada, "senha errada não abre")
	_prog.ui.digitar_senha_teste(Jogo.codigo)
	await get_tree().create_timer(1.2).timeout
	_conferir(not porta_el.trancada and porta_el.aberta, "senha certa abre a sala elétrica")
	await _recalcular_navegacao()
	var de := _disjuntor("Eletrica")
	await _ir_ate(de.global_position, "disjuntor da sala elétrica")
	await _interagir(de, "disjuntor elétrica")
	_conferir(Jogo.todos_disjuntores_ligados(), "4 disjuntores ligados (%d)" % Jogo.disjuntores_ligados)

	# Extras: esconderijo e arremesso.
	var armario := get_tree().get_nodes_in_group("esconderijo").filter(func(e: Node) -> bool: return e.get_meta("tipo") == "armario")
	_conferir(armario.size() >= 4, "armários-esconderijo no vestiário: %d" % armario.size())
	# Esconder num armário e sair.
	var volta := _jogador.global_position
	var antes := _jogador.global_position
	await _prog.esconder(armario[0])
	await get_tree().physics_frame
	_conferir(_jogador.escondido and _jogador.is_in_group("escondido") and _jogador.collision_layer == 0, "escondido no armário")
	_prog.sair_do_esconderijo()
	await get_tree().physics_frame
	_conferir(not _jogador.escondido and _prog._livre(_jogador.global_position - Vector3(0, 0.05, 0))
		and _jogador.global_position.distance_to(armario[0].global_position) < 3.0, "saiu do armário para um ponto livre na frente")
	# Barulhos: lata arremessada, cacos de vidro e o fio desencapado.
	var ruidos: Array = []
	var ouvir := func(pos: Vector3, raio: float, intensidade: float) -> void: ruidos.append([pos, raio, intensidade])
	Jogo.ruido_emitido.connect(ouvir)
	var lata := _prog.find_child("Lata*", false, false)
	await _interagir(lata.get_node("Interacao_Lata"), "lata")
	_conferir(_prog.latas() == 1, "pegou uma lata")
	_jogador.global_position = PlantaV2.mundo(30, 10, 0.05)
	_prog.arremessar_lata()
	await get_tree().create_timer(3.0).timeout
	_conferir(ruidos.any(func(r: Array) -> bool: return is_equal_approx(r[2], 0.75)), "lata arremessada fez barulho ao bater")
	ruidos.clear()
	_jogador.agachado = false
	_jogador.global_position = PlantaV2.mundo(30, 17.2, 0.05)
	for i in 6:
		await get_tree().physics_frame
	_conferir(ruidos.any(func(r: Array) -> bool: return is_equal_approx(r[2], 0.7)), "pisar nos cacos de vidro faz barulho")
	Jogo.ruido_emitido.disconnect(ouvir)
	_jogador.travado = false
	_jogador.global_position = volta
	await get_tree().create_timer(1.5).timeout

	# 11. Gerador e fuga para a sala de segurança.
	var gerador := _mundo.find_child("Gerador_Principal", true, false) as Node3D
	await _ir_ate(gerador.global_position + gerador.global_basis.z * 1.2, "gerador")
	await _interagir(_area("Gerador_Principal"), "gerador")
	_conferir(Jogo.gerador_esta_ligado, "gerador ligado")
	await _ir_ate(spawn, "volta para a sala de segurança")
	_conferir(not _venceu, "ainda não venceu com a porta de aço aberta")
	await _interagir(_area("Botao_Porta_Seguranca"), "botão da porta de aço")
	await get_tree().create_timer(0.3).timeout
	_conferir(Jogo.porta_seguranca_fechada, "porta de aço fechada")
	for i in 10:
		await get_tree().physics_frame
	_conferir(_venceu, "VITÓRIA (06:00)")

	print("[cadeia] esconderijos: %d · dutos: %d · portas: %d" % [get_tree().get_nodes_in_group("esconderijo").size(),
		get_tree().get_nodes_in_group("duto_grade").size(), get_tree().get_nodes_in_group("porta").size()])
