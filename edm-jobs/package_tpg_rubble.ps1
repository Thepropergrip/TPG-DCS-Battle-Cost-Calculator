$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$asset = "TPG_Rubble_Pile_20ft_HQ500_V2"
$display = "TPG Rubble Pile 20ft HQ500 V2"
$pkg = Join-Path $root $asset
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models = @(
  "$asset.edm",
  "TPG_Rubble_Pile_20ft_HQ500_V2_Destroyed.edm",
  "TPG_Rubble_Pile_20ft_HQ500_V2_LOD1.edm",
  "TPG_Rubble_Pile_20ft_HQ500_V2_LOD2.edm"
)
foreach ($m in $models) {
  $src = Join-Path $root $m
  if (-not (Test-Path $src)) { throw "Missing required model: $m" }
  Copy-Item $src $shapes -Force
}

$lods = @"
model={
    lods={
        {"TPG_Rubble_Pile_20ft_HQ500_V2.edm",350.0};
        {"TPG_Rubble_Pile_20ft_HQ500_V2_LOD1.edm",1200.0};
        {"TPG_Rubble_Pile_20ft_HQ500_V2_LOD2.edm",7000.0};
    };
    collision_shell="TPG_Rubble_Pile_20ft_HQ500_V2.edm";
}
"@
Set-Content -Path (Join-Path $shapes "$asset.lods") -Value $lods -Encoding ASCII

if (Test-Path (Join-Path $root "Textures")) {
    Copy-Item (Join-Path $root "Textures\*") $textures -Force
}

$entry = @"
declare_plugin("TPG Rubble Pile 20ft HQ500 V2",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Rubble Pile 20ft HQ500 V2"),
    version = "2.0.0",
    state = "installed",
    info = _("HQ500 high-density 20 x 20 ft warzone rubble static structure; unique ID/folder so it coexists with TPG Rubble Pile 20ft V1")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_pile_hq500_v2.lua")
plugin_done()
"@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @"
local function add_structure(f)
    f.shape_table_data = {
        {
            file = f.ShapeName,
            life = f.Life,
            username = f.Name,
            desrt = f.ShapeNameDestr or "self",
            classname = "lLandVehicle",
            positioning = "BYNORMAL",
        }
    }
    if f.ShapeNameDestr then
        f.shape_table_data[#f.shape_table_data + 1] = { name = f.ShapeNameDestr, file = f.ShapeNameDestr }
    end
    f.mapclasskey = "P0091000076"
    f.attribute = {wsType_Static, wsType_Standing, "Structures"}
    add_surface_unit(f)
end

add_structure({
    Name = "TPG_Rubble_Pile_20ft_HQ500_V2",
    DisplayName = _("TPG Rubble Pile 20ft HQ500 V2"),
    ShapeName = "TPG_Rubble_Pile_20ft_HQ500_V2",
    ShapeNameDestr = "TPG_Rubble_Pile_20ft_HQ500_V2_Destroyed",
    Life = 450,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
"@
Set-Content -Path (Join-Path $db "db_tpg_rubble_pile_hq500_v2.lua") -Value $dbLua -Encoding UTF8

$readme = @"
TPG Rubble Pile 20ft HQ500 V2
================================

COEXISTENCE:
This is a separate DCS asset from TPG_Rubble_Pile_20ft_V1.
Do NOT delete the original V1. Both folders can be installed at the same time.

Install:
Copy the folder "TPG_Rubble_Pile_20ft_HQ500_V2" into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Rubble Pile 20ft HQ500 V2

Unique identifiers:
- Plugin: TPG Rubble Pile 20ft HQ500 V2
- Folder: TPG_Rubble_Pile_20ft_HQ500_V2
- DCS unit Name: TPG_Rubble_Pile_20ft_HQ500_V2
- Shape: TPG_Rubble_Pile_20ft_HQ500_V2
- Destroyed shape: TPG_Rubble_Pile_20ft_HQ500_V2_Destroyed

HQ500 visual target:
- Dense filled rubble core with no see-through suspended appearance
- 2K hero concrete, fractured aggregate, CMU, brick, debris fines and dark-rust rebar textures
- Ribbed rebar geometry with oxidized/rusty-black steel treatment
- Porous cinderblock/CMU material and true hollow-core CMU geometry
- Distinct fired-brick material and brick fragments
- Irregular fractured slabs with aggregate fracture faces and embedded rebar
- Dense small/medium infill, debris skirt and terrain-integrated lower rubble
- Broken pipes, structural steel, corrugated sheet, wood, wire and restrained trash
- Dedicated collision, LOD1, LOD2 and destroyed state
"@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Rubble_Pile_20ft_HQ500_V2_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if (-not (Test-Path $zip)) { throw "Package ZIP was not created" }
& (Join-Path $env:GITHUB_WORKSPACE "edm-jobs\validate_tpg_rubble_package.ps1") -ZipPath $zip
Write-Host "Packaged and validated coexistable asset: $zip"
