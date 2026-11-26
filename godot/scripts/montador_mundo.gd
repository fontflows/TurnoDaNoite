extends Node
## Monta o mundo da V2 a partir dos MARCADORES que vêm do Blender (nomes com "__"):
##   Arte__<nome>     -> pôster/letreiro com a arte do Gemini (ou feita por código), envelhecida
##   Luz__<tipo>_NN   -> uma luz pronta (fluorescente, emergência, neon, abajur, holofote, claraboia, tela)
##   Som__<tipo>_NN   -> som 3D em loop (goteira, zumbido, rádio...)
##   Decal__<tipo>_NN -> mancha projetada (água, gordura, pegadas, confete...)
##   Disjuntor_<Area> -> a lógica do disjuntor (cena cenas/objetos/disjuntor.tscn)
##   Esconderijo__ / Item__ / Pista__ -> entram em grupos para a lógica da V2.5
##   Porta__<tipo>__<id>, máquinas, gerador... -> a lógica fica em scripts/v2/progressao_v2.gd
##
## Por que assim: o mapa inteiro sai do Blender. Mudou um móvel ou uma luz de lugar no
## script do Blender? Reexporte e pronto: o Godot monta tudo de novo sozinho.
##
## Energia: fluorescentes, neons e telas de cada cômodo só acendem quando o disjuntor
## daquele cômodo é religado (tabela ENERGIA em blender/scripts/planta_v2.py).

## Nó que contém os .glb do cenário (prédio + móveis).
@export var cenario: NodePath
## Onde a lógica dos disjuntores é criada.
@export var pasta_disjuntores: NodePath
## Senha fixa da sala elétrica (para testar ou apresentar). Vazio = sorteada a cada partida.
@export var codigo_fixo := ""

const PLANTA := "res://assets/dados/planta_v2.json"
const CENA_DISJUNTOR := preload("res://cenas/objetos/disjuntor.tscn")
const LUZ_PISCANTE := preload("res://scripts/luz_piscante.gd")

## Aparência de cada tipo de luz. Mude aqui para mudar todas as luzes daquele tipo.
const PRESETS := {
	"fluorescente": {"cor": Color(0.85, 0.95, 1.0), "energia": 1.1, "alcance": 5.5, "piscar": 0.5},
	"emergencia": {"cor": Color(1.0, 0.15, 0.1), "energia": 0.45, "alcance": 2.5},
	"neon_rosa": {"cor": Color(1.0, 0.25, 0.65), "energia": 0.9, "alcance": 3.5},
	"neon_ciano": {"cor": Color(0.25, 0.9, 1.0), "energia": 0.9, "alcance": 3.5},
	"neon_amarelo": {"cor": Color(1.0, 0.85, 0.25), "energia": 0.9, "alcance": 3.5},
	"abajur": {"cor": Color(1.0, 0.72, 0.42), "energia": 0.8, "alcance": 3.0},
	"tela": {"cor": Color(0.45, 0.75, 1.0), "energia": 0.35, "alcance": 2.0},
	"holofote": {"cor": Color(1.0, 0.85, 0.6), "energia": 3.0, "alcance": 14.0, "spot": 20.0},
	"claraboia": {"cor": Color(0.55, 0.68, 1.0), "energia": 2.6, "alcance": 6.0, "spot": 24.0, "para_baixo": true},
}
## Tipos que não dependem de disjuntor (bateria de emergência, luar, abajur do vigia).
const SEMPRE_ACESAS := ["emergencia", "claraboia", "abajur"]
## Sons disponíveis para cada tipo (os que ainda não existem são pulados).
const SONS := {"zumbido": "zumbido_lampada", "radio": "estatica", "goteira": "goteira", "rangido": "rangido",
	"ventilacao": "ventilacao", "geladeira": "geladeira", "bipes": "bipes", "vento": "vento"}

var _planta := {}
## id da energia ("cozinha", "deposito", ..., "gerador") -> nós que acendem com ela
var _por_energia := {}
var _arte: ArteExterna
var progressao: ProgressaoV2


func _ready() -> void:
	# Primeiro zera a partida e sorteia a senha: o pôster da festa e o quadro de avisos mostram dígitos dela.
	Jogo.preparar_partida_v2(codigo_fixo)
	_planta = JSON.parse_string(FileAccess.get_file_as_string(PLANTA))
	_arte = ArteExterna.new()
	_arte.name = "ArteExterna"
	add_child(_arte)
	var raiz := get_node(cenario)
	var semente := 0.0
	for no in raiz.find_children("*", "", true, false):
		var n := String(no.name)
		if n.begins_with("Arte__") and no is MeshInstance3D:
			semente += 1.37
			_arte.aplicar(no, semente)  # assíncrono: as artes aparecem nos primeiros quadros
		elif n.begins_with("Luz__"):
			_criar_luz(no, _tipo(n, "Luz__"))
		elif n.begins_with("Som__"):
			_criar_som(no, _tipo(n, "Som__"))
		elif n.begins_with("Decal__"):
			_criar_decal(no, _tipo(n, "Decal__"))
		elif n.begins_with("Esconderijo__"):
			no.add_to_group("esconderijo")
			no.set_meta("tipo", _tipo(n, "Esconderijo__"))
		elif n.begins_with("Item__"):
			no.add_to_group("item_chave")
			no.set_meta("id_item", n.trim_prefix("Item__"))
		elif n.begins_with("Pista__"):
			no.add_to_group("pista_codigo")
			no.set_meta("id_pista", n.trim_prefix("Pista__"))
		elif n.begins_with("Disjuntor_") and n.count("_") == 1:
			_criar_disjuntor(no as Node3D, raiz)
		elif n.ends_with("_Tela") and n.begins_with("Arcade_"):
			_registrar_energia(no, "")
	# Cadeia de progressão (portas, itens, máquinas, gerador, dutos, esconderijos...).
	progressao = ProgressaoV2.new()
	progressao.name = "ProgressaoV2"
	progressao.montador = self
	add_child(progressao)
	progressao.montar(raiz, get_parent())


## "Luz__neon_rosa_02" -> "neon_rosa"
func _tipo(nome: String, prefixo: String) -> String:
	var t := nome.trim_prefix(prefixo)
	var partes := t.rsplit("_", true, 1)
	return partes[0] if partes.size() == 2 and partes[1].is_valid_int() else t


## Em qual cômodo fica um ponto do mundo (pela planta). Godot: x = X + 30, z = Z + 22,5.
func comodo_em(pos: Vector3) -> String:
	var x := pos.x + 30.0
	var z := pos.z + 22.5
	for c in _planta["comodos"]:
		if x >= c["x0"] and x <= c["x1"] and z >= c["z0"] and z <= c["z1"]:
			return c["nome"]
	return ""


func _energia_do_comodo(comodo: String) -> String:
	for id in _planta["energia"]:
		if comodo in _planta["energia"][id]:
			return id
	return ""


## Guarda o nó para acender quando a energia do cômodo dele voltar.
func _registrar_energia(no: Node, forcar_id: String) -> void:
	var id := forcar_id if forcar_id != "" else _energia_do_comodo(comodo_em(no.global_position))
	if id == "":
		return
	_por_energia.get_or_add(id, []).append(no)
	if no is Light3D:
		no.visible = false
		if "ativa" in no:
			no.ativa = false


func _criar_luz(marcador: Node3D, tipo: String) -> void:
	var p: Dictionary = PRESETS.get(tipo, PRESETS["fluorescente"])
	var luz: Light3D
	if p.has("spot"):
		var s := SpotLight3D.new()
		s.spot_range = p["alcance"]
		s.spot_angle = p["spot"]
		s.spot_angle_attenuation = 2.0
		luz = s
	else:
		var o := OmniLight3D.new()
		o.omni_range = p["alcance"]
		o.omni_attenuation = 1.6
		luz = o
	luz.light_color = p["cor"]
	luz.light_energy = p["energia"]
	luz.shadow_enabled = false  # sombra só na lanterna (PC fraco)
	luz.add_to_group("fonte_luz_ilha")
	if p.has("piscar"):
		luz.set_script(LUZ_PISCANTE)
		luz.chance_falha_por_segundo = p["piscar"]
	marcador.add_child(luz)
	if p.get("para_baixo", false):
		luz.global_basis = Basis.looking_at(Vector3.DOWN, Vector3.FORWARD)
	if tipo in SEMPRE_ACESAS:
		return
	_registrar_energia(luz, "gerador" if tipo == "holofote" else "")


func _criar_som(marcador: Node3D, tipo: String) -> void:
	var caminho := "res://assets/sons/%s.wav" % SONS.get(tipo, tipo)
	# Versão externa (docs/PROMPTS_AUDIO.md), se existir: ex.: efeitos/goteira_loop.mp3
	var externo: String = {"goteira": "goteira_loop", "ventilacao": "ventilacao_loop", "geladeira": "geladeira_loop",
		"vento": "vento_loop", "zumbido": "zumbido_lampada_loop"}.get(tipo, "")
	var stream: AudioStream = SomExterno.efeito(externo, caminho) if externo != "" else (load(caminho) as AudioStream if ResourceLoader.exists(caminho) else null)
	if stream == null:
		return  # sem som para este tipo: fica em silêncio
	var s := AudioStreamPlayer3D.new()
	s.stream = stream
	s.volume_db = -10.0
	s.unit_size = 2.5
	s.max_distance = 14.0
	s.autoplay = true
	marcador.add_child(s)


func _criar_decal(marcador: Node3D, tipo: String) -> void:
	if not QualidadeGrafica.decals_ligados(Config.qualidade):
		return  # decals só existem no renderer completo e na qualidade Média/Alta
	var caminho := "res://assets/texturas/decals/decal_%s.png" % tipo
	if not ResourceLoader.exists(caminho):
		return
	var d := Decal.new()
	d.texture_albedo = load(caminho)
	d.size = marcador.global_basis.get_scale().abs().max(Vector3(0.05, 0.05, 0.05))
	d.upper_fade = 0.2
	d.lower_fade = 0.2
	marcador.add_child(d)
	d.global_basis = marcador.global_basis.orthonormalized()


func _criar_disjuntor(modelo: Node3D, raiz: Node) -> void:
	var area := String(modelo.name).trim_prefix("Disjuntor_")
	var logica := CENA_DISJUNTOR.instantiate()
	logica.name = "Disjuntor_" + area
	logica.nome_modelo = String(modelo.name)
	logica.nome_area = {"Eletrica": "Sala elétrica", "Deposito": "Depósito", "Gerente": "Sala do gerente"}.get(area, area)
	# Cozinha: fios soltos; Gerente: fusível queimado (minigame de conserto antes de religar).
	logica.conserto = {"Cozinha": "fios", "Gerente": "fusivel"}.get(area, "")
	get_node(pasta_disjuntores).add_child(logica)
	logica.modelos = logica.get_path_to(raiz)
	logica._ready()  # já entrou na árvore antes de saber o modelo: liga de novo agora
	logica.religado.connect(ligar_energia)


## Acende tudo o que depende desta energia (chamado quando um disjuntor é religado).
func ligar_energia(id: String) -> void:
	for no in _por_energia.get(id, []):
		if no is Light3D:
			if no.has_method("acender"):
				no.acender()
			else:
				no.visible = true
		elif no is MeshInstance3D:
			# Tela de máquina: acende com um brilho (o modo demonstração vem na V2.5).
			var m := StandardMaterial3D.new()
			m.albedo_color = Color(0.1, 0.2, 0.3)
			m.emission_enabled = true
			m.emission = Color.from_hsv(randf(), 0.7, 1.0)
			m.emission_energy_multiplier = 1.5
			no.material_override = m
