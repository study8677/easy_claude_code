import os
import subprocess
from openai import OpenAI

# 1. 初始化客户端
client = OpenAI(
    api_key='',
    base_url="https://api.deepseek.com"
)

# 2. 定义安全护栏：危险关键词黑名单
DANGER_ZONE = [
    "rm ", "del ", "rd ", "format", "mkfs", "shred", 
    "chmod 777", "chown", "> /dev/", "powershell.exe", 
    "reg delete", "taskkill", "shutdown"
]

def run_command(cmd):
    # 安全检查逻辑
    is_dangerous = any(danger in cmd.lower() for danger in DANGER_ZONE)
    
    if is_dangerous:
        print(f"\n⚠️  [安全警告]: AI 试图执行高危命令: {cmd}")
        confirm = input("确认执行吗？ (y/n): ").strip().lower()
        if confirm != 'y':
            return "执行已被用户拦截：处于安全理由，用户拒绝了该命令的执行。"

    print(f"  [系统执行]: {cmd}")
    try:
        # 运行命令并获取输出
        result = subprocess.check_output(cmd, shell=True, stderr=subprocess.STDOUT, text=True, encoding='utf-8', errors='replace')
        return result or "成功执行（无输出）"
    except subprocess.CalledProcessError as e:
        return f"执行出错: {e.output}"

# 3. 配置工具说明书
tools = [
    {
        "type": "function",
        "function": {
            "name": "run_command",
            "description": "在本地终端执行系统命令（如 ls, dir, echo, python 等）",
            "parameters": {
                "type": "object",
                "properties": {
                    "cmd": {"type": "string", "description": "要执行的命令行代码"}
                },
                "required": ["cmd"]
            }
        }
    }
]

messages = [{"role": "system", "content": "你是一个有实操能力的助手。如果用户要求你查文件或运行代码，请使用 run_command 工具。"}]

print("--- Agent 模式已启动 (输入 'exit' 退出) ---")

while True:
    user_input = input("\n用户: ")
    if user_input.lower() in ['quit', 'exit']: break
    
    messages.append({"role": "user", "content": user_input})

    # --- 核心 Agent 循环开始 ---
    while True:
        response = client.chat.completions.create(
            model="deepseek-chat",
            messages=messages,
            tools=tools, # 每次请求都带着工具箱
            stream=False
        )
        
        reply = response.choices[0].message
        # 检查模型是否想调用工具
        if reply.tool_calls:
            messages.append(reply) # 必须把模型的“请求”存入历史
            
            for tool_call in reply.tool_calls:
                # 提取参数并运行函数
                import json
                args = json.loads(tool_call.function.arguments)
                result = run_command(args['cmd'])
                
                # 将“执行结果”喂回给模型
                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": result
                })
            
            # 继续下一次 while 循环，让模型根据结果再思考
            continue 
        else:
            # 模型不想调工具了，说明它想给出最终回复
            print(f"AI: {reply.content}")
            messages.append(reply)
            break # 退出内部循环，等待用户下一次输入
