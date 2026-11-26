extends Minigame
## SPACE PIZZA — reserva do TITO KART, com a mesma recompensa (2 dígitos da senha).
##
## A nave é uma fatia de pizza no pé da tela. Azeitonas descem do céu; cada uma
## derrubada vale 10 pontos. Azeitona que passa direto tira 5; azeitona que bate na
## nave tira 10. Faça a meta de pontos em 40 segundos para vencer.
##
## Dificuldade (pela mesma variável do kart, velocidade_rivais_kart = v):
##   - as azeitonas caem v vezes mais rápido e nascem v vezes mais seguido;
##   - a meta de pontos também cresce com v (Fácil 180, Normal 220, Pesadelo 280).
##
## A montagem da tela (SubViewport 320×240 + shader de CRT + moldura) é a mesma do kart:
## as funções estáticas de kart.gd são reaproveitadas aqui.

const Kart := preload("res://scripts/minigames/kart.gd")

const LARGURA_TELA := 320
const ALTURA_TELA := 240
const ALTURA_HUD := 16
const TEMPO_TOTAL := 40.0
## Meta de pontos no Normal (multiplicada pela dificuldade e arredondada de 10 em 10).
const META_NORMAL := 220.0
const Y_NAVE := 214.0
const VEL_NAVE := 150.0
## Segundos entre dois tiros (segurando ESPAÇO a nave atira sozinha nesse ritmo).
const CADENCIA := 0.2
const VEL_TIRO := 260.0
const RAIO_AZEITONA := 6.0
## Segundos entre duas azeitonas no Normal.
const INTERVALO_AZEITONA := 0.8
const PASSO := 1.0 / 120.0

# Paleta neon: azul e laranja.
const COR_FUNDO := Color(0.02, 0.03, 0.1)
const COR_LARANJA := Color(1.0, 0.55, 0.1)
const COR_AZUL := Color(0.2, 0.6, 1.0)
const COR_CIANO := Color(0.4, 0.95, 1.0)
const COR_QUEIJO := Color(1.0, 0.82, 0.2)

enum Estado { INTRO, JOGO, FIM }


class Azeitona:
	var pos := Vector2.ZERO
	var vel := 40.0
	## Fase do balanço para os lados (cada uma balança diferente).
	var fase := 0.0
	var verde := false


class Explosao:
	var pos := Vector2.ZERO
	var tempo := 0.0


## Ferramenta de teste: a nave mira e atira sozinha (usado por dev/teste_kart.gd).
var piloto_automatico := false

var estado := Estado.INTRO
var tempo_estado := 0.0
var tempo_restante := TEMPO_TOTAL
var pontos := 0
var meta := 220
var venceu := false
var nave_x := 160.0
var tempo_piscando := 0.0
var azeitonas: Array[Azeitona] = []
var tiros: Array[Vector2] = []
var explosoes: Array[Explosao] = []
## Estrelas do fundo: x, y e velocidade (z).
var estrelas: Array[Vector3] = []
## Textinhos flutuantes (+10, -5): posição, texto e tempo de vida.
var avisos: Array[Dictionary] = []

var _v := 1.0
var _acumulador := 0.0
var _relogio := 0.0
var _tempo_tiro := 0.0
var _tempo_nascer := 0.0
var _espaco_antes := false
var _sorteio := RandomNumberGenerator.new()

var _tela: SubViewport
var _desenho: Node2D
var _tela_crt: TextureRect
var _fonte: FontFile
var _fonte_crt: Font
var _som_tiro: AudioStreamPlayer
var _som_explosao: AudioStreamPlayer
var _som_vitoria: AudioStreamPlayer
var _som_derrota: AudioStreamPlayer
var _som_batida: AudioStreamPlayer


func _ready() -> void:
	_montar_tela()
	_som_tiro = _criar_som("sp_tiro")
	_som_explosao = _criar_som("sp_explosao")
	_som_vitoria = _criar_som("kart_vitoria")
	_som_derrota = _criar_som("kart_derrota")
	_som_batida = _criar_som("kart_batida")
	_som_tiro.volume_db = -8.0
	super()


func _montar_tela() -> void:
	var original: FontFile = load("res://assets/fontes/PressStart2P/PressStart2P-Regular.ttf")
	_fonte = original.duplicate() as FontFile
	_fonte.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	_fonte_crt = load("res://assets/fontes/VT323/VT323-Regular.ttf")

	_tela = SubViewport.new()
	_tela.name = "TelaInterna"
	_tela.size = Vector2i(LARGURA_TELA, ALTURA_TELA)
	_tela.disable_3d = true
	_tela.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_tela.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_tela)

	_desenho = Node2D.new()
	_desenho.name = "Desenho"
	_desenho.draw.connect(_desenhar_quadro)
	_tela.add_child(_desenho)

	_tela_crt = TextureRect.new()
	_tela_crt.name = "TelaCRT"
	_tela_crt.texture = _tela.get_texture()
	_tela_crt.expand_mode = TextureRect.EXPAND_IGNORE_SIZE
	_tela_crt.stretch_mode = TextureRect.STRETCH_SCALE
	_tela_crt.texture_filter = CanvasItem.TEXTURE_FILTER_LINEAR
	_tela_crt.mouse_filter = Control.MOUSE_FILTER_IGNORE
	var material_crt := ShaderMaterial.new()
	material_crt.shader = Kart.criar_shader_crt()
	material_crt.set_shader_parameter("resolucao", Vector2(LARGURA_TELA, ALTURA_TELA))
	_tela_crt.material = material_crt
	add_child(_tela_crt)

	resized.connect(_posicionar_tela)
	_posicionar_tela()

	# Estrelas sempre no mesmo lugar (semente fixa), para o fundo não "pular".
	var r := RandomNumberGenerator.new()
	r.seed = 1984
	for k in 60:
		estrelas.append(Vector3(r.randf_range(0, LARGURA_TELA), r.randf_range(0, ALTURA_TELA), r.randf_range(8, 40)))


func _posicionar_tela() -> void:
	if _tela_crt == null:
		return
	var escala := maxf(minf(size.x * 0.84 / LARGURA_TELA, size.y * 0.74 / ALTURA_TELA), 0.5)
	var tamanho := Vector2(LARGURA_TELA, ALTURA_TELA) * escala
	_tela_crt.size = tamanho
	_tela_crt.position = ((size - tamanho) * 0.5 + Vector2(0, size.y * 0.01)).round()
	queue_redraw()


func _draw() -> void:
	Kart.desenhar_moldura(self, _tela_crt, "SPACE PIZZA", COR_LARANJA, COR_AZUL, _fonte_crt,
		"A/D move · ESPAÇO atira · ESC/E sai")


func _ao_iniciar() -> void:
	_v = dificuldade.velocidade_rivais_kart
	meta = int(round(META_NORMAL * _v / 10.0)) * 10
	_sorteio.randomize()
	estado = Estado.INTRO
	tempo_estado = 0.0
	tempo_restante = TEMPO_TOTAL
	pontos = 0
	_espaco_antes = Input.is_action_pressed("minigame_acao")
	_posicionar_tela()


func _ao_processar(delta: float) -> void:
	_acumulador += minf(delta, 0.1)
	while _acumulador >= PASSO and not _acabou:
		_acumulador -= PASSO
		_passo(PASSO)
	_desenho.queue_redraw()


func _passo(dt: float) -> void:
	tempo_estado += dt
	_relogio += dt
	var espaco := Input.is_action_pressed("minigame_acao")
	var espaco_apertou := espaco and not _espaco_antes
	_espaco_antes = espaco
	_mover_estrelas(dt)

	match estado:
		Estado.INTRO:
			if tempo_estado > 4.0 or espaco_apertou or piloto_automatico:
				estado = Estado.JOGO
				tempo_estado = 0.0
				_tempo_tiro = CADENCIA  # o ESPAÇO que começou o jogo não conta como tiro
		Estado.JOGO:
			tempo_restante -= dt
			_jogar(dt, espaco)
			if pontos >= meta:
				_terminar(true)
			elif tempo_restante <= 0.0:
				tempo_restante = 0.0
				_terminar(false)
		Estado.FIM:
			_atualizar_efeitos(dt)
			if tempo_estado > (2.4 if venceu else 2.0):
				if venceu:
					finalizar(true, {"digitos": _digitos()})
				else:
					finalizar(false, {})


func _jogar(dt: float, atirando: bool) -> void:
	# --- Nave ---
	var direcao := Input.get_axis("mover_esquerda", "mover_direita")
	if piloto_automatico:
		var alvo := _alvo_automatico()
		direcao = clampf((alvo - nave_x) / 6.0, -1.0, 1.0)
		atirando = true
	nave_x = clampf(nave_x + direcao * VEL_NAVE * dt, 12.0, LARGURA_TELA - 12.0)
	_tempo_tiro += dt
	if atirando and _tempo_tiro >= CADENCIA:
		_tempo_tiro = 0.0
		tiros.append(Vector2(nave_x, Y_NAVE - 10.0))
		_tocar(_som_tiro)
	tempo_piscando = maxf(0.0, tempo_piscando - dt)

	# --- Azeitonas nascendo no alto ---
	_tempo_nascer -= dt
	if _tempo_nascer <= 0.0:
		_tempo_nascer = INTERVALO_AZEITONA / _v * _sorteio.randf_range(0.7, 1.3)
		var a := Azeitona.new()
		a.pos = Vector2(_sorteio.randf_range(16, LARGURA_TELA - 16), ALTURA_HUD - 6.0)
		a.vel = _sorteio.randf_range(34.0, 52.0) * _v
		a.fase = _sorteio.randf() * TAU
		a.verde = _sorteio.randf() < 0.35
		azeitonas.append(a)

	# --- Movimento dos tiros ---
	for i in range(tiros.size() - 1, -1, -1):
		var tiro := tiros[i]
		tiro.y -= VEL_TIRO * dt
		tiros[i] = tiro
		if tiro.y < ALTURA_HUD:
			tiros.remove_at(i)

	# --- Azeitonas: caem balançando; testa tiro, nave e chão ---
	for i in range(azeitonas.size() - 1, -1, -1):
		var a := azeitonas[i]
		a.pos.y += a.vel * dt
		a.pos.x += sin(_relogio * 2.0 + a.fase) * 18.0 * dt
		var acertou := false
		for j in range(tiros.size() - 1, -1, -1):
			if tiros[j].distance_to(a.pos) < RAIO_AZEITONA + 2.0:
				tiros.remove_at(j)
				acertou = true
				break
		if acertou:
			pontos += 10
			_explodir(a.pos, "+10")
			azeitonas.remove_at(i)
		elif tempo_piscando <= 0.0 and a.pos.distance_to(Vector2(nave_x, Y_NAVE)) < RAIO_AZEITONA + 7.0:
			pontos = maxi(0, pontos - 10)
			tempo_piscando = 1.0
			_explodir(a.pos, "-10")
			_tocar(_som_batida)
			azeitonas.remove_at(i)
		elif a.pos.y > ALTURA_TELA + RAIO_AZEITONA:
			pontos = maxi(0, pontos - 5)
			avisos.append({"pos": Vector2(a.pos.x, ALTURA_TELA - 12.0), "texto": "-5", "vida": 0.8})
			azeitonas.remove_at(i)
	_atualizar_efeitos(dt)


## Piloto automático: vai para baixo da azeitona mais perigosa (a mais baixa).
func _alvo_automatico() -> float:
	var alvo := nave_x
	var mais_baixa := -INF
	for a in azeitonas:
		if a.pos.y > mais_baixa and a.pos.y < Y_NAVE - 12.0:
			mais_baixa = a.pos.y
			alvo = a.pos.x
	return alvo


func _explodir(pos: Vector2, texto: String) -> void:
	var e := Explosao.new()
	e.pos = pos
	explosoes.append(e)
	avisos.append({"pos": pos, "texto": texto, "vida": 0.8})
	_tocar(_som_explosao)


func _atualizar_efeitos(dt: float) -> void:
	for i in range(explosoes.size() - 1, -1, -1):
		explosoes[i].tempo += dt
		if explosoes[i].tempo > 0.4:
			explosoes.remove_at(i)
	for i in range(avisos.size() - 1, -1, -1):
		var aviso: Dictionary = avisos[i]
		var vida: float = aviso["vida"]
		var p: Vector2 = aviso["pos"]
		aviso["vida"] = vida - dt
		aviso["pos"] = p + Vector2(0, -14.0 * dt)
		if vida - dt <= 0.0:
			avisos.remove_at(i)


func _mover_estrelas(dt: float) -> void:
	for i in estrelas.size():
		var e := estrelas[i]
		e.y += e.z * dt
		if e.y > ALTURA_TELA:
			e.y -= ALTURA_TELA
		estrelas[i] = e


func _terminar(ganhou: bool) -> void:
	venceu = ganhou
	estado = Estado.FIM
	tempo_estado = 0.0
	_tocar(_som_vitoria if ganhou else _som_derrota)


func _digitos() -> String:
	var codigo := str(dados.get("codigo", "47"))
	if codigo.length() < 2:
		codigo = "47"
	return codigo.substr(0, 2)


func _resultado_decidido() -> Variant:
	return [true, {"digitos": _digitos()}] if estado == Estado.FIM and venceu else null


func _ao_vencer_agora() -> void:
	finalizar(true, {"digitos": _digitos()})


func _criar_som(nome: String) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = &"Efeitos"
	var caminho := "res://assets/sons/minigames/%s.wav" % nome
	if ResourceLoader.exists(caminho):
		p.stream = load(caminho)
	add_child(p)
	return p


func _tocar(p: AudioStreamPlayer) -> void:
	if p and p.stream and p.is_inside_tree():
		p.play()


# ==============================================================================
# Desenho (pixels da tela interna 320×240)
# ==============================================================================

func _desenhar_quadro() -> void:
	var d := _desenho
	d.draw_rect(Rect2(0, 0, LARGURA_TELA, ALTURA_TELA), COR_FUNDO)
	for e in estrelas:
		var brilho := 0.35 + e.z / 60.0
		d.draw_rect(Rect2(Vector2(e.x, e.y).floor(), Vector2.ONE), Color(0.6, 0.8, 1.0, brilho))
	# Chão neon em perspectiva (linhas que fogem para o horizonte).
	for k in range(-6, 7):
		d.draw_line(Vector2(160 + k * 8, 226), Vector2(160 + k * 40, ALTURA_TELA), Color(COR_AZUL, 0.35), 1.0)
	d.draw_line(Vector2(0, 226), Vector2(LARGURA_TELA, 226), Color(COR_AZUL, 0.6), 1.0)

	for a in azeitonas:
		_desenhar_azeitona(d, a)
	for t in tiros:
		d.draw_rect(Rect2(t.x - 1, t.y - 3, 2, 6), COR_CIANO)
	for e in explosoes:
		var raio := 3.0 + e.tempo * 30.0
		var alfa := 1.0 - e.tempo / 0.4
		d.draw_arc(e.pos, raio, 0.0, TAU, 16, Color(COR_LARANJA, alfa), 1.0)
		for k in 6:
			var dir := Vector2.from_angle(k * TAU / 6.0 + e.tempo * 3.0)
			d.draw_rect(Rect2((e.pos + dir * raio * 0.7).floor(), Vector2(2, 2)), Color(COR_QUEIJO, alfa))
	if estado != Estado.INTRO and (tempo_piscando <= 0.0 or fmod(_relogio, 0.15) < 0.08):
		_desenhar_nave(d, Vector2(nave_x, Y_NAVE))
	for aviso in avisos:
		var p: Vector2 = aviso["pos"]
		var texto: String = aviso["texto"]
		var cor := Color(0.4, 1.0, 0.5) if texto.begins_with("+") else Color(1.0, 0.35, 0.3)
		d.draw_string(_fonte, (p + Vector2(-8, 0)).round(), texto, HORIZONTAL_ALIGNMENT_LEFT, -1, 8, cor)
	_desenhar_hud(d)
	match estado:
		Estado.INTRO:
			_desenhar_intro(d)
		Estado.FIM:
			_desenhar_fim(d)


## A nave: fatia de pizza apontando para cima, com borda de massa e pepperonis.
func _desenhar_nave(d: Node2D, c: Vector2) -> void:
	var p := c.round()
	# Fogo do motor.
	var chama := 3.0 + 2.0 * absf(sin(_relogio * 35.0))
	d.draw_colored_polygon(PackedVector2Array([p + Vector2(-4, 8), p + Vector2(4, 8), p + Vector2(0, 8 + chama)]),
		COR_CIANO)
	d.draw_colored_polygon(PackedVector2Array([p + Vector2(-9, 6), p + Vector2(9, 6), p + Vector2(0, -10)]), COR_QUEIJO)
	d.draw_rect(Rect2(p + Vector2(-10, 5), Vector2(20, 3)), Color(0.78, 0.45, 0.15))
	for o: Vector2 in [Vector2(-3, 1), Vector2(3, 2), Vector2(0, -4)]:
		d.draw_circle(p + o, 1.6, Color(0.85, 0.12, 0.1))


func _desenhar_azeitona(d: Node2D, a: Azeitona) -> void:
	var p := a.pos.round()
	if a.verde:
		d.draw_circle(p, RAIO_AZEITONA, Color(0.45, 0.62, 0.15))
		d.draw_circle(p, 2.2, Color(0.9, 0.2, 0.1))  # recheio de pimentão
	else:
		d.draw_circle(p, RAIO_AZEITONA, Color(0.16, 0.12, 0.2))
		d.draw_arc(p, RAIO_AZEITONA, 0.0, TAU, 16, Color(0.55, 0.35, 0.9), 1.0)  # contorno neon
		d.draw_circle(p, 2.0, COR_FUNDO)  # o furo do caroço
	d.draw_rect(Rect2(p + Vector2(-3, -4), Vector2(2, 1)), Color(1, 1, 1, 0.6))  # brilho


func _desenhar_hud(d: Node2D) -> void:
	d.draw_rect(Rect2(0, 0, LARGURA_TELA, ALTURA_HUD), Color(0.0, 0.0, 0.03))
	d.draw_rect(Rect2(0, ALTURA_HUD - 1, LARGURA_TELA, 1), COR_LARANJA)
	d.draw_string(_fonte, Vector2(4, 12), "PONTOS %d/%d" % [pontos, meta], HORIZONTAL_ALIGNMENT_LEFT, -1, 8,
		COR_QUEIJO)
	var cor_tempo := Color(1.0, 0.3, 0.3) if tempo_restante < 10.0 else COR_CIANO
	d.draw_string(_fonte, Vector2(0, 12), "TEMPO %02d" % ceili(tempo_restante), HORIZONTAL_ALIGNMENT_RIGHT,
		LARGURA_TELA - 4, 8, cor_tempo)
	# Barrinha de progresso até a meta.
	var fracao := clampf(float(pontos) / meta, 0.0, 1.0)
	d.draw_rect(Rect2(140, 5, 60, 6), Color(COR_AZUL, 0.4), false, 1.0)
	d.draw_rect(Rect2(141, 6, 58 * fracao, 4), COR_LARANJA)


func _desenhar_intro(d: Node2D) -> void:
	var painel := Rect2(30, 36, 260, 180)
	d.draw_rect(painel, Color(0.01, 0.02, 0.08, 0.92))
	d.draw_rect(painel, COR_AZUL, false, 2.0)
	_texto_centro(d, 66, "SPACE PIZZA", 16, COR_LARANJA, COR_AZUL)
	_desenhar_nave(d, Vector2(160, 94))
	_texto_centro(d, 126, "DERRUBE AS AZEITONAS!", 8, COR_CIANO)
	_texto_centro(d, 146, "FAÇA %d PONTOS" % meta, 8, Color.WHITE)
	_texto_centro(d, 160, "EM %d SEGUNDOS" % int(TEMPO_TOTAL), 8, Color.WHITE)
	if fmod(_relogio, 0.8) < 0.55:
		_texto_centro(d, 194, "ESPAÇO: COMEÇAR", 8, Color(0.3, 1.0, 0.4))


func _desenhar_fim(d: Node2D) -> void:
	var painel := Rect2(20, 64, 280, 112)
	d.draw_rect(painel, Color(0.01, 0.02, 0.08, 0.94))
	d.draw_rect(painel, COR_LARANJA if venceu else Color(1.0, 0.3, 0.3), false, 2.0)
	if venceu:
		_texto_centro(d, 96, "NOVO RECORDE!", 16, Color.from_hsv(fmod(_relogio * 0.8, 1.0), 0.8, 1.0), Color.BLACK)
		_texto_centro(d, 128, "A SENHA COMEÇA COM", 8, COR_CIANO)
		_texto_centro(d, 158, _digitos() + "..", 16, COR_QUEIJO, COR_AZUL)
	else:
		_texto_centro(d, 108, "FALTARAM %d PONTOS" % (meta - pontos), 8, Color(1.0, 0.4, 0.35))
		_texto_centro(d, 136, "TENTE DE NOVO", 8, Color.WHITE)


func _texto_centro(d: Node2D, y: float, texto: String, tamanho: int, cor: Color,
		cor_sombra := Color(0, 0, 0, 0)) -> void:
	if cor_sombra.a > 0.0:
		var o := float(maxi(1, floori(tamanho / 8.0)))
		d.draw_string(_fonte, Vector2(o, y + o), texto, HORIZONTAL_ALIGNMENT_CENTER, LARGURA_TELA, tamanho, cor_sombra)
	d.draw_string(_fonte, Vector2(0, y), texto, HORIZONTAL_ALIGNMENT_CENTER, LARGURA_TELA, tamanho, cor)
