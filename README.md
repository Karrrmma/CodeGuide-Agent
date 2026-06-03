# CodeGuide-Agent

A tool-calling AI agent that answers questions about any codebase — grounded in the actual source files, not guesses.

Point it at a project folder and ask things like *"How does authentication work?"* or *"Where are API routes defined?"*. The agent uses OpenAI function calling to explore the repository with real tools (list, search, read), then answers with references to the specific files it inspected.

---

## How it works

CodeGuide-Agent gives an LLM three safe, read-only tools over a target project and lets it decide which to call:

| Tool | What it does |
|------|--------------|
| `list_files` | Lists project files, skipping unsafe/generated folders (`.git`, `node_modules`, `venv`, `dist`, etc.) |
| `search_code` | Searches the codebase for a keyword/phrase, returning file + line + matching text |
| `read_file` | Reads a specific file's contents |

The agent runs an **OpenAI function-calling loop** (up to 6 tool steps per question): it searches to narrow down, reads the files that matter, then synthesizes a grounded answer. A system prompt enforces that it only makes claims it has verified with the tools — reducing hallucinated, unsupported answers.

**Safety by design:**
- **Project-boundary validation** — `read_file` resolves paths and refuses anything outside the target project directory.
- **Ignore-list filtering** — generated/sensitive folders are never listed or read.
- **Read-only** — the agent inspects code; it never modifies your files.

## Quickstart

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure your API key
cp .env.example .env
# then edit .env and add your OpenAI API key

# 3. Run
python agent.py
```

You'll be prompted for a project path, then you can chat with the agent about that codebase. Type `exit` to quit.

```
Enter the project path: /path/to/some/repo

CodeGuide-Agent is ready. Ask about this codebase.
Type 'exit' to quit.

You: How does the login flow work?
```

## Configuration

| Env var | Default | Purpose |
|---------|---------|---------|
| `OPENAI_API_KEY` | — | Required. Your OpenAI API key. |
| `OPENAI_MODEL` | `gpt-4.1-mini` | Model used for the agent loop. |

## Project structure

```
agent.py            # Agent loop: OpenAI function calling + tool dispatch
tools.py            # The three tools + path-safety helpers
prompts/system.md   # Agent role and grounding rules
prompts/workflow.md # Step-by-step answering strategy
requirements.txt
```

## Requirements

- Python 3.9+
- An OpenAI API key

## License

MIT
