class_name Dificuldade
extends Resource
## Todos os números de balanceamento de uma dificuldade, num lugar só.
## Os arquivos ficam em assets/dificuldade/ (facil.tres, normal.tres, pesadelo.tres):
## dê dois cliques num deles no Godot e mude os valores no Inspetor.

@export var nome := "Normal"

@export_group("Noite")
## Segundos reais de cada hora do jogo (a noite tem 6 horas).
@export var segundos_por_hora := 120.0
## Recomeçar do último disjuntor ligado depois de perder.
@export var checkpoint_por_disjuntor := false

## Multiplica a luz ambiente do mapa (o "luar"). Fácil um pouco mais claro para quem está aprendendo.
@export_range(0.5, 2.5) var luz_ambiente := 1.0

@export_group("Lanterna e pilhas")
## Quantos segundos a lanterna dura ligada direto, com a bateria cheia.
@export var duracao_bateria_s := 90.0
## Quantas pilhas existem no mapa inteiro.
@export var pilhas_no_mapa := 3
## Quanto cada pilha recarrega (40 = +40%).
@export var recarga_pilha := 40.0
## Abaixo desta porcentagem, a lanterna perde alcance e força aos poucos.
@export var bateria_fraca := 30.0
## Abaixo desta porcentagem, a lanterna falha.
@export var bateria_falhando := 15.0

@export_group("Corpo do vigia")
## Segundos de corrida contínua até a stamina acabar.
@export var duracao_stamina_s := 5.5

@export_group("Fichas e minigames")
## Fichas espalhadas pelo mapa (cada tentativa de garra ou kart gasta 1).
@export var fichas_no_mapa := 5
## Fichas que o vigia já tem no bolso quando a noite começa (menos procura no escuro).
@export var fichas_iniciais := 1
## Segundos para reaparecer uma ficha se o jogador ficar sem nenhuma (evita travar a partida).
@export var reaparecer_ficha_s := 90.0
## Força da garra (0 = frouxa, 1 = forte). Garra forte quase nunca derruba o prêmio.
@export_range(0.0, 1.0) var forca_garra := 0.6
## Segundos para jogar a garra por ficha.
@export var tempo_garra_s := 20.0
## Velocidade dos carrinhos rivais no TITO KART (1 = normal).
@export var velocidade_rivais_kart := 1.0
## Embaralhar os fios do disjuntor a cada tentativa.
@export var embaralhar_fios := false

@export_group("Animatrônicos")
## Multiplica as velocidades dos animatrônicos (1 = como está na cena).
@export var multiplicador_velocidade := 1.0
## Multiplica o alcance de visão e audição.
@export var multiplicador_sentidos := 1.0
## Chance (0 a 1) de um animatrônico checar o esconderijo onde o vigia está.
@export_range(0.0, 1.0) var chance_checar_esconderijo := 0.4
## Quão ativo é o "diretor de tensão" (0 = desligado, 1 = bem insistente).
@export_range(0.0, 1.0) var intensidade_diretor := 0.5

@export_group("Itens")
## 0 = posições fixas; 1 = pilhas e fichas sorteadas; 2 = tudo sorteado (alicate e pistas também).
@export_range(0, 2) var nivel_sorteio := 1
