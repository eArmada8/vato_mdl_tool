# Tool to export texture data from the txp format used by Valkyrie Anatomia: The Origin.
#
# Usage:  Run by itself without commandline arguments and it will read
# every txp file it finds in the folder and output png files.
#
# For command line options, run:
# /path/to/python3 vato_extract_txp.py --help
#
# Requires the pillow module, which can be installed by:
# /path/to/python3 -m pip install pillow
#
# Requires lib_fmtibvb.py, put in the same directory
#
# GitHub eArmada8/vato_mdl_tool

try:
    import struct, io, os, sys, glob
    from PIL import Image
except ModuleNotFoundError as e:
    print("Python module missing! {}".format(e.msg))
    input("Press Enter to abort.")
    raise   

def read_null_terminated_string (f):
    null_term_string = f.read(1)
    while null_term_string[-1] != 0:
        null_term_string += f.read(1)
    return(null_term_string[:-1].decode())

# Thank you to https://github.com/mariodon/taikotools/ for the decompression algorithm
def decompress_taiko_v (f):
    output = bytes()
    unc_size_w_flags, = struct.unpack("<I", f.read(4))
    unc_size = (unc_size_w_flags & 0xFFFFFF00) >> 8
    cmp_data = f.read()
    cmp_data_len = len(cmp_data)
    with io.BytesIO(cmp_data) as f:
        while f.tell() < cmp_data_len:
            c = int.from_bytes(f.read(1))
            if (c > 0xBF):
                len_ = (c - 0xBE) * 2
                flag = int.from_bytes(f.read(1))
                back = ((flag & 0x7f) << 8) + int.from_bytes(f.read(1)) + 1
                if ((flag & 0x80) != 0):
                    len_ += 1
                end = len(output)
                for i in range(len_):
                    output += output[end-back+i:end-back+i+1]
            elif (c > 0x7F):
                len_ = ((c >> 2) & 0x1F)
                back = ((c & 0x3) << 8) + int.from_bytes(f.read(1)) + 1
                if ((c & 0x80) != 0):
                    len_ += 3
                end = len(output)
                for i in range(len_):
                    if i > end:
                        output += output[end-1:end]
                    else:
                        output += output[end-back+i:end-back+i+1]
            elif (c > 0x3F):
                len_ = (c >> 4) - 2
                back = (c & 0x0F) + 1
                end = len(output)
                for i in range(len_):
                    if i > end:
                        output += output[end-1:end]
                    else:
                        output += output[end-back+i:end-back+i+1]
            elif (c == 0x00):
                offset = f.tell() - 1
                flag = int.from_bytes(f.read(1))
                flag2 = 0
                len_ = 0x40
                if ((flag & 0x80) == 0):
                    flag2 = int.from_bytes(f.read(1))
                    len_ = 0xBF + flag2 + (flag << 8)
                    peek = int.from_bytes(f.read(1))
                    f.seek(-1,1)
                    if flag == 0 and flag2 == 0 and peek == 0:
                        break
                else:
                    len_ = flag & 0x7F
                output += f.read(len_)
            else:
                output += f.read(c)
    return(output)

def convert_vato_tga (f):
    def decode_vato_5551 (raw_color): # Thank you to Platinarei for this code
        return(tuple([x << 3 | x >> 2 for x in
            [(raw_color & 0xF800) >> 11, (raw_color & 0x7C0) >> 6, (raw_color & 0x3E) >> 1]]))
    desc_offset, tex_size, tex_offset, tex_format, width, height, maybe_mips, unk1, unk2 = struct.unpack("<4I2H3I", f.read(32))
    f.seek(desc_offset, 0)
    file_desc = read_null_terminated_string (f)
    print("Processing {}...".format(file_desc))
    if tex_format != 4:
        input("{} is not format type 4, skipping!  Press Enter to continue.".format(file_desc))
        return
    f.seek(tex_offset, 0)
    raw_bitmap = struct.unpack("<{}H".format(tex_size//2), f.read(tex_size))
    bitmap = [decode_vato_5551(x) for x in raw_bitmap]
    im = Image.new('RGB', (width, height))
    im.putdata(bitmap)
    im.save('{}.png'.format(file_desc))
    return

def process_txp_file (txp_file):
    with open(txp_file, 'rb') as f:
        magic = f.read(4)
        f.seek(0)
        if magic == b'GLTP':
            unc_data = f.read()
        else: # Assume compressed
            print("File magic is not GLTP, attempting decompression...")
            unc_data = decompress_taiko_v(f)
    with io.BytesIO(unc_data) as f:
        magic = f.read(4)
        if magic == b'GLTP':
            version, num_files, hash_offset = struct.unpack("<3I", f.read(12))
            for i in range(num_files):
                f.seek(0x20 * (i+1), 0)
                convert_vato_tga(f)

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
        parser.add_argument('txp_filename', help="Name of txp file to export from (required).")
        args = parser.parse_args()
        if os.path.exists(args.txp_filename) and args.txp_filename[-4:].lower() == '.txp':
            process_txp_file(args.txp_filename)
    else:
        txp_files = glob.glob('*.txp')
        for i in range(len(txp_files)):
            process_txp_file(txp_files[i])
