# Step 6「生成后结构自检」失败率评测

日期：2026-06-11 · 分支：`feat/post-gen-self-check` · 生成/自检模型：claude-fable-5

## 要回答的问题

prose 自检（SKILL.md Step 6）能把结构失败率压低多少？失败形态是什么？——作为「是否值得引入 elkjs 确定性布局」的决策依据。

## 方法

- **配对样本**：10 个真实 prompt（5 flow + 5 architecture，8–16 节点，覆盖回环、三路分支、并行轨、消息总线、嵌套/并列边界、异步边），见 `prompts.json`。
- **baseline**：10 个独立 agent 各读 `/tmp` 冻结快照（**不含 Step 6** 的旧 skill），按 Step 1–5 生成 → `runs/baseline/`。
- **自检组**：10 个独立 agent 读新 SKILL.md 的 Step 6 清单，对 baseline 文件逐条核对并修复 → `runs/checked/`。
- **测量**：`check_diagram.py` 确定性几何检测（C1 重叠 / C2 连线穿框 / C3 虚线周期断环 / C4 viewBox 越界 / C5 光点脱线 / C6 黑色填充 / C7 端点刺入 / C8 begin 引用悬空 / PARSE）。校准：两个官方模板 0 误报；8 类注入缺陷 8/8 检出。

## 数字

| | 自检前 | 自检后 |
|---|---|---|
| 确定性检测失败（≥1 违规的图） | **2/10** | **2/10** |
| 全部已知缺陷（含脚本不覆盖的软规则） | **3/10** | **2/10** |
| 模型自检对已知缺陷的召回 | — | **1/3** |

| 文件 | baseline 检测 | 模型自检报告 | 自检后检测 |
|---|---|---|---|
| f1-cicd / f2-order-saga / f4-etl / f5-incident | PASS | 无违规 | PASS |
| f3-signup-state | **PARSE**（注释含 `--` 提前闭合，散落文本泄入 DOM） | 无违规 ✗ 漏检 | **PARSE**（未修） |
| a1-saas-aws / a2-k8s-kafka / a3-multi-region | PASS | 无违规 | PASS |
| a4-serverless | **4×C5**（光点脱离连接线） | 无违规 ✗ 漏检 | **4×C5**（未修） |
| a5-hybrid | PASS（缺陷在脚本盲区） | **抓到**：动画扇出间隙 44px < 规则 90px，修复并级联 viewBox 662→698 | PASS ✓ |

缺陷明细（均经人工复核为真阳性）：

- **a4**：生成者把多跳 journey 合并成自创路径——`M434 218 H756` 横穿 (510,190,170×56) 组件盒正中（连接线只有 `M434 218 H506` 和 `M684 218 H756` 两段），4 条 dot 全部如此。dot 绘制在组件之下，视觉上光点钻入盒子又凭空穿出，跳跃语义全失。
- **f3**：`<!-- Validate Input -- errors --> back to form -->`——XML 注释内的 `--` 提前闭合注释。浏览器容错（SVG 内散落文本不渲染），但文件不再是良构 XML，会弄坏下游工具链（转换器/解析器）。
- **a5**：ALB→App 层间隙 44px，内有动画扇出轨+双 dot，architecture-mode.md 要求此时 ≥90px。模型自检正确执行了算术（426+90>470）并完整修复（行移位、子网/VPC/图例/viewBox 级联、dot 时长按速度守恒调整）。

## 三个发现

1. **布局算术失败率 = 0/10**。重叠、连线穿框、越界、断环一例都没有——模板 + references 的布局算术已经把 DiagramEval 量化的那类坐标失败挡在门外。**elkjs 要解决的问题（节点布局）目前不是 dashmotion 的痛点**，10 样本下没有出现一例它能修的缺陷。
2. **残余失败集中在动画-几何一致性层**（dot 路径 vs connector 几何）。方向上与 DiagramEval「Path 层主导失败」一致，但具体形态是 dashmotion 特有的「journey 合并跨段」——这不是布局引擎能修的，是「动画路径必须从连接线派生」的一致性约束问题。
3. **prose 自检对软布局规则有效，对几何核对不可靠**。a5 的间距算术它做了且做对了；a4 的贴线核对清单第 3 条**明确要求**，agent 仍报告「无违规」——模型会"声称检查过"而实际没做逐条算术。结论与全局经验一致：**能跑的机制才真生效，prose 会被静默漏掉**——对模型也成立。

## 结论

- **elkjs：暂缓**。它针对的失败类别在本 skill 的模板化场景下实测为零。
- **下一步最高杠杆**：把 `check_diagram.py` 机制化——作为 `scripts/` 资源打进 skill，Step 6 改为「环境有 Python 就跑脚本，否则才走 prose 清单」。它恰好覆盖模型自检漏掉的两类（C5 脱线、PARSE），且不进产物、不破坏输出零依赖。**需要先拍板「零依赖」卖点的边界定义（产物零依赖 vs 生成器零依赖）**。
- Step 6 文本已按两个漏检形态补强（v1.1）：journey 跨段拆分的操作化核对、注释 `--` 卫生。**v1.1 未经第二轮评测验证**。

## 局限

- n=10、单模型、单轮；生成与自检同代模型。弱模型的 baseline 失败率大概率更高，本数字是下界。
- 自检 agent 无生成上下文（新 agent 读文件），与真实场景（生成者顺手自检）有偏差，方向不明。
- 检测脚本盲区：文字/标签碰撞（需字体度量）、边界 20px padding、tier 间距规则（a5 类）、图例位置。盲区内的缺陷只能靠模型自检或人眼。
- f3 的 PARSE 无视觉影响，计入失败是按「良构产物」契约从严。

## 复现

```bash
python3 eval/check_diagram.py eval/runs/baseline/*.html eval/runs/checked/*.html
```

---

# 附：mermaid 输入（v2.2.0）验收评测

日期：2026-06-12 · 生成/自检模型：claude-fable-5 · 用例：`prompts.json` 的 m1–m6（TB 分支+回环 / LR 嵌套 subgraph→architecture / stateDiagram-v2 自环 / 边种类 / 对抗标签 / 样式指令忽略）

## 方法

每用例一个无上下文 agent 读 v2.2.0 skill（含新增 `references/mermaid-input.md`）生成；测量 = `check_diagram.py`（C1–C8）+ 新增 `check_fidelity.py`（F1 节点标签在场 / F2 边标签在场 / F3 分组标签在场 / F4 连线数==源边数，容差=回环边数）+ 用例级 grep 断言。同时用同一改后 skill 重跑 3 个自然语言回归用例（CI/CD flow、K8s architecture、混合路由）。

## 数字

| | 结果 |
|---|---|
| 自然语言回归（3 用例，改动后） | **3/3 PASS**——mermaid 改动零回归 |
| mermaid 用例确定性检测 C1–C8 | **6/6 PASS** |
| mermaid fidelity F1–F4 | **6/6 PASS**（m1 12/12 边、m3 7 连线+1 ↻ 自环、m5 对抗标签逐字保真含 `--`/中文/`<admin>` 转义） |
| 产物真缺陷 | **1/9 次生成**（m6 首轮）：agent 把「样式已丢弃」的告知写进产物 summary card。根因是 mermaid-input.md 没写明告知位置——spec 缺口而非模型失误；补「告知放对话、产物禁含 mermaid 指令词」后重生成通过 |
| 检测器误报（当场修复） | 3 处：dasharray 断言不认 CSS 类写法；fidelity 把 legend 样例线计为连接线（改为端点须落在节点框附近）；fidelity 对 tspan 换行拼接漏空格 |

## 发现

1. **mermaid 输入的布局算术失败率 0/6**，与自然语言路径的 0/10 一致——结构化输入没有引入新的坐标失败面。
2. **唯一缺陷出现在 prose 没写死的自由度上**（告知放哪），不是几何，再次印证「能跑的机制才真生效，prose 留白必被走偏」。
3. Step 6 第 6 条（fidelity 计数）模型全部主动执行且与脚本结果一致——计数类核对是模型自检擅长的形态（对比上轮：贴线几何核对是它不擅长的形态）。

## 局限

n=6、单模型、单轮；m6 为修 spec 后二次生成（首轮失败已计入上表）；fidelity 的 F4 连线计数对「端点不落在节点框附近的装饰线」存在盲区；[人工目检] 项（动画观感、LR 重排效果）不在脚本覆盖内。

## 复现

```bash
python3 test/run_checks.py test/runs/<date>-post   # 全量断言（test/ 不入库，runner 在 test/run_checks.py）
python3 eval/check_fidelity.py <case>.mmd <out>.html
```
