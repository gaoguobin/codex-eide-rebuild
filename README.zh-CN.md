# codex-eide-rebuild

[![CI](https://github.com/gaoguobin/codex-eide-rebuild/actions/workflows/ci.yml/badge.svg)](https://github.com/gaoguobin/codex-eide-rebuild/actions/workflows/ci.yml)

面向 Codex 和 Claude Code 的 EIDE / Embedded IDE for VS Code 重建 Agent Skill。它通过 Windows-first Python runner 现场生成 `builder.params`，调用 EIDE `unify_builder`，并把编译日志、产物、内存占用、栈报告和环境诊断整理成单个 JSON 结果。

[English](README.md) · [Agent Skill](#agent-skill-和可发现性) · [安装](#安装) · [验证](#验证) · [输出协议](#输出协议) · [安全边界](#安全边界) · [Plugin readiness](#plugin-readiness) · [开发](#开发)

## 为什么需要

这个项目适合已经能在本机 EIDE 正常编译的固件工程，让 Agent 以同样的 rebuild 语义做验证。它避免依赖 VS Code bridge 注册链路，把 Agent 侧协议简化为：执行一个 runner，读取一个完整 JSON。

Agent 可以先跑 `doctor`，再 rebuild 所有 EIDE target，并从 JSON 里拿到失败步骤、compiler log、artifact、stack report 等定位信息。

## 核心能力

| 能力 | 含义 |
| --- | --- |
| Agent-ready JSON | 输出包含 `ok`、`errorCode`、target summary、日志、步骤、产物和 transcript 的完整 JSON。 |
| 新鲜 build parameters | 每次 rebuild 前读取 `.eide/eide.yml`、`.eide/env.ini`、`.eide/files.options.yml` 和 workspace GCC 配置生成 `builder.params`。 |
| EIDE rebuild 语义 | 调用 `dotnet exec --roll-forward Major <unify_builder.dll> -p <builder.params> --rebuild`。 |
| 工具自动发现 | 自动发现 EIDE extension tools、model files、`unify_builder`、`dotnet` 和 workspace 配置的 GCC root。 |
| 环境诊断 | `doctor` 输出结构化 `toolChecks`、PyYAML 状态和 .NET runtime probing 结果。 |
| 超时保护 | 编译步骤 60 秒超时后返回 `STEP_TIMEOUT`。 |
| Subagent 适配 | 长日志 rebuild 可以交给 worker subagent，主 Agent 只处理 JSON 结果。 |
| 同步护栏 | CI 校验 shared runtime 和 skill bundle 内副本保持一致。 |

## 兼容性

- Windows-first 工作流。
- Python 3.11+ 和 PyYAML。
- VS Code 中已安装 Embedded IDE for VS Code (`cl.eide`)。
- 本机存在与 EIDE `unify_builder` 兼容的 .NET runtime。
- EIDE 工程包含 `.code-workspace` 和 `.eide/eide.yml`。
- 当前仓库同时提供 Codex skill 安装入口和 Claude Code command/subagent 模板。

## Agent Skill 和可发现性

这个仓库包含一个 Agent Skill：

- Skill 名称：`eide-rebuild`
- Skill 路径：`skills/eide-rebuild/SKILL.md`
- 主要用途：让 Agent rebuild EIDE / Embedded IDE for VS Code 固件工程，并返回结构化 JSON 编译结果。
- 触发表达：`帮我编译确认一下`、`先 rebuild 看结果`、`EIDE rebuild C:\work\demo\project.code-workspace`、`/eide-rebuild C:\work\demo\project.code-workspace`。
- Runner 入口：`skills/eide-rebuild/scripts/eide_rebuild.py`
- 环境检查：`python skills/eide-rebuild/scripts/eide_rebuild.py doctor`

索引公开 GitHub 仓库 Agent Skills 的工具，包括 SkillsMP-style GitHub indexers，可以通过上面的路径发现这个 skill。仓库同时提供明确的 skill metadata、稳定 skill 路径和 `.codex-plugin/plugin.json` discovery metadata。

项目状态：社区 GitHub 项目，包含 Agent Skill 和预备的 Codex plugin metadata。不声明已被 SkillsMP 或 marketplace 收录，也不声明 OpenAI 官方身份。

## Plugin Readiness

Codex plugin 文档定义 `.codex-plugin/plugin.json` 为 plugin manifest，`skills/` 保持在 plugin root。当前仓库已经包含 `.codex-plugin/plugin.json`，并指向 `./skills/`，方便 plugin-aware 工具识别内置 skill。

当前正式支持的安装方式仍然是下面的 Codex-managed / Claude Code-managed 流程。plugin metadata 只用于发现和后续打包准备。运行时影响：无。hook 安装、权限变更、用户配置修改、后台服务启动、rebuild 行为变更都在范围外。

## 安装

### Codex

把这句话贴给 Codex：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md
```

安装流程会把仓库 clone 到 `~/.codex/codex-eide-rebuild`，安装 PyYAML，把 skill namespace 链接到 `~/.agents/skills`，并运行 `doctor`。

`doctor.ok=true` 后重启 Codex，让它重新扫描 skill。

### Claude Code

把这句话贴给 Claude Code：

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/INSTALL.md
```

Claude Code 集成会安装 command 和 subagent 模板。安装后运行 `/reload-plugins`。

## 更新

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UPDATE.md
```

更新 skill 文件后，Codex 需要重启，Claude Code 运行 `/reload-plugins`。

## 卸载

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UNINSTALL.md
```

## 验证

从已安装 skill 目录运行环境检查：

```powershell
python skills/eide-rebuild/scripts/eide_rebuild.py doctor
```

对 workspace 或工程目录执行 rebuild：

```powershell
python skills/eide-rebuild/scripts/eide_rebuild.py rebuild C:\work\demo\project.code-workspace
```

Agent 应按下面规则处理结果：

- 从 `stdout` 读取一个完整 JSON。
- `exitCode=0` 表示成功。
- `exitCode=6` 表示编译失败。
- 其它非零 exit code 表示环境、配置、runtime 或超时问题。
- 保留 `compilerLog`、`steps`、`artifacts`、`transcript` 供后续分析。

## 输出协议

```json
{
  "schemaVersion": "1",
  "ok": true,
  "exitCode": 0,
  "errorCode": "OK",
  "mode": "rebuild-all",
  "targets": [
    {
      "name": "Debug",
      "ok": true,
      "builderParamsPath": "C:/work/demo/build/Debug/builder.params",
      "compilerLogPath": "C:/work/demo/build/Debug/compiler.log",
      "artifacts": [
        {
          "path": "C:/work/demo/build/Debug/app.bin",
          "kind": "bin",
          "size": 139104
        }
      ]
    }
  ]
}
```

## 常用命令

Agent 应把 runner 当作事实来源：

```powershell
python skills/eide-rebuild/scripts/eide_rebuild.py doctor
python skills/eide-rebuild/scripts/eide_rebuild.py rebuild C:\work\demo\project.code-workspace
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

默认路径：

| 项目 | 路径 |
| --- | --- |
| Codex 安装仓库 | `~/.codex/codex-eide-rebuild` |
| Codex skill namespace | `~/.agents/skills/codex-eide-rebuild` |
| Skill 文件 | `skills/eide-rebuild/SKILL.md` |
| Runner 脚本 | `skills/eide-rebuild/scripts/eide_rebuild.py` |
| Rebuild 结果 | `<project>/build/rebuild_result.json` |
| Target compiler log | `<project>/<outDir>/<target>/compiler.log` |

## 安全边界

- Runner 在目标 workspace 内执行本地 EIDE rebuild 命令。
- Runner 会在工程输出目录写入生成的 `builder.params`、compiler log、artifact 和 `build/rebuild_result.json`。
- Runner 从 `.code-workspace`、`.eide/eide.yml`、`.eide/env.ini`、`.eide/files.options.yml` 读取工程配置。
- Runner 会执行 EIDE 工程里定义的 pre-build 和 post-build tasks，因为这些任务属于 EIDE build model。
- Runner 范围外：安装 VS Code extension、注册 VS Code bridge、修改源码、修改 Codex 配置、修改 VS Code settings、安装 hooks。
- 安装器会把本仓 `skills/` 目录链接到用户的 Agent skill 目录，并为当前用户安装 PyYAML。
- 仓内 runtime tests 和 smoke checks 使用脱敏示例和 mock 数据。

## 目录

```text
.codex/              Codex 安装、更新、卸载文档
.codex-plugin/       Codex plugin discovery manifest
runtime/
  python/            共享 Python runner
  tests/             单元测试和仓库审计
skills/
  eide-rebuild/      Agent Skill 和 bundled runner copy
integrations/
  claude-code/       Claude Code 安装文档、command 和 subagent 模板
scripts/
  sync_skill_runtime.py
```

## 开发

同步 runtime 到 skill bundle 并运行测试：

```powershell
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
python -m compileall runtime\python scripts
```

## 安全和隐私

本仓只使用脱敏示例和通用路径。运行时测试和 smoke 检查使用 mock 数据。安全问题报告请参考 [SECURITY.md](SECURITY.md)。

## 上游参考

本项目自动化调用上游 EIDE 项目的 Embedded IDE for VS Code 扩展构建链路。

## License

MIT - see [LICENSE](LICENSE).
