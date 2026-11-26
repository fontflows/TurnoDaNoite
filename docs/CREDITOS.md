# Créditos

Os modelos 3D, o cenário e os sons do jogo foram gerados por script pelo próprio grupo. Abaixo estão listados os recursos de terceiros utilizados no projeto, com seus autores e licenças.

## Fontes

Todas as fontes foram obtidas no repositório oficial do Google Fonts e são distribuídas sob a SIL Open Font License 1.1 (OFL). Uma cópia da licença (`OFL.txt`) acompanha cada fonte em `godot/assets/fontes/<NomeDaFonte>/`.

| Fonte | Autor/Designer | Licença | Origem | Uso no jogo |
|---|---|---|---|---|
| Bungee | David Jonathan Ross | SIL OFL 1.1 | [google/fonts/ofl/bungee](https://github.com/google/fonts/tree/main/ofl/bungee) | Logo e placas |
| Bungee Shade | David Jonathan Ross | SIL OFL 1.1 | [google/fonts/ofl/bungeeshade](https://github.com/google/fonts/tree/main/ofl/bungeeshade) | Logo e placas |
| Fredoka | Milena Brandão, Hafontia | SIL OFL 1.1 | [google/fonts/ofl/fredoka](https://github.com/google/fonts/tree/main/ofl/fredoka) | Logo e placas |
| Press Start 2P | CodeMan38 | SIL OFL 1.1 | [google/fonts/ofl/pressstart2p](https://github.com/google/fonts/tree/main/ofl/pressstart2p) | Fliperama, relógio e HUD |
| VT323 | Peter Hull | SIL OFL 1.1 | [google/fonts/ofl/vt323](https://github.com/google/fonts/tree/main/ofl/vt323) | Fliperama, relógio e HUD |
| Courier Prime | Alan Dague-Greene | SIL OFL 1.1 | [google/fonts/ofl/courierprime](https://github.com/google/fonts/tree/main/ofl/courierprime) | Documentos datilografados |
| Caveat | Impallari Type | SIL OFL 1.1 | [google/fonts/ofl/caveat](https://github.com/google/fonts/tree/main/ofl/caveat) | Letra de funcionário |
| Gochi Hand | HT Fonts | SIL OFL 1.1 | [google/fonts/ofl/gochihand](https://github.com/google/fonts/tree/main/ofl/gochihand) | Recados de criança |
| Creepster | Sideshow | SIL OFL 1.1 | [google/fonts/ofl/creepster](https://github.com/google/fonts/tree/main/ofl/creepster) | Título do jogo no menu |

Observação: as fontes variáveis foram renomeadas localmente para evitar colchetes no caminho dos arquivos:

- `Fredoka[wdth,wght].ttf` → `Fredoka-Variable.ttf`
- `Caveat[wght].ttf` → `Caveat-Variable.ttf`

## Texturas

| Material (pasta) | Asset (ambientCG) | Autor | Licença | Link | Uso |
|---|---|---|---|---|---|
| `azulejo_branco` | Tiles133C | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Tiles133C | azulejos da cozinha e dos banheiros |
| `chapa_antiderrapante` | DiamondPlate008D | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=DiamondPlate008D | piso da cozinha e da câmara fria |
| `madeira_lambri` | Planks037A | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Planks037A | lambri na parte de baixo das paredes |
| `madeira_palco` | WoodFloor043 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=WoodFloor043 | piso do palco (2K) |
| `reboco_pintado` | PaintedPlaster015 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=PaintedPlaster015 | paredes de serviço |
| `concreto` | Concrete036 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Concrete036 | depósito e sala elétrica |
| `tijolo` | Bricks097 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Bricks097 | tijolo aparente no depósito |
| `veludo` | Fabric062 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Fabric062 | cortinas (tingido de vermelho no jogo) |
| `metal_pintado` | PaintedMetal012 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=PaintedMetal012 | portas, armários e partes dos animatrônicos |
| `ferrugem` | Rust009 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Rust009 | metal enferrujado |
| `animatronicos` | Fabric084 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Fabric084 | pelúcia do Tito e da Pipoca finais (relevo dos tufos; a cor é tingida por `ferramentas/gerar_texturas_animatronicos.py` e o normal é somado ao pelo curto assado em `blender/scripts/assar_pelo.py`) |
| `metal_escovado` | Metal009 | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Metal009 | inox da cozinha e peças metálicas |
| `plastico` | Plastic013B | ambientCG (Lennart Demes) | CC0 1.0 | https://ambientcg.com/view?id=Plastic013B | máquinas, cadeiras e brinquedos |

Arquivos em `godot/assets/texturas/<material>/` (`_cor`, `_normal` padrão OpenGL, `_aspereza` e `_ao`), em 1K, exceto o piso do palco, em 2K.

### Texturas geradas pelo grupo (por script)

Feitas pelo próprio grupo com `ferramentas/gerar_texturas.py` (ruído e formas desenhadas por código, nada baixado). Os materiais repetem sem emenda e seguem o mesmo padrão de arquivos (`_cor`, `_normal` OpenGL e `_aspereza`):

- `carpete_fliperama` (2K): carpete de fliperama anos 90 com planetas, estrelas e rabiscos em neon desbotado.
- `quadriculado_gasto`: piso xadrez preto e branco, sujo, com peças lascadas e rachadas.
- `papel_parede_festa`: papel de parede vinho com chapéus de festa e estrelas, com manchas de umidade.
- `forro_manchado`: forro de placas 60x60 com furinhos e manchas de infiltração.
- `sujeira_cantos`: máscara de sujeira em tons de cinza.
- `decals/`: mancha de água, gordura, pegadas, confete, refrigerante, rachadura, desenho de giz de cera e marca de mão (PNG com alfa).
- `lanterna/lanterna_cookie.png`: formato do facho da lanterna.

Para gerar de novo (a partir da pasta `TurnoDaNoite`):

```
"C:\Program Files\Blender Foundation\Blender 5.3\blender.exe" --background --factory-startup --python ferramentas/gerar_texturas.py
```

## Imagens externas

Artes geradas pelo grupo a partir dos prompts de docs/PROMPTS_ARTE.md, quando presentes.

## Vozes (V2.7)
- **Recado da secretária eletrônica** (`godot/assets/sons/secretaria_recado.wav`): falas geradas offline com as vozes em português que já vêm instaladas no Windows (**Microsoft Daniel** e **Microsoft Maria**, via `System.Speech`), pelo script `ferramentas/gerar_secretaria.py`. Depois o som é filtrado para parecer fita de secretária eletrônica antiga. Nada foi baixado.

## Sons e músicas sintetizados (V2.5 e V2.7)
- `ferramentas/gerar_sons_v25.py`, `ferramentas/gerar_sons_v27.py`, `ferramentas/gerar_sons_kart.py` e `ferramentas/gerar_sons_garra_conserto.py`: todos os efeitos, ambientes, camadas de música (tensão e perseguição) e a versão sombria da música do menu são feitos por síntese (ondas e ruído), sem amostras externas.

## Áudio externo (V2.2)
- Voz e efeitos gerados pelo grupo seguindo `docs/PROMPTS_AUDIO.md` e colocados em `godot/assets/audio_externo/`.
- **Voz:** geração de fala do Google AI Studio (Gemini TTS).
- **Efeitos sonoros:** gerados na **ElevenLabs** (Sound Effects), plano gratuito — **crédito: elevenlabs.io** (também no README e no rodapé do menu principal do jogo).
- Os arquivos estão em `godot/assets/audio_externo/efeitos/` (lista completa em `docs/PROMPTS_AUDIO.md`).

