"""
The agent loop: send the task, execute tool calls locally, feed results
back, repeat until the model stops asking for tools (or max_turns).

Works with any client exposing `.messages.create(...)` in the Anthropic
SDK shape — the real Anthropic client, or tests' FakeClient.
"""

from pathlib import Path

from agentkit.tools import TOOL_SCHEMAS, execute_tool

DEFAULT_MODEL = "claude-sonnet-4-6"
MAX_TURNS = 40


def run_agent(client, system_prompt: str, task: str, workdir: Path,
              model: str = DEFAULT_MODEL, max_turns: int = MAX_TURNS,
              verbose: bool = True) -> str:
    """Runs the loop; returns the agent's final text message."""
    workdir.mkdir(parents=True, exist_ok=True)
    messages = [{"role": "user", "content": task}]
    final_text = ""

    for turn in range(max_turns):
        response = client.messages.create(
            model=model, max_tokens=8000,
            system=system_prompt, tools=TOOL_SCHEMAS, messages=messages,
        )

        # Collect text + tool calls from this turn
        tool_results = []
        assistant_content = []
        for block in response.content:
            if block.type == "text":
                final_text = block.text
                if verbose and block.text.strip():
                    print(f"  [agent] {block.text[:200]}")
                assistant_content.append({"type": "text", "text": block.text})
            elif block.type == "tool_use":
                if verbose:
                    preview = str(block.input)[:80]
                    print(f"  [tool ] {block.name}: {preview}")
                assistant_content.append({
                    "type": "tool_use", "id": block.id,
                    "name": block.name, "input": block.input,
                })
                result = execute_tool(block.name, block.input, workdir)
                tool_results.append({
                    "type": "tool_result", "tool_use_id": block.id, "content": result,
                })

        if response.stop_reason != "tool_use":
            return final_text

        messages.append({"role": "assistant", "content": assistant_content})
        messages.append({"role": "user", "content": tool_results})

    return final_text + "\n[stopped: max_turns reached]"
