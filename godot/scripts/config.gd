extends Node
## Autoload "Config": guarda as opções do jogador no arquivo user://config.cfg,
## para valerem da próxima vez que o jogo abrir. Também cuida da tecla F11 (tela cheia)
## e manda cada som para o "barramento" certo (Música, Efeitos ou Vozes).

signal mudou()

const ARQUIVO := "user://config.cfg"

enum ModoJanela { JANELA, TELA_CHEIA, SEM_BORDA }
enum Qualidade { BAIXA, MEDIA, ALTA }
enum Nivel { FACIL, NORMAL, PESADELO }

## Limite do brilho (gamma). Maior que isso estragaria o escuro, que é o coração do jogo.
const BRILHO_MAXIMO := 1.25
const BRILHO_MINIMO := 0.7
const LIMITES_FPS := [0, 30, 60, 120, 144]  # 0 = sem limite

# --- Vídeo ---
var modo_janela := ModoJanela.JANELA
var vsync := true
var limite_fps := 0
## Escala da resolução 3D (1.0 = nativa; 0.5 = metade, bem mais leve).
var escala_render := 1.0
var qualidade := Qualidade.ALTA
## Campo de visão da câmera do vigia, em graus.
var fov := 75.0
## Brilho (gamma). 1.0 é o normal.
var brilho := 1.0
var vhs_ativo := true
var vhs_intensidade := 0.6

# --- Áudio (0 a 1) ---
var volume_geral := 0.8
var volume_musica := 0.8
var volume_efeitos := 1.0
var volume_vozes := 1.0

# --- Controles ---
## Sensibilidade do mouse. 1.0 é o normal; 2.0 gira o dobro.
var sensibilidade := 1.0
var inverter_y := false
## Painel fixo com o objetivo atual no canto da tela (V2.2).
var mostrar_objetivo := true

# --- Jogo ---
## Última dificuldade escolhida (o menu já abre com ela marcada).
var dificuldade := Nivel.NORMAL


func _ready() -> void:
	process_mode = Node.PROCESS_MODE_ALWAYS
	carregar()
	aplicar()
	# Todo som novo que aparecer no jogo vai para o barramento certo (ver _ao_adicionar_no).
	get_tree().node_added.connect(_ao_adicionar_no)


func _input(evento: InputEvent) -> void:
	if evento.is_action_pressed("tela_cheia"):
		modo_janela = ModoJanela.JANELA if modo_janela != ModoJanela.JANELA else ModoJanela.TELA_CHEIA
		aplicar()
		salvar()
		get_viewport().set_input_as_handled()


func carregar() -> void:
	var cfg := ConfigFile.new()
	if cfg.load(ARQUIVO) != OK:
		return  # primeira vez: fica com os valores padrão acima
	for secao in cfg.get_sections():
		for chave in cfg.get_section_keys(secao):
			if chave in self:
				set(chave, cfg.get_value(secao, chave))
	brilho = clampf(brilho, BRILHO_MINIMO, BRILHO_MAXIMO)


func salvar() -> void:
	var cfg := ConfigFile.new()
	var secoes := {
		"video": ["modo_janela", "vsync", "limite_fps", "escala_render", "qualidade", "fov", "brilho", "vhs_ativo", "vhs_intensidade"],
		"audio": ["volume_geral", "volume_musica", "volume_efeitos", "volume_vozes"],
		"controles": ["sensibilidade", "inverter_y", "mostrar_objetivo"],
		"jogo": ["dificuldade"],
	}
	for secao in secoes:
		for chave in secoes[secao]:
			cfg.set_value(secao, chave, get(chave))
	cfg.save(ARQUIVO)


## Aplica tudo o que não depende da cena (janela, FPS, volumes). Brilho, VHS e
## qualidade gráfica são lidos por quem cuida deles, ao receber o sinal "mudou".
func aplicar() -> void:
	brilho = clampf(brilho, BRILHO_MINIMO, BRILHO_MAXIMO)
	var janela := get_window()
	if not DisplayServer.get_name() == "headless":
		# Só mexe na janela se o modo MUDOU: reaplicar (ex.: ao mexer no volume) tirava o jogo
		# da tela cheia no Windows, porque mudar "borderless" numa janela cheia a devolve ao modo janela.
		var desejado: Window.Mode = {ModoJanela.JANELA: Window.MODE_WINDOWED, ModoJanela.TELA_CHEIA: Window.MODE_EXCLUSIVE_FULLSCREEN,
			ModoJanela.SEM_BORDA: Window.MODE_FULLSCREEN}.get(modo_janela, Window.MODE_WINDOWED)
		# Em "Janela", a janela maximizada (botão □ ou clique duplo na barra) também vale: não encolhe.
		var ja_esta_certo := janela.mode == desejado or (desejado == Window.MODE_WINDOWED
			and janela.mode in [Window.MODE_MAXIMIZED, Window.MODE_MINIMIZED])
		if not ja_esta_certo:
			if desejado == Window.MODE_WINDOWED and janela.borderless:
				janela.borderless = false
			janela.mode = desejado  # SEM_BORDA = tela cheia "sem borda" (troca de janela mais rápida)
		DisplayServer.window_set_vsync_mode(DisplayServer.VSYNC_ENABLED if vsync else DisplayServer.VSYNC_DISABLED)
	Engine.max_fps = limite_fps
	janela.scaling_3d_scale = clampf(escala_render, 0.5, 1.0)
	QualidadeGrafica.aplicar_viewport(janela, qualidade)

	_volume("Master", volume_geral)
	_volume("Musica", volume_musica)
	_volume("Efeitos", volume_efeitos)
	_volume("Vozes", volume_vozes)
	for amb in get_tree().root.find_children("*", "WorldEnvironment", true, false):
		QualidadeGrafica.aplicar_ambiente(amb.environment, qualidade)
	mudou.emit()


func _volume(barramento: String, valor: float) -> void:
	var i := AudioServer.get_bus_index(barramento)
	if i < 0:
		return
	AudioServer.set_bus_volume_db(i, linear_to_db(maxf(valor, 0.0001)))
	AudioServer.set_bus_mute(i, valor <= 0.001)


## Sons novos vão para "Efeitos", a não ser que estejam no grupo "som_musica" ou "som_voz".
## Assim ninguém precisa lembrar de escolher o barramento em cada nó de som.
func _ao_adicionar_no(no: Node) -> void:
	if no is WorldEnvironment:
		# Ambiente novo (menu, mundo...): aplica o preset de qualidade quando ele estiver pronto.
		no.ready.connect(func(): QualidadeGrafica.aplicar_ambiente(no.environment, qualidade), CONNECT_ONE_SHOT)
		return
	if not (no is AudioStreamPlayer or no is AudioStreamPlayer2D or no is AudioStreamPlayer3D):
		return
	if no.bus != &"Master":
		return  # alguém já escolheu um barramento de propósito
	if no.is_in_group("som_musica"):
		no.bus = &"Musica"
	elif no.is_in_group("som_voz"):
		no.bus = &"Vozes"
	else:
		no.bus = &"Efeitos"
