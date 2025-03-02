# Tool to export files from the pck format used by Valkyrie Anatomia: The Origin.
#
# Usage:  Run by itself without commandline arguments and it will read
# every pck file it finds in the folder and output contained files.
#
# For command line options, run:
# /path/to/python3 vato_unpack_pck.py --help
#
# GitHub eArmada8/vato_mdl_tool

try:
    import io, struct, glob, os, sys
except ModuleNotFoundError as e:
    print("Python module missing! {}".format(e.msg))
    input("Press Enter to abort.")
    raise   

def read_null_terminated_string (f):
    null_term_string = f.read(1)
    while null_term_string[-1] != 0:
        null_term_string += f.read(1)
    return(null_term_string[:-1].decode())

def unpack_pck_block(f, header, pck_filename):
    entries = []
    for i in range(header['num_entries']):
        offset, size = struct.unpack("<2I", f.read(8))
        entries.append({'offset': offset, 'size': size})
    for i in range(len(entries)):
        f.seek(entries[i]['offset'])
        filedata = f.read(entries[i]['size'])
        if filedata[0:4] == b'IANM':
            extension = 'anm'
        elif filedata[0:4] == b'IMDL':
            extension = 'mdl'
        elif filedata[0:4] == b'IMTN':
            extension = 'mtn'
        elif b'GLTP' in filedata[0:0x20]:
            extension = 'txp'
        else:
            extension = 'bin'
        open(pck_filename[:-4]+"_{0}.{1}".format(i, extension), 'wb').write(filedata)
    return

def unpack_pck (f, pck_filename):
    header = {}
    header['num_entries'], header['flags'], header['unk'], header['unk2'] = struct.unpack("<4I", f.read(16))
    if header['flags'] == 0:
        unpack_pck_block(f, header, pck_filename)
    elif header['flags'] == 0x80:
        # Can there be more than one of these pck-embedded pcks?
        offset, size = struct.unpack("<2I", f.read(8))
        internal_pck_filename = read_null_terminated_string(f) + '.pck'
        f.seek(offset)
        internal_pck = f.read(size)
        with io.BytesIO(internal_pck) as internal_f:
            unpack_pck(internal_f, internal_pck_filename)
    else: # I think these are compressed or something
        print("{} is in a .pck format that is not supported yet!".format(pck_filename))
    return

def unpack_pck_file (pck_filename):
    with open(pck_filename, 'rb') as f:
        unpack_pck (f, pck_filename)

if __name__ == "__main__":
    # Set current directory
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.abspath(os.path.dirname(__file__)))

    # If argument given, attempt to export from file in argument
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('pck_filename', help="Name of pck file to unpack (required).")
        args = parser.parse_args()
        if os.path.exists(args.pck_filename) and args.pck_filename[-4:].lower() == '.pck':
            unpack_pck_file(args.pck_filename)
    else:
        pck_files = glob.glob('*.pck')
        for i in range(len(pck_files)):
            unpack_pck_file(pck_files[i])
