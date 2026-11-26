"""
gerar_sons_v25.py — sons novos da fase V2.5 (corpo do vigia, portas, teclado, gerador, itens).
Mesmo jeito do gerar_sons.py: tudo por síntese, sementes fixas, nada baixado da internet.

Rodar (a partir da pasta TurnoDaNoite):  python ferramentas/gerar_sons_v25.py
Precisa de numpy (o mesmo do gerar_sons.py).
"""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gerar_sons import (DOIS_PI, SR, PASTA_SONS, colocar, estalo, fades, fase_de, filtrar, gerador,  # noqa: E402
                        normalizar, salvar_wav, serra, tempo)


def batimento():
    """Coração: 'tum-tum' grave (dois baques por ciclo), em loop de 1 s (o jogo acelera com o pitch)."""
    sr = SR
    x = np.zeros(int(sr * 1.0))
    for inicio, forca in ((0.0, 1.0), (0.22, 0.7)):
        t = tempo(0.18, sr)
        f = 55.0 * np.exp(-t * 6.0) + 38.0
        baque = np.sin(fase_de(f, sr)) * np.exp(-t / 0.05) * forca
        colocar(x, baque, int(inicio * sr), circular=True)
    x = filtrar(x, sr, passa_baixas=180, circular=True)
    return normalizar(x, -2.0), sr, True


def _sopro(r, sr, dur, cor_baixa, cor_alta, forca):
    """Um sopro de ar (inspirar ou expirar): ruído filtrado na faixa da voz, com envelope suave."""
    t = tempo(dur, sr)
    env = np.sin(np.pi * t / dur) ** 2.5
    ar = filtrar(r.standard_normal(len(t)), sr, passa_altas=cor_baixa, passa_baixas=cor_alta, ordem=3)
    return ar * env * forca


def ofegante():
    """Respiração ofegante depois de correr (V2.2: mais grave, macia e baixa; a antiga chiava demais)."""
    sr, r = SR, gerador(51)
    x = np.zeros(int(sr * 2.6))
    for i in range(3):
        base = i * 0.82
        colocar(x, _sopro(r, sr, 0.34, 180, 900, 0.8), int(base * sr))           # puxa o ar (boca)
        colocar(x, _sopro(r, sr, 0.42, 150, 700, 1.0), int((base + 0.36) * sr))  # solta
    return normalizar(fades(x, sr, 0.02, 0.1), -14.0), sr, False


def respiracao_escondido():
    """Respiração tensa e baixinha de quem está escondido (loop de 6 s): pelo nariz, trêmula."""
    sr, r = SR, gerador(61)
    n = int(sr * 6.0)
    x = np.zeros(n)
    for inicio in (0.2, 2.2, 4.1):
        inspira = _sopro(r, sr, 0.9, 120, 600, 0.6)
        tremor = 1.0 + 0.35 * np.sin(np.arange(len(inspira)) / sr * 2 * np.pi * 9.0)
        colocar(x, inspira * tremor, int(inicio * sr), circular=True)
        colocar(x, _sopro(r, sr, 1.1, 100, 500, 0.5), int((inicio + 0.95) * sr), circular=True)
    return normalizar(x, -18.0), sr, True


def porta_rangido():
    """Dobradiça velha rangendo: tom que sobe e desce com aspereza (serra + vibrato)."""
    sr, r = SR, gerador(52)
    t = tempo(1.1, sr)
    f = 380 + 220 * np.sin(np.pi * t / 1.1) + 25 * np.sin(DOIS_PI * 13 * t)
    x = 0.6 * serra(fase_de(f, sr)) + 0.4 * np.sin(fase_de(f * 2.01, sr))
    x *= (0.6 + 0.4 * (r.random(len(t)) > 0.3)) * np.sin(np.pi * t / 1.1) ** 0.6
    x = filtrar(x, sr, passa_altas=200, passa_baixas=3500)
    return normalizar(fades(x, sr, 0.01, 0.05), -5.0), sr, False


def corrente_cortada():
    """Alicate cortando a corrente (estalo seco) e a corrente caindo no chão (tilintar metálico)."""
    sr, r = SR, gerador(53)
    x = np.zeros(int(sr * 1.6))
    colocar(x, estalo(sr, r, 0.03, 0.006) * 1.5, 0)
    for i in range(14):
        inicio = 0.25 + i * 0.07 + r.random() * 0.03
        t = tempo(0.25, sr)
        f = r.uniform(1800, 4200)
        tin = (np.sin(DOIS_PI * f * t) + 0.5 * np.sin(DOIS_PI * f * 2.7 * t)) * np.exp(-t / 0.05)
        colocar(x, tin * (1.0 - i / 18.0), int(inicio * sr))
    t = tempo(0.3, sr)
    colocar(x, np.sin(DOIS_PI * 70 * t) * np.exp(-t / 0.06) * 0.8, int(0.27 * sr))
    return normalizar(fades(x, sr), -1.0), sr, False


def porta_aco():
    """Porta de aço pesada deslizando e batendo: ronco grave de motor + 'CLANG' final."""
    sr, r = SR, gerador(54)
    x = np.zeros(int(sr * 1.8))
    t = tempo(1.3, sr)
    motor = serra(fase_de(np.full(len(t), 48.0), sr)) * 0.5 + filtrar(r.standard_normal(len(t)), sr, passa_baixas=400) * 0.4
    colocar(x, motor * np.minimum(t / 0.1, 1.0), 0)
    t = tempo(0.5, sr)
    clang = sum(np.sin(DOIS_PI * f * t) * a for f, a in ((180, 1.0), (437, 0.6), (911, 0.4), (1630, 0.25))) * np.exp(-t / 0.12)
    colocar(x, clang * 1.5, int(1.3 * sr))
    return normalizar(fades(x, sr), -1.0), sr, False


def porta_trancada():
    """Maçaneta forçada numa porta trancada: dois 'tec-tec' secos."""
    sr, r = SR, gerador(55)
    x = np.zeros(int(sr * 0.45))
    for inicio in (0.0, 0.18):
        t = tempo(0.08, sr)
        tec = (np.sin(DOIS_PI * 900 * t) * 0.5 + r.standard_normal(len(t)) * 0.5) * np.exp(-t / 0.012)
        colocar(x, tec, int(inicio * sr))
    return normalizar(filtrar(x, sr, passa_altas=300), -4.0), sr, False


def bip(freq, dur, forma="seno"):
    sr = SR
    t = tempo(dur, sr)
    onda = np.sin(DOIS_PI * freq * t) if forma == "seno" else np.sign(np.sin(DOIS_PI * freq * t)) * 0.6
    return fades(onda, sr, 0.003, 0.01)


def teclado_bip():
    return normalizar(bip(1500, 0.06), -8.0), SR, False


def teclado_erro():
    x = np.concatenate([bip(320, 0.18, "quadrada"), np.zeros(int(SR * 0.05)), bip(260, 0.3, "quadrada")])
    return normalizar(x, -4.0), SR, False


def teclado_certo():
    x = np.concatenate([bip(1046, 0.09), bip(1318, 0.09), bip(1568, 0.2)])
    return normalizar(x, -6.0), SR, False


def gerador_partida():
    """Gerador a diesel pegando: arranque engasgando e o motor subindo até ficar estável."""
    sr, r = SR, gerador(56)
    dur = 4.0
    t = tempo(dur, sr)
    rpm = np.where(t < 1.2, 6 + 3 * np.sin(DOIS_PI * 2.5 * t), 6 + 22 * np.minimum((t - 1.2) / 1.5, 1.0))
    pulsos = np.maximum(np.sin(fase_de(rpm, sr)), 0) ** 6
    corpo = filtrar(r.standard_normal(len(t)), sr, passa_baixas=600) * pulsos
    ronco = serra(fase_de(rpm * 4.0, sr)) * 0.3 * np.minimum(t / 1.5, 1.0)
    x = filtrar(corpo + ronco, sr, passa_baixas=1200)
    return normalizar(fades(x, sr, 0.01, 0.3), -1.0), sr, False


def ficha():
    """Ficha de fliperama: 'tlin' metálico curto."""
    sr = SR
    t = tempo(0.35, sr)
    x = (np.sin(DOIS_PI * 2350 * t) + 0.6 * np.sin(DOIS_PI * 3710 * t) + 0.3 * np.sin(DOIS_PI * 5900 * t)) * np.exp(-t / 0.07)
    return normalizar(fades(x, sr), -6.0), sr, False


def duto_rastejar():
    """Rastejando no duto de metal: batidas ocas de joelho e mão, chapa vibrando. 3 s."""
    sr, r = SR, gerador(57)
    x = np.zeros(int(sr * 3.0))
    for i in range(10):
        inicio = i * 0.29 + r.random() * 0.05
        t = tempo(0.25, sr)
        f = r.uniform(140, 220)
        oco = (np.sin(DOIS_PI * f * t) + 0.4 * np.sin(DOIS_PI * f * 2.6 * t)) * np.exp(-t / 0.05)
        colocar(x, oco * r.uniform(0.5, 1.0), int(inicio * sr))
    x += filtrar(r.standard_normal(len(x)), sr, passa_altas=800, passa_baixas=3000) * 0.04
    return normalizar(fades(x, sr, 0.05, 0.3), -4.0), sr, False


def vidro_quebrando():
    """Pisar em cacos de vidro: vários estalos agudos e tilintar curto."""
    sr, r = SR, gerador(58)
    x = np.zeros(int(sr * 0.6))
    for i in range(18):
        inicio = r.random() * 0.35
        t = tempo(0.06, sr)
        f = r.uniform(3000, 8000)
        colocar(x, np.sin(DOIS_PI * f * t) * np.exp(-t / 0.015) * r.uniform(0.3, 1.0), int(inicio * sr))
        colocar(x, estalo(sr, r, 0.01, 0.002) * 0.5, int(inicio * sr))
    return normalizar(filtrar(x, sr, passa_altas=1500), -3.0), sr, False


def lata_batendo():
    """Lata de alumínio quicando no chão: três batidas cada vez menores."""
    sr, r = SR, gerador(59)
    x = np.zeros(int(sr * 0.9))
    for i, (inicio, forca) in enumerate(((0.0, 1.0), (0.28, 0.55), (0.45, 0.3), (0.55, 0.15))):
        t = tempo(0.2, sr)
        lata = sum(np.sin(DOIS_PI * f * t) * a for f, a in ((620, 1.0), (1480, 0.6), (2730, 0.4))) * np.exp(-t / 0.04)
        colocar(x, (lata + estalo(sr, r, 0.2, 0.004)[:len(t)] * 0.6) * forca, int(inicio * sr))
    return normalizar(fades(x, sr), -2.0), sr, False


def choque():
    """Choque elétrico: zumbido forte e chiado com estalos (curto)."""
    sr, r = SR, gerador(60)
    t = tempo(0.9, sr)
    zum = serra(fase_de(np.full(len(t), 120.0), sr)) * 0.6 + np.sign(np.sin(DOIS_PI * 60 * t)) * 0.3
    zum *= (r.random(len(t)) > 0.15)
    x = zum * np.exp(-t / 0.5)
    for i in range(25):
        colocar(x, estalo(sr, r, 0.005, 0.001) * 1.2, int(r.random() * len(t) * 0.9))
    return normalizar(fades(filtrar(x, sr, passa_altas=80), sr), -2.0), sr, False


SONS = {
    "batimento.wav": batimento,
    "ofegante.wav": ofegante,
    "respiracao_escondido.wav": respiracao_escondido,
    "porta_rangido.wav": porta_rangido,
    "corrente_cortada.wav": corrente_cortada,
    "porta_aco.wav": porta_aco,
    "porta_trancada.wav": porta_trancada,
    "teclado_bip.wav": teclado_bip,
    "teclado_erro.wav": teclado_erro,
    "teclado_certo.wav": teclado_certo,
    "gerador_partida.wav": gerador_partida,
    "ficha.wav": ficha,
    "duto_rastejar.wav": duto_rastejar,
    "vidro_quebrando.wav": vidro_quebrando,
    "lata_batendo.wav": lata_batendo,
    "choque.wav": choque,
}


def main():
    PASTA_SONS.mkdir(parents=True, exist_ok=True)
    for nome, funcao in SONS.items():
        x, sr, loop = funcao()
        salvar_wav(nome, x, sr, loop)
        print(f"{nome:<24}{len(x) / sr:6.2f} s{'  (loop)' if loop else ''}")


if __name__ == "__main__":
    main()
