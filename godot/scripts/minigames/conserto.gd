class_name MinigameConserto
extends Minigame
## CONSERTO DO DISJUNTOR — a caixa do disjuntor aberta, vista de frente.
##
## Dois modos (dados.modo):
##   "fios"    -> Disjuntor da Cozinha: ligar 4 fios soltos nos bornes da mesma cor.
##                W/S escolhe o fio, ESPAÇO pega; W/S escolhe o borne, ESPAÇO liga.
##                Errou: faísca, susto, o fio volta. No Pesadelo (embaralhar_fios),
##                as cores dos bornes livres trocam de lugar a cada erro.
##   "fusivel" -> Disjuntor do Gerente: 3 fusíveis, um queimado (vidro preto).
##                A/D escolhe, ESPAÇO tira; depois A/D escolhe um fusível novo na
##                caixinha e ESPAÇO encaixa. Tirar um fusível BOM dá choque.
##
## O mouse também funciona: clique no fio (ou fusível) e depois no borne (ou na caixinha).
##
## Computação Gráfica: os fios são CURVAS DE BÉZIER cúbicas (4 pontos de controle),
## as faíscas são um SISTEMA DE PARTÍCULAS simples (posição, velocidade, gravidade,
## tempo de vida) e o "tremor" da tela é um deslocamento aleatório na matriz de vista.

const VIRTUAL := Vector2(1280.0, 720.0)

## Cores dos fios, na ordem em que saem do bloco da esquerda.
const CORES := [Color(0.92, 0.16, 0.14), Color(0.2, 0.45, 0.98), Color(0.98, 0.84, 0.12), Color(0.2, 0.8, 0.3)]
const NOMES_CORES := ["VERMELHO", "AZUL", "AMARELO", "VERDE"]

# Posições (no papel 1280x720)
const X_ANCORA := 430.0          ## onde os fios saem (bloco da esquerda)
const X_BORNE := 790.0           ## centro dos bornes (direita)
const Y_PRIMEIRO := 220.0
const ESPACO_Y := 92.0
const X_FUSIVEIS := [500.0, 640.0, 780.0]
const Y_FUSIVEL := 300.0
const AMPERAGEM_CERTA := 20
const PONTO_FAISCA := Vector2(905.0, 140.0)  ## fio desencapado que solta faíscas sozinho

const TEMPO_FIM := 1.1           ## pausa com a mensagem de sucesso antes de fechar
const BLOQUEIO_ERRO := 0.55      ## tempo sem controle depois de ligar errado
const BLOQUEIO_CHOQUE := 1.0     ## tempo sem controle depois do choque ("perde ~1 s")

## Uma partícula de faísca.
class Faisca:
	var pos := Vector2.ZERO
	var vel := Vector2.ZERO
	var vida := 0.0
	var vida_max := 0.5
	var cor := Color(1.0, 0.9, 0.5)

var sorteio := RandomNumberGenerator.new()
var modo := "fios"
## Fase atual: fios -> "fio" / "borne"; fusível -> "tirar" / "por"; ambos -> "fim".
var fase := "fio"

# --- Fios ---
## cor (índice em CORES) de cada borne, de cima para baixo.
var borne_cores: Array[int] = [0, 1, 2, 3]
var fio_ligado: Array[bool] = [false, false, false, false]    ## por fio (cor)
var borne_ocupado: Array[bool] = [false, false, false, false]  ## por posição de borne
var cursor_fio := 0
var cursor_borne := 0
var erros := 0

# --- Fusível ---
## Estado de cada suporte: "bom", "queimado", "vazio" ou "novo".
var suportes: Array[String] = ["bom", "bom", "bom"]
## Amperagem dos fusíveis da caixinha (0 = já usado/tirado da caixinha).
var caixinha: Array[int] = [10, 20, 30]
var cursor_suporte := 0
var cursor_caixa := 0
var suporte_vazio := -1

var _bloqueio := 0.0
var _tremor := 0.0
var _tremor_forca := 0.0
var _clarao := 0.0
var _cor_clarao := Color.WHITE
var _relogio := 0.0
var _proxima_faisca := 1.0
var _tempo_fim := 0.0
var _aviso := ""
var _tempo_aviso := 0.0
var _faiscas: Array[Faisca] = []
var _vista := Transform2D.IDENTITY

var _som_zumbido: AudioStreamPlayer
var _som_faisca: AudioStreamPlayer
var _som_estalo: AudioStreamPlayer
var _som_choque: AudioStreamPlayer
var _som_encaixe: AudioStreamPlayer

var _fonte_titulo: Font = preload("res://assets/fontes/Bungee/Bungee-Regular.ttf")
var _fonte_pixel: Font = preload("res://assets/fontes/PressStart2P/PressStart2P-Regular.ttf")
var _fonte_tela: Font = preload("res://assets/fontes/VT323/VT323-Regular.ttf")
var _fonte_placa: Font = preload("res://assets/fontes/CourierPrime/CourierPrime-Bold.ttf")


func _init() -> void:
	nome_minigame = "conserto_fios"
	intensidade_ruido = 0.4


# =============================================================================
# Início
# =============================================================================

func _ao_iniciar() -> void:
	sorteio.randomize()
	modo = "fusivel" if str(dados.get("modo", "fios")) == "fusivel" else "fios"
	nome_minigame = "conserto_" + modo
	intensidade_ruido = 0.4
	if modo == "fios":
		fase = "fio"
		_embaralhar_bornes(true)
	else:
		fase = "tirar"
		suportes = ["bom", "bom", "bom"]
		suportes[sorteio.randi_range(0, 2)] = "queimado"
		caixinha = [10, 20, 30]
		_embaralhar_inteiros(caixinha)
		cursor_suporte = 1
		cursor_caixa = 1
	_som_zumbido = _criar_som("conserto_zumbido.wav", -10.0)
	_som_faisca = _criar_som("conserto_faisca.wav", -2.0)
	_som_estalo = _criar_som("conserto_faisca.wav", -18.0)
	_som_choque = _criar_som("conserto_choque.wav", 0.0)
	_som_encaixe = _criar_som("conserto_encaixe.wav", -3.0)
	_tocar(_som_zumbido)


## Ao sair da árvore, para todos os sons (o mundo continua rodando sem a máquina).
func _exit_tree() -> void:
	super()
	for filho in get_children():
		if filho is AudioStreamPlayer:
			(filho as AudioStreamPlayer).stop()
			(filho as AudioStreamPlayer).stream = null  # solta o som já (evita aviso de "leak" ao fechar o jogo)


func _criar_som(arquivo: String, volume_db: float) -> AudioStreamPlayer:
	var p := AudioStreamPlayer.new()
	p.bus = &"Efeitos"
	p.volume_db = volume_db
	var caminho := "res://assets/sons/minigames/" + arquivo
	if ResourceLoader.exists(caminho):
		p.stream = load(caminho)
	add_child(p)
	return p


## No modo --headless (testes automáticos) não existe saída de som: não tocamos nada,
## para o teste não fechar o jogo com um som ainda "pendurado" no servidor de áudio.
func _tocar(som: AudioStreamPlayer, tom := 1.0) -> void:
	if som and som.stream and DisplayServer.get_name() != "headless":
		som.pitch_scale = tom
		som.play()


## Embaralha (Fisher-Yates) uma lista de inteiros com o sorteio da máquina.
func _embaralhar_inteiros(lista: Array[int]) -> void:
	for i in range(lista.size() - 1, 0, -1):
		var j := sorteio.randi_range(0, i)
		var tmp := lista[i]
		lista[i] = lista[j]
		lista[j] = tmp


## Troca de lugar as cores dos bornes LIVRES (os já ligados ficam onde estão).
## inicio=true embaralha tudo no começo da partida.
func _embaralhar_bornes(inicio := false) -> void:
	var livres: Array[int] = []
	for j in 4:
		if inicio or not borne_ocupado[j]:
			livres.append(j)
	if livres.size() < 2:
		return
	var cores_livres: Array[int] = []
	for j in livres:
		cores_livres.append(borne_cores[j])
	var antes := cores_livres.duplicate()
	for tentativa in 8:  # garante que a ordem mudou de verdade
		_embaralhar_inteiros(cores_livres)
		if cores_livres != antes:
			break
	for k in livres.size():
		borne_cores[livres[k]] = cores_livres[k]


# =============================================================================
# Controles (teclado e mouse chamam as mesmas funções)
# =============================================================================

func _ao_processar(delta: float) -> void:
	_relogio += delta
	_bloqueio = maxf(0.0, _bloqueio - delta)
	_tremor = maxf(0.0, _tremor - delta)
	_clarao = maxf(0.0, _clarao - delta * 2.5)
	_tempo_aviso = maxf(0.0, _tempo_aviso - delta)
	if fase == "fim":
		_tempo_fim += delta
		if _tempo_fim >= TEMPO_FIM:
			finalizar(true, {})
			return
	else:
		if modo == "fios":
			if Input.is_action_just_pressed("mover_frente"):
				mover_cursor(-1)
			elif Input.is_action_just_pressed("mover_tras"):
				mover_cursor(1)
		else:
			if Input.is_action_just_pressed("mover_esquerda"):
				mover_cursor(-1)
			elif Input.is_action_just_pressed("mover_direita"):
				mover_cursor(1)
		if Input.is_action_just_pressed("minigame_acao"):
			confirmar()
	_atualizar_faiscas(delta)
	queue_redraw()


## W/S (fios) ou A/D (fusível): anda o cursor, pulando o que já está resolvido.
func mover_cursor(passo: int) -> void:
	if _bloqueio > 0.0 or fase == "fim":
		return
	match fase:
		"fio":
			cursor_fio = _proximo_livre(cursor_fio, passo, fio_ligado)
		"borne":
			cursor_borne = _proximo_livre(cursor_borne, passo, borne_ocupado)
		"tirar":
			cursor_suporte = clampi(cursor_suporte + passo, 0, 2)
		"por":
			cursor_caixa = _proximo_caixa(cursor_caixa, passo)


## ESPAÇO: pega/liga o fio, ou tira/encaixa o fusível.
func confirmar() -> void:
	if _bloqueio > 0.0 or fase == "fim":
		return
	match fase:
		"fio":
			if not fio_ligado[cursor_fio]:
				fase = "borne"
				cursor_borne = _proximo_livre(cursor_borne, 0, borne_ocupado)
				_tocar(_som_encaixe, 1.6)
		"borne":
			_ligar_fio(cursor_fio, cursor_borne)
		"tirar":
			_tirar_fusivel(cursor_suporte)
		"por":
			_por_fusivel(cursor_caixa)


## Próximo índice (0..3) não marcado em 'usados', andando 'passo' (0 = o próprio, se livre).
func _proximo_livre(atual: int, passo: int, usados: Array[bool]) -> int:
	if passo == 0:
		if not usados[atual]:
			return atual
		passo = 1
	var i := atual
	for k in 4:
		i = (i + passo + 4) % 4
		if not usados[i]:
			return i
	return atual


func _proximo_caixa(atual: int, passo: int) -> int:
	var i := atual
	for k in 3:
		i = clampi(i + passo, 0, 2)
		if caixinha[i] != 0:
			return i
	return atual


func _ligar_fio(fio: int, borne: int) -> void:
	var pos := _pos_borne(borne)
	if borne_cores[borne] == fio:
		fio_ligado[fio] = true
		borne_ocupado[borne] = true
		_tocar(_som_encaixe)
		_soltar_faiscas(pos + Vector2(-30, 0), 8, Color(0.6, 1.0, 0.7))
		if not fio_ligado.has(false):
			_concluir("FIOS LIGADOS!")
		else:
			fase = "fio"
			cursor_fio = _proximo_livre(cursor_fio, 0, fio_ligado)
	else:
		# Errou: faísca, susto e o fio volta a ficar solto.
		erros += 1
		fase = "fio"
		_bloqueio = BLOQUEIO_ERRO
		_tremor = 0.35
		_tremor_forca = 10.0
		_clarao = 0.6
		_cor_clarao = Color(1.0, 0.9, 0.6)
		_tocar(_som_faisca)
		_soltar_faiscas(pos + Vector2(-30, 0), 40, Color(1.0, 0.85, 0.4))
		_avisar("ERRADO! Fio %s não vai no borne %s." % [NOMES_CORES[fio], NOMES_CORES[borne_cores[borne]]])
		if dificuldade.embaralhar_fios:
			_embaralhar_bornes()
			_avisar("ERRADO! E os bornes trocaram de lugar...")


func _tirar_fusivel(i: int) -> void:
	var pos := Vector2(X_FUSIVEIS[i], Y_FUSIVEL)
	if suportes[i] == "queimado":
		suportes[i] = "vazio"
		suporte_vazio = i
		fase = "por"
		cursor_caixa = _proximo_caixa(cursor_caixa, 0) if caixinha[cursor_caixa] != 0 else _proximo_caixa(0, 1)
		_tocar(_som_encaixe, 0.8)
		_avisar("Fusível queimado fora. Agora pegue um novo na caixinha.")
	elif suportes[i] == "bom":
		# CHOQUE: tela treme, clarão azul e o vigia fica ~1 s sem conseguir mexer.
		_bloqueio = BLOQUEIO_CHOQUE
		_tremor = 0.7
		_tremor_forca = 18.0
		_clarao = 1.0
		_cor_clarao = Color(0.6, 0.8, 1.0)
		_tocar(_som_choque)
		_soltar_faiscas(pos, 45, Color(0.7, 0.85, 1.0))
		_avisar("CHOQUE! Esse fusível estava bom.")


func _por_fusivel(k: int) -> void:
	if suporte_vazio < 0 or caixinha[k] == 0:
		return
	var amp := caixinha[k]
	var pos := Vector2(X_FUSIVEIS[suporte_vazio], Y_FUSIVEL)
	if amp == AMPERAGEM_CERTA:
		caixinha[k] = 0
		suportes[suporte_vazio] = "novo"
		_tocar(_som_encaixe)
		_soltar_faiscas(pos + Vector2(0, -70), 10, Color(0.6, 1.0, 0.7))
		_concluir("ENERGIA RESTABELECIDA!")
	else:
		_bloqueio = BLOQUEIO_ERRO
		_tremor = 0.3
		_tremor_forca = 8.0
		_clarao = 0.5
		_cor_clarao = Color(1.0, 0.9, 0.6)
		_tocar(_som_faisca)
		_soltar_faiscas(pos, 30, Color(1.0, 0.85, 0.4))
		if amp < AMPERAGEM_CERTA:
			_avisar("%dA é fraco demais: queimou na hora! Use %dA." % [amp, AMPERAGEM_CERTA])
		else:
			_avisar("%dA é forte demais: risco de incêndio! Use %dA." % [amp, AMPERAGEM_CERTA])


func _concluir(texto: String) -> void:
	fase = "fim"
	_tempo_fim = 0.0
	_avisar(texto)
	if _som_zumbido:
		_som_zumbido.stop()


func _avisar(texto: String) -> void:
	_aviso = texto
	_tempo_aviso = 2.2


func _resultado_decidido() -> Variant:
	return [true, {}] if fase == "fim" else null


func _ao_vencer_agora() -> void:
	finalizar(true, {})


## Mouse: clique escolhe o que estiver perto (fio, borne, fusível ou caixinha).
func _gui_input(evento: InputEvent) -> void:
	if not rodando or not (evento is InputEventMouseButton):
		return
	var botao := evento as InputEventMouseButton
	if not botao.pressed or botao.button_index != MOUSE_BUTTON_LEFT:
		return
	var p: Vector2 = _vista.affine_inverse() * botao.position  # da janela para o papel 1280x720
	match fase:
		"fio", "borne":
			for i in 4:
				if not fio_ligado[i] and p.distance_to(_ponta_solta(i)) < 45.0 or \
						(not fio_ligado[i] and absf(p.y - _pos_ancora(i).y) < 30.0 and p.x < X_ANCORA + 80.0 and p.x > X_ANCORA - 40.0):
					cursor_fio = i
					fase = "fio"
					confirmar()
					return
			if fase == "borne":
				for j in 4:
					if not borne_ocupado[j] and p.distance_to(_pos_borne(j)) < 45.0:
						cursor_borne = j
						confirmar()
						return
		"tirar":
			for i in 3:
				if absf(p.x - X_FUSIVEIS[i]) < 45.0 and absf(p.y - Y_FUSIVEL) < 90.0:
					cursor_suporte = i
					confirmar()
					return
		"por":
			for k in 3:
				if caixinha[k] != 0 and p.distance_to(_pos_caixa(k)) < 50.0:
					cursor_caixa = k
					confirmar()
					return
	accept_event()


# =============================================================================
# Partículas
# =============================================================================

func _soltar_faiscas(origem: Vector2, quantidade: int, cor: Color) -> void:
	for i in quantidade:
		var f := Faisca.new()
		f.pos = origem
		var angulo := sorteio.randf_range(-PI, 0.0)  # para cima, espalhando
		f.vel = Vector2(cos(angulo), sin(angulo)) * sorteio.randf_range(120.0, 520.0)
		f.vida_max = sorteio.randf_range(0.25, 0.7)
		f.vida = f.vida_max
		f.cor = cor
		_faiscas.append(f)


func _atualizar_faiscas(delta: float) -> void:
	# Faíscas "de ambiente" no fio desencapado, de tempos em tempos.
	_proxima_faisca -= delta
	if _proxima_faisca <= 0.0 and fase != "fim":
		_proxima_faisca = sorteio.randf_range(0.6, 2.0)
		_soltar_faiscas(PONTO_FAISCA, sorteio.randi_range(5, 12), Color(1.0, 0.9, 0.55))
		_tocar(_som_estalo, sorteio.randf_range(0.9, 1.3))
	for f in _faiscas:
		f.vel.y += 900.0 * delta  # gravidade
		f.vel *= 1.0 - 1.5 * delta  # resistência do ar
		f.pos += f.vel * delta
		f.vida -= delta
	_faiscas = _faiscas.filter(func(f: Faisca) -> bool: return f.vida > 0.0)


# =============================================================================
# Geometria dos fios
# =============================================================================

func _pos_ancora(fio: int) -> Vector2:
	return Vector2(X_ANCORA, Y_PRIMEIRO + fio * ESPACO_Y)


func _pos_borne(borne: int) -> Vector2:
	return Vector2(X_BORNE, Y_PRIMEIRO + borne * ESPACO_Y)


func _pos_caixa(k: int) -> Vector2:
	return Vector2(540.0 + k * 100.0, 570.0)


## Onde fica a ponta de um fio solto (balança um pouquinho).
func _ponta_solta(fio: int) -> Vector2:
	return _pos_ancora(fio) + Vector2(95.0 + 5.0 * sin(_relogio * 1.7 + fio), 46.0 + 4.0 * cos(_relogio * 2.3 + fio * 2.0))


## Pontos de uma curva de Bézier cúbica: B(t) = (1-t)³P0 + 3(1-t)²t P1 + 3(1-t)t² P2 + t³P3.
func _bezier(p0: Vector2, p1: Vector2, p2: Vector2, p3: Vector2, n := 24) -> PackedVector2Array:
	var pts := PackedVector2Array()
	for i in n + 1:
		var t := float(i) / n
		var u := 1.0 - t
		pts.append(p0 * u * u * u + p1 * 3.0 * u * u * t + p2 * 3.0 * u * t * t + p3 * t * t * t)
	return pts


# =============================================================================
# Desenho
# =============================================================================

func _draw() -> void:
	var tamanho := size if size.x > 1.0 else get_viewport_rect().size
	draw_set_transform_matrix(Transform2D.IDENTITY)
	draw_rect(Rect2(Vector2.ZERO, tamanho), Color(0.04, 0.04, 0.05))
	var s := minf(tamanho.x / VIRTUAL.x, tamanho.y / VIRTUAL.y)
	var deslocamento := (tamanho - VIRTUAL * s) * 0.5
	if _tremor > 0.0:
		deslocamento += Vector2(sorteio.randf_range(-1, 1), sorteio.randf_range(-1, 1)) * _tremor_forca * s * minf(1.0, _tremor / 0.3)
	_vista = Transform2D(0.0, Vector2(s, s), 0.0, deslocamento)
	draw_set_transform_matrix(_vista)
	_desenhar_parede()
	_desenhar_caixa()
	if modo == "fios":
		_desenhar_fios()
	else:
		_desenhar_fusiveis()
	_desenhar_particulas()
	_desenhar_hud()
	if _clarao > 0.0:
		draw_set_transform_matrix(Transform2D.IDENTITY)
		draw_rect(Rect2(Vector2.ZERO, tamanho), Color(_cor_clarao, 0.35 * _clarao))


func _texto(fonte: Font, pos: Vector2, texto: String, tam: int, cor: Color, centralizado := false) -> void:
	var x := pos.x
	if centralizado:
		x -= fonte.get_string_size(texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam).x * 0.5
	draw_string(fonte, Vector2(x, pos.y), texto, HORIZONTAL_ALIGNMENT_LEFT, -1, tam, cor)


func _desenhar_parede() -> void:
	# Azulejo encardido da cozinha (ou parede do escritório), iluminado pela lanterna:
	# um degradê radial feito com círculos sobrepostos.
	for i in range(18, 0, -1):
		var r := 40.0 * i
		draw_circle(Vector2(640, 360), r, Color(0.16, 0.15, 0.13, 0.12))
	for x in range(0, 1281, 64):
		draw_line(Vector2(x, 0), Vector2(x, 720), Color(0, 0, 0, 0.25), 2.0)
	for y in range(0, 721, 64):
		draw_line(Vector2(0, y), Vector2(1280, y), Color(0, 0, 0, 0.25), 2.0)


func _desenhar_caixa() -> void:
	# Porta aberta (presa na dobradiça da esquerda, vista em perspectiva: um trapézio)
	var porta := PackedVector2Array([Vector2(330, 70), Vector2(190, 115), Vector2(190, 590), Vector2(330, 640)])
	draw_polygon(porta, PackedColorArray([Color(0.42, 0.47, 0.44), Color(0.25, 0.28, 0.26), Color(0.2, 0.22, 0.21), Color(0.33, 0.37, 0.35)]))
	draw_polyline(PackedVector2Array([Vector2(330, 70), Vector2(190, 115), Vector2(190, 590), Vector2(330, 640)]), Color(0.15, 0.16, 0.15), 3.0)
	# Adesivo de perigo na porta
	var tri := PackedVector2Array([Vector2(262, 250), Vector2(222, 330), Vector2(298, 322)])
	draw_colored_polygon(tri, Color(1.0, 0.82, 0.1))
	draw_polyline(PackedVector2Array([tri[0], tri[1], tri[2], tri[0]]), Color(0.1, 0.1, 0.1), 3.0)
	_texto(_fonte_titulo, Vector2(260, 318), "!", 34, Color(0.1, 0.1, 0.1), true)
	# Caixa de metal
	var corpo := PackedVector2Array([Vector2(330, 70), Vector2(950, 70), Vector2(950, 640), Vector2(330, 640)])
	draw_polygon(corpo, PackedColorArray([Color(0.46, 0.5, 0.48), Color(0.4, 0.44, 0.42), Color(0.28, 0.31, 0.3), Color(0.32, 0.35, 0.34)]))
	draw_rect(Rect2(360, 100, 560, 510), Color(0.09, 0.1, 0.11))
	draw_rect(Rect2(360, 100, 560, 510), Color(0.2, 0.22, 0.22), false, 3.0)
	for p in [Vector2(345, 85), Vector2(935, 85), Vector2(345, 625), Vector2(935, 625)]:
		draw_circle(p, 6.0, Color(0.6, 0.62, 0.6))
		draw_line(p + Vector2(-4, 0), p + Vector2(4, 0), Color(0.3, 0.3, 0.3), 2.0)
	# Placa com o nome
	var nome := "DISJUNTOR DA COZINHA" if modo == "fios" else "DISJUNTOR DO GERENTE"
	draw_rect(Rect2(470, 30, 340, 34), Color(0.85, 0.82, 0.7))
	draw_rect(Rect2(470, 30, 340, 34), Color(0.3, 0.28, 0.2), false, 2.0)
	_texto(_fonte_placa, Vector2(640, 55), nome, 22, Color(0.15, 0.12, 0.08), true)
	# Fio desencapado no canto (de onde saem as faíscas de ambiente)
	draw_polyline(_bezier(Vector2(920, 110), Vector2(900, 125), Vector2(915, 130), PONTO_FAISCA), Color(0.1, 0.1, 0.1), 7.0)
	draw_line(PONTO_FAISCA, PONTO_FAISCA + Vector2(-6, 8), Color(0.85, 0.5, 0.2), 3.0)
	var brilho := 0.3 + 0.3 * sin(_relogio * 23.0) * sin(_relogio * 7.0)
	draw_circle(PONTO_FAISCA, 10.0, Color(1.0, 0.9, 0.6, maxf(0.0, brilho)))
	# Alavanca do disjuntor (para baixo = desligado), só decoração
	var ligado := fase == "fim"
	draw_rect(Rect2(610, 112, 60, 48), Color(0.15, 0.15, 0.16))
	draw_rect(Rect2(625, 116 if ligado else 136, 30, 20), Color(0.85, 0.15, 0.15) if not ligado else Color(0.2, 0.85, 0.3))
	_texto(_fonte_pixel, Vector2(700, 140), "LIGA" if ligado else "DESL.", 10, Color(0.8, 0.8, 0.8))


func _desenhar_fios() -> void:
	# Bloco de terminais da esquerda
	draw_rect(Rect2(X_ANCORA - 40, Y_PRIMEIRO - 45, 50, ESPACO_Y * 3 + 90), Color(0.2, 0.2, 0.22))
	# Bornes da direita (com o anel colorido)
	for j in 4:
		var b := _pos_borne(j)
		var cor: Color = CORES[borne_cores[j]]
		draw_rect(Rect2(b + Vector2(-22, -30), Vector2(122, 60)), Color(0.22, 0.22, 0.24))
		draw_rect(Rect2(b + Vector2(-22, -30), Vector2(122, 60)), Color(0.4, 0.4, 0.42), false, 2.0)
		draw_circle(b, 17.0, cor)
		draw_circle(b, 10.0, Color(0.7, 0.68, 0.6))           # parafuso
		draw_line(b + Vector2(-6, -6), b + Vector2(6, 6), Color(0.35, 0.33, 0.3), 2.5)
		_texto(_fonte_tela, b + Vector2(24, 7), NOMES_CORES[borne_cores[j]], 24, cor)
		if fase == "borne" and j == cursor_borne and not borne_ocupado[j]:
			var piscar := 0.6 + 0.4 * sin(_relogio * 10.0)
			draw_rect(Rect2(b + Vector2(-30, -38), Vector2(138, 76)), Color(1.0, 1.0, 0.6, piscar), false, 3.0)
	# Fios (a ordem importa: o fio "na mão" é desenhado por último, por cima)
	var na_mao := cursor_fio if fase == "borne" else -1
	for i in 4:
		if i != na_mao:
			_desenhar_fio(i)
	if na_mao >= 0:
		_desenhar_fio(na_mao)


func _desenhar_fio(i: int) -> void:
	var a := _pos_ancora(i)
	var cor: Color = CORES[i]
	var fim: Vector2
	var c1: Vector2
	var c2: Vector2
	if fio_ligado[i]:
		fim = _pos_borne(borne_cores.find(i)) + Vector2(-14, 0)
		c1 = a + Vector2(170, 0)
		c2 = fim + Vector2(-170, 0)
	elif fase == "borne" and i == cursor_fio:
		# Na mão do vigia: a ponta vai até perto do borne escolhido
		fim = _pos_borne(cursor_borne) + Vector2(-55 + 4.0 * sin(_relogio * 9.0), 0)
		c1 = a + Vector2(150, 40)
		c2 = fim + Vector2(-140, 0)
	else:
		# Solto, pendurado (a curva "cai" com a gravidade)
		fim = _ponta_solta(i)
		c1 = a + Vector2(50, 0)
		c2 = fim + Vector2(-20, 50)
	var curva := _bezier(a, c1, c2, fim)
	var selecionado := fase == "fio" and i == cursor_fio and not fio_ligado[i]
	if selecionado:
		draw_polyline(curva, Color(1.0, 1.0, 0.7, 0.35 + 0.25 * sin(_relogio * 8.0)), 16.0)
	draw_polyline(curva, cor.darkened(0.5), 9.0)
	draw_polyline(curva, cor, 6.0)
	# Brilho do plástico (uma linha clarinha deslocada)
	var brilho := PackedVector2Array()
	for p in curva:
		brilho.append(p + Vector2(0, -1.5))
	draw_polyline(brilho, cor.lightened(0.45), 1.5)
	# Ponta de cobre (se não estiver ligada)
	if not fio_ligado[i]:
		var dir := (fim - curva[curva.size() - 3]).normalized()
		draw_line(fim, fim + dir * 12.0, Color(0.85, 0.5, 0.2), 4.0)
	# Parafuso da âncora
	draw_circle(a, 9.0, Color(0.7, 0.68, 0.6))
	draw_circle(a + Vector2(-26, 0), 7.0, cor)
	if selecionado:
		var seta := a + Vector2(-58.0 + 4.0 * sin(_relogio * 8.0), 0)  # setinha apontando o fio escolhido
		draw_colored_polygon(PackedVector2Array([seta + Vector2(-14, -10), seta + Vector2(0, 0), seta + Vector2(-14, 10)]), Color(1.0, 1.0, 0.6))


func _desenhar_fusiveis() -> void:
	for i in 3:
		var x: float = X_FUSIVEIS[i]
		# Suporte de porcelana
		draw_rect(Rect2(x - 42, Y_FUSIVEL - 95, 84, 190), Color(0.82, 0.8, 0.74))
		draw_rect(Rect2(x - 42, Y_FUSIVEL - 95, 84, 190), Color(0.5, 0.48, 0.44), false, 2.0)
		draw_rect(Rect2(x - 20, Y_FUSIVEL - 86, 40, 16), Color(0.65, 0.65, 0.68))  # presilhas
		draw_rect(Rect2(x - 20, Y_FUSIVEL + 70, 40, 16), Color(0.65, 0.65, 0.68))
		_texto(_fonte_placa, Vector2(x, Y_FUSIVEL - 104), "%dA" % AMPERAGEM_CERTA, 18, Color(0.85, 0.85, 0.8), true)
		var estado_suporte: String = suportes[i]
		if estado_suporte != "vazio":
			_desenhar_fusivel(Vector2(x, Y_FUSIVEL), true, estado_suporte == "queimado", AMPERAGEM_CERTA)
		else:
			draw_rect(Rect2(x - 12, Y_FUSIVEL - 62, 24, 124), Color(0.15, 0.14, 0.12))
		if fase == "tirar" and i == cursor_suporte:
			var piscar := 0.6 + 0.4 * sin(_relogio * 10.0)
			draw_rect(Rect2(x - 50, Y_FUSIVEL - 125, 100, 228), Color(1.0, 1.0, 0.6, piscar), false, 3.0)
		elif fase == "por" and i == suporte_vazio:
			var piscar2 := 0.5 + 0.5 * sin(_relogio * 6.0)
			draw_rect(Rect2(x - 50, Y_FUSIVEL - 125, 100, 228), Color(0.5, 1.0, 0.6, piscar2), false, 3.0)
	# Caixinha de fusíveis novos (papelão)
	draw_rect(Rect2(470, 515, 340, 95), Color(0.55, 0.4, 0.24))
	draw_rect(Rect2(470, 515, 340, 95), Color(0.35, 0.24, 0.12), false, 3.0)
	_texto(_fonte_placa, Vector2(640, 532), "FUSÍVEIS NOVOS", 14, Color(0.2, 0.12, 0.05), true)
	for k in 3:
		var c := _pos_caixa(k)
		if caixinha[k] != 0:
			_desenhar_fusivel(c, false, false, caixinha[k])
		if fase == "por" and k == cursor_caixa and caixinha[k] != 0:
			var piscar3 := 0.6 + 0.4 * sin(_relogio * 10.0)
			draw_rect(Rect2(c + Vector2(-48, -26), Vector2(96, 52)), Color(1.0, 1.0, 0.6, piscar3), false, 3.0)


## Um fusível de cartucho: tubo de vidro com tampas de metal e o filamento dentro.
## vertical=false desenha deitado (na caixinha). queimado: vidro preto e filamento partido.
func _desenhar_fusivel(c: Vector2, vertical: bool, queimado: bool, amperes: int) -> void:
	var comprimento := 120.0 if vertical else 80.0
	var largura := 30.0 if vertical else 22.0
	var eixo := Vector2(0, 1) if vertical else Vector2(1, 0)
	var lado := Vector2(1, 0) if vertical else Vector2(0, 1)
	var meio := comprimento * 0.5
	var tampa := comprimento * 0.16
	# Vidro
	var vidro := Color(0.05, 0.04, 0.04, 0.95) if queimado else Color(0.75, 0.88, 0.95, 0.45)
	var quad := PackedVector2Array([c - eixo * (meio - tampa) - lado * largura * 0.5, c + eixo * (meio - tampa) - lado * largura * 0.5,
		c + eixo * (meio - tampa) + lado * largura * 0.5, c - eixo * (meio - tampa) + lado * largura * 0.5])
	draw_colored_polygon(quad, vidro)
	# Filamento
	if queimado:
		draw_line(c - eixo * (meio - tampa), c - eixo * 6.0 + lado * 3.0, Color(0.3, 0.25, 0.2), 1.5)
		draw_line(c + eixo * (meio - tampa), c + eixo * 8.0 - lado * 2.0, Color(0.3, 0.25, 0.2), 1.5)
		draw_circle(c + lado * 4.0, 7.0, Color(0.15, 0.1, 0.08, 0.8))  # mancha de fuligem
	else:
		draw_line(c - eixo * (meio - tampa), c + eixo * (meio - tampa), Color(0.75, 0.75, 0.7), 1.5)
		draw_line(c - eixo * (meio - tampa) - lado * largura * 0.3, c + eixo * (meio - tampa) - lado * largura * 0.3, Color(1, 1, 1, 0.5), 2.0)
	# Tampas de metal
	for sinal in [-1.0, 1.0]:
		var centro_tampa: Vector2 = c + eixo * (meio - tampa * 0.5) * sinal
		var r := Rect2(centro_tampa - (eixo * tampa + lado * (largura + 4)) * 0.5, eixo * tampa + lado * (largura + 4))
		draw_rect(r.abs(), Color(0.72, 0.72, 0.74))
		draw_rect(r.abs(), Color(0.4, 0.4, 0.42), false, 1.5)
	# Etiqueta com a amperagem (só nos da caixinha; nos suportes, a placa fica em cima)
	if not vertical:
		_texto(_fonte_pixel, c + Vector2(0, largura * 0.5 + 18), "%dA" % amperes, 12, Color(1.0, 0.9, 0.4), true)


func _desenhar_particulas() -> void:
	for f in _faiscas:
		var t := f.vida / f.vida_max
		var cor := Color(1, 1, 1).lerp(f.cor, 1.0 - t)
		cor.a = clampf(t * 1.5, 0.0, 1.0)
		draw_line(f.pos, f.pos - f.vel * 0.025, cor, 2.5)


func _desenhar_hud() -> void:
	# Painel da direita: instruções
	draw_rect(Rect2(985, 120, 270, 330), Color(0.05, 0.04, 0.05, 0.9))
	draw_rect(Rect2(985, 120, 270, 330), Color(0.45, 0.41, 0.35), false, 2.0)
	var linhas: Array = []
	var objetivo := ""
	if modo == "fios":
		objetivo = "Ligue cada fio no borne da MESMA COR."
		linhas = [["W / S", "escolhe fio/borne"], ["ESPAÇO", "pega / liga"], ["ESC / E", "sai"]]
	else:
		objetivo = "Troque o fusível queimado por um novo de %dA." % AMPERAGEM_CERTA
		linhas = [["A / D", "escolhe"], ["ESPAÇO", "tira / encaixa"], ["ESC / E", "sai"]]
	_texto(_fonte_pixel, Vector2(1120, 150), "CONSERTO", 14, Color(1.0, 0.86, 0.25), true)
	draw_multiline_string(_fonte_tela, Vector2(1000, 182), objetivo, HORIZONTAL_ALIGNMENT_LEFT, 240, 26, -1, Color(0.9, 0.9, 0.9))
	var y := 290.0
	for l: Array in linhas:
		_texto(_fonte_pixel, Vector2(1000, y), l[0], 12, Color(1.0, 0.86, 0.25))
		_texto(_fonte_tela, Vector2(1000, y + 26), l[1], 26, Color(0.9, 0.9, 0.9))
		y += 52.0
	# Progresso
	var progresso := ""
	if modo == "fios":
		progresso = "FIOS: %d/4" % fio_ligado.count(true)
	else:
		progresso = "FUSÍVEL: " + ("OK" if fase == "fim" else ("TIRE O QUEIMADO" if fase == "tirar" else "PONHA UM NOVO"))
	_texto(_fonte_titulo, Vector2(640, 670), progresso, 20, Color(0.6, 1.0, 0.7), true)
	# Dica do passo atual
	var dica := ""
	match fase:
		"fio":
			dica = "Escolha um fio solto (W/S) e aperte ESPAÇO"
		"borne":
			dica = "Leve o fio %s até o borne da mesma cor" % NOMES_CORES[cursor_fio]
		"tirar":
			dica = "Qual fusível está queimado? (A/D e ESPAÇO)"
		"por":
			dica = "Escolha o fusível novo certo na caixinha (A/D e ESPAÇO)"
	_texto(_fonte_tela, Vector2(640, 700), dica + "   ·   ESC/E sai", 26, Color(0.85, 0.85, 0.85), true)
	# Aviso (erro, choque, sucesso)
	if _tempo_aviso > 0.0 or fase == "fim":
		var cor := Color(0.5, 1.0, 0.6) if fase == "fim" else Color(1.0, 0.45, 0.35)
		var caixa := Rect2(340, 300, 600, 70)
		draw_rect(caixa, Color(0.04, 0.03, 0.04, 0.92 * minf(1.0, _tempo_aviso * 3.0 + (1.0 if fase == "fim" else 0.0))))
		draw_rect(caixa, cor, false, 3.0)
		var tam := 30 if fase == "fim" else 20
		var fonte := _fonte_titulo if fase == "fim" else _fonte_tela
		if fase != "fim":
			tam = 32
		_texto(fonte, Vector2(640, 346), _aviso, tam, cor, true)
