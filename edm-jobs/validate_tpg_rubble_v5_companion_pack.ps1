param([Parameter(Mandatory=$true)][string]$ZipPath)
$ErrorActionPreference='Stop'
if(-not(Test-Path $ZipPath)){throw "ZIP missing: $ZipPath"}

$expectedRoot='TPG_Rubble_Shape_Pack'
$assets=@(
 'TPG_Rubble_Small_Low',
 'TPG_Rubble_Tractor_Pushed',
 'TPG_Rubble_Long_Rectangular',
 'TPG_Rubble_Wall_Lean',
 'TPG_Rubble_Long_Ridge',
 'TPG_Rubble_Multi_Hump'
)
$life=@{
 'TPG_Rubble_Small_Low'=850
 'TPG_Rubble_Tractor_Pushed'=1200
 'TPG_Rubble_Long_Rectangular'=1350
 'TPG_Rubble_Wall_Lean'=1400
 'TPG_Rubble_Long_Ridge'=1450
 'TPG_Rubble_Multi_Hump'=1750
}

$tmp=Join-Path $env:RUNNER_TEMP ('tpg_rubble_shape_validate_'+[guid]::NewGuid().ToString('N'))
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
  if($edm.Count -ne 30){throw "Expected exactly 30 EDM files (6 assets x intact/destroyed/LOD1/LOD2/collision); found $($edm.Count)"}

  foreach($a in $assets){
    foreach($s in @('', '_Destroyed', '_LOD1', '_LOD2')){
      $f=Join-Path $root ("Shapes\$a$s.edm")
      if(-not(Test-Path $f)){throw "Missing required EDM: $a$s.edm"}
      if((Get-Item $f).Length -lt 16384){throw "Suspiciously small visual EDM: $a$s.edm"}
    }
    $cf=Join-Path $root ("Shapes\${a}_Collision.edm")
    if(-not(Test-Path $cf)){throw "Missing dedicated collision EDM: ${a}_Collision.edm"}
    # Dedicated collision-only EDMs are intentionally tiny: a valid simple shell can be
    # only a few hundred bytes. Keep a low corruption guard while allowing lean convex shells.
    if((Get-Item $cf).Length -lt 256){throw "Suspiciously small collision EDM: ${a}_Collision.edm"}

    $lod=Join-Path $root ("Shapes\$a.lods")
    if(-not(Test-Path $lod)){throw "Missing LODS file: $a.lods"}
    $lt=Get-Content $lod -Raw
    foreach($s in @("$a.edm","${a}_LOD1.edm","${a}_LOD2.edm")){
      if($lt -notmatch [regex]::Escape($s)){throw "LODS $a.lods does not reference $s"}
    }
    if($lt -notmatch [regex]::Escape("collision_shell=`"${a}_Collision.edm`"")){
      throw "LODS $a.lods does not reference dedicated collision shell"
    }
    if($lt -match [regex]::Escape("collision_shell=`"$a.edm`"")){
      throw "LODS $a.lods still uses visible intact EDM as collision shell"
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
  if($entry -notmatch 'TPG Rubble Shape Pack'){throw 'Wrong/missing clean plugin identity'}
  if($entry -notmatch 'version="1.1.0"'){throw 'Expected v1.1.0 plugin version'}

  $dbPath=Join-Path $root 'Database\db_tpg_rubble_shape_pack.lua'
  if(-not(Test-Path $dbPath)){throw 'Shape pack database file missing'}
  $db=Get-Content $dbPath -Raw
  if(-not $db.Contains('positioning="ONLYHEIGTH"')){throw 'Database missing terrain-locked ONLYHEIGTH positioning'}
  if($db.Contains('positioning="BYNORMAL"')){throw 'Database still contains BYNORMAL positioning'}

  foreach($a in $assets){
    foreach($needle in @(
      ('Name="' + $a + '"'),
      ('ShapeName="' + $a + '"'),
      ('ShapeNameDestr="' + $a + '_Destroyed"'),
      ('Life=' + [string]$life[$a])
    )){
      if(-not $db.Contains($needle)){throw "Database missing expected definition '$needle' for $a"}
    }
  }

  foreach($clean in @(
    'TPG Rubble Small Low',
    'TPG Rubble Tractor Pushed',
    'TPG Rubble Long Rectangular',
    'TPG Rubble Wall Lean',
    'TPG Rubble Long Ridge',
    'TPG Rubble Multi Hump'
  )){
    if(-not $db.Contains('DisplayName=_("' + $clean + '")')){
      throw "Missing clean Mission Editor display name: $clean"
    }
  }

  foreach($old in @(
    'TPG_Rubble_Pile_20ft_Cinematic_V5',
    'TPG_Rubble_SmallLow_Cinematic_V5A',
    'TPG_Rubble_Pushed_Cinematic_V5B',
    'TPG_Rubble_Rectangular_Cinematic_V5C',
    'TPG_Rubble_BuildingFace_Cinematic_V5D',
    'TPG_Rubble_Ridge_Cinematic_V5E',
    'TPG_Rubble_MultiHump_Cinematic_V5F'
  )){
    if($db.Contains('Name="' + $old + '"')){throw "Database identity collision with older asset: $old"}
  }

  Write-Host 'TPG_RUBBLE_SHAPE_PACK_V11_VALIDATION_SUCCESS'
}
finally {
  if(Test-Path $tmp){Remove-Item $tmp -Recurse -Force -ErrorAction SilentlyContinue}
}
