# -*- coding: utf-8 -*-
"""
sui_accretion_builder.py  —  P1：长尾层累链自动化构建器
=========================================================
定位（绑定 SUI v4.6 文档）：
  - §2.3 第二层：层累链ID（历时定位）—— "旧层不被新层替换，各层共存，按语境寻址"
  - §7.2 "长尾层（生僻词、古籍词、方言词）暴露码本缺口，目标 ≥ 60%（允许按域扩展）"

本脚本只做**机器起草**：
  - 输入：一个概念 + 若干 (时期, 语境片段) 层
  - 处理：用 CSMT 义原码本（anchor_library.csv，不碰 TFMC）做"弱匹配"抽取每层候选义原组合；
          按时期排序 → 生成层累链提案（accretion chain proposal）
  - 输出：JSON 提案，逐层标注 needs_expert_review=True（机器起草，非真值）

诚实边界：
  - 义原组合的"弱匹配"是启发式（字符串/家族/注释命中），不是专家蒸馏（CDC）。
  - 用户流程中"德"的手工层累链（n1殷商神秘力量…n4汉代道德品质）作为对照样例内嵌，
    用于自检：自动提案应逼近手工链的核心结构，但绝不声称等同。
  - 本工具的目标是把"长尾概念"从"码本缺口暴露"推进到"有草案可审"，而不是替代 §6.1 的三专家共识蒸馏。

用法：
  python sui_accretion_builder.py              # 跑内置 demo（德 + 一个长尾词）
  python sui_accretion_builder.py --concept "气" --layers "先秦:阴阳哲学中的本原之气" --layers "中医:气血运行的物质基础"
  python sui_accretion_builder.py --batch my_layers.json --out chain_proposals.json
  python sui_accretion_builder.py --corpus concept_history.csv --out sui_accretion_corpus_drafts.json

支持 --corpus 批量入口：从概念史语料（CSV，列 concept/period/context）批量读入
(概念, 时期, 语境) 三元组，循环调用 build_chain 整批出草案，dump 成 JSON。
语料必须由本地提供，本工具不联网抓数据。
"""
import argparse
import csv
import json
import re
import sys

# ── 路径：与码本同目录 ─────────────────────────────────────────────
import os
HERE = os.path.dirname(os.path.abspath(__file__))
CODEBOOK = os.path.join(HERE, "anchor_library.csv")

# ── 加载 CSMT 义原码本（只取 ID/义原/家族，不引入任何 TFMC 概念）──
def load_codebook(path=CODEBOOK):
    rows = list(csv.DictReader(open(path, encoding="utf-8-sig")))
    # 仅用语义字本身做倒排（不用散乱的注释字段，避免噪声）
    idx = {}
    for r in rows:
        idx.setdefault(r["sememe"], r)
    return rows, idx

ROWS, IDX = load_codebook()

# ── 手工精选概念同义映射（覆盖 demo/常见概念；仅作起草提示，非真值）──
# 键=语境中可能出现的"整词/概念"，值=码本中相关义原字列表
SYN = {
    "神秘": ["神"], "力量": [], "祭祀": ["祭"], "祖先": ["祖"],
    "政治": [], "品德": ["德"], "天命": ["天", "命"], "统治": ["治"],
    "正当": ["正"], "哲学": [], "本体": [], "无为": ["为"],
    "道德": ["德"], "品质": ["德"], "伦理": [], "规范": [],
    "自然": ["天", "地", "自"], "本原": ["本"], "物质": ["物"],
    "气血": ["气", "血"], "运行": ["行", "运"], "基础": ["基"],
    "关系": ["关"], "人伦": ["人", "伦"], "评价": ["评"], "属性": ["属"],
}

# ── 停用字：语境中这些字通常是动词/虚字/专名用字，不构成"语义义原"强信号 ──
STOP = set("指是谓名曰为在从与及于而其者之乎也矣焉哉"
           "老子孙周殷西汉代当统政伦哲无本物基关评属运")

# ── 弱匹配：从一段语境文本里猜候选义原组合（启发式，强信号优先）──
def weak_match(period_text: str):
    """返回 (候选义原列表[{id,sememe,family,reason}], 强命中数, 是否完全缺口)。"""
    hits = []
    seen = set()
    strong = 0
    # 1) 强信号：语境里直接出现某义原字（真实词义，且非停用字）
    for ch in re.findall(r"[\u4e00-\u9fff]", period_text):
        if ch in STOP:
            continue
        r = IDX.get(ch)
        if r and r["id"] not in seen:
            seen.add(r["id"])
            strong += 1
            hits.append({"id": r["id"], "sememe": r["sememe"],
                         "family": r["family_name"], "reason": f"义原字直接命中'{ch}'"})
    # 2) 中信号：语境中的整词/概念 → 同义映射（手工精选，低噪声）
    for kw, sems in SYN.items():
        if kw in period_text:
            for s in sems:
                r = IDX.get(s)
                if r and r["id"] not in seen:
                    seen.add(r["id"])
                    hits.append({"id": r["id"], "sememe": r["sememe"],
                                 "family": r["family_name"],
                                 "reason": f"概念同义'{kw}'→'{s}'"})
    # 3) 家族兜底：仅用于"是否完全缺口"探测，不塞进候选（避免噪声）
    fam_kw = {
        "动作族": ["行", "作", "为", "动", "生", "死", "变", "祭"],
        "人体族": ["身", "心", "血", "骨", "目", "口"],
        "自然族": ["天", "地", "水", "火", "气", "阴", "阳", "日", "月"],
        "属性族": ["善", "美", "大", "小", "正", "真", "德"],
        "数词族": ["一", "二", "三", "多", "少"],
        "人称族": ["我", "你", "他", "人", "众"],
        "指量族": ["此", "彼", "这", "那"],
        "动物族": ["兽", "鸟", "虫", "鱼"],
    }
    has_fam = any(kw in period_text for kws in fam_kw.values() for kw in kws)
    is_gap = (strong == 0 and len(hits) == 0)
    return hits, strong, is_gap

# ── 构建单概念层累链提案 ───────────────────────────────────────────
def build_chain(concept: str, layers: list):
    """
    layers: [(period, context_text), ...]  需按时期从早到晚排序（调用方负责）
    返回 dict：{concept, k, chain:[{n_i, period, context, candidate_sememes, match_count, is_codebook_gap, needs_expert_review}]}
    """
    chain = []
    for i, (period, ctx) in enumerate(layers, start=1):
        cands, strong, is_gap = weak_match(ctx)
        chain.append({
            "n_i": f"n{i}",
            "period": period,
            "context": ctx,
            "candidate_sememes": cands,
            "strong_match": strong,
            "is_codebook_gap": is_gap,      # True=该层码本完全未覆盖（长尾缺口信号）
            "needs_expert_review": True,   # 机器起草，必经专家蒸馏
        })
    return {
        "concept": concept,
        "k": len(chain),
        "codebook_size": len(ROWS),
        "chain": chain,
        "needs_expert_review": True,
        "provenance": "auto_draft_P1",     # 非真值
        "bind": "SUI v4.6 §2.3 层累链ID（机器起草草案，待CDC蒸馏）",
    }

# ── 内置对照样例：文档 §2.3 手工"德"链（专家级，用于自检）──────────
DOC_DE_HAND = {
    "concept": "德",
    "k": 4,
    "chain": [
        {"n_i": "n1", "period": "殷商",   "core_sememes": ["神秘力量"],         "source": "文档§2.3手工"},
        {"n_i": "n2", "period": "西周",   "core_sememes": ["政治品德", "天命"], "source": "文档§2.3手工"},
        {"n_i": "n3", "period": "春秋老子", "core_sememes": ["哲学本体", "无为"], "source": "文档§2.3手工"},
        {"n_i": "n4", "period": "汉代以后", "core_sememes": ["道德品质", "规范"], "source": "文档§2.3手工"},
    ],
}

def demo():
    print("="*70)
    print("P1 demo 1：长尾/古籍词自动化起草 —— 以'德'对照文档手工链")
    print("="*70)
    # 用与文档§2.3相同的四时期语境，跑自动弱匹配，对比手工链
    layers = [
        ("殷商",     "殷商时期德指神秘力量与祖先祭祀的禀赋"),
        ("西周",     "西周德指政治品德与天命所归的统治正当性"),
        ("春秋老子", "老子哲学中德是道衍生的本体无为境界"),
        ("汉代以后", "汉代以后德指个人的道德品质与伦理规范"),
    ]
    prop = build_chain("德", layers)
    print(json.dumps(prop, ensure_ascii=False, indent=2))
    print("\n→ 诚实备注：自动提案只输出'强/中信号候选义原'，结构（4层、按时期）逼近")
    print("  手工链；但每层'核心义原组合'须经三专家CDC蒸馏（文档§6.1）定稿，本工具不替代。")

    print("\n" + "="*70)
    print("P1 demo 2：真正的长尾词（方言/生僻）—— 码本缺口暴露示例")
    print("="*70)
    # 长尾词：假设一个古籍/方言概念，码本未必直接覆盖
    layers2 = [
        ("上古",   "该词在上古指某种自然现象与祭祀相关的行为动作"),
        ("中古",   "中古引申为人伦关系中的某种属性评价"),
    ]
    prop2 = build_chain("𢼾(示例生僻字)", layers2)
    print(json.dumps(prop2, ensure_ascii=False, indent=2))
    print("\n→ 长尾层目标（文档§7.2）：暴露码本缺口、≥60% 可扩展。")
    print("  若 match_count=0，说明该层完全在码本外，正是'需按域扩展'的信号。")

# ── 批量入口：从概念史语料 CSV 读入三元组，循环出整批草案 ─────────────
def _period_key(p):
    """best-effort 排序键：能转数字按数字，否则按字符串排。"""
    try:
        return (0, float(p))
    except (ValueError, TypeError):
        return (1, p)


def run_corpus(corpus_path: str, out_path: str):
    """
    读 CSV（列至少含 concept/period/context）：
      - 按 concept 分组（同一概念多行=多个时期层）
      - 每组按 period best-effort 排序后调 build_chain
      - 收集进 {corpus, provenance, needs_expert_review, note, drafts}
      - json.dump(ensure_ascii=False, indent=2) 写出
    健壮性：缺列/编码错误/行异常 try/except 捕获并 print 警告跳过；
            concept 或 context 为空跳过该行。
    """
    try:
        f = open(corpus_path, encoding="utf-8-sig", newline="")
    except (OSError, UnicodeDecodeError) as e:
        print(f"[corpus] 无法打开语料文件，已跳过：{e}")
        return

    groups = {}
    with f:
        reader = csv.DictReader(f)
        required = ("concept", "period", "context")
        if not all(c in (reader.fieldnames or []) for c in required):
            print(f"[corpus] 语料缺少必要列（需含 {required}），"
                  f"现有列：{reader.fieldnames}，已跳过")
            return
        for n, row in enumerate(reader, start=1):
            try:
                concept = (row.get("concept") or "").strip()
                period = (row.get("period") or "").strip()
                context = (row.get("context") or "").strip()
            except Exception as e:
                print(f"[corpus] 第{n}行读取异常，跳过：{e}")
                continue
            if not concept:
                print(f"[corpus] 第{n}行 concept 为空，跳过")
                continue
            if not context:
                print(f"[corpus] 第{n}行 concept='{concept}' 的 context 为空，跳过")
                continue
            groups.setdefault(concept, []).append((period, context))

    drafts = []
    for concept in groups:
        layers = sorted(groups[concept], key=lambda pc: _period_key(pc[0]))
        try:
            draft = build_chain(concept, layers)
        except Exception as e:
            print(f"[corpus] 概念'{concept}'构建失败，跳过：{e}")
            continue
        drafts.append(draft)

    out = {
        "corpus": corpus_path,
        "provenance": "auto_draft_P1_corpus",
        "needs_expert_review": True,
        "note": "机器批量草案，必经专家CDC蒸馏定稿，不计入SUI-Gold专家基准",
        "drafts": drafts,
    }
    json.dump(out, open(out_path, "w", encoding="utf-8"),
              ensure_ascii=False, indent=2)
    print(f"已写出 {len(drafts)} 条批量草案 → {out_path}")


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--concept", default=None)
    ap.add_argument("--layers", action="append", default=[],
                    help="格式 '时期:语境文本' ，可多次")
    ap.add_argument("--batch", default=None, help="JSON 文件：{concept:[[period,ctx],...]}")
    ap.add_argument("--corpus", default=None,
                    help="CSV 文件：列 concept/period/context（可含额外列），批量出草案")
    ap.add_argument("--out", default="sui_accretion_corpus_drafts.json")
    args = ap.parse_args()

    if args.concept and args.layers:
        parsed = []
        for L in args.layers:
            if ":" not in L:
                print("layer 格式应为 '时期:语境文本'"); sys.exit(1)
            p, c = L.split(":", 1)
            parsed.append((p.strip(), c.strip()))
        res = build_chain(args.concept, parsed)
        print(json.dumps(res, ensure_ascii=False, indent=2))
    elif args.batch:
        batch = json.load(open(args.batch, encoding="utf-8"))
        out = {c: build_chain(c, layers) for c, layers in batch.items()}
        json.dump(out, open(args.out, "w", encoding="utf-8"),
                  ensure_ascii=False, indent=2)
        print(f"已写出 {len(out)} 条链提案 → {args.out}")
    elif args.corpus:
        run_corpus(args.corpus, args.out)
    else:
        demo()
