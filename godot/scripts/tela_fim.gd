extends Control
## Tela de fim de partida (Game Over ou Vitória). A mesma lógica serve para as duas:
## o texto muda conforme o que aconteceu (lido do autoload Jogo).

## true = tela de vitória; false = tela de Game Over.
@export var eh_vitoria := false

@onready var titulo: Label = %Titulo
@onready var subtitulo: Label = %Subtitulo
@onready var detalhe: Label = %Detalhe
@onready var botao_de_novo: Button = %BotaoDeNovo
@onready var botao_menu: Button = %BotaoMenu
@onready var som: AudioStreamPlayer = $Som


func _ready() -> void:
	Input.mouse_mode = Input.MOUSE_MODE_VISIBLE
	botao_de_novo.pressed.connect(Jogo.reiniciar_partida)
	botao_menu.pressed.connect(Jogo.ir_para_menu)
	botao_de_novo.grab_focus()
	if eh_vitoria:
		titulo.text = "06:00 AM"
		subtitulo.text = "Você sobreviveu ao turno!"
		var segundos := int(Jogo.tempo_total)
		detalhe.text = "Tempo levado: %d min %02d s  ·  Disjuntores: %d/%d" % [
			segundos / 60, segundos % 60, Jogo.disjuntores_ligados, Jogo.total_disjuntores]
		if Jogo.usa_gerador:
			detalhe.text = _relatorio_v2(segundos)
	elif Jogo.motivo_derrota == "tempo":
		titulo.text = "06:00 AM"
		subtitulo.text = "O gerente chegou... e você foi demitido!"
		detalhe.text = "Os disjuntores não foram religados a tempo (%d/%d)." % [
			Jogo.disjuntores_ligados, Jogo.total_disjuntores]
	else:
		titulo.text = "FIM DE TURNO"
		var quem := Jogo.quem_pegou if Jogo.quem_pegou != "" else "Alguém"
		subtitulo.text = "%s te pegou!" % quem
		detalhe.text = "Hora: %s  ·  Disjuntores: %d/%d" % [
			Jogo.texto_relogio(), Jogo.disjuntores_ligados, Jogo.total_disjuntores]
	# Entrada suave do texto.
	if not eh_vitoria and Jogo.dificuldade and Jogo.dificuldade.checkpoint_por_disjuntor and not Jogo.checkpoint.is_empty():
		detalhe.text += "\n(Fácil: \"Tentar de novo\" continua do último disjuntor religado)"
	modulate.a = 0.0
	create_tween().tween_property(self, "modulate:a", 1.0, 0.6)
	som.play()


## Relatório do turno (V2): como foi a noite e a "avaliação do gerente".
func _relatorio_v2(segundos: int) -> String:
	var e := Jogo.estatisticas
	var estrelas := 3 - mini(Jogo.derrotas_na_noite, 2)
	var nome := Jogo.dificuldade.nome if Jogo.dificuldade else ""
	var linhas: Array[String] = [
		"Dificuldade: %s  ·  Tempo: %d min %02d s  ·  Derrotas nesta noite: %d" % [nome, segundos / 60, segundos % 60, Jogo.derrotas_na_noite],
		"Fichas achadas: %d  ·  Tentativas na garra: %d  ·  no TITO KART: %d" % [e.get("fichas", 0), e.get("tentativas_garra", 0), e.get("tentativas_kart", 0)],
		"Vezes escondido: %d  ·  Pilhas usadas: %d  ·  Latas jogadas: %d  ·  Barulhos altos: %d" % [
			e.get("escondido", 0), e.get("pilhas", 0), e.get("latas", 0), e.get("barulhos_altos", 0)],
		"",
		"Avaliação do gerente: %s%s" % ["★".repeat(estrelas), "☆".repeat(3 - estrelas)],
	]
	if estrelas == 3:
		linhas.append("FUNCIONÁRIO DO MÊS! (tiraram a foto antiga do quadro)")
	return "\n".join(linhas)
