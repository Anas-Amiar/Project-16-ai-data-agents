# AI Data Agents — Four Functional Tool-Using Agents

Four autonomous agents — **data analyst**, **data scientist**, **AI engineer**, and
**ML engineer** — built on a local agent framework: a real Anthropic tool-use loop with
sandboxed `bash` / `read_file` / `write_file` tools, so each agent writes and runs actual
Python in its own working directory until its deliverable is done.

The agent roles and system prompts come from Anthropic's Managed Agents cookbooks (included
in `notebooks/`); this repo makes them runnable **locally** with nothing but an API key —
no hosted platform, no beta access.

| Agent | Give it | Get back |
|---|---|---|
| `data-analyst` | any CSV | narrative `report.html` with 3+ interactive plotly charts |
| `data-scientist` | CSV with a target column | `report.html` + cross-validated `model.pkl` + `metrics.json` |
| `ai-engineer` | a markdown knowledge base | a complete RAG package with a pytest eval harness + quality gate |
| `ml-engineer` | CSV with a target column | FastAPI service + Dockerfile + passing test suite |

## Quick start

```bash
git clone https://github.com/Anas-Amiar/Project-16-ai-data-agents.git
cd "Project 16 - ai-data-agents"
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-ant-...   # https://platform.claude.com/settings/keys

# Run any agent on its bundled sample dataset:
python3 -m agentkit.run data-analyst
python3 -m agentkit.run data-scientist
python3 -m agentkit.run ai-engineer
python3 -m agentkit.run ml-engineer

# Or on your own data with your own task:
python3 -m agentkit.run data-analyst --data ~/my_sales.csv --task "Find the churn drivers"
```

Each run creates `runs/<agent>-<timestamp>/` containing the data, every script the agent
wrote, and its `outputs/` deliverables. You watch the agent work live — every tool call and
message is printed as it happens.

**No API key yet?** The framework itself is fully verified offline:

```bash
python3 -m pytest tests/ -q    # 5 tests: agent loop, sandboxing, timeouts, data, definitions
```

## How it works

```
agentkit/
  loop.py         The agent loop: send task -> model requests tools -> execute
                  locally -> feed results back -> repeat until done (max 40 turns)
  tools.py        Sandboxed tools: bash (cwd-scoped, 300s timeout, output capped),
                  write_file / read_file (path-escape rejected)
  definitions.py  The four agents: system prompts (from the cookbooks, retargeted
                  at the local sandbox) + default tasks + sample datasets
  run.py          CLI: pick an agent, optionally your data/task/model
data/
  make_samples.py Generates the four sample datasets (sales, churn, houses, FAQ)
tests/
  test_framework.py  Offline verification with a scripted FakeClient: proves the
                  loop executes tools end-to-end, the sandbox blocks path escapes,
                  bash errors/timeouts are handled, and all 4 agents are wired
notebooks/        The original Managed Agents cookbook notebooks (the hosted-
                  platform path — needs Managed Agents beta access)
```

### What makes the agents reliable

The system prompts carry the production discipline from the cookbooks:
- **data-scientist**: dummy baseline before any model, stratified 5-fold CV
  (mean ± std, never a single split), untouched holdout test set, calibrated claims,
  a limitations section
- **ai-engineer**: dependency-injected LLM client (`StubClient` so all evals run
  offline and deterministically), 10+ eval cases, and a hard quality gate —
  retrieval hit-rate ≥ 0.8 or keep iterating
- **ml-engineer**: mandatory self-verification — the agent must run its own pytest
  suite and only report success at exit code 0, with the summary line pasted

## Architecture decisions

**Why a local loop instead of the Managed Agents platform?**
The notebooks target Anthropic's hosted runtime (beta access + per-session containers).
The local loop needs only the standard Messages API: same system prompts, same agent
behavior, your machine as the sandbox. The `FakeClient` test proves the loop mechanics
without spending a token.

**Why sandbox the tools?**
An autonomous agent that can run bash needs a blast radius. Every run gets a fresh
directory; file tools reject paths that escape it; bash runs with a hard timeout and
capped output so a runaway command can't wedge the loop or flood the context.

**Why print every tool call?**
An agent you can't watch is an agent you can't debug or trust. The stream mirrors the
cookbook's event stream: every message and tool invocation, live.

## What's deliberately out of scope for v1

- Streaming token output (turn-level printing is enough to follow along)
- Parallel tool execution within a turn
- Cost/token tracking per run (add from `response.usage`)
- The Managed Agents path itself — the notebooks in `notebooks/` cover it when you
  have platform access
