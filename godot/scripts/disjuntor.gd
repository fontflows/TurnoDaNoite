extends Area3D
## Lógica de um disjuntor. O MODELO (caixa + alavanca) vem do Blender, no arquivo
## assets/cenario/disjuntores.glb. Esta cena só guarda a lógica e "gruda" no modelo.
##
## Por que separado: se o modelo for reexportado do Blender, nada desta lógica se perde.
## A posição do disjuntor é a do Blender (para mudar de lugar, mova lá e reexporte).

## Avisa qual área foi religada ("cozinha", "deposito", ...), para acender as luzes dela.
signal religado(id_area: String)

@export_group("Disjuntor")
## Nome da área (aparece na dica: "religar o disjuntor (Cozinha)").
@export var nome_area := "Cozinha"
## Nome do objeto do disjuntor no Blender (o mesmo nome aparece no .glb).
@export var nome_modelo := "Disjuntor_Cozinha"
## Nó onde o disjuntores.glb foi colocado na cena do mundo.
@export var modelos: NodePath
## Luzes que acendem quando este disjuntor é religado.
@export var luzes_da_area: Array[NodePath] = []

## "" = religa direto. "fios" ou "fusivel" = antes é preciso vencer o minigame de conserto (V2).
@export var conserto := ""

@export_group("Animação")
## Ângulo (graus) da alavanca depois de ligada. Desligada ela fica em -40.
@export var angulo_ligado := 40.0
## Duração (s) do movimento da alavanca.
@export var duracao_animacao := 0.35

var ligado := false
var consertado := false
var _modelo: Node3D
var _alavanca: Node3D
var _led: MeshInstance3D

@onready var som: AudioStreamPlayer3D = $Som


func _ready() -> void:
	add_to_group("disjuntor")
	add_to_group("interagivel")
	if modelos.is_empty():
		return  # na V2 o montador do mundo define o modelo e chama _ready de novo
	var raiz := get_node_or_null(modelos)
	if raiz:
		_modelo = raiz.find_child(nome_modelo, true, false) as Node3D
	if _modelo == null:
		push_warning("Disjuntor '%s': modelo '%s' não encontrado no .glb." % [name, nome_modelo])
		return
	# Fica exatamente onde o modelo está (posição e rotação vindas do Blender).
	global_transform = _modelo.global_transform
	_alavanca = _modelo.find_child(nome_modelo + "_Alavanca", true, false) as Node3D
	_led = _modelo.find_child(nome_modelo + "_Led", true, false) as MeshInstance3D


func texto_dica() -> String:
	if ligado:
		return "Disjuntor (%s): ligado" % nome_area
	if conserto != "" and not consertado:
		return "Aperte E para consertar o disjuntor (%s): %s" % [nome_area, "fios soltos" if conserto == "fios" else "fusível queimado"]
	return "Aperte E para religar o disjuntor (%s)" % nome_area


func interagir(_jogador: Node) -> void:
	if ligado:
		return
	if conserto != "" and not consertado:
		var progressao := get_tree().get_first_node_in_group("progressao_v2")
		if progressao:
			progressao.abrir_minigame("conserto", {"modo": conserto}, global_position, func(venceu: bool, _r: Dictionary) -> void:
				if venceu:
					consertado = true
					ligar())
			return
	ligar()


func ligar() -> void:
	if ligado:
		return
	ligado = true
	if _alavanca:
		var giro := create_tween().set_trans(Tween.TRANS_BACK).set_ease(Tween.EASE_OUT)
		giro.tween_property(_alavanca, "rotation:x", deg_to_rad(angulo_ligado), duracao_animacao)
	if _led:
		# LED fica verde para mostrar que está ligado.
		var verde := StandardMaterial3D.new()
		verde.albedo_color = Color(0.2, 1.0, 0.3)
		verde.emission_enabled = true
		verde.emission = Color(0.2, 1.0, 0.3)
		verde.emission_energy_multiplier = 2.0
		_led.material_override = verde
	var externo := SomExterno.efeito("disjuntor_clique")
	if externo:
		som.stream = externo
	som.play()
	for caminho in luzes_da_area:
		var luz := get_node_or_null(caminho)
		if luz and luz.has_method("acender"):
			luz.acender()
	religado.emit(nome_modelo.trim_prefix("Disjuntor_").to_lower())
	Jogo.registrar_disjuntor(nome_modelo.trim_prefix("Disjuntor_").to_lower())
