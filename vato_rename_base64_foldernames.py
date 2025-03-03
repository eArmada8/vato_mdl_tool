# Tool to rename folders from Valkyrie Anatomia: The Origin.
#
# Usage:  Run by itself without commandline arguments and it will rename
# every folder it finds in the folder.
#
# For command line options, run:
# /path/to/python3 vato_rename_base64_foldernames.py --help
#
# GitHub eArmada8/vato_mdl_tool

import base64, glob, os, sys

if __name__ == "__main__":
    # Set current directory
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.abspath(os.path.dirname(__file__)))

    folders = [x for x in glob.glob('*') if os.path.isdir(x)]
    for folder in folders:
        real_foldername = base64.b64decode(folder.encode("ascii"))
        os.rename(folder, real_foldername.decode())