# dashmotion 实现原理

实现说明。想了解 dashmotion 能做什么、怎么安装,见 [README](../README.zh-CN.md);版本历史见 [CHANGELOG.md](../CHANGELOG.md)。

## 动画

**流动的虚线** — 让 `stroke-dashoffset` 每次精确偏移一个虚线周期:

```css
.flow { stroke-dasharray: 5 5; animation: dashmove 0.75s linear infinite; }
@keyframes dashmove { to { stroke-dashoffset: -10; } }
```

**沿路径运动的光点** — `<animateMotion>` 直接复用连线自己的路径数据。Architecture 模式中,光点通过 SMIL 事件时序链(`begin="j1.end+0.3s"`)串联,一个请求逐层跳跃、清晰可见:

```svg
<circle r="3.5" fill="#22d3ee">
  <animateMotion id="j2" dur="0.7s" begin="j1.end+0.3s" fill="freeze"
    path="M416 118 L464 118"/>
</circle>
```

## 布局引擎

让生成稳定可靠的布局算术——扇出/汇入的 branch-bar 模式、边界嵌套与留白、半透明填充下的不透明遮蔽、图例摆放、无缝循环周期约束、无碰撞布线、以及让光点"钻进"节点而非滑过的绘制顺序——由自带的纯标准库引擎 `scripts/layout.py` 计算:模型把图描述成语义图,脚本算出几何,模型照着转写(无 `python3` 时退回人工计算)。交付前两个自带校验脚本各跑一遍并修复——`scripts/check_diagram.py` 查结构(框重叠、连线穿框、动画循环断裂、坐标越界、节点落在不属于它的分组框内);Mermaid 输入时 `scripts/check_fidelity.py` 确认每个标签和边都逐字保留。无论哪条路,**产物本身始终零依赖**:一个 HTML 文件,无库、无构建——Python 只在生成端用。

## 项目结构

```
dashmotion/                               # 仓库根
├── skills/dashmotion/                    # skill 本体——安装的就是这个目录
│   ├── SKILL.md                          # 模式路由 + 动画契约 + 共享设计令牌
│   ├── references/
│   │   ├── flow-mode.md                  # 流程图布局算术
│   │   ├── architecture-mode.md          # 语义配色、边界、图例、请求旅程
│   │   ├── mermaid-input.md              # Mermaid → dashmotion 转换规则 + fidelity 契约
│   │   └── layout-script.md              # layout.py 输入/输出契约 + 转写指南
│   ├── scripts/                          # 纯标准库,只在生成端用(产物保持零依赖)
│   │   ├── layout.py                     # 确定性布局引擎——语义图 → 几何
│   │   ├── check_diagram.py              # 结构校验(C1–C9)
│   │   └── check_fidelity.py             # Mermaid fidelity 校验(标签/边逐字)
│   └── resources/
│       ├── template-flow.html            # 可直接运行的流程图示例
│       └── template-architecture.html    # 可直接运行的架构图示例(AWS + 动画请求)
├── eval/                                 # 结构自检脚手架 + 前后对比证据
├── examples/                             # demo GIF
├── CHANGELOG.md                          # 版本历史
└── README.md
```

`npx skills add` 和发行版 zip 只打包 `skills/dashmotion/`;`eval/`、`examples/`、`docs/` 和 `CHANGELOG.md` 留在仓库里。两个模板本身就是完整可用的示例——现在就能用浏览器打开。

## 导出 GIF / MP4

直接录屏(macOS ⌘⇧5)。动画周期均能整除 3 秒,录 3 秒即可无缝循环。带光点的图优先用录屏——原因见下方提示。

无头 / 可脚本化:

```bash
npx timecut your-diagram.html --viewport=1200,900 --duration=3 --fps=30 --output=out.mp4
ffmpeg -i out.mp4 out.gif
```

> **`timecut` 与光点:** `<animateMotion>` 光点跑在 SVG 的 SMIL 时间线上,而 `timecut` 的虚拟时钟不驱动它——延迟启动的光点会停在 SVG 原点,在每一帧左上角留下杂散标记。`timecut` 对虚线连接线的流动没问题;但光点请改用实时录屏,或驱动实时无头录屏(如 Chrome DevTools 的 `Page.startScreencast`)。
