from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass
class ProjectInput:
    project_root: Path
    workspace_path: str
    eide_yml_path: Path


def resolve_project_input(input_path: str) -> ProjectInput:
    path_obj = Path(input_path).expanduser().resolve()
    if not path_obj.exists():
        raise FileNotFoundError(input_path)

    if path_obj.is_file() and path_obj.suffix.lower() == ".code-workspace":
        project_root = path_obj.parent
        eide_yml = project_root / ".eide" / "eide.yml"
        if not eide_yml.exists():
            raise FileNotFoundError(str(eide_yml))
        return ProjectInput(
            project_root=project_root,
            workspace_path=str(path_obj).replace("\\", "/"),
            eide_yml_path=eide_yml,
        )

    if path_obj.is_dir():
        workspace_files = sorted(path_obj.glob("*.code-workspace"))
        if len(workspace_files) > 1:
            raise RuntimeError(f"Expected one workspace file in {path_obj}")
        eide_yml = path_obj / ".eide" / "eide.yml"
        if eide_yml.exists():
            workspace_path = str(workspace_files[0].resolve()).replace("\\", "/") if workspace_files else ""
            return ProjectInput(
                project_root=path_obj,
                workspace_path=workspace_path,
                eide_yml_path=eide_yml,
            )
        if len(workspace_files) == 1:
            raise FileNotFoundError(str(eide_yml))

    raise FileNotFoundError(input_path)
