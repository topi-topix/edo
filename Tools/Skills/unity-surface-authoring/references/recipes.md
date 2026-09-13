# Recipes — runnable `execute_code` patterns

All snippets are the **body** sent to `mcp__unityMCP__execute_code` (`action:"execute"`). Remember §1
gotchas: no `using`, fully-qualified names, `UnityEngine.Object.DestroyImmediate`, no
`AssetDatabase.DeleteAsset`.

## Table of contents
- [Screenshot helper](#screenshot-helper)
- [Splatmap paint](#splatmap-paint)
- [Mesh grass detail](#mesh-grass-detail)
- [Extract roads from map](#extract-roads-from-map)
- [Georeference & verify](#georeference--verify)

---

## Screenshot helper

Eye-level and top-down. Writes under `Screenshots/` (gitignored), then open with Read.

```csharp
System.Func<Vector3,Vector3,float,string,string> shot=(pos,euler,fov,name)=>{
  var camGo=new GameObject("__cap"); var cam=camGo.AddComponent<Camera>();
  cam.transform.position=pos; cam.transform.eulerAngles=euler; cam.fieldOfView=fov;
  cam.farClipPlane=6000; cam.nearClipPlane=0.05f; cam.clearFlags=CameraClearFlags.Skybox;
  int W=1280,H=720; var rt=new RenderTexture(W,H,24); cam.targetTexture=rt; cam.Render();
  RenderTexture.active=rt; var tex=new Texture2D(W,H,TextureFormat.RGB24,false);
  tex.ReadPixels(new Rect(0,0,W,H),0,0); tex.Apply(); RenderTexture.active=null;
  System.IO.File.WriteAllBytes(Application.dataPath+"/../Screenshots/"+name+".png",tex.EncodeToPNG());
  UnityEngine.Object.DestroyImmediate(rt);UnityEngine.Object.DestroyImmediate(tex);UnityEngine.Object.DestroyImmediate(camGo);
  return name;
};
// eye-level over player:
var p=GameObject.Find("Player").transform.position;
shot(new Vector3(p.x,p.y+1.6f,p.z), new Vector3(6,90,0), 60f, "eye");
// top-down ortho: set cam.orthographic=true; cam.orthographicSize=<halfSpan>; euler=(90,0,0)
return "ok";
```

**Bank grass around a water body, gated by land-use (don't spill onto roads/town):** to grass only the
pond/moat banks, iterate the alphamap region around the `WaterBody.outline`, keep a texel only if it's
(a) outside the water polygon, (b) within a band (~70 m) of the nearest polygon edge, (c) above the
waterline and not too high above it (height gate ~28 m so far plateaus stay bare), AND (d) its land-use
class is not ROAD(1)/COMMONER(4) — query via `EdoLandUse.BuildMapClasses(out W,out H,true)` once +
`WorldToMapPixel(world,W,H,out px,out py)` per candidate (reflection, `"EdoLandUse, Assembly-CSharp-Editor"`).
Paint grass into `L_grass`(layer 1) AND write detail density in the same cells. If you already over-painted,
**reload the pristine splat from the on-disk terrain asset** (temp-import trick, `GetAlphamaps`→`SetAlphamaps`)
to undo, then repaint constrained. **Detail array orientation varies** — after `GetDetailLayer(x,y,w,h,0)`
detect it: `bool zMajor = D.GetLength(0)==regionH;` then index `D[z,x]` vs `D[x,z]` accordingly (got this
wrong → transposed grass).

**⚠️ Gate by EFFECTIVE class, not `BuildMapClasses` alone.** `EdoLandUse.BuildMapClasses` returns only the
**auto** (old-map colour) classification — the user's hand-painted `landuse_override.png` is applied ONLY
inside `Bake()` ([EdoLandUse.cs:159](Assets/Edo/Scripts/Editor/EdoLandUse.cs)). Gating grass on auto-only
put grass on blocks the user had manually marked ROAD/COMMONER (auto misread them as SAMURAI) → a whole
block got grassed. Compute the effective class yourself: `ovc = overridePx[az*res+ax].r; eff = ovc!=0 ? ovc :
SampleClassVote(autoCls, mpx,mpy)` (override PNG is at alphamap res, R=class id, 0=AUTO). Exclude ROAD(1)+
COMMONER(4) (+ dilate that mask a few texels as a buffer). If you already smeared grass over the land-use
splat, **`EdoLandUse.Bake()` repaints the whole splat correctly (auto+override) and calls RebuildGrass** —
run it to reset, THEN re-apply the effective-class-gated bank grass on top. (Reality check for this project:
the Tameike bank band is ~38% ROAD + ~56% SAMURAI — the pond is ringed by the embankment road and samurai
estates, so a correctly-gated bank fringe is necessarily thin.)

**⚠️ `GetDetailLayer` returns `[x,z]` but `GetAlphamaps` returns `[z,x]` — OPPOSITE axis order.**
This cost a long debug: painting detail density in the same loop as the grass splat but indexing the
detail array the same way as the alphamap put the density in a TRANSPOSED location (co-location with the
grass splat was ~12%, so grass "grew" nowhere near the green). Confirm the orientation from the returned
non-square dims: `GetDetailLayer(x,y,w,h,0)` on a region where `w!=h` comes back dimensioned `[w,h]`
(= `[X,Z]`), whereas `GetAlphamaps(x,y,w,h)` is `[h,w,layers]` (= `[Z,X]`). The project's proven, safe
convention (matches `EdoLandUse.RebuildGrass`): build a **square** `new int[detailWidth,detailWidth]`
indexed `dens[z,x]` (z = outer/Z loop, from `GetInterpolatedHeight`/alphamap's z), sample the grass
splat `alpha[az,ax,1]` at the co-located texel, and `SetDetailLayer(0,0,0,dens)`. Verify co-location in
memory (`dens[z,x]>0` where `alpha[z,x,1]>0.6` → should be ~100%) before trusting it. (Note the project's
`RebuildGrass` also gates on `h>-4f`, which excludes the sub-sea-level Tameike banks at ~-16 m — drop
that gate when grassing the pond.)

**⚠️ Terrain detail GRASS does NOT render in scripted off-screen `Camera.Render()` captures — only trees do.**
Spent a while thinking placed grass was broken; it wasn't. Verify grass by the DATA instead: `GetDetailLayer`
nonzero-cell count + density sum, and `terrain.drawTreesAndFoliage`/`detailObjectDensity`/`detailObjectDistance`.
The grass renders fine in the real Scene/Game view. Don't switch renderMode/scale/prototype chasing a
"missing grass" that only the screenshot is missing — confirm via density data and tell the user to look in
the viewport.

**Meadow Environment (NatureManufacture) grass as terrain detail:** the pack ships
`Grass/Prefabs Unity Terrain Grass/prefab_Terrain_grass_meadow_0N_*` built for terrain detail. Their
material uses `NatureManufacture Shaders/Grass/Advanced Grass Specular` — check `Shader.Find(...)!=null`
(URP support sub-package imported) so it isn't pink. Set `detailPrototypes[0]` `usePrototypeMesh=true`,
`prototype=<meadow grass prefab>`, `renderMode=DetailRenderMode.Grass`, `useInstancing=true`,
`healthyColor≈white` (let the material carry colour). Replacing prototype[0] keeps the painted density map.

**Tree avenue (並木) along a water/road edge:** walk the `WaterBody.outline` edges sampling ~every metre,
accumulate spacing (10–14 m); at each step the outward normal `n=perp(edgeDir)` (flip if `PointInPoly(p+n*6)`),
keep only the side you want (`n.x<0.35` = west/road side), offset `p+n*15`, seat a `TreeInstance` at
normalized `((wx-px0)/sx, GetInterpolatedHeight(u,v)/sizeY, (wz-pz0)/sz)`. Set `treeBillboardDistance=treeDistance`
(no white billboards). Sakura-summer prototypes stand in for 桐/broadleaf.

**Shooting depth/refraction shaders (water, etc.):** a plain offscreen Camera won't generate the
depth/opaque textures those shaders read, so the effect renders blank. Force them on the capture cam:
```csharp
var cd=camGo.GetComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
if(cd==null) cd=camGo.AddComponent<UnityEngine.Rendering.Universal.UniversalAdditionalCameraData>();
cd.requiresDepthOption=UnityEngine.Rendering.Universal.CameraOverrideOption.On;
cd.requiresColorOption=UnityEngine.Rendering.Universal.CameraOverrideOption.On;   // _CameraOpaqueTexture
```
(`GetUniversalAdditionalCameraData()` is an extension method — unusable in `execute_code`; use
GetComponent/AddComponent as above. Also needs Depth+Opaque Texture enabled on the URP asset.)

## Splatmap paint

Assign 4 PBR layers, then paint by slope/height/noise. `L_dirt/grass/bare/rock` are existing project
`.terrainlayer` assets.

```csharp
var terr=GameObject.Find("ModernTerrain").GetComponent<Terrain>(); var td=terr.terrainData;
float originY=terr.transform.position.y;
string[] lp={ "Assets/Edo/Terrain/layers/L_dirt.terrainlayer","Assets/Edo/Terrain/layers/L_grass.terrainlayer",
              "Assets/Edo/Terrain/layers/L_bare.terrainlayer","Assets/Edo/Terrain/layers/L_rock.terrainlayer" };
var layers=new TerrainLayer[lp.Length];
for(int i=0;i<lp.Length;i++) layers[i]=UnityEditor.AssetDatabase.LoadAssetAtPath<TerrainLayer>(lp[i]);
layers[0].tileSize=new Vector2(6,6); layers[1].tileSize=new Vector2(9,9);
layers[2].tileSize=new Vector2(14,14); layers[3].tileSize=new Vector2(10,10);
td.alphamapResolution=1024; td.terrainLayers=layers;
int res=td.alphamapResolution; var map=new float[res,res,4];
for(int y=0;y<res;y++){ float v=y/(float)(res-1);
  for(int x=0;x<res;x++){ float u=x/(float)(res-1);
    float steep=td.GetSteepness(u,v);
    float n1=Mathf.PerlinNoise(u*55f,v*55f), n2=Mathf.PerlinNoise(u*11f+100f,v*11f+100f);
    float wD=0,wG=0,wB=0,wR=0;
    if(steep>40f){ wR=1f; wB=0.35f; }
    else if(steep>20f){ float t=(steep-20f)/20f; wG=1f-0.5f*t; wR=0.15f+0.7f*t; wD=0.15f; }
    else { wD=0.65f; wB=0.20f+0.55f*n1; wG=0.45f*Mathf.SmoothStep(0.52f,0.78f,n2); wD+=0.10f*(1f-n1); }
    float s=wD+wG+wB+wR; if(s<1e-4f){wD=1;s=1;}
    map[y,x,0]=wD/s; map[y,x,1]=wG/s; map[y,x,2]=wB/s; map[y,x,3]=wR/s;
  }
}
td.SetAlphamaps(0,0,map); terr.Flush();
UnityEditor.EditorUtility.SetDirty(td); UnityEditor.AssetDatabase.SaveAssets();
return "painted";
```

Note alphamap indexing: `map[y,x,layer]`, x→terrain X (east), y→terrain Z (north);
`GetSteepness(u,v)` uses the same normalized (u=x, v=y).

## Mesh grass detail

Build a crossed-quad tuft, material, prefab, then swap the terrain detail prototype. Fixes the
"flat pasted billboard" look at oblique angles.

```csharp
// 1) crossed-quad mesh (3 quads @0/60/120, double-sided)
var verts=new System.Collections.Generic.List<Vector3>(); var uvs=new System.Collections.Generic.List<Vector2>();
var tris=new System.Collections.Generic.List<int>(); var norms=new System.Collections.Generic.List<Vector3>();
float w=0.28f,h=0.6f;
for(int q=0;q<3;q++){ float a=q*60f*Mathf.Deg2Rad; float cx=Mathf.Cos(a),sx=Mathf.Sin(a);
  System.Func<float,float,Vector3> P=(X,Y)=> new Vector3(X*cx,Y,X*sx); int b=verts.Count;
  verts.Add(P(-w,0)); verts.Add(P(w,0)); verts.Add(P(w,h)); verts.Add(P(-w,h));
  uvs.Add(new Vector2(0,0)); uvs.Add(new Vector2(1,0)); uvs.Add(new Vector2(1,1)); uvs.Add(new Vector2(0,1));
  for(int k=0;k<4;k++)norms.Add(new Vector3(0,1,0));
  tris.AddRange(new[]{b,b+1,b+2,b,b+2,b+3}); tris.AddRange(new[]{b,b+2,b+1,b,b+3,b+2}); }
var mesh=new Mesh(); mesh.name="GrassTuft"; mesh.SetVertices(verts); mesh.SetUVs(0,uvs);
mesh.SetNormals(norms); mesh.SetTriangles(tris,0); mesh.RecalculateBounds();
string dir="Assets/Edo/Terrain/details/";
UnityEditor.AssetDatabase.CreateAsset(mesh,dir+"GrassTuft.asset");
// 2) two-sided alpha-clip material
var grass=UnityEditor.AssetDatabase.LoadAssetAtPath<Texture2D>(dir+"grass_billboard.png");
var mat=new Material(Shader.Find("Universal Render Pipeline/Lit")); mat.name="GrassTuft";
mat.SetTexture("_BaseMap",grass); mat.SetFloat("_AlphaClip",1f); mat.EnableKeyword("_ALPHATEST_ON");
mat.SetFloat("_Cutoff",0.4f); mat.SetFloat("_Cull",0f); mat.SetFloat("_Smoothness",0.15f);
mat.SetColor("_BaseColor",new Color(0.72f,0.78f,0.55f,1f));
UnityEditor.AssetDatabase.CreateAsset(mat,dir+"GrassTuft.mat");
// 3) prefab
var go=new GameObject("GrassTuft"); go.AddComponent<MeshFilter>().sharedMesh=mesh;
go.AddComponent<MeshRenderer>().sharedMaterial=mat;
var prefab=UnityEditor.PrefabUtility.SaveAsPrefabAsset(go,dir+"GrassTuft.prefab");
UnityEngine.Object.DestroyImmediate(go); UnityEditor.AssetDatabase.SaveAssets();
// 4) assign prototype (density layer preserved — do NOT call SetDetailResolution)
var terr=GameObject.Find("ModernTerrain").GetComponent<Terrain>(); var td=terr.terrainData;
var dp=new DetailPrototype{ usePrototypeMesh=true, prototype=prefab, renderMode=DetailRenderMode.Grass,
  useInstancing=true, minWidth=0.7f,maxWidth=1.3f,minHeight=0.7f,maxHeight=1.4f, noiseSpread=0.5f,
  healthyColor=new Color(0.85f,0.90f,0.72f,1f), dryColor=new Color(0.80f,0.74f,0.50f,1f) };
var arr=td.detailPrototypes; if(arr.Length==0)arr=new DetailPrototype[1]; arr[0]=dp; td.detailPrototypes=arr;
terr.detailObjectDistance=180f; terr.Flush(); UnityEditor.AssetDatabase.SaveAssets();
return "grass mesh detail set";
```

To first paint density (once), size the layer then vote from the grass splat channel:
`td.SetDetailResolution(1024,16);` then build `int[dres,dres]` where density>0 only if
`grassWeight>0.3 && slope<28 && height>waterline`, and `td.SetDetailLayer(0,0,0,dens);`.

## Extract roads from map

Preview the yellow-road detector on the map first (highlight detections red), then paint.

```csharp
var bytes=System.IO.File.ReadAllBytes(Application.dataPath+"/Edo/OldMap/oldmap_center.png");
var tex=new Texture2D(2,2,TextureFormat.RGBA32,false); tex.LoadImage(bytes);
int W=tex.width,H=tex.height; var px=tex.GetPixels32();
System.Func<Color32,bool> isRoad=(c)=>{ float r=c.r/255f,g=c.g/255f,b=c.b/255f;
  return r>0.60f&&g>0.48f&&b<0.62f&&(r-b)>0.16f&&(g-b)>0.08f&&(r-g)<0.30f&&b<g+0.05f; };
var outpx=(Color32[])px.Clone(); long n=0;
for(int i=0;i<px.Length;i++) if(isRoad(px[i])){ n++; outpx[i]=new Color32(255,0,0,255); }
var o=new Texture2D(W,H,TextureFormat.RGBA32,false); o.SetPixels32(outpx); o.Apply();
System.IO.File.WriteAllBytes(Application.dataPath+"/../Screenshots/road_mask_preview.png",o.EncodeToPNG());
UnityEngine.Object.DestroyImmediate(tex);UnityEngine.Object.DestroyImmediate(o);
return $"flagged {100.0*n/px.Length:F1}%";
```

Then paint (proven). Precompute a `byte[] road` for the whole map, a **coarse 65×65 grid** of
world→map-pixel (so you call the heavy `UnityToLatLon` only ~4k times, not 1M), bilinear-interpolate
per texel, vote over a 3×3 map neighbourhood (spacing ~2px = anti-undersample + slight widen), then
write a road-aware splat. Roads = compacted light bare earth; lots lose their random bare so the road
network reads.

```csharp
var bytes=System.IO.File.ReadAllBytes(Application.dataPath+"/Edo/OldMap/oldmap_center.png");
var mtex=new Texture2D(2,2,TextureFormat.RGBA32,false); mtex.LoadImage(bytes);
int MW=mtex.width,MH=mtex.height; var mpx=mtex.GetPixels32();
var road=new byte[MW*MH];
for(int i=0;i<mpx.Length;i++){ var c=mpx[i]; float r=c.r/255f,g=c.g/255f,b=c.b/255f;
  if(r>0.60f&&g>0.48f&&b<0.62f&&(r-b)>0.16f&&(g-b)>0.08f&&(r-g)<0.30f&&b<g+0.05f) road[i]=1; }
UnityEngine.Object.DestroyImmediate(mtex);
double LON_C=139.74215,LAT_C=35.67225,HALF=3000.0,M_LAT=111132.0;
double M_LON=111320.0*System.Math.Cos(LAT_C*System.Math.PI/180.0);
var terr=GameObject.Find("ModernTerrain").GetComponent<Terrain>(); var td=terr.terrainData;
var O=terr.transform.position; var Sz=td.size; int res=td.alphamapResolution;
int Gr=65; var gX=new float[Gr,Gr]; var gY=new float[Gr,Gr];
for(int gj=0;gj<Gr;gj++){ float wz=O.z+(gj/(float)(Gr-1))*Sz.z;
  for(int gi=0;gi<Gr;gi++){ float wx=O.x+(gi/(float)(Gr-1))*Sz.x;
    double la,lo,hh; Edo.Geo.GeoReference.UnityToLatLon(new Vector3(wx,0,wz),out la,out lo,out hh);
    gX[gi,gj]=(float)(((lo-LON_C)*M_LON/(2*HALF)+0.5)*(MW-1));
    gY[gi,gj]=(float)(((la-LAT_C)*M_LAT/(2*HALF)+0.5)*(MH-1)); } }
System.Func<int,int,bool> R=(px,py)=> px>=0&&py>=0&&px<MW&&py<MH&&road[py*MW+px]==1;
var map=new float[res,res,4];
for(int y=0;y<res;y++){ float ny=y/(float)(res-1); float fy=ny*(Gr-1); int gj=Mathf.Min((int)fy,Gr-2); float ty=fy-gj; float v=y/(float)(res-1);
  for(int x=0;x<res;x++){ float nx=x/(float)(res-1); float fx=nx*(Gr-1); int gi=Mathf.Min((int)fx,Gr-2); float tx=fx-gi; float u=x/(float)(res-1);
    float mx=Mathf.Lerp(Mathf.Lerp(gX[gi,gj],gX[gi+1,gj],tx),Mathf.Lerp(gX[gi,gj+1],gX[gi+1,gj+1],tx),ty);
    float my=Mathf.Lerp(Mathf.Lerp(gY[gi,gj],gY[gi+1,gj],tx),Mathf.Lerp(gY[gi,gj+1],gY[gi+1,gj+1],tx),ty);
    int mpX=Mathf.RoundToInt(mx),mpY=Mathf.RoundToInt(my); int votes=0;
    for(int dy=-1;dy<=1;dy++)for(int dx=-1;dx<=1;dx++) if(R(mpX+dx*2,mpY+dy*2))votes++;
    bool road_=votes>=2; float steep=td.GetSteepness(u,v); float n2=Mathf.PerlinNoise(u*11f+100f,v*11f+100f);
    float wD=0,wG=0,wB=0,wR=0;
    if(road_){ wB=0.9f; wD=0.1f; }
    else if(steep>40f){ wR=1f; wD=0.2f; }
    else if(steep>20f){ float t=(steep-20f)/20f; wG=1f-0.5f*t; wR=0.15f+0.7f*t; wD=0.15f; }
    else { wD=0.8f; wG=0.5f*Mathf.SmoothStep(0.52f,0.80f,n2); }
    float s=wD+wG+wB+wR; if(s<1e-4f){wD=1;s=1;}
    map[y,x,0]=wD/s; map[y,x,1]=wG/s; map[y,x,2]=wB/s; map[y,x,3]=wR/s; } }
td.SetAlphamaps(0,0,map); terr.Flush(); UnityEditor.AssetDatabase.SaveAssets();
return "roads painted";
```

After repainting the splat, **rebuild the detail-grass density from the new grass channel**
(`alpha[ay,ax,1]`) so grass is removed from roads and matches the new lot grassiness — otherwise old
tufts still sit on the roads. Use `td.GetAlphamaps` + `td.SetDetailLayer(0,0,0,dens)` (see the grass
recipe's density note; gate on `grassWeight>0.3 && slope<28 && height>waterline`).

Gotcha: a top-down ortho verification shot washes out to blue haze if scene **fog** is on (camera is
hundreds of metres up) — set `RenderSettings.fog=false` around the capture and restore after.

The project also has a manual `Edo/Road Tracer` (spline) for hand-drawing roads over the corrected
overlay — an alternative to auto-paint.

## Georeference & verify

Map (equirectangular about geoCenter) ↔ Unity world. Constants from `edo-map` meta.json.

```csharp
double LON_C=139.74215, LAT_C=35.67225, HALF=3000.0, M_LAT=111132.0;
double M_LON=111320.0*System.Math.Cos(LAT_C*System.Math.PI/180.0);
// world -> map uv (v up = north):
double lat,lon,h; Edo.Geo.GeoReference.UnityToLatLon(worldPos,out lat,out lon,out h);
double u=(lon-LON_C)*M_LON/(2*HALF)+0.5;
double v=(lat-LAT_C)*M_LAT/(2*HALF)+0.5;   // pixel = (u*(W-1), v*(H-1))
```

Place the overlay quad's 4 corners at the geographic corners:

```csharp
double dLon=HALF/M_LON, dLat=HALF/M_LAT; float Y=48f;
System.Func<double,double,Vector3> Pt=(la,lo)=>{ var wv=Edo.Geo.GeoReference.LatLonToUnity(la,lo,25.0);
  return new Vector3(wv.x,Y,wv.z); };
var NW=Pt(LAT_C+dLat,LON_C-dLon), NE=Pt(LAT_C+dLat,LON_C+dLon),
    SE=Pt(LAT_C-dLat,LON_C+dLon), SW=Pt(LAT_C-dLat,LON_C-dLon);
// assign to the OldMapQuad mesh vertices, matched by their UV (NW=uv(0,1),NE=(1,1),SE=(1,0),SW=(0,0)).
```

Verify: for each `GeoMarker` anchor, project its world pos → (u,v) → draw a disc on a copy of the map,
zoom in, and confirm it lands on the drawn landmark. A ~660 m SE offset was the symptom of the raw
scan being placed as a plain origin-centred square instead of via these corners.

---

## Recover an unsaved terrain from its on-disk asset (undo a bad heightmap edit)

When a tool (e.g. water/moat carving) has trashed the live terrain **but you haven't saved yet**, the
`.asset` on disk is still the pre-edit terrain. Splice the pristine heights back in — no scene reload,
keeps splatmaps/details/other GameObjects untouched.

Confirm it's recoverable first: `UnityEditor.EditorUtility.IsDirty(terrainData)==True` **and**
`git diff HEAD -- <terrainData path>` is empty ⇒ edits are memory-only, disk = pristine.

```csharp
// 1) copy the on-disk asset to a temp path, import as a SEPARATE TerrainData
var src=Application.dataPath+"/Edo/Terrain/ModernTerrain.asset";
var rel="Assets/Edo/Terrain/_pristine_tmp.asset";
System.IO.File.Copy(src, Application.dataPath+"/Edo/Terrain/_pristine_tmp.asset", true);
UnityEditor.AssetDatabase.ImportAsset(rel, UnityEditor.ImportAssetOptions.ForceSynchronousImport|UnityEditor.ImportAssetOptions.ForceUpdate);
var pristine=UnityEditor.AssetDatabase.LoadAssetAtPath<TerrainData>(rel);
// 2) splice heights only (splat/detail usually identical — diff them first to be sure)
var live=Terrain.activeTerrain.terrainData; int res=live.heightmapResolution;
live.SetHeights(0,0, pristine.GetHeights(0,0,res,res));
// 3) cleanup: File.Delete + AssetDatabase.DeleteAsset are BOTH MCP-blocked → delete the temp
//    .asset + .meta with Bash `rm`, then refresh_unity.
```

Gotchas that bit here: **terrain base `transform.position.y` matters.** If a carving tool converts a
world-space level to a normalized height with `(worldY - depth)/size.y` and forgets `- terrainPosY`,
then on a terrain whose base is below 0 (e.g. `y=-35`) every dig clamps to the floor → a giant trench.
Always convert world↔normalized as `norm = (worldY - terrainPosY)/size.y`. Also: a "re-snapshot from
current terrain" restore feature (fit-to-terrain) will **overwrite the pre-dig snapshot with the
already-dug terrain** if pressed after digging — the true original is then only in the on-disk asset.

## Bulk-convert pink (Built-in Standard) materials to URP via execute_code

Pink/magenta assets in a URP project = material shader is Built-in `Standard`, which URP can't render.
Fix = run URP's official `StandardUpgrader` (maps Metallic/Smoothness/Emission/Normal + render mode
correctly; preserves textures) over the whole pack. Do it in-editor, no menu clicking needed.

Two `execute_code` gotchas learned here:
- **codedom compiler (the default when Roslyn isn't installed) runs your code as a METHOD BODY** →
  `using` directives at the top fail with "Unexpected symbol". Use fully-qualified names
  (`UnityEditor.AssetDatabase...`) instead. `roslyn` compiler was "not available" in this project.
- The upgrader lives in the URP editor asm; grab it by reflection. `StandardUpgrader` is public with a
  `ctor(string)`; the static `Upgrade(Material, MaterialUpgrader, UpgradeFlags)` is on the BASE type
  `UnityEditor.Rendering.MaterialUpgrader` (note: `.Rendering`, not `.Rendering.Universal`).

```csharp
System.Type tStd=null;
foreach (var a in System.AppDomain.CurrentDomain.GetAssemblies()){
    var t=a.GetType("UnityEditor.Rendering.Universal.StandardUpgrader"); if(t!=null){tStd=t;break;} }
var tUp=tStd.BaseType; // UnityEditor.Rendering.MaterialUpgrader
System.Reflection.MethodInfo up=null;
foreach (var mi in tUp.GetMethods(System.Reflection.BindingFlags.Public|System.Reflection.BindingFlags.Static))
    if(mi.Name=="Upgrade" && mi.GetParameters().Length==3 && mi.GetParameters()[0].ParameterType==typeof(UnityEngine.Material)){up=mi;break;}
var flags=System.Enum.ToObject(up.GetParameters()[2].ParameterType,0);      // UpgradeFlags.None
var inst=System.Activator.CreateInstance(tStd,new object[]{"Standard"});
foreach (var g in UnityEditor.AssetDatabase.FindAssets("t:Material")){
    var p=UnityEditor.AssetDatabase.GUIDToAssetPath(g);
    if(p.ToLower().IndexOf("japanese castle")<0) continue;                    // scope filter
    var m=UnityEditor.AssetDatabase.LoadAssetAtPath<UnityEngine.Material>(p);
    if(m==null||m.shader==null||m.shader.name!="Standard") continue;
    up.Invoke(null,new object[]{m,inst,flags}); UnityEditor.EditorUtility.SetDirty(m);
}
UnityEditor.AssetDatabase.SaveAssets(); UnityEditor.AssetDatabase.Refresh();
```

After: verify `m.shader.name=="Universal Render Pipeline/Lit"` and `m.GetTexture("_BaseMap")!=null`, then
off-screen render one prefab to confirm no magenta. Custom shaders (e.g. `Japanese/Foliage`) are already
pipeline-agnostic — skip them. Re-importing the asset pack reverts `.mat` files → Standard; just re-run.

## Heightmap world↔normalized conversion MUST include terrain.transform.position.y (山王北3屋敷 2026-08-12)

The Akasaka terrain sits at `tp.y = -9.94`, so `worldY = h_norm * td.size.y + tp.y` — NOT `h_norm * size.y`.
Forgetting `tp.y` in threshold masks and pad targets has a distinctive fingerprint:
- Laplacian mask cell counts come out tiny or zero ("relax cells=0" where thousands are expected) because
  the world-space threshold was compared against terrain-local heights (~10m higher here).
- Flattening pads/aprons get dug ~|tp.y| meters BELOW the intended level (a gate apron targeted at 15.0
  world became a 10 m pit at world 5.06).
`SampleHeight()+tp.y` (used everywhere for reads) hides the offset — it only bites when writing via
`GetHeights/SetHeights`. Fix: define `HtoW(h)=h*ts.y+tp.y` / `WtoH(w)=(w-tp.y)/ts.y` once and use them in
every mask test and target assignment. Always write a raw-normalized backup .bin BEFORE the first
SetHeights and sanity-check the reported cell counts against the expected area/4m² before proceeding.
Note: re-running a Stage0 that re-takes its backup would capture the ALREADY-MODIFIED terrain — re-apply
fixes via inline execute_code instead, or version the backup filename.
