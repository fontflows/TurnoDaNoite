class_name ProgressaoV2
extends Node
## Liga a CADEIA DE PROGRESSÃO do mapa da V2 (docs/PLANO_V2.md §5) nos modelos que vêm do Blender:
##   portas especiais, alicate, fichas, pistas da senha, teclado da sala elétrica,
##   máquinas do fliperama (garra e TITO KART), gerador, porta de aço, dutos e esconderijos,
##   cacos de vidro (barulho) e latas para arremessar (G).
##
## O montador do mundo cria este nó depois de montar luzes e disjuntores.
## Tudo é achado pelo NOME do objeto no .glb; mudou no Blender, muda aqui sozinho.

const PASTA_MINIGAMES := "res://cenas/minigames/"
const MINIGAME_KART_RESERVA := "space_pizza"

## Saídas de duto que o vigia alcança (grade baixa na parede): ponto da planta onde ele fica em pé
## e para onde olha ao sair (graus; 0 = olhando para o norte da planta, que é -Z no Godot).
const SAIDAS_DUTO := {
	"Oficina": {"x": 11.0, "z": 15.2, "olhar": 0.0, "titulo": "Oficina"},
	"Festa_Piratas": {"x": 42.0, "z": 28.3, "olhar": 180.0, "titulo": "Sala de festa dos Piratas"},
	"Copa": {"x": 53.0, "z": 44.2, "olhar": 0.0, "titulo": "Copa dos funcionários"},
}
## Segundos rastejando por metro de duto.
const SEGUNDOS_POR_METRO_DUTO := 0.12


## Cacos de vidro no chão (planta x, z): pisar sem agachar faz barulho.
const CACOS := [[30.0, 17.2], [9.0, 17.8], [33.5, 36.0], [45.5, 30.5], [20.0, 36.5], [52.0, 17.6], [46.0, 4.0]]
## Latas que dá para pegar e jogar (G) para distrair os animatrônicos.
const LATAS := [[16.5, 10.0], [27.0, 22.0], [33.6, 24.0], [45.0, 40.0], [8.0, 25.0], [50.0, 38.5]]

var ui: UIV2
var montador: Node
var cenario: Node
var _camada_minigame: CanvasLayer
var _minigame: Minigame
var _posicao_minigame := Vector3.ZERO
var _tempo_ruido_minigame := 0.0
var _portas := {}  # id -> PortaV2
var _candidatos_ficha: Array[Vector3] = []
var _tempo_sem_fichas := 0.0
var _escondido_em: Node3D
var _posicao_antes_esconder := Transform3D()
var _latas_na_mao := 0
var _som: AudioStreamPlayer


func _ready() -> void:
	add_to_group("progressao_v2")
	ui = UIV2.new()
	ui.name = "UIV2"
	add_child(ui)
	_camada_minigame = CanvasLayer.new()
	_camada_minigame.layer = 20
	add_child(_camada_minigame)
	_som = AudioStreamPlayer.new()
	add_child(_som)


## Chamado pelo montador. 'raiz_cenario' contém os .glb; 'mundo' é a cena inteira.
func montar(raiz_cenario: Node, mundo: Node) -> void:
	cenario = raiz_cenario
	for no in raiz_cenario.find_children("Porta__*", "", true, false):
		if String(no.get_parent().name).begins_with("Porta__"):
			continue  # maçaneta, corrente e cadeado são peças da porta, não portas
		var partes := String(no.name).split("__")
		if partes.size() == 3 and no is Node3D:
			_portas[partes[2]] = PortaV2.montar(no, partes[1], partes[2])
	_montar_alicate()
	_montar_secretaria()
	_montar_pistas()
	_montar_teclado()
	_montar_gerador()
	_montar_botao_porta_aco()
	_montar_maquinas()
	_montar_dutos()
	_montar_esconderijos()
	_montar_fichas(mundo.get_node_or_null("Marcadores/Fichas"))
	_montar_cacos_e_latas(mundo)
	var diretor := DiretorTensao.new()
	diretor.name = "DiretorTensao"
	add_child(diretor)
	var audio := AudioDinamico.new()
	audio.name = "AudioDinamico"
	add_child(audio)
	_montar_mapa()
	_montar_musica_maquinas()
	_montar_destaques()
	if not Jogo.checkpoint.is_empty():
		# Depois que o Mundo começar a partida (que zera hora e disjuntores).
		_aplicar_checkpoint.call_deferred()


## Fácil: recomeça do último disjuntor religado (mesma senha, itens, portas e hora).
func _aplicar_checkpoint() -> void:
	var c: Dictionary = Jogo.checkpoint.duplicate(true)
	for id in c["itens"]:
		Jogo.dar_item(id)
	if Jogo.tem_item("alicate"):
		var malha := _achar("Alicate_Corta_Corrente")
		if malha:
			malha.hide()
		var area := cenario.find_child("Interacao_Alicate", true, false) as Interacao
		if area:
			area.desativar()
	for id in c["portas"]:
		if _portas.has(id):
			_portas[id].abrir_para_teste()
	var mundo := get_tree().get_first_node_in_group("mundo")
	for d in get_tree().get_nodes_in_group("disjuntor"):
		if String(d.nome_modelo).trim_prefix("Disjuntor_").to_lower() in c["disjuntores"]:
			d.consertado = true
			d.ligar()
	for i in 4:
		if c["digitos"][i]:
			Jogo.revelar_digitos(i, 1)
	Jogo.minigames_vencidos = c["minigames"]
	Jogo.fichas = c["fichas"]
	Jogo.fichas_mudaram.emit(Jogo.fichas)
	Jogo.hora = c["hora"]
	Jogo.tempo_na_hora = c["tempo_na_hora"]
	Jogo.checkpoint = c  # ligar() acima salvou de novo; mantém o original
	if mundo and mundo.has_method("pedir_reassar_navegacao"):
		mundo.pedir_reassar_navegacao()
	Jogo.mensagem.emit("CHECKPOINT: continuando do último disjuntor", 3.0)


func _achar(nome: String) -> Node3D:
	return cenario.find_child(nome, true, false) as Node3D


func _jogador() -> CharacterBody3D:
	return get_tree().get_first_node_in_group("jogador") as CharacterBody3D


## Coloca uma área de interação na frente de um modelo (frente = +Z local do modelo).
func _interacao_em(modelo: Node3D, tamanho: Vector3, centro_local: Vector3, dica: Callable, acao: Callable) -> Interacao:
	var area := Interacao.criar(tamanho, dica, acao, "Interacao_" + String(modelo.name))
	modelo.add_child(area)
	area.position = centro_local
	return area


## Toca um som curto; se houver a versão externa (mesmo nome em audio_externo/efeitos/), usa ela.
func _tocar(caminho: String, volume := 0.0) -> void:
	var nome := caminho.get_file().get_basename()
	nome = {"pegar_pilha": "pegar_item"}.get(nome, nome)  # pegar item usa o som externo "pegar_item"
	if caminho.begins_with("res://assets/sons/"):
		caminho = SomExterno.caminho("res://assets/audio_externo/efeitos/" + nome, caminho)
	if caminho != "" and ResourceLoader.exists(caminho):
		_som.stream = load(caminho)
		_som.volume_db = volume
		_som.play()


# ---------------------------------------------------------------------------
# Itens e pistas
# ---------------------------------------------------------------------------

func _montar_alicate() -> void:
	var marcador := _achar("Item__alicate")
	var malha := _achar("Alicate_Corta_Corrente")
	if marcador == null:
		return
	# Pesadelo: o alicate pode estar em outro móvel da oficina (bancada, mesa de peças ou estante).
	if Jogo.dificuldade.nivel_sorteio >= 2:
		var lugares := [Vector3(4.0, 0.96, 3.0), Vector3(12.6, 0.76, 9.0), Vector3(9.5, 1.07, 0.6)]
		var p: Vector3 = lugares.pick_random()
		var novo := PlantaV2.mundo(p.x, p.z, p.y)
		if malha:
			malha.global_position = novo  # o alicate fica deitado em cima do móvel sorteado
		marcador.global_position = novo + Vector3(0, 0.04, 0)
	var area := Interacao.criar(Vector3(0.7, 0.4, 0.7), func() -> String: return "Aperte E para pegar o ALICATE corta-corrente",
		func(_j: Node) -> void: pass, "Interacao_Alicate")
	marcador.add_child(area)
	area.funcao_acao = func(_j: Node) -> void:
		Jogo.dar_item("alicate")
		Jogo.anotar("Alicate", "Corta a corrente da porta do depósito (corredor principal, lado oeste). Faz barulho!")
		_tocar("res://assets/sons/pegar_pilha.wav", -4.0)
		if malha:
			malha.hide()
		area.desativar()


# ---------------------------------------------------------------------------
# Secretária eletrônica (recado do gerente no começo da noite, com legendas)
# ---------------------------------------------------------------------------

const RECADO := "res://assets/sons/secretaria_recado.wav"
const LEGENDAS := "res://assets/dados/secretaria_legendas.json"

var _recado: AudioStreamPlayer3D
var _legendas: Array = []
var _rotulo_legenda: Label


func _montar_secretaria() -> void:
	var modelo := _achar("Secretaria_Eletronica")
	if modelo == null or not ResourceLoader.exists(RECADO):
		return
	_recado = AudioStreamPlayer3D.new()
	_recado.name = "Recado"
	_recado.add_to_group("som_voz")  # barramento "Vozes" (volume próprio nas opções)
	_recado.stream = load(RECADO)
	_recado.unit_size = 3.0
	_recado.max_distance = 14.0
	modelo.add_child(_recado)
	if FileAccess.file_exists(LEGENDAS):
		_legendas = JSON.parse_string(FileAccess.get_file_as_string(LEGENDAS)).get("legendas", [])
	_montar_vozes_externas()
	_interacao_em(modelo, Vector3(0.35, 0.3, 0.3), Vector3(0, 0.05, 0.05),
		func() -> String: return "Aperte E para %s o recado da secretária eletrônica" % ("parar" if recado_tocando() else "ouvir"),
		func(_j: Node) -> void:
			if recado_tocando():
				parar_recado()
			else:
				tocar_recado())
	# Toca sozinho logo no começo da noite (não depois de um checkpoint nem nas capturas de tela).
	_recado.finished.connect(_ao_terminar_fala)
	if Jogo.checkpoint.is_empty() and not Jogo.modo_captura:
		get_tree().create_timer(2.5).timeout.connect(func() -> void:
			if is_instance_valid(_recado) and Jogo.em_partida:
				tocar_recado())


# --- Voz externa (docs/PROMPTS_AUDIO.md): uma fala por arquivo, com o filtro de secretária aplicado aqui ---
const FALAS := "res://assets/dados/secretaria_falas.json"
const PASTA_VOZ := "res://assets/audio_externo/voz/"
var _fila_vozes: Array = []   # [{stream, quem, texto}]
var _indice_fala := -1


func _montar_vozes_externas() -> void:
	if not FileAccess.file_exists(FALAS) or SomExterno.caminho(PASTA_VOZ + "voz_recado_01") == "":
		return  # sem a voz externa: fica a gravação feita por script
	for f in JSON.parse_string(FileAccess.get_file_as_string(FALAS)).get("falas", []):
		var s := SomExterno.carregar(PASTA_VOZ + String(f["arquivo"]))
		if s:
			_fila_vozes.append({"stream": s, "quem": f["quem"], "texto": f["texto"]})
	# Barramento "Secretaria": telefone velho = só os médios, um pouco saturado (a voz chega limpa).
	if AudioServer.get_bus_index(&"Secretaria") < 0:
		AudioServer.add_bus()
		var i := AudioServer.bus_count - 1
		AudioServer.set_bus_name(i, &"Secretaria")
		AudioServer.set_bus_send(i, &"Vozes")
		var passa_altas := AudioEffectHighPassFilter.new()
		passa_altas.cutoff_hz = 380.0
		var passa_baixas := AudioEffectLowPassFilter.new()
		passa_baixas.cutoff_hz = 3200.0
		var saturar := AudioEffectDistortion.new()
		saturar.mode = AudioEffectDistortion.MODE_OVERDRIVE
		saturar.drive = 0.22
		saturar.post_gain = -4.0
		for e in [passa_altas, passa_baixas, saturar]:
			AudioServer.add_bus_effect(i, e)
	_recado.bus = &"Secretaria"
	_chiado_fita = AudioStreamPlayer3D.new()
	_chiado_fita.stream = load("res://assets/sons/estatica.wav")
	_chiado_fita.volume_db = -30.0
	_chiado_fita.unit_size = 3.0
	_chiado_fita.max_distance = 14.0
	_chiado_fita.bus = &"Secretaria"
	_recado.get_parent().add_child(_chiado_fita)


var _chiado_fita: AudioStreamPlayer3D


func recado_tocando() -> bool:
	return _recado != null and _recado.playing


func tocar_recado() -> void:
	_anotar_recado()
	if _fila_vozes.is_empty():
		_recado.play()
		return
	_indice_fala = 0
	_tocar_fala()


func parar_recado() -> void:
	_indice_fala = -1
	_recado.stop()
	if _chiado_fita:
		_chiado_fita.stop()


func _tocar_fala() -> void:
	if _indice_fala < 0 or _indice_fala >= _fila_vozes.size():
		parar_recado()
		return
	_recado.stream = _fila_vozes[_indice_fala]["stream"]
	_recado.play()
	if _chiado_fita and not _chiado_fita.playing:
		_chiado_fita.play()


func _ao_terminar_fala() -> void:
	if _indice_fala >= 0:
		# Pausa curta entre as falas (como um recado gravado de verdade) e segue.
		_indice_fala += 1
		await get_tree().create_timer(0.35).timeout
		if _indice_fala > 0:
			_tocar_fala()


func _anotar_recado() -> void:
	Jogo.anotar("Recado do gerente", "Religar os 4 disjuntores (cozinha, gerente, sala elétrica, depósito), depois ligar o gerador " +
		"e fechar a porta de aço da sala de segurança. Chave do gerente: presa na máquina de garra. Senha da sala elétrica: " +
		"metade no bilhete da mesa dele, metade no recorde do TITO KART.")


func _atualizar_legenda() -> void:
	if _recado == null:
		return
	var texto := ""
	if _recado.playing and _indice_fala >= 0 and _indice_fala < _fila_vozes.size():
		texto = "%s: %s" % [_fila_vozes[_indice_fala]["quem"], _fila_vozes[_indice_fala]["texto"]]
	elif _recado.playing:
		var t := _recado.get_playback_position()
		for l in _legendas:
			if t >= float(l["inicio"]) and t <= float(l["fim"]) + 0.4:
				texto = "%s: %s" % [l["quem"], l["texto"]]
	if _rotulo_legenda == null:
		var hud := montador.get_parent().get_node_or_null("HUD") if montador else null
		if hud == null:
			return
		_rotulo_legenda = Label.new()
		_rotulo_legenda.theme_type_variation = &"RotuloHUD"
		_rotulo_legenda.add_theme_font_size_override("font_size", 24)
		_rotulo_legenda.add_theme_constant_override("outline_size", 6)
		_rotulo_legenda.add_theme_color_override("font_outline_color", Color.BLACK)
		_rotulo_legenda.add_theme_color_override("font_color", Color(0.95, 0.92, 0.75))
		_rotulo_legenda.set_anchors_and_offsets_preset(Control.PRESET_CENTER_BOTTOM)
		_rotulo_legenda.offset_left = -520
		_rotulo_legenda.offset_right = 520
		_rotulo_legenda.offset_top = -150
		_rotulo_legenda.offset_bottom = -96
		_rotulo_legenda.horizontal_alignment = HORIZONTAL_ALIGNMENT_CENTER
		_rotulo_legenda.autowrap_mode = TextServer.AUTOWRAP_WORD_SMART
		hud.add_child(_rotulo_legenda)
	_rotulo_legenda.text = texto


## Textos das pistas. {D3} e {D4} viram os dígitos sorteados da senha.
const PISTAS := {
	"aniversario": {"titulo": "FESTA DO LUCAS!", "estilo": "cartaz", "revela": [],
		"texto": "Venha comemorar os {D3} aninhos do Lucas\ncom o Tito e a Pipoca!\n\nSábado, 15h — Sala das Estrelas\nTraga seu sorriso!"},
	"quadro_avisos": {"titulo": "QUADRO DE AVISOS", "estilo": "documento", "revela": [],
		"texto": "ESCALA DA NOITE: vigia (novo)\n\n• Não deixar comida na geladeira!!\n• Máquina de garra: chamar a assistência (de novo)\n• Os bonecos ficam no palco. SEMPRE.\n• Quem pegou o grampeador da gerência devolve."},
	"recado_gerente": {"titulo": "(bilhete na mesa do gerente)", "estilo": "manuscrito", "revela": [2, 2],
		"texto": "Troquei a senha da sala elétrica.\nPra não esquecer:\n— os 2 PRIMEIROS números = o meu recorde no TITO KART\n— os 2 ÚLTIMOS números = {D3}{D4}\nNÃO deixe o novo vigia mexer no gerador."},
}


const NOMES_PISTAS := {"aniversario": "Pôster da festa do Lucas", "quadro_avisos": "Quadro de avisos da copa",
	"recado_gerente": "Bilhete do gerente (senha)"}


func texto_pista(id: String) -> String:
	var texto := String(PISTAS[id]["texto"])
	return texto.replace("{D3}", Jogo.codigo[2]).replace("{D4}", Jogo.codigo[3])


func _montar_pistas() -> void:
	for id in PISTAS:
		var marcador := _achar("Pista__" + id)
		if marcador == null:
			push_warning("Pista sem marcador no mapa: " + id)
			continue
		marcador.add_to_group("documento")
		var p: Dictionary = PISTAS[id]
		var area := Interacao.criar(Vector3(0.8, 0.8, 0.8), func() -> String: return "Aperte E para ler",
			func(_j: Node) -> void:
				ui.mostrar_documento(p["titulo"], texto_pista(id), p["estilo"])
				Jogo.anotar(NOMES_PISTAS[id], texto_pista(id).replace("\n", " "))
				var r: Array = p["revela"]
				if not r.is_empty():
					Jogo.revelar_digitos(r[0], r[1]), "Interacao_Pista_" + id)
		marcador.add_child(area)


# ---------------------------------------------------------------------------
# Teclado, gerador e porta de aço
# ---------------------------------------------------------------------------

func _montar_teclado() -> void:
	var teclado := _achar("Teclado_Eletrica")
	if teclado == null:
		return
	_interacao_em(teclado, Vector3(0.45, 0.45, 0.3), Vector3(0, 0.1, 0.12),
		func() -> String:
			var porta: PortaV2 = _portas.get("eletrica")
			if porta and not porta.trancada:
				return "Teclado: acesso liberado"
			return "Aperte E para digitar a senha (%s)" % Jogo.codigo_conhecido(),
		func(_j: Node) -> void:
			var porta: PortaV2 = _portas.get("eletrica")
			if porta and porta.trancada:
				ui.abrir_teclado(Jogo.codigo, _ao_acertar_senha))


func _ao_acertar_senha() -> void:
	Jogo.revelar_digitos(0, 4)
	var porta: PortaV2 = _portas.get("eletrica")
	if porta:
		porta.destrancar()
		porta.alternar(_jogador())
	Jogo.mensagem.emit("Sala elétrica liberada.", 2.0)


func _montar_gerador() -> void:
	var gerador := _achar("Gerador_Principal")
	if gerador == null:
		return
	var alavanca := gerador.find_child("Gerador_Principal_Alavanca", false, false) as Node3D
	_interacao_em(gerador, Vector3(2.4, 1.5, 0.35), Vector3(0, 0.9, 0.82),
		func() -> String:
			if Jogo.gerador_esta_ligado:
				return "Gerador principal: LIGADO"
			if not Jogo.todos_disjuntores_ligados():
				return "Gerador principal: religue os 4 disjuntores antes (%d/%d)" % [Jogo.disjuntores_ligados, Jogo.total_disjuntores]
			return "Aperte E para LIGAR O GERADOR (e depois corra!)",
		func(_j: Node) -> void:
			if Jogo.gerador_esta_ligado or not Jogo.todos_disjuntores_ligados():
				return
			if alavanca:
				create_tween().tween_property(alavanca, "rotation:x", deg_to_rad(35), 0.5).set_trans(Tween.TRANS_BACK)
			_tocar("res://assets/sons/gerador_partida.wav")
			Jogo.emitir_ruido(gerador.global_position, 60.0, 1.0)
			if montador and montador.has_method("ligar_energia"):
				montador.ligar_energia("gerador")
			Jogo.ligar_gerador())


func _montar_botao_porta_aco() -> void:
	var botao := _achar("Botao_Porta_Seguranca")
	if botao == null:
		return
	var luz := botao.find_child("Botao_Porta_Seguranca_Luz", false, false) as MeshInstance3D
	_interacao_em(botao, Vector3(0.4, 0.45, 0.3), Vector3(0, 0.1, 0.1),
		func() -> String:
			if not Jogo.gerador_esta_ligado:
				return "Porta de aço: SEM ENERGIA (só funciona com o gerador principal ligado)"
			return "Aperte E para %s a porta de aço" % ("ABRIR" if Jogo.porta_seguranca_fechada else "FECHAR"),
		func(_j: Node) -> void:
			var porta: PortaV2 = _portas.get("seguranca")
			if not Jogo.gerador_esta_ligado or porta == null:
				_tocar("res://assets/sons/teclado_erro.wav")
				return
			porta.alternar()
			Jogo.mudar_porta_seguranca(not porta.aberta)
			if luz:
				var m := StandardMaterial3D.new()
				var cor := Color(1, 0.15, 0.1) if not porta.aberta else Color(0.2, 1, 0.3)
				m.albedo_color = cor
				m.emission_enabled = true
				m.emission = cor
				m.emission_energy_multiplier = 3.0
				luz.material_override = m)


# ---------------------------------------------------------------------------
# Máquinas e minigames
# ---------------------------------------------------------------------------

## V2.2: as máquinas têm bateria própria (nobreak): funcionam sem disjuntor nenhum, para
## nunca travar a progressão de um jeito confuso.
func _fliperama_com_energia() -> bool:
	return true


func _montar_maquinas() -> void:
	var garra := _achar("Maquina_Garra")
	if garra:
		_interacao_em(garra, Vector3(1.0, 1.3, 0.35), Vector3(0, 1.1, 0.66),
			func() -> String: return _dica_maquina("MÁQUINA DE GARRA", Jogo.tem_item("chave_gerente")),
			func(_j: Node) -> void: _jogar_maquina("garra", {}, garra))
	var maquinas := {"Arcade_Tito_Kart": ["kart", "TITO KART"], "Arcade_Space_Pizza": [MINIGAME_KART_RESERVA, "SPACE PIZZA"]}
	for nome in maquinas:
		var m := _achar(nome)
		if m == null:
			continue
		var info: Array = maquinas[nome]
		_interacao_em(m, Vector3(0.75, 1.1, 0.35), Vector3(0, 1.2, 0.62),
			func() -> String: return _dica_maquina(info[1], Jogo.digitos_conhecidos[0] and Jogo.digitos_conhecidos[1]),
			func(_j: Node) -> void: _jogar_maquina(info[0], {"codigo": Jogo.codigo}, m))


func _dica_maquina(nome: String, ja_ganhou: bool) -> String:
	if ja_ganhou:
		return "Aperte E para jogar %s de graça (você já ganhou o que precisava aqui)" % nome
	if Jogo.fichas <= 0:
		return "%s: precisa de 1 ficha (você não tem nenhuma)" % nome
	return "Aperte E para jogar %s (1 ficha — você tem %d)" % [nome, Jogo.fichas]


func _jogar_maquina(nome: String, dados: Dictionary, maquina: Node3D) -> void:
	# Depois de cumprir o objetivo da máquina, ela fica de graça (sempre jogável).
	var gratis := (nome == "garra" and Jogo.tem_item("chave_gerente")) or \
		(nome != "garra" and Jogo.digitos_conhecidos[0] and Jogo.digitos_conhecidos[1])
	if not gratis and Jogo.fichas <= 0:
		_tocar("res://assets/sons/teclado_erro.wav")
		Jogo.mensagem.emit("Sem fichas. Procure no chão: elas brilham (e o mapa, M, ajuda).", 3.0)
		return
	if not ResourceLoader.exists(PASTA_MINIGAMES + nome + ".tscn"):
		nome = MINIGAME_KART_RESERVA if nome == "kart" else nome
	if not gratis:
		Jogo.mudar_fichas(-1)
	abrir_minigame(nome, dados, maquina.global_position, func(venceu: bool, resultado: Dictionary) -> void:
		if not venceu:
			return
		if resultado.get("premio", "") == "chave_gerente" and not Jogo.tem_item("chave_gerente"):
			Jogo.dar_item("chave_gerente")
			Jogo.anotar("Chave do gerente", "Ganha na garra. Abre a sala do gerente (corredor principal, lado da copa).")
		if resultado.has("digitos") and not (Jogo.digitos_conhecidos[0] and Jogo.digitos_conhecidos[1]):
			Jogo.revelar_digitos(0, 2)
			Jogo.anotar("Recorde do TITO KART", "A senha da sala elétrica começa com %s." % Jogo.codigo.left(2)))


## Abre um minigame por cima do jogo (o mundo NÃO pausa). 'ao_terminar(venceu, resultado)'.
func abrir_minigame(nome: String, dados: Dictionary, posicao: Vector3, ao_terminar: Callable) -> void:
	var caminho := PASTA_MINIGAMES + nome + ".tscn"
	if _minigame != null or not ResourceLoader.exists(caminho):
		if not ResourceLoader.exists(caminho):
			push_warning("Minigame não encontrado: " + caminho)
		return
	var jogador := _jogador()
	if jogador:
		jogador.travado = true
	_minigame = load(caminho).instantiate() as Minigame
	_camada_minigame.add_child(_minigame)
	_posicao_minigame = posicao
	_tempo_ruido_minigame = 0.0
	Jogo.minigame_aberto = nome
	Jogo.minigame_iniciado.emit(nome)
	_minigame.terminado.connect(func(venceu: bool, resultado: Dictionary) -> void:
		_minigame = null
		if jogador and is_instance_valid(jogador):
			jogador.travado = false
		Jogo.registrar_minigame(nome, venceu)
		ao_terminar.call(venceu, resultado))
	_minigame.iniciar(Jogo.dificuldade, dados)


## F7 (debug): vence o minigame aberto.
func vencer_minigame_aberto() -> void:
	if _minigame:
		_minigame.vencer_agora()


# ---------------------------------------------------------------------------
# Fichas (1 por tentativa na garra ou no kart)
# ---------------------------------------------------------------------------

func _montar_fichas(pasta: Node) -> void:
	if pasta == null:
		return
	for m in pasta.get_children():
		if m is Node3D:
			_candidatos_ficha.append((m as Node3D).global_position)
	var ordem := _candidatos_ficha.duplicate()
	if Jogo.dificuldade.nivel_sorteio >= 1:
		ordem.shuffle()
	for i in mini(Jogo.dificuldade.fichas_no_mapa, ordem.size()):
		_criar_ficha(ordem[i])
	if Jogo.checkpoint.is_empty() and Jogo.dificuldade.fichas_iniciais > 0:
		Jogo.mudar_fichas(Jogo.dificuldade.fichas_iniciais)


func _criar_ficha(pos: Vector3) -> void:
	var raiz := Node3D.new()
	raiz.name = "Ficha"
	raiz.add_to_group("ficha")
	add_child(raiz)
	raiz.global_position = pos + Vector3(0, 0.02, 0)
	var malha := MeshInstance3D.new()
	var cilindro := CylinderMesh.new()
	cilindro.top_radius = 0.045
	cilindro.bottom_radius = 0.045
	cilindro.height = 0.008
	malha.mesh = cilindro
	var m := StandardMaterial3D.new()
	m.albedo_color = Color(0.95, 0.75, 0.25)
	m.metallic = 0.8
	m.roughness = 0.35
	m.emission_enabled = true
	m.emission = Color(0.6, 0.45, 0.1)
	m.emission_energy_multiplier = 0.35  # brilha de leve para ser achada no escuro
	malha.material_override = m
	malha.position.y = 0.005
	raiz.add_child(malha)
	var area := Interacao.criar(Vector3(0.5, 0.4, 0.5), func() -> String: return "Aperte E para pegar a FICHA",
		func(_j: Node) -> void:
			Jogo.mudar_fichas(1)
			Jogo.contar("fichas")
			_tocar("res://assets/sons/ficha.wav" if ResourceLoader.exists("res://assets/sons/ficha.wav") else "res://assets/sons/pegar_pilha.wav", -4.0)
			raiz.queue_free(), "Interacao_Ficha")
	raiz.add_child(area)
	area.position.y = 0.15
	if is_inside_tree() and raiz.is_inside_tree():
		Destaque.colocar.call_deferred(raiz, Color(1.0, 0.82, 0.3), 0.8)


## Anti-travamento: sem fichas no bolso nem no mapa, e com garra ou kart ainda por vencer,
## uma ficha nova aparece num ponto candidato depois de um tempo.
func _verificar_fichas(delta: float) -> void:
	var falta_garra := not Jogo.tem_item("chave_gerente")
	var falta_kart := not (Jogo.digitos_conhecidos[0] and Jogo.digitos_conhecidos[1])
	if Jogo.fichas > 0 or not (falta_garra or falta_kart) or get_tree().get_nodes_in_group("ficha").size() > 0 \
			or _candidatos_ficha.is_empty():
		_tempo_sem_fichas = 0.0
		return
	_tempo_sem_fichas += delta
	if _tempo_sem_fichas >= Jogo.dificuldade.reaparecer_ficha_s:
		_tempo_sem_fichas = 0.0
		_criar_ficha(_candidatos_ficha.pick_random())
		Jogo.mensagem.emit("Você ouve uma moeda tilintar em algum lugar...", 3.0)


# ---------------------------------------------------------------------------
# Dutos (rastejar entre a oficina, a sala dos piratas e a copa)
# ---------------------------------------------------------------------------

func _montar_dutos() -> void:
	for comodo in SAIDAS_DUTO:
		var s: Dictionary = SAIDAS_DUTO[comodo]
		var ponto := Node3D.new()
		ponto.name = "Duto_Entrada_" + comodo
		ponto.add_to_group("duto_grade")
		ponto.set_meta("comodo", comodo)
		add_child(ponto)
		ponto.global_position = PlantaV2.mundo(s["x"], s["z"], 0.4)
		var area := Interacao.criar(Vector3(1.0, 0.8, 1.0), func() -> String: return "Aperte E para entrar no DUTO",
			func(_j: Node) -> void: _escolher_saida_duto(comodo), "Interacao_Duto")
		ponto.add_child(area)


func _escolher_saida_duto(de: String) -> void:
	var destinos: Array = []
	var textos: Array = []
	for c in SAIDAS_DUTO:
		if c != de:
			destinos.append(c)
			textos.append(SAIDAS_DUTO[c]["titulo"])
	ui.abrir_menu("Rastejar pelo duto até...", textos, func(i: int) -> void: rastejar(de, destinos[i]))


## Atravessa o duto: tela escura com o som de rastejar e o vigia sai do outro lado, agachado.
func rastejar(de: String, para: String) -> void:
	var jogador := _jogador()
	if jogador == null:
		return
	var a: Dictionary = SAIDAS_DUTO[de]
	var b: Dictionary = SAIDAS_DUTO[para]
	# O duto segue pelo forro: comprimento aproximado = distância "em L" entre as grades.
	var metros := absf(a["x"] - b["x"]) + absf(a["z"] - b["z"])
	var duracao := maxf(metros * SEGUNDOS_POR_METRO_DUTO, 2.0)
	jogador.no_duto = true
	jogador.add_to_group("no_duto")
	var tela := ColorRect.new()
	tela.color = Color(0, 0, 0, 0)
	tela.set_anchors_preset(Control.PRESET_FULL_RECT)
	var texto := Label.new()
	texto.text = "rastejando pelo duto..."
	texto.theme_type_variation = &"RotuloHUD"
	texto.set_anchors_and_offsets_preset(Control.PRESET_CENTER)
	tela.add_child(texto)
	ui.add_child(tela)
	_tocar("res://assets/sons/grade_duto.wav", -4.0)
	await get_tree().create_timer(0.3).timeout
	_tocar("res://assets/sons/duto_rastejar.wav")
	var t := create_tween()
	t.tween_property(tela, "color:a", 1.0, 0.4)
	await t.finished
	await get_tree().create_timer(duracao).timeout
	if not is_instance_valid(jogador):
		return
	jogador.global_position = PlantaV2.mundo(b["x"], b["z"], 0.05)
	jogador.rotation.y = deg_to_rad(b["olhar"])
	jogador.velocity = Vector3.ZERO
	jogador.no_duto = false
	jogador.remove_from_group("no_duto")
	Jogo.emitir_ruido(jogador.global_position, 5.0, 0.4)  # a grade range ao sair
	_tocar("res://assets/sons/grade_duto.wav", -4.0)
	var t2 := create_tween()
	t2.tween_property(tela, "color:a", 0.0, 0.5)
	t2.tween_callback(tela.queue_free)


# ---------------------------------------------------------------------------
# Esconderijos
# ---------------------------------------------------------------------------

func _montar_esconderijos() -> void:
	for marcador in get_tree().get_nodes_in_group("esconderijo"):
		var tipo := String(marcador.get_meta("tipo", ""))
		if not ESCONDERIJOS.has(tipo):
			continue  # ex.: "duto" (os dutos têm lógica própria)
		var area := Interacao.criar(Vector3(1.2, 1.6, 1.2), func() -> String: return "Aperte E para se ESCONDER",
			func(_j: Node) -> void: esconder(marcador), "Interacao_Esconderijo")
		marcador.add_child(area)
		area.position.y = 0.8


## Como é cada tipo de esconderijo por dentro:
##   altura: altura da câmera · vista: máscara (VistaEsconderijo) · recuo: quanto o "dentro" fica
##   atrás do marcador (armário: o marcador está na frente da porta) · giro/inclinacao: quanto dá
##   para virar a cabeça (graus) · som: arquivo de som ao entrar/sair.
const ESCONDERIJOS := {
	"armario": {"altura": 1.55, "vista": "frestas", "recuo": 0.55, "giro": 35.0, "inclinacao": 18.0, "som": "armario"},
	"armario_limpeza": {"altura": 1.45, "vista": "frestas", "recuo": 0.0, "giro": 35.0, "inclinacao": 18.0, "som": "armario"},
	"mesa_toalha": {"altura": 0.14, "vista": "toalha", "recuo": 0.0, "giro": 75.0, "inclinacao": 12.0, "som": "tecido"},
	"cabine": {"altura": 1.4, "vista": "nenhuma", "recuo": 0.0, "giro": 40.0, "inclinacao": 20.0, "som": "armario"},
	"cortina_palco": {"altura": 1.45, "vista": "tecido", "recuo": 0.0, "giro": 50.0, "inclinacao": 18.0, "som": "tecido"},
	"figurinos": {"altura": 1.35, "vista": "tecido", "recuo": 0.0, "giro": 50.0, "inclinacao": 18.0, "som": "tecido"},
}
const SONS_ESCONDER := {
	"armario": ["res://assets/audio_externo/efeitos/armario_entrar", "res://assets/audio_externo/efeitos/armario_sair", "res://assets/sons/porta_trancada.wav"],
	"tecido": ["res://assets/audio_externo/efeitos/tecido_esconder", "res://assets/audio_externo/efeitos/tecido_esconder", "res://assets/sons/vento.wav"],
}

var _vista: VistaEsconderijo
var _abafar: AudioEffectLowPassFilter
var _respiracao_escondido: AudioStreamPlayer


## Para onde o vigia olha de dentro: para a porta mais próxima do cômodo (é por onde o perigo entra).
## Debaixo da mesa, para o lado ABERTO da toalha (o único de onde dá para ver alguma coisa).
func _olhar_do_esconderijo(pos: Vector3, tipo := "") -> Vector3:
	if tipo == "cabine":
		return Vector3.LEFT  # a frente das cabines (com a porta) fica a oeste
	if tipo in ["mesa_toalha", "cortina_palco"]:
		# Mesa: raio rente ao chão (por baixo do tampo). Cortina: na altura do corpo (as cortinas têm colisão).
		var aberto := _lado_aberto(pos, 0.25 if tipo == "mesa_toalha" else pos.y + 1.0)
		if aberto != Vector3.ZERO:
			return aberto
	var comodo := PlantaV2.comodo_em(pos)
	var melhor := Vector3.ZERO
	var menor := INF
	var x := pos.x + 30.0
	var z := pos.z + 22.5
	for c in PlantaV2.dados()["comodos"]:
		if c["nome"] != comodo:
			continue
		for p in PlantaV2.dados()["portas"]:
			var px: float = p["centro"] if p["eixo"] == "z" else p["fixo"]
			var pz: float = p["fixo"] if p["eixo"] == "z" else p["centro"]
			# A porta pertence ao cômodo se está na borda dele.
			var na_borda: bool = px >= c["x0"] - 0.1 and px <= c["x1"] + 0.1 and pz >= c["z0"] - 0.1 and pz <= c["z1"] + 0.1
			var d := Vector2(px - x, pz - z).length()
			if na_borda and d < menor and d > 0.3:
				menor = d
				melhor = Vector3(px - x, 0, pz - z).normalized()
		if melhor == Vector3.ZERO:
			var centro := Vector3((c["x0"] + c["x1"]) / 2.0 - x, 0, (c["z0"] + c["z1"]) / 2.0 - z)
			melhor = centro.normalized() if centro.length() > 0.1 else Vector3.FORWARD
	return melhor if melhor != Vector3.ZERO else Vector3.FORWARD


## Raios na altura do chão nas 4 direções: o lado aberto é o que vai mais longe sem bater na toalha.
func _lado_aberto(pos: Vector3, altura := 0.25) -> Vector3:
	var espaco := get_viewport().get_world_3d().direct_space_state
	var melhor := Vector3.ZERO
	var maior := 0.0
	for d in [Vector3.FORWARD, Vector3.BACK, Vector3.LEFT, Vector3.RIGHT]:
		var de := Vector3(pos.x, altura, pos.z)
		var consulta := PhysicsRayQueryParameters3D.create(de, de + d * 3.0, 1)
		var r := espaco.intersect_ray(consulta)
		var distancia := 3.0 if r.is_empty() else de.distance_to(r.position)
		if distancia > maior:
			maior = distancia
			melhor = d
	return melhor


func esconder(marcador: Node3D) -> void:
	var jogador := _jogador()
	if jogador == null or jogador.escondido or jogador.no_duto:
		return
	var tipo := String(marcador.get_meta("tipo", ""))
	var cfg: Dictionary = ESCONDERIJOS.get(tipo, ESCONDERIJOS["armario"])
	var olhar := _olhar_do_esconderijo(marcador.global_position, String(marcador.get_meta("tipo", "")))
	var dentro := Vector3(marcador.global_position.x, 0.0, marcador.global_position.z) - olhar * float(cfg["recuo"])
	_escondido_em = marcador
	_posicao_antes_esconder = jogador.global_transform
	await _piscar_tela(0.1)
	jogador.escondido = true
	Jogo.contar("escondido")
	jogador.set_meta("esconderijo", marcador)
	jogador.add_to_group("escondido")
	jogador.collision_layer = 0  # os animatrônicos só acham se checarem o esconderijo
	jogador.global_position = Vector3(dentro.x, _altura_do_chao(dentro), dentro.z)
	jogador.rotation.y = atan2(-olhar.x, -olhar.z)  # a frente do vigia é -Z
	if tipo == "cabine":
		_fechar_porta_cabine(marcador, true)
		# Fica do lado do trinco, dentro da cabine, e espia pela fresta entre a ponta da porta
		# encostada (40 graus) e o batente: dali dá para ver quem passa no banheiro.
		var canto := marcador.global_position + Vector3(-0.1, 0, 0.55)
		jogador.global_position = Vector3(canto.x, jogador.global_position.y, canto.z)
		var fresta := Vector3(-1.0, 0, -0.25)
		jogador.rotation.y = atan2(-fresta.x, -fresta.z)
	jogador.travar_olhar(deg_to_rad(cfg["giro"]), deg_to_rad(cfg["inclinacao"]))
	var cabeca: Node3D = jogador.get_node("Cabeca")
	cabeca.rotation.x = 0.0
	cabeca.position.y = float(cfg["altura"])
	if jogador.lanterna_ligada:
		jogador.alternar_lanterna()  # luz acesa dentro do esconderijo entrega o vigia
	_vista = VistaEsconderijo.new()
	_vista.tipo = cfg["vista"]
	var hud := montador.get_parent().get_node_or_null("HUD") if montador else null
	if hud:
		hud.add_child(_vista)
		hud.move_child(_vista, 0)  # por baixo do HUD: bateria e mensagens continuam visíveis
	else:
		ui.add_child(_vista)
	_tocar_som_esconder(cfg["som"], 0)
	_abafar_som(true)
	Jogo.emitir_ruido(jogador.global_position, 2.0, 0.2)
	_piscar_tela_voltar()


func sair_do_esconderijo() -> void:
	var jogador := _jogador()
	if jogador == null or not jogador.escondido:
		return
	var marcador := _escondido_em
	var tipo := String(marcador.get_meta("tipo", "")) if marcador else ""
	var cfg: Dictionary = ESCONDERIJOS.get(tipo, ESCONDERIJOS["armario"])
	if tipo == "cabine":
		_fechar_porta_cabine(marcador, false)
	var saida := _ponto_de_saida(marcador) if marcador else _posicao_antes_esconder.origin
	jogador.escondido = false
	jogador.remove_meta("esconderijo")
	jogador.remove_from_group("escondido")
	jogador.collision_layer = 2
	jogador.liberar_olhar()
	jogador.global_position = saida
	jogador.velocity = Vector3.ZERO
	_escondido_em = null
	if is_instance_valid(_vista):
		_vista.queue_free()
	_tocar_som_esconder(cfg["som"], 1)
	_abafar_som(false)
	Jogo.emitir_ruido(jogador.global_position, 3.0, 0.3)


## Porta da cabine do banheiro (objeto "Cabine_NN_Porta" do Blender, origem na dobradiça).
## Escondido: fica QUASE fechada (sobra uma fresta para espiar). Saindo: volta a ficar aberta.
var _rotacao_porta_cabine := {}


func _fechar_porta_cabine(marcador: Node3D, fechar: bool) -> void:
	var numero := String(marcador.name).get_slice("_", String(marcador.name).get_slice_count("_") - 1)
	var porta := _achar("Cabine_%s_Porta" % numero)
	if porta == null:
		return
	if not _rotacao_porta_cabine.has(porta):
		_rotacao_porta_cabine[porta] = porta.rotation.y
	var alvo: float = deg_to_rad(40.0) if fechar else _rotacao_porta_cabine[porta]
	porta.rotation.y = alvo  # na hora: a tela está escura (o teleporte esconde o movimento)


## Altura do chão de verdade embaixo do esconderijo (o palco tem 0,6 m; o resto é 0).
## O raio sai de 0,68 m: acima do palco e abaixo do tampo das mesas (0,72 m), para não "pousar" na mesa.
## Antes usava a altura de onde o vigia estava e, se ela viesse alta, ele enxergava POR CIMA das cabines.
func _altura_do_chao(pos: Vector3) -> float:
	var de := Vector3(pos.x, 0.68, pos.z)
	var consulta := PhysicsRayQueryParameters3D.create(de, de + Vector3.DOWN * 1.2, 1)
	consulta.exclude = [_jogador().get_rid()] if _jogador() else []
	var r := get_viewport().get_world_3d().direct_space_state.intersect_ray(consulta)
	return r.position.y if r else 0.0


## Um ponto LIVRE na frente do esconderijo: na navegação e sem colidir com nada.
## Tenta na frente (1 m, 1,4 m...), depois para os lados e para trás; se nada servir, volta de onde entrou.
func _ponto_de_saida(marcador: Node3D) -> Vector3:
	var olhar := _olhar_do_esconderijo(marcador.global_position, String(marcador.get_meta("tipo", "")))
	var base := Vector3(marcador.global_position.x, 0.0, marcador.global_position.z)
	var mundo := get_tree().get_first_node_in_group("mundo")
	var mapa: RID = mundo.get_node("Navegacao").get_navigation_map() if mundo else RID()
	for distancia in [1.0, 1.4, 1.8]:
		for angulo in [0.0, 40.0, -40.0, 80.0, -80.0, 135.0, -135.0, 180.0]:
			var candidato: Vector3 = base + olhar.rotated(Vector3.UP, deg_to_rad(angulo)) * float(distancia)
			if mapa.is_valid():
				var na_navegacao := NavigationServer3D.map_get_closest_point(mapa, candidato)
				if Vector2(na_navegacao.x - candidato.x, na_navegacao.z - candidato.z).length() > 0.25:
					continue
				candidato = na_navegacao
			if _livre(candidato):
				return candidato + Vector3(0, 0.05, 0)
	return _posicao_antes_esconder.origin


## Cabe o vigia em pé aqui? (cápsula do tamanho dele, contra a camada "Mundo")
func _livre(pos: Vector3) -> bool:
	var forma := CapsuleShape3D.new()
	forma.radius = 0.33
	forma.height = 1.7
	var consulta := PhysicsShapeQueryParameters3D.new()
	consulta.shape = forma
	consulta.transform = Transform3D(Basis(), pos + Vector3(0, 0.9, 0))
	consulta.collision_mask = 1
	return get_viewport().get_world_3d().direct_space_state.intersect_shape(consulta, 1).is_empty()


## Escuro rápido (só para esconder o teleporte).
var _tela_preta: ColorRect


func _piscar_tela(duracao: float) -> void:
	if _tela_preta == null:
		_tela_preta = ColorRect.new()
		_tela_preta.color = Color(0, 0, 0, 0)
		_tela_preta.set_anchors_and_offsets_preset(Control.PRESET_FULL_RECT)
		_tela_preta.mouse_filter = Control.MOUSE_FILTER_IGNORE
		ui.add_child(_tela_preta)
	var t := create_tween()
	t.tween_property(_tela_preta, "color:a", 1.0, duracao)
	await t.finished


func _piscar_tela_voltar() -> void:
	if _tela_preta:
		create_tween().tween_property(_tela_preta, "color:a", 0.0, 0.18)


func _tocar_som_esconder(tipo_som: String, indice: int) -> void:
	var lista: Array = SONS_ESCONDER.get(tipo_som, [])
	if lista.is_empty():
		return
	var caminho := SomExterno.caminho(lista[indice], lista[2])
	if caminho != "":
		_tocar(caminho, -6.0)


## Escondido, o mundo soa abafado (filtro passa-baixa nos efeitos) e a respiração fica baixinha.
func _abafar_som(ligar: bool) -> void:
	var i := AudioServer.get_bus_index(&"Efeitos")
	if i < 0:
		return
	if _abafar == null:
		_abafar = AudioEffectLowPassFilter.new()
		_abafar.cutoff_hz = 900.0
		AudioServer.add_bus_effect(i, _abafar)
	for k in AudioServer.get_bus_effect_count(i):
		if AudioServer.get_bus_effect(i, k) == _abafar:
			AudioServer.set_bus_effect_enabled(i, k, ligar)
	if _respiracao_escondido == null:
		_respiracao_escondido = AudioStreamPlayer.new()
		var c := SomExterno.caminho("res://assets/audio_externo/efeitos/resp_escondido_loop", "res://assets/sons/respiracao_escondido.wav")
		if c != "":
			_respiracao_escondido.stream = load(c)
		_respiracao_escondido.volume_db = -16.0
		add_child(_respiracao_escondido)
		_respiracao_escondido.finished.connect(func() -> void:
			if _jogador() and _jogador().escondido:
				_respiracao_escondido.play())
	if ligar and _respiracao_escondido.stream:
		_respiracao_escondido.play()
	elif not ligar:
		_respiracao_escondido.stop()


func _exit_tree() -> void:
	if _abafar:
		_abafar_som(false)  # não deixar o menu abafado


# ---------------------------------------------------------------------------
# Cacos de vidro, latas (G) e fio desencapado
# ---------------------------------------------------------------------------

func _montar_cacos_e_latas(_mundo: Node) -> void:
	var mat_vidro := StandardMaterial3D.new()
	mat_vidro.albedo_color = Color(0.75, 0.9, 0.85, 0.55)
	mat_vidro.transparency = BaseMaterial3D.TRANSPARENCY_ALPHA
	mat_vidro.metallic = 0.4
	mat_vidro.roughness = 0.05
	for c in CACOS:
		var raiz := Node3D.new()
		raiz.name = "Cacos_Vidro"
		add_child(raiz)
		raiz.global_position = PlantaV2.mundo(c[0], c[1], 0.0)
		for i in 7:
			var caco := MeshInstance3D.new()
			var p := PrismMesh.new()
			p.size = Vector3(randf_range(0.05, 0.12), 0.006, randf_range(0.04, 0.1))
			caco.mesh = p
			caco.material_override = mat_vidro
			caco.position = Vector3(randf_range(-0.4, 0.4), 0.004, randf_range(-0.4, 0.4))
			caco.rotation.y = randf() * TAU
			raiz.add_child(caco)
		var area := Area3D.new()
		area.collision_layer = 0
		area.collision_mask = 2  # só o vigia
		var forma := CollisionShape3D.new()
		var caixa := BoxShape3D.new()
		caixa.size = Vector3(1.0, 0.5, 1.0)
		forma.shape = caixa
		area.add_child(forma)
		raiz.add_child(area)
		area.body_entered.connect(func(corpo: Node3D) -> void:
			if corpo.is_in_group("jogador") and not corpo.agachado:
				Jogo.emitir_ruido(raiz.global_position, 9.0, 0.7)
				_tocar("res://assets/sons/vidro_quebrando.wav", -4.0))
	for l in LATAS:
		_criar_lata_no_chao(PlantaV2.mundo(l[0], l[1], 0.0))
	# (V2.2: o fio desencapado com choque foi removido: não era legível; ver PLANO_V2.md.)


func _criar_lata_no_chao(pos: Vector3) -> void:
	var raiz := Node3D.new()
	raiz.name = "Lata"
	add_child(raiz)
	raiz.global_position = pos
	var malha := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = 0.033
	c.bottom_radius = 0.033
	c.height = 0.12
	malha.mesh = c
	var m := StandardMaterial3D.new()
	m.albedo_color = Color.from_hsv(randf(), 0.6, 0.7)
	m.metallic = 0.7
	m.roughness = 0.4
	malha.material_override = m
	malha.rotation.z = PI / 2.0  # deitada
	malha.position.y = 0.033
	raiz.add_child(malha)
	var area := Interacao.criar(Vector3(0.4, 0.3, 0.4), func() -> String: return "Aperte E para pegar a lata (G arremessa)",
		func(_j: Node) -> void:
			_latas_na_mao += 1
			raiz.queue_free(), "Interacao_Lata")
	raiz.add_child(area)


## G: joga uma lata para frente. Onde ela bate faz barulho e atrai os animatrônicos.
func arremessar_lata() -> void:
	var jogador := _jogador()
	if jogador == null or _latas_na_mao <= 0 or jogador.travado or jogador.escondido:
		return
	_latas_na_mao -= 1
	Jogo.contar("latas")
	var camera: Camera3D = jogador.get_node("Cabeca/Camera3D")
	var corpo := RigidBody3D.new()
	corpo.collision_layer = 0
	corpo.collision_mask = 1
	corpo.contact_monitor = true
	corpo.max_contacts_reported = 1
	corpo.continuous_cd = true  # lata pequena e rápida: sem isto ela pode "atravessar" a parede
	var forma := CollisionShape3D.new()
	var cil := CylinderShape3D.new()
	cil.radius = 0.035
	cil.height = 0.12
	forma.shape = cil
	corpo.add_child(forma)
	var malha := MeshInstance3D.new()
	var c := CylinderMesh.new()
	c.top_radius = 0.033
	c.bottom_radius = 0.033
	c.height = 0.12
	malha.mesh = c
	corpo.add_child(malha)
	add_child(corpo)
	corpo.global_position = camera.global_position - camera.global_basis.z * 0.5
	corpo.linear_velocity = -camera.global_basis.z * 11.0 + Vector3.UP * 2.0
	corpo.angular_velocity = Vector3(randf(), randf(), randf()) * 8.0
	var bateu := [false]
	corpo.body_entered.connect(func(_outro: Node) -> void:
		if bateu[0]:
			return
		bateu[0] = true
		Jogo.emitir_ruido(corpo.global_position, 12.0, 0.75)
		_tocar("res://assets/sons/lata_batendo.wav", -2.0))
	# Se por algum motivo ela não acusar a batida, faz o barulho onde parou.
	get_tree().create_timer(2.5).timeout.connect(func() -> void:
		if is_instance_valid(corpo) and not bateu[0]:
			bateu[0] = true
			Jogo.emitir_ruido(corpo.global_position, 12.0, 0.75))
	get_tree().create_timer(12.0).timeout.connect(corpo.queue_free)


func latas() -> int:
	return _latas_na_mao


# ---------------------------------------------------------------------------
# Mapa (M), cômodos visitados e para onde ir (V2.2)
# ---------------------------------------------------------------------------

var _mapa: CanvasLayer
var _tempo_visitados := 0.0


func _montar_mapa() -> void:
	const CAMINHO := "res://scripts/v2/mapa_vigia.gd"
	if ResourceLoader.exists(CAMINHO):
		_mapa = load(CAMINHO).new()
		_mapa.name = "MapaVigia"
		add_child(_mapa)


## Onde fica cada "alvo" do objetivo (ver Jogo.objetivo_estruturado()).
func posicao_alvo(alvo: String) -> Variant:
	var mundo := get_tree().get_first_node_in_group("mundo")
	var no: Node3D = null
	match alvo:
		"disjuntor_cozinha", "disjuntor_gerente", "disjuntor_deposito", "disjuntor_eletrica":
			var area: String = {"disjuntor_cozinha": "Cozinha", "disjuntor_gerente": "Gerente",
				"disjuntor_deposito": "Deposito", "disjuntor_eletrica": "Eletrica"}[alvo]
			no = mundo.get_node_or_null("Disjuntores/Disjuntor_" + area) if mundo else null
		"maquina_garra":
			no = _achar("Maquina_Garra")
		"maquina_kart":
			no = _achar("Arcade_Tito_Kart")
		"duto_piratas":
			no = get_node_or_null("Duto_Entrada_Festa_Piratas")
		"alicate":
			no = _achar("Item__alicate")
		"teclado_eletrica":
			no = _achar("Teclado_Eletrica")
		"gerador":
			no = _achar("Gerador_Principal")
		"botao_porta":
			no = _achar("Botao_Porta_Seguranca")
	return no.global_position if no else null


## Os dados que a tela do mapa desenha (contrato em docs/CONTRATOS.md, V2-12).
func dados_mapa() -> Dictionary:
	var jogador := _jogador()
	var d := {"visitados": Jogo.comodos_visitados, "diario": Jogo.diario, "fichas": Jogo.fichas,
		"senha": Jogo.codigo_conhecido(), "marcacao": clampi(Config.dificuldade, 0, 2)}
	if jogador:
		var frente := -jogador.global_basis.z
		d["jogador"] = {"x": jogador.global_position.x + 30.0, "z": jogador.global_position.z + 22.5,
			"angulo": atan2(frente.x, -frente.z)}
	var nomes := {"alicate": "Alicate corta-corrente", "chave_gerente": "Chave do gerente"}
	var itens: Array[String] = []
	for id in Jogo.itens:
		itens.append(String(nomes.get(id, id)))
	d["itens"] = itens
	var disj: Array = []
	for no in get_tree().get_nodes_in_group("disjuntor"):
		var n := no as Node3D
		disj.append({"x": n.global_position.x + 30.0, "z": n.global_position.z + 22.5, "area": no.nome_area, "ligado": no.ligado})
	d["disjuntores"] = disj
	var gerador := _achar("Gerador_Principal")
	if gerador:
		d["gerador"] = {"x": gerador.global_position.x + 30.0, "z": gerador.global_position.z + 22.5, "ligado": Jogo.gerador_esta_ligado}
	var portas: Array = []
	for p in PlantaV2.dados()["portas"]:
		if p["tipo"] in ["livre", "catraca"]:
			continue
		var x: float = p["centro"] if p["eixo"] == "z" else p["fixo"]
		var z: float = p["fixo"] if p["eixo"] == "z" else p["centro"]
		var logica: PortaV2 = null
		var menor := 2.0
		for porta in _portas.values():
			var pos: Vector3 = porta.folha.global_position
			var dist := Vector2(pos.x + 30.0 - x, pos.z + 22.5 - z).length()
			if dist < menor:
				menor = dist
				logica = porta
		portas.append({"x": x, "z": z, "eixo": p["eixo"], "largura": p["largura"], "tipo": p["tipo"],
			"trancada": logica.trancada if logica else false, "aberta": logica.aberta if logica else false})
	d["portas"] = portas
	var o := Jogo.objetivo_estruturado()
	var texto: String = o["titulo"]
	for passo in o["passos"]:
		if passo["atual"]:
			texto = passo["texto"]
	var pos_alvo: Variant = posicao_alvo(o["alvo"])
	if pos_alvo != null:
		var v: Vector3 = pos_alvo
		d["objetivo"] = {"texto": texto, "x": v.x + 30.0, "z": v.z + 22.5, "comodo": PlantaV2.comodo_em(v)}
	else:
		d["objetivo"] = {}
	return d


func _marcar_visitado() -> void:
	var jogador := _jogador()
	if jogador == null:
		return
	var c := PlantaV2.comodo_em(jogador.global_position)
	if c != "" and not Jogo.comodos_visitados.has(c):
		Jogo.comodos_visitados[c] = true
		Jogo.objetivo_mudou.emit(Jogo.objetivo_atual())  # ex.: entrou na oficina -> "pegue o alicate"


# ---------------------------------------------------------------------------
# Guias pelo ambiente: música do fliperama e destaque dos interativos (V2.2)
# ---------------------------------------------------------------------------

## As máquinas tocam a música delas o tempo todo (baixinho): o som leva o vigia até o fliperama.
func _montar_musica_maquinas() -> void:
	for par in [["Maquina_Garra", "res://assets/sons/minigames/garra_musica.wav", -14.0],
			["Arcade_Tito_Kart", "res://assets/sons/minigames/kart_motor.wav", -22.0]]:
		var m := _achar(par[0])
		if m == null or not ResourceLoader.exists(par[1]):
			continue
		var s := AudioStreamPlayer3D.new()
		s.name = "MusicaAtracao"
		s.stream = load(par[1])
		s.volume_db = par[2]
		s.unit_size = 4.0
		s.max_distance = 22.0
		s.bus = &"Efeitos"
		m.add_child(s)
		s.position = Vector3(0, 1.6, 0.3)
		s.finished.connect(s.play)
		s.play()


## Brilho sutil + ícone em tudo que é interativo/coletável (itens-chave mais fortes).
func _montar_destaques() -> void:
	var chave := Color(1.0, 0.82, 0.3)
	var comum := Color(0.75, 0.9, 1.0)
	var lista: Array = []
	for nome in ["Item__alicate", "Teclado_Eletrica", "Gerador_Principal", "Botao_Porta_Seguranca", "Maquina_Garra",
			"Arcade_Tito_Kart", "Secretaria_Eletronica", "Pista__recado_gerente"]:
		var n := _achar(nome)
		if n:
			lista.append([n, chave, 1.0])
	for nome in ["Pista__aniversario", "Pista__quadro_avisos", "Arcade_Space_Pizza"]:
		var n := _achar(nome)
		if n:
			lista.append([n, comum, 0.6])
	var mundo := get_tree().get_first_node_in_group("mundo")
	if mundo:
		for d in mundo.get_node("Disjuntores").get_children():
			lista.append([d, chave, 1.0])
	for f in get_tree().get_nodes_in_group("ficha"):
		lista.append([f, chave, 0.8])
	for f in get_tree().get_nodes_in_group("pilha"):
		lista.append([f, comum, 0.8])
	for f in get_tree().get_nodes_in_group("duto_grade"):
		lista.append([f, comum, 0.7])
	for item in lista:
		Destaque.colocar(item[0], item[1], item[2], _condicao_destaque(item[0]))


## Quando o destaque de cada coisa deixa de fazer sentido.
func _condicao_destaque(no: Node3D) -> Callable:
	if no.is_in_group("disjuntor"):
		return func() -> bool: return not no.ligado
	match String(no.name):
		"Gerador_Principal":
			return func() -> bool: return not Jogo.gerador_esta_ligado
		"Teclado_Eletrica":
			return func() -> bool: return _portas.has("eletrica") and _portas["eletrica"].trancada
		"Botao_Porta_Seguranca":
			return func() -> bool: return Jogo.gerador_esta_ligado and not Jogo.porta_seguranca_fechada
		"Maquina_Garra":
			return func() -> bool: return not Jogo.tem_item("chave_gerente")
		"Arcade_Tito_Kart":
			return func() -> bool: return not (Jogo.digitos_conhecidos[0] and Jogo.digitos_conhecidos[1])
		"Secretaria_Eletronica":
			return func() -> bool: return Jogo.diario.is_empty()
	return Callable()


# ---------------------------------------------------------------------------

func _process(delta: float) -> void:
	_tempo_visitados -= delta
	if _tempo_visitados <= 0.0:
		_tempo_visitados = 0.5
		_marcar_visitado()
	_atualizar_legenda()
	_verificar_fichas(delta)
	# Máquina ligada faz barulho: os animatrônicos ouvem quem está jogando.
	if _minigame != null and is_instance_valid(_minigame):
		_tempo_ruido_minigame -= delta
		if _tempo_ruido_minigame <= 0.0:
			_tempo_ruido_minigame = 1.0
			var i := _minigame.intensidade_ruido
			Jogo.emitir_ruido(_posicao_minigame, 4.0 + 12.0 * i, i)


func _unhandled_input(evento: InputEvent) -> void:
	var jogador := _jogador()
	if jogador == null:
		return
	if evento.is_action_pressed("arremessar"):
		arremessar_lata()
