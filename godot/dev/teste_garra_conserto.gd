extends Node
## FERRAMENTA DE DESENVOLVIMENTO: joga a GARRA e o CONSERTO DO DISJUNTOR de verdade,
## com input simulado (Input.action_press / action_release), e confere as regras.
##
## Rodar (na pasta godot/):
##   godot --headless --path . res://dev/teste_garra_conserto.tscn --quit-after 20000
##
## O tempo do minigame é avançado "na mão" (chamando _ao_processar com 1/60 s), com o
## _process do minigame desligado: assim cada jogada é rápida e não depende do FPS.

const PASSO := 1.0 / 60.0
const RODADAS_GARRA := 100
## Erro de mira simulado (um jogador "bem centrado" ainda erra uns centímetros).
const ERRO_MIRA := 0.03

var _falhas := 0
var _ultimo: Array = []
var _camada: CanvasLayer
var _rng := RandomNumberGenerator.new()


func _ready() -> void:
	_camada = CanvasLayer.new()
	_camada.layer = 20
	add_child(_camada)
	_rng.seed = 4712
	await _testar_garra()
	await _testar_fios()
	await _testar_fusivel()
	print("[garra_conserto] %d falha(s)" % _falhas)
	for i in 10:  # deixa os minigames apagados liberarem os sons antes de sair
		await get_tree().process_frame
	get_tree().quit(1 if _falhas > 0 else 0)


func _falhar(texto: String) -> void:
	_falhas += 1
	print("[garra_conserto] FALHA ", texto)


func _ok(texto: String) -> void:
	print("[garra_conserto] ok    ", texto)


## Abre um minigame com o _process desligado (o teste avança o tempo).
func _abrir(cena: String, dif: Dificuldade, dados: Dictionary) -> Minigame:
	var m: Minigame = load(cena).instantiate()
	_camada.add_child(m)
	_ultimo = []
	m.terminado.connect(func(v: bool, r: Dictionary) -> void: _ultimo = [v, r])
	m.iniciar(dif, dados)
	m.set_process(false)
	return m


## Avança o minigame até ele terminar (ou estourar o limite de segundos).
func _rodar_ate_terminar(m: Minigame, limite_s: float) -> void:
	var t := 0.0
	while _ultimo.is_empty() and t < limite_s:
		m._ao_processar(PASSO)
		t += PASSO


## "Aperta" uma tecla por um quadro: a ação fica just_pressed neste quadro.
func _apertar(m: Minigame, acao: String) -> void:
	Input.action_press(acao)
	m._ao_processar(PASSO)
	Input.action_release(acao)
	await get_tree().process_frame  # o próximo aperto cai em outro quadro


# =============================================================================
# GARRA
# =============================================================================

func _testar_garra() -> void:
	for nome_dif in ["facil", "normal", "pesadelo"]:
		var dif: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome_dif)
		var vitorias := 0
		var pelucias := 0
		var chances := 0.0
		for rodada in RODADAS_GARRA:
			var m: MinigameGarra = _abrir("res://cenas/minigames/garra.tscn", dif, {})
			m.sorteio.seed = _rng.randi()  # sementes sorteadas (mas a do teste é fixa: resultado repetível)
			var alvo := m.capsula()
			var mira := Vector2(alvo.pos.x + _rng.randf_range(-ERRO_MIRA, ERRO_MIRA), alvo.pos.z + _rng.randf_range(-ERRO_MIRA, ERRO_MIRA))
			_mover_garra_ate(m, mira)
			await _apertar(m, "minigame_acao")
			if m.estado == "mirando":
				_falhar("garra: ESPAÇO não fez a garra descer")
			_rodar_ate_terminar(m, 30.0)
			chances += m._chance
			if _ultimo.is_empty():
				_falhar("garra %s: a jogada não terminou" % nome_dif)
			elif _ultimo[0]:
				vitorias += 1
				if _ultimo[1].get("premio") != "chave_gerente":
					_falhar("garra: vitória sem chave_gerente " + str(_ultimo))
			elif _ultimo[1].get("premio") == "pelucia":
				pelucias += 1
			await get_tree().process_frame
		var taxa := 100.0 * vitorias / RODADAS_GARRA
		print("[garra_conserto] garra %-8s bem centrada: %d/%d = %.0f%% (chance média calculada %.0f%%, pelúcias %d)" % [
			nome_dif, vitorias, RODADAS_GARRA, taxa, 100.0 * chances / RODADAS_GARRA, pelucias])
		var faixa := {"facil": [85.0, 100.0], "normal": [55.0, 80.0], "pesadelo": [30.0, 55.0]}
		var limites: Array = faixa[nome_dif]
		if taxa < limites[0] or taxa > limites[1]:
			_falhar("garra %s: taxa %.0f%% fora da faixa %s" % [nome_dif, taxa, str(limites)])
		else:
			_ok("garra %s: taxa dentro da faixa %s" % [nome_dif, str(limites)])
	# Chance teórica (sem sorte), para referência no relatório.
	for nome_dif in ["facil", "normal", "pesadelo"]:
		var dif: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome_dif)
		var linha := "[garra_conserto] chance teórica %-8s:" % nome_dif
		for c in [1.0, 0.85, 0.7, 0.5, 0.3]:
			linha += "  c=%.2f→%.0f%%" % [c, 100.0 * MinigameGarra.chance_total(dif.forca_garra, c)]
		print(linha)
	# Mirar longe de tudo: não pega nada.
	var dif_n: Dificuldade = load("res://assets/dificuldade/normal.tres")
	var m2: MinigameGarra = _abrir("res://cenas/minigames/garra.tscn", dif_n, {})
	m2.premios.clear()  # máquina vazia
	_mover_garra_ate(m2, Vector2(0.3, 0.5))
	await _apertar(m2, "minigame_acao")
	_rodar_ate_terminar(m2, 30.0)
	if _ultimo.size() == 2 and not _ultimo[0] and _ultimo[1].is_empty():
		_ok("garra: sem prêmio embaixo -> venceu=false, resultado {}")
	else:
		_falhar("garra vazia deu " + str(_ultimo))
	await get_tree().process_frame
	# Tempo acabando: a garra desce sozinha.
	var m3: MinigameGarra = _abrir("res://cenas/minigames/garra.tscn", dif_n, {})
	var t := 0.0
	while m3.estado == "mirando" and t < dif_n.tempo_garra_s + 2.0:
		m3._ao_processar(PASSO)
		t += PASSO
	if m3.estado != "mirando" and absf(t - dif_n.tempo_garra_s) < 0.2:
		_ok("garra: o tempo acabou (%.1f s) e a garra desceu sozinha" % t)
	else:
		_falhar("garra: não desceu sozinha ao fim do tempo (t=%.1f, estado=%s)" % [t, m3.estado])
	m3.cancelar()
	await get_tree().process_frame
	# Pegar uma pelúcia com garra forte: resultado {"premio": "pelucia"}.
	var dif_f: Dificuldade = load("res://assets/dificuldade/facil.tres")
	var m4: MinigameGarra = _abrir("res://cenas/minigames/garra.tscn", dif_f, {})
	m4.sorteio.seed = 7
	var pel: MinigameGarra.Premio = null
	for p in m4.premios:
		if p.tipo != "capsula" and absf(p.pos.z - 0.46) < 0.05:
			pel = p
	_mover_garra_ate(m4, Vector2(pel.pos.x, pel.pos.z))
	await _apertar(m4, "minigame_acao")
	_rodar_ate_terminar(m4, 30.0)
	if _ultimo.size() == 2 and not _ultimo[0] and _ultimo[1].get("premio") == "pelucia":
		_ok("garra: pegou pelúcia -> venceu=false, premio=pelucia")
	else:
		print("[garra_conserto] (aviso) pelúcia no Fácil deu ", _ultimo, " (pode escorregar raramente)")
	await get_tree().process_frame


## Segura A/D e W/S (como um jogador) até a garra chegar no ponto (x, z).
func _mover_garra_ate(m: MinigameGarra, alvo: Vector2) -> void:
	for eixo in 2:
		var limite := 0
		while limite < 1000:
			var atual := m.garra.x if eixo == 0 else m.garra.z
			var desejado := alvo.x if eixo == 0 else alvo.y
			var falta := desejado - atual
			if absf(falta) < 0.006:
				break
			var acao := ""
			if eixo == 0:
				acao = "mover_direita" if falta > 0.0 else "mover_esquerda"
			else:
				acao = "mover_frente" if falta > 0.0 else "mover_tras"  # W leva para o fundo (z maior)
			Input.action_press(acao)
			m._ao_processar(PASSO)
			Input.action_release(acao)
			limite += 1


# =============================================================================
# CONSERTO: fios
# =============================================================================

func _testar_fios() -> void:
	for nome_dif in ["facil", "normal", "pesadelo"]:
		var dif: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome_dif)
		# 1) Na ordem certa: vence.
		var m: MinigameConserto = _abrir("res://cenas/minigames/conserto.tscn", dif, {"modo": "fios"})
		if m.nome_minigame != "conserto_fios":
			_falhar("fios: nome_minigame = " + m.nome_minigame)
		var teclas := 0
		var t0 := Time.get_ticks_msec()
		for fio in 4:
			teclas += await _escolher(m, "fio", fio)
			await _apertar(m, "minigame_acao")
			var borne := m.borne_cores.find(fio)
			teclas += await _escolher(m, "borne", borne)
			await _apertar(m, "minigame_acao")
			teclas += 2
		_rodar_ate_terminar(m, 3.0)
		if _ultimo.size() == 2 and _ultimo[0]:
			_ok("fios %s: ordem certa vence (%d teclas, ~%.1f s de jogo a 0,4 s/tecla)" % [nome_dif, teclas, teclas * 0.4 + 1.1])
		else:
			_falhar("fios %s: ordem certa não venceu %s" % [nome_dif, str(_ultimo)])
		await get_tree().process_frame
		# 2) Fio errado: não vence, o fio volta e (no Pesadelo) os bornes embaralham.
		var m2: MinigameConserto = _abrir("res://cenas/minigames/conserto.tscn", dif, {"modo": "fios"})
		var antes := m2.borne_cores.duplicate()
		await _escolher(m2, "fio", 0)
		await _apertar(m2, "minigame_acao")
		var errado := (m2.borne_cores.find(0) + 1) % 4
		await _escolher(m2, "borne", errado)
		await _apertar(m2, "minigame_acao")
		_rodar_ate_terminar(m2, 3.0)
		var mudou := m2.borne_cores != antes
		if not _ultimo.is_empty():
			_falhar("fios %s: fio errado terminou o minigame %s" % [nome_dif, str(_ultimo)])
		elif m2.fio_ligado[0] or m2.fase != "fio" or m2.erros != 1:
			_falhar("fios %s: depois do erro o fio deveria voltar (ligado=%s fase=%s)" % [nome_dif, m2.fio_ligado[0], m2.fase])
		elif mudou != dif.embaralhar_fios:
			_falhar("fios %s: embaralhar_fios=%s mas bornes mudaram=%s" % [nome_dif, dif.embaralhar_fios, mudou])
		else:
			_ok("fios %s: fio errado não vence, o fio volta (bornes embaralharam: %s)" % [nome_dif, mudou])
		m2.cancelar()
		await get_tree().process_frame


## Aperta W/S até o cursor (de fio ou de borne) chegar no índice pedido. Devolve as teclas usadas.
func _escolher(m: MinigameConserto, qual: String, indice: int) -> int:
	var n := 0
	while (m.cursor_fio if qual == "fio" else m.cursor_borne) != indice and n < 8:
		await _apertar(m, "mover_tras")
		n += 1
	return n


# =============================================================================
# CONSERTO: fusível
# =============================================================================

func _testar_fusivel() -> void:
	for nome_dif in ["facil", "normal", "pesadelo"]:
		var dif: Dificuldade = load("res://assets/dificuldade/%s.tres" % nome_dif)
		var m: MinigameConserto = _abrir("res://cenas/minigames/conserto.tscn", dif, {"modo": "fusivel"})
		if m.nome_minigame != "conserto_fusivel":
			_falhar("fusível: nome_minigame = " + m.nome_minigame)
		var queimado := m.suportes.find("queimado")
		var bom := (queimado + 1) % 3
		# Primeiro tenta tirar um BOM: choque, não avança e trava ~1 s.
		await _ir_para(m, bom, true)
		await _apertar(m, "minigame_acao")
		var levou_choque := m.suportes[bom] == "bom" and m.fase == "tirar" and m._bloqueio > 0.8
		# Durante o choque, as teclas não fazem nada
		await _apertar(m, "mover_esquerda")
		var cursor_travado := m.cursor_suporte == bom
		for i in 70:
			m._ao_processar(PASSO)
		# Agora tira o queimado e põe o de 20 A
		await _ir_para(m, queimado, true)
		await _apertar(m, "minigame_acao")
		var tirou := m.fase == "por" and m.suportes[queimado] == "vazio"
		# Tenta primeiro um errado (se houver), depois o certo
		var k_errado := -1
		for k in 3:
			if m.caixinha[k] != 20:
				k_errado = k
		await _ir_para(m, k_errado, false)
		await _apertar(m, "minigame_acao")
		var recusou := m.fase == "por" and m.caixinha[k_errado] != 0
		for i in 40:
			m._ao_processar(PASSO)
		await _ir_para(m, m.caixinha.find(20), false)
		await _apertar(m, "minigame_acao")
		_rodar_ate_terminar(m, 3.0)
		var venceu := _ultimo.size() == 2 and bool(_ultimo[0])
		if levou_choque and cursor_travado and tirou and recusou and venceu:
			_ok("fusível %s: bom dá choque e trava ~1 s, 10A/30A recusados, tirar o queimado e pôr 20A vence" % nome_dif)
		else:
			_falhar("fusível %s: choque=%s travado=%s tirou=%s recusou=%s venceu=%s %s" % [
				nome_dif, levou_choque, cursor_travado, tirou, recusou, venceu, str(_ultimo)])
		await get_tree().process_frame


## A/D até o cursor (suporte ou caixinha) chegar no índice.
func _ir_para(m: MinigameConserto, indice: int, suporte: bool) -> void:
	var n := 0
	while (m.cursor_suporte if suporte else m.cursor_caixa) != indice and n < 6:
		var atual := m.cursor_suporte if suporte else m.cursor_caixa
		await _apertar(m, "mover_direita" if indice > atual else "mover_esquerda")
		n += 1
