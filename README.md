# visio-diagram

在 Windows 后台使用 Visio COM，将结构说明生成**原生可编辑的 `.vsdx` 和由同一文件导出的 PNG**。用于流程图、算法图、网络结构图和系统架构图。

包含 Codex Skill、可复用绘图/检查脚本、三种可运行布局示例和已验收的风格参考。当前版本见 [VERSION](VERSION)。

## 环境要求

- Windows；已安装并可正常使用的 Microsoft Visio 桌面版。
- 一个 Windows Python 环境，能够 `import win32com.client`（pywin32）。
- Git；使用 Skill 时需有 Codex。本绘图脚本也可以独立运行。

无需 Computer Use。Visio 和 Python 依赖不会随 Skill 自动安装。macOS/Linux 无法直接运行这里的 Windows COM 绘图脚本。

## 在另一台电脑安装

在 PowerShell 中执行；同一仓库只克隆一次：

```powershell
$visioSource = Join-Path $env:USERPROFILE '.codex\skill-sources\EvanKKAI\visio-diagram'
git clone https://github.com/EvanKKAI/visio-diagram.git $visioSource
& (Join-Path $visioSource 'scripts\install.ps1')
```

安装器在个人技能目录创建指向此 Git 仓库的目录联接，保留 `.git`、远端、分支和 commit；识别 `CODEX_HOME`，未设置时使用 `~/.codex`。已有同名普通目录或指向其他位置的联接时停止，不覆盖。

使用已有 Windows Python 检查环境；下面的 `python` 可替换为该解释器的完整路径：

```powershell
python -B (Join-Path $visioSource 'scripts\render.py') probe
```

若缺少 pywin32，在选定的 Python 环境安装后再检查，例如 `python -m pip install pywin32`。不要为了绘图额外安装大型 Python 发行版。

## 使用

在 Codex 中提供源码、流程说明或参考图，并说明目标用途：

> 使用 $visio-diagram，依据这个项目画结构图，沿用我的组会风格，交付原生可编辑 Visio 和 PNG。

允许按任务自动选用，也支持显式调用。若当前对话尚未识别新安装的技能，可在新对话中调用。

默认一框一动作（模块图按一致的模块层级）、公式放在框下、分区配色、优先留白和调整走线。内容与绘图代码分离，每张图保留独立 JSON 配置。具体算法、机器连接和实验参数不写死在通用引擎中。

## 独立运行示例

```powershell
python -B (Join-Path $visioSource 'scripts\render.py') render `
  (Join-Path $visioSource 'assets\examples\branch-fusion.json') `
  --output '.\out\branch-fusion.vsdx'
```

输出 VSDX、PNG、manifest 和 audit。修改时优先使用新文件名；明确要覆盖同名输出时加 `--overwrite`。

- [分支融合](assets/examples/branch-fusion.json)：根号、分式、旁路、汇合。
- [跳跃连接网络](assets/examples/skip-network.json)：主干、跳连、张量标注。
- [分层系统](assets/examples/layered-system.json)：容器、跨层路由、跨线桥。

配置字段和公式能力见 [spec.md](references/spec.md)，视觉规则见 [design.md](references/design.md)。

## 更新与后续定制

已安装后，在 PowerShell 执行：

```powershell
& (Join-Path $visioSource 'scripts\update.ps1')
```

更新脚本先检查工作区、分支和 origin，再获取上游并显示差异；只有可以快进时才更新。存在未提交修改、仅本地提交或分叉时停止，保留现场。更新后核验技能结构、目录联接、远端、分支、commit 和工作区状态。不会强制重置，也不会后台自动更新。

新增要求时，可让 Codex 修改此仓库中的通用组件或规则，并针对改动验证。仅某张图的内容修改留在该图的 JSON 中；稳定、可复用的改进再提交到仓库。`VERSION` 和 Git 标签用于记录正式版本；其他电脑在需要时运行更新脚本获取这些改进。

## 验证与边界

保存后重新打开实际 VSDX，检查原生文本、边界/遮挡、连接线双端吸附、保存后的走线、公式归属，以及移动节点后公式和端点是否随动。PNG 从重新打开的文件导出。

仍需查看整图与关键局部，核对算法依据和表达是否正确。引擎不自动理解源码，也不自动解决任意布局；复杂嵌套公式需要扩展原生组件。

先将三个示例渲染到同一个专用测试目录（文件名对应各自示例），再运行：

```powershell
python -B (Join-Path $visioSource 'scripts\check_engine.py') '.\test-output'
```

它复查三图、测试文字溢出/遮挡/断线的识别，并生成菱形/椭圆补充校样。测试修改不保存到原图。完整测试说明见 [maintenance.md](references/maintenance.md)。

`assets/accepted-reference.*` 是风格参考，其中的弱光算法、分辨率和迭代参数不作为新任务默认值。发布包不包含项目运行记录、远程连接配置、凭据、视频或数据集。
