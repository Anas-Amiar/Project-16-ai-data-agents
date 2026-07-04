"""
Local tool implementations for the agent loop.

Every tool executes inside a per-run working directory (the sandbox):
relative paths resolve there, absolute paths outside it are rejected, and
bash commands run with the workdir as cwd and a hard timeout.
"""

import re
import subprocess
from pathlib import Path

BASH_TIMEOUT_SECONDS = 300
MAX_OUTPUT_CHARS = 20_000

# Commands with outward-facing or destructive consequences require human
# approval.  The approval hook is set by the CLI (--allow-git wires an
# interactive prompt); the default denies with an explanation the agent
# can relay.
GUARDED_COMMAND = re.compile(
    r"\bgit\s+push|\bgh\s+repo\s+(create|delete)|\bgit\s+remote\s+add|"
    r"\bgit\s+reset\s+--hard|\bgit\s+clean|rm\s+-rf\s+[./~]", re.IGNORECASE)


def _deny_guarded(command: str) -> str:
    return ("DENIED: this command requires human approval and the run was not "
            "started with --allow-git. Continue with local work only.")


APPROVAL_HOOK = _deny_guarded  # replaced by run.py when --allow-git is set

TOOL_SCHEMAS = [
    {
        "name": "bash",
        "description": "Run a shell command in the working directory. Use for running "
                       "python scripts, pytest, listing files, installing nothing "
                       "(packages are preinstalled).",
        "input_schema": {
            "type": "object",
            "properties": {"command": {"type": "string"}},
            "required": ["command"],
        },
    },
    {
        "name": "write_file",
        "description": "Write a text file at a path relative to the working directory. "
                       "Creates parent directories automatically.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}, "content": {"type": "string"}},
            "required": ["path", "content"],
        },
    },
    {
        "name": "read_file",
        "description": "Read a text file at a path relative to the working directory.",
        "input_schema": {
            "type": "object",
            "properties": {"path": {"type": "string"}},
            "required": ["path"],
        },
    },
]


def _resolve(workdir: Path, path: str) -> Path:
    p = (workdir / path).resolve()
    if not str(p).startswith(str(workdir.resolve())):
        raise ValueError(f"path escapes the working directory: {path}")
    return p


def _truncate(text: str) -> str:
    if len(text) > MAX_OUTPUT_CHARS:
        return text[:MAX_OUTPUT_CHARS] + f"\n...[truncated {len(text) - MAX_OUTPUT_CHARS} chars]"
    return text


def execute_tool(name: str, tool_input: dict, workdir: Path) -> str:
    try:
        if name == "bash":
            cmd = tool_input["command"]
            if GUARDED_COMMAND.search(cmd):
                verdict = APPROVAL_HOOK(cmd)
                if verdict is not True:
                    return verdict if isinstance(verdict, str) else \
                        "DENIED: human rejected this command."
            result = subprocess.run(
                tool_input["command"], shell=True, cwd=workdir,
                capture_output=True, text=True, timeout=BASH_TIMEOUT_SECONDS)
            out = result.stdout + (("\n[stderr]\n" + result.stderr) if result.stderr else "")
            return _truncate(out or f"(no output, exit code {result.returncode})")

        if name == "write_file":
            p = _resolve(workdir, tool_input["path"])
            p.parent.mkdir(parents=True, exist_ok=True)
            p.write_text(tool_input["content"])
            return f"wrote {len(tool_input['content'])} chars to {tool_input['path']}"

        if name == "read_file":
            p = _resolve(workdir, tool_input["path"])
            return _truncate(p.read_text())

        return f"unknown tool: {name}"
    except subprocess.TimeoutExpired:
        return f"ERROR: command timed out after {BASH_TIMEOUT_SECONDS}s"
    except Exception as e:
        return f"ERROR: {type(e).__name__}: {e}"
