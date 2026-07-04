# AI Data Agents — the pitch

*A 2-minute walkthrough for presenting this project in an interview.*

## The 30-second version

"I took Anthropic's four Managed Agents cookbook roles — data analyst, data scientist, AI
engineer, ML engineer — and made them run locally on a framework I built: a real tool-use
agent loop against the Messages API, with sandboxed bash and file tools. Hand the data
scientist agent a CSV and it writes and runs its own Python — EDA, hypothesis tests, a
dummy baseline, cross-validated models — and hands back a report, a serialized model, and
honest metrics. The framework itself is verified offline with a scripted fake model, so I
can prove the loop, the sandboxing, and the failure handling work without spending a
single token."

## The problem, in plain terms

The cookbook notebooks are great but they target Anthropic's hosted Managed Agents
platform — beta access, per-session cloud containers, platform billing. If you just have
an API key, you can't run them. And an agent framework you can only test by paying for
live LLM calls is a framework you'll under-test.

## The idea

Split the problem in two:
1. **The loop is just software** — send task → model asks for tools → execute locally →
   return results → repeat. That's testable with a fake model that scripts a realistic
   tool sequence.
2. **The agent behavior lives in the system prompt** — the cookbooks' prompts carry the
   real discipline (baselines, CV, eval gates, self-verifying test suites), so I kept
   them nearly verbatim, retargeted at a local sandbox.

## How I built it (in order, and why that order)

1. **Sandboxed tools** (`agentkit/tools.py`) — bash scoped to a per-run working directory
   with a 300s timeout and capped output; file tools that reject path escapes. Built
   first because an autonomous agent with shell access needs a blast radius before it
   needs anything else.

2. **The loop** (`agentkit/loop.py`) — the standard Anthropic tool-use pattern: read
   `tool_use` blocks, execute, append `tool_result` blocks, continue until
   `stop_reason != "tool_use"` or max turns. Works with anything exposing
   `.messages.create(...)` — the real client or a test fake.

3. **The offline verification** (`tests/test_framework.py`) — a `FakeClient` that plays
   the model with a scripted sequence: write a script, run it, read its output, finish.
   The test asserts the files exist, the script's stdout came back as a tool result, and
   the final message surfaced. Plus sandbox-escape, bash-failure, and timeout tests.
   Five tests, zero tokens.

4. **The four agent definitions** (`agentkit/definitions.py`) — the cookbook system
   prompts with two changes: outputs go to `./outputs/` instead of the platform mount
   path, and web-tool references removed (everything runs offline against local files).

5. **Sample data + CLI** (`data/make_samples.py`, `agentkit/run.py`) — the notebooks'
   datasets recreated (sales orders, churn with planted noise features, house prices,
   the Acme FAQ) so each agent runs out of the box; the CLI takes any CSV/markdown and
   task override.

## The result

- `python3 -m pytest tests/ -q` → **5 passed** with no API key: loop mechanics, sandbox
  enforcement, error handling, data generators, agent wiring
- `python3 -m agentkit.run <agent>` → the full live agent with every tool call streamed,
  as soon as `ANTHROPIC_API_KEY` is set
- Without a key, the CLI exits with exact instructions instead of a stack trace

## What I'd highlight if asked "what was the hardest design decision?"

Designing the loop against an interface instead of the Anthropic client directly. It
sounds like a small thing, but it's what makes the framework testable: the `FakeClient`
scripts a realistic multi-turn tool sequence, and if those tests pass, the only untested
component is the model itself — which is exactly the component I shouldn't be paying to
test in CI. It's the same dependency-injection pattern the AI-engineer agent's own system
prompt demands of the code *it* generates (StubClient vs AnthropicClient). The framework
practices what its agents preach.

## What I'd build next

- Cost and token tracking per run from `response.usage`
- An agent-chaining runner: data-scientist selects the model, its `metrics.json` feeds
  the ml-engineer's task prompt (the cookbook's suggested composition)
- Streaming output and parallel tool execution within a turn
- Run the same definitions on Managed Agents when platform access is available —
  the notebooks in `notebooks/` are ready

## Companion projects

This is the practical twin of my [Agent Orchestration System](
https://github.com/Anas-Amiar/Project-15-agent-orchestration): that project builds the
*coordination* layer (supervisor, reviewer, human-in-the-loop) with mock agents; this one
builds the *execution* layer — real LLM-driven agents doing real work with real tools.
Put together, they're the two halves of a production agent platform.
