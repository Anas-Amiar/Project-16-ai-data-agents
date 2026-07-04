"""
Offline verification of the agent framework — no API key needed.

A FakeClient plays the model's role with a scripted tool-use sequence:
write a script, run it, read its output, then finish.  If this test
passes, the loop, tool execution, sandboxing, and turn-taking all work;
the real Anthropic client drops into the exact same interface.
"""

import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).parent.parent))

from agentkit.loop import run_agent
from agentkit.tools import execute_tool


def _text(t):
    return SimpleNamespace(type="text", text=t)


def _tool(id, name, input):
    return SimpleNamespace(type="tool_use", id=id, name=name, input=input)


class FakeClient:
    """Scripted 'model': writes a python script, runs it, reads the result."""

    def __init__(self):
        self.turn = 0
        self.seen_tool_results = []
        self.messages = self  # so client.messages.create resolves

    def create(self, **kwargs):
        # record tool results the loop fed back
        last = kwargs["messages"][-1]
        if isinstance(last.get("content"), list):
            for block in last["content"]:
                if isinstance(block, dict) and block.get("type") == "tool_result":
                    self.seen_tool_results.append(block["content"])

        self.turn += 1
        if self.turn == 1:
            return SimpleNamespace(stop_reason="tool_use", content=[
                _text("Writing the analysis script."),
                _tool("t1", "write_file", {
                    "path": "analyze.py",
                    "content": "print(sum(range(10)))\n"
                               "open('outputs/result.txt', 'w').write('45')\n"
                               "import os; os.makedirs('outputs', exist_ok=True)"}),
            ])
        if self.turn == 2:
            return SimpleNamespace(stop_reason="tool_use", content=[
                _tool("t2", "bash", {"command": "mkdir -p outputs && python3 analyze.py"}),
            ])
        if self.turn == 3:
            return SimpleNamespace(stop_reason="tool_use", content=[
                _tool("t3", "read_file", {"path": "outputs/result.txt"}),
            ])
        return SimpleNamespace(stop_reason="end_turn", content=[
            _text("Saved: outputs/result.txt")])


def test_loop_executes_tools_end_to_end(tmp_path):
    client = FakeClient()
    final = run_agent(client, "system", "task", tmp_path, verbose=False)

    assert final == "Saved: outputs/result.txt"
    assert (tmp_path / "analyze.py").exists()
    assert (tmp_path / "outputs" / "result.txt").read_text() == "45"
    # the bash run's stdout (45) came back as a tool result
    assert any("45" in r for r in client.seen_tool_results)


def test_sandbox_rejects_path_escape(tmp_path):
    result = execute_tool("write_file", {"path": "../escape.txt", "content": "x"}, tmp_path)
    assert result.startswith("ERROR")
    assert not (tmp_path.parent / "escape.txt").exists()


def test_bash_timeout_and_errors(tmp_path):
    result = execute_tool("bash", {"command": "exit 3"}, tmp_path)
    assert "exit code 3" in result
    result = execute_tool("read_file", {"path": "nope.txt"}, tmp_path)
    assert result.startswith("ERROR")


def test_sample_data_generators(tmp_path):
    from data.make_samples import MAKERS, ensure
    for name in MAKERS:
        p = ensure(name)
        assert p.exists() and p.stat().st_size > 100


def test_agent_definitions_complete():
    from agentkit.definitions import AGENTS
    assert set(AGENTS) == {"data-analyst", "data-scientist", "ai-engineer", "ml-engineer"}
    for name, spec in AGENTS.items():
        assert "{data}" in spec["default_task"]
        assert "outputs" in spec["system"]


def test_git_guard_denies_by_default(tmp_path):
    import agentkit.tools as tools
    for cmd in ["git push origin main", "gh repo create x --public",
                "git reset --hard HEAD~3", "rm -rf /tmp/x"]:
        result = execute_tool("bash", {"command": cmd}, tmp_path)
        assert result.startswith("DENIED"), f"not guarded: {cmd}"
    # normal git commands are NOT guarded
    result = execute_tool("bash", {"command": "git status"}, tmp_path)
    assert not result.startswith("DENIED")


def test_git_guard_approval_hook(tmp_path):
    import agentkit.tools as tools
    original = tools.APPROVAL_HOOK
    try:
        tools.APPROVAL_HOOK = lambda cmd: True   # human approves
        result = execute_tool("bash", {"command": "git push --dry-run 2>&1 || true"}, tmp_path)
        assert not result.startswith("DENIED")

        tools.APPROVAL_HOOK = lambda cmd: "DENIED: human rejected this command."
        result = execute_tool("bash", {"command": "git push origin main"}, tmp_path)
        assert result.startswith("DENIED")
    finally:
        tools.APPROVAL_HOOK = original


def test_broadened_role_prompts():
    from agentkit.definitions import AGENTS
    for name, spec in AGENTS.items():
        assert "ANY" in spec["system"], f"{name} prompt not broadened"
        assert "Engineering practices" in spec["system"]
