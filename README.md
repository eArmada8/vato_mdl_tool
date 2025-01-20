# VATO MDL mesh export and import
A script to get the mesh data out of MDL files from Valkyrie Anatomia: The Origin.  The output is in .glb files, although there is an option for .fmt/.ib/.vb/.vgmap that are compatible with DarkStarSword Blender import plugin for 3DMigoto.  This is theoretically a work in progress, but I wrote this just to get Estelle and Joshua (Trails in the Sky) and so there may never be an update for this.

## Credits:
I am as always very thankful for the dedicated reverse engineers at the Kiseki modding discord, for their brilliant work, and for sharing that work so freely.  Thank you to Kyuuhachi for help with the node skeleton (and reverse engineering in general), to Platinarei for help with textures, and to Badcatalex for sample files.  Thank you to taikotools for the txp decompression algorithm.

## Requirements:
1. Python 3.10 and newer is required for use of these scripts.  It is free from the Microsoft Store, for Windows users.  For Linux users, please consult your distro.
2. The pillow module for python is needed.  Install by typing "python3 -m pip install pillow" in the command line / shell.  (The io, struct, copy, json, glob, os, sys, and argparse modules are also required, but these are all already included in most basic python installations.)
3. The output can be imported into Blender as .glb, or as raw buffers using DarkStarSword's amazing plugin: https://github.com/DarkStarSword/3d-fixes/blob/master/blender_3dmigoto.py (tested on commit [5fd206c](https://raw.githubusercontent.com/DarkStarSword/3d-fixes/5fd206c52fb8c510727d1d3e4caeb95dac807fb2/blender_3dmigoto.py))
4. vato_extract_imdl.py is dependent on lib_fmtibvb.py, which must be in the same folder.  

## Usage:
### vato_extract_imdl.py
Double click the python script and it will search the current folder for all .mdl files and export as .glb.  To obtain textures, use vato_extract_txp.py.

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

### vato_extract_txp.py
Double click the python script and it will search the current folder for all .txp files and export as .png.  Only supports 0x4 format (BRG5551).

**Command line arguments:**
`vato_extract_txp.py [-h] txp_filename`

`-h, --help`
Shows help message.

## Known issues:
- I have not figured out how textures are assigned to materials, so my script makes guesses based on material names.  This does not always work.  Please fix the images by changing them in Blender or equivalent.  *As of v1.0.1*, the script will ask you to make the guess first if the script is unable to automatically guess - this behavior can be reverted by editing the variable `ask_if_texture_does_not_match` at the very top of the script.
- Some textures come out corrupted.  I have not figured out if this is due to a program with my script or the dumped assets.