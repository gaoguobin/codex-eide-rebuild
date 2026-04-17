from __future__ import annotations

import io
import json
import os
import shutil
import subprocess
import sys
import unittest
import uuid
from contextlib import contextmanager
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock


RUNTIME_PYTHON = Path(__file__).resolve().parents[1] / "python"
TEST_TMP_ROOT = Path(__file__).resolve().parents[2] / ".tmp" / "tests"
if str(RUNTIME_PYTHON) not in sys.path:
    sys.path.insert(0, str(RUNTIME_PYTHON))

import eide_rebuild
from eide_rebuild import builder_params as builder_params_module


@contextmanager
def make_temp_dir() -> str:
    TEST_TMP_ROOT.mkdir(parents=True, exist_ok=True)
    temp_dir = TEST_TMP_ROOT / f"tmp-{uuid.uuid4().hex}"
    temp_dir.mkdir(parents=True, exist_ok=False)
    try:
        yield str(temp_dir)
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


class ProjectResolutionTests(unittest.TestCase):
    def test_accepts_workspace_file_when_eide_yml_exists(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            workspace_file = project_dir / "demo.code-workspace"
            workspace_file.write_text("{}", encoding="utf-8")
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text("name: demo\ntargets: {Debug: {}}\n", encoding="utf-8")

            result = eide_rebuild.resolve_project_input(str(workspace_file))

            self.assertEqual(result.project_root, project_dir.resolve())
            self.assertEqual(result.workspace_path, workspace_file.resolve().as_posix())
            self.assertEqual(result.eide_yml_path, (eide_dir / "eide.yml").resolve())

    def test_accepts_project_root_without_workspace_file_when_eide_yml_exists(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text("name: demo\ntargets: {Debug: {}}\n", encoding="utf-8")

            result = eide_rebuild.resolve_project_input(str(project_dir))

            self.assertEqual(result.project_root, project_dir.resolve())
            self.assertEqual(result.workspace_path, "")
            self.assertEqual(result.eide_yml_path, (eide_dir / "eide.yml").resolve())

    def test_accepts_project_root_with_single_workspace_file(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            workspace_file = project_dir / "demo.code-workspace"
            workspace_file.write_text("{}", encoding="utf-8")
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text("name: demo\ntargets: {Debug: {}}\n", encoding="utf-8")

            result = eide_rebuild.resolve_project_input(str(project_dir))

            self.assertEqual(result.workspace_path, workspace_file.resolve().as_posix())

    def test_rejects_multiple_workspace_files_for_project_root(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text("name: demo\ntargets: {Debug: {}}\n", encoding="utf-8")
            (project_dir / "a.code-workspace").write_text("{}", encoding="utf-8")
            (project_dir / "b.code-workspace").write_text("{}", encoding="utf-8")

            with self.assertRaises(RuntimeError):
                eide_rebuild.resolve_project_input(str(project_dir))


class EideModelTests(unittest.TestCase):
    def test_discovers_all_targets_from_eide_yml(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder: {name: <virtual_root>, files: [], folders: []}
targets:
  Debug: {toolchain: GCC, toolchainConfigMap: {GCC: {options: {}, cpuType: Cortex-M33, scatterFilePath: linker.ld}}}
  Release: {toolchain: GCC, toolchainConfigMap: {GCC: {options: {}, cpuType: Cortex-M33, scatterFilePath: linker.ld}}}
''',
                encoding="utf-8",
            )

            model = eide_rebuild.load_eide_model(project_dir / ".eide" / "eide.yml")

            self.assertEqual(model.project_name, "demo")
            self.assertEqual(model.target_names, ["Debug", "Release"])


class BuilderParamsTests(unittest.TestCase):
    def test_collect_sources_respects_virtual_subtree_exclude_and_binary_extensions(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.c").write_text("int main(void) { return 0; }\n", encoding="utf-8")
            (project_dir / "src" / "keep.a").write_text("archive\n", encoding="utf-8")
            (project_dir / "src" / "keep.o").write_text("object\n", encoding="utf-8")
            (project_dir / "src" / "generated").mkdir()
            (project_dir / "src" / "generated" / "skip.c").write_text("int skip(void) { return 0; }\n", encoding="utf-8")
            (project_dir / "libs").mkdir()
            (project_dir / "libs" / "keep.lib").write_text("library\n", encoding="utf-8")
            (project_dir / "objs").mkdir()
            (project_dir / "objs" / "keep.obj").write_text("object\n", encoding="utf-8")
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder:
  name: <virtual_root>
  files: []
  folders:
    - name: src
      files:
        - { path: src/main.c }
        - { path: src/keep.a }
        - { path: src/keep.o }
      folders:
        - name: generated
          files:
            - { path: src/generated/skip.c }
          folders: []
    - name: libs
      files:
        - { path: libs/keep.lib }
      folders: []
    - name: objs
      files:
        - { path: objs/keep.obj }
      folders: []
targets:
  Debug:
    toolchain: GCC
    excludeList:
      - <virtual_root>/src/generated
    cppPreprocessAttrs: { incList: [], libList: [], defineList: [USE_FULL_LL_DRIVER] }
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        floatingPointHardware: none
        archExtensions: ""
        scatterFilePath: linker.ld
        options:
          global: {}
          linker:
            output-format: elf
''',
                encoding="utf-8",
            )

            model = eide_rebuild.load_eide_model(eide_dir / "eide.yml")
            debug_target = model.payload["targets"]["Debug"]

            source_list = builder_params_module.collect_sources(
                model.payload["virtualFolder"],
                debug_target["excludeList"],
            )

            self.assertEqual(
                source_list,
                [
                    "libs/keep.lib",
                    "objs/keep.obj",
                    "src/keep.a",
                    "src/keep.o",
                    "src/main.c",
                ],
            )

    def test_generate_builder_params_builds_full_shape_with_cpp_and_source_params(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (project_dir / "src").mkdir()
            (project_dir / "src" / "main.cpp").write_text("int main() { return 0; }\n", encoding="utf-8")
            (project_dir / "src" / "helper.c").write_text("int helper(void) { return 0; }\n", encoding="utf-8")
            (project_dir / "src" / "skip").mkdir()
            (project_dir / "src" / "skip" / "dead.c").write_text("int dead(void) { return 0; }\n", encoding="utf-8")
            (project_dir / "libs").mkdir()
            (project_dir / "libs" / "driver.a").write_text("archive\n", encoding="utf-8")
            (project_dir / "objs").mkdir()
            (project_dir / "objs" / "startup.obj").write_text("object\n", encoding="utf-8")
            (project_dir / "linker.ld").write_text("MEMORY {}\n", encoding="utf-8")
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder:
  name: <virtual_root>
  files: []
  folders:
    - name: src
      files:
        - { path: src/main.cpp }
        - { path: src/helper.c }
      folders:
        - name: skip
          files:
            - { path: src/skip/dead.c }
          folders: []
    - name: libs
      files:
        - { path: libs/driver.a }
      folders: []
    - name: objs
      files:
        - { path: objs/startup.obj }
      folders: []
targets:
  Debug:
    toolchain: GCC
    excludeList:
      - <virtual_root>/src/skip
    cppPreprocessAttrs:
      incList: [include, config]
      libList: [libs]
      defineList: [USE_FULL_LL_DRIVER, DEBUG]
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        floatingPointHardware: single
        archExtensions: "+fp"
        scatterFilePath: linker.ld
        options:
          global:
            misc-control: keep
          beforeBuildTasks:
            - name: generate version
              command: python Scripts/get_version.py
          linker:
            output-format: elf
          afterBuildTasks:
            - name: pack image
              command: python Scripts/pack_image.py
''',
                encoding="utf-8",
            )
            (eide_dir / "files.options.yml").write_text(
                '''
options:
  Debug:
    files:
      src/main.cpp:
        custom:
          optimize: O2
''',
                encoding="utf-8",
            )

            params = eide_rebuild.generate_builder_params(project_dir, "Debug", "C:/EIDE", "C:/gcc-arm")

            self.assertEqual(
                set(params.keys()),
                {
                    "alwaysInBuildSources",
                    "buildMode",
                    "defines",
                    "dumpPath",
                    "env",
                    "incDirs",
                    "libDirs",
                    "name",
                    "options",
                    "outDir",
                    "rootDir",
                    "showRepathOnLog",
                    "sourceList",
                    "sourceParams",
                    "sysPaths",
                    "target",
                    "threadNum",
                    "toolchain",
                    "toolchainCfgFile",
                    "toolchainLocation",
                },
            )
            self.assertEqual(params["name"], "demo")
            self.assertEqual(params["target"], "Debug")
            self.assertEqual(params["toolchain"], "GCC")
            self.assertEqual(params["toolchainLocation"], "C:/gcc-arm")
            self.assertEqual(params["toolchainCfgFile"], "C:/EIDE/arm.gcc.model.json")
            self.assertEqual(params["buildMode"], "fast|multhread")
            self.assertTrue(params["showRepathOnLog"])
            self.assertEqual(params["threadNum"], os.cpu_count() or 4)
            self.assertEqual(params["rootDir"], project_dir.as_posix())
            self.assertEqual(params["dumpPath"], "build/Debug")
            self.assertEqual(params["outDir"], "build/Debug")
            self.assertEqual(params["incDirs"], ["include", "config"])
            self.assertEqual(params["libDirs"], ["libs"])
            self.assertEqual(params["defines"], ["USE_FULL_LL_DRIVER", "DEBUG"])
            self.assertEqual(params["options"]["global"]["toolPrefix"], "arm-none-eabi-")
            self.assertEqual(params["options"]["global"]["microcontroller-cpu"], "cortex-m33-sp")
            self.assertEqual(params["options"]["global"]["microcontroller-fpu"], "cortex-m33-sp")
            self.assertEqual(params["options"]["global"]["microcontroller-float"], "cortex-m33-sp")
            self.assertEqual(params["options"]["global"]["$arch-extensions"], "+fp")
            self.assertEqual(params["options"]["global"]["$clang-arch-extensions"], "")
            self.assertEqual(params["options"]["global"]["$armlink-arch-extensions"], "")
            self.assertEqual(params["options"]["linker"]["$toolName"], "g++")
            self.assertEqual(params["options"]["linker"]["link-scatter"], [f"{project_dir.as_posix()}/linker.ld"])
            self.assertEqual(params["options"]["beforeBuildTasks"][0]["name"], "generate version")
            self.assertEqual(params["options"]["afterBuildTasks"][0]["name"], "pack image")
            self.assertEqual(
                params["sourceList"],
                [
                    "libs/driver.a",
                    "objs/startup.obj",
                    "src/helper.c",
                    "src/main.cpp",
                ],
            )
            self.assertEqual(
                params["sourceParams"],
                {
                    "src/main.cpp": {
                        "custom": {
                            "optimize": "O2",
                        }
                    }
                },
            )
            self.assertEqual(params["alwaysInBuildSources"], [])
            self.assertEqual(params["sysPaths"], [])
            self.assertEqual(
                set(params["env"].keys()),
                {
                    "ChipName",
                    "ChipPackDir",
                    "ConfigName",
                    "ExecutableName",
                    "OutDir",
                    "OutDirBase",
                    "OutDirRoot",
                    "ProjectName",
                    "ProjectRoot",
                    "SYS_DirSep",
                    "SYS_DirSeparator",
                    "SYS_EOL",
                    "SYS_PathSep",
                    "SYS_PathSeparator",
                    "SYS_Platform",
                    "ToolchainRoot",
                    "workspaceFolder",
                    "workspaceFolderBasename",
                },
            )
            self.assertEqual(params["env"]["ProjectName"], "demo")
            self.assertEqual(params["env"]["ConfigName"], "Debug")
            self.assertEqual(params["env"]["ProjectRoot"], project_dir.as_posix())
            self.assertEqual(params["env"]["ToolchainRoot"], "C:/gcc-arm")
            self.assertEqual(params["env"]["workspaceFolder"], project_dir.as_posix())
            self.assertEqual(params["env"]["workspaceFolderBasename"], project_dir.name)
            self.assertEqual(params["env"]["OutDir"], f"{project_dir.as_posix()}/build/Debug")
            self.assertEqual(params["env"]["OutDirRoot"], "build")
            self.assertEqual(params["env"]["OutDirBase"], "build/Debug")
            self.assertEqual(params["env"]["ExecutableName"], f"{project_dir.as_posix()}/build/Debug/demo")
            self.assertEqual(params["env"]["SYS_Platform"], "windows" if os.name == "nt" else "linux")
            self.assertEqual(params["env"]["SYS_DirSep"], "\\" if os.name == "nt" else "/")
            self.assertEqual(params["env"]["SYS_DirSeparator"], "\\" if os.name == "nt" else "/")
            self.assertEqual(params["env"]["SYS_PathSep"], ";" if os.name == "nt" else ":")
            self.assertEqual(params["env"]["SYS_PathSeparator"], ";" if os.name == "nt" else ":")
            self.assertEqual(params["env"]["SYS_EOL"], "\n")

    def test_write_builder_params_writes_expected_format(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            params = {
                "name": "demo",
                "target": "Debug",
            }

            output_path = eide_rebuild.write_builder_params(project_dir, "Debug", params)

            self.assertEqual(output_path, project_dir / "build" / "Debug" / "builder.params")
            content = output_path.read_text(encoding="utf-8")
            self.assertTrue(content.endswith("\n}"))
            self.assertIn('\n    "name": "demo"', content)
            self.assertEqual(json.loads(content), params)

    def test_pre_handle_options_uses_linker_lib_for_library_output(self) -> None:
        options = {
            "global": {},
            "linker": {
                "output-format": "lib",
            },
        }

        builder_params_module._pre_handle_options(
            options,
            ["src/main.c"],
            "Cortex-M33",
            "none",
            "",
            "linker.ld",
            Path("D:/demo"),
        )

        self.assertEqual(options["linker"]["$toolName"], "gcc")
        self.assertEqual(options["linker"]["$use"], "linker-lib")

    def test_source_exts_match_plan_contract(self) -> None:
        self.assertEqual(
            builder_params_module.SOURCE_EXTS,
            {".c", ".cpp", ".cc", ".cxx", ".s", ".a", ".o", ".lib", ".obj"},
        )

    def test_generate_builder_params_raises_key_error_for_unknown_target(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder: {name: <virtual_root>, files: [], folders: []}
targets:
  Debug:
    toolchain: GCC
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        scatterFilePath: linker.ld
        options: {global: {}, linker: {output-format: elf}}
''',
                encoding="utf-8",
            )

            with self.assertRaises(KeyError) as error:
                eide_rebuild.generate_builder_params(project_dir, "Release", "C:/EIDE", "C:/gcc-arm")

            self.assertEqual(error.exception.args[0], "Release")

    def test_generate_builder_params_normalizes_mixed_slash_toolchain_cfg_file(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (project_dir / "linker.ld").write_text("MEMORY {}\n", encoding="utf-8")
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder: {name: <virtual_root>, files: [], folders: []}
targets:
  Debug:
    toolchain: GCC
    cppPreprocessAttrs: { incList: [], libList: [], defineList: [] }
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        floatingPointHardware: none
        archExtensions: ""
        scatterFilePath: linker.ld
        options:
          global: {}
          linker:
            output-format: elf
''',
                encoding="utf-8",
            )

            params = eide_rebuild.generate_builder_params(project_dir, "Debug", r"C:\EIDE/", "C:/gcc-arm")

            self.assertEqual(params["toolchainCfgFile"], "C:/EIDE/arm.gcc.model.json")


class JsonProtocolTests(unittest.TestCase):
    def test_main_emits_single_json_object(self) -> None:
        result = eide_rebuild.RunResult(
            schema_version="1",
            ok=True,
            exit_code=0,
            error_code="OK",
            message="",
            mode="rebuild-all",
            platform="windows",
            workspace_path="C:/work/demo.code-workspace",
            project_root="C:/work",
            project_name="demo",
            started_at="2026-04-16T08:13:04Z",
            finished_at="2026-04-16T08:13:06Z",
            duration_ms=2000,
            summary={"discovered": 1, "passed": 1, "failed": 0},
            target_names=["Debug"],
            transcript="full transcript",
            targets=[],
        )

        payload = eide_rebuild.render_json_result(result)
        parsed = json.loads(payload)

        self.assertEqual(parsed["errorCode"], "OK")
        self.assertEqual(parsed["summary"]["passed"], 1)
        self.assertIn("targets", parsed)

    def test_result_contract_includes_target_step_and_artifact_details(self) -> None:
        step = eide_rebuild.StepResult(
            kind="unify-builder",
            name="build Debug",
            ok=True,
            exit_code=0,
            error_code="OK",
            message="",
            started_at="2026-04-16T08:13:04Z",
            finished_at="2026-04-16T08:13:05Z",
            duration_ms=1000,
            stdout="[ INFO ] start building\n",
            stderr="",
            command=["dotnet", "unify_builder.dll"],
            cwd="C:/work/demo",
        )
        target = eide_rebuild.TargetResult(
            name="Debug",
            index=1,
            total=1,
            ok=True,
            exit_code=0,
            error_code="OK",
            message="",
            started_at="2026-04-16T08:13:04Z",
            finished_at="2026-04-16T08:13:06Z",
            duration_ms=2000,
            builder_params_path="build/Debug/builder.params",
            builder_params_summary={"sourceCount": 103},
            compiler_log_path="build/Debug/compiler.log",
            compiler_log="[ DONE ] build successfully !\n",
            stack_report_json_path="build/Debug/stack_report.json",
            stack_report_html_path="build/Debug/stack_report.html",
            source_stats={"totalFiles": 103, "jobs": 8},
            memory=[{"name": "FLASH", "used": 139076, "total": 184320, "percent": 75.45, "unit": "B"}],
            artifacts=[{"path": "build/Debug/app.bin", "kind": "bin", "size": 139104}],
            transcript="target transcript",
            steps=[step],
        )

        result = eide_rebuild.build_run_result(
            workspace_path="C:/work/demo.code-workspace",
            project_root=Path("C:/work/demo"),
            project_name="demo",
            platform_name="windows",
            target_names=["Debug"],
            started_at="2026-04-16T08:13:04Z",
            finished_at="2026-04-16T08:13:06Z",
            duration_ms=2000,
            targets=[target],
            transcript="full transcript",
        )

        payload = json.loads(eide_rebuild.render_json_result(result))

        self.assertEqual(payload["schemaVersion"], "1")
        self.assertTrue(payload["ok"])
        self.assertEqual(payload["summary"], {"discovered": 1, "passed": 1, "failed": 0})
        self.assertEqual(payload["targets"][0]["builderParamsSummary"]["sourceCount"], 103)
        self.assertEqual(payload["targets"][0]["memory"][0]["name"], "FLASH")
        self.assertEqual(payload["targets"][0]["artifacts"][0]["kind"], "bin")
        self.assertEqual(payload["targets"][0]["steps"][0]["kind"], "unify-builder")
        self.assertEqual(payload["targets"][0]["steps"][0]["command"], ["dotnet", "unify_builder.dll"])

    def test_write_run_result_writes_same_json_payload(self) -> None:
        with make_temp_dir() as temp_dir:
            result = eide_rebuild.build_run_result(
                workspace_path="",
                project_root=Path(temp_dir),
                project_name="demo",
                platform_name="windows",
                target_names=[],
                started_at="2026-04-16T08:13:04Z",
                finished_at="2026-04-16T08:13:04Z",
                duration_ms=0,
                targets=[],
                transcript="",
            )
            output_path = Path(temp_dir) / "build" / "rebuild_result.json"

            eide_rebuild.write_run_result(output_path, result)

            self.assertEqual(json.loads(output_path.read_text(encoding="utf-8")), json.loads(eide_rebuild.render_json_result(result)))


class ToolDiscoveryTests(unittest.TestCase):
    def test_prefers_explicit_unify_builder_override(self) -> None:
        with make_temp_dir() as temp_dir:
            tool_path = Path(temp_dir) / "unify_builder.dll"
            tool_path.write_text("tool", encoding="utf-8")

            with mock.patch.dict(os.environ, {"EIDE_REBUILD_UNIFY_BUILDER": str(tool_path)}, clear=False):
                result = eide_rebuild.find_unify_builder()

            self.assertEqual(result, tool_path.resolve().as_posix())

    def test_resolves_unify_builder_from_eide_tools_dir(self) -> None:
        with make_temp_dir() as temp_dir:
            tool_path = Path(temp_dir) / "unify_builder.dll"
            tool_path.write_text("tool", encoding="utf-8")

            with mock.patch.dict(os.environ, {"EIDE_REBUILD_EIDE_TOOLS_DIR": temp_dir}, clear=False):
                result = eide_rebuild.find_unify_builder()

            self.assertEqual(result, tool_path.resolve().as_posix())

    def test_discovers_eide_layout_from_vscode_extension_root(self) -> None:
        with make_temp_dir() as temp_dir:
            extensions_root = Path(temp_dir) / "extensions"
            extension_root = extensions_root / "cl.eide-3.26.7"
            models_dir = extension_root / "res" / "data" / "models"
            unify_builder = extension_root / "res" / "tools" / "win32" / "unify_builder" / "unify_builder.dll"
            utils_dir = extension_root / "res" / "tools" / "win32" / "utils"
            models_dir.mkdir(parents=True)
            unify_builder.parent.mkdir(parents=True)
            utils_dir.mkdir(parents=True)
            (models_dir / "arm.gcc.model.json").write_text("{}", encoding="utf-8")
            unify_builder.write_text("tool", encoding="utf-8")
            (utils_dir / "python3.cmd").write_text("@echo off\r\npython.exe %*\r\n", encoding="utf-8")

            with mock.patch.dict(
                os.environ,
                {
                    "EIDE_REBUILD_VSCODE_EXTENSIONS_ROOT": str(extensions_root),
                },
                clear=False,
            ):
                self.assertEqual(eide_rebuild.find_eide_tools_dir(), models_dir.resolve().as_posix())
                self.assertEqual(eide_rebuild.find_unify_builder(), unify_builder.resolve().as_posix())
                self.assertEqual(eide_rebuild.find_eide_utils_dir(), utils_dir.resolve().as_posix())

    def test_prefers_unify_builder_exe_on_windows_layout(self) -> None:
        with make_temp_dir() as temp_dir:
            extensions_root = Path(temp_dir) / "extensions"
            extension_root = extensions_root / "cl.eide-3.26.7"
            unify_dir = extension_root / "res" / "tools" / "win32" / "unify_builder"
            models_dir = extension_root / "res" / "data" / "models"
            unify_dir.mkdir(parents=True)
            models_dir.mkdir(parents=True)
            (models_dir / "arm.gcc.model.json").write_text("{}", encoding="utf-8")
            (unify_dir / "unify_builder.exe").write_text("exe", encoding="utf-8")
            (unify_dir / "unify_builder.dll").write_text("dll", encoding="utf-8")

            with mock.patch.dict(os.environ, {"EIDE_REBUILD_VSCODE_EXTENSIONS_ROOT": str(extensions_root)}, clear=False):
                self.assertEqual(
                    eide_rebuild.find_unify_builder(),
                    (unify_dir / "unify_builder.exe").resolve().as_posix(),
                )

    def test_discovers_latest_toolchain_root_from_eide_tools_home(self) -> None:
        with make_temp_dir() as temp_dir:
            tools_root = Path(temp_dir) / "tools"
            old_root = tools_root / "xpack-arm-none-eabi-gcc-14.2.1-1.1" / "bin"
            new_root = tools_root / "xpack-arm-none-eabi-gcc-15.2.1-1.1" / "bin"
            old_root.mkdir(parents=True)
            new_root.mkdir(parents=True)
            (old_root / "arm-none-eabi-gcc.exe").write_text("gcc", encoding="utf-8")
            (new_root / "arm-none-eabi-gcc.exe").write_text("gcc", encoding="utf-8")

            with mock.patch.dict(
                os.environ,
                {
                    "EIDE_REBUILD_TOOLS_ROOT": str(tools_root),
                },
                clear=False,
            ):
                self.assertEqual(eide_rebuild.find_toolchain_root(), new_root.parent.resolve().as_posix())

    def test_build_process_env_prepends_utils_and_toolchain_bin(self) -> None:
        with make_temp_dir() as temp_dir:
            toolchain_root = Path(temp_dir) / "xpack-arm-none-eabi-gcc-15.2.1-1.1"
            toolchain_bin = toolchain_root / "bin"
            utils_dir = Path(temp_dir) / "utils"
            toolchain_bin.mkdir(parents=True)
            utils_dir.mkdir(parents=True)

            with mock.patch("eide_rebuild.tools.find_eide_utils_dir", return_value=utils_dir.resolve().as_posix()):
                env = eide_rebuild.build_process_env({"ProjectName": "demo"}, toolchain_root.resolve().as_posix())

            path_parts = env["PATH"].split(os.pathsep)
            self.assertEqual(path_parts[0], str(utils_dir.resolve()))
            self.assertEqual(path_parts[1], str(toolchain_bin.resolve()))
            self.assertEqual(env["ProjectName"], "demo")


class DoctorTests(unittest.TestCase):
    def test_doctor_reports_discovered_tools(self) -> None:
        with (
            mock.patch(
                "eide_rebuild.tools.check_pyyaml_dependency",
                return_value={"ok": True, "package": "PyYAML", "module": "yaml", "version": "6.0.2", "message": ""},
            ),
            mock.patch("eide_rebuild.tools.find_dotnet", return_value="C:/dotnet/dotnet.exe"),
            mock.patch("eide_rebuild.tools.find_eide_extension_dir", return_value="C:/EIDE/extension"),
            mock.patch("eide_rebuild.tools.find_eide_tools_dir", return_value="C:/EIDE/models"),
            mock.patch("eide_rebuild.tools.find_unify_builder", return_value="C:/EIDE/unify_builder.exe"),
            mock.patch("eide_rebuild.tools.find_toolchain_root", return_value="C:/gcc-arm"),
            mock.patch("eide_rebuild.tools.find_eide_utils_dir", return_value="C:/EIDE/utils"),
            mock.patch(
                "eide_rebuild.tools.check_unify_builder_runtime",
                return_value={"ok": True, "requiredFramework": "Microsoft.NETCore.App", "requiredVersion": "6.0.0"},
            ),
        ):
            result = eide_rebuild.run_doctor()

        self.assertTrue(result["ok"])
        self.assertEqual(result["tools"]["dotnet"], "C:/dotnet/dotnet.exe")
        self.assertEqual(result["tools"]["eideUtilsDir"], "C:/EIDE/utils")
        self.assertEqual(result["dependencies"]["pyyaml"]["version"], "6.0.2")
        self.assertEqual(result["runtime"]["requiredVersion"], "6.0.0")

    def test_doctor_reports_missing_unify_builder_runtime(self) -> None:
        with (
            mock.patch(
                "eide_rebuild.tools.check_pyyaml_dependency",
                return_value={"ok": True, "package": "PyYAML", "module": "yaml", "version": "6.0.2", "message": ""},
            ),
            mock.patch("eide_rebuild.tools.find_dotnet", return_value="C:/dotnet/dotnet.exe"),
            mock.patch("eide_rebuild.tools.find_eide_extension_dir", return_value="C:/EIDE/extension"),
            mock.patch("eide_rebuild.tools.find_eide_tools_dir", return_value="C:/EIDE/models"),
            mock.patch("eide_rebuild.tools.find_unify_builder", return_value="C:/EIDE/unify_builder.exe"),
            mock.patch("eide_rebuild.tools.find_toolchain_root", return_value="C:/gcc-arm"),
            mock.patch("eide_rebuild.tools.find_eide_utils_dir", return_value="C:/EIDE/utils"),
            mock.patch(
                "eide_rebuild.tools.check_unify_builder_runtime",
                return_value={
                    "ok": False,
                    "requiredFramework": "Microsoft.NETCore.App",
                    "requiredVersion": "6.0.0",
                    "message": "Missing Microsoft.NETCore.App 6.0 runtime.",
                },
            ),
        ):
            result = eide_rebuild.run_doctor()

        self.assertFalse(result["ok"])
        self.assertEqual(result["exitCode"], 3)
        self.assertEqual(result["errorCode"], "TOOL_NOT_FOUND")
        self.assertIn("6.0", result["message"])

    def test_doctor_reports_missing_pyyaml_dependency(self) -> None:
        with (
            mock.patch(
                "eide_rebuild.tools.check_pyyaml_dependency",
                return_value={
                    "ok": False,
                    "package": "PyYAML",
                    "module": "yaml",
                    "version": "",
                    "message": "PyYAML is required. Run `python -m pip install --user PyYAML`.",
                },
            ),
            mock.patch("eide_rebuild.tools.find_dotnet", return_value="C:/dotnet/dotnet.exe"),
            mock.patch("eide_rebuild.tools.find_eide_extension_dir", return_value="C:/EIDE/extension"),
            mock.patch("eide_rebuild.tools.find_eide_tools_dir", return_value="C:/EIDE/models"),
            mock.patch("eide_rebuild.tools.find_unify_builder", return_value="C:/EIDE/unify_builder.exe"),
            mock.patch("eide_rebuild.tools.find_toolchain_root", return_value="C:/gcc-arm"),
            mock.patch("eide_rebuild.tools.find_eide_utils_dir", return_value="C:/EIDE/utils"),
            mock.patch(
                "eide_rebuild.tools.check_unify_builder_runtime",
                return_value={"ok": True, "requiredFramework": "Microsoft.NETCore.App", "requiredVersion": "6.0.0"},
            ),
        ):
            result = eide_rebuild.run_doctor()

        self.assertFalse(result["ok"])
        self.assertEqual(result["exitCode"], 3)
        self.assertIn("PyYAML", result["message"])

    def test_main_supports_doctor_command(self) -> None:
        stdout_buffer = io.StringIO()
        with (
            mock.patch.object(
                eide_rebuild,
                "run_doctor",
                return_value={
                    "ok": True,
                    "exitCode": 0,
                    "errorCode": "OK",
                    "message": "",
                    "platform": "windows",
                    "tools": {},
                },
            ),
            redirect_stdout(stdout_buffer),
        ):
            exit_code = eide_rebuild.main(["doctor"])

        self.assertEqual(exit_code, 0)
        self.assertTrue(json.loads(stdout_buffer.getvalue())["ok"])


class ExecutorTests(unittest.TestCase):
    def test_records_step_stdout_stderr_command_cwd_and_transcript(self) -> None:
        completed = subprocess.CompletedProcess(
            args=["dotnet", "unify_builder.dll"],
            returncode=0,
            stdout="[ INFO ] start building\n[DONE] build successfully !\n",
            stderr="",
        )

        with mock.patch("eide_rebuild.executor.subprocess.run", return_value=completed) as run_mock:
            step = eide_rebuild.run_step(
                kind="unify-builder",
                name="build Debug",
                command=["dotnet", "unify_builder.dll"],
                cwd=Path.cwd(),
            )

        self.assertTrue(step.ok)
        self.assertEqual(step.exit_code, 0)
        self.assertEqual(step.error_code, "OK")
        self.assertIn("start building", step.stdout)
        self.assertEqual(step.stderr, "")
        self.assertEqual(step.command, ["dotnet", "unify_builder.dll"])
        self.assertEqual(step.cwd, Path.cwd().resolve().as_posix())
        run_mock.assert_called_once()

    def test_build_unify_builder_command_uses_dotnet_exec_with_roll_forward(self) -> None:
        with make_temp_dir() as temp_dir:
            unify_root = Path(temp_dir)
            exe_path = unify_root / "unify_builder.exe"
            dll_path = unify_root / "unify_builder.dll"
            exe_path.write_text("exe", encoding="utf-8")
            dll_path.write_text("dll", encoding="utf-8")

            command = eide_rebuild.build_unify_builder_command(
                dotnet_path="C:/Program Files/dotnet/dotnet.exe",
                unify_builder_path=exe_path.as_posix(),
                builder_params_path="D:/repo/build/Debug/builder.params",
            )

        self.assertEqual(
            command,
            [
                "C:/Program Files/dotnet/dotnet.exe",
                "exec",
                "--roll-forward",
                "Major",
                dll_path.resolve().as_posix(),
                "-p",
                "D:/repo/build/Debug/builder.params",
                "--rebuild",
            ],
        )


class TargetExecutionTests(unittest.TestCase):
    def test_rebuild_target_collects_memory_artifacts_and_stack_reports(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            build_dir = project_dir / "build" / "Debug"
            build_dir.mkdir(parents=True)
            (project_dir / "linker.ld").write_text("MEMORY {}\n", encoding="utf-8")
            (build_dir / "compiler.log").write_text("[ DONE ] build successfully !\n", encoding="utf-8")
            (build_dir / "app.bin").write_bytes(b"abc")
            (build_dir / "stack_report.json").write_text('{"pct_guard": 67.19}', encoding="utf-8")
            (build_dir / "stack_report.html").write_text("<html></html>", encoding="utf-8")
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder:
  name: <virtual_root>
  files:
    - { path: main.c }
  folders: []
targets:
  Debug:
    toolchain: GCC
    cppPreprocessAttrs: { incList: [], libList: [], defineList: [] }
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        scatterFilePath: linker.ld
        options:
          global: {}
          linker: { output-format: elf }
''',
                encoding="utf-8",
            )
            step = eide_rebuild.StepResult(
                kind="unify-builder",
                name="build Debug",
                ok=True,
                exit_code=0,
                error_code="OK",
                message="",
                started_at="2026-04-16T08:13:04Z",
                finished_at="2026-04-16T08:13:05Z",
                duration_ms=1000,
                stdout=(
                    "[ INFO ] file statistics (incremental mode)\n"
                    "+---------+-----------+-----------+---------------+--------+\n"
                    "| C Files | Cpp Files | Asm Files | Lib/Obj Files | Totals |\n"
                    "+---------+-----------+-----------+---------------+--------+\n"
                    "| 99      | 0         | 1         | 3             | 103    |\n"
                    "+---------+-----------+-----------+---------------+--------+\n"
                    "[ INFO ] start compiling (jobs: 8) ...\n"
                    "Memory region         Used Size  Region Size  %age Used\n"
                    "             RAM:       37816 B        64 KB     57.70%\n"
                    "           FLASH:      139076 B       180 KB     75.45%\n"
                ),
                stderr="",
                command=["dotnet", "unify_builder.dll", "-p", "build/Debug/builder.params", "--rebuild"],
                cwd=project_dir.as_posix(),
            )

            with mock.patch("eide_rebuild.executor.run_step", return_value=step):
                target = eide_rebuild.rebuild_target(
                    project_root=project_dir,
                    project_name="demo",
                    target_name="Debug",
                    target_index=1,
                    target_total=1,
                    dotnet_path="C:/dotnet/dotnet.exe",
                    unify_builder_path="C:/EIDE/unify_builder.dll",
                    eide_tools_dir="C:/EIDE",
                    toolchain_root="C:/gcc-arm",
                )

            self.assertTrue(target.ok)
            self.assertEqual(target.error_code, "OK")
            self.assertEqual(target.compiler_log, "[ DONE ] build successfully !\n")
            self.assertTrue(target.stack_report_json_path.endswith("/build/Debug/stack_report.json"))
            self.assertTrue(target.stack_report_html_path.endswith("/build/Debug/stack_report.html"))
            self.assertEqual(target.artifacts[0]["kind"], "bin")
            self.assertEqual(target.source_stats["cFiles"], 99)
            self.assertEqual(target.source_stats["jobs"], 8)
            self.assertEqual(target.memory[0]["name"], "RAM")
            self.assertEqual(target.memory[1]["name"], "FLASH")
            self.assertEqual(target.steps[0].kind, "generate-builder-params")
            self.assertEqual(target.steps[1].kind, "unify-builder")

    def test_rebuild_target_marks_missing_compiler_log(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (project_dir / "linker.ld").write_text("MEMORY {}\n", encoding="utf-8")
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder: {name: <virtual_root>, files: [], folders: []}
targets:
  Debug:
    toolchain: GCC
    cppPreprocessAttrs: { incList: [], libList: [], defineList: [] }
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        scatterFilePath: linker.ld
        options:
          global: {}
          linker: { output-format: elf }
''',
                encoding="utf-8",
            )
            step = eide_rebuild.StepResult(
                kind="unify-builder",
                name="build Debug",
                ok=True,
                exit_code=0,
                error_code="OK",
                message="",
                started_at="2026-04-16T08:13:04Z",
                finished_at="2026-04-16T08:13:05Z",
                duration_ms=1000,
                stdout="",
                stderr="",
                command=["dotnet", "unify_builder.dll", "-p", "build/Debug/builder.params", "--rebuild"],
                cwd=project_dir.as_posix(),
            )

            with mock.patch("eide_rebuild.executor.run_step", return_value=step):
                target = eide_rebuild.rebuild_target(
                    project_root=project_dir,
                    project_name="demo",
                    target_name="Debug",
                    target_index=1,
                    target_total=1,
                    dotnet_path="C:/dotnet/dotnet.exe",
                    unify_builder_path="C:/EIDE/unify_builder.dll",
                    eide_tools_dir="C:/EIDE",
                    toolchain_root="C:/gcc-arm",
                )

            self.assertFalse(target.ok)
            self.assertEqual(target.exit_code, 8)
            self.assertEqual(target.error_code, "COMPILER_LOG_MISSING")


class TargetHookTests(unittest.TestCase):
    def test_rebuild_target_runs_unify_builder_once_for_hooked_project(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            build_dir = project_dir / "build" / "Debug"
            build_dir.mkdir(parents=True)
            builder_params_path = build_dir / "builder.params"
            builder_params_path.write_text("{}", encoding="utf-8")
            (build_dir / "compiler.log").write_text("[ DONE ] build successfully !\n", encoding="utf-8")
            params = {
                "toolchain": "GCC",
                "threadNum": 8,
                "sourceList": ["main.c"],
                "options": {
                    "beforeBuildTasks": [
                        {"name": "generate version", "command": "python ${ProjectName}.py"},
                        {"name": "disabled hook", "command": "echo skip", "disable": True},
                    ],
                    "afterBuildTasks": [
                        {"name": "pack image", "command": "echo ${OutDirBase}"},
                    ],
                },
                "env": {
                    "ProjectName": "demo",
                    "ConfigName": "Debug",
                    "OutDirBase": "build/Debug",
                    "workspaceFolder": project_dir.as_posix(),
                },
            }
            calls: list[tuple[str, str, object]] = []

            def fake_run_step(kind: str, name: str, command, cwd: Path, env=None):
                calls.append((kind, name, command))
                return eide_rebuild.StepResult(
                    kind=kind,
                    name=name,
                    ok=True,
                    exit_code=0,
                    error_code="OK",
                    message="",
                    started_at="2026-04-16T08:13:04Z",
                    finished_at="2026-04-16T08:13:05Z",
                    duration_ms=1,
                    stdout="ok\n",
                    stderr="",
                    command=[command] if isinstance(command, str) else list(command),
                    cwd=project_dir.as_posix(),
                )

            with (
                mock.patch("eide_rebuild.executor.generate_builder_params", return_value=params),
                mock.patch("eide_rebuild.executor.write_builder_params", return_value=builder_params_path),
                mock.patch("eide_rebuild.executor.run_step", side_effect=fake_run_step),
            ):
                target = eide_rebuild.rebuild_target(
                    project_root=project_dir,
                    project_name="demo",
                    target_name="Debug",
                    target_index=1,
                    target_total=1,
                    dotnet_path="C:/dotnet/dotnet.exe",
                    unify_builder_path="C:/EIDE/unify_builder.dll",
                    eide_tools_dir="C:/EIDE",
                    toolchain_root="C:/gcc-arm",
                )

            self.assertTrue(target.ok)
            self.assertEqual([step.kind for step in target.steps], ["generate-builder-params", "unify-builder"])
            self.assertEqual(len(calls), 1)
            self.assertEqual(calls[0][0], "unify-builder")

    def test_rebuild_target_marks_embedded_post_build_failure(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            build_dir = project_dir / "build" / "Debug"
            build_dir.mkdir(parents=True)
            builder_params_path = build_dir / "builder.params"
            builder_params_path.write_text("{}", encoding="utf-8")
            (build_dir / "compiler.log").write_text("[ DONE ] build successfully !\n", encoding="utf-8")
            params = {
                "toolchain": "GCC",
                "threadNum": 8,
                "sourceList": ["main.c"],
                "options": {
                    "beforeBuildTasks": [],
                    "afterBuildTasks": [{"name": "pack image", "command": "python pack.py"}],
                },
                "env": {"ProjectName": "demo", "ConfigName": "Debug", "OutDirBase": "build/Debug"},
            }

            def fake_run_step(kind: str, name: str, command, cwd: Path, env=None):
                return eide_rebuild.StepResult(
                    kind="unify-builder",
                    name="build Debug",
                    ok=True,
                    exit_code=0,
                    error_code="OK",
                    message="",
                    started_at="2026-04-16T08:13:04Z",
                    finished_at="2026-04-16T08:13:05Z",
                    duration_ms=1,
                    stdout=(
                        "[ INFO ] pre-build tasks ...\n\n"
                        ">> generate version\t\t[done]\n\n"
                        "[ INFO ] post-build tasks ...\n\n"
                        ">> pack image\t\t[failed]\n\n"
                        "ERROR: pack failed\n"
                    ),
                    stderr="",
                    command=[command] if isinstance(command, str) else list(command),
                    cwd=project_dir.as_posix(),
                )

            with (
                mock.patch("eide_rebuild.executor.generate_builder_params", return_value=params),
                mock.patch("eide_rebuild.executor.write_builder_params", return_value=builder_params_path),
                mock.patch("eide_rebuild.executor.run_step", side_effect=fake_run_step),
            ):
                target = eide_rebuild.rebuild_target(
                    project_root=project_dir,
                    project_name="demo",
                    target_name="Debug",
                    target_index=1,
                    target_total=1,
                    dotnet_path="C:/dotnet/dotnet.exe",
                    unify_builder_path="C:/EIDE/unify_builder.dll",
                    eide_tools_dir="C:/EIDE",
                    toolchain_root="C:/gcc-arm",
                )

            self.assertFalse(target.ok)
            self.assertEqual(target.exit_code, 4)
            self.assertEqual(target.error_code, "POST_BUILD_TASK_FAILED")
            self.assertEqual(target.message, "pack image failed inside unify_builder.")
            self.assertEqual([step.kind for step in target.steps], ["generate-builder-params", "unify-builder"])


class PackageExportsTests(unittest.TestCase):
    def test_package_exports_direct_builder_api(self) -> None:
        self.assertTrue(callable(eide_rebuild.main))
        self.assertTrue(callable(eide_rebuild.rebuild_target))
        self.assertTrue(callable(eide_rebuild.render_json_result))
        self.assertIs(eide_rebuild.ExitError, eide_rebuild.__dict__["ExitError"])

    def test_main_uses_package_rebuild_target_patch(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder: {name: <virtual_root>, files: [], folders: []}
targets:
  Debug:
    toolchain: GCC
    cppPreprocessAttrs: { incList: [], libList: [], defineList: [] }
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        scatterFilePath: linker.ld
        options: { global: {}, linker: {} }
''',
                encoding="utf-8",
            )
            target_result = eide_rebuild.TargetResult(
                name="Debug",
                index=1,
                total=1,
                ok=True,
                exit_code=0,
                error_code="OK",
                message="",
                started_at="2026-04-16T08:13:04Z",
                finished_at="2026-04-16T08:13:05Z",
                duration_ms=1000,
                builder_params_path=f"{project_dir.as_posix()}/build/Debug/builder.params",
                compiler_log_path=f"{project_dir.as_posix()}/build/Debug/compiler.log",
                compiler_log="[ DONE ] build successfully !\n",
                transcript="[1/1] Building: Debug\n",
            )
            stdout_buffer = io.StringIO()

            with (
                mock.patch.object(eide_rebuild, "find_dotnet", return_value="C:/dotnet/dotnet.exe"),
                mock.patch.object(eide_rebuild, "find_unify_builder", return_value="C:/EIDE/unify_builder.dll"),
                mock.patch.object(eide_rebuild, "find_eide_tools_dir", return_value="C:/EIDE"),
                mock.patch.object(eide_rebuild, "find_toolchain_root", return_value="C:/gcc-arm"),
                mock.patch.object(
                    eide_rebuild,
                    "check_unify_builder_runtime",
                    return_value={"ok": True, "requiredFramework": "Microsoft.NETCore.App", "requiredVersion": "6.0.0"},
                ),
                mock.patch.object(eide_rebuild, "rebuild_target", return_value=target_result) as rebuild_target,
                redirect_stdout(stdout_buffer),
            ):
                exit_code = eide_rebuild.main(["rebuild", str(project_dir)])

            self.assertEqual(exit_code, 0)
            rebuild_target.assert_called_once()
            self.assertEqual(json.loads(stdout_buffer.getvalue())["summary"]["passed"], 1)


class DirectBuilderFlowTests(unittest.TestCase):
    def test_main_rebuilds_all_targets_and_writes_json_file(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text(
                '''
name: demo
virtualFolder: {name: <virtual_root>, files: [], folders: []}
targets:
  Debug:
    toolchain: GCC
    cppPreprocessAttrs: { incList: [], libList: [], defineList: [] }
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        scatterFilePath: linker.ld
        options: { global: {}, linker: {} }
  Release:
    toolchain: GCC
    cppPreprocessAttrs: { incList: [], libList: [], defineList: [] }
    toolchainConfigMap:
      GCC:
        cpuType: Cortex-M33
        scatterFilePath: linker.ld
        options: { global: {}, linker: {} }
''',
                encoding="utf-8",
            )

            def make_target(name: str, index: int) -> eide_rebuild.TargetResult:
                return eide_rebuild.TargetResult(
                    name=name,
                    index=index,
                    total=2,
                    ok=True,
                    exit_code=0,
                    error_code="OK",
                    message="",
                    builder_params_path=f"{project_dir.as_posix()}/build/{name}/builder.params",
                    compiler_log_path=f"{project_dir.as_posix()}/build/{name}/compiler.log",
                    compiler_log="[ DONE ] build successfully !\n",
                    started_at="2026-04-16T08:13:04Z",
                    finished_at="2026-04-16T08:13:05Z",
                    duration_ms=1000,
                    transcript=f"[{index}/2] Building: {name}\n",
                    source_stats={"jobs": 8, "totalFiles": 103},
                    memory=[],
                    artifacts=[],
                    steps=[],
                )

            stdout_buffer = io.StringIO()

            with (
                mock.patch.object(eide_rebuild, "find_dotnet", return_value="C:/dotnet/dotnet.exe"),
                mock.patch.object(eide_rebuild, "find_unify_builder", return_value="C:/EIDE/unify_builder.dll"),
                mock.patch.object(eide_rebuild, "find_eide_tools_dir", return_value="C:/EIDE"),
                mock.patch.object(eide_rebuild, "find_toolchain_root", return_value="C:/gcc-arm"),
                mock.patch.object(
                    eide_rebuild,
                    "check_unify_builder_runtime",
                    return_value={"ok": True, "requiredFramework": "Microsoft.NETCore.App", "requiredVersion": "6.0.0"},
                ),
                mock.patch.object(eide_rebuild, "rebuild_target", side_effect=[make_target("Debug", 1), make_target("Release", 2)]),
                redirect_stdout(stdout_buffer),
            ):
                exit_code = eide_rebuild.main(["rebuild", str(project_dir)])

            payload = json.loads(stdout_buffer.getvalue())

            self.assertEqual(exit_code, 0)
            self.assertEqual(payload["summary"]["discovered"], 2)
            self.assertEqual(payload["summary"]["passed"], 2)
            self.assertEqual(payload["targets"][1]["name"], "Release")
            self.assertTrue((project_dir / "build" / "rebuild_result.json").exists())

class MainFlowTests(unittest.TestCase):
    def test_main_emits_error_json_when_tool_is_missing(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text("name: demo\ntargets: {Debug: {}}\n", encoding="utf-8")
            stdout_buffer = io.StringIO()

            with (
                mock.patch.object(eide_rebuild, "find_dotnet", side_effect=FileNotFoundError("dotnet")),
                redirect_stdout(stdout_buffer),
            ):
                exit_code = eide_rebuild.main(["rebuild", str(project_dir)])

            payload = json.loads(stdout_buffer.getvalue())
            self.assertEqual(exit_code, 3)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["errorCode"], "TOOL_NOT_FOUND")

    def test_main_emits_error_json_for_multiple_workspace_files(self) -> None:
        with make_temp_dir() as temp_dir:
            project_dir = Path(temp_dir)
            eide_dir = project_dir / ".eide"
            eide_dir.mkdir()
            (eide_dir / "eide.yml").write_text("name: demo\ntargets: {Debug: {}}\n", encoding="utf-8")
            (project_dir / "a.code-workspace").write_text("{}", encoding="utf-8")
            (project_dir / "b.code-workspace").write_text("{}", encoding="utf-8")
            stdout_buffer = io.StringIO()

            with redirect_stdout(stdout_buffer):
                exit_code = eide_rebuild.main(["rebuild", str(project_dir)])

            payload = json.loads(stdout_buffer.getvalue())
            self.assertEqual(exit_code, 2)
            self.assertFalse(payload["ok"])
            self.assertEqual(payload["errorCode"], "MULTIPLE_WORKSPACES")
