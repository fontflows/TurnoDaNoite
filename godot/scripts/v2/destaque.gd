class_name Destaque
extends Sprite3D
## "Isso é interativo": um brilho suave que pulsa em cima de cada coisa que dá para usar ou pegar.
##   - Aparece só a uma distância razoável (não polui a tela) e some quando já foi usado.
##   - Fica bem mais forte quando a LANTERNA passa por cima (o reflexo chama o olho).
##   - Itens-chave usam cor quente e brilho maior; os opcionais, cor fria e mais fraca.
## Uso: Destaque.colocar(no_3d, cor, forca)

## Até que distância (m) o brilho aparece (multiplicado pela força).
const DISTANCIA := 11.0

var alvo: Node3D
var cor := Color.WHITE
var forca := 1.0
## Opcional: devolve false quando o objeto não precisa mais de destaque (ex.: disjuntor já ligado).
var ainda_util := Callable()
var _tempo := 0.0
var _jogador: Node3D

static var _textura: Texture2D


static func colocar(no: Node3D, cor_destaque: Color, forca_destaque := 1.0, condicao := Callable()) -> Destaque:
	if no == null or not is_instance_valid(no) or no.has_node("Destaque"):
		return null
	var d := Destaque.new()
	d.name = "Destaque"
	d.alvo = no
	d.cor = cor_destaque
	d.forca = forca_destaque
	d.ainda_util = condicao
	no.add_child(d)
	return d


static func _textura_brilho() -> Texture2D:
	if _textura == null:
		var g := Gradient.new()
		g.set_color(0, Color(1, 1, 1, 1))
		g.set_color(1, Color(1, 1, 1, 0))
		g.add_point(0.25, Color(1, 1, 1, 0.55))
		var t := GradientTexture2D.new()
		t.gradient = g
		t.fill = GradientTexture2D.FILL_RADIAL
		t.fill_from = Vector2(0.5, 0.5)
		t.fill_to = Vector2(1.0, 0.5)
		t.width = 64
		t.height = 64
		_textura = t
	return _textura


func _ready() -> void:
	texture = _textura_brilho()
	billboard = BaseMaterial3D.BILLBOARD_ENABLED
	shaded = false
	transparent = true
	no_depth_test = false
	alpha_cut = SpriteBase3D.ALPHA_CUT_DISABLED
	pixel_size = 0.004 * (0.7 + 0.3 * forca)
	modulate = Color(cor, 0.0)
	render_priority = 1
	# Em cima do objeto (no meio da caixa dele) e um pouco para fora.
	var altura := 0.4
	var malha := alvo as VisualInstance3D
	if malha:
		var aabb := malha.get_aabb()
		altura = clampf(aabb.get_center().y, 0.15, 1.6)
	position = Vector3(0, altura, 0)
	_tempo = randf() * TAU


func _process(delta: float) -> void:
	_tempo += delta
	if _jogador == null or not is_instance_valid(_jogador):
		_jogador = get_tree().get_first_node_in_group("jogador")
		if _jogador == null:
			return
	# Some quando o objeto deixou de ser interativo (item pego, área desligada...).
	if not _ainda_interativo():
		queue_free()
		return
	var d := global_position.distance_to(_jogador.global_position)
	var alcance := DISTANCIA * (0.6 + 0.4 * forca)
	var alfa := clampf(1.0 - d / alcance, 0.0, 1.0)
	if alfa > 0.0 and _jogador.has_method("lanterna_ilumina") and _jogador.lanterna_ilumina(global_position):
		alfa = minf(alfa * 2.2 + 0.2, 1.0)  # reflexo da lanterna
	var pulso := 0.65 + 0.35 * sin(_tempo * 3.0)
	modulate = Color(cor, alfa * pulso * (0.45 + 0.45 * forca))


func _ainda_interativo() -> bool:
	if not is_instance_valid(alvo):
		return false
	if ainda_util.is_valid():
		return ainda_util.call()
	for f in alvo.get_children():
		if f is Area3D and f.is_in_group("interagivel"):
			return true
	return alvo.is_in_group("interagivel") or alvo.is_in_group("ficha") or alvo.is_in_group("pilha")
