# codex-eide-rebuild

`codex-eide-rebuild` 提供 Windows Python runner 和 Agent skill，用于触发 EIDE 构建链路并把完整结果以单个 JSON 返回。同时支持 Codex 和 Claude Code。

## 安装

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/INSTALL.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/INSTALL.md
```

Agent 会按安装文档完成安装、运行 `doctor`、回报 JSON 结果。`doctor.ok=true` 之后重启 Agent。

## 升级

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UPDATE.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UPDATE.md
```

## 卸载

### Codex

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/.codex/UNINSTALL.md
```

### Claude Code

```text
Fetch and follow instructions from https://raw.githubusercontent.com/gaoguobin/codex-eide-rebuild/main/integrations/claude-code/UNINSTALL.md
```

## 自然语言入口

安装完成后，Agent 可以用下面这类表达自动触发编译：

- `你自己编译验证下对不对`
- `帮我编译确认一下`
- `先 rebuild 看结果`
- `用 EIDE 编一下`

也支持显式入口：

- `EIDE rebuild C:\work\demo\project.code-workspace`
- `EIDE subagent rebuild C:\work\demo\project.code-workspace`
- `/eide-rebuild C:\work\demo\project.code-workspace`（Claude Code 斜杠命令）

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

## 输出协议

```json
{
  "ok": true,
  "errorCode": "OK",
  "targets": [
    {
      "name": "Debug",
      "ok": true
    }
  ]
}
```

## 目录

```text
.codex/             面向 Codex 的安装、升级、卸载文档
runtime/
  python/          共享 Python runner
  tests/           单元测试和仓库审计
skills/
  eide-rebuild/    可从 GitHub 安装的 Codex skill
integrations/
  claude-code/     Claude Code 安装文档、command 和 agent 模板
scripts/
  sync_skill_runtime.py
```

## 开发

同步 runtime 并运行测试：

```powershell
python .\scripts\sync_skill_runtime.py --copy
python .\scripts\sync_skill_runtime.py --check
python -m unittest discover -s .\runtime\tests -p "test_*.py"
```

## 安全和隐私

本仓只使用脱敏示例和通用路径。运行时测试和 smoke 检查使用 mock 数据。安全问题报告请参考 `SECURITY.md`。

## 上游参考

本项目自动化调用上游 EIDE 项目的 Embedded IDE for VS Code 扩展构建链路。
