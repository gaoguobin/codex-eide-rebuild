# codex-eide-rebuild

`codex-eide-rebuild` 提供两部分能力：GitHub 可安装的 Codex skill、Windows Python runner。它会直接触发 EIDE 的构建链路，并把完整结果以单个 JSON 返回给 Agent。

## 安装

给工程师的一句话：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md
```

安装入口：

`Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md`

备用入口：

```powershell
python install-skill-from-github.py --repo gaoguobin/codex-eide-rebuild --path skills/eide-rebuild
```

第一次安装通常会有一次权限批准。Agent 会按 `INSTALL.md` 完成安装、运行 `doctor`、回报 JSON 结果。`doctor.ok=true` 之后重启 Codex。

## 升级

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md
```

升级会更新本地 repo，并刷新 direct-builder 运行时。升级后重启 Codex。

## 卸载

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md
```

卸载会移除 skill、本地 repo，并清理旧版 bridge 安装留下的本地状态。卸载后重启 Codex。

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
- 读取当前工程的 `.eide/eide.yml` 和相关配置
- 现场生成 `builder.params`
- 自动发现环境里最新的 EIDE 扩展、模型/工具目录、`unify_builder` 和 `dotnet`
- 当 `.code-workspace` 提供 GCC 安装配置时，按工程配置匹配 GCC
- 调用 `dotnet exec --roll-forward Major <unify_builder.dll> -p <builder.params>`
- 把完整结果以单个 JSON 输出给 Agent
- 编译步骤 60 秒无响应时返回 `STEP_TIMEOUT`
- `doctor.toolChecks` 会结构化报告环境检查失败原因

## 开发

```powershell
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
