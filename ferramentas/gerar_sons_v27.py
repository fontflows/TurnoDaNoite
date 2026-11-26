"""
gerar_sons_v27.py — sons da fase V2.7 (áudio e acabamento), por síntese como o gerar_sons.py.

  - musica_menu_sombria: a mesma caixinha de música do menu, mas em tom MENOR, mais lenta,
    mais desafinada e com um grave por baixo (toca quando a capa do menu "vira" a versão sombria).
  - vhs_glitch: rajada de chiado de fita com o som "embolando" (a troca das capas).
  - ambientes por cômodo (loops): goteira, rangido, ventilação, geladeira, bipes, vento.
  - camadas de tensão (loops): tensao_drone (perigo perto) e perseguicao (sendo caçado).
  - sustos de ambiente (curtos): batida de metal longe, brinquedo chiando, caixinha com notas erradas.

Rodar (a partir da pasta TurnoDaNoite):  python ferramentas/gerar_sons_v27.py
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gerar_sons import (ACORDES, DOIS_PI, MELODIA, SR, SR_LONGO, colocar, estalo, fades, fase_de, filtrar,  # noqa: E402
                        gerador, midi_para_hz, normalizar, nota_caixinha, salvar_wav, serra, tempo)


def menor(nota):
    """Dó maior -> dó menor: mi, lá e si descem meio tom."""
    return nota - 1 if nota % 12 in (4, 9, 11) else nota


def musica_menu_sombria():
    """A caixinha do menu em dó menor, a 72 bpm, com fita bem gasta e um grave escuro por baixo. Loop."""
    sr, r = SR_LONGO, gerador(71)
    batida = 60.0 / 72.0
    duracao = len(MELODIA) * 3 * batida
    n = int(round(duracao * sr))
    cauda = int(3.5 * sr)
    total = n + cauda
    tt = np.arange(total) / sr
    ciclos = round(duracao / 4.0)  # oscilações com ciclos inteiros no loop (emendam sem salto)
    oscilacao = 1.0 + 0.012 * np.sin(DOIS_PI * ciclos / duracao * tt) + 0.004 * np.sin(DOIS_PI * 6.0 * tt)
    buf = np.zeros(total)

    def tocar(nota_midi, instante, volume, brilho=1.0):
        cents = r.uniform(-25, 25) + r.choice([0, 0, -40, 35])
        freq = midi_para_hz(menor(nota_midi) - 12) * 2.0 ** (cents / 1200.0)  # uma oitava abaixo
        inicio = int(round(instante * sr))
        som = nota_caixinha(freq, sr, 3.5, oscilacao[inicio:inicio + int(3.5 * sr)], brilho)
        colocar(buf, som * volume, inicio)

    for c, (compasso, (baixo, acorde)) in enumerate(zip(MELODIA, ACORDES)):
        inicio_compasso = c * 3 * batida
        for tempo_nota, nota in compasso:
            if r.random() < 0.12:
                continue  # notas que "falham" (pino da caixinha quebrado)
            tocar(nota, inicio_compasso + tempo_nota * batida, 0.85, brilho=0.6)
        tocar(baixo, inicio_compasso, 0.6, brilho=0.4)
    x = buf[:n].copy()
    x[:cauda] += buf[n:]
    # Grave escuro (dó e sol desafinados) respirando devagar
    t = np.arange(n) / sr
    resp = 0.6 + 0.4 * np.sin(DOIS_PI * round(duracao / 10.0) / duracao * t) ** 2
    drone = (serra(DOIS_PI * 32.7 * t) * 0.5 + serra(DOIS_PI * 49.2 * t) * 0.35) * resp
    x += filtrar(drone, sr, passa_baixas=220, circular=True) * 0.18
    chiado = filtrar(r.standard_normal(n), sr, 1500, 6000, circular=True)
    x += chiado / np.max(np.abs(chiado)) * 0.012
    return normalizar(x, -3.0), sr, True


def vhs_glitch():
    """Fita VHS embolando: chiado forte, tom que despenca e cortes rápidos. 0,9 s."""
    sr, r = SR, gerador(72)
    t = tempo(0.9, sr)
    chiado = filtrar(r.standard_normal(len(t)), sr, passa_altas=400, passa_baixas=9000)
    f = 900 * np.exp(-t * 3.0) + 60
    tom = serra(fase_de(f, sr)) * 0.5
    cortes = (np.sin(DOIS_PI * 23 * t) > -0.3).astype(float)
    x = (chiado * 0.7 + tom) * cortes * np.minimum(t / 0.03, 1.0) * np.exp(-t / 0.6)
    return normalizar(fades(x, sr, 0.005, 0.08), -3.0), sr, False


def _ruido_loop(r, dur, sr, pa, pb):
    return filtrar(r.standard_normal(int(dur * sr)), sr, passa_altas=pa, passa_baixas=pb, circular=True)


def goteira():
    """Pingos d'água num balde/poça, com eco curto. Loop de 4 s."""
    sr, r = SR, gerador(73)
    x = np.zeros(int(4.0 * sr))
    for inicio in (0.3, 1.45, 2.2, 3.4):
        t = tempo(0.35, sr)
        f = 1400 * np.exp(-t * 25) + 700
        ping = np.sin(fase_de(f, sr)) * np.exp(-t / 0.05)
        colocar(x, ping, int(inicio * sr), circular=True)
        colocar(x, ping * 0.25, int((inicio + 0.09) * sr), circular=True)
    return normalizar(x, -8.0), sr, True


def rangido():
    """Estrutura velha rangendo de vez em quando (madeira/metal). Loop de 8 s."""
    sr, r = SR, gerador(74)
    x = np.zeros(int(8.0 * sr))
    for inicio, dur in ((1.0, 1.2), (5.2, 0.8)):
        t = tempo(dur, sr)
        f = 140 + 60 * np.sin(np.pi * t / dur) + 8 * np.sin(DOIS_PI * 17 * t)
        ranger = serra(fase_de(f, sr)) * (0.5 + 0.5 * (r.random(len(t)) > 0.4)) * np.sin(np.pi * t / dur)
        colocar(x, filtrar(ranger, sr, passa_altas=90, passa_baixas=1800), int(inicio * sr), circular=True)
    return normalizar(x, -6.0), sr, True


def ventilacao():
    """Ar passando pelo duto: chiado grave com ronco de motor. Loop de 4 s."""
    sr, r = SR, gerador(75)
    t = np.arange(int(4.0 * sr)) / sr
    x = _ruido_loop(r, 4.0, sr, 80, 900) + 0.25 * np.sin(DOIS_PI * 100 * t) + 0.12 * np.sin(DOIS_PI * 50 * t)
    return normalizar(x, -10.0), sr, True


def geladeira():
    """Motor da geladeira: zumbido de 60 Hz com harmônicos e vibração. Loop de 4 s."""
    sr, r = SR, gerador(76)
    t = np.arange(int(4.0 * sr)) / sr
    x = sum(np.sin(DOIS_PI * f * t) * a for f, a in ((60, 1.0), (120, 0.6), (180, 0.3), (240, 0.15)))
    x = x * (1.0 + 0.1 * np.sin(DOIS_PI * 3.0 * t)) + _ruido_loop(r, 4.0, sr, 200, 2000) * 0.15
    return normalizar(x, -12.0), sr, True


def bipes():
    """Aparelho eletrônico velho apitando de vez em quando (painel/câmeras). Loop de 6 s."""
    sr = SR
    x = np.zeros(int(6.0 * sr))
    for inicio, f in ((0.5, 2200), (0.65, 2200), (3.8, 1600)):
        t = tempo(0.08, sr)
        colocar(x, fades(np.sin(DOIS_PI * f * t), sr, 0.003, 0.01), int(inicio * sr), circular=True)
    return normalizar(x, -14.0), sr, True


def vento():
    """Vento lá fora assobiando pelas frestas. Loop de 8 s."""
    sr, r = SR_LONGO, gerador(77)
    n = int(8.0 * sr)
    t = np.arange(n) / sr
    base = _ruido_loop(r, 8.0, sr, 200, 1200)
    rajada = 0.5 + 0.5 * np.sin(DOIS_PI * 1 / 8.0 * t) ** 2
    assobio = np.sin(fase_de(700 + 120 * np.sin(DOIS_PI * 2 / 8.0 * t), sr)) * 0.08 * rajada
    return normalizar(base * rajada + assobio, -10.0), sr, True


def tensao_drone():
    """Camada de perigo: grave pulsando como um coração enorme + cordas dissonantes. Loop de 8 s."""
    sr, r = SR_LONGO, gerador(78)
    n = int(8.0 * sr)
    t = np.arange(n) / sr
    pulso = np.exp(-((t * 1.0) % 1.0) / 0.25)  # 1 pulso por segundo (8 no loop)
    grave = np.sin(DOIS_PI * 41.2 * t) * pulso
    cordas = sum(serra(DOIS_PI * f * t) for f in (110.0, 116.5, 155.6)) / 3.0
    cordas = filtrar(cordas, sr, passa_baixas=700, circular=True) * (0.5 + 0.5 * np.sin(DOIS_PI * 1 / 8.0 * t) ** 2)
    return normalizar(grave * 0.8 + cordas * 0.35, -4.0), sr, True


def perseguicao():
    """Camada de perseguição: percussão metálica rápida e grave insistente. Loop de 4 s (150 bpm)."""
    sr, r = SR, gerador(79)
    n = int(3.2 * sr)  # 8 tempos a 150 bpm
    x = np.zeros(n)
    batida = 60.0 / 150.0
    for i in range(8):
        t = tempo(0.25, sr)
        bumbo = np.sin(fase_de(90 * np.exp(-t * 30) + 45, sr)) * np.exp(-t / 0.12)
        colocar(x, bumbo, int(i * batida * sr), circular=True)
        if i % 2 == 1:
            metal = sum(np.sin(DOIS_PI * f * t) for f in (523, 1307, 2411)) * np.exp(-t / 0.05) / 3.0
            colocar(x, metal * 0.6 + estalo(sr, r, 0.25, 0.01)[:len(t)] * 0.3, int(i * batida * sr), circular=True)
    t = np.arange(n) / sr
    x += serra(DOIS_PI * 55 * t) * 0.15 * (np.sin(DOIS_PI * 2.5 * t) > 0)
    return normalizar(filtrar(x, sr, passa_baixas=5000, circular=True), -3.0), sr, True


def susto_batida_metal():
    """Algo de metal caindo longe (com eco do prédio vazio)."""
    sr, r = SR, gerador(80)
    x = np.zeros(int(2.5 * sr))
    t = tempo(1.5, sr)
    golpe = sum(np.sin(DOIS_PI * f * t) * a for f, a in ((210, 1.0), (517, 0.5), (1130, 0.3))) * np.exp(-t / 0.3)
    golpe += estalo(sr, r, 1.5, 0.01)[:len(t)] * 0.5
    golpe = filtrar(golpe, sr, passa_baixas=2500)
    for i, (atraso, vol) in enumerate(((0.0, 1.0), (0.23, 0.4), (0.51, 0.2), (0.83, 0.1))):
        colocar(x, golpe * vol, int(atraso * sr))
    return normalizar(fades(x, sr), -6.0), sr, False


def susto_brinquedo():
    """Brinquedo de apertar chiando sozinho, longe (sem voz)."""
    sr, r = SR, gerador(81)
    x = np.zeros(int(1.6 * sr))
    for inicio, dur in ((0.0, 0.35), (0.6, 0.5)):
        t = tempo(dur, sr)
        f = 900 + 500 * np.sin(np.pi * t / dur)
        chiado = (np.sin(fase_de(f, sr)) + 0.4 * filtrar(r.standard_normal(len(t)), sr, 1000, 4000)) * np.sin(np.pi * t / dur)
        colocar(x, chiado, int(inicio * sr))
    return normalizar(filtrar(x, sr, passa_baixas=3000), -8.0), sr, False


def susto_caixinha():
    """Três notas de caixinha de música, erradas e lentas, vindas do nada."""
    sr = SR_LONGO
    x = np.zeros(int(4.0 * sr))
    for i, nota in enumerate((72, 71, 66)):
        colocar(x, nota_caixinha(midi_para_hz(nota) * 0.985, sr, 2.5), int(i * 0.9 * sr))
    return normalizar(x, -6.0), sr, False


def objetivo():
    """Plim curto (duas notas subindo) quando um passo do objetivo é concluído (V2.2)."""
    sr = SR
    x = np.zeros(int(0.6 * sr))
    for i, f in enumerate((880.0, 1318.5)):
        tt = tempo(0.35, sr)
        colocar(x, (np.sin(DOIS_PI * f * tt) + 0.3 * np.sin(DOIS_PI * 2 * f * tt)) * np.exp(-tt / 0.12), int(i * 0.11 * sr))
    return normalizar(fades(x, sr), -9.0), sr, False


SONS = {
    "objetivo.wav": objetivo,
    "musica_menu_sombria.wav": musica_menu_sombria,
    "vhs_glitch.wav": vhs_glitch,
    "goteira.wav": goteira,
    "rangido.wav": rangido,
    "ventilacao.wav": ventilacao,
    "geladeira.wav": geladeira,
    "bipes.wav": bipes,
    "vento.wav": vento,
    "tensao_drone.wav": tensao_drone,
    "perseguicao.wav": perseguicao,
    "susto_batida_metal.wav": susto_batida_metal,
    "susto_brinquedo.wav": susto_brinquedo,
    "susto_caixinha.wav": susto_caixinha,
}


def main():
    pasta = Path(__file__).resolve().parents[1] / "godot" / "assets" / "sons"
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, funcao in SONS.items():
        x, sr, loop = funcao()
        salvar_wav(nome, x, sr, loop)
        print(f"{nome:<26}{len(x) / sr:6.2f} s{'  (loop)' if loop else ''}")


if __name__ == "__main__":
    main()
