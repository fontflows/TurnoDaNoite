# Turno da Noite: Pizzaria do Tito

Jogo de terror leve em primeira pessoa, feito para a disciplina de Computação Gráfica.
Cenário e personagens modelados no **Blender** (gerados por scripts Python); jogo feito no **Godot 4** (GDScript, renderer **Forward+** com volta automática para OpenGL em PCs sem Vulkan/D3D12).

> Você é o vigia noturno da Pizzaria do Tito. À meia-noite a energia cai e os animatrônicos Tito (urso) e Pipoca (coelha) começam a andar. Religue os 4 disjuntores, ligue o gerador principal e volte correndo para a sala de segurança para fechar a porta de aço antes que eles te alcancem.

- Design do jogo: [`docs/GDD.md`](docs/GDD.md) (V1) e [`docs/PLANO_V2.md`](docs/PLANO_V2.md) (mapa novo, cadeia de progressão, dificuldade)
- **Guia para a apresentação** (Blender e Godot do zero): [`docs/GUIA_APRESENTACAO.md`](docs/GUIA_APRESENTACAO.md)
- Padrão para os personagens finais: [`docs/PADRAO_PERSONAGENS.md`](docs/PADRAO_PERSONAGENS.md)
- Contratos técnicos (nomes, posições, sinais): [`docs/CONTRATOS.md`](docs/CONTRATOS.md)
- Artes 2D (pôsteres, capas, letreiros): [`docs/PROMPTS_ARTE.md`](docs/PROMPTS_ARTE.md) · Créditos: [`docs/CREDITOS.md`](docs/CREDITOS.md)
- Voz e efeitos sonoros externos: [`docs/PROMPTS_AUDIO.md`](docs/PROMPTS_AUDIO.md) — efeitos sonoros gerados na ElevenLabs: crédito **elevenlabs.io**
- Acompanhamento das fases com imagens: `docs/progresso/index.html`

## Versões usadas

| Programa | Versão |
|---|---|
| Godot | **4.7.2** (padrão, não .NET) |
| Blender | **5.3.0** |
| Python | 3 com numpy (só para gerar os sons) |

## Controles

| Ação | Tecla |
|---|---|
| Andar / correr | W A S D / Shift (gasta fôlego) |
| Olhar | mouse |
| Agachar | Ctrl (segurar) |
| Prender a respiração | Alt (segurar) |
| Lanterna / sacudir a lanterna fraca | F / R |
| Interagir (portas, disjuntores, itens, máquinas, esconderijos, dutos) | E |
| Arremessar lata | G |
| Inventário / acender o painel de objetivo | Tab (segurar) / O |
| Mapa e diário do vigia | M |
| Trocar câmera no monitor | Q |
| Minigames | W A S D + Espaço · ESC ou E sai |
| Pausa / sair do monitor | ESC |
| Tela cheia | F11 |
| Debug (começa DESLIGADO: **Ctrl+Shift+D** liga/desliga, ou abra o jogo com `-- debug`) | **F9 abre o painel com todos os atalhos** · F1 +1 hora · F2 disjuntores · F3 invencível · F4 IA · F5 bateria · F6 fichas · F7 vence o minigame · F8 luz · F10 próximo cômodo · F12 navegação e ruídos · Shift+F1 congelar animatrônicos · Shift+F2 fôlego infinito · Shift+F3 bateria infinita · Shift+F4 itens e senha · Shift+F5 modo observação (animatrônicos ignoram o vigia) |

## Jogar sem instalar nada

- **Windows:** `builds/windows/TurnoDaNoite.exe`
- **Linux:** `builds/linux/TurnoDaNoite.x86_64`
  Se não abrir com dois cliques, abra um terminal nessa pasta e rode:
  ```
  chmod +x TurnoDaNoite.x86_64
  ./TurnoDaNoite.x86_64
  ```

## Abrir o projeto no Godot

1. Abra o Godot 4.7.2 → **Importar** → escolha `godot/project.godot` → **Importar e Editar**.
2. Na primeira vez ele importa os modelos, texturas e sons (pode levar um minuto).
3. **F5** roda o jogo a partir do menu. Para ir direto ao mapa, abra `cenas/mundo_v2.tscn` e aperte **F6**.
   (O mapa antigo da V1 continua em `cenas/mundo.tscn`, usado só por alguns testes.)

## Regenerar o conteúdo do Blender (mapa da V2)

Tudo é gerado por script. Na pasta `TurnoDaNoite`, nesta ordem:

```
python blender/scripts/planta_v2.py --json                              (planta -> godot/assets/dados/planta_v2.json)
blender --background --python blender/scripts/gerar_predio_v2.py        (paredes, pisos, portas)
blender --background --python blender/scripts/moveis_v2_publico.py      (salão, cozinha, recepção, festas...)
blender --background --python blender/scripts/moveis_v2_diversao.py     (fliperama, palco, máquinas)
blender --background --python blender/scripts/moveis_v2_servico.py      (segurança, oficina, depósito, elétrica, gerente...)
blender --background --python blender/scripts/moveis_v2_enchimento.py   (acha e enche espaços vazios grandes)
python ferramentas/gerar_materiais_godot.py                             (materiais editáveis do Godot + docs/progresso/relatorio_materiais.txt)
python ferramentas/gerar_mundo_v2.py --forcar                           (cena cenas/mundo_v2.tscn)
```

O Godot reimporta sozinho; a lógica (portas, máquinas, luzes, sons...) é montada em tempo de execução a partir dos **nomes** dos objetos do Blender, então nada se perde.

- Mudanças de cor permanentes: `blender/scripts/comum.py` (`CORES`) e `materiais_v2.py` (`TEXTURIZADOS`).
- Todo material precisa ter textura (`materiais_v2.TEXTURIZADOS`) ou estar na lista `LISOS` (cor lisa de propósito: telas, luzes, vidro, letras). O `gerar_materiais_godot.py` lista os que faltam.
- Texturas feitas por script (papel, papelão, cortiça, tecido, carpete...): `blender --background --factory-startup --python ferramentas/gerar_texturas.py` (ou `... -- papel tecido` para gerar só algumas).
- Personagens provisórios e o mapa da V1: `blender --background --python blender/scripts/gerar_tudo.py`.
- Sons: `python ferramentas/gerar_sons.py`, `gerar_sons_v25.py`, `gerar_sons_v27.py`, `gerar_sons_kart.py`, `gerar_sons_garra_conserto.py`; recado da secretária (Windows): `python ferramentas/gerar_secretaria.py`.
- Artes 2D: coloque as imagens nas pastas de `godot/assets/arte_externa/` e confira com `python ferramentas/verificar_arte.py`.
- Ícone do jogo (janela, barra de tarefas e o `.exe`): `python ferramentas/gerar_icone.py` (usa a ARTE-33 se existir; senão recorta o Tito da capa) e exporte de novo. A capa sombria do menu (ARTE-25, `menu/menu_fundo_sombrio.jpg`) é opcional: sem ela, o shader escurece a capa normal.

## Exportar (builds)

Presets prontos em `godot/export_presets.cfg` (Windows Desktop e Linux, `.pck` embutido; a pasta `dev/` fica de fora, e `docs/` está fora do projeto).
Precisa dos *export templates* do Godot 4.7.2 (no editor: **Editor → Gerenciar Modelos de Exportação**).

No editor: **Projeto → Exportar...** → escolha o preset → **Exportar Projeto**.
Pelo terminal (na pasta `godot`):
```
godot --headless --export-release "Windows Desktop" ../builds/windows/TurnoDaNoite.exe
godot --headless --export-release "Linux" ../builds/linux/TurnoDaNoite.x86_64
```

## Testes automáticos (ferramentas de desenvolvimento)

Na pasta `godot` (não entram no build):

| Comando | Confere |
|---|---|
| `godot --headless --path . res://dev/validar.tscn` | todos os scripts e cenas carregam sem erro |
| `godot --headless --path . res://dev/validar_progressao.tscn` | **a noite pode ser vencida nas 3 dificuldades** (grava `docs/progresso/relatorio_progressao.txt`) |
| `godot --headless --path . res://dev/teste_cadeia.tscn -- dificuldade=1` | joga a cadeia inteira sem inimigos: disjuntores, fichas, garra, kart, pistas, duto, alicate, senha, gerador, porta de aço |
| `godot --headless --path . res://dev/teste_ia_v2.tscn` | visão/audição da Pipoca, portas, esconderijos, Tito no escuro, gerador, diretor de tensão, checkpoint |
| `godot --headless --path . res://dev/teste_esconderijos.tscn` | todos os esconderijos: entrar com E, vista de dentro, Pipoca sem ter visto não acha, sair para um ponto livre |
| `godot --headless --path . res://dev/estimar_tempo.tscn` | tempo do caminho crítico (grava `docs/progresso/relatorio_tempo.txt`) |
| `godot --headless --path . res://dev/medir_audio_externo.tscn` | volume dos áudios externos (o `verificar_audio.py` já chama) |
| `godot --headless --path . res://dev/teste_mapa.tscn` | um robô anda até todos os pontos do mapa sem atravessar paredes nem cair |
| `godot --headless --path . res://dev/teste_minigames.tscn` | contrato dos 4 minigames (vencer, sair) nas 3 dificuldades |
| `godot --headless --path . res://dev/teste_kart.tscn` e `teste_garra_conserto.tscn` | os minigames jogados de verdade (tempos e taxas de acerto) |
| `godot --headless --path . res://dev/teste_fumaca_v2.tscn` | Tito e Pipoca andando pelo mapa novo sem erros |
| `godot --headless --path . res://dev/teste_menus.tscn` | menu → intro → carregamento → jogo → pausa → monitor → vitória/derrota → menu |
| `godot --headless --path . res://dev/teste_fluxo.tscn` e `teste_inimigos.tscn` | testes da V1 (mapa antigo) |
| `godot --path . res://dev/medir_desempenho.tscn` | FPS nas qualidades Alta e Baixa (grava `docs/progresso/relatorio_desempenho.txt`) |
| `godot --path . res://dev/captura.tscn -- plano=V2.5` | tira prints do jogo para `docs/progresso/imagens/` |
| `godot --headless --path . res://dev/validar_artes.tscn` | todas as artes (`Arte__*`) e textos 3D: definição, material, frente livre, nada colado atrás (z-fighting), letras com acento na fonte, texto cabe (grava `docs/progresso/relatorio_artes.txt`) |
| `godot --headless --path . res://dev/validar_itens.tscn` | pilhas, fichas, alicate e pistas fora de colisores, visíveis e alcançáveis; cadeados, correntes, teclado e disjuntores no lugar (grava `docs/progresso/relatorio_itens.txt`) |
| `godot --path . res://dev/captura_artes.tscn` | foto de frente de cada arte (`-- textos` inclui os textos 3D) para `docs/progresso/imagens/` |

## Estrutura de pastas

```
TurnoDaNoite/
├── README.md
├── blender/
│   ├── scripts/          planta_v2.py, gerar_predio_v2.py, moveis_v2_*.py, materiais_v2.py, comum.py,
│   │                     (V1) gerar_predio.py, gerar_moveis.py, gerar_placeholders.py, gerar_tudo.py ...
│   └── *.blend
├── ferramentas/          sons, texturas, materiais do Godot, cena do mundo, conferência das artes
├── godot/                project.godot, export_presets.cfg
│   ├── assets/           cenario/ (.glb), personagens/, sons/, texturas/, materiais/, fontes/,
│   │                     arte_externa/, dificuldade/ (.tres), dados/, shaders/
│   ├── cenas/            mundo_v2.tscn (jogo), mundo.tscn (V1), jogador, animatrônicos, minigames/, objetos/
│   ├── scripts/          lógica em GDScript (v2/ = portas, progressão, IA de tensão, áudio, interface)
│   ├── ui/               menu (capa dupla), intro, carregamento, HUD, pausa, opções, fim de jogo, tema
│   └── dev/              captura de tela, testes e validadores (fora do build)
├── docs/                 GDD, PLANO_V2, CONTRATOS, PADRAO_PERSONAGENS, GUIA_APRESENTACAO, CREDITOS, progresso/
└── builds/               windows/, linux/
```

## Regras do projeto

- Personagens, nomes, músicas e textos próprios.
- Modelos 3D e músicas gerados por script. Assets externos só com licença livre ou com crédito: texturas CC0, fontes OFL e efeitos sonoros da ElevenLabs (**elevenlabs.io**), todos listados em `docs/CREDITOS.md`.
- Sem sangue ou violência explícita: o medo vem do escuro, do som e de um susto limpo.
