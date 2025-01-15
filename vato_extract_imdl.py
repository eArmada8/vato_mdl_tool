# Tool to export model data from the imdl format used by Valkyrie Anatomia: The Origin.
# Dumps meshes for import into Blender.
# Usage:  Run by itself without commandline arguments and it will read only the mesh section of
# every model it finds in the folder and output fmt / ib / vb files.
#
# For command line options, run:
# /path/to/python3 vato_extract_imdl.py --help
#
# Requires lib_fmtibvb.py, put in the same directory
#
# GitHub eArmada8/vato_mdl_tool

try:
    import io, struct, sys, os, glob, json
    from itertools import chain
    from lib_fmtibvb import *
except ModuleNotFoundError as e:
    print("Python module missing! {}".format(e.msg))
    input("Press Enter to abort.")
    raise   

def make_fmt():
    return({'stride': '52', 'topology': 'trianglelist', 'format': 'DXGI_FORMAT_R16_UINT',\
        'elements': [{'id': '0', 'SemanticName': 'POSITION', 'SemanticIndex': '0',\
        'Format': 'R32G32B32_FLOAT', 'InputSlot': '0', 'AlignedByteOffset': '0',\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'}, {'id': '1',\
        'SemanticName': 'TEXCOORD', 'SemanticIndex': '0',\
        'Format': 'R32G32_FLOAT', 'InputSlot': '0', 'AlignedByteOffset': '12',\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'}, {'id': '2',\
        'SemanticName': 'NORMAL', 'SemanticIndex': '0', 'Format': 'R32G32B32_FLOAT',\
        'InputSlot': '0', 'AlignedByteOffset': '20', 'InputSlotClass': 'per-vertex',\
        'InstanceDataStepRate': '0'}, {'id': '3',\
        'SemanticName': 'BLENDINDICES', 'SemanticIndex': '0', 'Format': 'R8G8B8A8_UINT',\
        'InputSlot': '0', 'AlignedByteOffset': '32', 'InputSlotClass': 'per-vertex',\
        'InstanceDataStepRate': '0'}, {'id': '4', 'SemanticName': 'BLENDWEIGHTS', 'SemanticIndex': '0',\
        'Format': 'R32G32B32A32_FLOAT', 'InputSlot': '0', 'AlignedByteOffset': '36',\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'}]})

def read_string_dictionary (f, start_offset, next_section_offset):
    f.seek(start_offset)
    return([x.decode() for x in f.read(next_section_offset - start_offset).split(b'\x00')])
    
def process_imdl (imdl_file, overwrite = False):
    print("Processing {}...".format(imdl_file))
    with open(imdl_file, "rb") as f:
        f.seek(0,2)
        eof = f.tell()
        f.seek(0,0)
        magic = f.read(4)
        if magic == b'IMDL':
            unk0, unk1, unk2, num_sections = struct.unpack("<4H", f.read(8))
            block_offsets = {}
            block_offsets["dictionary"], block_offsets["blend_indices"], block_offsets["triangles"],\
                block_offsets["unknown_blanks"], block_offsets["vertices"] = struct.unpack("<5I", f.read(20))
            while f.tell() < block_offsets["dictionary"]:
                section_magic = f.read(4)
                section_size, = struct.unpack("<I", f.read(4))
                if section_magic == b'mesh':
                    meshes = []
                    num_sections, num_meshes = struct.unpack("<2I", f.read(8))
                    for _ in range(num_meshes):
                        mesh = {}
                        mesh['sub_index'], mesh['unk0'], mesh['unk1'], mesh['index_buffer_len'], mesh['index_buffer_offset']\
                            = struct.unpack("<2H3I", f.read(16))
                        meshes.append(mesh)
                elif section_magic == b'shap':
                    shapes = []
                    num_sections, num_shapes = struct.unpack("<2I", f.read(8))
                    for _ in range(num_shapes):
                        shape = {}
                        shape['unk0'], shape['unk1'], shape['num_vertices'], shape['pos_offset'],\
                        shape['uv_offset'], shape['abs_vert_start'], shape['norm_offset'],\
                        shape['blend_indices_offset'], shape['blendweight_offset'] = struct.unpack("<9I", f.read(36))
                        shapes.append(shape)
                else:
                    #print("Skipping section {}...".format(section_magic.decode()))
                    f.seek(section_size - 8, 1)
            text_dict = read_string_dictionary (f, block_offsets["dictionary"], block_offsets["blend_indices"])
            if os.path.exists(imdl_file[:-4]) and (os.path.isdir(imdl_file[:-4])) and (overwrite == False):
                if str(input(imdl_file[:-4] + " folder exists! Overwrite? (y/N) ")).lower()[0:1] == 'y':
                    overwrite = True
            if (overwrite == True) or not os.path.exists(imdl_file[:-4]):
                if not os.path.exists(imdl_file[:-4]):
                    os.mkdir(imdl_file[:-4])
                fmt = make_fmt()
                submesh_num = 0
                submeshes = [i for i in range(len(meshes)) if meshes[i]['sub_index'] == 0]
                for i in range(len(meshes)):
                    vb = []
                    f.seek(block_offsets["vertices"] + (shapes[submesh_num]['pos_offset'] * 4))
                    pos_buffer = list(struct.unpack("<{}f".format(shapes[submesh_num]['num_vertices']*3),
                        f.read(shapes[submesh_num]['num_vertices'] * 4 * 3)))
                    vb.append({'Buffer': [pos_buffer[j*3:j*3+3] for j in range(len(pos_buffer)//3)]})
                    uv_buffer = list(struct.unpack("<{}f".format(shapes[submesh_num]['num_vertices']*2),
                        f.read(shapes[submesh_num]['num_vertices'] * 4 * 2)))
                    vb.append({'Buffer': [uv_buffer[j*2:j*2+2] for j in range(len(uv_buffer)//2)]})
                    norm_buffer = list(struct.unpack("<{}f".format(shapes[submesh_num]['num_vertices']*3),
                        f.read(shapes[submesh_num]['num_vertices'] * 4 * 3)))
                    vb.append({'Buffer': [norm_buffer[j*3:j*3+3] for j in range(len(norm_buffer)//3)]})
                    wt_buffer = list(struct.unpack("<{}f".format(shapes[submesh_num]['num_vertices']*4),
                        f.read(shapes[submesh_num]['num_vertices'] * 4 * 4)))
                    matrix_buffer = [] # Dunno what these are for currently, maybe bind matrices?
                    if submesh_num + 1 < len(shapes):
                        while f.tell() < (block_offsets["vertices"] + (shapes[submesh_num+1]['pos_offset'] * 4)):
                            matrix_buffer.append(list(struct.unpack("<16f", f.read(64))))
                    else:
                        while f.tell() < eof:
                            matrix_buffer.append(list(struct.unpack("<16f", f.read(64))))
                    f.seek(block_offsets["blend_indices"] + (shapes[submesh_num]['blend_indices_offset'] * 1))
                    wt_index_buffer = list(struct.unpack("<{}B".format(shapes[submesh_num]['num_vertices']*4),
                        f.read(shapes[submesh_num]['num_vertices'] * 4)))
                    vb.append({'Buffer': [wt_index_buffer[j*4:j*4+4] for j in range(len(wt_index_buffer)//4)]})
                    vb.append({'Buffer': [wt_buffer[j*4:j*4+4] for j in range(len(wt_buffer)//4)]})
                    if i in submeshes: # New mesh
                        ib = []
                    f.seek(block_offsets["triangles"] + (meshes[i]['index_buffer_offset'] * 2))
                    ib.extend(list(struct.unpack("<{}H".format(meshes[i]['index_buffer_len']),
                        f.read(meshes[i]['index_buffer_len'] * 2))))
                    # This is a little inefficient since the entire buffer is written more than once but I'll figure it out later
                    write_fmt(fmt, "{0}/{1:02d}.fmt".format(imdl_file[:-4], submesh_num))
                    write_vb(vb, "{0}/{1:02d}.vb".format(imdl_file[:-4], submesh_num), fmt)
                    write_ib(ib, "{0}/{1:02d}.ib".format(imdl_file[:-4], submesh_num), fmt)
                    if i in submeshes: # New mesh
                        submesh_num = submesh_num + 1
    return

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
        parser.add_argument('-o', '--overwrite', help="Overwrite existing files", action="store_true")
        parser.add_argument('imdl_filename', help="Name of imdl file to export from (required).")
        args = parser.parse_args()
        if os.path.exists(args.imdl_filename) and args.imdl_filename[-4:].lower() == '.mdl':
            process_imdl(args.imdl_filename, overwrite = args.overwrite)
    else:
        imdl_files = glob.glob('*.mdl')
        for i in range(len(imdl_files)):
            process_imdl(imdl_files[i])
