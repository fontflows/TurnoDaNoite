extends Node
## FERRAMENTA DE DESENVOLVIMENTO: abre a GARRA e o CONSERTO numa janela, monta uma
## situação interessante de cada um, salva prints em docs/progresso/imagens/ (com um
## .json de legenda ao lado, no mesmo formato de dev/captura.gd) e fecha sozinho.
##
## Rodar SEM --headless (precisa desenhar de verdade), na pasta godot/:
##   godot --path . res://dev/captura_garra_conserto.tscn --quit-after 3000

const Captura := preload("res://dev/captura.gd")
const PASSO := 1.0 / 60.0

var _carimbo := ""
var _camada: CanvasLayer


func _ready() -> void:
	var t := Time.get_datetime_dict_from_system()
	_carimbo = "%04d-%02d-%02d_%02d%02d" % [t.year, t.month, t.day, t.hour, t.minute]
	_camada = CanvasLayer.new()
	_camada.layer = 20
	add_child(_camada)
	var normal: Dificuldade = load("res://assets/dificuldade/normal.tres")

	# 1) Garra mirando na cápsula
	var g: MinigameGarra = _abrir("res://cenas/minigames/garra.tscn", normal, {})
	g.sorteio.seed = 3
	var c := g.capsula()
	g.garra.x = c.pos.x + 0.03
	g.garra.z = c.pos.z
	_avancar(g, 5.0)
	await _salvar("v25_garra", "V2.5: minigame GARRA — mirando na cápsula da chave do gerente (Normal)")
	# 2) Garra levando a cápsula até a saída
	g.descer()
	var limite := 0
	while g.estado != "fechando" and limite < 2000:
		_avancar(g, PASSO)
		limite += 1
	g._vai_segurar = true  # para a foto: desta vez a garra segura
	g._vai_manter = true
	while g.estado != "levando" and limite < 4000:
		_avancar(g, PASSO)
		limite += 1
	_avancar(g, 0.7)
	await _salvar("v25_garra_levando", "V2.5: GARRA levando o prêmio para a saída (ela balança)")
	# 3) Resultado
	limite = 0
	while g.estado != "resultado" and limite < 2000:
		_avancar(g, PASSO)
		limite += 1
	_avancar(g, 0.3)
	await _salvar("v25_garra_resultado", "V2.5: GARRA — mensagem de resultado")
	g.cancelar()

	# 4) Conserto: fios (um ligado, outro na mão)
	var f: MinigameConserto = _abrir("res://cenas/minigames/conserto.tscn", normal, {"modo": "fios"})
	f.sorteio.seed = 5
	f.cursor_fio = 0
	f.confirmar()
	f.cursor_borne = f.borne_cores.find(0)
	f.confirmar()
	f.cursor_fio = 2
	f.confirmar()
	f.cursor_borne = (f.borne_cores.find(2) + 1) % 4
	if f.borne_ocupado[f.cursor_borne]:
		f.cursor_borne = (f.cursor_borne + 1) % 4
	_avancar(f, 1.3)
	f._soltar_faiscas(Vector2(905, 140), 14, Color(1.0, 0.9, 0.55))
	_avancar(f, 0.08)
	await _salvar("v25_conserto", "V2.5: CONSERTO DO DISJUNTOR (cozinha) — ligar os fios nas cores certas")
	f.cancelar()

	# 5) Conserto: fusível
	var u: MinigameConserto = _abrir("res://cenas/minigames/conserto.tscn", normal, {"modo": "fusivel"})
	u.cursor_suporte = u.suportes.find("queimado")
	_avancar(u, 1.0)
	await _salvar("v25_conserto_fusivel", "V2.5: CONSERTO DO DISJUNTOR (gerente) — achar e trocar o fusível queimado")
	u.cancelar()
	await get_tree().process_frame
	get_tree().quit()


func _abrir(cena: String, dif: Dificuldade, dados: Dictionary) -> Minigame:
	var m: Minigame = load(cena).instantiate()
	_camada.add_child(m)
	m.iniciar(dif, dados)
	m.set_process(false)  # a captura avança o tempo na mão
	return m


func _avancar(m: Minigame, segundos: float) -> void:
	var t := 0.0
	while t < segundos:
		m._ao_processar(PASSO)
		t += PASSO


func _salvar(nome: String, legenda: String) -> void:
	for i in 4:
		await RenderingServer.frame_post_draw
	var pasta := ProjectSettings.globalize_path("res://").path_join("../docs/progresso/imagens").simplify_path()
	DirAccess.make_dir_recursive_absolute(pasta)
	var base := "%s_%s" % [_carimbo, nome]
	var imagem := get_viewport().get_texture().get_image()
	imagem.save_png(pasta.path_join(base + ".png"))
	var t := Time.get_datetime_dict_from_system()
	var dados := {
		"arquivo": base + ".png",
		"legenda": legenda,
		"fase": "V2.5",
		"horario": "%04d-%02d-%02d %02d:%02d:%02d" % [t.year, t.month, t.day, t.hour, t.minute, t.second],
		"brilho": snappedf(Captura.brilho_medio(imagem), 0.1),
	}
	var arq := FileAccess.open(pasta.path_join(base + ".json"), FileAccess.WRITE)
	arq.store_string(JSON.stringify(dados, "  "))
	arq.close()
	print("[captura] ", base, ".png")
