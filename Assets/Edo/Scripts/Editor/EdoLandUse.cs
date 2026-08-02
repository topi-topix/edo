using System.Collections.Generic;
using UnityEngine;
using UnityEditor;
using Edo.Geo;

/// <summary>
/// 古地図の色から土地利用を分類し、地形スプラットに反映する。
/// さらに Scene ビューで手直し(上書き)できるブラシを提供する。
///
/// パイプライン:
///   ① 古地図(oldmap_center.png)を色で分類 → クラス/画素
///   ② 道・水で囲まれた区画を多数色で塗りつぶし(ブロック塗り, 文字ノイズ除去)
///   ③ 上書きマスク landuse_override.png を上塗り(あなたの手直し。再ベイクでも消えない)
///   ④ クラス→スプラット重み(+傾斜ルール)で ModernTerrain を塗る＆草密度を再生成
///
/// メニュー Edo ▸ Land Use ▸ …／ブラシ窓 Edo ▸ Land Use ▸ Brush。
/// すべて Undo 対応(地形は RegisterCompleteObjectUndo、上書きはブラシ窓の履歴)。
/// </summary>
public static class EdoLandUse
{
    // クラスID(上書きマスクの R 値 = id)。0=自動(下地を使う)
    public const byte AUTO=0, ROAD=1, WATER=2, SAMURAI=3, COMMONER=4, TEMPLE=5, FIELD=6, OTHER=7, GRASS=8;

    public const string MapPath      = "Assets/Edo/OldMap/oldmap_center.png";
    public const string OverridePath = "Assets/Edo/Terrain/landuse_override.png";
    public const string TerrainName  = "ModernTerrain";

    // 古地図オーバーレイのジオリファレンス定義(edo-map と一致)
    const double LON_C=139.74215, LAT_C=35.67225, HALF=3000.0, M_LAT=111132.0;
    static double M_LON => 111320.0*System.Math.Cos(LAT_C*System.Math.PI/180.0);

    /// <summary>ワールド座標 → 古地図の画素座標(クランプ済)。他ツール(植樹など)がクラスを引くのに使う。</summary>
    public static void WorldToMapPixel(Vector3 world, int W, int H, out int px, out int py)
    {
        double lat,lon,h; GeoReference.UnityToLatLon(world, out lat, out lon, out h);
        double u=(lon-LON_C)*M_LON/(2*HALF)+0.5, v=(lat-LAT_C)*M_LAT/(2*HALF)+0.5;
        px=Mathf.Clamp(Mathf.RoundToInt((float)(u*(W-1))),0,W-1);
        py=Mathf.Clamp(Mathf.RoundToInt((float)(v*(H-1))),0,H-1);
    }

    public static Color BrushColor(byte c) => c switch {
        ROAD=>new Color(0.9f,0.2f,0.2f), WATER=>new Color(0.2f,0.4f,0.95f),
        SAMURAI=>new Color(0.95f,0.92f,0.75f), COMMONER=>new Color(0.6f,0.6f,0.6f),
        TEMPLE=>new Color(0.9f,0.3f,0.85f), FIELD=>new Color(0.3f,0.75f,0.3f),
        GRASS=>new Color(0.45f,0.9f,0.35f),
        _=>Color.clear };
    public static string ClassName(byte c) => c switch {
        ROAD=>"道", WATER=>"水", SAMURAI=>"武家地", COMMONER=>"町人地",
        TEMPLE=>"寺社", FIELD=>"田畑", GRASS=>"草原(緑)", _=>"(自動)" };

    // ---------- 古地図の色分類 ----------
    static byte Classify(Color32 c)
    {
        float r=c.r/255f, g=c.g/255f, b=c.b/255f;
        float mx=Mathf.Max(r,Mathf.Max(g,b)), mn=Mathf.Min(r,Mathf.Min(g,b)), sat=mx-mn;
        if (b>=mx && (b-r)>0.06f && b>0.40f) return WATER;
        if (r>0.60f&&g>0.48f&&b<0.62f&&(r-b)>0.16f&&(g-b)>0.08f&&(r-g)<0.30f&&b<g+0.05f) return ROAD;
        if (r>0.50f&&(r-g)>0.13f&&(r-b)>0.13f&&Mathf.Abs(g-b)<0.18f) return TEMPLE;
        if (g>=mx&&(g-r)>0.05f&&(g-b)>0.05f) return FIELD;
        if (mx<0.42f) return OTHER;                       // 文字・罫線
        if (mx>0.80f&&sat<0.16f) return SAMURAI;          // 生成り(既定=武家地)
        if (sat<0.16f) return COMMONER;                   // 灰(既定=町人地)
        return OTHER;
    }

    /// <summary>古地図を分類し、任意でブロック塗り。map解像度の class 配列(byte)を返す。</summary>
    public static byte[] BuildMapClasses(out int W, out int H, bool blockFill)
    {
        var tex = LoadReadable(MapPath);
        W=tex.width; H=tex.height; var px=tex.GetPixels32();
        var cls=new byte[W*H];
        for (int i=0;i<px.Length;i++) cls[i]=Classify(px[i]);
        Object.DestroyImmediate(tex);
        if (blockFill) BlockFill(cls, W, H);
        return cls;
    }

    /// <summary>道・水だけを境界に、囲まれた区画を多数色(武家/町人/寺社/田畑)で塗る。
    /// 文字・罫線(OTHER)は境界にせず塗りつぶし対象に含める → 区画内の文字ノイズが消える。</summary>
    static void BlockFill(byte[] cls, int W, int H)
    {
        bool IsBarrier(byte c)=> c==ROAD||c==WATER;
        var seen=new bool[W*H];
        var stack=new Stack<int>();
        var region=new List<int>(1024);
        for (int start=0; start<cls.Length; start++)
        {
            if (seen[start] || IsBarrier(cls[start])) continue;
            region.Clear(); stack.Clear(); stack.Push(start); seen[start]=true;
            int cS=0,cC=0,cT=0,cF=0;
            while (stack.Count>0)
            {
                int p=stack.Pop(); region.Add(p);
                switch(cls[p]){ case SAMURAI:cS++;break; case COMMONER:cC++;break; case TEMPLE:cT++;break; case FIELD:cF++;break; }
                int x=p%W, y=p/W;
                if (x>0){int n=p-1; if(!seen[n]&&!IsBarrier(cls[n])){seen[n]=true;stack.Push(n);}}
                if (x<W-1){int n=p+1; if(!seen[n]&&!IsBarrier(cls[n])){seen[n]=true;stack.Push(n);}}
                if (y>0){int n=p-W; if(!seen[n]&&!IsBarrier(cls[n])){seen[n]=true;stack.Push(n);}}
                if (y<H-1){int n=p+W; if(!seen[n]&&!IsBarrier(cls[n])){seen[n]=true;stack.Push(n);}}
            }
            byte maj=COMMONER; int best=cC;
            if (cS>best){best=cS;maj=SAMURAI;} if (cT>best){best=cT;maj=TEMPLE;} if (cF>best){best=cF;maj=FIELD;}
            if (best==0) continue;
            foreach (int p in region) cls[p]=maj;
        }
    }

    // ---------- 上書きマスク(alphamap解像度) ----------
    public static Texture2D LoadOrCreateOverride(int res)
    {
        if (System.IO.File.Exists(OverridePath))
        {
            var t=new Texture2D(2,2,TextureFormat.RGBA32,false);
            t.LoadImage(System.IO.File.ReadAllBytes(OverridePath));
            if (t.width==res && t.height==res) return t;
            Object.DestroyImmediate(t);
        }
        var tex=new Texture2D(res,res,TextureFormat.RGBA32,false);
        var px=new Color32[res*res];
        for (int i=0;i<px.Length;i++) px[i]=new Color32(0,0,0,255); // R=0 → AUTO
        tex.SetPixels32(px); tex.Apply();
        return tex;
    }
    public static void SaveOverride(Texture2D tex)
    {
        System.IO.File.WriteAllBytes(OverridePath, tex.EncodeToPNG());
        AssetDatabase.ImportAsset(OverridePath);
    }

    // ---------- ベイク ----------
    [MenuItem("Edo/土地利用/ベイク（自動＋上書き）")]
    public static void Bake() { Bake(true); }

    public static void Bake(bool blockFill)
    {
        var go=GameObject.Find(TerrainName);
        if (go==null){ Debug.LogWarning("[LandUse] ModernTerrain が見つかりません。"); return; }
        var terr=go.GetComponent<Terrain>(); var td=terr.terrainData;
        var O=terr.transform.position; var Sz=td.size; int res=td.alphamapResolution;

        int MW,MH; var mapCls=BuildMapClasses(out MW,out MH,blockFill);
        var ov=LoadOrCreateOverride(res); var ovpx=ov.GetPixels32();

        // GRASS(草原)の上書きは境界をぼかして柔らかいカバレッジ(0-1)に → 縁のガタつきを解消
        var gcov=new float[res*res];
        for(int i=0;i<gcov.Length;i++) gcov[i]=(ovpx[i].r==GRASS)?1f:0f;
        for(int pass=0;pass<4;pass++){ var gsrc=(float[])gcov.Clone();
            for(int yy=1;yy<res-1;yy++)for(int xx=1;xx<res-1;xx++){ int ii=yy*res+xx;
                gcov[ii]=(gsrc[ii]*4f+gsrc[ii-1]+gsrc[ii+1]+gsrc[ii-res]+gsrc[ii+res])/8f; } }

        // 粗グリッドで world→map画素
        int G=65; var gX=new float[G,G]; var gY=new float[G,G];
        for (int gj=0;gj<G;gj++){ float wz=O.z+(gj/(float)(G-1))*Sz.z;
            for (int gi=0;gi<G;gi++){ float wx=O.x+(gi/(float)(G-1))*Sz.x;
                double la,lo,hh; GeoReference.UnityToLatLon(new Vector3(wx,0,wz),out la,out lo,out hh);
                gX[gi,gj]=(float)(((lo-LON_C)*M_LON/(2*HALF)+0.5)*(MW-1));
                gY[gi,gj]=(float)(((la-LAT_C)*M_LAT/(2*HALF)+0.5)*(MH-1)); } }

        Undo.RegisterCompleteObjectUndo(td,"Bake Land Use");
        var map=new float[res,res,4];
        for (int y=0;y<res;y++){ float ny=y/(float)(res-1); float fy=ny*(G-1); int gj=Mathf.Min((int)fy,G-2); float ty=fy-gj; float v=y/(float)(res-1);
            for (int x=0;x<res;x++){ float nx=x/(float)(res-1); float fx=nx*(G-1); int gi=Mathf.Min((int)fx,G-2); float tx=fx-gi; float u=x/(float)(res-1);
                float mx=Mathf.Lerp(Mathf.Lerp(gX[gi,gj],gX[gi+1,gj],tx),Mathf.Lerp(gX[gi,gj+1],gX[gi+1,gj+1],tx),ty);
                float my=Mathf.Lerp(Mathf.Lerp(gY[gi,gj],gY[gi+1,gj],tx),Mathf.Lerp(gY[gi,gj+1],gY[gi+1,gj+1],tx),ty);
                // 道は近傍投票で細線補強
                byte cl=SampleClassVote(mapCls,MW,MH,mx,my);
                byte ovc=ovpx[y*res+x].r;           // 上書き(0=自動)
                bool over=ovc!=AUTO && ovc!=GRASS;  // GRASS はぼかしカバレッジで別扱い
                if (over) cl=ovc;

                float steep=td.GetSteepness(u,v);
                float n2=Mathf.PerlinNoise(u*11f+100f,v*11f+100f);
                float nMacro=Mathf.PerlinNoise(u*3.5f+40f,v*3.5f+40f);   // 低周波=大きな斑(反復崩し)
                float wD,wG,wB,wR; ClassToSplat(cl,steep,n2,nMacro,over,out wD,out wG,out wB,out wR);
                float s=wD+wG+wB+wR; if(s<1e-4f){wD=1;s=1;} wD/=s; wG/=s; wB/=s; wR/=s;

                // 草原: 柔らかいカバレッジで草へブレンド(縁が滑らかにフェード)
                float gc=gcov[y*res+x];
                if(gc>0.001f){
                    float ngG=0.96f+0.03f*n2, ngD=0.04f;   // 草原レシピ(少しノイズ)
                    wD=Mathf.Lerp(wD,ngD,gc); wG=Mathf.Lerp(wG,ngG,gc); wB=Mathf.Lerp(wB,0f,gc); wR=Mathf.Lerp(wR,0f,gc);
                    float s2=wD+wG+wB+wR; if(s2<1e-4f)s2=1; wD/=s2; wG/=s2; wB/=s2; wR/=s2;
                }
                map[y,x,0]=wD; map[y,x,1]=wG; map[y,x,2]=wB; map[y,x,3]=wR;
            } }
        td.SetAlphamaps(0,0,map);
        Object.DestroyImmediate(ov);
        RebuildGrass(terr,td);
        terr.Flush(); EditorUtility.SetDirty(td); AssetDatabase.SaveAssets();
        Debug.Log($"[LandUse] Bake 完了 (blockFill={blockFill}, res={res})");
    }

    static byte SampleClassVote(byte[] cls,int W,int H,float mx,float my)
    {
        int px=Mathf.Clamp(Mathf.RoundToInt(mx),0,W-1), py=Mathf.Clamp(Mathf.RoundToInt(my),0,H-1);
        int road=0;
        for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++){
            int sx=Mathf.Clamp(px+dx*2,0,W-1), sy=Mathf.Clamp(py+dy*2,0,H-1);
            if(cls[sy*W+sx]==ROAD)road++; }
        if(road>=2) return ROAD;
        return cls[py*W+px];
    }

    // クラス+傾斜 → スプラット重み(0=dirt,1=grass,2=bare,3=rock)。
    // overridden=手描き上書き。上書きされた所は塗ったクラスを尊重し、傾斜による草化はしない
    // (自動分類の所だけ土手を草がちにする)。崖(超急斜面)だけは岩。
    static void ClassToSplat(byte c,float steep,float n2,float nMacro,bool overridden,out float wD,out float wG,out float wB,out float wR)
    {
        wD=wG=wB=wR=0;
        // 建物地面は 2種の土(dirt#9 と bare/earth#7)を低周波ノイズで混ぜ、タイル反復のマダラを崩す。
        float e=Mathf.SmoothStep(0.38f,0.62f,nMacro);   // 0=dirt寄り, 1=earth寄り(大きな斑)
        // クラス別の基本地面(江戸=密集市街。地面主体は建物の締まった土、緑は庭木/杜/田畑/土手)
        switch(c){
            case ROAD:     wB=0.92f; wD=0.08f; break;                                       // 街道=砂
            case WATER:    wR=1f; break;                                                    // お堀=泥(層3=L_moat)。land-useで判定
            // 町人地=濃い踏み固め土(dirt主体)。低周波でbareを15〜40%だけ混ぜて反復崩し(黒マダラは出さない)。
            case COMMONER: { float b=0.95f; float bf=0.15f+0.25f*e; wD=b*(1f-bf); wB=b*bf; wG=0.05f*n2; break; }
            // 武家地=淡い土(bare寄り)＋庭木の緑。町人地の濃い土と対比。
            case SAMURAI:  { float b=0.70f; float bf=0.58f+0.18f*e; wD=b*(1f-bf); wB=b*bf; wG=0.34f*Mathf.SmoothStep(0.45f,0.85f,n2); break; }
            case TEMPLE:   { float b=0.60f; wD=b*(1f-e); wB=b*e; wG=0.40f*Mathf.SmoothStep(0.42f,0.82f,n2); break; } // 寺社
            case FIELD:    wG=0.92f; wD=0.08f; break;                                        // 田畑=草
            case GRASS:    wG=0.96f; wD=0.04f; break;                                        // 草原=緑草(手描き)
            default:       { float b=0.88f; wD=b*(1f-e); wB=b*e; wG=0.12f; break; }           // 未分類=土
        }
        // 傾斜の反映(修飾)。自動分類の土手だけ草を足す。手描きは尊重して足さない。
        if(!overridden && steep>20f){
            float t=Mathf.Clamp01((steep-20f)/20f);
            wG += t*0.6f;                                   // 自動の土手=草がち(基本地面は残す)
        }
        // 崖=淡い土(bare)。※旧rock枠(層3)はお堀の泥に転用したので岩(wR)は使わない。
        float cliffStart = overridden ? 47f : 40f;
        if(steep>cliffStart){
            float k=Mathf.Clamp01((steep-cliffStart)/8f);
            wD*=(1f-k); wG*=(1f-k); wB += k*1.6f;
        }
    }

    // GLSL版smoothstep(値を[e0,e1]→[0,1]に伸長)。UnityのMathf.SmoothStep(a,b,t)はa→b補間で別物なので自前。
    static float GrassSS(float e0,float e1,float x){ float t=Mathf.Clamp01((x-e0)/(e1-e0)); return t*t*(3f-2f*t); }
    // 縁を軽く崩すノイズ(単一オクターブ)。UnityのMathf.SmoothStep(a,b,t)はa→b補間で別物なのでGrassSSで伸長。
    static float GrassBig(float wx,float wz){
        return GrassSS(0.36f,0.64f, Mathf.PerlinNoise(wx*0.05f+5.3f, wz*0.05f+9.1f));
    }

    // 草原(緑)の芝ウェイトから草ディテールを再生成。二値マスクを軽くぼかし、閾値を弱いノイズで揺らして
    // 直線的な境界を少しだけ崩す(道への漏れは数%に抑制)。層0=密(細葉GrassLowA)、層1=疎らな広葉(GrassLowB)。
    // 水部分は芝ウェイトが低いので自然に除外される。
    static void RebuildGrass(Terrain terr, TerrainData td)
    {
        if (td.detailPrototypes.Length==0) return;
        Vector3 tp=terr.transform.position;
        int ares=td.alphamapResolution; var alpha=td.GetAlphamaps(0,0,ares,ares);
        // 芝ゾーンの二値マスク + 傾斜(alphamap解像度で前計算)
        var mask=new float[ares*ares]; var steepA=new float[ares*ares];
        for(int y=0;y<ares;y++)for(int x=0;x<ares;x++){ int idx=y*ares+x;
            mask[idx]= alpha[y,x,1]>=0.35f ? 1f : 0f;
            steepA[idx]=td.GetSteepness((x+0.5f)/ares,(y+0.5f)/ares); }
        // マスクを分離ボックスぼかし(半径R=1≒数m) → 縁を短いランプにする(漏れを最小化)
        int R=1; var tmp=new float[ares*ares]; var blur=new float[ares*ares];
        for(int y=0;y<ares;y++){ float acc=0; for(int x=-R;x<=R;x++)acc+=mask[y*ares+Mathf.Clamp(x,0,ares-1)];
            for(int x=0;x<ares;x++){ tmp[y*ares+x]=acc/(2*R+1); acc+=mask[y*ares+Mathf.Clamp(x+R+1,0,ares-1)]-mask[y*ares+Mathf.Clamp(x-R,0,ares-1)]; } }
        for(int x=0;x<ares;x++){ float acc=0; for(int y=-R;y<=R;y++)acc+=tmp[Mathf.Clamp(y,0,ares-1)*ares+x];
            for(int y=0;y<ares;y++){ blur[y*ares+x]=acc/(2*R+1); acc+=tmp[Mathf.Clamp(y+R+1,0,ares-1)*ares+x]-tmp[Mathf.Clamp(y-R,0,ares-1)*ares+x]; } }
        System.Func<float,float,float> sampleB=(wxf,wzf)=>{
            float fx=(wxf-tp.x)/td.size.x*ares-0.5f, fy=(wzf-tp.z)/td.size.z*ares-0.5f;
            int x0=Mathf.Clamp((int)Mathf.Floor(fx),0,ares-1), y0=Mathf.Clamp((int)Mathf.Floor(fy),0,ares-1);
            int x1=Mathf.Min(x0+1,ares-1), y1=Mathf.Min(y0+1,ares-1);
            float tx=Mathf.Clamp01(fx-x0), ty=Mathf.Clamp01(fy-y0);
            return Mathf.Lerp(Mathf.Lerp(blur[y0*ares+x0],blur[y0*ares+x1],tx),Mathf.Lerp(blur[y1*ares+x0],blur[y1*ares+x1],tx),ty); };
        int dres=td.detailWidth;
        var dA=new int[dres,dres];
        bool hasB=td.detailPrototypes.Length>1; var dB=hasB?new int[dres,dres]:null;
        float cell=td.size.x/dres;
        for(int dy=0;dy<dres;dy++){ float wz=tp.z+(dy+0.5f)*cell; int ay=Mathf.Clamp((int)((dy+0.5f)/dres*ares),0,ares-1);
            for(int dx=0;dx<dres;dx++){ float wx=tp.x+(dx+0.5f)*cell; int ax=Mathf.Clamp((int)((dx+0.5f)/dres*ares),0,ares-1);
                if(steepA[ay*ares+ax]>30f)continue;
                float cover=sampleB(wx, wz);                                   // ワープなし(冗長なので廃止)
                if(cover<Mathf.Lerp(0.50f,0.90f, GrassBig(wx,wz))) continue;   // 厳しめ閾値＋軽いノイズ(道漏れ<1%)
                float patch=Mathf.PerlinNoise(wx*0.05f,wz*0.05f);
                int d=Mathf.Min(16,(int)Mathf.Lerp(12f,16f,patch)); if(d<10)d=10;
                dA[dy,dx]=d;
                if(hasB){ float pB=Mathf.PerlinNoise(wx*0.03f+77f,wz*0.03f+54f), jit=Mathf.PerlinNoise(wx*1.7f,wz*1.7f);
                    if(cover>0.95f && pB>0.72f && jit>0.6f) dB[dy,dx]=1; }
            } }
        td.SetDetailLayer(0,0,0,dA);
        if(hasB) td.SetDetailLayer(0,0,1,dB);
    }

    static Texture2D LoadReadable(string assetPath)
    {
        var abs=System.IO.Path.Combine(System.IO.Directory.GetCurrentDirectory(), assetPath);
        var t=new Texture2D(2,2,TextureFormat.RGBA32,false);
        t.LoadImage(System.IO.File.ReadAllBytes(abs));
        return t;
    }
}
