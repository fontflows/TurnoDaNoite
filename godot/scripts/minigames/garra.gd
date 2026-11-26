class_name MinigameGarra
extends Minigame
## GARRA — a máquina de pegar pelúcia do fliperama.
##
## O que o vigia vê: a máquina DE FRENTE, através do vidro. Lá dentro há uma pilha de
## pelúcias (Tito e Pipoca) e, no meio delas, uma cápsula com a CHAVE DO GERENTE.
##
## Ideia de Computação Gráfica usada aqui: a cena é pensada em 3D (x, y, z) e desenhada
## em 2D com uma PROJEÇÃO simples:
##   - x vai da esquerda (-1) para a direita (+1);
##   - y é a altura (0 = chão da máquina);
##   - z é a profundidade (0 = junto ao vidro, 1 = fundo).
## Quanto mais fundo (z maior), mais alto na tela e menor o objeto (escala < 1).
## Isso é uma perspectiva "de mentira", mas dá a sensação de profundidade.
## Os objetos são desenhados do fundo para a frente (ALGORITMO DO PINTOR), para que os
## da frente cubram os de trás.
##
## Controles: A/D move para os lados, W/S para o fundo/frente, ESPAÇO desce a garra.
## Uma descida por ficha; quando o tempo acaba, a garra desce sozinha.

# --- Tela virtual ------------------------------------------------------------
## Tudo é desenhado num "papel" de 1280 x 720 e depois escalado para o tamanho real da janela.
const VIRTUAL := Vector2(1280.0, 720.0)

# --- Geometria da máquina (em unidades do "mundo" da máquina) ----------------
const CENTRO_X := 640.0          ## x na tela do centro da máquina
const CHAO_FRENTE_Y := 560.0     ## y na tela do chão, junto ao vidro (z = 0)
const CHAO_FUNDO_Y := 450.0      ## y na tela do chão, no fundo (z = 1)
const ESCALA_FUNDO := 0.72       ## tamanho das coisas no fundo (1 = junto ao vidro)
const MEIA_LARGURA := 270.0      ## pixels de x = 0 até x = 1, junto ao vidro
const PIXELS_POR_ALTURA := 300.0 ## pixels por unidade de altura, junto ao vidro
const ALTURA_TRILHO := 1.22      ## altura do trilho de onde a garra pendura
const ALTURA_TOPO := 1.05        ## altura do "cubo" da garra quando está em cima
const LIMITE_X := 0.9
const LIMITE_Z_MIN := 0.06
const LIMITE_Z_MAX := 0.94

## Saída (o buraco do prêmio), no canto da frente à esquerda.
const SAIDA_X_MAX := -0.62
const SAIDA_Z_MAX := 0.36
const SAIDA_CENTRO := Vector2(-0.81, 0.17)  # (x, z)

# --- Jogo --------------------------------------------------------------------
const VEL_X := 0.7               ## velocidade lateral da garra (unidades/s)
const VEL_Z := 0.5               ## velocidade para o fundo/frente
const VEL_DESCER := 0.9
const VEL_SUBIR := 0.7
const VEL_LEVAR := 0.6
const RAIO_CAPTURA := 0.16       ## distância máxima (no plano x-z) para a garra pegar algo
const TEMPO_FECHAR := 0.5
const TEMPO_SOLTAR := 0.9
const TEMPO_MENSAGEM := 1.5
const GRAVIDADE := 4.0

## Um prêmio dentro da máquina (pelúcia ou cápsula).
class Premio:
	var tipo := "tito"            # "tito", "pipoca" ou "capsula"
	var pos := Vector3.ZERO       # ponto da BASE do objeto (onde ele encosta no chão)
	var inclinacao := 0.0         # rotação em radianos (deixa a pilha bagunçada)
	var tamanho := 1.0            # multiplica a escala do desenho
	var altura := 0.3             # altura do objeto (unidades do mundo)
	var vel_y := 0.0
	var caindo := false
	var na_saida := false         # caiu no buraco do prêmio

## Sorteios da máquina (os testes podem fixar a semente para repetir uma jogada).
var sorteio := RandomNumberGenerator.new()

var premios: Array[Premio] = []
## Estados: "mirando", "descendo", "fechando", "subindo", "levando", "soltando", "resultado".
var estado := "mirando"
var tempo_restante := 20.0
var garra := Vector3(SAIDA_CENTRO.x, ALTURA_TOPO, SAIDA_CENTRO.y)
var abertura := 0.6              ## 0 = garra fechada, 1 = toda aberta
var balanco := 0.0               ## deslocamento em x do balanço da garra
var preso: Premio = null         ## o que a garra está segurando agora
var premio_ganho: Premio = null  ## o que caiu na saída
var escorregou := false

# Sorteios feitos quando a garra fecha (decididos uma vez só, para não depender do FPS).
var _alvo_descida := 0.0
var _vai_segurar := false
var _vai_manter := false
var _altura_escorregar := 0.0
var _fracao_soltar := 0.0
var _desvio_preso := Vector2.ZERO  ## (x, z) do prêmio em relação à garra; vai a zero na subida
var _distancia_levar := 1.0
var _cronometro := 0.0
var _relogio := 0.0              ## tempo total (para piscar as luzes)
var _centralizacao := 0.0        ## 0 a 1, guardado para o HUD e para os testes
var _chance := 0.0
var _mensagem := ""
var _submensagem := ""
var _cor_mensagem := Color.WHITE
var _resultado_final: Array = []  # [venceu, resultado] a entregar depois da mensagem

# Sons
var _som_musica: AudioStreamPlayer
var _som_motor: AudioStreamPlayer
var _som_fechar: AudioStreamPlayer
var _som_premio: AudioStreamPlayer
var _som_errou: AudioStreamPlayer

# Fontes
var _fonte_titulo: Font = preload("res://assets/fontes/Bungee/Bungee-Regular.ttf")
var _fonte_pixel: Font = preload("res://assets/fontes/PressStart2P/PressStart2P-Regular.ttf")
var _fonte_tela: Font = preload("res://assets/fontes/VT323/VT323-Regular.ttf")

## Transformação "vista": leva do papel 1280x720 para a janela real (escala + centralização).
var _vista := Transform2D.IDENTITY


func _init() -> void:
	nome_minigame = "garra"
	intensidade_ruido = 0.8  # música alta da máquina: os animatrônicos ouvem


# =============================================================================
# Início
# =============================================================================

func _ao_iniciar() -> void:
	nome_minigame = "garra"
	intensidade_ruido = 0.8
	sorteio.randomize()
	tempo_restante = dificuldade.tempo_garra_s
	_montar_pilha()
	_som_musica = _criar_som("garra_musica.wav", -6.0)
	_som_motor = _criar_som("garra_motor.wav", -10.0)
	_som_fechar = _criar_som("garra_fechar.wav", -4.0)
	_som_premio = _criar_som("garra_premio.wav", -2.0)
	_som_errou = _criar_som("garra_errou.wav", -3.0)
	_tocar(_som_musica)


## Reconstrói a pilha (os testes chamam de novo depois de fixar a semente).
func _montar_pilha() -> void:
	premios.clear()
	# Fileiras de pelúcias: [profundidade z, posições x]. Deixamos um vão no meio
	# da fileira z = 0.46 para a cápsula, e a frente-esquerda livre para a saída.
	var fileiras := [
		[0.90, [-0.78, -0.48, -0.18, 0.12, 0.42, 0.72]],
		[0.68, [-0.62, -0.33, -0.04, 0.30, 0.60, 0.86]],
		[0.46, [-0.45, -0.16, 0.44, 0.72]],
		[0.24, [-0.30, 0.40, 0.68, 0.90]],
	]
	for fileira: Array in fileiras:
		var z: float = fileira[0]
		for x: float in fileira[1]:
			var p := Premio.new()
			p.tipo = "tito" if sorteio.randf() < 0.55 else "pipoca"
			p.pos = Vector3(x + sorteio.randf_range(-0.025, 0.025), 0.0, z + sorteio.randf_range(-0.02, 0.02))
			p.pos.y = _altura_monte(p.pos.x, p.pos.z)
			p.inclinacao = sorteio.randf_range(-0.28, 0.28)
			p.tamanho = sorteio.randf_range(0.92, 1.05)
			p.altura = 0.32
			premios.append(p)
	var c := Premio.new()
	c.tipo = "capsula"
	c.pos = Vector3(0.14 + sorteio.randf_range(-0.02, 0.02), 0.0, 0.46)
	c.pos.y = _altura_monte(c.pos.x, c.pos.z)
	c.inclinacao = sorteio.randf_range(-0.2, 0.2)
	c.altura = 0.2
	c.tamanho = 1.15  # um pouco maior que o normal, para dar para ver no meio da pilha
	premios.append(c)


## A pilha é um "morrinho": mais alta no fundo e no meio. No buraco da saída, chão = 0.
func _altura_monte(x: float, z: float) -> float:
	if _na_area_saida(x, z):
		return 0.0
	return 0.04 + 0.08 * z * (1.0 - 0.5 * x * x)


func _na_area_saida(x: float, z: float) -> bool:
	return x < SAIDA_X_MAX and z < SAIDA_Z_MAX


## Ao sair da árvore, para todos os sons (o mundo continua rodando sem a máquina).
func _exit_tree() -> void:
	super()
	for filho in get_children():
		if filho is AudioStreamPlayer:
			(filho as AudioStreamPlayer).stop()
			(filho as AudioStreamPlayer).stream = null  # solta o som já (evita aviso de "leak" ao fechar o jogo)


func _criar_som(arquivo: String, volume_db: float) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = &"Efeitos"  # a música também vem da máquina, então é "efeito", não trilha
	p.volume_db = volume_db
	var caminho := "res://assets/sons/minigames/" + arquivo
	if ResourceLoader.exists(caminho):
		p.stream = load(caminho)
	add_child(p)
	return p


## No modo --headless (testes automáticos) não existe saída de som: não tocamos nada,
## para o teste não fechar o jogo com um som ainda "pendurado" no servidor de áudio.
static func _sem_audio() -> bool:
	return DisplayServer.get_name() == "headless"


func _tocar(som: AudioStreamPlayer) -> void:
	if som and som.stream and not _sem_audio():
		som.play()


# =============================================================================
# Regras: chance de segurar o prêmio
# =============================================================================

## Chance de a garra AGARRAR quando fecha (0 a 1).
## forca: força da garra (Dificuldade.forca_garra). centralizacao: 1 = bem no meio, 0 = na borda.
## Garra fraca exige mais centralização (c_min sobe) e tem um "teto" menor.
static func chance_agarrar(forca: float, centralizacao: float) -> float:
	var c_min := 0.6 * (1.0 - forca)
	var c_ok := c_min + 0.45
	var teto := 0.4 + 0.6 * forca
	return teto * smoothstep(c_min, c_ok, centralizacao)


## Chance de a garra DERRUBAR o prêmio no caminho até a saída (balançando).
static func chance_derrubar(forca: float, centralizacao: float) -> float:
	return clampf((1.0 - forca) * (1.2 - centralizacao), 0.0, 1.0)


## Chance total de ganhar (agarrar e não derrubar).
static func chance_total(forca: float, centralizacao: float) -> float:
	return chance_agarrar(forca, centralizacao) * (1.0 - chance_derrubar(forca, centralizacao))


## O prêmio mais perto (no plano x-z) de um ponto; devolve null se a pilha estiver vazia.
func premio_mais_proximo(x: float, z: float) -> Premio:
	var melhor: Premio = null
	var melhor_d := INF
	for p in premios:
		if p.na_saida or p.caindo:
			continue
		var d := Vector2(p.pos.x - x, p.pos.z - z).length()
		if d < melhor_d:
			melhor_d = d
			melhor = p
	return melhor


func capsula() -> Premio:
	for p in premios:
		if p.tipo == "capsula":
			return p
	return null


# =============================================================================
# Laço do jogo
# =============================================================================

func _ao_processar(delta: float) -> void:
	_relogio += delta
	var forca := dificuldade.forca_garra
	var movendo := false
	match estado:
		"mirando":
			var dir := direcao_movimento()
			garra.x = clampf(garra.x + dir.x * VEL_X * delta, -LIMITE_X, LIMITE_X)
			# W (mover_frente) leva a garra para o FUNDO (z maior); S traz para o vidro.
			garra.z = clampf(garra.z - dir.y * VEL_Z * delta, LIMITE_Z_MIN, LIMITE_Z_MAX)
			movendo = dir.length() > 0.1
			tempo_restante -= delta
			if Input.is_action_just_pressed("minigame_acao") or tempo_restante <= 0.0:
				descer()
		"descendo":
			movendo = true
			abertura = move_toward(abertura, 1.0, 3.0 * delta)
			# Garra fraca balança já na descida (e erra um pouco o alvo).
			balanco = (1.0 - forca) * 0.035 * sin(_relogio * 5.0)
			garra.y = move_toward(garra.y, _alvo_descida, VEL_DESCER * delta)
			if is_equal_approx(garra.y, _alvo_descida):
				_fechar()
		"fechando":
			_cronometro += delta
			var alvo := 0.35 if preso else 0.0  # com prêmio, as pontas param em volta dele
			abertura = move_toward(abertura, alvo, 2.5 * delta)
			if _cronometro >= TEMPO_FECHAR:
				estado = "subindo"
		"subindo":
			movendo = true
			garra.y = move_toward(garra.y, ALTURA_TOPO, VEL_SUBIR * delta)
			balanco = (1.0 - forca) * 0.03 * sin(_relogio * 6.0)
			if preso and not _vai_segurar and garra.y >= _altura_escorregar:
				_soltar_preso()  # a garra fraca não firmou: escorrega na subida
			_prender_ao_gancho(delta)
			if is_equal_approx(garra.y, ALTURA_TOPO):
				estado = "levando"
				_distancia_levar = maxf(0.001, Vector2(garra.x, garra.z).distance_to(SAIDA_CENTRO))
		"levando":
			movendo = true
			var atual := Vector2(garra.x, garra.z).move_toward(SAIDA_CENTRO, VEL_LEVAR * delta)
			garra.x = atual.x
			garra.z = atual.y
			var amplitude := (1.0 - forca) * 0.06 + (0.02 if preso else 0.0)
			balanco = amplitude * sin(_relogio * 6.5)
			var fracao := 1.0 - atual.distance_to(SAIDA_CENTRO) / _distancia_levar
			if preso and not _vai_manter and fracao >= _fracao_soltar:
				_soltar_preso()  # balançou demais e o prêmio caiu no caminho
			_prender_ao_gancho(delta)
			if atual.distance_to(SAIDA_CENTRO) < 0.001:
				estado = "soltando"
				_cronometro = 0.0
				balanco = 0.0
				if preso:
					_soltar_preso()
		"soltando":
			_cronometro += delta
			abertura = move_toward(abertura, 1.0, 2.5 * delta)
			balanco = move_toward(balanco, 0.0, delta)
			if _cronometro >= TEMPO_SOLTAR and not _algo_caindo():
				_mostrar_resultado()
		"resultado":
			_cronometro += delta
			if _cronometro >= _tempo_da_mensagem() and _resultado_final.size() == 2:
				var venceu: bool = _resultado_final[0]
				var resultado: Dictionary = _resultado_final[1]
				finalizar(venceu, resultado)
				return
	_atualizar_quedas(delta)
	_atualizar_motor(movendo)
	queue_redraw()


## ESPAÇO (ou o tempo acabou): começa a descida. Só uma vez por ficha.
func descer() -> void:
	if estado != "mirando":
		return
	estado = "descendo"
	tempo_restante = maxf(tempo_restante, 0.0)
	# A garra para em cima do que estiver embaixo dela (ou no chão).
	var alvo := premio_mais_proximo(garra.x, garra.z)
	if alvo and Vector2(alvo.pos.x - garra.x, alvo.pos.z - garra.z).length() <= RAIO_CAPTURA:
		_alvo_descida = alvo.pos.y + alvo.altura * 0.55 + 0.14
	else:
		_alvo_descida = _altura_monte(garra.x, garra.z) + 0.17


## A garra chegou embaixo: decide (uma vez) se pegou algo e se vai segurar.
func _fechar() -> void:
	estado = "fechando"
	_cronometro = 0.0
	_tocar(_som_fechar)
	var x := garra.x + balanco
	var alvo := premio_mais_proximo(x, garra.z)
	if alvo == null:
		return
	var d := Vector2(alvo.pos.x - x, alvo.pos.z - garra.z).length()
	if d > RAIO_CAPTURA:
		return  # fechou no vazio
	var forca := dificuldade.forca_garra
	_centralizacao = 1.0 - d / RAIO_CAPTURA
	_chance = chance_total(forca, _centralizacao)
	_vai_segurar = sorteio.randf() < chance_agarrar(forca, _centralizacao)
	_vai_manter = sorteio.randf() >= chance_derrubar(forca, _centralizacao)
	_altura_escorregar = lerpf(garra.y, ALTURA_TOPO, sorteio.randf_range(0.2, 0.7))
	_fracao_soltar = sorteio.randf_range(0.15, 0.7)
	_desvio_preso = Vector2(alvo.pos.x - x, alvo.pos.z - garra.z)
	preso = alvo


## Faz o prêmio preso acompanhar a garra (pendurado entre as pontas).
## Se a garra pegou "de lado", o prêmio vai escorregando para o meio dela aos poucos.
func _prender_ao_gancho(delta: float) -> void:
	if preso == null:
		return
	_desvio_preso = _desvio_preso.move_toward(Vector2.ZERO, 0.35 * delta)
	preso.pos = Vector3(garra.x + balanco + _desvio_preso.x, garra.y - 0.14 - preso.altura * 0.55, garra.z + _desvio_preso.y)


func _soltar_preso() -> void:
	if preso == null:
		return
	if estado != "soltando":
		escorregou = true
	preso.caindo = true
	preso.vel_y = 0.0
	preso = null


func _algo_caindo() -> bool:
	for p in premios:
		if p.caindo:
			return true
	return false


## Gravidade simples nos prêmios que caíram da garra.
func _atualizar_quedas(delta: float) -> void:
	for p in premios:
		if not p.caindo:
			continue
		p.vel_y -= GRAVIDADE * delta
		p.pos.y += p.vel_y * delta
		var na_saida := _na_area_saida(p.pos.x, p.pos.z)
		var chao := -0.05 if na_saida else _altura_monte(p.pos.x, p.pos.z)
		if p.pos.y <= chao:
			p.pos.y = chao
			p.caindo = false
			if na_saida:
				p.na_saida = true
				premio_ganho = p


func _atualizar_motor(movendo: bool) -> void:
	if _som_motor == null or _som_motor.stream == null or _sem_audio():
		return
	if movendo and not _som_motor.playing:
		_som_motor.play()
	elif not movendo and _som_motor.playing:
		_som_motor.stop()
	_som_motor.pitch_scale = 0.85 if estado in ["descendo", "subindo"] else 1.0


func _resultado_decidido() -> Variant:
	if estado == "resultado" and _resultado_final is Array and not (_resultado_final as Array).is_empty():
		return _resultado_final
	return null


func _mostrar_resultado() -> void:
	estado = "resultado"
	_cronometro = 0.0
	if premio_ganho and premio_ganho.tipo == "capsula":
		_mensagem = "VOCÊ GANHOU: CHAVE DO GERENTE!"
		_submensagem = "Ela estava dentro da cápsula, no meio das pelúcias."
		_cor_mensagem = Color(1.0, 0.86, 0.25)
		_resultado_final = [true, {"premio": "chave_gerente"}]
		_tocar(_som_premio)
	elif premio_ganho:
		if premio_ganho.tipo == "tito":
			_mensagem = "VOCÊ GANHOU: UM TITO DE PELÚCIA!"
			_submensagem = "Ele não pisca. Nunca. Mas não era a chave."
		else:
			_mensagem = "VOCÊ GANHOU: UMA PIPOCA DE PELÚCIA!"
			_submensagem = "Cheira a pipoca velha e óleo de máquina. Não era a chave."
		_cor_mensagem = Color(0.95, 0.6, 0.85)
		_resultado_final = [false, {"premio": "pelucia"}]
		_tocar(_som_errou)
	else:
		_mensagem = "ESCORREGOU!" if escorregou else "NÃO PEGOU NADA..."
		_submensagem = "A garra desta máquina é famosa por ser... econômica."
		_cor_mensagem = Color(1.0, 0.45, 0.35)
		_resultado_final = [false, {}]
		_tocar(_som_errou)


func _tempo_da_mensagem() -> float:
	return TEMPO_MENSAGEM if _resultado_final.size() == 2 and _resultado_final[0] else TEMPO_MENSAGEM + 0.5


func _ao_vencer_agora() -> void:
	finalizar(true, {"premio": "chave_gerente"})


# =============================================================================
# Projeção 3D -> 2D
# =============================================================================

## Escala de um objeto na profundidade z (1 junto ao vidro, ESCALA_FUNDO no fundo).
func escala_profundidade(z: float) -> float:
	return lerpf(1.0, ESCALA_FUNDO, z)


## Converte um ponto do mundo da máquina (x, y, z) para o papel 1280x720.
func projetar(p: Vector3) -> Vector2:
	var e := escala_profundidade(p.z)
	var chao_y := lerpf(CHAO_FRENTE_Y, CHAO_FUNDO_Y, p.z)
	return Vector2(CENTRO_X + p.x * MEIA_LARGURA * e, chao_y - p.y * PIXELS_POR_ALTURA * e)


# =============================================================================
# Desenho
# =============================================================================

func _draw() -> void:
	var tamanho := size if size.x > 1.0 else get_viewport_rect().size
	# Fundo da tela inteira (fora do papel), sem transformação.
	draw_set_transform_matrix(Transform2D.IDENTITY)
	draw_rect(Rect2(Vector2.ZERO, tamanho), Color(0.03, 0.02, 0.04))
	# Matriz de VISTA: escala o papel para caber na janela, centralizado.
	var s := minf(tamanho.x / VIRTUAL.x, tamanho.y / VIRTUAL.y)
	_vista = Transform2D(0.0, Vector2(s, s), 0.0, (tamanho - VIRTUAL * s) * 0.5)
	_usar_vista()
	_desenhar_gabinete()
	_desenhar_interior()
	# Algoritmo do pintor: fundo -> frente. A garra entra na ordem pela profundidade dela.
	var ordenados := premios.duplicate()
	ordenados.sort_custom(func(a: Premio, b: Premio) -> bool: return a.pos.z > b.pos.z)
	var garra_desenhada := false
	for p: Premio in ordenados:
		if not garra_desenhada and p.pos.z < garra.z and p != preso:
			_desenhar_garra()
			garra_desenhada = true
		if p != preso and not p.na_saida:
			_desenhar_premio(p, projetar(p.pos), escala_profundidade(p.pos.z) * p.tamanho)
	if not garra_desenhada:
		_desenhar_garra()
	_usar_vista()
	_desenhar_sombra_garra()
	_desenhar_saida()
	_desenhar_vidro()
	_desenhar_luzes()
	_desenhar_painel()
	_desenhar_hud()
	_desenhar_vista_de_cima()
	if estado == "resultado":
		_desenhar_mensagem()


func _usar_vista() -> void:
	draw_set_transform_matrix(_vista)


## Matriz de MODELO: põe o desenho local (centrado na origem) numa posição, rotação e escala.
## A matriz final é vista * modelo, como numa pipeline gráfica de verdade.
func _usar_modelo(pos: Vector2, rotacao: float, escala: float) -> void:
	draw_set_transform_matrix(_vista * Transform2D(rotacao, Vector2(escala, escala), 0.0, pos))


func _elipse(centro: Vector2, raios: Vector2, cor: Color, rotacao := 0.0, pontos := 28) -> void:
	var poli := PackedVector2Array()
	for i in pontos:
		var a := TAU * i / pontos
		poli.append(centro + Vector2(cos(a) * raios.x, sin(a) * raios.y).rotated(rotacao))
	draw_colored_polygon(poli, cor)


func _texto(fonte: Font, pos: Vector2, texto: String, tam: int, cor: Color, centralizado := false) -> void:
	var x := pos.x
	if centralizado:
		x -= fonte.get_string_size(texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam).x * 0.5
	draw_string(fonte, Vector2(x, pos.y), texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam, cor)


func _texto_sombra(fonte: Font, pos: Vector2, texto: String, tam: int, cor: Color, sombra: Color, centralizado := false) -> void:
	_texto(fonte, pos + Vector2(3, 3), texto, tam, sombra, centralizado)
	_texto(fonte, pos, texto, tam, cor, centralizado)


## Pontos espaçados no contorno de um retângulo (para as lâmpadas).
func _contorno(r: Rect2, passo: float) -> PackedVector2Array:
	var pts := PackedVector2Array()
	var cantos := [r.position, Vector2(r.end.x, r.position.y), r.end, Vector2(r.position.x, r.end.y)]
	for i in 4:
		var a: Vector2 = cantos[i]
		var b: Vector2 = cantos[(i + 1) % 4]
		var n := maxi(1, int(a.distance_to(b) / passo))
		for k in n:
			pts.append(a.lerp(b, float(k) / n))
	return pts


# --- Gabinete (a caixa da máquina) -------------------------------------------

func _desenhar_gabinete() -> void:
	# Corpo da máquina: degradê vertical (cores por vértice são interpoladas pela GPU).
	var corpo := PackedVector2Array([Vector2(320, 20), Vector2(960, 20), Vector2(960, 710), Vector2(320, 710)])
	var cores := PackedColorArray([Color(0.55, 0.06, 0.12), Color(0.55, 0.06, 0.12), Color(0.22, 0.02, 0.06), Color(0.22, 0.02, 0.06)])
	draw_polygon(corpo, cores)
	# Letreiro de cima
	draw_rect(Rect2(340, 32, 600, 104), Color(0.12, 0.03, 0.15))
	draw_rect(Rect2(340, 32, 600, 104), Color(1.0, 0.8, 0.2), false, 3.0)
	var pulso := 0.85 + 0.15 * sin(_relogio * 4.0)
	_texto_sombra(_fonte_titulo, Vector2(640, 96), "GARRA DO TITO", 50, Color(1.0, 0.85, 0.2) * pulso, Color(0.8, 0.1, 0.2), true)
	_texto(_fonte_titulo, Vector2(640, 126), "PEGUE O PRÊMIO!", 16, Color(0.6, 0.95, 1.0), true)
	# Moldura do vidro
	draw_rect(Rect2(352, 148, 576, 430), Color(0.08, 0.06, 0.08))


# --- Interior: paredes, chão, luz ----------------------------------------------

func _desenhar_interior() -> void:
	var h := ALTURA_TRILHO + 0.08
	# Os 8 cantos da "caixa" interna, projetados.
	var f_ie := projetar(Vector3(-1.04, 0, 0)); var f_id := projetar(Vector3(1.04, 0, 0))
	var t_ie := projetar(Vector3(-1.04, 0, 1)); var t_id := projetar(Vector3(1.04, 0, 1))
	var f_se := projetar(Vector3(-1.04, h, 0)); var f_sd := projetar(Vector3(1.04, h, 0))
	var t_se := projetar(Vector3(-1.04, h, 1)); var t_sd := projetar(Vector3(1.04, h, 1))
	var roxo := Color(0.16, 0.05, 0.22)
	var rosa := Color(0.45, 0.12, 0.35)
	# Parede do fundo (degradê)
	draw_polygon(PackedVector2Array([t_se, t_sd, t_id, t_ie]), PackedColorArray([roxo, roxo, rosa, rosa]))
	# Paredes laterais (mais escuras = menos luz)
	draw_polygon(PackedVector2Array([f_se, t_se, t_ie, f_ie]), PackedColorArray([roxo.darkened(0.5), roxo.darkened(0.2), rosa.darkened(0.3), rosa.darkened(0.6)]))
	draw_polygon(PackedVector2Array([t_sd, f_sd, f_id, t_id]), PackedColorArray([roxo.darkened(0.2), roxo.darkened(0.5), rosa.darkened(0.6), rosa.darkened(0.3)]))
	# Teto
	draw_colored_polygon(PackedVector2Array([f_se, f_sd, t_sd, t_se]), Color(0.07, 0.03, 0.09))
	# Estrelinhas e o rosto do Tito estampados no fundo
	for i in 9:
		var p := t_se.lerp(t_sd, (i + 0.5) / 9.0) + Vector2(0, 40 + 30 * (i % 2))
		_estrela(p, 7.0, Color(1.0, 0.8, 0.3, 0.35))
	_texto(_fonte_titulo, (t_se + t_sd) * 0.5 + Vector2(0, 150), "TITO", 46, Color(1, 0.6, 0.8, 0.12), true)
	# Chão (forrado de feltro azul)
	draw_polygon(PackedVector2Array([t_ie, t_id, f_id, f_ie]), PackedColorArray([Color(0.08, 0.12, 0.3), Color(0.08, 0.12, 0.3), Color(0.12, 0.2, 0.45), Color(0.12, 0.2, 0.45)]))
	# Luz de cima: uma faixa de neon e um "cone" bem leve
	var luz := Color(1.0, 0.95, 0.8)
	draw_line(projetar(Vector3(-0.9, h - 0.02, 0.5)), projetar(Vector3(0.9, h - 0.02, 0.5)), luz, 4.0)
	draw_colored_polygon(PackedVector2Array([projetar(Vector3(-0.9, h, 0.5)), projetar(Vector3(0.9, h, 0.5)),
			f_id + Vector2(-40, 0), f_ie + Vector2(40, 0)]), Color(1.0, 0.95, 0.8, 0.05))
	# Trilhos da garra: dois de frente para o fundo e o travessão que acompanha o z da garra.
	var metal := Color(0.62, 0.64, 0.7)
	draw_line(projetar(Vector3(-1.0, ALTURA_TRILHO, 0)), projetar(Vector3(-1.0, ALTURA_TRILHO, 1)), metal, 5.0)
	draw_line(projetar(Vector3(1.0, ALTURA_TRILHO, 0)), projetar(Vector3(1.0, ALTURA_TRILHO, 1)), metal, 5.0)
	var e := escala_profundidade(garra.z)
	draw_line(projetar(Vector3(-1.0, ALTURA_TRILHO, garra.z)), projetar(Vector3(1.0, ALTURA_TRILHO, garra.z)), metal.darkened(0.15), 7.0 * e)
	# Buraco da saída, no chão
	var b1 := projetar(Vector3(-1.04, 0, 0)); var b2 := projetar(Vector3(SAIDA_X_MAX, 0, 0))
	var b3 := projetar(Vector3(SAIDA_X_MAX, 0, SAIDA_Z_MAX)); var b4 := projetar(Vector3(-1.04, 0, SAIDA_Z_MAX))
	draw_colored_polygon(PackedVector2Array([b4, b3, b2, b1]), Color(0.01, 0.0, 0.02))


func _estrela(c: Vector2, r: float, cor: Color) -> void:
	var pts := PackedVector2Array()
	for i in 10:
		var raio := r if i % 2 == 0 else r * 0.45
		var a := -PI / 2.0 + TAU * i / 10.0
		pts.append(c + Vector2(cos(a), sin(a)) * raio)
	draw_colored_polygon(pts, cor)


# --- Prêmios -------------------------------------------------------------------

func _desenhar_premio(p: Premio, pos: Vector2, escala: float) -> void:
	_usar_modelo(pos, p.inclinacao, escala)
	match p.tipo:
		"tito":
			_desenhar_tito()
		"pipoca":
			_desenhar_pipoca()
		"capsula":
			_desenhar_capsula()
	_usar_vista()


## Tito de pelúcia: urso marrom, chapéu de chef branco e gravata-borboleta mostarda.
## Desenho local: (0, 0) é a base; o urso tem ~110 px de altura.
func _desenhar_tito() -> void:
	var marrom := Color(0.52, 0.31, 0.17)
	var claro := Color(0.8, 0.6, 0.4)
	var escuro := Color(0.3, 0.16, 0.08)
	_elipse(Vector2(0, -2), Vector2(30, 6), Color(0, 0, 0, 0.3))          # sombra
	_elipse(Vector2(0, -30), Vector2(31, 29), escuro)                     # contorno do corpo
	_elipse(Vector2(0, -30), Vector2(29, 27), marrom)                     # corpo
	_elipse(Vector2(0, -26), Vector2(17, 16), claro)                      # barriga
	_elipse(Vector2(-17, -6), Vector2(12, 8), marrom.darkened(0.1))       # pés
	_elipse(Vector2(17, -6), Vector2(12, 8), marrom.darkened(0.1))
	_elipse(Vector2(-17, -6), Vector2(6, 4), claro)
	_elipse(Vector2(17, -6), Vector2(6, 4), claro)
	_elipse(Vector2(-29, -36), Vector2(9, 14), marrom.darkened(0.05), 0.4) # braços
	_elipse(Vector2(29, -36), Vector2(9, 14), marrom.darkened(0.05), -0.4)
	draw_circle(Vector2(-19, -84), 9.5, escuro)                            # orelhas
	draw_circle(Vector2(19, -84), 9.5, escuro)
	draw_circle(Vector2(-19, -84), 8.5, marrom)
	draw_circle(Vector2(19, -84), 8.5, marrom)
	draw_circle(Vector2(-19, -84), 4.5, claro)
	draw_circle(Vector2(19, -84), 4.5, claro)
	draw_circle(Vector2(0, -67), 25, escuro)                               # cabeça
	draw_circle(Vector2(0, -67), 23.5, marrom)
	_elipse(Vector2(0, -59), Vector2(12, 9), claro)                        # focinho
	_elipse(Vector2(0, -63), Vector2(5, 3.5), Color(0.12, 0.06, 0.04))     # nariz
	draw_line(Vector2(0, -60), Vector2(0, -55), Color(0.12, 0.06, 0.04), 1.5)
	for lado in [-1.0, 1.0]:                                               # olhos de botão
		draw_circle(Vector2(9 * lado, -72), 4.0, Color(0.03, 0.02, 0.02))
		draw_circle(Vector2(9 * lado - 1.3, -73.5), 1.3, Color(1, 1, 1, 0.9))
	# Chapéu de chef: faixa + três "nuvens" brancas
	var branco := Color(0.96, 0.95, 0.92)
	var cinza := Color(0.75, 0.74, 0.72)
	draw_circle(Vector2(-10, -103), 11, cinza)
	draw_circle(Vector2(10, -103), 11, cinza)
	draw_circle(Vector2(0, -110), 13, cinza)
	draw_circle(Vector2(-10, -103), 10, branco)
	draw_circle(Vector2(10, -103), 10, branco)
	draw_circle(Vector2(0, -110), 12, branco)
	draw_rect(Rect2(-16, -97, 32, 9), branco)
	draw_rect(Rect2(-16, -97, 32, 9), cinza, false, 1.0)
	# Gravata-borboleta mostarda
	var mostarda := Color(0.86, 0.64, 0.12)
	draw_colored_polygon(PackedVector2Array([Vector2(-14, -51), Vector2(0, -46), Vector2(-14, -40)]), mostarda)
	draw_colored_polygon(PackedVector2Array([Vector2(14, -51), Vector2(0, -46), Vector2(14, -40)]), mostarda)
	draw_circle(Vector2(0, -46), 3.5, mostarda.darkened(0.25))


## Pipoca de pelúcia: coelha lilás de orelhas compridas.
func _desenhar_pipoca() -> void:
	var lilas := Color(0.7, 0.58, 0.88)
	var claro := Color(0.9, 0.85, 0.97)
	var escuro := Color(0.42, 0.32, 0.58)
	var rosa := Color(0.96, 0.62, 0.78)
	_elipse(Vector2(0, -2), Vector2(28, 6), Color(0, 0, 0, 0.3))
	_elipse(Vector2(-9, -100), Vector2(8.5, 24), escuro, -0.15)            # orelhas (contorno)
	_elipse(Vector2(11, -98), Vector2(8.5, 24), escuro, 0.35)
	_elipse(Vector2(-9, -100), Vector2(7, 22.5), lilas, -0.15)
	_elipse(Vector2(11, -98), Vector2(7, 22.5), lilas, 0.35)
	_elipse(Vector2(-9, -99), Vector2(3.5, 16), rosa, -0.15)
	_elipse(Vector2(11, -97), Vector2(3.5, 16), rosa, 0.35)
	_elipse(Vector2(0, -28), Vector2(29, 28), escuro)                      # corpo
	_elipse(Vector2(0, -28), Vector2(27, 26), lilas)
	_elipse(Vector2(0, -24), Vector2(16, 15), claro)
	_elipse(Vector2(-16, -5), Vector2(12, 7), lilas.darkened(0.08))        # pés
	_elipse(Vector2(16, -5), Vector2(12, 7), lilas.darkened(0.08))
	_elipse(Vector2(-27, -34), Vector2(8, 13), lilas.darkened(0.05), 0.4)
	_elipse(Vector2(27, -34), Vector2(8, 13), lilas.darkened(0.05), -0.4)
	draw_circle(Vector2(0, -63), 23.5, escuro)                              # cabeça
	draw_circle(Vector2(0, -63), 22, lilas)
	_elipse(Vector2(0, -56), Vector2(11, 8), claro)
	for lado in [-1.0, 1.0]:
		draw_circle(Vector2(9 * lado, -68), 4.0, Color(0.05, 0.02, 0.06))
		draw_circle(Vector2(9 * lado - 1.3, -69.5), 1.3, Color(1, 1, 1, 0.9))
		_elipse(Vector2(15 * lado, -58), Vector2(4.5, 3), Color(1.0, 0.55, 0.7, 0.7))  # bochechas
	draw_colored_polygon(PackedVector2Array([Vector2(-3.5, -60), Vector2(3.5, -60), Vector2(0, -56)]), rosa.darkened(0.15))
	draw_rect(Rect2(-3, -55, 6, 5), Color(1, 1, 1))                         # dentinhos
	draw_line(Vector2(0, -55), Vector2(0, -50), Color(0.8, 0.8, 0.8), 1.0)
	# Laço vermelho e branco (de saquinho de pipoca) na orelha
	var vermelho := Color(0.9, 0.15, 0.2)
	draw_colored_polygon(PackedVector2Array([Vector2(-20, -84), Vector2(-11, -80), Vector2(-20, -75)]), vermelho)
	draw_colored_polygon(PackedVector2Array([Vector2(-2, -84), Vector2(-11, -80), Vector2(-2, -75)]), vermelho)
	draw_circle(Vector2(-11, -80), 3.0, Color(1, 0.95, 0.9))


## Cápsula de plástico (metade de baixo vermelha, de cima transparente) com a chave dentro.
func _desenhar_capsula() -> void:
	var c := Vector2(0, -30)
	var r := 27.0
	# Brilho pulsando em volta, para o jogador achar a cápsula no meio da pilha
	var brilho := 0.18 + 0.1 * sin(_relogio * 5.0)
	draw_circle(c, r + 14, Color(1.0, 0.85, 0.3, brilho * 0.5))
	draw_circle(c, r + 7, Color(1.0, 0.85, 0.3, brilho))
	_elipse(Vector2(0, -2), Vector2(24, 5), Color(0, 0, 0, 0.3))
	# Metade de baixo (vermelha): meio círculo
	var baixo := PackedVector2Array()
	for i in 17:
		var a := PI * i / 16.0
		baixo.append(c + Vector2(cos(a), sin(a)) * r)
	draw_colored_polygon(baixo, Color(0.85, 0.12, 0.18))
	# A chave do gerente (dourada)
	var ouro := Color(1.0, 0.8, 0.22)
	draw_circle(c + Vector2(-9, -2), 8.0, ouro)
	draw_circle(c + Vector2(-9, -2), 3.5, Color(0.4, 0.1, 0.1))
	draw_rect(Rect2(c + Vector2(-2, -4.5), Vector2(19, 5)), ouro)
	draw_rect(Rect2(c + Vector2(10, 0), Vector2(3, 6)), ouro)
	draw_rect(Rect2(c + Vector2(14, 0), Vector2(3, 4)), ouro)
	# Metade de cima: plástico transparente + reflexo
	draw_circle(c, r, Color(0.75, 0.9, 1.0, 0.3))
	draw_line(c + Vector2(-r, 0), c + Vector2(r, 0), Color(0.55, 0.05, 0.1), 3.0)
	draw_arc(c, r, 0, TAU, 32, Color(1, 1, 1, 0.55), 1.5)
	draw_arc(c, r - 6, PI * 1.1, PI * 1.45, 8, Color(1, 1, 1, 0.85), 3.0)


# --- Garra ---------------------------------------------------------------------

func _desenhar_garra() -> void:
	_usar_vista()
	var e := escala_profundidade(garra.z)
	var x := garra.x + balanco
	var carrinho := projetar(Vector3(garra.x, ALTURA_TRILHO, garra.z))
	var cubo := projetar(Vector3(x, garra.y, garra.z))
	# Carrinho no trilho
	draw_rect(Rect2(carrinho + Vector2(-22, -10) * e, Vector2(44, 18) * e), Color(0.35, 0.36, 0.4))
	draw_rect(Rect2(carrinho + Vector2(-22, -10) * e, Vector2(44, 18) * e), Color(0.8, 0.82, 0.86), false, 1.5)
	# Cabo
	draw_line(carrinho, cubo, Color(0.15, 0.15, 0.17), 3.0 * e)
	# O prêmio preso é desenhado "dentro" da garra (entre as pontas de trás e as da frente)
	var metal := Color(0.78, 0.8, 0.85)
	var metal_escuro := Color(0.45, 0.47, 0.52)
	var abre := abertura
	# Pontas de trás (esquerda e direita)
	for lado in [-1.0, 1.0]:
		var joelho := cubo + Vector2(lado * (16.0 + 22.0 * abre), 20.0) * e
		var ponta := cubo + Vector2(lado * (4.0 + 20.0 * abre), 50.0 - 6.0 * abre) * e
		draw_polyline(PackedVector2Array([cubo + Vector2(lado * 8.0, 6.0) * e, joelho, ponta]), metal_escuro, 6.0 * e)
		draw_polyline(PackedVector2Array([cubo + Vector2(lado * 8.0, 6.0) * e, joelho, ponta]), metal, 3.0 * e)
	if preso:
		_desenhar_premio(preso, projetar(preso.pos), e * preso.tamanho)
	# Ponta da frente (no meio, aponta para o jogador: aparece mais curta)
	var ponta_frente := cubo + Vector2(0, 44.0 - 8.0 * abre) * e
	draw_line(cubo + Vector2(0, 6) * e, ponta_frente, metal_escuro, 7.0 * e)
	draw_line(cubo + Vector2(0, 6) * e, ponta_frente, metal, 3.5 * e)
	draw_circle(ponta_frente, 4.0 * e, metal)
	# Cubo (motor da garra)
	draw_rect(Rect2(cubo + Vector2(-17, -14) * e, Vector2(34, 22) * e), Color(0.55, 0.57, 0.62))
	draw_rect(Rect2(cubo + Vector2(-17, -14) * e, Vector2(34, 7) * e), Color(0.85, 0.87, 0.9))
	draw_circle(cubo + Vector2(0, -3) * e, 3.0 * e, Color(1.0, 0.2, 0.2) if estado != "mirando" else Color(0.2, 1.0, 0.4))


## Sombra da garra no topo da pilha: mostra ONDE ela vai cair (pista de profundidade).
func _desenhar_sombra_garra() -> void:
	if estado != "mirando" and estado != "descendo":
		return
	var x := garra.x + balanco
	var embaixo := premio_mais_proximo(x, garra.z)
	var altura := _altura_monte(x, garra.z)
	if embaixo and Vector2(embaixo.pos.x - x, embaixo.pos.z - garra.z).length() <= RAIO_CAPTURA:
		altura = embaixo.pos.y + embaixo.altura
	var e := escala_profundidade(garra.z)
	var c := projetar(Vector3(x, altura, garra.z))
	_elipse(c, Vector2(30, 8) * e, Color(0, 0, 0, 0.35))
	_elipse(c, Vector2(30, 8) * e, Color(0.3, 1.0, 0.5, 0.12))


# --- Saída, vidro, luzes ---------------------------------------------------------

func _desenhar_saida() -> void:
	var h := 0.36
	var a := projetar(Vector3(SAIDA_X_MAX, 0, 0)); var b := projetar(Vector3(SAIDA_X_MAX, 0, SAIDA_Z_MAX))
	var c := projetar(Vector3(SAIDA_X_MAX, h, SAIDA_Z_MAX)); var d := projetar(Vector3(SAIDA_X_MAX, h, 0))
	var f := projetar(Vector3(-1.04, 0, SAIDA_Z_MAX)); var g := projetar(Vector3(-1.04, h, SAIDA_Z_MAX))
	var acrilico := Color(0.7, 0.9, 1.0, 0.16)
	var borda := Color(0.75, 0.95, 1.0, 0.7)
	draw_colored_polygon(PackedVector2Array([f, b, c, g]), acrilico)   # parede de trás
	draw_colored_polygon(PackedVector2Array([a, b, c, d]), acrilico)   # parede da direita
	draw_polyline(PackedVector2Array([g, c, d, a]), borda, 2.0)
	draw_line(b, c, borda, 2.0)
	_texto(_fonte_titulo, (a + d) * 0.5 + Vector2(-102, 10), "SAÍDA", 16, Color(1.0, 0.9, 0.3), false)
	draw_colored_polygon(PackedVector2Array([(a + d) * 0.5 + Vector2(-34, 22), (a + d) * 0.5 + Vector2(-22, 22), (a + d) * 0.5 + Vector2(-28, 32)]), Color(1.0, 0.9, 0.3))


func _desenhar_vidro() -> void:
	var vidro := Rect2(352, 148, 576, 430)
	# Reflexos diagonais (faixas brancas quase transparentes)
	draw_colored_polygon(PackedVector2Array([Vector2(420, 148), Vector2(480, 148), Vector2(380, 578), Vector2(352, 578), Vector2(352, 440)]), Color(1, 1, 1, 0.05))
	draw_colored_polygon(PackedVector2Array([Vector2(820, 148), Vector2(840, 148), Vector2(760, 578), Vector2(740, 578)]), Color(1, 1, 1, 0.04))
	draw_rect(vidro, Color(0.95, 0.75, 0.3), false, 4.0)


func _desenhar_luzes() -> void:
	# Lâmpadas em volta do letreiro e do vidro, acendendo em "perseguição" (como em parque).
	var passo_luz := int(_relogio * 8.0)
	var cores := [Color(1.0, 0.85, 0.2), Color(1.0, 0.25, 0.3), Color(0.3, 0.8, 1.0)]
	var i := 0
	for p in _contorno(Rect2(334, 26, 612, 116), 30.0):
		_lampada(p, (i + passo_luz) % 3 == 0, cores[i % 3])
		i += 1
	i = 0
	for p in _contorno(Rect2(340, 150, 600, 432), 34.0):
		if p.y < 156.0:
			continue  # a borda de cima já tem as lâmpadas do letreiro
		_lampada(p, (i + passo_luz) % 4 < 2, cores[(i + 1) % 3])
		i += 1


func _lampada(p: Vector2, ligada: bool, cor: Color) -> void:
	if ligada:
		draw_circle(p, 10.0, Color(cor, 0.22))
		draw_circle(p, 5.5, cor)
		draw_circle(p + Vector2(-1.5, -1.5), 2.0, Color(1, 1, 1, 0.9))
	else:
		draw_circle(p, 5.0, cor.darkened(0.7))


# --- Painel de controle e porta do prêmio ------------------------------------------

func _desenhar_painel() -> void:
	draw_colored_polygon(PackedVector2Array([Vector2(330, 596), Vector2(950, 596), Vector2(960, 700), Vector2(320, 700)]), Color(0.12, 0.02, 0.05))
	draw_line(Vector2(330, 596), Vector2(950, 596), Color(1.0, 0.8, 0.2), 2.0)
	# Porta do prêmio
	var porta := Rect2(372, 612, 150, 76)
	draw_rect(porta, Color(0.02, 0.01, 0.02))
	draw_rect(porta, Color(0.7, 0.7, 0.75), false, 3.0)
	_texto(_fonte_titulo, Vector2(447, 630), "PRÊMIO", 13, Color(0.8, 0.8, 0.85), true)
	if premio_ganho:
		_desenhar_premio(premio_ganho, Vector2(447, 684), 0.5)
	# Joystick: inclina conforme as teclas
	var dir := direcao_movimento() if estado == "mirando" else Vector2.ZERO
	var base := Vector2(700, 668)
	_elipse(base, Vector2(34, 10), Color(0.05, 0.05, 0.06))
	var topo := base + Vector2(dir.x * 16.0, -40.0 + dir.y * 6.0)
	draw_line(base, topo, Color(0.7, 0.7, 0.75), 6.0)
	draw_circle(topo, 13.0, Color(0.9, 0.15, 0.2))
	draw_circle(topo + Vector2(-4, -4), 4.0, Color(1, 0.6, 0.6))
	# Botão grande: acende enquanto a garra trabalha
	var aceso := estado != "mirando" or fmod(_relogio, 0.8) < 0.4
	var cor_botao := Color(1.0, 0.85, 0.15) if aceso else Color(0.45, 0.35, 0.05)
	_elipse(Vector2(840, 664), Vector2(36, 14), Color(0.05, 0.05, 0.06))
	_elipse(Vector2(840, 656), Vector2(30, 12), cor_botao)
	_texto(_fonte_pixel, Vector2(840, 694), "ESPAÇO", 10, Color(1, 0.9, 0.6), true)


# --- HUD (fora da máquina) -----------------------------------------------------------

func _desenhar_hud() -> void:
	# Painel da esquerda: tempo e controles
	draw_rect(Rect2(30, 150, 270, 400), Color(0.05, 0.03, 0.06, 0.92))
	draw_rect(Rect2(30, 150, 270, 400), Color(0.45, 0.41, 0.35), false, 2.0)
	_texto(_fonte_pixel, Vector2(165, 186), "TEMPO", 14, Color(0.8, 0.8, 0.8), true)
	var segundos := ceili(maxf(tempo_restante, 0.0))
	var cor_tempo := Color(1.0, 0.3, 0.25) if segundos <= 5 and estado == "mirando" else Color(1.0, 0.86, 0.25)
	_texto(_fonte_pixel, Vector2(165, 244), "%02d" % segundos, 44, cor_tempo, true)
	_texto(_fonte_pixel, Vector2(165, 276), "1 FICHA = 1 DESCIDA", 9, Color(0.7, 0.7, 0.7), true)
	var linhas := [["A / D", "esquerda / direita"], ["W / S", "fundo / frente"], ["ESPAÇO", "desce a garra"], ["ESC / E", "sai (perde a ficha)"]]
	var y := 318.0
	for l: Array in linhas:
		_texto(_fonte_pixel, Vector2(48, y), l[0], 12, Color(1.0, 0.86, 0.25))
		_texto(_fonte_tela, Vector2(48, y + 26), l[1], 26, Color(0.9, 0.9, 0.9))
		y += 56.0
	# Status da garra
	var status := {"mirando": "MIRE NA CÁPSULA!", "descendo": "DESCENDO...", "fechando": "FECHANDO...",
		"subindo": "SUBINDO...", "levando": "LEVANDO À SAÍDA...", "soltando": "SOLTANDO...", "resultado": ""}
	var texto_status: String = status.get(estado, "")
	_texto(_fonte_titulo, Vector2(640, 174), texto_status, 16, Color(0.6, 1.0, 0.7), true)
	# Barra de baixo com o resumo dos controles
	_texto(_fonte_tela, Vector2(640, 716), "A/D W/S move · ESPAÇO desce · ESC/E sai", 24, Color(0.85, 0.85, 0.85), true)


## Mini vista de cima (x para os lados, z para cima = fundo), como um mapa.
func _desenhar_vista_de_cima() -> void:
	var r := Rect2(990, 180, 260, 170)
	draw_rect(Rect2(980, 150, 280, 260), Color(0.05, 0.03, 0.06, 0.92))
	draw_rect(Rect2(980, 150, 280, 260), Color(0.45, 0.41, 0.35), false, 2.0)
	_texto(_fonte_pixel, Vector2(1120, 172), "VISTA DE CIMA", 11, Color(0.8, 0.8, 0.8), true)
	draw_rect(r, Color(0.08, 0.12, 0.3))
	var para_mapa := func(x: float, z: float) -> Vector2:
		return Vector2(r.position.x + (x + 1.0) * 0.5 * r.size.x, r.end.y - z * r.size.y)
	var s1: Vector2 = para_mapa.call(-1.0, SAIDA_Z_MAX)
	var s2: Vector2 = para_mapa.call(SAIDA_X_MAX, 0.0)
	draw_rect(Rect2(s1, s2 - s1), Color(0.0, 0.0, 0.0))
	draw_rect(Rect2(s1, s2 - s1), Color(0.75, 0.95, 1.0, 0.7), false, 1.0)
	for p in premios:
		if p.na_saida:
			continue
		var m: Vector2 = para_mapa.call(p.pos.x, p.pos.z)
		match p.tipo:
			"tito":
				draw_circle(m, 8.0, Color(0.52, 0.31, 0.17))
				draw_circle(m + Vector2(0, -3), 3.5, Color(0.96, 0.95, 0.92))
			"pipoca":
				draw_circle(m, 8.0, Color(0.7, 0.58, 0.88))
			"capsula":
				draw_circle(m, 10.0, Color(1.0, 0.85, 0.3, 0.35 + 0.2 * sin(_relogio * 5.0)))
				draw_circle(m, 7.0, Color(0.85, 0.12, 0.18))
				_estrela(m, 5.0, Color(1.0, 0.85, 0.25))
	# Garra: mira com o raio de captura
	var g: Vector2 = para_mapa.call(garra.x + balanco, garra.z)
	var raio := RAIO_CAPTURA * 0.5 * r.size.x
	draw_arc(g, raio, 0, TAU, 24, Color(0.3, 1.0, 0.5), 2.0)
	draw_line(g + Vector2(-raio - 4, 0), g + Vector2(raio + 4, 0), Color(0.3, 1.0, 0.5, 0.8), 1.0)
	draw_line(g + Vector2(0, -raio - 4), g + Vector2(0, raio + 4), Color(0.3, 1.0, 0.5, 0.8), 1.0)
	draw_rect(r, Color(0.45, 0.41, 0.35), false, 1.0)
	_texto(_fonte_tela, Vector2(1000, 374), "fundo ↑   vidro ↓", 22, Color(0.75, 0.75, 0.75))
	_texto(_fonte_tela, Vector2(1000, 398), "círculo verde = garra", 22, Color(0.3, 1.0, 0.5))


func _desenhar_mensagem() -> void:
	var caixa := Rect2(250, 290, 780, 150)
	draw_rect(caixa, Color(0.06, 0.02, 0.08, 0.94))
	draw_rect(caixa, _cor_mensagem, false, 4.0)
	var passo_luz := int(_relogio * 10.0)
	var i := 0
	for p in _contorno(caixa.grow(10.0), 28.0):
		_lampada(p, (i + passo_luz) % 2 == 0, _cor_mensagem)
		i += 1
	var tam := 34 if _mensagem.length() <= 32 else 28
	_texto_sombra(_fonte_titulo, Vector2(640, 360), _mensagem, tam, _cor_mensagem, Color(0, 0, 0), true)
	_texto(_fonte_tela, Vector2(640, 410), _submensagem, 30, Color(0.92, 0.92, 0.92), true)
