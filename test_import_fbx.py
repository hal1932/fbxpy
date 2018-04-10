# coding: utf-8
from __future__ import print_function, unicode_literals
import sys

from FbxCommon import *


def dump(key, value=None, indent=0):
    indent = '  ' * indent
    if value is not None:
        if isinstance(value, FbxString):
            value = value.Buffer()
        if isinstance(value, (str, unicode)):
            value = "'{}'".format(value)
        print('{}{}: {}'.format(indent, key, value))
    else:
        print('{}{}'.format(indent, key))


def display_metadata(scene):
    info = scene.GetSceneInfo()

    dump('=== metadata ===')
    indent = 1
    dump('title', info.mTitle, indent)
    dump('subject', info.mSubject, indent)
    dump('author', info.mAuthor, indent)
    dump('keywords', info.mKeywords, indent)
    dump('revision', info.mRevision, indent)
    dump('comment', info.mComment, indent)
    
    thumb = info.GetSceneThumbnail()
    if thumb is not None:
        dump('thumbnail format', thumb.GetDataFormat())
        dump('thumbnail size:', thumb.GetSize())
    
    dump('')


def display_content(scene):
    node = scene.GetRootNode()
    if node is None:
        return
    
    dump('=== content ===')

    for i in xrange(node.GetChildCount()):
        display_node_content(node.GetChild(i))
    
    dump('')


def display_node_content(node, indent=0):
    node_attr = node.GetNodeAttribute()
    if node_attr is None:
        dump('null node attribute', node.GetName(), indent)
        return
    
    dump(node.GetName(), None, indent)

    indent += 1

    attr_type = node_attr.GetAttributeType()
    if attr_type == FbxNodeAttribute.eNull:
        dump('null', None, indent)
    elif attr_type == FbxNodeAttribute.eMesh:
        display_mesh(node, indent)
    else:
        dump(type(node_attr), None, indent)
    
    target = node.GetTarget()
    if target is not None:
        dump(target.GetName())
    
    display_user_properties(node, indent)

    for i in xrange(node.GetChildCount()):
        display_node_content(node.GetChild(i), indent)


def display_mesh(node, indent):
    dump('mesh', None, indent)

    mesh = node.GetNodeAttribute()
    indent += 1

    display_mesh_geom(mesh, indent)
    display_mesh_material(mesh, indent)


def display_mesh_geom(mesh, indent):
    vertex_count = mesh.GetControlPointsCount()
    dump('vertices', vertex_count, indent)

    indent += 1

    points = mesh.GetControlPoints()
    for i in xrange(vertex_count):
        dump(points[i], None, indent)
    
    indent -= 1

    poly_count = mesh.GetPolygonCount()
    layer_count = mesh.GetLayerCount()
    dump('polygons', poly_count, indent)

    for i in xrange(poly_count):
        dump('polygon[{}]'.format(i), None, indent + 1)

        size = mesh.GetPolygonSize(i)
        dump('position', None, indent + 2)

        for j in xrange(size):
            vtx_index = mesh.GetPolygonVertex(i, j)
            dump(points[vtx_index], None, indent + 3)
        
        normals = [[]] * layer_count
        uvs = [[]] * layer_count
        for j in xrange(size):
        
            for k in xrange(layer_count):
                layer = mesh.GetLayer(k)

                normals_elem = layer.GetNormals()
                if normals_elem is not None:
                    normals[k].append(
                        get_vertex_elem(normals_elem, vtx_index, vtx_index)
                    )

                uvs_elem = layer.GetUVs()
                if uvs_elem is not None:
                    uvs[k].append(
                        get_vertex_elem(uvs_elem, vtx_index, mesh.GetTextureUVIndex(i, j))
                    )
        
        for j, normal in enumerate(normals):
            dump('normal{}'.format(j), None, indent + 2)
            for vec in normal:
                dump(vec, None, indent + 3)

        for j, uv in enumerate(uvs):
            dump('uv{}'.format(j), None, indent + 2)
            for vec in uv:
                dump(vec, None, indent + 3)


def display_mesh_material(mesh, indent):
    node = mesh.GetNode()
    material_count = node.GetMaterialCount()

    materials = {node.GetMaterial(x): [] for x in xrange(material_count)}

    for i in xrange(mesh.GetLayerCount()):
        layer = mesh.GetLayer(i)
        
        material_elem = layer.GetMaterials()
        if material_elem is None:
            continue
        
        map_mode = material_elem.GetMappingMode()
        ref_mode = material_elem.GetReferenceMode()
        
        indices = material_elem.GetIndexArray()

        if map_mode == FbxLayerElement.eAllSame:
            index = indices.GetAt(0)
            material = node.GetMaterial(index)
            materials[material].append(xrange(mesh.GetPolygonCount()))
        
        elif map_mode == FbxLayerElement.eByPolygon:
            for j in xrange(mesh.GetPolygonCount()):
                index = indices.GetAt(j)
                material = node.GetMaterial(index)
                materials[material].append(j)
    
    for material, mesh_indices in materials.items():
        dump(material.GetName(), ', '.join(['polygon[{}]'.format(x) for x in mesh_indices]), indent)

        impl = GetImplementation(material, 'ImplementationHLSL')
        if impl is None:
            impl = GetImplementation(material, 'ImplementationCGFX')
        
        if impl is not None:
            dump(impl, None, indent + 1)
        else:
            class_id = material.GetClassId()
            if class_id.Is(FbxSurfaceLambert.ClassId):
                dump('lambert', None, indent + 1)
                dump('diffuse', prop_to_str(material.Diffuse), indent + 2)
                dump('ambient', prop_to_str(material.Ambient), indent + 2)
                dump('emissive', prop_to_str(material.Emissive), indent + 2)
                dump('transparency', prop_to_str(material.TransparencyFactor), indent + 2)
            
            elif class_id.Is(FbxSurfacePhong.ClassId):
                dump('lambert', None, indent + 1)
                dump('diffuse', prop_to_str(material.Diffuse), indent + 2)
                dump('ambient', prop_to_str(material.Ambient), indent + 2)
                dump('emissive', prop_to_str(material.Emissive), indent + 2)
                dump('transparency', prop_to_str(material.TransparencyFactor), indent + 2)
                dump('specular', prop_to_str(material.Specular), indent + 2)
                dump('shininess', prop_to_str(material.Shininess), indent + 2)
                dump('reflection', prop_to_str(material.Reflection), indent + 2)
            
            else:
                dump('unknown', None, indent + 1)
    
    tex_type = FbxCriteria.ObjectType(FbxTexture.ClassId)

    textures = {}
    for material in materials.keys():
        for i in xrange(FbxLayerElement.sTypeTextureCount()):
            channel = FbxLayerElement.sTextureChannelNames(i)

            prop = material.FindProperty(channel)
            if not prop.IsValid():
                continue
            
            layered_tex_count = prop.GetSrcObjectCount(FbxCriteria.ObjectType(FbxLayeredTexture.ClassId))
            if layered_tex_count > 0:
                print('layered texture: ' + prop.GetName())

            else:
                tex_count = prop.GetSrcObjectCount(tex_type)
                for j in xrange(tex_count):
                    texture = prop.GetSrcObject(tex_type)
                    
                    tex_dest = (material.GetName(), prop.GetName())
                    if texture in textures:
                        textures[texture].append(tex_dest)
                    else:
                        textures[texture] = [tex_dest]
    
    for texture, destinations in textures.items():
        dump(texture.GetName(), None, indent)
        dump('file', texture.GetFileName(), indent + 1)
        dump('dest', ', '.join(['{}@{}'.format(p, m) for m, p in destinations]), indent + 1)


def get_vertex_elem(element, vtx_index, elem_index):
    value = None

    map_mode = element.GetMappingMode()
    ref_mode = element.GetReferenceMode()

    if map_mode == FbxLayerElement.eByControlPoint:

        if ref_mode == FbxLayerElement.eDirect:
            value = element.GetDirectArray().GetAt(vtx_index)
        
        elif ref_mode == FbxLayerElement.eIndexToDirect:
            elem_index = element.GetIndexArray().GetAt(vtx_index)
            value = element.GetDirectArray().GetAt(elem_index)
    
    elif map_mode == FbxLayerElement.eByPolygonVertex:
        
        if ref_mode == FbxLayerElement.eDirect or ref_mode == FbxLayerElement.eIndexToDirect:
            value = element.GetDirectArray().GetAt(elem_index)

    return value


def display_user_properties(node, indent):
    prop = node.GetFirstProperty()
    while prop.IsValid():
        if prop.GetFlag(FbxPropertyFlags.eUserDefined):
            dump(
                'user prop',
                'label {}, name {}, {}'.format(prop.GetLabel(), prop.GetName(), prop_to_str(prop)),
                indent)
        prop = node.GetNextProperty(prop)


def prop_to_str(prop):
    prop_type = prop.GetPropertyDataType().GetType()

    if prop_type == eFbxBool:
        return 'bool({})'.format(FbxPropertyBool1(prop).Get())
    elif prop_type == eFbxDouble:
        return 'double({})'.format(FbxPropertyDouble1(prop).Get())
    elif prop_type == eFbxFloat:
        return 'float({})'.format(FbxPropertyFloat1(prop).Get())
    elif prop_type == eFbxInt:
        return 'int({})'.format(FbxPropertyInteger1(prop).Get())
    elif prop_type == eFbxDouble3:
        values = FbxPropertyDouble3(prop).Get()
        return 'double3({}, {}, {})'.format(values[0], values[1], values[2])
    elif prop_type == eFbxDouble4:
        values = FbxPropertyDouble3(prop).Get()
        return 'double4({}, {}, {}, {})'.format(values[0], values[1], values[2], values[3])
    elif prop_type == eFbxString:
        return 'string("{}")'.format(FbxPropertyString(prop).Get().Buffer().strip())
    
    return 'unknown type({})'.format(prop.GetPropertyDataType().GetName())


def main():
    sdk_manager, scene = InitializeSdkObjects()

    if LoadScene(sdk_manager, scene, sys.argv[1]):
        display_metadata(scene)
        display_content(scene)

    sdk_manager.Destroy()
    return 0


if __name__ == '__main__':
    sys.exit(main())
