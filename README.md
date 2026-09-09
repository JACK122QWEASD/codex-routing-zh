# Codex Task Router

**Route the boring subtasks to a cheap model. Keep the hard ones on your main model.**

A set of routing rules that runs inside Codex (ChatGPT desktop app or CLI). Give it a task, and it
splits the work into subtasks, scores each one on a 9-dimension rubric, sends the cheap ones to a
cheap model in parallel, and keeps anything genuinely hard for itself.

No plugin, no code changes to Codex. Markdown rules plus two small helper scripts.

[中文版](./README.zh-CN.md)

---

## Why

Most real tasks are a mix. Buried inside a "refactor this module" request are ten mechanical
subtasks — renames, comment blocks, boilerplate tests — that don't need a frontier model at all.

Send all of that to your main model and you pay full price for work a cheap model handles
just as well.

---

## Requirements

| | |
|---|---|
| Codex | Desktop or CLI, **0.122+** (that release dropped non-Responses protocols) |
| OS | Unix shell — scripts use `grep` / `sed` / `chmod`. Windows: use WSL |
| Python | 3.7+ (JSON assembly only; **no `tomllib` dependency**) |
| Node | Optional, for `node --check` / `node --test` verification |
| Cheap model | Anything with a Chat Completions endpoint |

Every model name and endpoint in this repo is an **example**. The rules are vendor-agnostic.

## Getting started

### 1. Install

```bash
git clone https://github.com/JACK122QWEASD/codex-routing.git
cd codex-routing
./install.sh
```

`install.sh` writes the entry file to `~/.codex/AGENTS.md` (so every Codex session picks it up, in
any directory) and generates `.route-state.json` and `~/.codex/config.toml` from templates.

### 2. Point it at your models

Edit `~/.codex/config.toml`:

```toml
model = "your-strong-model"
model_provider = "your-provider"

[model_providers.your-provider]
name = "Strong"
base_url = "https://your-endpoint/v1"
env_key = "YOUR_API_KEY"
```

> Never commit a key to this repo. Use `env_key` with an environment variable, or put it in
> `~/.codex/config.toml` with `chmod 600` — that file is outside version control.

### 3. Use it

Restart Codex (on desktop: `Cmd+Q` fully, then reopen) and start a new conversation.

It opens with three configuration questions:

```
[Setup 1/3] Enter routed mode?
[Setup 2/3] Subtask granularity?
[Setup 3/3] Confirm strong / cheap models
```

Then it prints a dispatch plan and **waits for you to say "go"** before touching anything.

---

## Layout

```
agent.md            Full routing protocol (loaded on demand)
rubric.md           9-dimension rubric + coding-task routing rules (read when scoring)
weak-channel.md     Cheap-model call channel + batch dispatch script (read when dispatching)
prompts.md          Prompt templates for the cheap model (read when dispatching)
tools/merge.py      Merges results into files
tools/roundtrip.py  Round-trip verification
examples/           Config templates
install.sh          Installer
```

The design point: only a ~60-line entry file loads every round. Everything else is read on demand,
which is what keeps per-round token cost down.

---

## How routing works

### Scoring

Nine dimensions — verifiability, context radius, reasoning depth, tool need, decision freedom,
failure cost, ambiguity, output size, domain dependency — each scored 0–4, weighted into a
**difficulty score 0–100**, mapped to L1–L5, then passed through 7 hard gates.

### Tiers

| Tier | Handles | Notes |
|---|---|---|
| **S strong** | L4/L5 | Your main session model |
| **M mid** | L3 | Coding tasks may drop to cheap (see `rubric.md` §6) |
| **W cheap** | L1/L2 | Cheap model, called over HTTP, not through Codex |

### Dispatch checklist (every box, or it's a violation)

```
Before   □ Use a template from prompts.md (don't improvise)
         □ Canary probe (if it fails, escalate)
         □ Self-contained script
During   □ One parallel batch + wait
         □ Verify by exit code, not by reading content
         □ Round-trip check (reversible tasks, zero tokens)
         □ Merge via merge.py
         □ Spot-check N items
After    □ Closing report
```

### Fallback

Retry once → retry serially → escalate a tier → strong model takes over. If ≥50% of a batch fails,
treat it as a provider outage and downgrade the whole batch. **Every fallback must appear in the
closing report** — no silent downgrades.

---

## Swapping in your own models

One file, `.route-state.json`:

```json
{
  "strong_model": "your-strong-model",
  "cheap_model": "your-cheap-model",
  "cheap_no_think": true
}
```

- **The strong tier must support the Responses protocol** (Codex 0.122+ requires it).
- **The cheap tier is called over plain HTTP** and only needs Chat Completions.
- If your cheap model is a reasoning model, **turn thinking off** (`cheap_no_think: true`).
  Otherwise ~88% of tokens go to reasoning instead of the answer.

---

## FAQ

**Q: Desktop app says "Missing environment variable"?**
Apps launched from the Dock don't inherit shell variables. Either put the key in
`~/.codex/config.toml` as `experimental_bearer_token` (chmod 600), or run
`launchctl setenv KEY value` and restart the app.

**Q: It just started working without asking me anything.**
Check the entry file: `ls -l ~/.codex/AGENTS.md`. Codex reads instructions at global → repo root →
subdirectory. A desktop conversation outside your project directory only sees the global layer.

**Q: Does it work on Codex CLI?**
Yes, but CLI runs are non-interactive, so it declares config, prints the plan, and executes
(see `agent.md` §0.5).

---

## License

MIT
