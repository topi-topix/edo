---
name: r157-back-koshi-and-swap-after-3d
description: 岡部 第157巡 — 棟の背の野面石の腰は PlaceUnderWallInner を背の壁の外面+x で呼ぶだけ(RunBackKoshi・S3d)・倍率は IG_<run>_ の駒の localScale・S2b が 13 分に縮み S3d 6.6 分・一続きの後にスワップが 4.7→13.8GB
metadata:
  type: project
---
2026-10-17 EDO-0502 第157巡(S1→S2→S2b→S3→S3d を一続き・計約 25 分)。

1. **背の腰の型 = 内向きの石垣と同じ器**。EdoBuild.PlaceUnderWallInner の「区画の線から wallInnerIn に天端の前の縁・法は内」は、
   wallInnerIn = 背の壁の外面(FaceOut の背)+ backFace の x と読めばそのまま背の腰になる(新しい置き方は不要)。区間は欄の「s a〜b の背は」か
   EdoBuild.DropRanges(座 − 背の面の x+0.25 外の地表 ≥ d)。駒は Ishigaki の群の IGB_ ⇒ 後の RunBackBands の under に入り帯が触らない。
2. **倍率は scene の IG_<run>_ の駒の localScale.x**(一続きで揃えた値が載っている)── 静的な _kidanC は domain reload で消えるので S3d 単独でも引ける所から取る。
3. 指図の欄が要る版の名を変える: 部材方が焼いた Neribei_Saka_D0882_NK を、この巡の S2 は Neribei_Saka_D0882_T10_NK と呼んだ(版の厚みの接尾)。
   届いた駒の名と S2 の「駒が無い」の名を並べてから待ちを書く。
4. 長い一続きの後にスワップが跳ねる(S2b 後 4.7GB → S3d と QA の後 13.8GB)。写真・追加の測りは次の窓へ回す。
5. 着手前の heightmap の退避を忘れた(S1 は bin からの全面の造成で冪等だが、差分の報告が出せない)⇒ 一続きの頭に hmc_pre を採る型(r154 chain)を使う。

**How to apply:** backFace の欄が他の棟に来たら RunBackKoshi が拾う(Runs の Nagaya で back+backFace の両方)。ログの「背の腰」行の見付・駒数を見る。
関連 [[r156-heiline-continuation-and-inner-wall]] [[r155-off-heiline-dobei-sinks-and-unread-fields]] [[machine-memory-is-the-unity-bottleneck]]
