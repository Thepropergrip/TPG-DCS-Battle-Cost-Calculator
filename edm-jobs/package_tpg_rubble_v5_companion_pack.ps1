param()
$ErrorActionPreference='Stop'
$root=Join-Path $env:GITHUB_WORKSPACE 'edm-artifacts'
$asset='TPG_Rubble_Companion_Pack_Cinematic_V5'
$pkg=Join-Path $root $asset
$shapes=Join-Path $pkg 'Shapes'
$textures=Join-Path $pkg 'Textures'
$db=Join-Path $pkg 'Database'
if(Test-Path $pkg){Remove-Item $pkg -Recurse -Force}
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$defs=@(
  @{Name='TPG_Rubble_SmallLow_Cinematic_V5A'; Display='TPG Rubble Small Low Cinematic V5A'},
  @{Name='TPG_Rubble_Pushed_Cinematic_V5B'; Display='TPG Rubble Tractor-Pushed Cinematic V5B'},
  @{Name='TPG_Rubble_Rectangular_Cinematic_V5C'; Display='TPG Rubble Rectangular Cinematic V5C'},
  @{Name='TPG_Rubble_BuildingFace_Cinematic_V5D'; Display='TPG Rubble Building-Face Cinematic V5D'},
  @{Name='TPG_Rubble_Ridge_Cinematic_V5E'; Display='TPG Rubble Long Ridge Cinematic V5E'},
  @{Name='TPG_Rubble_MultiHump_Cinematic_V5F'; Display='TPG Rubble Multi-Hump Cinematic V5F'}
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
        {\"$a.edm\",350.0};
        {\"${a}_LOD1.edm\",1200.0};
        {\"${a}_LOD2.edm\",7000.0};
    };
    collision_shell=\"$a.edm\";
}
"@
  Set-Content -Path (Join-Path $shapes "$a.lods") -Value $lods -Encoding ASCII
}

# All six pieces intentionally share the exact Cinematic V5 texture/material family.
# The textures are copied once for the whole pack, not duplicated per shape.
$srcTex=Join-Path $root 'Textures'
if(-not(Test-Path $srcTex)){throw 'Texture staging folder missing'}
$dds=@(Get-ChildItem $srcTex -Filter *.dds -File)
if($dds.Count -lt 45){throw "Expected at least 45 shared Cinematic V5 DDS textures; found $($dds.Count)"}
Copy-Item (Join-Path $srcTex '*.dds') $textures -Force

$entry=@'
declare_plugin("TPG Rubble Companion Pack Cinematic V5",
{
    installed=true,
    dirName=current_mod_path,
    displayName=_("TPG Rubble Companion Pack Cinematic V5"),
    version="5.1.0",
    state="installed",
    info=_("Six additional high-detail Cinematic V5 rubble silhouettes sharing the same PBR rubble, masonry, trash, round pipes and oxidized ribbed rebar")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_companion_pack_cinematic_v5.lua")
plugin_done()
'@
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
$dbText=$dbHead
foreach($d in $defs){
  $a=$d.Name
  $display=$d.Display
  $dbText += @"
add_structure({
    Name=\"$a\",
    DisplayName=_(\"$display\"),
    ShapeName=\"$a\",
    ShapeNameDestr=\"${a}_Destroyed\",
    Life=450,
    Rate=100,
    category=\"Structures\",
    SeaObject=false,
    isPutToWater=false,
    numParking=0,
})

"@
}
Set-Content -Path (Join-Path $db 'db_tpg_rubble_companion_pack_cinematic_v5.lua') -Value $dbText -Encoding UTF8

$readme=@'
TPG Rubble Companion Pack Cinematic V5
======================================

INSTALL
Copy TPG_Rubble_Companion_Pack_Cinematic_V5 directly into:
Saved Games\DCS\Mods\tech\

MISSION EDITOR
Static Objects -> Structures

INCLUDED PIECES
1. TPG Rubble Small Low Cinematic V5A
   Approx. 12 x 12 ft. Low, compact rubble mound for filler/roadside/yard placement.

2. TPG Rubble Tractor-Pushed Cinematic V5B
   Approx. 18 x 12 ft. Asymmetrical small-machine pushed pile with compressed front and dragged tail.

3. TPG Rubble Rectangular Cinematic V5C
   Approx. 20 x 10 ft. Elongated, somewhat rectangular rubble bed for lots, curbs and structure edges.

4. TPG Rubble Building-Face Cinematic V5D
   Approx. 10 ft wall section. Origin is on the tall rough face so it can be placed flush against a building;
   the rubble falls/slopes outward from that near-vertical contact face.

5. TPG Rubble Long Ridge Cinematic V5E
   Approx. 24 x 8 ft. Long narrow windrow/ridge with a slightly irregular spine.

6. TPG Rubble Multi-Hump Cinematic V5F
   Approx. 22 x 18 ft. Three connected collapse lobes with lower saddles between them.

SHARED CINEMATIC V5 ART LANGUAGE
- Exact same Cinematic V5 PBR rubble/fines, concrete debris, brick and CMU texture family.
- Exact same round dirty/oxidized pipe treatment.
- Exact same warmer oxidized ribbed rebar treatment.
- Same slabs, masonry, metal, wood, wire and construction-trash vocabulary.
- Same no-spoke/no-radial-fan mound technology.
- Shared textures are stored only once for all six pieces.
- Each piece has its own intact EDM, destroyed EDM, LOD1, LOD2, .lods file and unique DCS database identity.

COEXISTENCE
This companion pack is a separate plugin/folder/database identity and does not replace the original
TPG Rubble Pile 20ft Cinematic V5. The shared TPG_CIN5 texture filenames are intentionally byte-identical
with the original V5 material family, so either mounted copy resolves to the same artwork.

EXPORT
Built with Blender 4.1.1 and the official Eagle Dynamics Blender EDM exporter.
'@
Set-Content -Path (Join-Path $pkg 'README.txt') -Value $readme -Encoding UTF8

$zip=Join-Path $root 'TPG_Rubble_Companion_Pack_Cinematic_V5_DCS_DropIn.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if(-not(Test-Path $zip)){throw 'Package ZIP was not created'}
& (Join-Path $env:GITHUB_WORKSPACE 'edm-jobs\validate_tpg_rubble_v5_companion_pack.ps1') -ZipPath $zip
Write-Host "Packaged and validated $zip"
