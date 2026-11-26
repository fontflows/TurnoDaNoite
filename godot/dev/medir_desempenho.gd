extends Node
## FERRAMENTA DE DESENVOLVIMENTO: mede o FPS do mapa da V2 nas qualidades Alta e Baixa.
## Precisa de janela (NÃO usar --headless). Sem vsync e sem limite, de 3 pontos pesados do mapa.
## Grava em docs/progresso/relatorio_desempenho.txt sem mexer nas opções reais do jogador.
## Rodar: godot --path godot res://dev/medir_desempenho.tscn

## Pontos de vista (planta x, z, olhar para x, z): salão com palco, fliperama cheio de telas, corredor longo.
const PONTOS := [
	["Salão e palco", 27.0, 14.0, 27.0, 2.0],
	["Fliperama", 23.0, 31.0, 23.0, 21.0],
	["Corredor principal", 2.0, 17.5, 58.0, 17.5],
]
const SEGUNDOS_POR_PONTO := 4.0

var _linhas: Array[String] = []


func _ready() -> void:
	var qualidade_original: int = Config.qualidade
	var vsync_original := DisplayServer.window_get_vsync_mode()
	DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = 0
	Jogo.modo_captura = true
	var t := Time.get_datetime_dict_from_system()
	_linhas.append("DESEMPENHO — mapa V2 (%s, %s, %dx%d)" % [RenderingServer.get_current_rendering_method(),
		RenderingServer.get_video_adapter_name(), get_viewport().size.x, get_viewport().size.y])
	_linhas.append("Medido em %02d/%02d/%04d %02d:%02d, sem vsync e sem limite de FPS." % [t.day, t.month, t.year, t.hour, t.minute])
	_linhas.append("")
	for nivel in [Config.Qualidade.ALTA, Config.Qualidade.BAIXA]:
		Config.qualidade = nivel
		var mundo: Node3D = load("res://cenas/mundo_v2.tscn").instantiate()
		add_child(mundo)
		Config.aplicar()
		# Config.aplicar() põe de volta o vsync e o limite de FPS do jogador: desliga só para medir.
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_DISABLED)
		Engine.max_fps = 0
		for i in 60:
			await get_tree().process_frame
		var jogador: CharacterBody3D = mundo.get_node("Jogador")
		jogador.set_physics_process(false)
		_linhas.append("Qualidade %s:" % ["Baixa", "Média", "Alta"][nivel])
		for p in PONTOS:
			jogador.global_position = PlantaV2.mundo(p[1], p[2])
			var d := PlantaV2.mundo(p[3], p[4]) - jogador.global_position
			jogador.rotation.y = atan2(-d.x, -d.z)
			jogador.lanterna_ligada = true
			jogador._seguir_lanterna(1.0)
			for i in 30:
				await get_tree().process_frame
			var quadros := 0
			var pior := 0.0
			var inicio := Time.get_ticks_usec()
			var anterior := inicio
			while Time.get_ticks_usec() - inicio < SEGUNDOS_POR_PONTO * 1_000_000:
				await get_tree().process_frame
				var agora := Time.get_ticks_usec()
				pior = maxf(pior, (agora - anterior) / 1000.0)
				anterior = agora
				quadros += 1
			var fps := quadros / ((Time.get_ticks_usec() - inicio) / 1_000_000.0)
			_linhas.append("  %-20s %6.0f FPS médio · pior quadro %5.1f ms" % [p[0], fps, pior])
		mundo.queue_free()
		await get_tree().process_frame
		_linhas.append("")
	Config.qualidade = qualidade_original
	Config.aplicar()  # volta tudo como o jogador deixou (qualidade, vsync, limite de FPS)
	DisplayServer.window_set_vsync_mode(vsync_original)
	var arq := FileAccess.open(ProjectSettings.globalize_path("res://").path_join("../docs/progresso/relatorio_desempenho.txt"), FileAccess.WRITE)
	arq.store_string("\n".join(_linhas) + "\n")
	arq.close()
	print("\n".join(_linhas))
	get_tree().quit()
