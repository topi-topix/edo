import re, sys, math, collections

path = sys.argv[1]
txt = open(path, encoding='utf-8', errors='replace').read()

# split into documents
docs = re.split(r'\n--- !u!(\d+) &(\d+)(?: stripped)?\n', txt)
# docs[0] = header, then triples (classid, fileid, body)
objs = {}   # fileid -> (classid, body)
for i in range(1, len(docs)-2, 3):
    objs[docs[i+1]] = (docs[i], docs[i+2])

gameobjects = {}   # fileid -> name
transforms = {}    # fileid -> dict
for fid, (cid, body) in objs.items():
    if cid == '1':
        m = re.search(r'^  m_Name: (.*)$', body, re.M)
        gameobjects[fid] = m.group(1).strip() if m else '?'
    elif cid == '4':
        go = re.search(r'm_GameObject: \{fileID: (\d+)\}', body)
        pos = re.search(r'm_LocalPosition: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', body)
        rot = re.search(r'm_LocalRotation: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+), w: ([-\d.e]+)\}', body)
        scl = re.search(r'm_LocalScale: \{x: ([-\d.e]+), y: ([-\d.e]+), z: ([-\d.e]+)\}', body)
        fat = re.search(r'm_Father: \{fileID: (\d+)\}', body)
        if not (go and pos and scl):
            continue
        transforms[fid] = dict(go=go.group(1), pos=tuple(float(x) for x in pos.groups()),
                               rot=tuple(float(x) for x in rot.groups()) if rot else None,
                               scl=tuple(float(x) for x in scl.groups()),
                               father=fat.group(1) if fat else '0')

# prefab instances (classid 1001) — get their name + transform overrides
prefabs = {}
for fid, (cid, body) in objs.items():
    if cid != '1001':
        continue
    src = re.search(r'm_SourcePrefab: \{fileID: [-\d]+, guid: ([0-9a-f]+)', body)
    fat = re.search(r'm_TransformParent: \{fileID: (\d+)\}', body)
    name = re.search(r'propertyPath: m_Name\n      value: (.*)\n', body)
    def ov(p):
        m = re.search(r'propertyPath: ' + p + r'\n      value: ([-\d.e]+)\n', body)
        return float(m.group(1)) if m else None
    prefabs[fid] = dict(guid=src.group(1) if src else '?', father=fat.group(1) if fat else '0',
                        name=name.group(1).strip() if name else '?',
                        pos=(ov('m_LocalPosition\\.x'), ov('m_LocalPosition\\.y'), ov('m_LocalPosition\\.z')),
                        scl=(ov('m_LocalScale\\.x'), ov('m_LocalScale\\.y'), ov('m_LocalScale\\.z')),
                        rot=(ov('m_LocalRotation\\.x'), ov('m_LocalRotation\\.y'), ov('m_LocalRotation\\.z'), ov('m_LocalRotation\\.w')))

# find roots
name2tf = {}
for fid, t in transforms.items():
    n = gameobjects.get(t['go'])
    name2tf.setdefault(n, []).append(fid)

for target in ['Ishigaki_Ext_1', 'Ishigaki_Ext_2', 'Ishigaki_Ext_3', 'Ishigaki_Ext_4']:
    tfids = name2tf.get(target, [])
    if not tfids:
        print(target, 'NOT FOUND'); continue
    root = tfids[0]
    kids = []
    for fid, t in transforms.items():
        if t['father'] == root:
            kids.append((gameobjects.get(t['go']), t['pos'], t['rot'], t['scl'], 'tf'))
    for fid, p in prefabs.items():
        if p['father'] == root:
            kids.append((p['name'], p['pos'], p['rot'], p['scl'], 'prefab:' + p['guid'][:6]))
    print('===', target, 'children =', len(kids))
    ys = collections.Counter()
    for k in kids:
        ys[round(k[3][1], 3) if k[3][1] is not None else None] += 1
    def yaw(q):
        if not q or q[0] is None: return None
        x, y, z, w = q
        return round(math.degrees(math.atan2(2*(w*y + x*z), 1 - 2*(y*y + x*x))) % 360, 1)
    rots = collections.Counter(yaw(k[2]) for k in kids)
    print('  scaleY:', dict(sorted(ys.items(), key=lambda kv: -kv[1])))
    print('  yaw   :', dict(sorted(rots.items(), key=lambda kv: -kv[1])))
    kinds = collections.Counter(k[4] for k in kids)
    print('  kinds :', dict(kinds))

print()
print('--- neighbour step (top-height jump between spatially adjacent pieces) ---')
for target in ['Ishigaki_Ext_1','Ishigaki_Ext_2','Ishigaki_Ext_3','Ishigaki_Ext_4']:
    root = name2tf.get(target,[None])[0]
    if not root: continue
    kids=[]
    for fid,p in prefabs.items():
        if p['father']==root and p['pos'][0] is not None:
            kids.append((p['pos'], p['scl'][1], yaw(p['rot'])))
    # group by yaw bucket, order along run
    buckets={}
    for pos,sy,yw in kids:
        buckets.setdefault(round(yw or 0), []).append((pos,sy))
    steps=[]
    for yw,items in buckets.items():
        a=math.radians(yw); dx,dz=math.sin(a),math.cos(a)
        items.sort(key=lambda it: it[0][0]*dx+it[0][2]*dz)
        for i in range(1,len(items)):
            steps.append(abs(items[i][1]-items[i-1][1])*4.0)  # *4 = mesh height per scale unit
    if steps:
        steps.sort()
        print(f'  {target}: n={len(steps)}  mean={sum(steps)/len(steps):.3f}m  max={steps[-1]:.3f}m  >0.10m count={sum(1 for s in steps if s>0.10)}')
