"""Check the exported FBX coordinate data independently of Blender re-import."""
from io_scene_fbx import parse_fbx

def children(node,key):
    return [n for n in node.elems if n.id==key]

def properties(node):
    parts=children(node,b"Properties70")
    return {p.props[0]:p.props[4:] for part in parts for p in part.elems}

def verify_raw(path,bounds):
    tree,_=parse_fbx.parse(str(path))
    header,=children(tree,b"GlobalSettings")
    assert properties(header)[b"UnitScaleFactor"]==[1.0],path
    nodes,=children(tree,b"Objects")
    model,=children(nodes,b"Model")
    geometry,=children(nodes,b"Geometry")
    assert model.props[2]==b"Mesh",path
    values=properties(model)
    for key,expected in (
        (b"Lcl Translation",0),(b"Lcl Rotation",0),(b"Lcl Scaling",1),
        (b"GeometricTranslation",0),(b"GeometricRotation",0),(b"GeometricScaling",1),
        (b"PreRotation",0),(b"PostRotation",0),
    ):
        assert all(abs(x-expected)<1e-6 for x in values.get(key,[expected]*3)),(path,key,values.get(key))
    vert,=children(geometry,b"Vertices")
    v=vert.props[0]
    raw=[v[0::3],v[2::3],v[1::3]]
    low=[min(raw[0]),-max(raw[1]),min(raw[2])]
    high=[max(raw[0]),-min(raw[1]),max(raw[2])]
    assert max(abs(cm-m*100) for pair,ref in zip((low,high),bounds) for cm,m in zip(pair,ref))<.01,(path,low,high,bounds)
    return dict(units="centimetres",model_transform="identity")
