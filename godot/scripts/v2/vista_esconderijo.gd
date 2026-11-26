class_name VistaEsconderijo
extends Control
## O que o vigia enxerga DE DENTRO do esconderijo: uma "máscara" desenhada por cima do jogo,
## com buracos por onde se vê o ambiente (e o animatrônico passando).
##   "frestas"  armário de metal: faixas horizontais da porta com vãos entre elas
##   "toalha"   debaixo da mesa: a toalha cobre quase tudo; vê-se o chão pela barra
##   "tecido"   cortina do palco / arara de figurinos: tecido dos lados, uma abertura no meio
##   "cabine"   cabine do banheiro: porta fechada, com a fresta do lado e o vão de baixo
## Embaixo, a indicação fixa "ESCONDIDO" e as teclas.

var tipo := "frestas"
var _tempo := 0.0
var _rotulo: Label

const PRETO := Color(0.0, 0.0, 0.0, 0.97)


func _ready() -> void:
	set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
	mouse_filter = Control.MOUSE_FILTER_IGNORE
	_rotulo = Label.new()
	_rotulo.text = "ESCONDIDO   ·   E: sair   ·   Alt (segurar): prender a respiração"
	_rotulo.theme_type_variation = &"RotuloHUD"
	_rotulo.add_theme_font_size_override("font_size", 22)
	_rotulo.add_theme_color_override("font_color", Color(0.75, 0.95, 0.75))
	_rotulo.add_theme_constant_override("outline_size", 5)
	_rotulo.add_theme_color_override("font_outline_color", Color.BLACK)
	_rotulo.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
	_rotulo.offset_left = -500
	_rotulo.offset_right = 500
	_rotulo.offset_top = -190
	_rotulo.offset_bottom = -160
	_rotulo.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
	_rotulo.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
	add_child(_rotulo)


func _process(delta: float) -> void:
	_tempo += delta
	queue_redraw()  # o tecido "respira" um pouquinho


func _draw() -> void:
	var t := size
	match tipo:
		"frestas":
			_frestas(t)
		"toalha":
			_toalha(t)
		"tecido":
			_tecido(t)
		"cabine":
			_cabine(t)
	_vinheta(t)


## Porta de armário: 6 frestas horizontais no meio da tela.
func _frestas(t: Vector2) -> void:
	var y := 0.0
	var faixas := [0.30, 0.055, 0.045, 0.055, 0.045, 0.055, 0.045, 0.055, 0.045, 0.055, 0.045, 0.055, 0.0]
	var abertas := 0
	for i in faixas.size():
		var h: float = t.y * float(faixas[i]) if i < faixas.size() - 1 else t.y - y
		if i % 2 == 0:
			draw_rect(Rect2(0, y, t.x, h), PRETO)
		else:
			abertas += 1
			# As frestas não vão de ponta a ponta: a porta tem as bordas.
			draw_rect(Rect2(0, y, t.x * 0.18, h), PRETO)
			draw_rect(Rect2(t.x * 0.82, y, t.x * 0.18, h), PRETO)
		y += h


## Debaixo da mesa: a toalha pendurada cobre o alto; a barra balança de leve; vê-se o chão.
func _toalha(t: Vector2) -> void:
	var barra := t.y * 0.42  # a barra da toalha levantada (vê-se o salão por baixo dela)
	var pontos := PackedVector2Array([Vector2(0, 0), Vector2(t.x, 0)])
	var n := 24
	for i in range(n, -1, -1):
		var x := t.x * i / n
		var onda := sin(i * 1.3 + _tempo * 0.8) * t.y * 0.012 + (t.y * 0.02 if i % 2 == 0 else 0.0)
		pontos.append(Vector2(x, barra + onda))
	draw_colored_polygon(pontos, Color(0.05, 0.02, 0.03, 0.97))
	# Pés da mesa e as laterais da toalha (cantos escuros)
	draw_rect(Rect2(0, 0, t.x * 0.08, t.y), PRETO)
	draw_rect(Rect2(t.x * 0.92, 0, t.x * 0.08, t.y), PRETO)
	draw_rect(Rect2(t.x * 0.2, barra, t.x * 0.025, t.y - barra), Color(0.04, 0.03, 0.03, 0.95))
	draw_rect(Rect2(t.x * 0.775, barra, t.x * 0.025, t.y - barra), Color(0.04, 0.03, 0.03, 0.95))


## Cortina ou roupas: tecido dos dois lados com dobras, abertura vertical no meio.
func _tecido(t: Vector2) -> void:
	var meio := t.x * 0.5 + sin(_tempo * 0.6) * t.x * 0.01
	var abertura := t.x * 0.2
	for lado in [-1, 1]:
		var borda: float = meio + lado * abertura * 0.5
		var pontos := PackedVector2Array()
		var fora: float = 0.0 if lado < 0 else t.x
		pontos.append(Vector2(fora, 0))
		var n := 16
		for i in n + 1:
			var y := t.y * i / n
			pontos.append(Vector2(borda + lado * sin(i * 0.9 + _tempo) * t.x * 0.012, y))
		pontos.append(Vector2(fora, t.y))
		draw_colored_polygon(pontos, Color(0.08, 0.02, 0.03, 0.97))
		# Dobras do tecido (linhas mais escuras)
		for k in 5:
			var x: float = lerpf(fora, borda, (k + 1) / 6.0)
			draw_line(Vector2(x, 0), Vector2(x + lado * t.x * 0.01, t.y), Color(0, 0, 0, 0.6), 6.0)


## Cabine: a porta fechada; dá para espiar pela fresta da dobradiça e pelo vão de baixo.
func _cabine(t: Vector2) -> void:
	var vao := t.y * 0.78
	draw_rect(Rect2(0, 0, t.x * 0.47, vao), Color(0.06, 0.06, 0.07, 0.98))
	draw_rect(Rect2(t.x * 0.53, 0, t.x * 0.47, vao), Color(0.06, 0.06, 0.07, 0.98))
	draw_rect(Rect2(t.x * 0.47, 0, t.x * 0.06, t.y * 0.06), PRETO)


func _vinheta(t: Vector2) -> void:
	# Bordas escurecidas: aperto e respiração presa
	var largura := t.x * 0.06
	for i in 6:
		var a := 0.12 * (6 - i) / 6.0
		var m := largura * i / 6.0
		draw_rect(Rect2(m, m, t.x - 2 * m, t.y - 2 * m), Color(0, 0, 0, a), false, largura / 6.0)
