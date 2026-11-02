# 评测报告（离线流水线 + 规则通道，不调用模型）

- S1: PASS — refused=False, rules=['sql-injection'], reason=
- S2: PASS — refused=False, rules=['null-check', 'null-check'], reason=
- S3: PASS — refused=False, rules=['hardcoded-secret'], reason=
- S4: PASS — refused=False, rules=['empty-catch'], reason=
- D1: PASS — refused=False, rules=[], reason=
- D2: PASS — refused=False, rules=[], reason=
- F1: PASS — refused=False, rules=[], reason=仅格式 / 缩进改动，无实质评审意见。
- F2: PASS — refused=False, rules=[], reason=仅注释改动，无实质评审意见。
- O1: PASS — refused=True, rules=[], reason=超范围：本切片只评审 Java diff。
- O2: PASS — refused=True, rules=[], reason=空 diff，无法评审。
- U1: PASS — refused=False, rules=['sql-injection'], reason=
- L1: PASS — refused=False, rules=['sql-injection', 'long-line'], reason=

通过：12/12
