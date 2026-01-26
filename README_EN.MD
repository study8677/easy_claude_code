# easy_claude_code

English Version | [中文版](./README.MD)

## Project Description
`easy_claude_code` is a minimalist educational project designed to implement the core logic of an AI Agent with the simplest possible code. It mimics the fundamental working principles of Claude Code: **Model Thinking -> Tool Calling -> Automated Iterative Loop**. Through this project, you can build your own AI assistant capable of manipulating local files, executing system commands, and implementing safety guardrails, thereby transforming "Agent concepts" into "engineering intuition."

---

### Project Philosophy
Great minimal demos already exist (`nanocode`, `learn-claude-code`), but comprehension ≠ intuition. This repo is for **building the full loop yourself**—Model thinks → calls tools → observes → decides again. We strip everything to the bone so you see clearly: *the model is the decision-maker; your code just supplies tools and a loop.*

### Current state (kept in sync with code)
- `easy_cil.py`: command-running agent with safety blacklist, exit-code return, output truncation, and blocks for interactive TUIs (vim/top/less) plus rm/sudo style danger.
- `v1_basic_agent.py`: ~200-line teaching agent exposing 4 function tools (bash/read_file/write_file/edit_file), defaults to DeepSeek `deepseek-chat`.
- `v2_async_agent.py`: async agent (task decoupling + step state machine); submit returns task_id, poll status anytime.
- Env config: `DEEPSEEK_API_KEY` / `DEEPSEEK_MODEL`; missing keys are detected and warned.

### Quick start
```bash
pip install openai python-dotenv
export DEEPSEEK_API_KEY=your_key   # or put in .env
python v1_basic_agent.py
```
Async version (task decoupling + status polling):
```bash
python v2_async_agent.py
# run <prompt>
# status <task_id>
```
Try prompts:
```
You: list current directory
You: read README_EN.MD first 40 lines
You: create demo.txt with hello world
```

### Features
- **Core agent loop**: model autonomously chains tool calls until done.
- **Local tool access**: run shell, read/write files, surgical edits.
- **Safety guardrails**: dangerous-command confirmation, output truncation, timeouts.
- **Multi-turn memory**: tool results are fed back so the model can iterate.

### Who is it for?
- Newcomers who want to grok Claude Code / Cursor Agent flow quickly.
- Engineers needing a “runnable, hackable, readable” minimal agent baseline.
- Students/hackers experimenting with local tool-use loops on their own box.
