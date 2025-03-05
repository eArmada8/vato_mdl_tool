# Tool to export animation data from the imtn format used by Valkyrie Anatomia: The Origin.
#
# Usage:  Run by itself without commandline arguments and it will read the nodK section of
# every animation it finds in the folder and output glb files.  Requires a model file
# in order to obtain a skeleton (by default it will pick 00_base.mdl).
#
# For command line options, run:
# /path/to/python3 vato_extract_imtn.py --help
#
# GitHub eArmada8/vato_mdl_tool

try:
    import struct, json, glob, numpy, os, sys
except ModuleNotFoundError as e:
    print("Python module missing! {}".format(e.msg))
    input("Press Enter to abort.")
    raise

ani_fps = 24

def read_from_string_dictionary (f, start_offset):
    current_loc = f.tell()
    f.seek(start_offset)
    null_term_string = f.read(1)
    while null_term_string[-1] != 0:
        null_term_string += f.read(1)
    f.seek(current_loc)
    return(null_term_string[:-1].decode())

def obtain_skeleton_from_imdl (imdl_file):
    def add_child_to_node (nodes, i):
        current_node = i
        nodes[i]['children'] = []
        for j in range(nodes[i]['num_children']):
            i += 1
            nodes[current_node]['children'].append(i)
            nodes, i = add_child_to_node(nodes, i)
        return (nodes, i)
    nodes = []
    with open(imdl_file, "rb") as f:
        magic = f.read(4)
        if magic == b'IMDL':
            unk0, unk1, unk2, num_sections = struct.unpack("<4H", f.read(8))
            block_offsets = {}
            block_offsets["dictionary"], block_offsets["blend_indices"], block_offsets["triangles"],\
                block_offsets["unknown_blanks"], block_offsets["vertices"] = struct.unpack("<5I", f.read(20))
            while f.tell() < block_offsets["dictionary"]:
                section_magic = f.read(4)
                section_size, = struct.unpack("<I", f.read(4))
                if section_magic == b'node':
                    num_sections, num_nodes = struct.unpack("<2I", f.read(8))
                    for _ in range(num_nodes):
                        node = {}
                        string_offset, = struct.unpack("<I", f.read(4))
                        node['name'] = read_from_string_dictionary (f, block_offsets["dictionary"] + string_offset)
                        node['unk1'], = struct.unpack("<f", f.read(4))
                        node['matrix'] = list(struct.unpack("<16f", f.read(64)))
                        node['num_children'], node['postorder_traversal'] = struct.unpack("<2I", f.read(8))
                        nodes.append(node)
                    nodes, _ = add_child_to_node(nodes, 0)
                else:
                    f.seek(section_size - 8, 1)
    skel_struct = []
    for i in range(len(nodes)):
        g_node = {'name': nodes[i]['name']}
        if not (nodes[i]['matrix'] == [1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0,0.0,0.0,0.0,0.0,1.0]):
            g_node['matrix'] = nodes[i]['matrix']
        if len(nodes[i]['children']) > 0:
            g_node['children'] = nodes[i]['children']
        skel_struct.append(g_node)
    return(skel_struct)

def process_imtn (imtn_file, skel_struct, write_binary_gltf = True, overwrite = False):
    global ani_fps
    print("Processing {}...".format(imtn_file))
    gltf_data = {}
    gltf_data['asset'] = { 'version': '2.0' }
    gltf_data['accessors'] = []
    gltf_data['animations'] = [{ 'channels': [], 'samplers': [] }]
    gltf_data['bufferViews'] = []
    gltf_data['buffers'] = []
    gltf_data['nodes'] = skel_struct
    gltf_data['scenes'] = [{}]
    gltf_data['scenes'][0]['nodes'] = [0]
    gltf_data['scene'] = 0
    gltf_data['skins'] = []
    giant_buffer = bytes()
    buffer_view = 0
    with open(imtn_file, "rb") as f:
        magic = f.read(4)
        if magic == b'IMTN':
            unk0, unk1, unk2, num_sections = struct.unpack("<4H", f.read(8))
            block_offsets = {}
            #block 1 is unknown - may visK data
            #block 2 is keyframes
            #block 3 is actually empty in my sample file (same offset as block 4)
            #block 4 is animation data (TRS)
            block_offsets["dictionary"], block_offsets["block1"], block_offsets["times"],\
                block_offsets["block3"], block_offsets["trs_vals"] = struct.unpack("<5I", f.read(20))
            while f.tell() < block_offsets["dictionary"]:
                section_magic = f.read(4)
                section_size, = struct.unpack("<I", f.read(4))
                if section_magic == b'nodK':
                    keyframes = []
                    num_sections, num_keyframes = struct.unpack("<2I", f.read(8))
                    for _ in range(num_keyframes):
                        string_offset, = struct.unpack("<I", f.read(4))
                        node_name = read_from_string_dictionary (f, block_offsets["dictionary"] + string_offset)
                        kf_data = struct.unpack("<4I", f.read(16))
                        keyframes.append({'node_name': node_name, 'num_keyframes': kf_data[0], 'times': kf_data[1],
                            'channel': kf_data[2], 'trs_values': kf_data[3]})
                if section_magic == b'visK':
                    visK_blocks = []
                    num_sections, num_visK_data = struct.unpack("<2I", f.read(8))
                    for _ in range(num_visK_data):
                        string_offset, = struct.unpack("<I", f.read(4))
                        node_name = read_from_string_dictionary (f, block_offsets["dictionary"] + string_offset)
                        visK_data = struct.unpack("<3I", f.read(12))
                        visK_blocks.append([node_name,visK_data])
            ani_struct = []
            for i in range(len(keyframes)):
                ani_block = {'bone': keyframes[i]['node_name'], 'channel': {2:'translation', 14:'rotation'}[keyframes[i]['channel']]}
                f.seek(block_offsets["times"] + keyframes[i]['times'] * 2)
                times = struct.unpack("<{}H".format(keyframes[i]['num_keyframes']),
                    f.read(keyframes[i]['num_keyframes']*2))
                ani_block['inputs'] = [float(x) / ani_fps for x in times]
                f.seek(block_offsets["trs_vals"] + keyframes[i]['trs_values'] * 4)
                ani_block['outputs'] = []
                num_vals = {2:3, 14:4}[keyframes[i]['channel']]
                for _ in range(keyframes[i]['num_keyframes']):
                    ani_block['outputs'].append(list(struct.unpack("<{}f".format(num_vals), f.read(num_vals*4))))
                ani_struct.append(ani_block)
            node_dict = {gltf_data['nodes'][j]['name']:j for j in range(len(gltf_data['nodes']))}
            if not all([x['bone'] in node_dict.keys() for x in ani_struct]):
                input("Warning! This animation may not be compatible with the provided .mdl file! Press Enter to continue.")
            for i in range(len(ani_struct)):
                if ani_struct[i]['bone'] in node_dict.keys():
                    sampler = { 'input': len(gltf_data['accessors']), 'interpolation': 'LINEAR', 'output':  len(gltf_data['accessors'])+1 }
                    channel = { 'sampler': len(gltf_data['animations'][0]['samplers']),\
                        'target': { 'node': node_dict[ani_struct[i]['bone']],\
                        'path': ani_struct[i]['channel'] } }
                    gltf_data['accessors'].append({"bufferView" : len(gltf_data['bufferViews']),\
                        "componentType": 5126,\
                        "count": len(ani_struct[i]['inputs']),\
                        "type": 'SCALAR',\
                        "max": [max(ani_struct[i]['inputs'])], "min": [min(ani_struct[i]['inputs'])]})
                    input_buffer = numpy.array(ani_struct[i]['inputs'],dtype='float32').tobytes()
                    gltf_data['bufferViews'].append({"buffer": 0,\
                        "byteOffset": len(giant_buffer),\
                        "byteLength": len(input_buffer)})
                    giant_buffer += input_buffer
                    gltf_data['accessors'].append({"bufferView" : len(gltf_data['bufferViews']),\
                        "componentType": 5126,\
                        "count": len(ani_struct[i]['outputs']),\
                        "type": {'translation':'VEC3', 'rotation':'VEC4', 'scale':'VEC3'}[ani_struct[i]['channel']]})
                    output_buffer = numpy.array(ani_struct[i]['outputs'],dtype='float32').tobytes()
                    gltf_data['bufferViews'].append({"buffer": 0,\
                        "byteOffset": len(giant_buffer),\
                        "byteLength": len(output_buffer)})
                    giant_buffer +=output_buffer
                    gltf_data['animations'][0]['channels'].append(channel)
                    gltf_data['animations'][0]['samplers'].append(sampler)
            skin = {}
            skin['skeleton'] = 0
            joints = [i for i in range(len(gltf_data['nodes'])) if i != 0]
            if len(joints) > 0:
                skin['joints'] = joints
            gltf_data['skins'].append(skin)
            # Write GLB
            gltf_data['buffers'].append({"byteLength": len(giant_buffer)})
            if (os.path.exists(imtn_file[:-4] + '.gltf') or os.path.exists(imtn_file[:-4] + '.glb')) and (overwrite == False):
                if str(input(imtn_file[:-4] + ".glb/.gltf exists! Overwrite? (y/N) ")).lower()[0:1] == 'y':
                    overwrite = True
            if (overwrite == True) or not (os.path.exists(imtn_file[:-4] + '.gltf') or os.path.exists(imtn_file[:-4] + '.glb')):
                if write_binary_gltf == True:
                    with open(imtn_file[:-4]+'.glb', 'wb') as f:
                        jsondata = json.dumps(gltf_data).encode('utf-8')
                        jsondata += b' ' * (4 - len(jsondata) % 4)
                        f.write(struct.pack('<III', 1179937895, 2, 12 + 8 + len(jsondata) + 8 + len(giant_buffer)))
                        f.write(struct.pack('<II', len(jsondata), 1313821514))
                        f.write(jsondata)
                        f.write(struct.pack('<II', len(giant_buffer), 5130562))
                        f.write(giant_buffer)
                else:
                    gltf_data['buffers'][0]["uri"] = imtn_file[:-4]+'.bin'
                    with open(imtn_file[:-4]+'.bin', 'wb') as f:
                        f.write(giant_buffer)
                    with open(imtn_file[:-4]+'.gltf', 'wb') as f:
                        f.write(json.dumps(gltf_data, indent=4).encode("utf-8"))
    return

if __name__ == "__main__":
    # Set current directory
    if getattr(sys, 'frozen', False):
        os.chdir(os.path.dirname(sys.executable))
    else:
        os.chdir(os.path.abspath(os.path.dirname(__file__)))

    if os.path.exists('00_base.mdl'): #Default choice
        skel_struct = obtain_skeleton_from_imdl ('00_base.mdl')
    else:
        imdl_files = glob.glob('*.mdl')
        if len(imdl_files) > 0:
            skel_struct = obtain_skeleton_from_imdl (imdl_files[0])
        else:
            input("No .mdl found to use as a skeleton! Press Enter to quit.")
            sys.exit()

    # If argument given, attempt to export from file in argument
    if len(sys.argv) > 1:
        import argparse
        parser = argparse.ArgumentParser()
        parser.add_argument('-t', '--textformat', help="Write gltf instead of glb", action="store_false")
        parser.add_argument('-o', '--overwrite', help="Overwrite existing files", action="store_true")
        parser.add_argument('imtn_filename', help="Name of imtn file to export from (required).")
        args = parser.parse_args()
        if os.path.exists(args.imtn_filename) and args.imtn_filename[-4:].lower() == '.mdl':
            process_imtn(args.imtn_filename, skel_struct,\
                write_binary_gltf = args.textformat, overwrite = args.overwrite)
    else:
        imtn_files = glob.glob('*.mtn')
        for i in range(len(imtn_files)):
            process_imtn(imtn_files[i], skel_struct)
