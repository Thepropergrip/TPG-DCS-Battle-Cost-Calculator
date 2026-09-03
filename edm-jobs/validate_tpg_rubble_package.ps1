param(
    [string]$ZipPath = ""
)

$ErrorActionPreference = "Stop"
$asset = "TPG_Rubble_Pile_20ft_HQ500_V2"
$oldAsset = "TPG_Rubble_Pile_20ft_V1"

if (-not $ZipPath) {
    $ZipPath = Join-Path $env:GITHUB_WORKSPACE "edm-artifacts\TPG_Rubble_Pile_20ft_HQ500_V2_DCS_DropIn.zip"
}
if (-not (Test-Path $ZipPath)) { throw "Rubble package ZIP missing: $ZipPath" }

$temp = Join-Path $env:RUNNER_TEMP ("tpg-rubble-validate-" + [guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $temp | Out-Null
try {
    Expand-Archive -Path $ZipPath -DestinationPath $temp -Force

    $top = Join-Path $temp $asset
    if (-not (Test-Path $top)) { throw "Expected unique top-level mod folder is missing: $asset" }

    $topEntries = @(Get-ChildItem -LiteralPath $temp -Force)
    if ($topEntries.Count -ne 1 -or $topEntries[0].Name -ne $asset) {
        throw "ZIP is not a clean one-folder DCS drop-in package."
    }

    $required = @(
        "entry.lua",
        "README.txt",
        "Database\db_tpg_rubble_pile_hq500_v2.lua",
        "Shapes\TPG_Rubble_Pile_20ft_HQ500_V2.edm",
        "Shapes\TPG_Rubble_Pile_20ft_HQ500_V2_Destroyed.edm",
        "Shapes\TPG_Rubble_Pile_20ft_HQ500_V2_LOD1.edm",
        "Shapes\TPG_Rubble_Pile_20ft_HQ500_V2_LOD2.edm",
        "Shapes\TPG_Rubble_Pile_20ft_HQ500_V2.lods"
    )
    foreach ($rel in $required) {
        $p = Join-Path $top $rel
        if (-not (Test-Path $p)) { throw "Required package file missing: $rel" }
        if ((Get-Item $p).PSIsContainer -eq $false -and (Get-Item $p).Length -le 0) {
            throw "Required package file is empty: $rel"
        }
    }

    $nested = Join-Path $top $asset
    if (Test-Path $nested) { throw "Double-nested mod folder detected." }

    foreach ($edm in Get-ChildItem (Join-Path $top "Shapes") -Filter *.edm -File) {
        if ($edm.Length -lt 1024) { throw "Suspiciously small EDM: $($edm.Name) $($edm.Length) bytes" }
    }

    $textures = @(Get-ChildItem (Join-Path $top "Textures") -Filter *.png -File)
    if ($textures.Count -lt 20) {
        throw "Expected full albedo + RoughMet texture set; found only $($textures.Count) PNG files."
    }

    $entry = Get-Content (Join-Path $top "entry.lua") -Raw
    if ($entry -notmatch "mount_vfs_model_path" -or $entry -notmatch "mount_vfs_texture_path") {
        throw "entry.lua is missing DCS model/texture mount calls."
    }

    $db = Get-Content (Join-Path $top "Database\db_tpg_rubble_pile_hq500_v2.lua") -Raw
    foreach ($token in @("TPG_Rubble_Pile_20ft_HQ500_V2","TPG_Rubble_Pile_20ft_HQ500_V2_Destroyed","Structures")) {
        if ($db -notmatch [regex]::Escape($token)) { throw "Database registration missing token: $token" }
    }

    if ($db -match 'Name\s*=\s*"TPG_Rubble_Pile_20ft_V1"') {
        throw "Database unit Name still collides with the old V1 asset."
    }
    if ($entry -match 'declare_plugin\("TPG Rubble Pile 20ft V1"') {
        throw "Plugin name still collides with the old V1 asset."
    }

    Write-Host "TPG_RUBBLE_COEXISTENCE_VALIDATION_SUCCESS"
    Write-Host "Unique asset ID: $asset"
    Write-Host "Original preserved ID: $oldAsset"
    Write-Host "ZIP: $ZipPath"
    Write-Host "Textures: $($textures.Count)"
}
finally {
    if (Test-Path $temp) { Remove-Item $temp -Recurse -Force }
}
