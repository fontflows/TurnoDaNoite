extends CanvasLayer
## Autoload "FiltroVHS": desenha o filtro de tela VHS por cima de TUDO (jogo e menus).
## Ele também aplica o brilho (gamma) escolhido nas opções.
## Os valores vêm do autoload Config; aqui só repassamos para o shader.

@onready var tela: ColorRect = $Tela


func _ready() -> void:
	# Fica acima de todas as outras camadas e continua funcionando com o jogo pausado.
	layer = 100
	process_mode = Node.PROCESS_MODE_ALWAYS
	Config.mudou.connect(aplicar)
	aplicar()


## Lê as opções atuais e atualiza o shader.
func aplicar() -> void:
	var material := tela.material as ShaderMaterial
	var intensidade := Config.vhs_intensidade if Config.vhs_ativo else 0.0
	material.set_shader_parameter("intensidade", intensidade)
	material.set_shader_parameter("gamma", Config.brilho)
	# Sem VHS e com brilho normal o filtro não muda nada: escondemos para economizar
	# processamento (importante no PC fraco do laboratório).
	tela.visible = intensidade > 0.001 or absf(Config.brilho - 1.0) > 0.001
