# easy_claude_code

English Version | [中文版](./README.MD)

## Project Description
`easy_claude_code` is a minimalist educational project designed to implement the core logic of an AI Agent with the simplest possible code. It mimics the fundamental working principles of Claude Code: **Model Thinking -> Tool Calling -> Automated Iterative Loop**. Through this project, you can build your own AI assistant capable of manipulating local files, executing system commands, and implementing safety guardrails, thereby transforming "Agent concepts" into "engineering intuition."

---

### Project Philosophy
Several excellent projects, such as `nanocode` and `learn-claude-code`, have demonstrated the principles of Claude Code in a minimalist manner. These projects are invaluable for lowering the barrier to entry and showcasing core workflows.

However, in the era of AI, true understanding goes beyond "reading and understanding"—it lies in "hands-on implementation." Only after building the key mechanisms yourself will the concepts of model invocation, context organization, and tool orchestration transform from abstract ideas into intuition.

This project is born from this perspective:  
Building upon previous minimalist implementations, it further strips away unnecessary concepts and engineering noise. With fewer layers of abstraction, it empowers readers to truly grasp how Claude Code works by "building it once."

### Features
- **Core Agent Loop**: Implementation of the "think-act-observe" loop.
- **Local Tool Access**: Ability to run shell commands and manage files.
- **Safety Guardrails**: Interceptive logic for high-risk commands.
- **Multimodal Interactions**: Support for multi-turn conversations with history context.
