# Auditing a past version of a wall from the .unity scene file

Use this when you need "what did the wall look like before commit X" — Unity only holds the current
state, and the scene YAML is far too large to read directly (Akasaka.unity ≈ 470k lines).

```bash
git show <sha>:Assets/Edo/Scenes/Akasaka.unity > /tmp/before.unity
python3 references/scene_prefab_dump.py /tmp/before.unity
```

`scene_prefab_dump.py` prints, per `Ishigaki_Ext_*` group: child count, the histogram of
`scale.y`, the histogram of yaw, which prefab GUIDs were used, and the neighbour-to-neighbour
coping step (mean / max / count above 0.10 m). Edit the target-name list at the bottom for other
walls.

## Scene-YAML facts the parser relies on

- Documents are separated by `--- !u!<classid> &<fileid>`; `1` = GameObject, `4` = Transform,
  `1001` = PrefabInstance.
- Wall pieces are **PrefabInstances**, not plain Transforms — their transform lives in
  `m_Modifications` as `propertyPath: m_LocalPosition.x` etc., and the instance name is the
  `m_Name` modification. A parser that only walks class-4 Transforms will report zero children.
- Parent linkage for a PrefabInstance is `m_TransformParent: {fileID: …}`, pointing at the group
  root's **Transform** fileID (not the GameObject's).
- Group roots sit at the origin with identity rotation, so local == world for the pieces.
- Yaw from the stored quaternion: `atan2(2(wy + xz), 1 − 2(y² + x²))`, degrees, mod 360.
- Coping height = `position.y + 4.0 * scale.y` for the `Castle Wall` family.

## zsh gotcha when looping over commits

`git show $c:Assets/…` breaks in zsh — `:A` is a history/parameter modifier and mangles the path.
Always brace it:

```bash
for c in $(git log --format=%h -14 -- Assets/Edo/Scenes/Akasaka.unity); do
  n=$(git show "${c}:Assets/Edo/Scenes/Akasaka.unity" | grep -c "Castle Wall Corner")
  echo "$c corner_refs=$n  $(git show --format='%s' -s $c)"
done
```

Counting `"Castle Wall Corner"` occurrences across commits is the cheapest way to bisect *when*
corner pieces entered (or vanished from) a wall.
