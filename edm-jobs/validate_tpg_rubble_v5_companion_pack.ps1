param([Parameter(Mandatory=$true)][string]$ZipPath)
$ErrorActionPreference='Stop'
if(-not(Test-Path $ZipPath)){throw "ZIP missing: $ZipPath"}

$expectedRoot='TPG_Rubble_Companion_Pack_Cinematic_V5'
$assets=@(
 'TPG_Rubble_SmallLow_Cinematic_V5A',
 'TPG_Rubble_Pushed_Cinematic_V5B',
 'TPG_Rubble_Rectangular_Cinematic_V5C',
 'TPG_Rubble_BuildingFace_Cinematic_V5D',
 'TPG_Rubble_Ridge_Cinematic_V5E',
 'TPG_Rubble_MultiHump_Cinematic_V5F'
)

$tmp=Join-Path $env:RUNNER_TEMP ('tpg_rubble_pack_validate_'+[guid]::NewGuid().ToString('N'))
New-Item -ItemType Directory -Force -Path $tmp | Out-Null
try {
  Expand-Archive -Path $ZipPath -DestinationPath $tmp -Force
  $tops=@(Get-ChildItem $tmp)
  if($tops.Count -ne 1 -or -not $tops[0].PSIsContainer -or $tops[0].Name -ne $expectedRoot){
    throw "ZIP must contain exactly one top-level folder named $expectedRoot"
  }
  $root=$tops[0].FullName
  foreach($p in @('entry.lua','README.txt','Database','Shapes','Textures')){
    if(-not(Test-Path (Join-Path $root $p))){throw "Missing package path: $p"}
  }

  $edm=@(Get-ChildItem (Join-Path $root 'Shapes') -Filter *.edm -File)
  if($edm.Count -ne 24){throw "Expected exactly 24 EDM files (6 assets x 4 states/LODs); found $($edm.Count)"}

  foreach($a in $assets){
    foreach($s in @('', '_Destroyed', '_LOD1', '_LOD2')){
      $f=Join-Path $root ("Shapes\$a$s.edm")
      if(-not(Test-Path $f)){throw "Missing required EDM: $a$s.edm"}
      if((Get-Item $f).Length -lt 16384){throw "Suspiciously small EDM: $a$s.edm"}
    }
    $lod=Join-Path $root ("Shapes\$a.lods")
    if(-not(Test-Path $lod)){throw "Missing LODS file: $a.lods"}
    $lt=Get-Content $lod -Raw
    foreach($s in @("$a.edm","${a}_LOD1.edm","${a}_LOD2.edm")){
      if($lt -notmatch [regex]::Escape($s)){throw "LODS $a.lods does not reference $s"}
    }
  }

  $dds=@(Get-ChildItem (Join-Path $root 'Textures') -Filter *.dds -File)
  if($dds.Count -lt 45){throw "Expected shared Cinematic V5 DDS texture set; found only $($dds.Count)"}
  $png=@(Get-ChildItem (Join-Path $root 'Textures') -Filter *.png -File)
  if($png.Count -ne 0){throw "Shipping Textures contains PNG files; expected DDS-only package"}
  foreach($hero in @(
    'TPG_CIN5_RubbleBase_diff.dds','TPG_CIN5_RubbleBase_nor_gl.dds','TPG_CIN5_RubbleBase_arm.dds',
    'TPG_CIN5_ConcreteDebris_diff.dds','TPG_CIN5_CMU_diff.dds','TPG_CIN5_Brick_diff.dds',
    'TPG_CIN5_RebarOxidized.dds','TPG_CIN5_DirtyPipe.dds')){
    if(-not(Test-Path (Join-Path $root "Textures\$hero"))){throw "Missing required V5 shared texture: $hero"}
  }

  $entry=Get-Content (Join-Path $root 'entry.lua') -Raw
  if($entry -notmatch 'TPG Rubble Companion Pack Cinematic V5'){throw 'Wrong/missing plugin identity'}
  if($entry -match 'declare_plugin\("TPG Rubble Pile 20ft Cinematic V5"'){throw 'Plugin identity collides with original V5'}

  $dbPath=Join-Path $root 'Database\db_tpg_rubble_companion_pack_cinematic_v5.lua'
  if(-not(Test-Path $dbPath)){throw 'Companion pack database file missing'}
  $db=Get-Content $dbPath -Raw
  foreach($a in $assets){
    $nameNeedle='Name="' + $a + '"'
    $shapeNeedle='ShapeName="' + $a + '"'
    $destrNeedle='ShapeNameDestr="' + $a + '_Destroyed"'
    # remove literal backslash characters from the PowerShell string construction above
    $nameNeedle=$nameNeedle.Replace('\','')
    $shapeNeedle=$shapeNeedle.Replace('\','')
    $destrNeedle=$destrNeedle.Replace('\','')
    if(-not $db.Contains($nameNeedle)){throw "Database missing unique Name for $a"}
    if(-not $db.Contains($shapeNeedle)){throw "Database missing ShapeName for $a"}
    if(-not $db.Contains($destrNeedle)){throw "Database missing destroyed ShapeName for $a"}
  }
  if($db.Contains('Name="TPG_Rubble_Pile_20ft_Cinematic_V5"'.Replace('\',''))){throw 'Database collides with original Cinematic V5 Name'}

  Write-Host 'TPG_RUBBLE_V5_COMPANION_PACK_VALIDATION_SUCCESS'
}
finally {
  if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue}
}
