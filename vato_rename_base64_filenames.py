# Tool to rename files from Valkyrie Anatomia: The Origin.
#
# Usage:  Run by itself without commandline arguments and it will rename
# every file it finds via a recursive search.
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

    files = [x for x in glob.glob('**/*.*', recursive = True) if not x[-3:] == '.py']
    for file in files:
        foldername = os.path.dirname(file)
        filename, ext = os.path.splitext(os.path.basename(file))
        #print("filename: {}".format(filename))
        real_filename = base64.b64decode(filename.encode("ascii"))
        if not foldername == '':
            foldername += '/'
        os.rename(foldername + filename+ext, foldername + real_filename.decode()+ext)