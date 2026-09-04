param()
$ErrorActionPreference='Stop'
$root=Join-Path $env:GITHUB_WORKSPACE 'edm-artifacts'
$asset='TPG_Rubble_Shape_Pack'
$pkg=Join-Path $root $asset
$shapes=Join-Path $pkg 'Shapes'
$textures=Join-Path $pkg 'Textures'
$db=Join-Path $pkg 'Database'
if(Test-Path $pkg){Remove-Item $pkg -Recurse -Force}
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$defs=@(
  @{Name='TPG_Rubble_Small_Low';        Display='TPG Rubble Small Low';        Life=850},
  @{Name='TPG_Rubble_Tractor_Pushed';   Display='TPG Rubble Tractor Pushed';   Life=1200},
  @{Name='TPG_Rubble_Long_Rectangular'; Display='TPG Rubble Long Rectangular'; Life=1350},
  @{Name='TPG_Rubble_Wall_Lean';        Display='TPG Rubble Wall Lean';        Life=1400},
  @{Name='TPG_Rubble_Long_Ridge';       Display='TPG Rubble Long Ridge';       Life=1450},
  @{Name='TPG_Rubble_Multi_Hump';       Display='TPG Rubble Multi Hump';       Life=1750}
)

foreach($d in $defs){
  $a=$d.Name
  foreach($s in @('', '_Destroyed', '_LOD1', '_LOD2', '_Collision')){
    $m="$a$s.edm"
    $src=Join-Path $root $m
    if(-not(Test-Path $src)){throw "Missing required model: $m"}
    Copy-Item $src $shapes -Force
  }
  $lods=@"
model={
    lods={
        {"$a.edm",350.0};
        {"${a}_LOD1.edm",1200.0};
        {"${a}_LOD2.edm",7000.0};
    };
    collision_shell="${a}_Collision.edm";
}
"@
  Set-Content -Path (Join-Path $shapes "$a.lods") -Value $lods -Encoding ASCII
}

# Shared exact Cinematic V5 texture family, copied once for all six shapes.
$srcTex=Join-Path $root 'Textures'
if(-not(Test-Path $srcTex)){throw 'Texture staging folder missing'}
$dds=@(Get-ChildItem $srcTex -Filter *.dds -File)
if($dds.Count -lt 45){throw "Expected at least 45 shared Cinematic V5 DDS textures; found $($dds.Count)"}
Copy-Item (Join-Path $srcTex '*.dds') $textures -Force

$entry=@'
declare_plugin("TPG Rubble Shape Pack",
{
    installed=true,
    dirName=current_mod_path,
    displayName=_("TPG Rubble Shape Pack"),
    version="1.1.0",
    state="installed",
    info=_("Six high-detail rubble shapes using Cinematic V5 materials, terrain-locked placement and dedicated physical cover collision shells")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_shape_pack.lua")
plugin_done()
'@
$entry=$entry.Replace('\"','"')
Set-Content -Path (Join-Path $pkg 'entry.lua') -Value $entry -Encoding UTF8

$dbHead=@'
local function add_structure(f)
    f.shape_table_data={
        {
            file=f.ShapeName,
            life=f.Life,
            username=f.Name,
            desrt=f.ShapeNameDestr or "self",
            classname="lLandVehicle",
            positioning="ONLYHEIGTH",
        }
    }
    if f.ShapeNameDestr then
        f.shape_table_data[#f.shape_table_data+1]={name=f.ShapeNameDestr,file=f.ShapeNameDestr}
    end
    f.mapclasskey="P0091000076"
    f.attribute={wsType_Static,wsType_Standing,"Structures"}
    add_surface_unit(f)
end

'@
$dbHead=$dbHead.Replace('\"','"')
$dbText=$dbHead
foreach($d in $defs){
  $a=$d.Name
  $display=$d.Display
  $life=$d.Life
  $dbText += @"
add_structure({
    Name="$a",
    DisplayName=_("$display"),
    ShapeName="$a",
    ShapeNameDestr="${a}_Destroyed",
    Life=$life,
    Rate=100,
    category="Structures",
    SeaObject=false,
    isPutToWater=false,
    numParking=0,
})

"@
}
Set-Content -Path (Join-Path $db 'db_tpg_rubble_shape_pack.lua') -Value $dbText -Encoding UTF8

$readme=@'
TPG Rubble Shape Pack v1.1
==========================

INSTALL
Copy TPG_Rubble_Shape_Pack directly into:
Saved Games\DCS\Mods\tech\

MISSION EDITOR
Static Objects -> Structures

INCLUDED
- TPG Rubble Small Low
- TPG Rubble Tractor Pushed
- TPG Rubble Long Rectangular
- TPG Rubble Wall Lean
- TPG Rubble Long Ridge
- TPG Rubble Multi Hump

TERRAIN-LOCKED PLACEMENT
This revision uses DCS positioning="ONLYHEIGTH" instead of BYNORMAL. The intent is to keep
rubble referenced to terrain height when its footprint overlaps scenery/buildings, allowing the
visual rubble to clip into a wall/building instead of being promoted onto the contacted roof/top.
Runtime DCS placement remains authoritative because scenery interaction can vary by object/map.

DEDICATED COLLISION SHELLS
Each of the six statics now has its own separate *_Collision.edm. The .lods file references that
simplified physical hull instead of using the entire high-detail visible rubble EDM as collision.
The collision hull follows the useful mass of each pile so vehicles/projectiles can still be blocked,
while protruding pipes, rebar, bricks and high visual fragments no longer define collision behavior.
The Wall Lean collision shell is a tapered wedge with Y=0 as the wall-contact edge.

GEOMETRY / SCALE
Visible bricks, hollow CMUs, pipes, rebar, slabs, beams, wood and trash retain their original
Cinematic V5 dimensions and proportions. Alternate silhouettes are made by reshaping the continuous
rubble/fines envelope and rigidly relocating complete debris objects/assemblies.

WALL LEAN
The wall-contact piece has a straight ~10 ft wall edge at its placement origin and a shorter tapered
outward toe. Its top-view footprint is intentionally trapezoidal rather than square, making the
wall-facing direction visually obvious in Mission Editor placement.

DURABILITY / COVER
Static Life values remain tuned from 850 to 1750. Larger rubble masses are intended to absorb several
tank hits and multiple artillery impacts while functioning as physical cover. Exact hit counts vary
by weapon, impact point, fuze and blast calculation. A direct 500 lb-class bomb is not intended to
provide reliable protection.

COEXISTENCE
This clean-name pack keeps the same DCS identities as v1.0 so v1.1 is an in-place upgrade of
TPG_Rubble_Shape_Pack. It remains separate from the original Cinematic V5 pile and the older
Cinematic V5 Companion Pack.

SHARED ART
Uses the same Cinematic V5 PBR rubble/fines, concrete, brick, CMU, round dirty pipes,
oxidized ribbed rebar, metal, wood and construction-trash texture/material family.

EXPORT
Built with Blender 4.1.1 and the official Eagle Dynamics Blender EDM exporter.
'@
Set-Content -Path (Join-Path $pkg 'README.txt') -Value $readme -Encoding UTF8

$zip=Join-Path $root 'TPG_Rubble_Shape_Pack_DCS_DropIn.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if(-not(Test-Path $zip)){throw 'Package ZIP was not created'}
& (Join-Path $env:GITHUB_WORKSPACE 'edm-jobs\validate_tpg_rubble_v5_companion_pack.ps1') -ZipPath $zip
Write-Host "Packaged and validated $zip"
