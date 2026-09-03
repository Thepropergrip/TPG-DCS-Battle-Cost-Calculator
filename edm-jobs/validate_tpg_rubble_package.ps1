param([string]$ZipPath="")
$ErrorActionPreference="Stop"
$asset="TPG_Rubble_Pile_20ft_Cinematic_V4"
if(-not $ZipPath){$ZipPath=Join-Path $env:GITHUB_WORKSPACE "edm-artifacts\TPG_Rubble_Pile_20ft_Cinematic_V4_DCS_DropIn.zip"}
if(-not(Test-Path $ZipPath)){throw "Missing ZIP: $ZipPath"}

$tmp=Join-Path $env:RUNNER_TEMP ("tpg-rubble-v4-"+[guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
try{
 Expand-Archive -Path $ZipPath -DestinationPath $tmp -Force
 $top=Join-Path $tmp $asset
 if(-not(Test-Path $top)){throw "Unique V4 top folder missing"}
 $entries=@(Get-ChildItem $tmp -Force)
 if($entries.Count -ne 1 -or $entries[0].Name -ne $asset){throw "ZIP is not a clean single-folder DCS drop-in"}

 $required=@(
  "entry.lua","README.txt","Database\db_tpg_rubble_pile_cinematic_v4.lua",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V4.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V4_Destroyed.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V4_LOD1.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V4_LOD2.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V4.lods"
 )
 foreach($rel in $required){
  $p=Join-Path $top $rel
  if(-not(Test-Path $p)){throw "Missing: $rel"}
  if((Get-Item $p).PSIsContainer -eq $false -and (Get-Item $p).Length -le 0){throw "Empty: $rel"}
 }

 foreach($edm in Get-ChildItem (Join-Path $top "Shapes") -Filter *.edm -File){
  if($edm.Length -lt 4096){throw "Suspiciously small EDM: $($edm.Name)"}
 }

 $dds=@(Get-ChildItem (Join-Path $top "Textures") -Filter *.dds -File)
 if($dds.Count -lt 45){throw "Too few DDS texture maps: $($dds.Count)"}
 $png=@(Get-ChildItem (Join-Path $top "Textures") -Filter *.png -File)
 if($png.Count -ne 0){throw "PNG source/build textures leaked into shipping package"}

 $requiredTex=@(
  "TPG_CIN4_RubbleBase_diff.dds","TPG_CIN4_RubbleBase_arm.dds","TPG_CIN4_RubbleBase_nor_gl.dds",
  "TPG_CIN4_ConcreteDebris_diff.dds","TPG_CIN4_ConcreteDebris_arm.dds","TPG_CIN4_ConcreteDebris_nor_gl.dds",
  "TPG_CIN4_RoughConcrete_diff.dds","TPG_CIN4_CMU_diff.dds","TPG_CIN4_Brick_diff.dds","TPG_CIN4_RustMetal_diff.dds",
  "TPG_CIN4_RebarDarkOxide.dds","TPG_CIN4_RebarDarkOxide_Normal.dds","TPG_CIN4_RebarDarkOxide_RoughMet.dds"
 )
 foreach($t in $requiredTex){
  if(-not(Test-Path (Join-Path $top "Textures\$t"))){throw "Missing V4 DDS map: $t"}
 }

 $dbText=Get-Content (Join-Path $top "Database\db_tpg_rubble_pile_cinematic_v4.lua") -Raw
 foreach($old in @("TPG_Rubble_Pile_20ft_V1","TPG_Rubble_Pile_20ft_HQ500_V2","TPG_Rubble_Pile_20ft_Cinematic_V3")){
  if($dbText -match ('Name\s*=\s*"' + [regex]::Escape($old) + '"')){throw "Coexistence collision with $old"}
 }
 if($dbText -notmatch [regex]::Escape($asset)){throw "V4 asset ID missing from database"}

 Write-Host "TPG_RUBBLE_CINEMATIC_V4_VALIDATION_SUCCESS"
 Write-Host "DDS textures: $($dds.Count)"
 Write-Host "ZIP bytes: $((Get-Item $ZipPath).Length)"
}
finally{
 if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force}
}
