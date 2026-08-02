using System.Collections.Generic;
using System.Linq;
using UnityEngine;
using UnityEditor;

/// <summary>
/// 土地利用ゾーンに応じて樹木を地形に植える。江戸の緑の主役は木立。
/// 樹木は Japanese Garden 2 Free (Waldemarst) の SpeedTree を使う:
///   松(クロマツ) = 武家地・寺社の主木 / 桜 = アクセント(夏=緑, 春=花) / 竹 = 寺社の藪。
///   寺社=密, 武家地=中, 町人地=疎, 道/水/田畑=無し。傾斜・水位で除外。
/// SpeedTree なのでビルボード LOD 内蔵 = 遠景も正しく描画される。
///
/// メニュー Edo ▸ Land Use ▸ Plant Trees / Clear Trees。
/// ※ パックのマテリアルは事前に URP へシェーダー変換済みであること(SpeedTree8→URP)。
/// </summary>
public static class EdoTrees
{
    const string PackTrees = "Assets/Waldemarst/FreeJapaneseGarden/Prefabs/Trees";

    static List<GameObject> Load(string sub, string mustContain)
    {
        var res=new List<GameObject>();
        foreach(var g in AssetDatabase.FindAssets("t:Prefab", new[]{PackTrees+"/"+sub})){
            var p=AssetDatabase.GUIDToAssetPath(g);
            if(!p.Contains(mustContain)) continue;
            var go=AssetDatabase.LoadAssetAtPath<GameObject>(p);
            if(go!=null) res.Add(go);
        }
        return res;
    }

    [MenuItem("Edo/土地利用/植林")]
    public static void Plant()
    {
        var go=GameObject.Find(EdoLandUse.TerrainName);
        if(go==null){ Debug.LogWarning("[Trees] ModernTerrain が見つかりません。"); return; }
        var terr=go.GetComponent<Terrain>(); var td=terr.terrainData;
        var O=terr.transform.position; var Sz=td.size;

        // --- 樹種プレハブ ---
        var pine  = Load("BlackPine","_Green_");
        var sakG  = Load("Sakura","_Summer_");   // 夏=緑葉
        var sakB  = Load("Sakura","_Spring_");   // 春=花
        var bamboo= Load("Bamboo","_Green_");
        if(pine.Count==0 && sakG.Count==0){ Debug.LogWarning("[Trees] パックの樹木プレハブが見つかりません。"); return; }

        var protos=new List<GameObject>();
        int pi=protos.Count; protos.AddRange(pine);   int piEnd=protos.Count;
        int gi=protos.Count; protos.AddRange(sakG);   int giEnd=protos.Count;
        int bi=protos.Count; protos.AddRange(sakB);   int biEnd=protos.Count;
        int mi=protos.Count; protos.AddRange(bamboo); int miEnd=protos.Count;
        td.treePrototypes = protos.Select(p=>new TreePrototype{prefab=p}).ToArray();

        int MW,MH; var cls=EdoLandUse.BuildMapClasses(out MW,out MH,true);
        Undo.RegisterCompleteObjectUndo(td,"Plant Trees");
        var rnd=new System.Random(20250718);
        var inst=new List<TreeInstance>(20000);

        System.Func<int,int,int> pick=(a,b)=> (b>a)? a+rnd.Next(b-a) : -1; // ランダムなプロトタイプ番号
        int samples=90000;
        for(int i=0;i<samples;i++)
        {
            float nx=(float)rnd.NextDouble(), nz=(float)rnd.NextDouble();
            float steep=td.GetSteepness(nx,nz); if(steep>26f) continue;
            float h=td.GetInterpolatedHeight(nx,nz)+O.y; if(h< -3f) continue;
            float wx=O.x+nx*Sz.x, wz=O.z+nz*Sz.z;
            int px,py; EdoLandUse.WorldToMapPixel(new Vector3(wx,0,wz),MW,MH,out px,out py);
            byte c=cls[py*MW+px];

            float prob = c switch { EdoLandUse.TEMPLE=>0.85f, EdoLandUse.SAMURAI=>0.40f, EdoLandUse.COMMONER=>0.02f, _=>0f };
            if(prob<=0f || rnd.NextDouble()>prob) continue;

            // 樹種を土地利用で選ぶ
            int proto;
            double r=rnd.NextDouble();
            if(c==EdoLandUse.TEMPLE)      proto = r<0.40?pick(pi,piEnd): r<0.62?pick(gi,giEnd): r<0.78?pick(bi,biEnd): pick(mi,miEnd);
            else if(c==EdoLandUse.SAMURAI)proto = r<0.62?pick(pi,piEnd): r<0.88?pick(gi,giEnd): pick(bi,biEnd);
            else                          proto = pick(pi,piEnd); // 町人地=松のみ疎ら
            if(proto<0) proto=pick(pi,piEnd);
            if(proto<0) continue;

            float s=0.8f+(float)rnd.NextDouble()*0.5f;
            inst.Add(new TreeInstance{
                prototypeIndex=proto,
                position=new Vector3(nx,(h-O.y)/Sz.y,nz),
                widthScale=s*(0.92f+(float)rnd.NextDouble()*0.16f),
                heightScale=s,
                rotation=(float)(rnd.NextDouble()*6.283),
                color=Color.white, lightmapColor=Color.white
            });
        }
        td.SetTreeInstances(inst.ToArray(), true);
        // SpeedTree のビルボードは URP で白飛びするため無効化(=描画距離と同値)。全て3Dメッシュ描画。
        terr.treeDistance=1000f; terr.treeBillboardDistance=1000f; terr.treeCrossFadeLength=0f;
        terr.Flush(); EditorUtility.SetDirty(td); AssetDatabase.SaveAssets();
        Debug.Log($"[Trees] 植樹 {inst.Count} 本 (松{pine.Count}/桜夏{sakG.Count}/桜春{sakB.Count}/竹{bamboo.Count}種)。");
    }

    [MenuItem("Edo/土地利用/植林を消す")]
    public static void Clear()
    {
        var go=GameObject.Find(EdoLandUse.TerrainName); if(go==null)return;
        var td=go.GetComponent<Terrain>().terrainData;
        Undo.RegisterCompleteObjectUndo(td,"Clear Trees");
        td.SetTreeInstances(new TreeInstance[0], true);
        EditorUtility.SetDirty(td); AssetDatabase.SaveAssets();
        Debug.Log("[Trees] 全伐採。");
    }
}
