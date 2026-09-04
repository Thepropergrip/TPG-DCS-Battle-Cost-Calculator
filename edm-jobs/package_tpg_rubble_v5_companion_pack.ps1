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

# Visible/DCS-facing names are deliberately plain descriptive names.
# Life is an initial gameplay tuning pass: larger rubble masses are tougher,
# while no piece is intended to reliably protect against a direct 500 lb-class bomb.
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
  foreach($s in @('', '_Destroyed', '_LOD1', '_LOD2')){
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
    collision_shell="$a.edm";
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
    version="1.0.0",
    state="installed",
    info=_("Six high-detail rubble shapes using the Cinematic V5 material family, rigid full-scale debris and durable collision cover")
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
TPG Rubble Shape Pack
=====================

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

GEOMETRY / SCALE
This revision does NOT stretch visible rubble to create the alternate silhouettes.
Bricks, hollow CMUs, pipes, rebar, slabs, beams, wood and trash retain their original
Cinematic V5 dimensions and proportions. The pile is reshaped by changing the continuous
rubble/fines envelope and rigidly relocating complete debris objects/assemblies.

WALL LEAN
The wall-contact piece has a straight ~10 ft wall edge at its placement origin and a much
shorter tapered outward toe. Its top-view footprint is intentionally trapezoidal rather
than square, making the wall-facing direction visually obvious during Mission Editor placement.

DURABILITY / COVER
The database assigns real static-object Life values and the EDMs include collision geometry.
Initial Life tuning ranges from 850 for the small pile to 1750 for the largest multi-hump pile.
The intended gameplay target is that larger pieces can absorb roughly several direct tank hits
and about 5-7 artillery impacts while still acting as physical cover. Exact hit counts vary with
weapon, impact point, fuze and blast calculation in DCS, so runtime combat testing is authoritative.
A direct 500 lb-class bomb is NOT intended to provide reliable protection; at most the rubble should
offer limited mitigation depending on stand-off/impact geometry.

COEXISTENCE
This is a new clean-name pack with unique DCS identities. It can coexist with:
- TPG Rubble Pile 20ft Cinematic V5
- the earlier Cinematic V5 Companion Pack

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
