$ErrorActionPreference = "Stop"
$root = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts"
$pkg = Join-Path $root "TPG_Rubble_Pile_20ft_V1"
$shapes = Join-Path $pkg "Shapes"
$textures = Join-Path $pkg "Textures"
$db = Join-Path $pkg "Database"
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null

$models = @(
  "TPG_Rubble_Pile_20ft_V1.edm",
  "TPG_Rubble_Pile_20ft_V1_Destroyed.edm",
  "TPG_Rubble_Pile_20ft_V1_LOD1.edm",
  "TPG_Rubble_Pile_20ft_V1_LOD2.edm"
)
foreach ($m in $models) {
  $src = Join-Path $root $m
  if (-not (Test-Path $src)) { throw "Missing required model: $m" }
  Copy-Item $src $shapes -Force
}

$lods = @'
model={
    lods={
        {"TPG_Rubble_Pile_20ft_V1.edm",350.0};
        {"TPG_Rubble_Pile_20ft_V1_LOD1.edm",1200.0};
        {"TPG_Rubble_Pile_20ft_V1_LOD2.edm",7000.0};
    };
    collision_shell="TPG_Rubble_Pile_20ft_V1.edm";
}
'@
Set-Content -Path (Join-Path $shapes "TPG_Rubble_Pile_20ft_V1.lods") -Value $lods -Encoding ASCII

if (Test-Path (Join-Path $root "Textures")) { Copy-Item (Join-Path $root "Textures\*") $textures -Force }

$entry = @'
declare_plugin("TPG Rubble Pile 20ft V1",
{
    installed = true,
    dirName = current_mod_path,
    displayName = _("TPG Rubble Pile 20ft V1"),
    version = "1.0.0",
    state = "installed",
    info = _("High-detail 20 x 20 ft warzone building rubble static structure")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_pile.lua")
plugin_done()
'@
Set-Content -Path (Join-Path $pkg "entry.lua") -Value $entry -Encoding UTF8

$dbLua = @'
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
    Name = "TPG_Rubble_Pile_20ft_V1",
    DisplayName = _("TPG Rubble Pile 20ft V1"),
    ShapeName = "TPG_Rubble_Pile_20ft_V1",
    ShapeNameDestr = "TPG_Rubble_Pile_20ft_V1_Destroyed",
    Life = 450,
    Rate = 100,
    category = "Structures",
    SeaObject = false,
    isPutToWater = false,
    numParking = 0,
})
'@
Set-Content -Path (Join-Path $db "db_tpg_rubble_pile.lua") -Value $dbLua -Encoding UTF8

$readme = @'
TPG Rubble Pile 20ft V1
========================

Install:
Copy the folder "TPG_Rubble_Pile_20ft_V1" into:
  Saved Games\DCS\Mods\tech\

Mission Editor:
Static Objects -> Structures -> TPG Rubble Pile 20ft V1

Design target:
- Roughly 20 x 20 ft / 6.1 x 6.1 m irregular warzone rubble mound
- No raised terrain bed and no visible ground plane
- Lower debris intentionally embeds slightly into terrain to integrate with map rocks
- Shattered concrete and aggregate, slabs, masonry/cinder-block fragments
- Exposed and loose rusty rebar
- Broken dirty/rusted pipes
- Bent sheet metal and beam fragments
- Broken timber, draped wire/cable, sparse authentic trash/plastic
- Material-specific roughness, rust, grime and surface variation
- Dedicated simplified collision masses
- Hero model plus LOD1 and LOD2
- Separate further-blasted/scorched destruction state

The model is intended as the first member of a future TPG rubble library with multiple footprints, silhouettes, materials and regional/map-specific debris mixes.
'@
Set-Content -Path (Join-Path $pkg "README.txt") -Value $readme -Encoding UTF8

$zip = Join-Path $root "TPG_Rubble_Pile_20ft_V1_DCS_DropIn.zip"
if (Test-Path $zip) { Remove-Item $zip -Force }
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if (-not (Test-Path $zip)) { throw "Package ZIP was not created" }
& (Join-Path $env:GITHUB_WORKSPACE "edm-jobs\validate_tpg_rubble_package.ps1") -ZipPath $zip
if ($LASTEXITCODE -ne 0) { throw "Final rubble package validation failed." }
Write-Host "Packaged and validated $zip"
