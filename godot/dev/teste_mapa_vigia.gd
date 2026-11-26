extends Node
## FERRAMENTA DE DESENVOLVIMENTO — não entra no build.
## Abre a tela do mapa do vigia (MapaVigia) sozinha, com os dados de exemplo.
##
## Sem argumentos (F6 no editor): só abre o mapa para olhar. M ou ESC fecha/abre,
## 1, 2 e 3 trocam a marcação (Fácil, Normal, Pesadelo).
## Com "-- --prints": tira prints em várias marcações e resoluções, salva em
## docs/progresso/imagens/ (com o .json ao lado) e fecha sozinho. Precisa de janela:
##   godot --path . res://dev/teste_mapa_vigia.tscn --quit-after 3000 -- --prints

const FASE := "V2.9"
# [marcação, largura, altura, nome do arquivo, legenda]
const VARIACOES := [
	[0, 1280, 720, "v29_mapa_facil_1280x720", "V2.9: mapa (M) no Fácil — ponto exato do objetivo com bilhete, jogo pausado (1280×720)"],
	[1, 1280, 720, "v29_mapa_normal_1280x720", "V2.9: mapa (M) no Normal — só o cômodo do objetivo destacado (1280×720)"],
	[2, 1280, 720, "v29_mapa_pesadelo_1280x720", "V2.9: mapa (M) no Pesadelo — sem marcação, só a planta e o vigia (1280×720)"],
	[0, 1920, 1080, "v29_mapa_facil_1920x1080", "V2.9: mapa (M) no Fácil em 1920×1080"],
	[1, 1024, 768, "v29_mapa_normal_1024x768", "V2.9: mapa (M) no Normal em 1024×768 (tela 4:3)"],
]

var _mapa: MapaVigia
var _carimbo := ""


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	_mapa = MapaVigia.new()
	add_child(_mapa)
	if "--prints" in OS.get_cmdline_user_args():
		_tirar_prints()
	else:
		_mapa.abrir.call_deferred()


func _unhandled_input(evento: InputEvent) -> void:
	if evento is InputEventKey and evento.pressed and not evento.echo:
		var tecla := (evento as InputEventKey).keycode
		if tecla >= KEY_1 and tecla <= KEY_3:
			_mapa.fechar()
			_mapa.marcacao_exemplo = tecla - KEY_1
			_mapa.abrir()


func _tirar_prints() -> void:
	var t := Time.get_datetime_dict_from_system()
	_carimbo = "%04d-%02d-%02d_%02d%02d" % [t.year, t.month, t.day, t.hour, t.minute]
	for v: Array in VARIACOES:
		get_window().size = Vector2i(v[1], v[2])
		_mapa.fechar()
		_mapa.marcacao_exemplo = v[0]
		await _esperar(6)
		_mapa.abrir()
		await get_tree().create_timer(0.75).timeout  # deixa o fade terminar e o layout assentar
		# Espera um pouco mais, sorteado, para não cair sempre no mesmo instante da
		# "tremida" do filtro VHS (que depende do relógio).
		await get_tree().create_timer(randf_range(0.0, 0.4)).timeout
		await _esperar(2)
		_salvar(v[3], v[4])
	_mapa.fechar()
	get_tree().quit()


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
		"brilho": snappedf(_brilho_medio(imagem), 0.1),
	}
	var arq := FileAccess.open(pasta.path_join(base + ".json"), FileAccess.WRITE)
	arq.store_string(JSON.stringify(dados, "  "))
	arq.close()
	print("[teste_mapa_vigia] ", base, ".png  (", imagem.get_width(), "x", imagem.get_height(), ")")


## Brilho médio de 0 a 100 (mesma conta de dev/captura.gd), 1 a cada 4 pixels.
static func _brilho_medio(imagem: Image) -> float:
	var soma := 0.0
	var n := 0
	for y in range(0, imagem.get_height(), 4):
		for x in range(0, imagem.get_width(), 4):
			var c := imagem.get_pixel(x, y)
			soma += 0.2126 * c.r + 0.7152 * c.g + 0.0722 * c.b
			n += 1
	return 100.0 * soma / maxf(n, 1)
