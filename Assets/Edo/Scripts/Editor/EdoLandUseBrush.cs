using System.Collections.Generic;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 土地利用の手直しブラシ。Scene で地形をクリック/ドラッグして「ここは道/水/武家地…」と
/// 上書きマスク(landuse_override.png)に描き込む。Bake で地形に反映される。
/// 上書きは保存され、古地図を再ベイクしても消えない(下地の上に常に再適用される)。
///
/// 使い方:
///   1) クラスを選ぶ  2) 「塗り開始」  3) Scene で地形を左ドラッグ(Shift=自動に戻す/消しゴム)
///   4) 「Bake で反映」。 元に戻す=「1手戻す」ボタン(ストローク単位)。
/// </summary>
public class EdoLandUseBrush : EditorWindow
{
    byte cls = EdoLandUse.ROAD;
    float radius = 25f;         // ワールド半径(m)
    bool painting;
    Terrain terr;
    TerrainData td;
    Texture2D ov;               // 上書きマスク(alphamap解像度)
    int res;
    Color32[] px;
    readonly List<Color32[]> undo = new List<Color32[]>();
    readonly List<int> undoMarkCounts = new List<int>();   // 各ストローク開始時の marks 数(プレビュー整合用)
    bool strokeDirty;
    readonly List<(Vector3 p,float r,byte c,bool e)> marks = new List<(Vector3,float,byte,bool)>(); // 塗り跡プレビュー
    Vector3 lastMark; bool hasLast;

    [MenuItem("Edo/土地利用/ブラシ")]
    static void Open() => GetWindow<EdoLandUseBrush>("Land Use Brush");

    void OnEnable(){ SceneView.duringSceneGui += OnScene; EnsureLoaded(); }
    void OnDisable(){ SceneView.duringSceneGui -= OnScene; if(ov)DestroyImmediate(ov); }

    void EnsureLoaded()
    {
        var go=GameObject.Find(EdoLandUse.TerrainName); if(go==null)return;
        terr=go.GetComponent<Terrain>(); td=terr.terrainData; res=td.alphamapResolution;
        if(ov!=null)DestroyImmediate(ov);
        ov=EdoLandUse.LoadOrCreateOverride(res); px=ov.GetPixels32();
    }

    void OnGUI()
    {
        if(terr==null){ EditorGUILayout.HelpBox("ModernTerrain が見つかりません。",MessageType.Warning); if(GUILayout.Button("再読込"))EnsureLoaded(); return; }
        EditorGUILayout.HelpBox("クラスを選び『塗り開始』→ Scene で地形を左ドラッグ。\nShift+ドラッグ = 自動(下地)に戻す消しゴム。塗ったら『Bake で反映』。",MessageType.Info);

        EditorGUILayout.LabelField("クラス", EditorStyles.boldLabel);
        DrawClassButton(EdoLandUse.ROAD); DrawClassButton(EdoLandUse.WATER);
        DrawClassButton(EdoLandUse.SAMURAI); DrawClassButton(EdoLandUse.COMMONER);
        DrawClassButton(EdoLandUse.TEMPLE); DrawClassButton(EdoLandUse.FIELD);
        DrawClassButton(EdoLandUse.GRASS);

        radius=EditorGUILayout.Slider("ブラシ半径(m)", radius, 3f, 120f);

        GUI.backgroundColor = painting ? new Color(1f,0.5f,0.5f) : new Color(0.6f,1f,0.6f);
        if(GUILayout.Button(painting?"■ 塗り停止":"▶ 塗り開始", GUILayout.Height(32))){ painting=!painting; SceneView.RepaintAll(); }
        GUI.backgroundColor=Color.white;

        using(new EditorGUI.DisabledScope(undo.Count==0))
            if(GUILayout.Button($"↶ 1手戻す ({undo.Count})")) UndoStroke();

        EditorGUILayout.Space();
        if(GUILayout.Button("💾 上書きを保存")) { EdoLandUse.SaveOverride(ov); ShowNotification(new GUIContent("保存しました")); }
        // 塗った所だけベイク = 他所のテレインペイント(手描き)を巻き込まない。既定はこちら。
        GUI.backgroundColor=new Color(0.7f,0.85f,1f);
        using(new EditorGUI.DisabledScope(marks.Count==0))
            if(GUILayout.Button($"🔥 塗った所だけ Bake ({marks.Count}箇所)", GUILayout.Height(30))){
                EdoLandUse.SaveOverride(ov);
                float feather=Mathf.Max(3f, radius*0.25f);
                var mask=new EdoLandUse.BakeMask{ Feather=feather };
                foreach(var m in marks) mask.AddSpot(m.p, m.r+feather);
                EdoLandUse.Bake(true, mask);
                marks.Clear(); hasLast=false; SceneView.RepaintAll();
            }
        GUI.backgroundColor=new Color(1f,0.85f,0.7f);
        if(GUILayout.Button("全面 Bake（手描きは消えます）")){
            if(EditorUtility.DisplayDialog("全面ベイク",
                "地面の塗りと草を全面的に作り直します。\nテレインペイントで手描きした分は消えます。",
                "全面ベイクする","やめる")){
                EdoLandUse.SaveOverride(ov); EdoLandUse.Bake(true); marks.Clear(); hasLast=false; SceneView.RepaintAll(); }
        }
        using(new EditorGUI.DisabledScope(marks.Count==0))
            if(GUILayout.Button($"塗り跡プレビューを消す ({marks.Count})")){ marks.Clear(); hasLast=false; SceneView.RepaintAll(); }
        GUI.backgroundColor=Color.white;
        EditorGUILayout.LabelField("選択中", $"{EdoLandUse.ClassName(cls)}");
    }

    void DrawClassButton(byte c)
    {
        var col=EdoLandUse.BrushColor(c);
        var old=GUI.backgroundColor; GUI.backgroundColor = (cls==c)? Color.Lerp(col,Color.white,0.2f):col;
        if(GUILayout.Button((cls==c?"● ":"")+EdoLandUse.ClassName(c), GUILayout.Height(24))) cls=c;
        GUI.backgroundColor=old;
    }

    void OnScene(SceneView sv)
    {
        if(terr==null) return;
        // 塗った跡(このセッション)を色付きの面で表示 → 塗っている最中に塗り場所が見える
        for(int i=0;i<marks.Count;i++){
            var m=marks[i];
            Color col = m.e ? new Color(1f,1f,1f,0.28f) : (Color)EdoLandUse.BrushColor(m.c);
            col.a = m.e?0.28f:0.35f; Handles.color=col;
            Handles.DrawSolidDisc(m.p, Vector3.up, m.r);
        }
        if(!painting) return;
        Event e=Event.current;
        int id=GUIUtility.GetControlID(FocusType.Passive);
        HandleUtility.AddDefaultControl(id);

        // カーソル位置に太いブラシ円(選択クラス色)
        Ray ray=HandleUtility.GUIPointToWorldRay(e.mousePosition);
        if(RaycastTerrain(ray, out Vector3 hit)){
            Handles.color = e.shift? new Color(1,1,1,0.95f) : (Color)EdoLandUse.BrushColor(cls);
            Handles.DrawWireDisc(hit, Vector3.up, radius);
            Handles.DrawWireDisc(hit, Vector3.up, Mathf.Max(0f,radius-0.6f));
        }

        if(e.type==EventType.MouseDown && e.button==0){ PushUndo(); strokeDirty=false; hasLast=false; PaintAt(ray,e.shift); e.Use(); }
        else if(e.type==EventType.MouseDrag && e.button==0){ PaintAt(ray,e.shift); e.Use(); }
        else if(e.type==EventType.MouseUp && e.button==0){ if(strokeDirty){ ov.SetPixels32(px); ov.Apply(); } e.Use(); }
        sv.Repaint();
    }

    void PaintAt(Ray ray, bool erase)
    {
        if(!RaycastTerrain(ray, out Vector3 hit)) return;
        // 塗り跡プレビュー用マーク(間引き)
        if(!hasLast || Vector3.Distance(hit,lastMark) > radius*0.5f){
            marks.Add((hit, radius, cls, erase)); lastMark=hit; hasLast=true;
            if(marks.Count>4000) marks.RemoveRange(0,600);
        }
        var O=terr.transform.position; var Sz=td.size;
        // world → 上書きマスク画素(alphamap空間: x=terrainX, y=terrainZ)
        float u=(hit.x-O.x)/Sz.x, v=(hit.z-O.z)/Sz.z;
        float cx=u*(res-1), cy=v*(res-1);
        float rpx=radius/Sz.x*(res-1);
        int r=Mathf.CeilToInt(rpx); int icx=Mathf.RoundToInt(cx), icy=Mathf.RoundToInt(cy);
        byte val = erase? EdoLandUse.AUTO : cls;
        for(int dy=-r;dy<=r;dy++)for(int dx=-r;dx<=r;dx++){
            if(dx*dx+dy*dy>rpx*rpx)continue;
            int X=icx+dx, Y=icy+dy; if(X<0||Y<0||X>=res||Y>=res)continue;
            int idx=Y*res+X; px[idx]=new Color32(val,0,0,255);
        }
        strokeDirty=true;
    }

    bool RaycastTerrain(Ray ray, out Vector3 hit)
    {
        hit=Vector3.zero;
        if(Physics.Raycast(ray, out RaycastHit rh, 100000f)){ hit=rh.point; return true; }
        if(Mathf.Abs(ray.direction.y)>1e-4f){ float t=-(ray.origin.y-terr.transform.position.y)/ray.direction.y;
            if(t>0){ Vector3 p=ray.origin+ray.direction*t; p.y=terr.SampleHeight(p)+terr.transform.position.y; hit=p; return true; } }
        return false;
    }

    void PushUndo(){ undo.Add((Color32[])px.Clone()); undoMarkCounts.Add(marks.Count); if(undo.Count>40){ undo.RemoveAt(0); undoMarkCounts.RemoveAt(0); } }
    void UndoStroke(){
        if(undo.Count==0)return; int last=undo.Count-1;
        px=undo[last]; int mc=undoMarkCounts[last];
        undo.RemoveAt(last); undoMarkCounts.RemoveAt(last);
        if(mc>=0 && mc<marks.Count) marks.RemoveRange(mc, marks.Count-mc);   // 直近ストロークの塗り跡だけ消す(全消ししない)
        ov.SetPixels32(px); ov.Apply(); EdoLandUse.SaveOverride(ov); hasLast=false; SceneView.RepaintAll();
    }
}
