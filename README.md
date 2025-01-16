# VATO MDL mesh export and import
A script to get the mesh data out of MDL files from Valkyrie Anatomia: The Origin.  The output is in .glb files, although there is an option for .fmt/.ib/.vb/.vgmap that are compatible with DarkStarSword Blender import plugin for 3DMigoto.  This is theoretically a work in progress, but I wrote this just to get Estelle and Joshua (Trails in the Sky) and so there may never be an update for this.

## Credits:
I am as always very thankful for the dedicated reverse engineers at the Kiseki modding discord, for their brilliant work, and for sharing that work so freely.

## Requirements:
1. Python 3.10 and newer is required for use of these scripts.  It is free from the Microsoft Store, for Windows users.  For Linux users, please consult your distro.
2. The output can be imported into Blender as .glb, or as raw buffers using DarkStarSword's amazing plugin: https://github.com/DarkStarSword/3d-fixes/blob/master/blender_3dmigoto.py (tested on commit [5fd206c](https://raw.githubusercontent.com/DarkStarSword/3d-fixes/5fd206c52fb8c510727d1d3e4caeb95dac807fb2/blender_3dmigoto.py))
4. vato_extract_imdl.py is dependent on lib_fmtibvb.py, which must be in the same folder.  

## Usage:
### vato_extract_imdl.py
Double click the python script and it will search the current folder for all .mdl files and export as .glb.

**Command line arguments:**
`vato_extract_imdl.py [-h] [-t] [-d] [-o] mdl_filename`

`-t, --textformat`
Output .gltf/.bin format instead of .glb format.

`-d, --dumprawbuffers`
Dump .fmt/.ib/.vb/.vgmap files in a folder with the same name as the .mdl file.  Use DarkStarSword's plugin to view.  Separate materials will be combined into a single mesh with this option.

`-h, --help`
Shows help message.

`-o, --overwrite`
Overwrite existing files without prompting.