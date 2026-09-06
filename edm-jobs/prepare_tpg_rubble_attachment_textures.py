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
    m=np.asarray(Image.open(metal_path).convert('L').resize((r.shape[1],r.shape[0])),dtype=np.uint8)
    a=np.full_like(r,255)
    Image.fromarray(np.dstack([a,r,m]),'RGB').save(dst_png)

alb=src/'attachment_albedo.jpg'; nor=src/'attachment_normal.jpg'; rou=src/'attachment_roughness.jpg'; met=src/'attachment_metallic.jpg'
for p in [alb,nor,rou,met]:
    if not p.exists(): raise RuntimeError(f'Missing supplied map: {p}')
run_tex(alb,'TPG_ATTACH_Rubble_diff.dds','BC7_UNORM_SRGB')
run_tex(nor,'TPG_ATTACH_Rubble_nor_gl.dds','BC7_UNORM')
arm_png=out/'TPG_ATTACH_Rubble_arm_src.png'
arm(rou,met,arm_png)
run_tex(arm_png,'TPG_ATTACH_Rubble_arm.dds','BC7_UNORM')
if arm_png.exists(): arm_png.unlink()
print('TPG_ATTACHMENT_TEXTURES_READY')
