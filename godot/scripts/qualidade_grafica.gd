class_name QualidadeGrafica
## Presets de qualidade gráfica (Baixa / Média / Alta).
## Liga e desliga os efeitos caros. No modo de compatibilidade (OpenGL), os efeitos
## que não existem lá são simplesmente ignorados pelo Godot, sem erro.
##
## Regra do projeto: nenhuma mecânica depende de um efeito daqui (ex.: nada fica
## escondido só na névoa volumétrica), então a Baixa continua jogável.

## Tamanho do "atlas" de sombras de luzes pontuais (lanterna, luzes piscando).
const SOMBRAS := [1024, 2048, 4096]
## Densidade relativa das partículas (poeira no ar etc.).
const PARTICULAS := [0.0, 0.6, 1.0]


## true se o jogo está rodando no renderer completo (Forward+). No fallback OpenGL, false.
static func eh_forward_plus() -> bool:
	return RenderingServer.get_current_rendering_method() == "forward_plus"


static func aplicar_viewport(vp: Viewport, nivel: int) -> void:
	vp.positional_shadow_atlas_size = SOMBRAS[nivel]
	vp.msaa_3d = Viewport.MSAA_2X if nivel == Config.Qualidade.ALTA else Viewport.MSAA_DISABLED
	vp.screen_space_aa = Viewport.SCREEN_SPACE_AA_FXAA if nivel == Config.Qualidade.MEDIA else Viewport.SCREEN_SPACE_AA_DISABLED
	RenderingServer.directional_shadow_atlas_set_size(SOMBRAS[nivel], true)


## Aplica o preset num Environment (o da cena do mundo ou do menu).
static func aplicar_ambiente(amb: Environment, nivel: int) -> void:
	if amb == null:
		return
	amb.ssao_enabled = nivel == Config.Qualidade.ALTA
	amb.glow_enabled = nivel >= Config.Qualidade.MEDIA
	amb.volumetric_fog_enabled = nivel >= Config.Qualidade.MEDIA
	amb.sdfgi_enabled = false  # caro demais para o PC do laboratório; a luz assada cuida disso


## Quantas partículas usar (multiplica o "amount" dos emissores de poeira).
static func fator_particulas(nivel: int) -> float:
	return PARTICULAS[nivel]


## Decals (manchas no chão e nas paredes) só na Média e Alta.
static func decals_ligados(nivel: int) -> bool:
	return nivel >= Config.Qualidade.MEDIA and eh_forward_plus()
