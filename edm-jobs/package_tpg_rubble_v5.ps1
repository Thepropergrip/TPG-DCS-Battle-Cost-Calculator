param()
$ErrorActionPreference='Stop'
$root=Join-Path $env:GITHUB_WORKSPACE 'edm-artifacts'
$asset='TPG_Rubble_Pile_20ft_Cinematic_V5'
$pkg=Join-Path $root $asset
$shapes=Join-Path $pkg 'Shapes'
$textures=Join-Path $pkg 'Textures'
$db=Join-Path $pkg 'Database'
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models=@(
 'TPG_Rubble_Pile_20ft_Cinematic_V5.edm',
 'TPG_Rubble_Pile_20ft_Cinematic_V5_Destroyed.edm',
 'TPG_Rubble_Pile_20ft_Cinematic_V5_LOD1.edm',
 'TPG_Rubble_Pile_20ft_Cinematic_V5_LOD2.edm'
)
foreach($m in $models){
 $src=Join-Path $root $m
 if(-not(Test-Path $src)){throw "Missing required model: $m"}
 Copy-Item $src $shapes -Force
}

$lods=@'
model={
    lods={
        {"TPG_Rubble_Pile_20ft_Cinematic_V5.edm",350.0};
        {"TPG_Rubble_Pile_20ft_Cinematic_V5_LOD1.edm",1200.0};
        {"TPG_Rubble_Pile_20ft_Cinematic_V5_LOD2.edm",7000.0};
    };
    collision_shell="TPG_Rubble_Pile_20ft_Cinematic_V5.edm";
}
'@
Set-Content -Path (Join-Path $shapes 'TPG_Rubble_Pile_20ft_Cinematic_V5.lods') -Value $lods -Encoding ASCII

$srcTex=Join-Path $root 'Textures'
if(-not(Test-Path $srcTex)){throw 'Texture staging folder missing'}
$dds=@(Get-ChildItem $srcTex -Filter *.dds -File)
if($dds.Count -lt 45){throw "Expected at least 45 DDS textures; found $($dds.Count)"}
Copy-Item (Join-Path $srcTex '*.dds') $textures -Force

$entry=@'
declare_plugin("TPG Rubble Pile 20ft Cinematic V5",
{
    installed=true,
    dirName=current_mod_path,
    displayName=_("TPG Rubble Pile 20ft Cinematic V5"),
    version="5.0.0",
    state="installed",
    info=_("Rounded no-spoke cinematic rubble pile with visible masonry/trash, textured round pipes and oxidized ribbed rebar")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_pile_cinematic_v5.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg 'entry.lua') -Value $entry -Encoding UTF8

$dbLua=@'
local function add_structure(f)
    f.shape_table_data={
        {
            file=f.ShapeName,
            life=f.Life,
            username=f.Name,
            desrt=f.ShapeNameDestr or "self",
            classname="lLandVehicle",
            positioning="BYNORMAL",
        }
    }
    if f.ShapeNameDestr then
        f.shape_table_data[#f.shape_table_data+1]={name=f.ShapeNameDestr,file=f.ShapeNameDestr}
    end
    f.mapclasskey="P0091000076"
    f.attribute={wsType_Static,wsType_Standing,"Structures"}
    add_surface_unit(f)
end

add_structure({
    Name="TPG_Rubble_Pile_20ft_Cinematic_V5",
    DisplayName=_("TPG Rubble Pile 20ft Cinematic V5"),
    ShapeName="TPG_Rubble_Pile_20ft_Cinematic_V5",
    ShapeNameDestr="TPG_Rubble_Pile_20ft_Cinematic_V5_Destroyed",
    Life=450,
    Rate=100,
    category="Structures",
    SeaObject=false,
    isPutToWater=false,
    numParking=0,
})
'@
Set-Content -Path (Join-Path $db 'db_tpg_rubble_pile_cinematic_v5.lua') -Value $dbLua -Encoding UTF8

$readme=@'
TPG Rubble Pile 20ft Cinematic V5
=================================

INSTALL
Copy TPG_Rubble_Pile_20ft_Cinematic_V5 directly into:
Saved Games\DCS\Mods\tech\

MISSION EDITOR
Static Objects -> Structures -> TPG Rubble Pile 20ft Cinematic V5

COEXISTENCE
V5 uses unique plugin, unit, shape, database, texture and package namespaces and is designed to coexist with V1, HQ500 V2, Cinematic V3 and Cinematic V4.

V5 ART PASS
- Cartesian quad-grid mound surface removes the V4 top-down radial/starburst artifact.
- Rounded asymmetric crown with broad local collapse lobes and no center fan vertex.
- Rubble/fines PBR remains visible as interstitial filler between debris.
- Additional visible surface/perimeter concrete, CMU, brick and masonry chips.
- More readable construction trash around the edge and on the pile.
- Pipes use high-sided smooth cylinders and dedicated textured dirty/oxidized metal.
- Rebar uses 16-sided geometry, stronger ribs, cylindrical UVs and warmer oxidized steel texture instead of solid black.
- Official Eagle Dynamics Blender EDM exporter, LOD1, LOD2, destroyed state and collision shell retained.

PBR SOURCE
Powered by Poly Haven public API. Source maps are CC0.
'@
Set-Content -Path (Join-Path $pkg 'README.txt') -Value $readme -Encoding UTF8

$zip=Join-Path $root 'TPG_Rubble_Pile_20ft_Cinematic_V5_DCS_DropIn.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if(-not(Test-Path $zip)){throw 'Package ZIP was not created'}
& (Join-Path $env:GITHUB_WORKSPACE 'edm-jobs\validate_tpg_rubble_v5_package.ps1') -ZipPath $zip
Write-Host "Packaged and validated $zip"
