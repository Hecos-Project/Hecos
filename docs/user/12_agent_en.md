# 🤖 12. Autonomous Agent & Sandbox

Zentra Core is equipped with an advanced reasoning engine that allows it to operate as an autonomous Agent.

- **Agent Loop**: Zentra can plan and execute complex tasks by breaking them down into sub-objectives, calling plugins and tools in succession.
- **AST Sandbox**: Every time the AI generates code (Python, algorithms, logic), it is executed in a protected "nursery" (AST Sandbox). This prevents the execution of commands dangerous to the operating system.
- **Automatic Tools**: The Agent can use the calculator, manage files, and search for information without constant user intervention.
