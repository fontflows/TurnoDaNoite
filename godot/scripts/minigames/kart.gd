extends Minigame
## TITO KART — corrida 2D vista de cima, 3 voltas, contra 2 rivais.
##
## Como a cena é montada (tudo por código, nada de imagens):
##   - Uma SubViewport de 320×240 pixels é a "placa de vídeo" da máquina. Dentro dela,
##     dois Node2D desenham com _draw: "Fundo" (grama e pista, desenhado UMA vez) e
##     "Desenho" (carrinhos, pizzas e HUD, redesenhado a cada quadro).
##   - Um TextureRect mostra a imagem da SubViewport ampliada, com um shader de CRT
##     (curvatura, linhas de varredura, cantos escuros e "sharp bilinear" para os pixels
##     ficarem nítidos mesmo com ampliação quebrada, como 2,4×).
##   - O próprio Control (este script) desenha a moldura escura do gabinete em volta.
##
## Regras:
##   - Tela de recordes no começo: o GER tem o 1º lugar com um tempo a bater.
##   - Contagem 3-2-1 e largada. W acelera, S freia/dá ré, A/D viram.
##   - Fatia de pizza na pista = um turbo guardado; ESPAÇO usa.
##   - Sair do asfalto (grama) deixa o carrinho lento.
##   - Vence quem chegar em 1º E abaixo do tempo do GER. O prêmio são os 2 primeiros
##     dígitos da senha (dados.codigo).
##
## A física é igual para todos os carrinhos: cada um tem "entradas" (acelerar, frear,
## virar, turbo). O jogador preenche as entradas pelo teclado; os rivais, pelo "piloto do computador" que
## segue os pontos da pista (waypoints). O carro não sabe quem está dirigindo.

# --- Tela interna (resolução baixa, esticada depois) ----------------------------
const LARGURA_TELA := 320
const ALTURA_TELA := 240
## Altura da faixa do HUD no topo da tela.
const ALTURA_HUD := 16

# --- Pista ----------------------------------------------------------------------
## Pontos de controle da linha central (no sistema da tela 320×240). Uma curva
## Catmull-Rom passa por todos eles e fecha o circuito. O 1º ponto é a linha de chegada.
const PONTOS_CONTROLE: Array[Vector2] = [
	Vector2(150, 212), Vector2(250, 212), Vector2(290, 178), Vector2(292, 72),
	Vector2(258, 38), Vector2(200, 42), Vector2(178, 78), Vector2(166, 118),
	Vector2(138, 128), Vector2(112, 96), Vector2(98, 50), Vector2(52, 40),
	Vector2(26, 86), Vector2(28, 172), Vector2(68, 212),
]
## Largura do asfalto, em pixels da tela interna.
const LARGURA_PISTA := 26.0
## Distância entre dois pontos seguidos da pista depois de reamostrada.
const ESPACAMENTO := 4.0
const VOLTAS := 3

# --- Carrinho -------------------------------------------------------------------
## Velocidade máxima do jogador no asfalto (pixels por segundo).
const VEL_MAX := 66.0
const ACELERACAO := 70.0
const FREIO := 150.0
## Perda de velocidade sem acelerar nem frear.
const ATRITO := 35.0
const VEL_RE := 22.0
## Quanto o carrinho gira por segundo (radianos) com o volante todo para um lado.
const GIRO := 3.4
## Na grama, a velocidade máxima cai para esta fração.
const FATOR_GRAMA := 0.45
const TURBO_DURACAO := 1.3
const TURBO_FATOR := 1.55
const RAIO_CARRO := 4.5
## Velocidade de cada rival em relação ao jogador (antes da dificuldade).
const PROPORCAO_RIVAIS: Array[float] = [0.80, 0.74]

# --- Tempo do GER ---------------------------------------------------------------
## Tempo de uma corrida muito bem feita (medido com o piloto automático de dev/teste_kart).
const TEMPO_IDEAL := 50.0
## Folga sobre o tempo ideal no Normal. No Fácil a folga cresce e no Pesadelo encolhe
## (folga = FOLGA_NORMAL / velocidade_rivais_kart²: Fácil 7,8 s, Normal 5 s, Pesadelo 3,2 s).
const FOLGA_NORMAL := 5.0
## Quanto o piloto do computador olha à frente (em pontos da pista) para mirar o volante.
const OLHAR_FRENTE := 5

## Passo fixo da simulação: a física fica igual em qualquer taxa de quadros.
const PASSO := 1.0 / 120.0

# --- Cores (paleta de fliperama: primárias fortes) ------------------------------
const COR_GRAMA_1 := Color(0.13, 0.55, 0.18)
const COR_GRAMA_2 := Color(0.10, 0.47, 0.15)
const COR_ASFALTO := Color(0.30, 0.30, 0.34)
const COR_ZEBRA_1 := Color(0.90, 0.12, 0.12)
const COR_ZEBRA_2 := Color(0.96, 0.96, 0.96)
const COR_AMARELO := Color(1.0, 0.85, 0.1)
const COR_CIANO := Color(0.3, 0.85, 1.0)
const COR_JOGADOR := Color(0.55, 0.32, 0.15)

enum Estado { RECORDES, CONTAGEM, CORRIDA, FIM }


## Um carrinho. Os mesmos campos servem para o jogador e para os rivais.
class Carro:
	var nome := ""
	var cor := Color.WHITE
	var eh_jogador := false
	var pos := Vector2.ZERO
	## Direção para onde o nariz aponta (radianos; 0 = direita, cresce no sentido horário).
	var angulo := 0.0
	## Velocidade ao longo do nariz (negativa = ré).
	var velocidade := 0.0
	var vel_max := 0.0
	var aceleracao := 0.0
	## Ponto da pista mais perto do carrinho.
	var indice := 0
	## Quantos pontos da pista o carrinho já andou (volta completa = pista.size()).
	var progresso := 0
	var terminou := false
	var tempo_chegada := 0.0
	## Deslocamento lateral preferido pelo piloto do computador (para os rivais não andarem um em cima do outro).
	var faixa := 0.0
	var tempo_turbo := 0.0
	var tem_turbo := false
	var na_grama := false
	# Entradas (como se fossem as teclas): preenchidas pelo teclado ou pelo piloto do computador.
	var ent_acelerar := 0.0
	var ent_frear := 0.0
	var ent_virar := 0.0
	var ent_turbo := false


## Uma fatia de pizza na pista (vale um turbo).
class Fatia:
	var pos := Vector2.ZERO
	var ativa := true
	var tempo_para_voltar := 0.0


## Ferramenta de teste: quando true, o carrinho do jogador é dirigido pelo mesmo piloto do computador dos
## rivais (com velocidade de jogador e usando turbo). Usado por dev/teste_kart.gd.
var piloto_automatico := false
## Encerra a corrida assim que não dá mais para vencer (um rival chegou ou o tempo do GER
## estourou). O teste desliga para medir o tempo dos rivais até o fim.
var encerrar_quando_impossivel := true
## Preenchido quando a corrida acaba (para os testes e para quem quiser ler).
var resultado_corrida := {}

var estado := Estado.RECORDES
var tempo_estado := 0.0
var tempo_corrida := 0.0
var tempo_ger := 50.0
var venceu := false
var mensagem_fim: Array[String] = []

## Linha central da pista, com pontos a cada ESPACAMENTO pixels.
var pista := PackedVector2Array()
## Direção da pista em cada ponto (ângulo da tangente) e o vetor normal (para o lado).
var angulos := PackedFloat32Array()
var normais := PackedVector2Array()

var carros: Array[Carro] = []
var jogador: Carro
var fatias: Array[Fatia] = []

var _acumulador := 0.0
var _espaco_antes := false
var _ultimo_bip := -1
var _tempo_batida := 0.0
var _relogio := 0.0  # só para piscar textos e animar

# Nós montados por código.
var _tela: SubViewport
var _fundo: Node2D
var _desenho: Node2D
var _tela_crt: TextureRect
var _fonte: FontFile
var _fonte_crt: Font

# Sons.
var _som_motor: AudioStreamPlayer
var _som_bip: AudioStreamPlayer
var _som_largada: AudioStreamPlayer
var _som_turbo: AudioStreamPlayer
var _som_pizza: AudioStreamPlayer
var _som_batida: AudioStreamPlayer
var _som_vitoria: AudioStreamPlayer
var _som_derrota: AudioStreamPlayer


func _ready() -> void:
	_montar_tela()
	_som_motor = _criar_som("kart_motor")
	_som_bip = _criar_som("kart_bip")
	_som_largada = _criar_som("kart_largada")
	_som_turbo = _criar_som("kart_turbo")
	_som_pizza = _criar_som("kart_pizza")
	_som_batida = _criar_som("kart_batida")
	_som_vitoria = _criar_som("kart_vitoria")
	_som_derrota = _criar_som("kart_derrota")
	_som_motor.volume_db = -10.0
	_som_motor.finished.connect(_ao_motor_parar)
	_gerar_pista()
	super()


# ==============================================================================
# Montagem da tela de CRT
# ==============================================================================

func _montar_tela() -> void:
	# Fonte de fliperama sem suavização: os pixels da letra ficam quadradinhos.
	var original: FontFile = load("res://assets/fontes/PressStart2P/PressStart2P-Regular.ttf")
	_fonte = original.duplicate() as FontFile
	_fonte.antialiasing = TextServer.FONT_ANTIALIASING_NONE
	_fonte_crt = load("res://assets/fontes/VT323/VT323-Regular.ttf")

	_tela = SubViewport.new()
	_tela.name = "TelaInterna"
	_tela.size = Vector2i(LARGURA_TELA, ALTURA_TELA)
	_tela.disable_3d = true
	_tela.transparent_bg = false
	_tela.canvas_item_default_texture_filter = Viewport.DEFAULT_CANVAS_ITEM_TEXTURE_FILTER_NEAREST
	_tela.render_target_update_mode = SubViewport.UPDATE_ALWAYS
	add_child(_tela)

	_fundo = Node2D.new()
	_fundo.name = "Fundo"
	_fundo.draw.connect(_desenhar_fundo)
	_tela.add_child(_fundo)

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
	material_crt.shader = criar_shader_crt()
	material_crt.set_shader_parameter("resolucao", Vector2(LARGURA_TELA, ALTURA_TELA))
	_tela_crt.material = material_crt
	add_child(_tela_crt)

	resized.connect(_posicionar_tela)
	_posicionar_tela()


## Shader de CRT (público para o SPACE PIZZA reaproveitar).
static func criar_shader_crt() -> Shader:
	var shader := Shader.new()
	shader.code = """
shader_type canvas_item;
// Tela de tubo (CRT) de fliperama.
uniform vec2 resolucao = vec2(320.0, 240.0);
uniform float curvatura = 0.03;
uniform float forca_linhas = 0.28;

void fragment() {
	// 1) Curvatura: afasta os pontos do centro, como o vidro abaulado do tubo.
	vec2 c = UV * 2.0 - 1.0;
	c *= 1.0 + curvatura * dot(c, c);
	vec2 uv = c * 0.5 + 0.5;
	if (uv.x < 0.0 || uv.x > 1.0 || uv.y < 0.0 || uv.y > 1.0) {
		COLOR = vec4(0.0, 0.0, 0.0, 1.0);
	} else {
		// 2) "Sharp bilinear": dentro de cada texel a cor é constante; só na borda
		//    entre dois texels há uma mistura de 1 pixel. Pixels nítidos e do mesmo tamanho.
		vec2 texel = uv * resolucao;
		vec2 escala = 1.0 / max(fwidth(texel), vec2(1e-4));
		vec2 dist_centro = fract(texel) - 0.5;
		vec2 faixa = 0.5 - 0.5 / escala;
		vec2 f = (dist_centro - clamp(dist_centro, -faixa, faixa)) * escala + 0.5;
		uv = (floor(texel) + f) / resolucao;
		vec3 cor = texture(TEXTURE, uv).rgb;
		// 3) Linhas de varredura: cada linha da imagem fica mais clara no meio.
		float linha = 0.5 - 0.5 * cos(uv.y * resolucao.y * 6.2831853);
		cor *= mix(1.0, linha, forca_linhas) * 1.12;
		// 4) Cantos mais escuros (vinheta).
		cor *= 1.0 - 0.45 * pow(length(c) * 0.72, 3.0);
		COLOR = vec4(cor, 1.0);
	}
}
"""
	return shader


## Centraliza a tela 4:3 e deixa espaço para a moldura, o letreiro e os controles.
func _posicionar_tela() -> void:
	if _tela_crt == null:
		return
	var escala := minf(size.x * 0.84 / LARGURA_TELA, size.y * 0.74 / ALTURA_TELA)
	escala = maxf(escala, 0.5)
	var tamanho := Vector2(LARGURA_TELA, ALTURA_TELA) * escala
	_tela_crt.size = tamanho
	_tela_crt.position = ((size - tamanho) * 0.5 + Vector2(0, size.y * 0.01)).round()
	queue_redraw()


## Moldura do gabinete (desenhada em resolução cheia, por isso os textos são nítidos).
func _draw() -> void:
	desenhar_moldura(self, _tela_crt, "TITO KART", COR_AMARELO, COR_ZEBRA_1, _fonte_crt,
		"WASD dirige · ESPAÇO turbo · ESC/E sai")


## Moldura reaproveitável (o SPACE PIZZA usa a mesma, com outras cores).
static func desenhar_moldura(no: Control, tela: TextureRect, titulo: String, cor_titulo: Color,
		cor_borda: Color, fonte_controles: Font, controles: String) -> void:
	if tela == null:
		return
	var fonte_titulo: Font = load("res://assets/fontes/PressStart2P/PressStart2P-Regular.ttf")
	no.draw_rect(Rect2(Vector2.ZERO, no.size), Color(0.015, 0.012, 0.02, 0.96))
	var r := Rect2(tela.position, tela.size)
	var alto := r.size.y
	# Gabinete: plástico escuro com filete colorido.
	var gabinete := StyleBoxFlat.new()
	gabinete.bg_color = Color(0.07, 0.055, 0.08)
	gabinete.set_corner_radius_all(int(alto * 0.04))
	gabinete.set_border_width_all(maxi(2, int(alto * 0.006)))
	gabinete.border_color = cor_borda.darkened(0.25)
	var area_gabinete := Rect2(r.position - Vector2(alto * 0.07, alto * 0.15),
		r.size + Vector2(alto * 0.14, alto * 0.27))
	no.draw_style_box(gabinete, area_gabinete)
	# Vidro em volta do tubo.
	var vidro := StyleBoxFlat.new()
	vidro.bg_color = Color(0.0, 0.0, 0.0)
	vidro.set_corner_radius_all(int(alto * 0.03))
	no.draw_style_box(vidro, r.grow(alto * 0.025))
	# Letreiro com sombra.
	var tam_titulo := int(alto * 0.065)
	var base_titulo := Vector2(area_gabinete.position.x, r.position.y - alto * 0.05)
	var largura := area_gabinete.size.x
	no.draw_string(fonte_titulo, base_titulo + Vector2(3, 3), titulo, HORIZONTAL_ALIGNMENT_CENTER,
		largura, tam_titulo, cor_borda)
	no.draw_string(fonte_titulo, base_titulo, titulo, HORIZONTAL_ALIGNMENT_CENTER, largura,
		tam_titulo, cor_titulo)
	# Linha de controles embaixo da tela.
	var tam_controles := int(alto * 0.065)
	no.draw_string(fonte_controles, Vector2(area_gabinete.position.x, r.end.y + alto * 0.085),
		controles, HORIZONTAL_ALIGNMENT_CENTER, largura, tam_controles, Color(0.85, 0.85, 0.8))


# ==============================================================================
# Pista
# ==============================================================================

## Ponto de uma curva Catmull-Rom entre p1 e p2 (t de 0 a 1). p0 e p3 são os vizinhos.
static func catmull_rom(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, t: float) -> Vector2:
	var t2 := t * t
	var t3 := t2 * t
	return 0.5 * ((2.0 * p1) + (p2 - p0) * t + (2.0 * p0 - 5.0 * p1 + 4.0 * p2 - p3) * t2 \
		+ (3.0 * p1 - p0 - 3.0 * p2 + p3) * t3)


## Gera a linha central suave e depois a reamostra com pontos igualmente espaçados.
## Pontos igualmente espaçados deixam o "progresso" (quantos pontos andou) justo.
func _gerar_pista() -> void:
	var fina := PackedVector2Array()
	var n := PONTOS_CONTROLE.size()
	for i in n:
		var p0: Vector2 = PONTOS_CONTROLE[(i - 1 + n) % n]
		var p1: Vector2 = PONTOS_CONTROLE[i]
		var p2: Vector2 = PONTOS_CONTROLE[(i + 1) % n]
		var p3: Vector2 = PONTOS_CONTROLE[(i + 2) % n]
		for k in 24:
			fina.append(catmull_rom(p0, p1, p2, p3, k / 24.0))

	pista = PackedVector2Array([fina[0]])
	var andado := 0.0  # distância desde o último ponto colocado
	for i in fina.size():
		var a: Vector2 = fina[i]
		var b: Vector2 = fina[(i + 1) % fina.size()]
		var segmento := a.distance_to(b)
		var dentro := 0.0  # quanto já avançamos neste segmento
		while andado + (segmento - dentro) >= ESPACAMENTO:
			dentro += ESPACAMENTO - andado
			pista.append(a.lerp(b, dentro / segmento))
			andado = 0.0
		andado += segmento - dentro
	# O último ponto pode ter caído em cima do primeiro: tira.
	if pista[pista.size() - 1].distance_to(pista[0]) < ESPACAMENTO * 0.5:
		pista.remove_at(pista.size() - 1)

	var total := pista.size()
	angulos.resize(total)
	normais.resize(total)
	for i in total:
		var tangente := (pista[(i + 1) % total] - pista[(i - 1 + total) % total]).normalized()
		angulos[i] = tangente.angle()
		normais[i] = Vector2(-tangente.y, tangente.x)  # 90° para a direita de quem anda
	_fundo.queue_redraw()


## Distância do ponto até a linha central, olhando os dois segmentos vizinhos do índice.
func _distancia_ao_centro(p: Vector2, indice: int) -> float:
	var n := pista.size()
	var a: Vector2 = pista[(indice - 1 + n) % n]
	var b: Vector2 = pista[indice]
	var c: Vector2 = pista[(indice + 1) % n]
	var d1 := p.distance_to(Geometry2D.get_closest_point_to_segment(p, a, b))
	var d2 := p.distance_to(Geometry2D.get_closest_point_to_segment(p, b, c))
	return minf(d1, d2)


## Atualiza o índice, o progresso e se o carrinho está na grama.
func _atualizar_na_pista(c: Carro) -> void:
	var n := pista.size()
	var melhor := c.indice
	var melhor_d := INF
	# Procura só perto do último índice (a pista passa perto de si mesma em alguns trechos).
	for k in range(-10, 11):
		var i := posmod(c.indice + k, n)
		var d := c.pos.distance_squared_to(pista[i])
		if d < melhor_d:
			melhor_d = d
			melhor = i
	# Se o carrinho foi parar longe (empurrão, atalho), procura na pista inteira.
	if melhor_d > 40.0 * 40.0:
		for i in n:
			var d := c.pos.distance_squared_to(pista[i])
			if d < melhor_d:
				melhor_d = d
				melhor = i
	var delta := melhor - c.indice
	if delta > n * 0.5:
		delta -= n
	elif delta < -n * 0.5:
		delta += n
	c.progresso += delta
	c.indice = melhor
	c.na_grama = _distancia_ao_centro(c.pos, melhor) > LARGURA_PISTA * 0.5


## Volta em que o carrinho está (1 a VOLTAS).
func volta_de(c: Carro) -> int:
	return clampi(floori(float(c.progresso) / pista.size()) + 1, 1, VOLTAS)


## Posição na corrida (1 = primeiro). Quem já chegou vale pela ordem de chegada.
func posicao_de(c: Carro) -> int:
	var pos := 1
	for outro in carros:
		if outro != c and _pontuacao(outro) > _pontuacao(c):
			pos += 1
	return pos


func _pontuacao(c: Carro) -> float:
	if c.terminou:
		return 1000000.0 - c.tempo_chegada
	return float(c.progresso)


# ==============================================================================
# Início
# ==============================================================================

func _ao_iniciar() -> void:
	var v := dificuldade.velocidade_rivais_kart
	tempo_ger = TEMPO_IDEAL + FOLGA_NORMAL / (v * v)
	estado = Estado.RECORDES
	tempo_estado = 0.0
	tempo_corrida = 0.0
	_espaco_antes = Input.is_action_pressed("minigame_acao")
	_montar_largada()
	_posicionar_tela()


func _montar_largada() -> void:
	var n := pista.size()
	carros.clear()
	# Rivais na primeira fila (lado a lado); o jogador larga atrás, no meio.
	var nomes: Array[String] = ["PIP", "BOB"]
	var cores: Array[Color] = [Color(0.92, 0.15, 0.15), Color(0.15, 0.4, 0.95)]
	var faixas: Array[float] = [-6.0, 6.0]
	var v := dificuldade.velocidade_rivais_kart
	for i in 2:
		var r := Carro.new()
		r.nome = nomes[i]
		r.cor = cores[i]
		r.vel_max = VEL_MAX * PROPORCAO_RIVAIS[i] * v
		r.aceleracao = ACELERACAO * (0.9 + 0.1 * v)
		r.faixa = faixas[i]
		_colocar_no_grid(r, n - 3, faixas[i])
		carros.append(r)
	jogador = Carro.new()
	jogador.nome = "TITO"
	jogador.cor = COR_JOGADOR
	jogador.eh_jogador = true
	jogador.vel_max = VEL_MAX
	jogador.aceleracao = ACELERACAO
	_colocar_no_grid(jogador, n - 8, 0.0)
	carros.append(jogador)

	# Três fatias de pizza espalhadas pela volta.
	fatias.clear()
	var lugares: Array[float] = [0.17, 0.46, 0.80]
	var lados: Array[float] = [-4.0, 4.0, 0.0]
	for k in lugares.size():
		var f := Fatia.new()
		var i := int(lugares[k] * n)
		f.pos = pista[i] + normais[i] * lados[k]
		fatias.append(f)


func _colocar_no_grid(c: Carro, indice: int, lado: float) -> void:
	var n := pista.size()
	c.indice = posmod(indice, n)
	c.progresso = c.indice - n  # ainda antes da linha de chegada: progresso negativo
	c.pos = pista[c.indice] + normais[c.indice] * lado
	c.angulo = angulos[c.indice]


# ==============================================================================
# Laço principal
# ==============================================================================

func _ao_processar(delta: float) -> void:
	_acumulador += minf(delta, 0.1)
	while _acumulador >= PASSO and not _acabou:
		_acumulador -= PASSO
		_passo(PASSO)
	_atualizar_motor()
	_desenho.queue_redraw()


func _passo(dt: float) -> void:
	tempo_estado += dt
	_relogio += dt
	var espaco := Input.is_action_pressed("minigame_acao")
	var espaco_apertou := espaco and not _espaco_antes
	_espaco_antes = espaco

	match estado:
		Estado.RECORDES:
			if tempo_estado > 5.0 or espaco_apertou or piloto_automatico:
				_mudar_estado(Estado.CONTAGEM)
		Estado.CONTAGEM:
			var falta := 3 - int(tempo_estado)
			if falta != _ultimo_bip and falta > 0:
				_ultimo_bip = falta
				_tocar(_som_bip)
			if tempo_estado >= 3.0:
				_tocar(_som_largada)
				_mudar_estado(Estado.CORRIDA)
		Estado.CORRIDA:
			tempo_corrida += dt
			_ler_entradas(espaco_apertou)
			_simular_carros(dt)
			_verificar_fim()
		Estado.FIM:
			# Os rivais continuam andando atrás da mensagem.
			for c in carros:
				if c.eh_jogador:
					c.ent_acelerar = 0.0
					c.ent_frear = 0.0
					c.ent_virar = 0.0
					c.ent_turbo = false
			_simular_carros(dt)
			if tempo_estado > (2.4 if venceu else 2.0):
				if venceu:
					finalizar(true, {"digitos": _digitos()})
				else:
					finalizar(false, {})


func _mudar_estado(novo: Estado) -> void:
	estado = novo
	tempo_estado = 0.0


## Teclado -> entradas do carrinho do jogador; piloto do computador -> entradas dos rivais.
func _ler_entradas(espaco_apertou: bool) -> void:
	for c in carros:
		if c.eh_jogador and not piloto_automatico:
			c.ent_acelerar = 1.0 if Input.is_action_pressed("mover_frente") else 0.0
			c.ent_frear = 1.0 if Input.is_action_pressed("mover_tras") else 0.0
			c.ent_virar = Input.get_axis("mover_esquerda", "mover_direita")
			c.ent_turbo = espaco_apertou
		elif not c.terminou:
			_pilotar_computador(c)
		else:
			# Rival que já chegou dá uma volta de honra devagar.
			_pilotar_computador(c)
			c.ent_acelerar = 0.4


## Piloto do computador: mira num ponto um pouco à frente na pista e freia antes das curvas fechadas.
func _pilotar_computador(c: Carro) -> void:
	var n := pista.size()
	var i_alvo := (c.indice + OLHAR_FRENTE) % n
	var alvo: Vector2 = pista[i_alvo] + normais[i_alvo] * c.faixa
	var erro := wrapf((alvo - c.pos).angle() - c.angulo, -PI, PI)
	c.ent_virar = clampf(erro * 2.5, -1.0, 1.0)
	# Quanto a pista vai virar nos próximos ~64 px?
	var curva := 0.0
	for k: int in [4, 8, 12, 16]:
		var dif := absf(wrapf(angulos[(c.indice + k) % n] - angulos[c.indice], -PI, PI))
		curva = maxf(curva, dif)
	var vel_alvo := c.vel_max * clampf(1.12 - curva * 0.5, 0.55, 1.0)
	if c.tempo_turbo > 0.0:
		vel_alvo *= TURBO_FATOR
	if c.velocidade > vel_alvo + 2.0:
		c.ent_acelerar = 0.0
		c.ent_frear = 1.0
	else:
		c.ent_acelerar = 1.0
		c.ent_frear = 0.0
	c.ent_turbo = c.tem_turbo and curva < 0.3 and not c.na_grama


func _simular_carros(dt: float) -> void:
	for c in carros:
		_mover_carro(c, dt)
	_colisoes_entre_carros(dt)
	for c in carros:
		_atualizar_na_pista(c)
		if not c.terminou and c.progresso >= VOLTAS * pista.size():
			c.terminou = true
			c.tempo_chegada = tempo_corrida
	_pegar_pizzas(dt)
	_tempo_batida = maxf(0.0, _tempo_batida - dt)


## A física do carrinho (igual para todos).
func _mover_carro(c: Carro, dt: float) -> void:
	if c.ent_turbo and c.tem_turbo:
		c.tem_turbo = false
		c.tempo_turbo = TURBO_DURACAO
		c.velocidade = maxf(c.velocidade, c.vel_max)
		if c.eh_jogador:
			_tocar(_som_turbo)
	var vmax := c.vel_max
	var acel := c.aceleracao
	if c.tempo_turbo > 0.0:
		c.tempo_turbo -= dt
		vmax *= TURBO_FATOR
		acel *= 2.2
	if c.na_grama:
		vmax *= FATOR_GRAMA

	if c.ent_acelerar > 0.0:
		c.velocidade += acel * c.ent_acelerar * dt
	elif c.ent_frear > 0.0:
		if c.velocidade > 0.0:
			c.velocidade -= FREIO * c.ent_frear * dt
		else:
			c.velocidade -= acel * 0.5 * c.ent_frear * dt  # ré
	else:
		c.velocidade = move_toward(c.velocidade, 0.0, ATRITO * dt)
	# Acima do limite (ex.: entrou na grama embalado): perde velocidade rápido, sem parar seco.
	if c.velocidade > vmax:
		c.velocidade = move_toward(c.velocidade, vmax, 140.0 * dt)
	c.velocidade = maxf(c.velocidade, -VEL_RE)

	# O carrinho só vira se estiver andando (e de ré o volante inverte, como num carro de verdade).
	var fator_giro := clampf(c.velocidade / 25.0, -1.0, 1.0)
	c.angulo = wrapf(c.angulo + c.ent_virar * GIRO * fator_giro * dt, -PI, PI)
	c.pos += Vector2.from_angle(c.angulo) * c.velocidade * dt

	# Bordas da tela funcionam como muro.
	var limite := Rect2(5, ALTURA_HUD + 5, LARGURA_TELA - 10, ALTURA_TELA - ALTURA_HUD - 10)
	var presa := c.pos.clamp(limite.position, limite.end)
	if presa != c.pos:
		c.pos = presa
		c.velocidade *= 0.5


## Carrinhos que se encostam são empurrados para os lados e perdem um pouco de velocidade.
func _colisoes_entre_carros(dt: float) -> void:
	for i in carros.size():
		for j in range(i + 1, carros.size()):
			var a := carros[i]
			var b := carros[j]
			var d := b.pos - a.pos
			var dist := d.length()
			if dist < RAIO_CARRO * 2.0 and dist > 0.001:
				var empurrao := d / dist * (RAIO_CARRO * 2.0 - dist) * 0.5
				a.pos -= empurrao
				b.pos += empurrao
				a.velocidade = move_toward(a.velocidade, 0.0, 40.0 * dt)
				b.velocidade = move_toward(b.velocidade, 0.0, 40.0 * dt)
				if (a.eh_jogador or b.eh_jogador) and _tempo_batida <= 0.0:
					_tempo_batida = 0.5
					_tocar(_som_batida)


func _pegar_pizzas(dt: float) -> void:
	for f in fatias:
		if not f.ativa:
			f.tempo_para_voltar -= dt
			if f.tempo_para_voltar <= 0.0:
				f.ativa = true
		elif not jogador.tem_turbo and jogador.pos.distance_to(f.pos) < 8.0:
			f.ativa = false
			f.tempo_para_voltar = 5.0
			jogador.tem_turbo = true
			_tocar(_som_pizza)


func _verificar_fim() -> void:
	var rival_chegou := false
	var todos_rivais := true
	for c in carros:
		if not c.eh_jogador:
			rival_chegou = rival_chegou or c.terminou
			todos_rivais = todos_rivais and c.terminou
	if jogador.terminou:
		var pos := posicao_de(jogador)
		venceu = pos == 1 and jogador.tempo_chegada < tempo_ger
		if venceu:
			mensagem_fim = ["NOVO RECORDE!", "SEU TEMPO " + formatar_tempo(jogador.tempo_chegada),
				"A SENHA COMEÇA COM", _digitos() + ".."]
		elif pos > 1:
			mensagem_fim = ["VOCÊ CHEGOU EM %dº" % pos, "TENTE DE NOVO"]
		else:
			mensagem_fim = ["1º LUGAR... MAS", "O GER AINDA É MAIS RÁPIDO"]
	elif encerrar_quando_impossivel and rival_chegou:
		mensagem_fim = ["%s CHEGOU NA FRENTE" % _primeiro_rival(), "TENTE DE NOVO"]
	elif encerrar_quando_impossivel and tempo_corrida > tempo_ger:
		mensagem_fim = ["TEMPO DO GER ESTOUROU", "TENTE DE NOVO"]
	elif todos_rivais or tempo_corrida > tempo_ger + 60.0:
		mensagem_fim = ["FIM DE CORRIDA", "TENTE DE NOVO"]
	else:
		return
	resultado_corrida = {
		"venceu": venceu,
		"tempo_jogador": jogador.tempo_chegada if jogador.terminou else -1.0,
		"posicao": posicao_de(jogador),
		"tempo_ger": tempo_ger,
		"tempos_rivais": carros.filter(func(c: Carro) -> bool: return not c.eh_jogador) \
			.map(func(c: Carro) -> float: return c.tempo_chegada if c.terminou else -1.0),
	}
	_tocar(_som_vitoria if venceu else _som_derrota)
	_mudar_estado(Estado.FIM)


func _primeiro_rival() -> String:
	var melhor := ""
	var melhor_tempo := INF
	for c in carros:
		if not c.eh_jogador and c.terminou and c.tempo_chegada < melhor_tempo:
			melhor_tempo = c.tempo_chegada
			melhor = c.nome
	return melhor


## Os 2 primeiros dígitos da senha (ou "47" se ninguém passou o código).
func _digitos() -> String:
	var codigo := str(dados.get("codigo", "47"))
	if codigo.length() < 2:
		codigo = "47"
	return codigo.substr(0, 2)


func _resultado_decidido() -> Variant:
	return [true, {"digitos": _digitos()}] if estado == Estado.FIM and venceu else null


func _ao_vencer_agora() -> void:
	finalizar(true, {"digitos": _digitos()})


static func formatar_tempo(t: float) -> String:
	return "%d:%05.2f" % [int(t / 60.0), fmod(t, 60.0)]


# ==============================================================================
# Sons
# ==============================================================================

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


## O ronco do motor sobe de tom com a velocidade.
func _atualizar_motor() -> void:
	if _som_motor.stream == null:
		return
	var ligado := estado != Estado.RECORDES
	if ligado and not _som_motor.playing:
		_som_motor.play()
	elif not ligado and _som_motor.playing:
		_som_motor.stop()
	if jogador:
		var fracao := absf(jogador.velocidade) / VEL_MAX
		_som_motor.pitch_scale = 0.7 + fracao * 1.1
		_som_motor.volume_db = -14.0 + fracao * 6.0


func _ao_motor_parar() -> void:
	# Plano B caso o .wav não tenha sido importado como loop.
	if rodando and estado != Estado.RECORDES:
		_som_motor.play()


# ==============================================================================
# Desenho (tudo em pixels da tela interna 320×240)
# ==============================================================================

## Grama, zebras, asfalto e linha de chegada. Não muda, então é desenhado uma vez só.
func _desenhar_fundo() -> void:
	var d := _fundo
	# Grama quadriculada (as listras ajudam a perceber a velocidade).
	for y in range(0, ALTURA_TELA, 16):
		for x in range(0, LARGURA_TELA, 16):
			var cor := COR_GRAMA_1 if int((x + y) / 16.0) % 2 == 0 else COR_GRAMA_2
			d.draw_rect(Rect2(x, y, 16, 16), cor)
	if pista.is_empty():
		return
	var n := pista.size()
	var meia := LARGURA_PISTA * 0.5
	# Cada trecho entre dois pontos vira um quadrilátero (esquerda e direita da linha central).
	for i in n:
		var j := (i + 1) % n
		var cor_zebra := COR_ZEBRA_1 if int(i / 2.0) % 2 == 0 else COR_ZEBRA_2
		for lado: float in [-1.0, 1.0]:
			var faixa_zebra := PackedVector2Array([
				pista[i] + normais[i] * lado * meia, pista[j] + normais[j] * lado * meia,
				pista[j] + normais[j] * lado * (meia + 3.0), pista[i] + normais[i] * lado * (meia + 3.0)])
			d.draw_colored_polygon(faixa_zebra, cor_zebra)
	for i in n:
		var j := (i + 1) % n
		var asfalto := PackedVector2Array([
			pista[i] - normais[i] * meia, pista[j] - normais[j] * meia,
			pista[j] + normais[j] * meia, pista[i] + normais[i] * meia])
		d.draw_colored_polygon(asfalto, COR_ASFALTO)
	# Faixa tracejada no meio.
	for i in range(0, n, 4):
		d.draw_line(pista[i], pista[(i + 1) % n], Color(0.85, 0.85, 0.8, 0.6), 1.0)
	# Linha de chegada quadriculada (2 colunas de quadradinhos de 2 px).
	d.draw_set_transform(pista[0], angulos[0], Vector2.ONE)
	for linha in 2:
		for k in range(-int(meia / 2.0), int(meia / 2.0)):
			var branco := (k + linha) % 2 == 0
			d.draw_rect(Rect2(linha * 2.0 - 2.0, k * 2.0, 2.0, 2.0), Color.WHITE if branco else Color.BLACK)
	d.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# Arquibancada de enfeite no miolo da pista.
	for k in 6:
		var x := 196.0 + k * 12.0
		d.draw_rect(Rect2(x, 150, 10, 14), Color(0.75, 0.75, 0.8))
		d.draw_rect(Rect2(x + 2, 152, 6, 3), [COR_ZEBRA_1, COR_AMARELO, Color(0.2, 0.45, 1.0)][k % 3])


## Carrinhos, pizzas, HUD e as telas de recorde, contagem e fim.
func _desenhar_quadro() -> void:
	var d := _desenho
	if pista.is_empty() or jogador == null:
		return
	for f in fatias:
		if f.ativa:
			_desenhar_fatia(d, f.pos + Vector2(0, sin(_relogio * 5.0) * 1.0), 1.0)
	for c in carros:
		_desenhar_carro(d, c)
	_desenhar_hud(d)
	match estado:
		Estado.RECORDES:
			_desenhar_recordes(d)
		Estado.CONTAGEM:
			_desenhar_contagem(d)
		Estado.CORRIDA:
			if tempo_estado < 0.8:
				_texto_centro(d, 136, "JÁ!", 32, Color(0.2, 1.0, 0.3))
		Estado.FIM:
			_desenhar_fim(d)


func _desenhar_carro(d: Node2D, c: Carro) -> void:
	d.draw_set_transform(c.pos.round(), c.angulo, Vector2.ONE)
	# Fogo do turbo saindo de trás.
	if c.tempo_turbo > 0.0:
		var chama := 4.0 + 3.0 * absf(sin(_relogio * 40.0))
		d.draw_colored_polygon(PackedVector2Array([Vector2(-5, -2), Vector2(-5 - chama, 0), Vector2(-5, 2)]),
			Color(1.0, 0.55, 0.1))
		d.draw_colored_polygon(PackedVector2Array([Vector2(-5, -1), Vector2(-5 - chama * 0.5, 0), Vector2(-5, 1)]),
			COR_AMARELO)
	# Rodas (pretas), carroceria, bico mais claro e o piloto.
	for x: float in [-4.0, 2.0]:
		for y: float in [-4.5, 3.0]:
			d.draw_rect(Rect2(x, y, 3, 1.5), Color(0.05, 0.05, 0.05))
	d.draw_rect(Rect2(-5, -3, 10, 6), c.cor)
	d.draw_rect(Rect2(3, -2, 2, 4), c.cor.lightened(0.35))
	d.draw_rect(Rect2(-5, -3, 1, 6), c.cor.darkened(0.4))
	if c.eh_jogador:
		# Tito: cabeça marrom e chapéu de chef branco.
		d.draw_circle(Vector2(-1, 0), 2.0, Color(0.42, 0.25, 0.12))
		d.draw_circle(Vector2(-1.5, 0), 1.6, Color.WHITE)
		d.draw_rect(Rect2(-3.5, -1.0, 1.5, 2.0), Color.WHITE)
	else:
		d.draw_circle(Vector2(-1, 0), 1.8, Color(1.0, 0.85, 0.6))
		d.draw_rect(Rect2(-2, -1, 2, 2), c.cor.darkened(0.5))  # capacete
	d.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)
	# Poeira quando está na grama.
	if c.na_grama and absf(c.velocidade) > 10.0:
		var tras := c.pos - Vector2.from_angle(c.angulo) * 6.0
		for k in 3:
			var o := Vector2(sin(_relogio * 31.0 + k * 2.1), cos(_relogio * 23.0 + k * 1.7)) * 2.5
			d.draw_rect(Rect2((tras + o).round(), Vector2(1, 1)), Color(0.65, 0.5, 0.3))


## Fatia de pizza: triângulo de queijo, borda de massa e pepperonis.
func _desenhar_fatia(d: Node2D, centro: Vector2, escala: float) -> void:
	d.draw_set_transform(centro.round(), 0.0, Vector2.ONE * escala)
	d.draw_colored_polygon(PackedVector2Array([Vector2(-4, -4), Vector2(4, -4), Vector2(0, 4)]), COR_AMARELO)
	d.draw_rect(Rect2(-4, -5, 8, 2), Color(0.75, 0.42, 0.15))
	d.draw_rect(Rect2(-2, -2, 1.5, 1.5), Color(0.85, 0.1, 0.1))
	d.draw_rect(Rect2(1, -1, 1.5, 1.5), Color(0.85, 0.1, 0.1))
	d.draw_rect(Rect2(-0.5, 1, 1.5, 1.5), Color(0.85, 0.1, 0.1))
	d.draw_set_transform(Vector2.ZERO, 0.0, Vector2.ONE)


func _desenhar_hud(d: Node2D) -> void:
	d.draw_rect(Rect2(0, 0, LARGURA_TELA, ALTURA_HUD), Color(0.02, 0.02, 0.06))
	d.draw_rect(Rect2(0, ALTURA_HUD - 1, LARGURA_TELA, 1), Color(0.2, 0.45, 1.0))
	var y := 12.0
	_texto(d, Vector2(4, y), "VOLTA %d/%d" % [volta_de(jogador), VOLTAS], 8, Color.WHITE)
	var pos := posicao_de(jogador)
	var cor_pos := COR_AMARELO if pos == 1 else Color(1.0, 0.35, 0.3)
	_texto(d, Vector2(86, y), "%dº" % pos, 8, cor_pos)
	_texto(d, Vector2(114, y), formatar_tempo(tempo_corrida), 8, Color.WHITE)
	# Turbo guardado: a fatia aparece no HUD e pisca.
	d.draw_rect(Rect2(178, 2, 13, 12), Color(0.2, 0.45, 1.0), false, 1.0)
	if jogador.tem_turbo and fmod(_relogio, 0.5) < 0.35:
		_desenhar_fatia(d, Vector2(184.5, 8.5), 1.0)
	var estourou := estado == Estado.CORRIDA and tempo_corrida > tempo_ger
	var cor_ger := Color(1.0, 0.3, 0.3) if estourou else COR_CIANO
	_texto(d, Vector2(0, y), "GER " + formatar_tempo(tempo_ger), 8, cor_ger,
		HORIZONTAL_ALIGNMENT_RIGHT, LARGURA_TELA - 4)


func _desenhar_recordes(d: Node2D) -> void:
	d.draw_rect(Rect2(0, ALTURA_HUD, LARGURA_TELA, ALTURA_TELA - ALTURA_HUD), Color(0, 0, 0, 0.55))
	var painel := Rect2(36, 30, 248, 196)
	d.draw_rect(painel, Color(0.02, 0.02, 0.08, 0.92))
	d.draw_rect(painel, Color(0.2, 0.45, 1.0), false, 2.0)
	_texto_centro(d, 56, "TITO KART", 16, COR_AMARELO, COR_ZEBRA_1)
	_texto_centro(d, 76, "- RECORDES -", 8, COR_CIANO)
	var linhas: Array = [["GER", 0.0], ["PIP", 6.35], ["BOB", 11.8], ["ANA", 17.2], ["LUC", 24.65]]
	for k in linhas.size():
		var linha: Array = linhas[k]
		var nome: String = linha[0]
		var extra: float = linha[1]
		var cor := Color.WHITE
		if k == 0:
			cor = COR_AMARELO if fmod(_relogio, 0.6) < 0.4 else Color(1.0, 0.6, 0.1)
		var texto := "%dº  %s  %s" % [k + 1, nome, formatar_tempo(tempo_ger + extra)]
		_texto_centro(d, 100 + k * 14, texto, 8, cor)
	if fmod(_relogio, 0.8) < 0.55:
		_texto_centro(d, 184, "BATA O TEMPO DO GER!", 8, Color(1.0, 0.35, 0.3))
	_texto_centro(d, 204, "1º LUGAR E MAIS RÁPIDO", 8, Color(0.75, 0.75, 0.8))
	_texto_centro(d, 218, "ESPAÇO: COMEÇAR", 8, Color(0.3, 1.0, 0.4))


func _desenhar_contagem(d: Node2D) -> void:
	var falta := 3 - int(tempo_estado)
	var cores: Array[Color] = [Color(0.2, 1.0, 0.3), COR_AMARELO, Color(1.0, 0.25, 0.2)]
	var cor := cores[clampi(falta - 1, 0, 2)]
	_texto_centro(d, 136, str(falta), 32, cor, Color(0, 0, 0))
	# Setinha "VOCÊ" em cima do carrinho do jogador.
	var p := jogador.pos.round()
	_texto(d, p + Vector2(-15, -14), "VOCÊ", 8, Color.WHITE)
	d.draw_colored_polygon(PackedVector2Array([p + Vector2(-3, -10), p + Vector2(3, -10), p + Vector2(0, -7)]),
		Color.WHITE)


func _desenhar_fim(d: Node2D) -> void:
	var painel := Rect2(20, 64, 280, 112)
	d.draw_rect(painel, Color(0.02, 0.02, 0.08, 0.94))
	d.draw_rect(painel, COR_AMARELO if venceu else Color(1.0, 0.3, 0.3), false, 2.0)
	if mensagem_fim.is_empty():
		return
	if venceu:
		var arco := Color.from_hsv(fmod(_relogio * 0.8, 1.0), 0.8, 1.0)
		_texto_centro(d, 94, mensagem_fim[0], 16, arco, Color(0, 0, 0))
		_texto_centro(d, 114, mensagem_fim[1], 8, Color.WHITE)
		_texto_centro(d, 136, mensagem_fim[2], 8, COR_CIANO)
		_texto_centro(d, 162, mensagem_fim[3], 16, COR_AMARELO, COR_ZEBRA_1)
	else:
		_texto_centro(d, 108, mensagem_fim[0], 8, Color(1.0, 0.4, 0.35))
		_texto_centro(d, 136, mensagem_fim[1], 8, Color.WHITE)


## Texto na tela interna. 'pos' é o canto esquerdo da linha de base da letra.
func _texto(d: Node2D, pos: Vector2, texto: String, tamanho: int, cor: Color,
		alinhamento := HORIZONTAL_ALIGNMENT_LEFT, largura := -1.0) -> void:
	d.draw_string(_fonte, pos.round(), texto, alinhamento, largura, tamanho, cor)


## Texto centralizado na largura da tela, com sombra opcional (deslocada 1 px por 8 px de letra).
func _texto_centro(d: Node2D, y: float, texto: String, tamanho: int, cor: Color,
		cor_sombra := Color(0, 0, 0, 0)) -> void:
	if cor_sombra.a > 0.0:
		var o := float(maxi(1, floori(tamanho / 8.0)))
		d.draw_string(_fonte, Vector2(o, y + o), texto, HORIZONTAL_ALIGNMENT_CENTER, LARGURA_TELA, tamanho, cor_sombra)
	d.draw_string(_fonte, Vector2(0, y), texto, HORIZONTAL_ALIGNMENT_CENTER, LARGURA_TELA, tamanho, cor)
