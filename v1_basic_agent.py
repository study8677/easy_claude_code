#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
v1_basic_agent.py - 极简 Claude Code 思路演示（约 200 行）

核心理念：“模型自己就是 Agent”
=============================
把花哨的进度条、权限系统都拿掉，留下的就是：
   循环（model -> tool -> result -> model）直到模型觉得可以停。

传统助手：
    用户 -> 模型 -> 文本回复

Agent 模式：
    用户 -> 模型 -> [工具 -> 结果]* -> 最终回复
                          ^_____|
星号 * 的含义：模型会反复调用工具，直到它认为任务完成。

重点：决策者是模型。代码只负责把“工具箱 + 循环”摆好。

四个核心工具（覆盖 90% 编程场景）
-------------------------------
| 工具       | 用途            | 示例                     |
|------------|-----------------|--------------------------|
| bash       | 跑任意命令      | npm install, git status  |
| read_file  | 读文件内容      | 查看 src/index.ts        |
| write_file | 创建/覆盖文件   | 写 README.md             |
| edit_file  | 局部替换        | 修改某个函数             |

运行方式：
    python v1_basic_agent.py
"""

import os
import subprocess
import sys
from pathlib import Path

from openai import OpenAI



# 工作目录固定为当前目录，避免越界
WORKDIR = Path.cwd()
# 创建客户端（OpenAI 兼容接口指向 DeepSeek）
client = OpenAI(
    api_key='sk-09b279eaac60459c96bd01226bb7a2ca',
    base_url="https://api.deepseek.com/v1"
)
# -----------------------------------------------------------------------------
# 系统提示词（给模型的唯一“规则”）
# -----------------------------------------------------------------------------

SYSTEM = f"""你是一名在目录 {WORKDIR} 里的编码 Agent。

循环：先简短思考 -> 调用工具 -> 汇报结果。

规则：
- 多用工具，少空谈；能动手就别光解释。
- 不要凭空猜文件路径，不确定就先 ls/find。
- 修改要最小化，不要过度设计。
- 完成后简述改动内容。"""

# -----------------------------------------------------------------------------
# 工具定义（告诉模型有哪些工具可用）
# -----------------------------------------------------------------------------

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

# -----------------------------------------------------------------------------
# 工具实现
# -----------------------------------------------------------------------------

def safe_path(p: str) -> Path:
    """
    确保路径留在工作区内，防止通过 ../ 越界访问。
    """
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"路径越界：{p}")
    return path


def run_bash(command: str) -> str:
    """
    执行 shell 命令，附带简单安全限制与超时。
    - 拦截明显危险的模式。
    - 超时 60 秒。
    - 输出截断到 50KB，避免撑爆上下文。
    """
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
    """
    读取文件，可指定 limit 仅返回前 N 行；输出截断 50KB。
    """
    try:
        text = safe_path(path).read_text()
        lines = text.splitlines()
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... (还有 {len(text.splitlines()) - limit} 行)"]
        return "\n".join(lines)[:50000]
    except Exception as e:
        return f"Error: {e}"


def run_write(path: str, content: str) -> str:
    """
    写文件（创建或覆盖），会自动建父目录。
    """
    try:
        fp = safe_path(path)
        fp.parent.mkdir(parents=True, exist_ok=True)
        fp.write_text(content)
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


def run_edit(path: str, old_text: str, new_text: str) -> str:
    """
    精确替换文件中的第一处 old_text，避免大面积误替换。
    """
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


def execute_tool(name: str, args: dict) -> str:
    """
    根据工具名分发到具体实现，并返回字符串结果。
    """
    if name == "bash":
        return run_bash(args["command"])
    if name == "read_file":
        return run_read(args["path"], args.get("limit"))
    if name == "write_file":
        return run_write(args["path"], args["content"])
    if name == "edit_file":
        return run_edit(args["path"], args["old_text"], args["new_text"])
    return f"Unknown tool: {name}"


# -----------------------------------------------------------------------------
# 核心 Agent 循环
# -----------------------------------------------------------------------------

def agent_loop(messages: list) -> list:
    """
    完整的 Agent 循环：
        1) 调模型
        2) 若模型要用工具，则执行并把结果塞回对话
        3) 没有工具调用就返回（任务结束）
    """
    while True:
        # 1. 让模型思考/决策
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
        )

        reply = response.choices[0].message

        # 2. 没有工具调用，任务完成
        if not reply.tool_calls:
            print(reply.content)
            messages.append({
                "role": "assistant",
                "content": reply.content or ""
            })
            return messages

        # 3. 执行工具并收集结果
        results = []
        import json
        for tc in reply.tool_calls:
            args = json.loads(tc.function.arguments)
            print(f"\n> {tc.function.name}: {args}")
            output = execute_tool(tc.function.name, args)
            preview = output[:200] + "..." if len(output) > 200 else output
            print(f"  {preview}")
            results.append({
                "role": "tool",
                "tool_call_id": tc.id,
                "content": output,
            })

        # 4. 把模型回复和工具结果加入历史，继续循环
        messages.append({
            "role": "assistant",
            "content": reply.content or "",
            "tool_calls": reply.tool_calls,
        })
        messages.extend(results)


# -----------------------------------------------------------------------------
# 简易 REPL 入口
# -----------------------------------------------------------------------------

def main():
    """
    交互式循环：逐条读取用户输入，保持上下文记忆。
    """
    print(f"Mini Claude Code v1 - {WORKDIR}")
    print("输入 exit / quit 可退出。\n")

    history = []

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            break

        if not user_input or user_input.lower() in {"exit", "quit", "q"}:
            break

        history.append({"role": "user", "content": user_input})

        try:
            agent_loop(history)
        except Exception as e:
            print(f"Error: {e}")

        print()


if __name__ == "__main__":
    main()
