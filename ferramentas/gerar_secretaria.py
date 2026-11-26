"""
gerar_secretaria.py — grava o recado da SECRETÁRIA ELETRÔNICA da sala de segurança.

Usa as vozes em português que já vêm no Windows (Microsoft Daniel e Maria, pelo System.Speech,
sem internet). Cada frase vira um .wav; depois este script junta tudo com "cara de fita velha
de telefone" (só os médios, chiado, cliques, wow) e grava:
    godot/assets/sons/secretaria_recado.wav
    godot/assets/dados/secretaria_legendas.json   (texto e instante de cada frase, para as legendas)

Rodar no Windows (a partir da pasta TurnoDaNoite):  python ferramentas/gerar_secretaria.py
Se as vozes não existirem, o jogo mostra só as legendas com bipes.
"""

import json
import subprocess
import sys
import tempfile
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
from gerar_sons import colocar, estalo, filtrar, gerador, normalizar, salvar_wav  # noqa: E402

RAIZ = Path(__file__).resolve().parents[1]
SAIDA_JSON = RAIZ / "godot" / "assets" / "dados" / "secretaria_legendas.json"
SR = 22050

# (voz, frase). A "máquina" fala com a voz da Maria; o gerente com a do Daniel.
# Mesmas falas de docs/PROMPTS_AUDIO.md (godot/assets/dados/secretaria_falas.json): esta gravação é a reserva
# usada enquanto a voz externa não existir.
FALAS = [
    ("Microsoft Maria", "Você tem. Uma. Nova mensagem."),
    ("Microsoft Daniel", "Alô? Alô... Oi, aqui é o gerente. Bem-vindo ao turno da noite."),
    ("Microsoft Daniel", "Olha, tô gravando rapidinho, então presta atenção."),
    ("Microsoft Daniel", "A energia caiu de novo. Os quatro disjuntores desarmaram."),
    ("Microsoft Daniel", "Cozinha, depósito, a minha sala... e a sala elétrica."),
    ("Microsoft Daniel", "Religa os quatro. Depois liga o gerador principal, lá na sala elétrica."),
    ("Microsoft Daniel", "A chave da minha sala... ficou presa na máquina de garra. Não pergunta."),
    ("Microsoft Daniel", "E eu troquei a senha da sala elétrica. Metade tá num bilhete na minha mesa. A outra metade... é o meu recorde no Títu Kárt."),
    ("Microsoft Daniel", "Ah, e... se você ouvir passos. Ou música vindo do palco..."),
    ("Microsoft Daniel", "Fica quietinho. Os bonecos têm um... modo noturno. É normal. Acho."),
    ("Microsoft Daniel", "Quando terminar, fecha a porta de aço da sua sala. Tá bom?"),
    ("Microsoft Daniel", "Boa noite. E... boa sorte."),
    ("Microsoft Maria", "Fim. Das mensagens."),
]

PS = r"""
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$s.SelectVoice('{voz}')
$s.Rate = {velocidade}
$f = New-Object System.Speech.AudioFormat.SpeechAudioFormatInfo({sr}, [System.Speech.AudioFormat.AudioBitsPerSample]::Sixteen, [System.Speech.AudioFormat.AudioChannel]::Mono)
$s.SetOutputToWaveFile('{arquivo}', $f)
$s.Speak([IO.File]::ReadAllText('{texto}', [Text.Encoding]::UTF8))
$s.Dispose()
"""


def falar(voz, frase, pasta, i):
    arquivo = pasta / f"fala_{i:02d}.wav"
    texto = pasta / f"fala_{i:02d}.txt"
    texto.write_text(frase, encoding="utf-8")
    script = PS.format(voz=voz, velocidade=-1 if "Maria" in voz else 0, sr=SR, arquivo=arquivo, texto=texto)
    subprocess.run(["powershell", "-NoProfile", "-Command", script], check=True, capture_output=True)
    with wave.open(str(arquivo), "rb") as w:
        dados = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype(np.float64) / 32768.0
    return dados


def tirar_silencio(x, limite=0.01):
    ativo = np.where(np.abs(x) > limite)[0]
    return x if len(ativo) == 0 else x[max(ativo[0] - 400, 0):ativo[-1] + 800]


def main():
    r = gerador(90)
    pedacos, legendas = [], []
    instante = 0.6  # um tiquinho de fita antes de começar
    with tempfile.TemporaryDirectory() as tmp:
        pasta = Path(tmp)
        for i, (voz, frase) in enumerate(FALAS):
            x = tirar_silencio(falar(voz, frase, pasta, i))
            if "Maria" in voz:
                x = filtrar(x, SR, passa_altas=500, passa_baixas=2600) * 0.9  # voz da máquina: mais "lata"
            legendas.append({"inicio": round(instante, 2), "fim": round(instante + len(x) / SR, 2),
                             "quem": "SECRETÁRIA" if "Maria" in voz else "GERENTE",
                             "texto": frase.replace("Títu Kárt", "Tito Kart")})  # grafia só para a pronúncia
            pedacos.append((instante, x))
            pausa = 0.9 if i in (0, len(FALAS) - 2) else 0.45
            instante += len(x) / SR + pausa
    total = int((instante + 0.8) * SR)
    fita = np.zeros(total)
    for inicio, x in pedacos:
        colocar(fita, x, int(inicio * SR))
    # Bipe antes do recado do gerente
    t = np.arange(int(0.45 * SR)) / SR
    colocar(fita, np.sin(2 * np.pi * 1000 * t) * 0.35, int((legendas[1]["inicio"] - 0.7) * SR))
    # "Telefone + fita velha": só os médios, um pouco de saturação, wow lento e chiado.
    tt = np.arange(total) / SR
    wow = 1.0 + 0.004 * np.sin(2 * np.pi * 0.7 * tt)
    idx = np.clip(np.cumsum(wow) - 1, 0, total - 1)
    fita = np.interp(idx, np.arange(total), fita)
    fita = filtrar(fita, SR, passa_altas=300, passa_baixas=3400)
    fita = np.tanh(fita * 1.8) / 1.8
    fita += filtrar(r.standard_normal(total), SR, 1500, 7000) * 0.012
    for k in range(6):
        colocar(fita, estalo(SR, r, 0.004, 0.001) * 0.15, int(r.random() * total))
    salvar_wav("secretaria_recado.wav", normalizar(fita, -2.0), SR)
    SAIDA_JSON.parent.mkdir(parents=True, exist_ok=True)
    SAIDA_JSON.write_text(json.dumps({"legendas": legendas, "duracao": round(total / SR, 2)}, ensure_ascii=False, indent=1),
                          encoding="utf-8")
    print(f"recado: {total / SR:.1f} s, {len(legendas)} falas -> {SAIDA_JSON.name}")


if __name__ == "__main__":
    main()
