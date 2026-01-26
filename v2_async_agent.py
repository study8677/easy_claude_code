#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v2_async_agent.py - 异步版 Agent（step 状态机 + 任务解耦）

核心理念：
- 请求只负责“投递任务”
- Agent 在后台按 step 运行，每步显式让出控制权
- 通过 task_id 查询状态（非阻塞）
"""

import asyncio
import os
import subprocess
import sys
import uuid
from pathlib import Path

from openai import AsyncOpenAI

# 工作目录固定为当前目录，避免越界
WORKDIR = Path.cwd()

# 创建客户端（OpenAI 兼容接口指向 DeepSeek）
client = AsyncOpenAI(
    api_key=os.getenv("DEEPSEEK_API_KEY", ""),
    base_url="https://api.deepseek.com/v1",
)

SYSTEM = f"""你是一名在目录 {WORKDIR} 里的编码 Agent。

异步规则：
- 每次 step 只做有限工作；需要工具时只执行一次工具调用然后返回。
- 每步结束必须让出控制权（由外层 loop 统一 await/yield）。
- 不要猜路径，不确定就先 ls/find。
- 修改要最小化，不要过度设计。"""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "bash",
            "description": "执行任意 Shell 命令，如 ls、find、grep、git、npm、python 等。",
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "要运行的 shell 命令"}
                },
                "required": ["command"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": "读取文件内容（UTF-8）。可选 limit 只读前 N 行。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对路径"},
                    "limit": {"type": "integer", "description": "最多读取的行数"},
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file",
            "description": "写入文件（创建或覆盖），自动创建父目录。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对路径"},
                    "content": {"type": "string", "description": "写入的全文内容"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "edit_file",
            "description": "对文件做精确替换：用 new_text 替换第一次出现的 old_text。",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "相对路径"},
                    "old_text": {"type": "string", "description": "待替换的原文（需精确匹配）"},
                    "new_text": {"type": "string", "description": "替换后的文本"},
                },
                "required": ["path", "old_text", "new_text"],
            },
        },
    },
]


def safe_path(p: str) -> Path:
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径越界：{p}")
    return path


def run_bash(command: str) -> str:
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: 危险命令已拦截"

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=WORKDIR,
            capture_output=True,
            text=True,
            timeout=60,
        )
        output = (result.stdout + result.stderr).strip()
        return output[:50000] if output else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: 命令超时 (60s)"
    except Exception as e:
        return f"Error: {e}"


def run_read(path: str, limit: int | None = None) -> str:
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... (还有 {len(text.splitlines()) - limit} 行)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    try:
        fp = safe_path(path)
        content = fp.read_text()
        if old_text not in content:
            return f"Error: 未找到要替换的内容 ({path})"
        new_content = content.replace(old_text, new_text, 1)
        fp.write_text(new_content)
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


async def execute_tool(name: str, args: dict) -> str:
    if name == "bash":
        return await asyncio.to_thread(run_bash, args["command"])
    if name == "read_file":
        return await asyncio.to_thread(run_read, args["path"], args.get("limit"))
    if name == "write_file":
        return await asyncio.to_thread(run_write, args["path"], args["content"])
    if name == "edit_file":
        return await asyncio.to_thread(run_edit, args["path"], args["old_text"], args["new_text"])
    return f"Unknown tool: {name}"


class AsyncAgent:
    def __init__(self, user_prompt: str):
        self.done = False
        self.state = {"status": "running", "step": 0, "answer": ""}
        self.messages = [
            {"role": "system", "content": SYSTEM},
            {"role": "user", "content": user_prompt},
        ]

    async def step(self):
        """单步执行：一次模型调用 + （可选）一次工具调用。"""
        self.state["step"] += 1

        response = await client.chat.completions.create(
            model=os.getenv("DEEPSEEK_MODEL", "deepseek-chat"),
            messages=self.messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        reply = response.choices[0].message

        # 没有工具调用 => 结束
        if not reply.tool_calls:
            self.state["status"] = "finished"
            self.state["answer"] = reply.content or ""
            self.done = True
            self.messages.append({"role": "assistant", "content": reply.content or ""})
            return

        # 有工具调用：执行一次并回填
        self.messages.append({
            "role": "assistant",
            "content": reply.content or "",
            "tool_calls": reply.tool_calls,
        })

        import json
        for tc in reply.tool_calls:
            args = json.loads(tc.function.arguments)
            output = await execute_tool(tc.function.name, args)
            self.messages.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output,
            })


async def agent_loop(agent: AsyncAgent):
    while not agent.done:
        await agent.step()
        await asyncio.sleep(0)  # 显式让出控制权


TASKS: dict[str, AsyncAgent] = {}


def submit_task(prompt: str) -> str:
    task_id = str(uuid.uuid4())
    agent = AsyncAgent(prompt)
    TASKS[task_id] = agent
    asyncio.create_task(agent_loop(agent))
    return task_id


def get_status(task_id: str) -> dict:
    agent = TASKS.get(task_id)
    if not agent:
        return {"error": "task not found"}
    return agent.state


async def repl():
    print(f"Mini Claude Code v2 (async) - {WORKDIR}")
    print("命令：run <prompt> | status <task_id> | exit\n")

    while True:
        user_input = input("You: ").strip()
        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit", "q"}:
            break

        if user_input.startswith("run "):
            prompt = user_input[4:].strip()
            task_id = submit_task(prompt)
            print(f"task_id: {task_id}")
            continue

        if user_input.startswith("status "):
            task_id = user_input[7:].strip()
            print(get_status(task_id))
            continue

        print("未知命令，请用: run <prompt> | status <task_id> | exit")


if __name__ == "__main__":
    try:
        asyncio.run(repl())
    except KeyboardInterrupt:
        pass
