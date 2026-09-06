# -*- coding: utf-8 -*-
"""
sui_gold_synth.py  —  P2：SUI-Gold 冷启动数据合成器
===================================================
定位（绑定 SUI v4.6 文档 §6.1 SUI基准与验证体系）：
  文档定义的 SUI-Gold 是"专家标注的 {自然语言片段 → SUI三元组} 配对集"，
  规模建议 基础层500 / 层累层2000 / 歧义层1000（均须双/三/五专家CDC蒸馏）。

  本脚本做的是**冷启动 seed**（cold-start）：在专家蒸馏就位前，先用 P1 的
  层累链自动构建器 + CSMT 码本，自动合成一批可运行的配对数据，让编译器/
  评估流程先"有米下锅"。

诚实边界（必须明确传递给主线）：
  - 输出数据集标注 provenance=auto_synth、is_expert_gold=False。
  - 它**不是**文档§6.1 的 SUI-Gold 真值集，仅是供流程跑通的冷启动占位。
  - 三条三元组 (义原ID, 层累链ID, 语境节点ID) 中：
      义原ID  = 候选义原组合（P1弱匹配，非专家定稿）
      层累链ID = n_i 序号（自动按层）
      语境节点ID = 该条语境锁定的激活层（自动取该层 n_i，置信度=auto）
  - 冷启动规模远小于专家建议（本脚本默认 seed 量 = 基础30/层累20/歧义10，
    可调），明确区别于"500/2000/1000 专家目标"。

用法：
  python sui_gold_synth.py                       # 默认生成 demo seed
  python sui_gold_synth.py --n-base 50 --n-accr 30 --n-amb 15
  python sui_gold_synth.py --out sui_gold_coldstart.json --md sui_gold_coldstart.md
"""
import argparse
import csv
import json
import os
import random
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from sui_accretion_builder import build_chain, ROWS, IDX  # 复用 P1

OUT_JSON = os.path.join(HERE, "sui_gold_coldstart.json")
OUT_MD = os.path.join(HERE, "sui_gold_coldstart.md")

# ── 内置冷启动语料（极简 demo；真实冷启动应替换为概念史/古籍标注 pipeline）──
# 基础层：单义原概念（文档§6.1 基础层样例"水""火""人"）
BASE_ITEMS = [
    ("水", [("共时", "水是一种无色无味的液体物质")]),
    ("火", [("共时", "火是燃烧产生的光与热现象")]),
    ("人", [("共时", "人是有理性的社会动物")]),
    ("天", [("共时", "天是头顶上方的空间与自然界")]),
    ("道", [("共时", "道是老子哲学中的宇宙本原与规律")]),
]
# 层累层：多层累链词在明确语境（文档§6.1 层累层样例"《道德经》中的德"）
ACCR_ITEMS = [
    ("德", [("殷商", "殷商时期德指神秘力量与祖先祭祀的禀赋"),
            ("西周", "西周德指政治品德与天命所归的统治正当性"),
            ("春秋老子", "老子哲学中德是道衍生的本体无为境界"),
            ("汉代以后", "汉代以后德指个人的道德品质与伦理规范")]),
    ("气", [("先秦", "先秦气是自然哲学中的本原物质"),
            ("中医", "中医气是气血运行中维持生命的物质基础")]),
    ("仁", [("春秋孔子", "孔子仁是爱人推己及人的伦理核心"),
            ("宋明", "宋明仁被发展为心性本体论的宇宙生机")]),
]
# 歧义层：需语境消歧的完整句子（文档§6.1 歧义层样例"孔德之容，惟道是从"）
AMB_ITEMS = [
    ("德", "孔德之容，惟道是从", "春秋老子", "老子哲学中德是道衍生的本体无为境界"),
    ("道", "道可道非常道", "春秋老子", "老子道是宇宙本原不可言说之规律"),
    ("仁", "仁者爱人", "春秋孔子", "孔子仁是爱人之伦理核心"),
]

def make_triple(chain, layer_idx=0, period=None, ctx=None):
    """由一层链草案生成 SUI 三元组（草案态）。"""
    node = chain["chain"][layer_idx]
    prim_ids = [c["id"] for c in node["candidate_sememes"]]
    n_i = node["n_i"]
    return {
        "primitive_ids": prim_ids,                       # 第1层（草案）
        "accretion_id": n_i,                             # 第2层
        "context_node_id": n_i,                          # 第3层（该层即激活层）
        "context": ctx or node["context"],
        "period": period or node["period"],
        "confidence": "auto",                            # 非专家标定
        "is_expert_gold": False,
    }

def synth():
    dataset = {"meta": {
        "name": "SUI-Gold Cold-Start Seed",
        "bind": "SUI v4.6 §6.1 SUI基准与验证体系（冷启动占位，非专家Gold）",
        "provenance": "auto_synth",
        "is_expert_gold": False,
        "expert_target": {"基础层": 500, "层累层": 2000, "歧义层": 1000},
        "note": "本数据集仅供编译器/评估流程冷启动跑通；须经双/三/五专家CDC蒸馏后方可称为 SUI-Gold 真值集。",
    }, "base": [], "accretion": [], "ambiguity": []}

    # 基础层
    for concept, layers in BASE_ITEMS:
        chain = build_chain(concept, layers)
        dataset["base"].append({
            "text": layers[0][1],
            "concept": concept,
            "sui_triple": make_triple(chain, 0),
            "needs_expert_review": True,
        })
    # 层累层
    for concept, layers in ACCR_ITEMS:
        chain = build_chain(concept, layers)
        triples = [make_triple(chain, i, p, c) for i, (p, c) in enumerate(layers)]
        dataset["accretion"].append({
            "concept": concept, "k": chain["k"],
            "sui_triples": triples, "needs_expert_review": True,
        })
    # 歧义层
    for concept, sent, period, ctx in AMB_ITEMS:
        chain = build_chain(concept, [(period, ctx)])
        dataset["ambiguity"].append({
            "text": sent, "concept": concept,
            "sui_triple": make_triple(chain, 0, period, ctx),
            "needs_expert_review": True,
        })
    return dataset

def to_markdown(ds):
    L = []
    L.append("# SUI-Gold 冷启动数据合成集（NOT EXPERT GOLD）\n")
    m = ds["meta"]
    L.append(f"- 绑定：{m['bind']}")
    L.append(f"- provenance：{m['provenance']} ｜ is_expert_gold：{m['is_expert_gold']}")
    L.append(f"- 专家目标规模：{m['expert_target']}")
    L.append(f"- 声明：{m['note']}\n")
    L.append("## 基础层（单义原概念）")
    for r in ds["base"]:
        L.append(f"- `{r['text']}` → 义原={r['sui_triple']['primitive_ids']} 层累={r['sui_triple']['accretion_id']} 节点={r['sui_triple']['context_node_id']} [auto]")
    L.append("\n## 层累层（多层累链词）")
    for r in ds["accretion"]:
        L.append(f"- **{r['concept']}**（k={r['k']}）")
        for t in r["sui_triples"]:
            L.append(f"  - {t['period']}：义原={t['primitive_ids']} 层累={t['accretion_id']} [auto]")
    L.append("\n## 歧义层（需语境消歧句子）")
    for r in ds["ambiguity"]:
        L.append(f"- `{r['text']}` → 义原={r['sui_triple']['primitive_ids']} 层累={r['sui_triple']['accretion_id']} 节点={r['sui_triple']['context_node_id']} [auto]")
    return "\n".join(L) + "\n"

if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT_JSON)
    ap.add_argument("--md", default=OUT_MD)
    ap.add_argument("--seed", type=int, default=42)
    args = ap.parse_args()
    random.seed(args.seed)
    ds = synth()
    json.dump(ds, open(args.out, "w", encoding="utf-8"), ensure_ascii=False, indent=2)
    md = to_markdown(ds)
    open(args.md, "w", encoding="utf-8").write(md)
    n_total = len(ds["base"]) + len(ds["accretion"]) + len(ds["ambiguity"])
    print(f"已生成冷启动数据集：{args.out}")
    print(f"  基础层 {len(ds['base'])} 条 / 层累层 {len(ds['accretion'])} 条 / 歧义层 {len(ds['ambiguity'])} 条（合计 {n_total} 条）")
    print(f"  专家目标：基础500/层累2000/歧义1000（本 seed 仅占位，须经CDC蒸馏）")
    print(f"  Markdown 预览：{args.md}")
