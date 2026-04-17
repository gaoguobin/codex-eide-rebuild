# codex-eide-rebuild

`codex-eide-rebuild` 提供两部分能力：GitHub 可安装的 Codex skill、Windows Python runner。它会直接触发 EIDE 的构建链路，并把完整结果以单个 JSON 返回给 Agent。

## 安装

主入口：

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md`

备用入口：

```powershell
python install-skill-from-github.py --repo gaoguobin/codex-eide-rebuild --path skills/eide-rebuild
```

第一次安装通常会有一次权限批准。安装后重启 Codex。

## 升级

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md
```

升级会更新本地 repo，并强制重装 bridge VSIX。升级后重启 Codex。

## 卸载

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md
```

卸载会移除 skill、本地 repo、bridge 扩展和相关本地状态。卸载后重启 Codex。

## 自然语言入口

安装完成后，Codex 可以用下面这类表达自动触发编译：

- `你自己编译验证下对不对`
- `帮我编译确认一下`
- `先 rebuild 看结果`
- `用 EIDE 编一下`

也支持显式入口：

- `EIDE rebuild C:\work\demo\project.code-workspace`
- `EIDE subagent rebuild C:\work\demo\project.code-workspace`

## 行为

- 解析 `.code-workspace` 或只包含一个工作区文件的工程目录
- 复用已打开的目标 VS Code 工作区
- 在缺少活跃桥接时自动打开工作区
- 自动安装仓库内置 VSIX 到默认 VS Code profile
- 调用 `eide.project.rebuild`
- 通过 EIDE 构建产物判定完成
- 输出纯文本协议和完整 `compiler.log`

## 开发

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File .\runtime\bridge\build-vsix.ps1
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

## 目录

- `.codex/`：面向 Codex 的安装、升级、卸载文档
- `runtime/`：共享运行时
- `skills/eide-rebuild/`：Codex skill
- `integrations/claude-code/`：Claude Code 第二阶段模板
- `scripts/`：同步和维护脚本
