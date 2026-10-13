---
name: r129-grade-seroji-hakiguchi-chain-s3
description: 岡部 第129巡 ── GradeQA は背の路地の切り(S2b)を知らず東で 3m の超過・張り出し付きの吐き口 AH_Ago は敷き石を線の外 0.40 へ延ばす・S1 を流したら S3 も流さないと附属屋の均しが消えて浮く・突き合わせは留め柱 TomeBashira_<run> を知らなかった
metadata:
  type: project
---
2026-10-13 EDO-0502 第129巡。

1. **GradeQA の 13,000 升の大半は東の帯(x −408〜−384)で地形が設計面より 2〜4m 低い** = 背の路地の床。算出物 graded は長屋の実メッシュを知らないので路地を持たず、
   S2b が SeRojiPlanOf → CutAlongBack で切る。⇒ GradeQA に SeRojiPlan.At の枠(超過に数えず別に刷る)を足した。他の枠(ramps・pads・benches)と同じ型。
2. **吐き口 Doi_Mizo_AH_Ago_D* は口の敷き石を板の外の縁 +0.40 まで延ばしてある**(build_doi_haisui.py ago_A haki)── 指図「敷き石の外の面は区画の線を越えない【硬】」を割る。
   ⇒ EdoBuild.MizoStoneXMax(石の材だけの +X)で版を検め、線を越える版は張り出しの無い AH へ替える(PlaceMizoSections)。部材の側で直すなら敷き石を xc で止める。
3. **第128巡の流しは S1→S2→S2b→S3d で S3 を飛ばした** ⇒ S1 が地面を graded へ戻し、附属屋(米蔵・薪蔵 padGroup)の LevelPad が消えて薪蔵が +0.016 浮いた。
   ⇒ S1 から流す巡は RunAll の順(S1→S2→S2b→S3→S3d)。S4・S5 は地形を書かない。
4. 突き合わせ(EdoSashizuExport の外周)は runs[].tomeBashira の柱を名で知らず「孤児の囲い」── names に TomeBashira_<run> を足した。
5. D_N40_Mae の頭の駒が P40 で辺39 の線の外 0.007(頭の探しは断面3点で石の面取りを見ない)⇒ PullAlongInside に mats を足し、石だけで下流へ引く。
6. 段の棟止め(TomeA/B)の足の浮き 0.013 は台の端の石の面取り。棟止めを 0.02 埋めると笠が隣と 0.02 ずれるので止めた。0.9/0.65 は段の面の上の頂点一つ(下の段の棟止めが閉じる)。
7. 普請検査の execute_code は MCP の log が回ると消える ── unity_mcp_server.log.1/.2 も舐める(scratchpad r129/qa に抜いた)。
8. **流しの最中に .cs を保存すると、流しの末尾の書き戻し(AssetDatabase の保存)がコンパイルを起こし、domain reload で execute_code が途中で消える**
   (第129巡: 書き戻しとシーンの保存は済んだが、その後の段ごとの写しと帰属の計測が書かれなかった)。⇒ 流しの間は .cs を触らない・計測は書き戻しより前に。
9. FillUnderFoot を水平の棟へ使うと、足を「半径 0.45 の内の最下点」で判じるので妻の壁の上端を足と読み 7.85m 盛った ⇒ globalBand(最下点から 0.05)と「足の底 −0.30 より低い節点は触らない」。
**How to apply:** 外周を S1 から流す巡は S3 を入れる。GradeQA の大きな超過は先に「どの Stage が書いたか」を段ごとの地形の写しで割る(r129/chain_a.cs の型)。
関連 [[okabe-perimeter-rerun-order-and-neribei-measure]] [[qa-code-in-mcp-log]] [[graded-bin-stale-after-sashizu-commit]]
