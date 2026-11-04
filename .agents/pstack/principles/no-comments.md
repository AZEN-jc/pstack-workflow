# Principle: No Comments (The "Comment Sicko" Rule)

AI 模型极度热衷于在代码里写满 `# Validate input`、`// Loop through items`、`# Return result` 这类废话注释。本原则由 `scripts/verify-code-slop.py` 强制执行。

## 1. 注释清洗三步法
1. **复述代码做什么（What）的注释：一律直接删除。** 如果代码需要注释才能看懂它在做什么，说明变量名、函数名或控制流写得太烂。重命名标识符或提取小函数，而不是加注释。
2. **解释业务约束（Constraint）的注释：转化为类型、断言或测试。**
   - 不要写：`# user_id 必须大于 0 且不能为空`
   - 要写成：`assert isinstance(user_id, int) and user_id > 0, f"Invalid user_id: {user_id}"`
3. **唯一允许保留的注释（Why / External Trap）**：仅当存在代码本身无法表达的外部世界怪癖（如操作系统内核 Bug、第三方 API 未文档化的限流行为、反直觉的性能权衡）时，才允许保留注释，且必须以 `Why:` 或 `Constraint:` 开头并附上实证依据或链接。
