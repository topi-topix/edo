import re, sys, math, collections, json

path = sys.argv[1]
txt = open(path, encoding='utf-8', errors='replace').read()
docs = re.split(r'\n--- !u!(\d+) &(\d+)(?: stripped)?\n', txt)
objs = {}
for i in range(1, len(docs)-2, 3):
    objs[docs[i+1]] = (docs[i], docs[i+2])

go_name, tf = {}, {}
for fid, (cid, body) in objs.items():
    if cid == '1':
        m = re.search(r'^  m_Name: (.*)$', body, re.M)
        go_name[fid] = m.group(1).strip() if m else '?'
    elif cid == '4':
        g = re.search(r'm_GameObject: \{fileID: (\d+)\}', body)
        fa = re.search(r'm_Father: \{fileID: (\d+)\}', body)
        pos = re.search(r'm_LocalPosition: \{x: ([-\d.e+]+), y: ([-\d.e+]+), z: ([-\d.e+]+)\}', body)
        scl = re.search(r'm_LocalScale: \{x: ([-\d.e+]+), y: ([-\d.e+]+), z: ([-\d.e+]+)\}', body)
        rot = re.search(r'm_LocalRotation: \{x: ([-\d.e+]+), y: ([-\d.e+]+), z: ([-\d.e+]+), w: ([-\d.e+]+)\}', body)
        tf[fid] = dict(go=g.group(1) if g else None, father=fa.group(1) if fa else '0',
                       pos=tuple(float(v) for v in pos.groups()) if pos else None,
                       scl=tuple(float(v) for v in scl.groups()) if scl else None,
                       rot=tuple(float(v) for v in rot.groups()) if rot else None,
                       stripped=(g is None))

# prefab instances
pi = {}
for fid, (cid, body) in objs.items():
    if cid != '1001':
        continue
    fa = re.search(r'm_TransformParent: \{fileID: (\d+)\}', body)
    nm = re.search(r'propertyPath: m_Name\n      value: (.*)\n', body)
    guid = re.search(r'm_SourcePrefab: \{fileID: [-\d]+, guid: ([0-9a-f]+)', body)
    def ov(p):
        m = re.search(r'propertyPath: ' + p + r'\n      value: ([-\d.eE+]+)\n', body)
        return float(m.group(1)) if m else None
    pi[fid] = dict(father=fa.group(1) if fa else '0', name=nm.group(1).strip() if nm else '?',
                   guid=guid.group(1) if guid else '?',
                   pos=(ov(r'm_LocalPosition\.x'), ov(r'm_LocalPosition\.y'), ov(r'm_LocalPosition\.z')),
                   scl=(ov(r'm_LocalScale\.x'), ov(r'm_LocalScale\.y'), ov(r'm_LocalScale\.z')),
                   rot=(ov(r'm_LocalRotation\.x'), ov(r'm_LocalRotation\.y'), ov(r'm_LocalRotation\.z'), ov(r'm_LocalRotation\.w')))

def yaw(q):
    if not q or q[0] is None: return None
    x, y, z, w = q
    return round(math.degrees(math.atan2(2*(w*y + x*z), 1 - 2*(y*y + x*x))) % 360, 2)

# locate Edo_Yashiki_*/Ishigaki transforms
def name_of_tf(fid):
    t = tf.get(fid)
    if not t or not t['go']: return None
    return go_name.get(t['go'])

targets = {}
for fid, t in tf.items():
    if name_of_tf(fid) == 'Ishigaki':
        par = name_of_tf(t['father'])
        if par and par.startswith('Edo_Yashiki'):
            targets[par] = fid

out = []
for gname, root in sorted(targets.items()):
    kids = []
    for fid, p in pi.items():
        if p['father'] == root and p['pos'][0] is not None:
            kids.append(dict(name=p['name'], guid=p['guid'][:8], pos=p['pos'], scl=p['scl'], yaw=yaw(p['rot'])))
    for fid, t in tf.items():
        if t['father'] == root and not t['stripped']:
            kids.append(dict(name=name_of_tf(fid), guid='plain', pos=t['pos'], scl=t['scl'], yaw=yaw(t['rot'])))
    out.append(dict(group=gname, n=len(kids), kids=kids))

json.dump(out, open(sys.argv[2], 'w'))
for o in out:
    ks = o['kids']
    print('===', o['group'], o['n'])
    print('  guid :', dict(collections.Counter(k['guid'] for k in ks)))
    print('  scale:', dict(collections.Counter(tuple(round(v,4) if v is not None else None for v in k['scl']) for k in ks)))
    print('  posY :', dict(collections.Counter(round(k['pos'][1],3) for k in ks)))
    print('  yaw  :', dict(sorted(collections.Counter(k['yaw'] for k in ks).items())))
