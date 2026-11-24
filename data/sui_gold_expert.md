<!-- 本工具仅提供蒸馏流程骨架，专家标注/仲裁为人工环节，auto 数据未经 CDC 蒸馏前不得计入 SUI-Gold 专家基准，不用于 H-SUI-7 阈值评估。 -->

# SUI-Gold Expert 蒸馏骨架产物（NOT FINAL EXPERT GOLD）

> ⚠️ 本工具仅提供蒸馏流程骨架，专家标注/仲裁为人工环节，auto 数据未经 CDC 蒸馏前不得计入 SUI-Gold 专家基准，不用于 H-SUI-7 阈值评估。

- 绑定：SUI §6.1 基准与验证体系（蒸馏骨架产物，非最终真值）
- provenance：cdc_ingest_skeleton ｜ is_expert_gold(占位)=True ｜ cdc_distilled=False
- 专家目标规模：{'基础层': 500, '层累层': 2000, '歧义层': 1000}
- 声明：本文件由蒸馏骨架产出：is_expert_gold=True 仅为下游格式占位；是否真正进入 SUI-Gold 专家基准取决于 cdc_distilled / needs_arbitration / final_sememes_source 等字段，且须由人工完成 CDC 蒸馏与仲裁。

## κ 一致性报告（仅当 ≥2 专家标注时可计算）

- 专家数：0
- 平均 κ：**N/A** ｜ 最低 κ：**N/A**
- 说明：单专家标注（或 auto 沿用），κ 需 ≥2 专家，无法计算。

## 样本明细

| sample_id | 层 | auto义原 | 最终义原 | 来源 | κ | 需仲裁 |
| --- | --- | --- | --- | --- | --- | --- |
| base_水 | 基础层(base) | S01;N01;B43 | S01;N01;B43 | auto_carryover | N/A | 否 |
| base_火 | 基础层(base) | S02;V33 | S02;V33 | auto_carryover | N/A | 否 |
| base_人 | 基础层(base) | R09;V46 | R09;V46 | auto_carryover | N/A | 否 |
| base_天 | 基础层(base) | S06;B01;S39;V38;Z17;R07;S07 | S06;B01;S39;V38;Z17;R07;S07 | auto_carryover | N/A | 否 |
| base_道 | 基础层(base) | S34;V54 | S34;V54 | auto_carryover | N/A | 否 |
| accr_德_n1 | 层累层(accretion) | P35;S35;V58;V51 | P35;S35;V58;V51 | auto_carryover | N/A | 否 |
| accr_德_n2 | 层累层(accretion) | P35;S06;V63;P39 | P35;S06;V63;P39 | auto_carryover | N/A | 否 |
| accr_德_n3 | 层累层(accretion) | P35;S34;V33;B43 | P35;S34;V33;B43 | auto_carryover | N/A | 否 |
| accr_德_n4 | 层累层(accretion) | P35;R09;S34;V54 | P35;R09;S34;V54 | auto_carryover | N/A | 否 |
| accr_气_n1 | 层累层(accretion) | R07;S06;S07 | R07;S06;S07 | auto_carryover | N/A | 否 |
| accr_气_n2 | 层累层(accretion) | B20;V27;V33;V63 | B20;V27;V33;V63 | auto_carryover | N/A | 否 |
| accr_仁_n1 | 层累层(accretion) | R09;B29 | R09;B29 | auto_carryover | N/A | 否 |
| accr_仁_n2 | 层累层(accretion) | P38;B28;B29;B43;V33 | P38;B28;B29;B43;V33 | auto_carryover | N/A | 否 |
| amb_德_0 | 歧义层(ambiguity) | P35;S34;V33;B43 | P35;S34;V33;B43 | auto_carryover | N/A | 否 |
| amb_道_1 | 歧义层(ambiguity) | S34;Z09;V30;V54 | S34;Z09;V30;V54 | auto_carryover | N/A | 否 |
| amb_仁_2 | 歧义层(ambiguity) | R09;B29 | R09;B29 | auto_carryover | N/A | 否 |
