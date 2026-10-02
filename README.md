# Codex 输入栏统计

在 Windows 微软商店版 **Codex 官方客户端**的输入栏显示会话统计、累计 Token 用量、当前上下文和最大上下文。悬停查看详情，在客户端的插件管理中开关。支持 ChatGPT 登录和 API 登录。

本项目为社区插件，按 MIT 协议开源，与 OpenAI 无隶属关系。

## 安装

1. 安装 Windows x64 微软商店版 Codex，至少启动过一次。
2. 从 [GitHub Releases](https://github.com/wangding0610/codex-native-stats/releases/latest) 下载 `CodexStats-Setup-3.0.0-windows-x64.exe` 并运行。
3. 保存当前任务，**正常退出客户端一次**，再从桌面的 **Codex 官方版（输入栏统计）** 打开。
4. 在 Codex 的「设置 → 插件」中找到 **Codex 输入栏统计**，可以启用或停用。

安装器包含 Python、Node 和依赖，不需要另装 Conda、Python、Node，不需要管理员权限。默认安装到 `%USERPROFILE%\CodexNativeStats`，不修改系统 PATH 或 PowerShell 执行策略。首次发行未做代码签名。

首次安装不结束正在运行的官方客户端。原来以普通入口启动的窗口没有本地加载端点，等待再久也不能挂载控件；正常退出后使用上述入口。新建空对话没有统计，发送消息并产生本地记录后才显示。

如果以前装过 `codex-native-stats@personal`，先保存任务、正常退出 Codex，并移除旧 personal 插件，再安装此版，避免同时运行两个控制器。安装器会检测并提示。

## GitHub 插件市场

市场地址：`wangding0610/codex-native-stats`。官方插件机制只负责安装插件，不负责提供本地运行环境，所以 **Windows 安装包仍是必需的**。

安装器默认注册发行包内的本地市场，方便离线安装。希望由 GitHub 管理插件源时，先完成安装器安装、正常退出 Codex，然后在独立 PowerShell 窗口将本地市场源换成 GitHub 源：

```powershell
codex plugin marketplace remove codex-stats
codex plugin marketplace add wangding0610/codex-native-stats --ref main
codex plugin add codex-native-stats@codex-stats
```

GitHub 仓库本身就是可安装市场；这并不表示已进入 OpenAI 官方公共插件目录。

## 更新与卸载

官方客户端继续由微软商店/官方机制更新。加载器每次查找当前注册的官方包，不复制或修改官方程序。**客户端界面结构变化仍可能使挂载失效，需要插件适配，不能承诺永久兼容。**

插件发行包更新：从 Releases 下载新安装器，安装到原目录。安装器按版本保存运行环境，切换当前版本，并重新注册该版本附带的本地市场。建议先保存任务、正常退出 Codex，再升级插件。GitHub 市场更新也需要安装对应运行环境，避免代码和依赖不同步。

卸载：Windows「设置 → 应用 → 已安装的应用 → Codex 输入栏统计」，或开始菜单中的卸载入口。卸载保留官方 App、登录、API 配置、聊天以及本地统计样本。它只移除本市场下的插件、自己的快捷方式和运行文件。

## 统计含义

| 显示 | 含义 |
|---|---|
| 累计用量 | 本会话各次请求的累计用量；重复输入会重复计入 |
| 当前上下文 / 最大上下文 | 最新上下文记录中的使用量和有效上限；压缩后当前上下文可能下降 |
| TTFT / 耗时 | 本地事件记录的首 Token 等待和执行时间 |
| 生成速度 | 对已完整观察并匹配的输出事件计算的客户端估计，包含网络和缓冲影响 |

这些指标不是账单。模型/API 提供方的价格、缓存规则和实际账单另行决定费用。不把字符数冒充 Token，不重构未观察到的历史生成速度。

## 工作方式与数据

插件通过官方客户端的本机 renderer 调试端点嵌入 DOM；这是本地加载方案，**不是官方提供的输入栏扩展 API**。端点只接受环回地址，并验证官方进程及对应用户配置目录；处理微软商店虚拟文件路径。

从 `CODEX_HOME`（默认 `~/.codex`）以只读方式查询会话 SQLite 和 rollout 记录。统计状态保存在 `~/.codex/plugins/state/codex-native-stats`。不上传聊天、API Key 或统计数据；GitHub 更新和下载依赖需要联网。适用本机 Codex 会话；远程主机和 ChatGPT 云端会话可能没有本地统计记录。

## 构建与验证

详见 [开发与验证](docs/development.md) 和 [兼容性](docs/compatibility.md)。

```powershell
python build/build.py
python tests/test_distribution.py
node plugins/codex-native-stats/tests/test_speed.cjs
```

Python 3.11+ 可执行构建脚本；Windows x64 的 .NET Framework C# 编译器负责生成安装器与启动器。依赖下载自 Python、Node 官方站点与 PyPI，版本和 SHA256 固定在 `build/dependencies.lock.json`。运行时保留第三方许可，详见 [第三方说明](THIRD_PARTY_NOTICES.md)。
