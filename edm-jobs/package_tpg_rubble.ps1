$ErrorActionPreference="Stop"
$root=Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$asset="TPG_Rubble_Pile_20ft_Cinematic_V3"
$display="TPG Rubble Pile 20ft Cinematic V3"
$pkg=Join-Path $root $asset
$shapes=Join-Path $pkg "Shapes"
$textures=Join-Path $pkg "Textures"
$db=Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models=@(
 "TPG_Rubble_Pile_20ft_Cinematic_V3.edm",
 "TPG_Rubble_Pile_20ft_Cinematic_V3_Destroyed.edm",
 "TPG_Rubble_Pile_20ft_Cinematic_V3_LOD1.edm",
 "TPG_Rubble_Pile_20ft_Cinematic_V3_LOD2.edm"
)
foreach($m in $models){
 $src=Join-Path $root $m
 if(-not(Test-Path $src)){throw "Missing required model: $m"}
 Copy-Item $src $shapes -Force
}

$lods=@"
model={
    lods={
        {"TPG_Rubble_Pile_20ft_Cinematic_V3.edm",350.0};
        {"TPG_Rubble_Pile_20ft_Cinematic_V3_LOD1.edm",1200.0};
        {"TPG_Rubble_Pile_20ft_Cinematic_V3_LOD2.edm",7000.0};
    };
    collision_shell="TPG_Rubble_Pile_20ft_Cinematic_V3.edm";
}
"@
Set-Content -Path (Join-Path $shapes "TPG_Rubble_Pile_20ft_Cinematic_V3.lods") -Value $lods -Encoding ASCII

if(Test-Path (Join-Path $root "Textures")){
 Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$entry=@"
declare_plugin("TPG Rubble Pile 20ft Cinematic V3",
{
    installed=true,
    dirName=current_mod_path,
    displayName=_("TPG Rubble Pile 20ft Cinematic V3"),
    version="3.0.0",
    state="installed",
    info=_("Cinematic photo-PBR 20 x 20 ft warzone rubble static structure; unique V3 namespace")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_pile_cinematic_v3.lua")
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
    Name="TPG_Rubble_Pile_20ft_Cinematic_V3",
    DisplayName=_("TPG Rubble Pile 20ft Cinematic V3"),
    ShapeName="TPG_Rubble_Pile_20ft_Cinematic_V3",
    ShapeNameDestr="TPG_Rubble_Pile_20ft_Cinematic_V3_Destroyed",
    Life=450,
    Rate=100,
    category="Structures",
    SeaObject=false,
    isPutToWater=false,
    numParking=0,
})
"@
Set-Content -Path (Join-Path $db "db_tpg_rubble_pile_cinematic_v3.lua") -Value $dbLua -Encoding UTF8

$readme=@"
TPG Rubble Pile 20ft Cinematic V3
=================================

COEXISTENCE
This is a separate DCS asset. It can be installed beside:
- TPG_Rubble_Pile_20ft_V1
- TPG_Rubble_Pile_20ft_HQ500_V2

Install
Copy only the folder "TPG_Rubble_Pile_20ft_Cinematic_V3" into:
Saved Games\DCS\Mods\tech\

Mission Editor
Static Objects -> Structures -> TPG Rubble Pile 20ft Cinematic V3

Cinematic V3 visual pass
- Solid irregular rubble/fines core to eliminate see-through/floating appearance
- ~3x denser visible fill and significantly more small/medium breakup
- Natural icosphere-derived broken concrete geometry replacing pyramid-like chunk shapes
- 8K photo-based PBR rubble/debris hero materials
- 4K photo-based PBR rough concrete, CMU, brick and rusty steel materials
- Normal maps and packed AO/Roughness/Metal maps on photo-PBR materials
- Ribbed dark-oxidized rebar geometry with dedicated normal/RoughMet maps
- Hollow-core CMU geometry, separate brick fragments, aggregate fracture faces
- Smaller, more numerous jagged slabs with embedded/bent rebar
- Structural steel, corrugated sheet, broken pipes, timber, wire and restrained trash
- Dedicated collision, LOD1, LOD2 and destroyed state

PBR source credit
Powered by Poly Haven public API.
Photo-based PBR source assets: rubble, concrete_debris, rough_concrete,
concrete_block_wall_03, red_bricks_02, rusty_metal_sheet.
The downloaded asset maps are CC0.
"@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip=Join-Path $root "TPG_Rubble_Pile_20ft_Cinematic_V3_DCS_DropIn.zip"
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if(-not(Test-Path $zip)){throw "Package ZIP was not created"}
& (Join-Path $env:GITHUB_WORKSPACE "edm-jobs\validate_tpg_rubble_package.ps1") -ZipPath $zip
Write-Host "Packaged and validated $zip"
