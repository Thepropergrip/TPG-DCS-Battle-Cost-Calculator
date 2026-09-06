param()
$ErrorActionPreference='Stop'
$root=Join-Path $env:GITHUB_WORKSPACE 'edm-artifacts'
$asset='TPG_Rubble_Attachment_Shape_Pack'
$pkg=Join-Path $root $asset
$shapes=Join-Path $pkg 'Shapes'
$textures=Join-Path $pkg 'Textures'
$db=Join-Path $pkg 'Database'
if(Test-Path $pkg){Remove-Item $pkg -Recurse -Force}
New-Item -ItemType Directory -Force -Path $shapes,$textures,$db | Out-Null
$defs=@(
 @{Name='TPG_Rubble_Attachment_Small_Low';Display='TPG Rubble Small Low Attachment';Life=850},
 @{Name='TPG_Rubble_Attachment_Tractor_Pushed';Display='TPG Rubble Tractor Pushed Attachment';Life=1200},
 @{Name='TPG_Rubble_Attachment_Long_Rectangular';Display='TPG Rubble Long Rectangular Attachment';Life=1350},
 @{Name='TPG_Rubble_Attachment_Wall_Lean';Display='TPG Rubble Wall Lean Attachment';Life=1400},
 @{Name='TPG_Rubble_Attachment_Long_Ridge';Display='TPG Rubble Long Ridge Attachment';Life=1450},
 @{Name='TPG_Rubble_Attachment_Multi_Hump';Display='TPG Rubble Multi Hump Attachment';Life=1750}
)
foreach($d in $defs){
 $a=$d.Name
 foreach($s in @('', '_Destroyed','_LOD1','_LOD2','_Collision')){
  $src=Join-Path $root ($a+$s+'.edm'); if(-not(Test-Path $src)){throw "Missing $src"}; Copy-Item $src $shapes -Force
 }
 @"
model={
 lods={
  {\"$a.edm\",350.0};
  {\"${a}_LOD1.edm\",1200.0};
  {\"${a}_LOD2.edm\",7000.0};
 };
 collision_shell=\"${a}_Collision.edm\";
}
"@.Replace('\"','"') | Set-Content (Join-Path $shapes "$a.lods") -Encoding ASCII
}
$srcTex=Join-Path $root 'Textures'
$dds=@(Get-ChildItem $srcTex -Filter *.dds -File)
if($dds.Count -lt 54){throw "Expected V5 + attachment DDS textures; found $($dds.Count)"}
Copy-Item (Join-Path $srcTex '*.dds') $textures -Force
$entry=@'
declare_plugin("TPG Rubble Attachment Shape Pack",
{
 installed=true,
 dirName=current_mod_path,
 displayName=_("TPG Rubble Attachment Shape Pack"),
 version="1.0.0",
 state="installed",
 info=_("Six upgraded rubble shapes using supplied source rubble mesh/PBR maps, shape-matched footprints, terrain locking and dedicated collision shells")
})
mount_vfs_model_path(current_mod_path.."/Shapes")
mount_vfs_texture_path(current_mod_path.."/Textures")
dofile(current_mod_path.."/Database/db_tpg_rubble_attachment_shape_pack.lua")
plugin_done()
'@
Set-Content (Join-Path $pkg 'entry.lua') $entry -Encoding UTF8
$dbText=@'
local function add_structure(f)
 f.shape_table_data={{file=f.ShapeName,life=f.Life,username=f.Name,desrt=f.ShapeNameDestr or "self",classname="lLandVehicle",positioning="ONLYHEIGTH"}}
 if f.ShapeNameDestr then f.shape_table_data[#f.shape_table_data+1]={name=f.ShapeNameDestr,file=f.ShapeNameDestr} end
 f.mapclasskey="P0091000076"
 f.attribute={wsType_Static,wsType_Standing,"Structures"}
 add_surface_unit(f)
end

'@
foreach($d in $defs){
 $dbText += "add_structure({Name=\"$($d.Name)\",DisplayName=_(\"$($d.Display)\"),ShapeName=\"$($d.Name)\",ShapeNameDestr=\"$($d.Name)_Destroyed\",Life=$($d.Life),Rate=100,category=\"Structures\",SeaObject=false,isPutToWater=false,numParking=0})`n"
}
Set-Content (Join-Path $db 'db_tpg_rubble_attachment_shape_pack.lua') $dbText -Encoding UTF8
@'
TPG Rubble Attachment Shape Pack
================================
INSTALL: copy TPG_Rubble_Attachment_Shape_Pack into Saved Games\DCS\Mods\tech\
MISSION EDITOR: Static Objects -> Structures
This is a coexisting pack with unique DCS-facing identities. It does not replace TPG_Rubble_Shape_Pack or Cinematic V5.
Uses the user-supplied rubble OBJ as actual rigid mesh geometry with the supplied PBR maps. Recognizable debris is not non-uniformly stretched.
Wall Lean uses a dense Cartesian quad wedge with a straight wall-contact edge and no center/radial fan topology.
Placement remains terrain-locked with positioning="ONLYHEIGTH" and dedicated simplified collision shells.
Built with Blender 4.1.1 and the official Eagle Dynamics Blender EDM exporter.
'@ | Set-Content (Join-Path $pkg 'README.txt') -Encoding UTF8
$zip=Join-Path $root 'TPG_Rubble_Attachment_Shape_Pack_DCS_DropIn.zip'
if(Test-Path $zip){Remove-Item $zip -Force}
Compress-Archive -Path $pkg -DestinationPath $zip -CompressionLevel Optimal
if(-not(Test-Path $zip)){throw 'ZIP not created'}
# hard validation
$tmp=Join-Path $env:RUNNER_TEMP ('tpg_attach_validate_'+[guid]::NewGuid().ToString('N'))
Expand-Archive $zip $tmp -Force
$r=Join-Path $tmp $asset
if(-not(Test-Path $r)){throw 'Wrong ZIP root'}
if(@(Get-ChildItem (Join-Path $r 'Shapes') -Filter *.edm -File).Count -ne 30){throw 'Expected 30 EDMs'}
if(@(Get-ChildItem (Join-Path $r 'Textures') -Filter *.dds -File).Count -lt 54){throw 'Missing attachment/V5 DDS set'}
$dbRaw=Get-Content (Join-Path $r 'Database\db_tpg_rubble_attachment_shape_pack.lua') -Raw
if(-not $dbRaw.Contains('positioning="ONLYHEIGTH"')){throw 'Missing ONLYHEIGTH'}
if($dbRaw.Contains('TPG_Rubble_Small_Low"')){throw 'Identity collision with old pack'}
Remove-Item $tmp -Recurse -Force
Write-Host 'TPG_RUBBLE_ATTACHMENT_PACK_VALIDATION_SUCCESS'
