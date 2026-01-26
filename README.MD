# easy_claude_code

[English Version](./README_EN.MD) | 中文版

## 项目描述
本项目（easy_claude_code）是一个旨在通过最精简的代码实现 AI Agent（智能体）核心逻辑的教学项目。它模仿了 Claude Code 的基本工作原理：**模型思考 -> 工具调用 -> 自动迭代循环**。通过本项目，你可以亲手构建一个能操作本地文件、执行系统命令并带有安全护栏的 AI 助手，从而真正将“Agent 概念”转化为“工程直觉”。

---

### 项目初心
社区里已有 `nanocode`、`learn-claude-code` 等极简示例，但“看懂”不等于“吃透”。本项目的目的就是让你 **自己搭一遍完整循环**：模型思考 → 调用工具 → 观察结果 → 再决策。代码被压到最小，只剩核心骨架，让“模型即决策者、代码只给工具箱”这件事变得直观。

### 现在的进度（随代码实测更新）
- `easy_cil.py`：带安全黑名单、退出码回传、输出截断的命令执行 Agent，黑名单覆盖 rm/sudo 以及 vim/top/less 等会挂起交互的指令。
- `v1_basic_agent.py`：约 200 行的教学版循环，4 个函数工具（bash/read_file/write_file/edit_file），默认直连 DeepSeek `deepseek-chat`。
- `v2_async_agent.py`：异步版 Agent（任务解耦 + step 状态机），提交任务返回 task_id，可通过 status 查询进度。
- `.env`/环境变量：支持通过 `DEEPSEEK_API_KEY`、`DEEPSEEK_MODEL` 配置；未设定时会提示缺失。

### 快速上手
```bash
pip install openai python-dotenv
export DEEPSEEK_API_KEY=你的key   # 或写入 .env
python v1_basic_agent.py
```
异步版（任务解耦 + 状态查询）：
```bash
python v2_async_agent.py
# run <prompt>
# status <task_id>
```
对话示例：
```
You: 列出当前目录
You: 读取 README.MD 前 40 行
You: 创建一个 demo.txt 写入 hello world
```

### 核心功能
- **核心 Agent 闭环**：模型自主决定工具调用顺序，直到完成任务。
- **本地工具访问**：执行 Shell、读写文件、小粒度编辑。
- **安全护栏**：高危命令二次确认，输出长度截断，执行超时保护。
- **多轮记忆**：对话历史累积，结果回灌给模型继续推理。

### 适合谁？
- 想快速理解 Claude Code / Cursor Agent 工作流的初学者。
- 需要一份“能跑、可改、看得懂”的最小代理参考实现的工程师。
- 希望在本地环境里试验模型 + 工具调用闭环的黑客与学生。
