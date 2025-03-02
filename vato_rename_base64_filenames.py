# Tool to rename files from Valkyrie Anatomia: The Origin.
#
# Usage:  Run by itself without commandline arguments and it will rename
# every file it finds in the folder.
#
# For command line options, run:
# /path/to/python3 vato_rename_base64_filenames.py --help
#
# GitHub eArmada8/vato_mdl_tool

import base64, glob, os, sys

if __name__ == "__main__":
    # Set current directory
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.abspath(os.path.dirname(__file__)))

    files = [x for x in glob.glob('*.*') if not x in glob.glob('*.py')]
    for file in files:
        filename, ext = os.path.splitext(os.path.basename(file))
        real_filename = base64.b64decode(filename.encode("ascii"))
        os.rename(filename+ext, real_filename.decode()+ext)