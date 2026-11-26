"""
render_animatronicos_juntos.py — render dos dois animatrônicos finais lado a lado (página de progresso).
Precisa de blender/personagens/tito_final.blend e pipoca_final.blend (gerados por animatronicos_finais.py).
Rodar: blender --background --factory-startup --python blender/scripts/render_animatronicos_juntos.py -- <arquivo.png>
"""
import sys
from pathlib import Path

import bpy

RAIZ = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(RAIZ / "scripts"))
import animatronicos_finais as A  # noqa: E402

saida = sys.argv[sys.argv.index("--") + 1]
bpy.ops.wm.open_mainfile(filepath=str(RAIZ / "personagens" / "tito_final.blend"))
with bpy.data.libraries.load(str(RAIZ / "personagens" / "pipoca_final.blend")) as (origem, destino):
    destino.objects = list(origem.objects)
for ob in destino.objects:
    bpy.context.scene.collection.objects.link(ob)
tito = bpy.data.objects["Tito_Rig"]
pipoca = bpy.data.objects["Pipoca_Rig"]
tito.location.x -= 0.78
pipoca.location.x += 0.7
cam = A.estudio()
bpy.context.view_layer.update()
A.fotografar(cam, saida, (0, 0, 1.1), 5.6, 12, 7, 50, (1800, 1400))
