param([string]$ZipPath="")
$ErrorActionPreference="Stop"
$asset="TPG_Rubble_Pile_20ft_Cinematic_V3"
if(-not $ZipPath){$ZipPath=Join-Path $env:GITHUB_WORKSPACE "edm-artifacts\TPG_Rubble_Pile_20ft_Cinematic_V3_DCS_DropIn.zip"}
if(-not(Test-Path $ZipPath)){throw "Missing ZIP: $ZipPath"}

$tmp=Join-Path $env:RUNNER_TEMP ("tpg-rubble-v3-"+[guid]::NewGuid().ToString("N"))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
try{
 Expand-Archive -Path $ZipPath -DestinationPath $tmp -Force
 $top=Join-Path $tmp $asset
 if(-not(Test-Path $top)){throw "Unique V3 top folder missing"}
 $topEntries=@(Get-ChildItem $tmp -Force)
 if($topEntries.Count -ne 1 -or $topEntries[0].Name -ne $asset){throw "ZIP is not a single clean drop-in folder"}

 $required=@(
  "entry.lua","README.txt","Database\db_tpg_rubble_pile_cinematic_v3.lua",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V3.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V3_Destroyed.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V3_LOD1.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V3_LOD2.edm",
  "Shapes\TPG_Rubble_Pile_20ft_Cinematic_V3.lods"
 )
 foreach($rel in $required){
  $p=Join-Path $top $rel
  if(-not(Test-Path $p)){throw "Missing: $rel"}
  if((Get-Item $p).PSIsContainer -eq $false -and (Get-Item $p).Length -le 0){throw "Empty: $rel"}
 }

 foreach($edm in Get-ChildItem (Join-Path $top "Shapes") -Filter *.edm -File){
  if($edm.Length -lt 4096){throw "Suspiciously small EDM: $($edm.Name)"}
 }

 $textures=@(Get-ChildItem (Join-Path $top "Textures") -Filter *.png -File)
 if($textures.Count -lt 30){throw "Too few texture maps: $($textures.Count)"}

 $requiredTex=@(
  "TPG_CIN3_RubbleBase_diff.png","TPG_CIN3_RubbleBase_arm.png","TPG_CIN3_RubbleBase_nor_gl.png",
  "TPG_CIN3_ConcreteDebris_diff.png","TPG_CIN3_ConcreteDebris_arm.png","TPG_CIN3_ConcreteDebris_nor_gl.png",
  "TPG_CIN3_RoughConcrete_diff.png","TPG_CIN3_CMU_diff.png","TPG_CIN3_Brick_diff.png","TPG_CIN3_RustMetal_diff.png"
 )
 foreach($t in $requiredTex){
  if(-not(Test-Path (Join-Path $top "Textures\$t"))){throw "Missing cinematic PBR map: $t"}
 }

 $dbText=Get-Content (Join-Path $top "Database\db_tpg_rubble_pile_cinematic_v3.lua") -Raw
 if($dbText -match 'Name\s*=\s*"TPG_Rubble_Pile_20ft_V1"' -or $dbText -match 'Name\s*=\s*"TPG_Rubble_Pile_20ft_HQ500_V2"'){
  throw "Coexistence collision with V1/V2"
 }
 if($dbText -notmatch [regex]::Escape($asset)){throw "V3 asset ID missing from database"}

 Write-Host "TPG_RUBBLE_CINEMATIC_V3_VALIDATION_SUCCESS"
 Write-Host "Textures: $($textures.Count)"
 Write-Host "ZIP: $ZipPath"
}
finally{
 if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force}
}
