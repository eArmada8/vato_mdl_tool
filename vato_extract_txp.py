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
    unc_size_w_flags, = struct.unpack("<I", f.read(4))
    unc_size = (unc_size_w_flags & 0xFFFFFF00) >> 8
    output = bytearray([0]*unc_size)
    out_loc = 0
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
                end = out_loc
                for i in range(len_):
                    output[out_loc] = output[end-back+i]
                    out_loc += 1
            elif (c > 0x7F):
                len_ = ((c >> 2) & 0x1F)
                back = ((c & 0x3) << 8) + int.from_bytes(f.read(1)) + 1
                if ((c & 0x80) != 0):
                    len_ += 3
                end = out_loc
                for i in range(len_):
                    if i > end:
                        output[out_loc] = output[end-1]
                    else:
                        output[out_loc] = output[end-back+i]
                    out_loc += 1
            elif (c > 0x3F):
                len_ = (c >> 4) - 2
                back = (c & 0x0F) + 1
                end = out_loc
                for i in range(len_):
                    if i > end:
                        output[out_loc] = output[end-1]
                    else:
                        output[out_loc] = output[end-back+i]
                    out_loc += 1
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
                    len_ += flag & 0x7F
                output[out_loc:out_loc+len_] = f.read(len_)
                out_loc += len_
            else:
                output[out_loc:out_loc+c] = f.read(c)
                out_loc += c
    return(output)

def convert_vato_tga (f):
     # Thank you to Platinarei for the RBGA code
    def decode_vato_5551 (raw_color):
        return(tuple([x << 3 | x >> 2 for x in
            [(raw_color & 0xF800) >> 11, (raw_color & 0x7C0) >> 6, (raw_color & 0x3E) >> 1]]\
            + [(raw_color & 0x1) * 255]))
    def decode_vato_4444 (raw_color):
        return(tuple([x * 17 for x in
            [(raw_color & 0xF000) >> 12, (raw_color & 0x0F00) >> 8, (raw_color & 0x00F0) >> 4, (raw_color & 0x000F)]]))
    desc_offset, tex_size, tex_offset, tex_format, width, height, maybe_mips, unk1, unk2 = struct.unpack("<4I2H3I", f.read(32))
    f.seek(desc_offset, 0)
    file_desc = read_null_terminated_string (f)
    print("Processing {}...".format(file_desc))
    if not tex_format in [4, 5, 6]:
        input("{} is not format type 4 or 5, skipping!  Press Enter to continue.".format(file_desc))
        return
    f.seek(tex_offset, 0)
    if tex_format in [4,5]:
        raw_bitmap = struct.unpack("<{}H".format(tex_size//2), f.read(tex_size))
        if tex_format == 4:
            bitmap = [decode_vato_5551(x) for x in raw_bitmap]
        elif tex_format == 5:
            bitmap = [decode_vato_4444(x) for x in raw_bitmap]
    else: # Format 6, R8G8B8_UINT
        raw_bitmap = struct.unpack("<{}B".format(tex_size), f.read(tex_size))
        bitmap = [(raw_bitmap[i*3], raw_bitmap[i*3+1], raw_bitmap[i*3+2]) for i in range(len(raw_bitmap)//3)]
    im = Image.new('RGBA', (width, height))
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
