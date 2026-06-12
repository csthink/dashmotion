# Dashmotion

[English](README.md) | 简体中文

**会流动的图。** 一个 Claude AI skill,把纯文字描述变成带动画的技术图表——虚线沿执行方向流动,光点像真实请求一样在系统中穿行——也就是现代基础设施产品官网(Diagrid、Temporal、Inngest)上那种动效,输出为单个自包含的 HTML/SVG 文件。

项目名即实现本身:**`stroke-dash`** offset 动画 + **`animateMotion`** 路径。全部技巧就这两招——零依赖库、不渲染 GIF、不需要设计工具。

| Flow 模式 | Architecture 模式 |
|---|---|
| ![flow demo](examples/images/flow-demo.gif) | ![architecture demo](examples/images/architecture-demo.gif) |

## 两种模式

**Flow 模式** — 工作流、流水线、状态机。*发生了什么,按什么顺序。* 单色"电路"美学:暗色画布上,执行流从 START 经分支与汇合,清晰可见地流向 END。

**Architecture 模式** — 系统、基础设施、拓扑。*系统由什么组成——以及请求如何在其中流动。* 语义化组件配色(前端/服务/数据/云/安全)、region 与安全组边界、图例、摘要卡片,以及差异化的核心:**动画请求旅程**。一颗青色光点从客户端出发,跳过 CDN 和网关,落进服务,抵达数据库,然后下一个请求开始。你的架构图解释的是*行为*,而不只是结构。

## 为什么不直接用 GIF?

| | GIF | Dashmotion (SVG/CSS) |
|---|---|---|
| 文件体积 | 数 MB | 数十 KB |
| 清晰度 | 固定分辨率 | 矢量,无限缩放 |
| 可编辑性 | 全部重新渲染 | 让 Claude 改一个框即可 |
| 无缝循环 | 逐帧对齐的苦活 | 天然免费 |
| 之后转 GIF | — | 一条命令(`timecut`)或直接录屏 |

## 快速开始

> 需要 Claude Pro、Max、Team 或 Enterprise 订阅。

1. 从 [Releases](../../releases) 下载 `dashmotion.zip`
2. claude.ai → **Settings** → **Capabilities** → **Skills** → **+ Add** → 上传 zip → 开启
3. 直接提问(中文提示词实测可正常触发):

```
帮我画一个动画流程图:
- 用户提交订单
- 并行校验支付和库存
- 等待风控定时器
- 发货后并行发送确认邮件和更新分析
```

或:

```
画出我们的系统架构并让主请求路径动起来:
- React 前端走 CloudFront
- API Gateway 后面是私有子网里的 Auth Service (Go) 和 Order Service (Node)
- 数据层 PostgreSQL + Redis
- Cognito 做认证
```

Claude 会返回一个 `.html` 文件,打开即动。

### Claude Code

用 [`skills`](https://github.com/vercel-labs/skills) CLI 安装——**Claude Code 请带上 `-a claude-code`**。一条命令搞定安装、升级、或替换手动解压的旧版:它会在 `~/.claude/skills/dashmotion` 写入一个真目录(`/skills` 能正常列出),并覆盖原有内容。

```bash
npx skills add csthink/dashmotion -a claude-code   # 安装——之后重跑这条即更新
```

> 为什么要这个 flag:裸 `npx skills add csthink/dashmotion` 建的是*符号链接*而非拷贝,而 Claude Code 当前对符号链接支持很不稳——链接可能根本没建成、符号链接的 skill 不出现在 `/skills`([claude-code#14836](https://github.com/anthropics/claude-code/issues/14836))、`npx skills update` 也不会刷新它。`-a claude-code` 用普通拷贝绕开了所有这些坑。其他 agent(Cursor、Codex 等)直接读 `~/.agents/skills/`,裸命令没问题。

想用 zip?同样可靠,只是手动——升级时先清空目录,避免旧文件残留:

```bash
rm -rf ~/.claude/skills/dashmotion && unzip dashmotion.zip -d ~/.claude/skills/   # 全局
unzip dashmotion.zip -d ./.claude/skills/                                         # 或项目级
```

### 卸载

用 `skills` CLI 装的(会从所有装过的 agent 一并移除):

```bash
npx skills remove dashmotion        # 全局安装的话加 -g
```

手动解压装的——直接删目录:

```bash
rm -rf ~/.claude/skills/dashmotion      # 全局
rm -rf ./.claude/skills/dashmotion      # 或项目级
```

## 动画原理

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

Skill 的真正价值在于把布局算术写成了硬约束,让生成稳定可靠:扇出/汇入的 branch-bar 模式、边界嵌套与留白规则、半透明填充下的不透明遮蔽、图例摆放、无缝循环的周期约束、以及让光点"钻进"节点而非滑过节点的绘制顺序。交付前还会对照结构自检清单复核一遍——框重叠、连线穿框、动画循环断裂、坐标越界——发现问题先修复再交付。

## 项目结构

```
dashmotion/                               # 仓库根
├── skills/dashmotion/                    # skill 本体——安装的就是这个目录
│   ├── SKILL.md                          # 模式路由 + 动画契约 + 共享设计令牌
│   ├── references/
│   │   ├── flow-mode.md                  # 流程图布局算术
│   │   └── architecture-mode.md          # 语义配色、边界、图例、请求旅程
│   └── resources/
│       ├── template-flow.html            # 可直接运行的流程图示例
│       └── template-architecture.html    # 可直接运行的架构图示例(AWS + 动画请求)
├── eval/                                 # 结构自检脚手架 + 前后对比证据
└── examples/                             # demo GIF
```

`npx skills add` 和发行版 zip 只打包 `skills/dashmotion/`;`eval/` 和 `examples/` 留在仓库里。两个模板本身就是完整可用的示例——现在就能用浏览器打开。

## 导出 GIF / MP4

直接录屏(macOS ⌘⇧5)。动画周期均能整除 3 秒,录 3 秒即可无缝循环。带光点的图优先用录屏——原因见下方提示。

无头 / 可脚本化:

```bash
npx timecut your-diagram.html --viewport=1200,900 --duration=3 --fps=30 --output=out.mp4
ffmpeg -i out.mp4 out.gif
```

> **`timecut` 与光点:** `<animateMotion>` 光点跑在 SVG 的 SMIL 时间线上,而 `timecut` 的虚拟时钟不驱动它——延迟启动的光点会停在 SVG 原点,在每一帧左上角留下杂散标记。`timecut` 对虚线连接线的流动没问题;但光点请改用实时录屏,或驱动实时无头录屏(如 Chrome DevTools 的 `Page.startScreencast`)。

## 可访问性

所有 CSS 动画包裹在 `@media (prefers-reduced-motion: no-preference)` 中;系统开启"减弱动态效果"时,SMIL 光点由脚本移除;每张图自带可见的暂停/播放按钮,以及 `role="img"` + `<title>`/`<desc>`。

## 常见问题

**可以和 [architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator) 同时安装吗?**
可以——已实测共存。带动画意图的请求("让请求路径动起来")路由到 dashmotion;纯静态架构图请求仍由 Cocoon 的 skill 处理。无文件冲突。

## 致谢

Skill 打包模式与静态架构设计体系基于 [Cocoon-AI/architecture-diagram-generator](https://github.com/Cocoon-AI/architecture-diagram-generator)(MIT)。视觉风格灵感来自 [diagrid.io](https://www.diagrid.io/catalyst) 的工作流动画。

## 协议

MIT