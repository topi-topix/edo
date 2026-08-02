using System.Collections.Generic;
using UnityEngine;

namespace Edo
{
    /// <summary>
    /// 江戸の寸法体系(京間 1間=1.818m)で切妻・平入りの町屋を実寸生成するモジュール。
    /// 間口・奥行・軒高・棟上がり・軒の出を「間」単位で指定。棟は間口方向(X)＝通りと平行＝平入り。
    /// 屋根は壁より軒(overhang)ぶん外へ張り出し、軒先は勾配を延長して下がる。
    /// Submesh 0 = 壁＋妻(body), Submesh 1 = 屋根(roof)。
    /// </summary>
    [ExecuteAlways]
    [RequireComponent(typeof(MeshFilter), typeof(MeshRenderer))]
    public class MachiyaBuilder : MonoBehaviour
    {
        public const float Ken = 1.818f; // 1間(京間) = 1.818 m

        [Header("寸法（間）")]
        public float frontageKen     = 3f;   // 間口(X)
        public float depthKen        = 5f;   // 奥行(Z)
        public float eaveKen         = 2f;   // 軒高
        public float roofRiseKen     = 1.5f; // 棟の高さ(軒からの上がり)
        public float eaveOverhangKen = 0.5f; // 軒の出(壁からの張り出し)

        void OnEnable()   { Rebuild(); }
        void OnValidate() { if (isActiveAndEnabled) Rebuild(); }

        public void Rebuild()
        {
            float hw = frontageKen * Ken * 0.5f; // 間口の半分
            float hd = depthKen    * Ken * 0.5f; // 奥行の半分
            float h  = eaveKen     * Ken;        // 軒高
            float r  = roofRiseKen * Ken;        // 棟上がり
            float o  = eaveOverhangKen * Ken;    // 軒の出

            float ex = hw + o;                   // 屋根の間口方向 半分(破風の出)
            float ez = hd + o;                   // 屋根の軒先 半分
            float ey = h - (r / hd) * o;         // 軒先の高さ(勾配を延長して下がる)

            // 壁(足元中央=原点, Y上)
            Vector3 A0 = new Vector3(-hw, 0, -hd), A1 = new Vector3(hw, 0, -hd);
            Vector3 A2 = new Vector3(hw, 0,  hd), A3 = new Vector3(-hw, 0,  hd);
            Vector3 B0 = new Vector3(-hw, h, -hd), B1 = new Vector3(hw, h, -hd);
            Vector3 B2 = new Vector3(hw, h,  hd), B3 = new Vector3(-hw, h,  hd);
            // 妻の頂点(壁の直上=棟高)
            Vector3 Ga = new Vector3(-hw, h + r, 0), Gb = new Vector3(hw, h + r, 0);
            // 屋根(間口方向・軒先方向へ張り出し)
            Vector3 RR0 = new Vector3(-ex, h + r, 0), RR1 = new Vector3(ex, h + r, 0);
            Vector3 P0 = new Vector3(-ex, ey, -ez), P1 = new Vector3(ex, ey, -ez);
            Vector3 P2 = new Vector3(ex, ey,  ez), P3 = new Vector3(-ex, ey,  ez);

            var verts = new List<Vector3>();
            var body  = new List<int>();
            var roof  = new List<int>();

            void Quad(List<int> s, Vector3 a, Vector3 b, Vector3 c, Vector3 d)
            {
                int i = verts.Count;
                verts.Add(a); verts.Add(b); verts.Add(c); verts.Add(d);
                s.Add(i); s.Add(i + 1); s.Add(i + 2);
                s.Add(i); s.Add(i + 2); s.Add(i + 3);
            }
            void Tri(List<int> s, Vector3 a, Vector3 b, Vector3 c)
            {
                int i = verts.Count;
                verts.Add(a); verts.Add(b); verts.Add(c);
                s.Add(i); s.Add(i + 1); s.Add(i + 2);
            }

            // body
            Quad(body, A1, A0, B0, B1); // 前壁(-Z 通り側)
            Quad(body, A3, A2, B2, B3); // 後壁(+Z)
            Quad(body, A0, A3, B3, B0); // 左壁(-X)
            Quad(body, A2, A1, B1, B2); // 右壁(+X)
            Tri (body, B0, B3, Ga);     // 左妻
            Tri (body, B2, B1, Gb);     // 右妻

            // roof（軒の出ぶん外へ張り出す）
            Quad(roof, RR0, RR1, P1, P0); // 前流れ
            Quad(roof, RR1, RR0, P3, P2); // 後流れ

            var mesh = new Mesh { name = "Machiya" };
            mesh.SetVertices(verts);
            mesh.subMeshCount = 2;
            mesh.SetTriangles(body, 0);
            mesh.SetTriangles(roof, 1);
            mesh.RecalculateNormals();
            mesh.RecalculateBounds();

            GetComponent<MeshFilter>().sharedMesh = mesh;
        }
    }
}
