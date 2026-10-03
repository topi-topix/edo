using System.IO;
using System.Linq;
using NUnit.Framework;

/// <summary>部材の札の関門(硬い・EDO-0491)。Unity の Test Runner(EditMode)で回す。
/// ⭐ 札と実メッシュの食い違い・札の欠けを、建てる前に捕まえる。→ `docs/oki-kata.md` §8</summary>
public class EdoPartSpecTests
{
    [Test]
    public void 門の語はすべて札を持つ()
    {
        EdoPartSpec.Reload();
        var kinds = EdoPartSpec.GateKinds();
        Assert.IsNotEmpty(kinds, "gate_kinds.json が読めない");
        var missing = kinds.Where(k => !File.Exists(EdoAssets.PartSpecs.Dir + k.spec + ".json")).Select(k => k.kind).ToList();
        Assert.IsEmpty(missing, "札の無い門の語: " + string.Join(", ", missing.ToArray()));
    }

    [Test]
    public void 門の語の札は類型ビルダーの部材と同じ資産を指す()
    {
        EdoPartSpec.Reload();
        var bad = EdoPartSpec.GateKinds()
            .Where(k => { var s = EdoPartSpec.Get(EdoTypologyBuilder.GatePathOf(k.kind)); return s == null || Path.GetFileNameWithoutExtension(s.prefab) != k.spec; })
            .Select(k => k.kind + " → " + EdoTypologyBuilder.GatePathOf(k.kind)).ToList();
        Assert.IsEmpty(bad, "類型ビルダーの門の部材に札が当たらない: " + string.Join(" / ", bad.ToArray()));
    }

    [Test]
    public void 札は実メッシュと食い違わない()
    {
        var r = EdoPartSpec.VerifyAll();
        Assert.IsTrue(r.Contains("⭕ 全部通った"), r);
    }
}
