$ErrorActionPreference="Stop"
$root=Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$asset="TPG_Rubble_Pile_20ft_Cinematic_V4"
$display="TPG Rubble Pile 20ft Cinematic V4"
$pkg=Join-Path $root $asset
$shapes=Join-Path $pkg "Shapes"
$textures=Join-Path $pkg "Textures"
$db=Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models=@(
 "TPG_Rubble_Pile_20ft_Cinematic_V4.edm",
 "TPG_Rubble_Pile_20ft_Cinematic_V4_Destroyed.edm",
 "TPG_Rubble_Pile_20ft_Cinematic_V4_LOD1.edm",
 "TPG_Rubble_Pile_20ft_Cinematic_V4_LOD2.edm"
)
foreach($m in $models){
 $src=Join-Path $root $m
 if(-not(Test-Path $src)){throw "Missing required model: $m"}
 Copy-Item $src $shapes -Force
}

$lods=@"
model={
    lods={
        {"TPG_Rubble_Pile_20ft_Cinematic_V4.edm",350.0};
        {"TPG_Rubble_Pile_20ft_Cinematic_V4_LOD1.edm",1200.0};
        {"TPG_Rubble_Pile_20ft_Cinematic_V4_LOD2.edm",7000.0};
    };
    collision_shell="TPG_Rubble_Pile_20ft_Cinematic_V4.edm";
}
"@
Set-Content -Path (Join-Path $shapes "TPG_Rubble_Pile_20ft_Cinematic_V4.lods") -Value $lods -Encoding ASCII

$srcTex=Join-Path $root "Textures"
if(-not(Test-Path $srcTex)){throw "Texture staging folder missing"}
$dds=@(Get-ChildItem $srcTex -Filter *.dds -File)
if($dds.Count -lt 45){throw "Expected at least 45 DDS textures; found $($dds.Count)"}
Copy-Item (Join-Path $srcTex "*.dds") $textures -Force

$entry=@"
declare_plugin("TPG Rubble Pile 20ft Cinematic V4",
{
    installed=true,
    dirName=current_mod_path,
    displayName=_("TPG Rubble Pile 20ft Cinematic V4"),
    version="4.0.0",
    state="installed",
    info=_("Cinematic photo-PBR 20 x 20 ft warzone rubble static structure; optimized BC7 DDS textures; unique V4 namespace")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_pile_cinematic_v4.lua")
plugin_done()
"@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua=@"
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
    Name="TPG_Rubble_Pile_20ft_Cinematic_V4",
    DisplayName=_("TPG Rubble Pile 20ft Cinematic V4"),
    ShapeName="TPG_Rubble_Pile_20ft_Cinematic_V4",
    ShapeNameDestr="TPG_Rubble_Pile_20ft_Cinematic_V4_Destroyed",
    Life=450,
    Rate=100,
    category="Structures",
    SeaObject=false,
    isPutToWater=false,
    numParking=0,
})
"@
Set-Content -Path (Join-Path $db "db_tpg_rubble_pile_cinematic_v4.lua") -Value $dbLua -Encoding UTF8

$readme=@"
TPG Rubble Pile 20ft Cinematic V4
=================================

COEXISTENCE
This is a new unique DCS asset. It can be installed beside V1, HQ500 V2, and Cinematic V3.
Do not delete the older versions.

INSTALL
Copy the folder "TPG_Rubble_Pile_20ft_Cinematic_V4" directly into:
Saved Games\DCS\Mods\tech\

MISSION EDITOR
Static Objects -> Structures -> TPG Rubble Pile 20ft Cinematic V4

V4 VISUAL / DELIVERY PASS
- Dense closed rubble/fines core: no zero-gravity see-through center
- Roughly triple the fine/small/medium infill of the earlier pile
- Natural fractured concrete chunks instead of pyramid-like debris
- 8K photo-based PBR hero albedo for rubble and concrete debris
- 4K photo-based PBR hero normal maps
- 4K photo-based concrete, CMU, brick, and rusty-metal albedo
- BC7 DDS compression with full mip chains for DCS-ready memory/streaming behavior
- Real normal-map and RoughMet inputs through the official ED material path
- Ribbed dark oxidized rebar geometry with dedicated high-detail normal/RoughMet maps
- Hollow-core CMU geometry and distinct brick fragments
- More numerous irregular slabs with aggregate fracture edges and embedded bent rebar
- Structural steel, corrugated sheet, broken pipes, wood, wire, and restrained trash
- Dedicated collision, LOD1, LOD2, and destroyed state
- Fully unique V4 folder/plugin/unit/shape/texture namespace

PBR SOURCE
Powered by Poly Haven public API.
Photo-based PBR source assets: rubble, concrete_debris, rough_concrete,
concrete_block_wall_03, red_bricks_02, rusty_metal_sheet.
Source maps are CC0.
"@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip=Join-Path $root "TPG_Rubble_Pile_20ft_Cinematic_V4_DCS_DropIn.zip"
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if(-not(Test-Path $zip)){throw "Package ZIP was not created"}
& (Join-Path $env:GITHUB_WORKSPACE "edm-jobs\validate_tpg_rubble_package.ps1") -ZipPath $zip
Write-Host "Packaged and validated $zip"
