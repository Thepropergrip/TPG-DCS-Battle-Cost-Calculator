import os, subprocess
from pathlib import Path
from PIL import Image
import numpy as np

root=Path(os.environ.get('GITHUB_WORKSPACE','.')).resolve()
src=root/'edm-source'/'rubble_attachment'
out=root/'edm-artifacts'/'Textures'
out.mkdir(parents=True,exist_ok=True)
texconv=Path(os.environ['TEXCONV_EXE'])

def run_tex(srcfile,dst,fmt):
    subprocess.run([str(texconv),'-nologo','-y','-f',fmt,'-m','0','-o',str(out),str(srcfile)],check=True)
    prod=out/(srcfile.stem+'.DDS')
    if not prod.exists(): prod=out/(srcfile.stem+'.dds')
    if not prod.exists(): raise RuntimeError(f'texconv missing output for {srcfile}')
    target=out/dst
    if target.exists(): target.unlink()
    prod.replace(target)

def arm(rough_path,metal_path,dst_png):
    r=np.asarray(Image.open(rough_path).convert('L'),dtype=np.uint8)
    if metal_path and Path(metal_path).exists():
        m=np.asarray(Image.open(metal_path).convert('L').resize((r.shape[1],r.shape[0])),dtype=np.uint8)
    else:
        m=np.zeros_like(r)
    a=np.full_like(r,255)
    rgb=np.dstack([a,r,m])
    Image.fromarray(rgb,'RGB').save(dst_png)

sets=[
 ('attachment','TPG_ATTACH_Rubble',True),
 ('debris_piles','TPG_ATTACH_DebrisPiles',False),
 ('tile','TPG_ATTACH_DebrisTile',False),
]
for stem,prefix,has_metal in sets:
    alb=src/f'{stem}_albedo.jpg'
    nor=src/f'{stem}_normal.jpg'
    rou=src/f'{stem}_roughness.jpg'
    met=src/f'{stem}_metallic.jpg' if has_metal else None
    for p in [alb,nor,rou]:
        if not p.exists(): raise RuntimeError(f'Missing supplied map: {p}')
    run_tex(alb,f'{prefix}_diff.dds','BC7_UNORM_SRGB')
    run_tex(nor,f'{prefix}_nor_gl.dds','BC7_UNORM')
    arm_png=out/f'{prefix}_arm_src.png'
    arm(rou,met,arm_png)
    run_tex(arm_png,f'{prefix}_arm.dds','BC7_UNORM')
    if arm_png.exists(): arm_png.unlink()
print('TPG_ATTACHMENT_TEXTURES_READY')
