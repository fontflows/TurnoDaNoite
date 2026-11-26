extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Fotografa DE FRENTE cada arte do mapa (planos Arte__<nome>) com luz de depuração,
## para conferir de olho se todas aparecem (página de progresso, AJUSTES V2.2 §3.1).
##
## Uso (na pasta godot/; SEM --headless, porque precisa desenhar a tela):
##   godot --path . res://dev/captura_artes.tscn
##   godot --path . res://dev/captura_artes.tscn -- textos          (também os textos 3D)
##   godot --path . res://dev/captura_artes.tscn -- so=cartaz        (só os nomes com "cartaz")
##   godot --path . res://dev/captura_artes.tscn -- malha=Placa_Saida (qualquer malha com esse nome)
## Grava docs/progresso/imagens/AAAA-MM-DD_HHMM_v29_arte_<nome>.png (+ .json da legenda).

const UTIL := preload("res://dev/artes_util.gd")
const CENA := "res://cenas/mundo_v2.tscn"
const FASE := "V2.9"
const FOV := 50.0

var _mundo: Node3D
var _camera: Camera3D
var _luz: DirectionalLight3D
var _carimbo := ""


func _ready() -> void:
	var t := Time.get_datetime_dict_from_system()
	_carimbo = "%04d-%02d-%02d_%02d%02d" % [t.year, t.month, t.day, t.hour, t.minute]
	var com_textos := OS.get_cmdline_user_args().has("textos")
	var filtro := ""
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("so="):
			filtro = arg.trim_prefix("so=")
	Jogo.modo_captura = true
	FiltroVHS.visible = false  # a arte crua, sem o chiado de VHS por cima
	_mundo = load(CENA).instantiate()
	add_child(_mundo)
	var jogador := get_tree().get_first_node_in_group("jogador")
	if jogador:
		jogador.process_mode = Node.PROCESS_MODE_DISABLED
	var hud := _mundo.get_node_or_null("HUD") as CanvasLayer
	if hud:
		hud.visible = false
	# Animatrônicos fora da frente das fotos.
	for a in get_tree().get_nodes_in_group("animatronico"):
		(a as Node3D).visible = false
	# Luz de depuração: ambiente claro, sem névoa, e uma luz direcional vinda da câmera.
	var ambiente := _mundo.get_node("Ambiente") as WorldEnvironment
	var amb := ambiente.environment.duplicate() as Environment
	amb.fog_enabled = false
	amb.volumetric_fog_enabled = false
	amb.ambient_light_source = Environment.AMBIENT_SOURCE_COLOR
	amb.ambient_light_color = Color(1, 1, 1)
	amb.ambient_light_energy = 0.75
	amb.background_color = Color(0.08, 0.08, 0.1)
	ambiente.environment = amb
	_luz = DirectionalLight3D.new()
	_luz.light_energy = 0.8
	add_child(_luz)
	_camera = Camera3D.new()
	_camera.fov = FOV
	_camera.near = 0.02
	_camera.far = 60.0
	add_child(_camera)
	_camera.current = true

	var pecas := UTIL.listar(_mundo.get_node("Navegacao/Cenario"))
	for arg in OS.get_cmdline_user_args():
		if arg.begins_with("malha="):
			# Depuração: fotografa qualquer malha pelo nome (mesmo que não seja arte nem texto).
			var procura := arg.trim_prefix("malha=")
			for no in _mundo.find_children("*" + procura + "*", "MeshInstance3D", true, false):
				pecas.append({"no": no, "tipo": "texto", "nome": String(no.name), "texto": String(no.name)})
			com_textos = true
			filtro = procura
	await _esperar_artes(pecas)
	var n := 0
	for p in pecas:
		if p["tipo"] == "texto" and not com_textos:
			continue
		if filtro != "" and not String(p["nome"]).to_lower().contains(filtro.to_lower()):
			continue
		await _fotografar(p)
		n += 1
	print("[captura_artes] concluída: %d imagens" % n)
	get_tree().quit()


## As artes são desenhadas de forma assíncrona (ArteExterna): espera todas ficarem prontas.
func _esperar_artes(pecas: Array[Dictionary]) -> void:
	for i in 600:
		var faltam := 0
		for p in pecas:
			if p["tipo"] != "arte":
				continue
			var m := (p["no"] as MeshInstance3D).material_override as ShaderMaterial
			if m == null or m.get_shader_parameter("arte") == null:
				faltam += 1
		if faltam == 0:
			break
		await RenderingServer.frame_post_draw
	for i in 10:
		await RenderingServer.frame_post_draw


func _fotografar(p: Dictionary) -> void:
	var m := p["no"] as MeshInstance3D
	var g := UTIL.geometria(m)
	var centro: Vector3 = g["centro"]
	var normal: Vector3 = g["normal"]
	var w: float = g["largura"]
	var h: float = g["altura"]
	# Distância para a peça inteira caber na foto (com folga de 30%).
	var tg := tan(deg_to_rad(FOV) / 2.0)
	var aspecto := float(get_viewport().get_visible_rect().size.x) / float(get_viewport().get_visible_rect().size.y)
	var dist := maxf((h / 2.0) / tg, (w / 2.0) / (tg * aspecto)) * 1.3 + 0.08
	dist = maxf(dist, 0.25)
	_camera.global_position = centro + normal * dist
	var cima: Vector3 = g["cima"]
	_camera.look_at(centro, cima)
	_luz.global_basis = _camera.global_basis
	await _esperar(6)
	var nome := UTIL.nome_curto(String(p["nome"]))
	var legenda := "V2.9: arte %s vista de frente (luz de depuração)" % String(p["nome"]).trim_prefix("Arte__")
	if p["tipo"] == "texto":
		nome = "texto_" + nome
		legenda = "V2.9: texto 3D \"%s\" (%s) visto de frente" % [String(p["texto"]).replace("\n", " / "), p["nome"]]
	_salvar("v29_arte_" + nome, legenda)


func _esperar(quadros: int) -> void:
	for i in quadros:
		await RenderingServer.frame_post_draw


func _salvar(nome: String, legenda: String) -> void:
	var pasta := ProjectSettings.globalize_path("res://").path_join("../docs/progresso/imagens").simplify_path()
	DirAccess.make_dir_recursive_absolute(pasta)
	var base := "%s_%s" % [_carimbo, nome]
	var imagem := get_viewport().get_texture().get_image()
	imagem.save_png(pasta.path_join(base + ".png"))
	var t := Time.get_datetime_dict_from_system()
	var dados := {
		"arquivo": base + ".png",
		"legenda": legenda,
		"fase": FASE,
		"horario": "%04d-%02d-%02d %02d:%02d:%02d" % [t.year, t.month, t.day, t.hour, t.minute, t.second],
	}
	var arq := FileAccess.open(pasta.path_join(base + ".json"), FileAccess.WRITE)
	arq.store_string(JSON.stringify(dados, "  "))
	arq.close()
	print("[captura_artes] ", base, ".png")
