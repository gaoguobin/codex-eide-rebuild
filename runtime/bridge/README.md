# EIDE Rebuild CLI Bridge

This bridge extension exposes one local rebuild endpoint per EIDE workspace.

## Responsibilities

- Register the active workspace through a local JSON registration file
- Validate that `cl.eide` is present and active
- Execute `eide.project.rebuild`
- Detect build completion from EIDE artifacts
- Return the target name, result status, and `compiler.log` path
