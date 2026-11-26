extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Teste do fluxo do jogo (sem inimigos agirem): religa os 4 disjuntores pela
## interação de verdade (raio da câmera + tecla E simulada), pega uma pilha,
## volta para a sala de segurança e espera a vitória. Depois testa a derrota por tempo.
## Uso: godot --headless --path . res://dev/teste_fluxo.tscn

var _mundo: Node3D
var _jogador: CharacterBody3D
var _venceu := false
var _motivo_derrota := ""
var _falhas := 0


func _ready() -> void:
	Jogo.modo_captura = false
	Jogo.ia_ativa = false  # este teste é só dos sistemas; os inimigos ficam parados
	Jogo.vitoria.connect(func(): _venceu = true)
	Jogo.derrota.connect(func(m): _motivo_derrota = m)
	_mundo = load("res://cenas/mundo.tscn").instantiate()
	add_child(_mundo)
	await _quadros(10)
	_jogador = get_tree().get_first_node_in_group("jogador")
	_conferir("partida começou", Jogo.em_partida)
	_conferir("relógio em 00:00", Jogo.texto_relogio() == "00:00")

	# --- Disjuntores ---
	var disjuntores := get_tree().get_nodes_in_group("disjuntor")
	_conferir("4 disjuntores na cena", disjuntores.size() == 4)
	for d in disjuntores:
		await _olhar_para(d.global_position + Vector3(0, 0, 0) + d.global_transform.basis.z * 0.1, d.global_transform.basis.z, 1.3)
		var dica: String = _jogador.dica_atual
		_conferir("dica aparece no %s ('%s')" % [d.name, dica], dica.contains("religar"))
		var antes: int = Jogo.disjuntores_ligados
		await _apertar("interagir")
		await _quadros(30)
		_conferir("%s ligou (total %d)" % [d.name, Jogo.disjuntores_ligados], d.ligado and Jogo.disjuntores_ligados == antes + 1)
		if d._alavanca:
			_conferir("alavanca do %s girou (x=%.0f°)" % [d.name, rad_to_deg(d._alavanca.rotation.x)], d._alavanca.rotation.x > 0.5)
	var luzes_acesas := get_tree().get_nodes_in_group("luz_area").filter(func(l): return l.visible).size()
	_conferir("4 luzes de área acesas (%d)" % luzes_acesas, luzes_acesas == 4)

	# --- Pilha ---
	_jogador.bateria = 50.0
	_jogador.lanterna_ligada = false
	var pilha: Node3D = get_tree().get_nodes_in_group("pilha")[0]
	var lado := Vector3(1, 0, 0) if pilha.global_position.x < 0 else Vector3(-1, 0, 0)
	await _olhar_para(pilha.global_position, lado, 0.2)
	await _apertar("interagir")
	await _quadros(5)
	_conferir("pilha recarregou (bateria %.0f)" % _jogador.bateria, _jogador.bateria >= 84.0)

	# --- Vitória ---
	_jogador.global_position = Vector3(5.5, 0.05, 6.5)
	await _quadros(10)
	_conferir("vitória ao voltar para a sala de segurança", _venceu)

	# --- Derrota por tempo ---
	_mundo.segundos_por_hora = 0.05
	Jogo.iniciar_partida(_mundo)
	await _quadros(40)
	_conferir("derrota por tempo às 06:00 (motivo '%s')" % _motivo_derrota, _motivo_derrota == "tempo")

	print("[fluxo] %d falha(s)" % _falhas)
	get_tree().quit(1 if _falhas > 0 else 0)


## Põe o vigia a 1,3 m do ponto, do lado indicado por 'frente', olhando para ele.
func _olhar_para(ponto: Vector3, frente: Vector3, altura_alvo: float) -> void:
	frente.y = 0
	frente = frente.normalized()
	var pos := ponto + frente * 1.3
	pos.y = 0.05
	_jogador.global_position = pos
	_jogador.velocity = Vector3.ZERO
	var olho := pos + Vector3(0, 1.6, 0)
	var alvo := Vector3(ponto.x, altura_alvo, ponto.z)
	var dir := alvo - olho
	_jogador.rotation = Vector3(0, atan2(-dir.x, -dir.z), 0)
	_jogador.get_node("Cabeca").rotation.x = atan2(dir.y, Vector2(dir.x, dir.z).length())
	await _quadros(4)


func _apertar(acao: String) -> void:
	var ev := InputEventAction.new()
	ev.action = acao
	ev.pressed = true
	Input.parse_input_event(ev)
	await _quadros(2)
	ev = InputEventAction.new()
	ev.action = acao
	ev.pressed = false
	Input.parse_input_event(ev)


func _quadros(n: int) -> void:
	for i in n:
		await get_tree().physics_frame


func _conferir(descricao: String, ok: bool) -> void:
	print("[fluxo] ", "ok   " if ok else "FALHA", " ", descricao)
	if not ok:
		_falhas += 1
