# Tool to export model data from the imdl format used by Valkyrie Anatomia: The Origin.
#
# Usage:  Run by itself without commandline arguments and it will read only the mesh section of
# every model it finds in the folder and output glb files.
#
# For command line options, run:
# /path/to/python3 vato_extract_imdl.py --help
#
# Requires lib_fmtibvb.py, put in the same directory
#
# GitHub eArmada8/vato_mdl_tool

try:
    import io, struct, copy, json, glob, os, sys
    from itertools import chain
    from lib_fmtibvb import *
except ModuleNotFoundError as e:
    print("Python module missing! {}".format(e.msg))
    input("Press Enter to abort.")
    raise   

#Set to False to default non-matching textures to the first texture
ask_if_texture_does_not_match = True

def make_fmt(uv = True, normals = True, weights = True):
    semantic_count = 0
    fmt = {'stride': '12', 'topology': 'trianglelist', 'format': 'DXGI_FORMAT_R16_UINT',\
        'elements': [{'id': str(semantic_count), 'SemanticName': 'POSITION', 'SemanticIndex': '0',\
        'Format': 'R32G32B32_FLOAT', 'InputSlot': '0', 'AlignedByteOffset': '0',\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'}]}
    stride = 12 # Position only
    if uv:
        semantic_count += 1
        fmt['elements'].append({'id': str(semantic_count), 'SemanticName': 'TEXCOORD',\
        'SemanticIndex': '0', 'Format': 'R32G32_FLOAT', 'InputSlot': '0', 'AlignedByteOffset': str(stride),\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'})
        stride += 8
    if normals:
        semantic_count += 1
        fmt['elements'].append({'id': str(semantic_count), 'SemanticName': 'NORMAL',\
        'SemanticIndex': '0', 'Format': 'R32G32B32_FLOAT', 'InputSlot': '0', 'AlignedByteOffset': str(stride),\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'})
        stride += 12
    if weights:
        semantic_count += 1
        fmt['elements'].append({'id': str(semantic_count), 'SemanticName': 'BLENDINDICES',\
        'SemanticIndex': '0', 'Format': 'R8G8B8A8_UINT', 'InputSlot': '0', 'AlignedByteOffset': str(stride),\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'})
        stride += 4
        semantic_count += 1
        fmt['elements'].append({'id': str(semantic_count), 'SemanticName': 'BLENDWEIGHTS',\
        'SemanticIndex': '0', 'Format': 'R32G32B32A32_FLOAT', 'InputSlot': '0', 'AlignedByteOffset': str(stride),\
        'InputSlotClass': 'per-vertex', 'InstanceDataStepRate': '0'})
        stride += 16
    fmt['stride'] = str(stride)
    return(fmt)

def read_from_string_dictionary (f, start_offset):
    current_loc = f.tell()
    f.seek(start_offset)
    null_term_string = f.read(1)
    while null_term_string[-1] != 0:
        null_term_string += f.read(1)
    f.seek(current_loc)
    return(null_term_string[:-1].decode())

def convert_format_for_gltf(dxgi_format):
    dxgi_format = dxgi_format.split('DXGI_FORMAT_')[-1]
    dxgi_format_split = dxgi_format.split('_')
    if len(dxgi_format_split) == 2:
        numtype = dxgi_format_split[1]
        vec_format = re.findall("[0-9]+",dxgi_format_split[0])
        vec_bits = int(vec_format[0])
        vec_elements = len(vec_format)
        if numtype in ['FLOAT', 'UNORM', 'SNORM']:
            componentType = 5126
            componentStride = len(re.findall('[0-9]+', dxgi_format)) * 4
            dxgi_format = "".join(['R32','G32','B32','A32','D32'][0:componentStride//4]) + "_FLOAT"
        elif numtype == 'UINT':
            if vec_bits == 32:
                componentType = 5125
                componentStride = len(re.findall('[0-9]+', dxgi_format)) * 4
            elif vec_bits == 16:
                componentType = 5123
                componentStride = len(re.findall('[0-9]+', dxgi_format)) * 2
            elif vec_bits == 8:
                componentType = 5121
                componentStride = len(re.findall('[0-9]+', dxgi_format))
        accessor_types = ["SCALAR", "VEC2", "VEC3", "VEC4"]
        accessor_type = accessor_types[len(re.findall('[0-9]+', dxgi_format))-1]
        return({'format': dxgi_format, 'componentType': componentType,\
            'componentStride': componentStride, 'accessor_type': accessor_type})
    else:
        return(False)

def convert_fmt_for_gltf(fmt):
    new_fmt = copy.deepcopy(fmt)
    stride = 0
    new_semantics = {'BLENDWEIGHTS': 'WEIGHTS', 'BLENDINDICES': 'JOINTS'}
    need_index = ['WEIGHTS', 'JOINTS', 'COLOR', 'TEXCOORD']
    for i in range(len(fmt['elements'])):
        if new_fmt['elements'][i]['SemanticName'] in new_semantics.keys():
            new_fmt['elements'][i]['SemanticName'] = new_semantics[new_fmt['elements'][i]['SemanticName']]
        new_info = convert_format_for_gltf(fmt['elements'][i]['Format'])
        new_fmt['elements'][i]['Format'] = new_info['format']
        if new_fmt['elements'][i]['SemanticName'] in need_index:
            new_fmt['elements'][i]['SemanticName'] = new_fmt['elements'][i]['SemanticName'] + '_' +\
                new_fmt['elements'][i]['SemanticIndex']
        new_fmt['elements'][i]['AlignedByteOffset'] = stride
        new_fmt['elements'][i]['componentType'] = new_info['componentType']
        new_fmt['elements'][i]['componentStride'] = new_info['componentStride']
        new_fmt['elements'][i]['accessor_type'] = new_info['accessor_type']
        stride += new_info['componentStride']
    index_fmt = convert_format_for_gltf(fmt['format'])
    new_fmt['format'] = index_fmt['format']
    new_fmt['componentType'] = index_fmt['componentType']
    new_fmt['componentStride'] = index_fmt['componentStride']
    new_fmt['accessor_type'] = index_fmt['accessor_type']
    new_fmt['stride'] = stride
    return(new_fmt)

def fix_strides(submesh):
    offset = 0
    for i in range(len(submesh['vb'])):
        submesh['vb'][i]['fmt']['AlignedByteOffset'] = str(offset)
        submesh['vb'][i]['stride'] = get_stride_from_dxgi_format(submesh['vb'][i]['fmt']['Format'])
        offset += submesh['vb'][i]['stride']
    return(submesh)

def process_imdl (imdl_file, write_raw_buffers = False, write_binary_gltf = True, overwrite = False):
    global ask_if_texture_does_not_match
    def add_child_to_node (nodes, i):
        current_node = i
        nodes[i]['children'] = []
        for j in range(nodes[i]['num_children']):
            i += 1
            nodes[current_node]['children'].append(i)
            nodes, i = add_child_to_node(nodes, i)
        return (nodes, i)
    print("Processing {}...".format(imdl_file))
    gltf_data = {}
    gltf_data['asset'] = { 'version': '2.0' }
    gltf_data['accessors'] = []
    gltf_data['bufferViews'] = []
    gltf_data['buffers'] = []
    gltf_data['meshes'] = []
    gltf_data['materials'] = []
    gltf_data['nodes'] = []
    gltf_data['samplers'] = []
    gltf_data['scenes'] = [{}]
    gltf_data['scenes'][0]['nodes'] = [0]
    gltf_data['scene'] = 0
    gltf_data['skins'] = []
    gltf_data['textures'] = []
    giant_buffer = bytes()
    buffer_view = 0
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
                if section_magic == b'tex ':
                    textures = []
                    num_sections, num_textures = struct.unpack("<2I", f.read(8))
                    for _ in range(num_textures):
                        string_offset, = struct.unpack("<I", f.read(4))
                        texture = read_from_string_dictionary (f, block_offsets["dictionary"] + string_offset)
                        textures.append(texture)
                elif section_magic == b'mate':
                    materials = []
                    num_sections, num_materials = struct.unpack("<2I", f.read(8))
                    for _ in range(num_materials):
                        material = {}
                        string_offset, = struct.unpack("<I", f.read(4))
                        material['name'] = read_from_string_dictionary (f, block_offsets["dictionary"] + string_offset)
                        material['unk0'], material['flags'] = struct.unpack("<iI", f.read(8))
                        material['unk_parameters'] = list(struct.unpack("<IfIfIfIfIf", f.read(40)))
                        material['unk2'], material['unk3'], material['unk4'] = struct.unpack("<f2H", f.read(8))
                        material['unk_values'] = list(struct.unpack("<4I", f.read(16)))
                        materials.append(material)
                elif section_magic == b'mesh':
                    meshes = []
                    num_sections, num_meshes = struct.unpack("<2I", f.read(8))
                    for _ in range(num_meshes):
                        mesh = {}
                        mesh['material'], mesh['unk0'], mesh['unk1'], mesh['index_buffer_len'], mesh['index_buffer_offset']\
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
                elif section_magic == b'geom':
                    geoms = []
                    num_sections, num_geoms = struct.unpack("<2I", f.read(8))
                    for _ in range(num_geoms):
                        geom = {}
                        string_offset, = struct.unpack("<I", f.read(4))
                        geom['name'] = read_from_string_dictionary (f, block_offsets["dictionary"] + string_offset)
                        geom['node'], geom['unk1'], geom['unk2'], geom['unk3'],\
                            geom['vertex_buffer'] = struct.unpack("<HhIHH", f.read(12))
                        geom['matrix'] = list(struct.unpack("<16f", f.read(64)))
                        geom['bbox'] = list(struct.unpack("<9f", f.read(36)))
                        geom['zeroes0'] = list(struct.unpack("<4I", f.read(16)))
                        geom['num_index_buffers'], geom['first_index_buffer'] = struct.unpack("<2H", f.read(4))
                        geom['num_bones'], = struct.unpack("<I", f.read(4))
                        geom['unk7'], geom['bone_palette_offset'] = struct.unpack("<2I", f.read(8))
                        geom['zeroes1'] = list(struct.unpack("<3I", f.read(12)))
                        geoms.append(geom)
                elif section_magic == b'node':
                    nodes = []
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
                    #print("Skipping section {}...".format(section_magic.decode()))
                    f.seek(section_size - 8, 1)
            # Materials
            gltf_data['images'] = [{'uri':'{0:02d}_{1}.png'.format(i, textures[i])} for i in range(len(textures))]
            # I can't figure out how to assign textures, so my best guess is via the names of the materials
            image_list = [x.split('.tga')[0] for x in textures]
            image_assignments_names = ['_'.join(x['name'].split('_')[1:]) if '_' in x['name'] else x for x in materials]
            internal_assignments = [x['unk_values'][2] for x in materials]
            if all([x < len(image_list) for x in internal_assignments]):
                image_assignments = internal_assignments
            elif ask_if_texture_does_not_match == True:
                image_assignments = []
                for i in range(len(image_assignments_names)):
                    if image_assignments_names[i] in image_list:
                        image_assignments.append(image_list.index(image_assignments_names[i]))
                    else:
                        if len(image_list) > 1:
                            print("Material {} does not have a matching image!  Which image is correct?".format(image_assignments_names[i]))
                            for j in range(len(image_list)):
                                print("{0}. {1}".format(j, image_list[j]))
                            img_choice = -1
                            while not img_choice in range(len(image_assignments_names)):
                                raw_input = input("Please select choice by number: ")
                                try:
                                    img_choice = int(raw_input)
                                except:
                                    pass
                            image_assignments.append(img_choice)
                        else:
                            image_assignments.append(0)
            else:
                image_assignments = [image_list.index(x) if x in image_list else 0 for x in image_assignments_names]
            for i in range(len(materials)):
                g_material = { 'name': materials[i]['name'] }
                sampler = { 'wrapS': 10497, 'wrapT': 10497 } # I have no idea if this setting exists
                texture = { 'source': image_assignments[i], 'sampler': len(gltf_data['samplers']) }
                g_material['pbrMetallicRoughness'] = { 'baseColorTexture' : { 'index' : len(gltf_data['textures']), },\
                    'metallicFactor' : 0.0, 'roughnessFactor' : 1.0 }
                if materials[i]['flags'] & 0x10:
                    g_material['alphaMode'] = 'MASK'
                elif not materials[i]['flags'] & 0x02:
                    g_material['alphaMode'] = 'BLEND'
                gltf_data['samplers'].append(sampler)
                gltf_data['textures'].append(texture)
                gltf_data['materials'].append(g_material)
            # Nodes
            for i in range(len(nodes)):
                g_node = {'children': nodes[i]['children'], 'name': nodes[i]['name'], 'matrix': nodes[i]['matrix']}
                gltf_data['nodes'].append(g_node)
            for i in range(len(gltf_data['nodes'])):
                if len(gltf_data['nodes'][i]['children']) == 0:
                    del(gltf_data['nodes'][i]['children'])
            # Meshes
            node_list = [x['name'] for x in nodes]
            material_dict = {gltf_data['materials'][i]['name']:i for i in range(len(gltf_data['materials']))}
            if write_raw_buffers == True:
                overwrite_buffers = copy.deepcopy(overwrite)
                if os.path.exists(imdl_file[:-4]) and (os.path.isdir(imdl_file[:-4])) and (overwrite_buffers == False):
                    if str(input(imdl_file[:-4] + " folder exists! Overwrite? (y/N) ")).lower()[0:1] == 'y':
                        overwrite_buffers = True
                if (overwrite_buffers == True) or not os.path.exists(imdl_file[:-4]):
                    if not os.path.exists(imdl_file[:-4]):
                        os.mkdir(imdl_file[:-4])
                    overwrite_buffers = True
            for i in range(len(geoms)):
                uv = (not shapes[geoms[i]['vertex_buffer']]['uv_offset'] == 0)
                normals = (not shapes[geoms[i]['vertex_buffer']]['norm_offset'] == 0)
                weights = (not shapes[geoms[i]['vertex_buffer']]['blendweight_offset'] == 0)
                fmt = make_fmt(uv, normals, weights)
                gltf_fmt = convert_fmt_for_gltf(fmt)
                # Vertex Buffer
                primitives = []
                vb = []
                # Cheating here, seeking only once since the sample files have no padding between buffers
                f.seek(block_offsets["vertices"] + (shapes[geoms[i]['vertex_buffer']]['pos_offset'] * 4))
                pos_buffer = list(struct.unpack("<{}f".format(shapes[geoms[i]['vertex_buffer']]['num_vertices']*3),
                    f.read(shapes[geoms[i]['vertex_buffer']]['num_vertices'] * 4 * 3)))
                vb.append({'Buffer': [pos_buffer[j*3:j*3+3] for j in range(len(pos_buffer)//3)]})
                if uv == True:
                    uv_buffer = list(struct.unpack("<{}f".format(shapes[geoms[i]['vertex_buffer']]['num_vertices']*2),
                        f.read(shapes[geoms[i]['vertex_buffer']]['num_vertices'] * 4 * 2)))
                    vb.append({'Buffer': [uv_buffer[j*2:j*2+2] for j in range(len(uv_buffer)//2)]})
                if normals == True:
                    norm_buffer = list(struct.unpack("<{}f".format(shapes[geoms[i]['vertex_buffer']]['num_vertices']*3),
                        f.read(shapes[geoms[i]['vertex_buffer']]['num_vertices'] * 4 * 3)))
                    vb.append({'Buffer': [norm_buffer[j*3:j*3+3] for j in range(len(norm_buffer)//3)]})
                if weights == True:
                    wt_buffer = list(struct.unpack("<{}f".format(shapes[geoms[i]['vertex_buffer']]['num_vertices']*4),
                        f.read(shapes[geoms[i]['vertex_buffer']]['num_vertices'] * 4 * 4)))
                    bind_matrix_buffer = f.read(64 * geoms[i]['num_bones'])
                    f.seek(block_offsets["blend_indices"] + (shapes[geoms[i]['vertex_buffer']]['blend_indices_offset'] * 1))
                    wt_index_buffer = list(struct.unpack("<{}B".format(shapes[geoms[i]['vertex_buffer']]['num_vertices']*4),
                        f.read(shapes[geoms[i]['vertex_buffer']]['num_vertices'] * 4)))
                    vb.append({'Buffer': [wt_index_buffer[j*4:j*4+4] for j in range(len(wt_index_buffer)//4)]})
                    vb.append({'Buffer': [wt_buffer[j*4:j*4+4] for j in range(len(wt_buffer)//4)]})
                primitive = {"attributes":{}}
                vb_stream = io.BytesIO()
                write_vb_stream(vb, vb_stream, gltf_fmt, e='<', interleave = False)
                block_offset = len(giant_buffer)
                for element in range(len(gltf_fmt['elements'])):
                    primitive["attributes"][gltf_fmt['elements'][element]['SemanticName']]\
                        = len(gltf_data['accessors'])
                    gltf_data['accessors'].append({"bufferView" : len(gltf_data['bufferViews']),\
                        "componentType": gltf_fmt['elements'][element]['componentType'],\
                        "count": len(vb[element]['Buffer']),\
                        "type": gltf_fmt['elements'][element]['accessor_type']})
                    if gltf_fmt['elements'][element]['SemanticName'] == 'POSITION':
                        gltf_data['accessors'][-1]['max'] =\
                            [max([x[0] for x in vb[element]['Buffer']]),\
                             max([x[1] for x in vb[element]['Buffer']]),\
                             max([x[2] for x in vb[element]['Buffer']])]
                        gltf_data['accessors'][-1]['min'] =\
                            [min([x[0] for x in vb[element]['Buffer']]),\
                             min([x[1] for x in vb[element]['Buffer']]),\
                             min([x[2] for x in vb[element]['Buffer']])]
                    gltf_data['bufferViews'].append({"buffer": 0,\
                        "byteOffset": block_offset,\
                        "byteLength": len(vb[element]['Buffer']) *\
                        gltf_fmt['elements'][element]['componentStride'],\
                        "target" : 34962})
                    block_offset += len(vb[element]['Buffer']) *\
                        gltf_fmt['elements'][element]['componentStride']
                vb_stream.seek(0)
                giant_buffer += vb_stream.read()
                vb_stream.close()
                del(vb_stream)
                # Index Buffers
                combined_ib = []
                for j in range(geoms[i]['num_index_buffers']):
                    current_primitive = copy.deepcopy(primitive)
                    f.seek(block_offsets["triangles"] + (meshes[geoms[i]['first_index_buffer']+j]['index_buffer_offset'] * 2))
                    ib = list(struct.unpack("<{}H".format(meshes[geoms[i]['first_index_buffer']+j]['index_buffer_len']),
                        f.read(meshes[geoms[i]['first_index_buffer']+j]['index_buffer_len'] * 2)))
                    combined_ib.extend(ib)
                    ib_stream = io.BytesIO()
                    write_ib_stream(ib, ib_stream, gltf_fmt, e='<')
                    # IB is 16-bit so can be misaligned, unlike VB
                    while (ib_stream.tell() % 4) > 0:
                        ib_stream.write(b'\x00')
                    current_primitive["indices"] = len(gltf_data['accessors'])
                    gltf_data['accessors'].append({"bufferView" : len(gltf_data['bufferViews']),\
                        "componentType": gltf_fmt['componentType'],\
                        "count": meshes[geoms[i]['first_index_buffer']+j]['index_buffer_len'],\
                        "type": gltf_fmt['accessor_type']})
                    gltf_data['bufferViews'].append({"buffer": 0,\
                        "byteOffset": len(giant_buffer),\
                        "byteLength": ib_stream.tell(),\
                        "target" : 34963})
                    ib_stream.seek(0)
                    giant_buffer += ib_stream.read()
                    ib_stream.close()
                    del(ib_stream)
                    current_primitive["mode"] = 4 #TRIANGLES
                    current_primitive["material"] = meshes[geoms[i]['first_index_buffer']+j]['material']
                    primitives.append(current_primitive)
                if not geoms[i]['node'] == 0xFFFF:
                    gltf_data['nodes'][geoms[i]['node']]['mesh'] = len(gltf_data['meshes'])
                else: # Add new node
                    gltf_data['nodes'][0]['children'].append(len(gltf_data['nodes']))
                    gltf_data['nodes'].append({'name': geoms[i]['name'], 'mesh': len(gltf_data['meshes'])})
                gltf_data['meshes'].append({"primitives": primitives, "name": geoms[i]['name']})
                # Skinning
                if weights == True:
                    f.seek(block_offsets["triangles"] + (geoms[i]['bone_palette_offset'] * 2))
                    bone_palette = list(struct.unpack("<{}H".format(geoms[i]['num_bones']), f.read(geoms[i]['num_bones'] * 2)))
                    vgmap = {node_list[bone_palette[i]]: i for i in range(len(bone_palette))}
                    gltf_data['nodes'][geoms[i]['node']]['skin'] = len(gltf_data['skins'])
                    gltf_data['skins'].append({"inverseBindMatrices": len(gltf_data['accessors']), "joints": bone_palette})
                    gltf_data['accessors'].append({"bufferView" : len(gltf_data['bufferViews']),\
                        "componentType": 5126,\
                        "count": geoms[i]['num_bones'],\
                        "type": "MAT4"})
                    gltf_data['bufferViews'].append({"buffer": 0,\
                        "byteOffset": len(giant_buffer),\
                        "byteLength": len(bind_matrix_buffer)})
                    giant_buffer += bind_matrix_buffer
                if write_raw_buffers == True and overwrite_buffers == True:
                    write_fmt(fmt, "{0}/{1:02d}_{2}.fmt".format(imdl_file[:-4], i, geoms[i]['name']))
                    write_vb(vb, "{0}/{1:02d}_{2}.vb".format(imdl_file[:-4], i, geoms[i]['name']), fmt)
                    write_ib(combined_ib, "{0}/{1:02d}_{2}.ib".format(imdl_file[:-4], i, geoms[i]['name']), fmt)
                    with open("{0}/{1:02d}_{2}.vgmap".format(imdl_file[:-4], i, geoms[i]['name']), 'wb') as ff:
                        ff.write(json.dumps(vgmap, indent=4).encode('utf-8'))
            # Write GLB
            gltf_data['buffers'].append({"byteLength": len(giant_buffer)})
            if (os.path.exists(imdl_file[:-4] + '.gltf') or os.path.exists(imdl_file[:-4] + '.glb')) and (overwrite == False):
                if str(input(imdl_file[:-4] + ".glb/.gltf exists! Overwrite? (y/N) ")).lower()[0:1] == 'y':
                    overwrite = True
            if (overwrite == True) or not (os.path.exists(imdl_file[:-4] + '.gltf') or os.path.exists(imdl_file[:-4] + '.glb')):
                if write_binary_gltf == True:
                    with open(imdl_file[:-4]+'.glb', 'wb') as f:
                        jsondata = json.dumps(gltf_data).encode('utf-8')
                        jsondata += b' ' * (4 - len(jsondata) % 4)
                        f.write(struct.pack('<III', 1179937895, 2, 12 + 8 + len(jsondata) + 8 + len(giant_buffer)))
                        f.write(struct.pack('<II', len(jsondata), 1313821514))
                        f.write(jsondata)
                        f.write(struct.pack('<II', len(giant_buffer), 5130562))
                        f.write(giant_buffer)
                else:
                    gltf_data['buffers'][0]["uri"] = imdl_file[:-4]+'.bin'
                    with open(imdl_file[:-4]+'.bin', 'wb') as f:
                        f.write(giant_buffer)
                    with open(imdl_file[:-4]+'.gltf', 'wb') as f:
                        f.write(json.dumps(gltf_data, indent=4).encode("utf-8"))
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
        parser.add_argument('-t', '--textformat', help="Write gltf instead of glb", action="store_false")
        parser.add_argument('-d', '--dumprawbuffers', help="Write fmt/ib/vb/vgmap files in addition to glb", action="store_true")
        parser.add_argument('-o', '--overwrite', help="Overwrite existing files", action="store_true")
        parser.add_argument('imdl_filename', help="Name of imdl file to export from (required).")
        args = parser.parse_args()
        if os.path.exists(args.imdl_filename) and args.imdl_filename[-4:].lower() == '.mdl':
            process_imdl(args.imdl_filename, write_raw_buffers = args.dumprawbuffers,\
                write_binary_gltf = args.textformat, overwrite = args.overwrite)
    else:
        imdl_files = glob.glob('*.mdl')
        for i in range(len(imdl_files)):
            process_imdl(imdl_files[i])
