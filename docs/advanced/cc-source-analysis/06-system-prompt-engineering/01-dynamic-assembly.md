# 动态拼装

> `prompts.ts` 有 866 行，产出一条 50-70K token 的系统提示词。它不是一个大字符串，而是数百个碎片在运行时按条件拼接。基础指令、安全守则、工具描述、用户偏好——每个碎片独立存在、独立决策。

你好，我是江小湖。

上一篇 [Fallback 与多模型路由](../05-llm-calling/03-fallback.md) 讲到 Claude Code 在线路故障时如何切换模型。这一篇进入提示词层：这套 50-70K token 的"操作手册"是怎么组装出来的。

## 目录

- [碎片化架构：40+ 个 section 函数](#碎片化架构40-个-section-函数)
- [动态边界：静态可缓存 vs 动态不可缓存](#动态边界静态可缓存-vs-动态不可缓存)
- [七大模块的职责分解](#七大模块的职责分解)
- [条件化注入：特性开关驱动的提示词](#条件化注入特性开关驱动的提示词)
- [总结](#总结)
- [参考链接](#参考链接)

## 碎片化架构：40+ 个 section 函数

`prompts.ts` 的核心函数是 `getSystemPrompt()`。它不返回一个大字符串，而是一个 `string[]`——每个元素是一个独立的提示碎片：

```typescript
export async function getSystemPrompt(
  tools: Tools,
  model: string,
  ...
): Promise<string[]> {
  return [
    // --- Static content (cacheable) ---
    getSimpleIntroSection(outputStyleConfig),
    getSimpleSystemSection(),
    getSimpleDoingTasksSection(),
    getActionsSection(),
    getUsingYourToolsSection(enabledTools),
    getSimpleToneAndStyleSection(),
    getOutputEfficiencySection(),
    // === BOUNDARY MARKER ===
    SYSTEM_PROMPT_DYNAMIC_BOUNDARY,
    // --- Dynamic content (not cacheable) ---
    ...resolvedDynamicSections,
  ].filter(s => s !== null)
}
```

用数组而不是字符串串接有一个关键好处：**每个碎片可以独立启用/禁用，且不影响缓存的哈希计算**。Claude Code 在构建 API 请求时，对"静态区"和"动态区"做不同的缓存处理。

## 动态边界：静态可缓存 vs 动态不可缓存

`SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 是一个特殊标记：

```typescript
export const SYSTEM_PROMPT_DYNAMIC_BOUNDARY =
  '__SYSTEM_PROMPT_DYNAMIC_BOUNDARY__'
```

边界之前的碎片是**静态的**：所有同版本 Claude Code 用户共享相同内容。这些内容使用 `scope: 'global'` 缓存，可以被跨组织共享。

边界之后的碎片是**动态的**：包含用户特定的信息、会话状态、工具列表等。这些内容不会被跨组织缓存。

```typescript
// prompts.ts — getSystemPrompt 的缓存策略
...(shouldUseGlobalCacheScope() ? [SYSTEM_PROMPT_DYNAMIC_BOUNDARY] : []),
```

当 `shouldUseGlobalCacheScope()` 返回 true 时（第一方 API + 特定模型），静态区使用 global scope 缓存，动态区使用 organization scope。如果 global scope 不能用，整个系统提示词都不插入边界标记，统一使用 org scope 缓存。

这种两层缓存策略的最大化了一个关键指标：**静态区的跨组织共享率**。静态区占总提示词的 70% 以上，全球 Claude Code 用户共享同一份缓存——这意味着每次新会话启动时，大部分提示词已经在服务端缓存中。详细的缓存冻结机制见下一篇 [缓存冻结](./02-cache-freezing.md)。

## 七大模块的职责分解

系统提示词可以按职责分成七个模块：

### 1. 身份与基础指令

```typescript
function getSimpleIntroSection(): string {
  return `You are an interactive agent that helps users with software engineering tasks.
IMPORTANT: Assist with authorized security testing...
IMPORTANT: You must NEVER generate or guess URLs...`
}
```

定义 Claude Code 的身份、能力边界、安全底线。面向所有用户，不依赖任何配置。

### 2. 系统环境

```typescript
function getSimpleSystemSection(): string {
  // 输出格式、权限模式、Hook 机制、自动压缩
}
```

告诉模型它运行在什么环境中：输出会被渲染为 Markdown、工具有权限控制、消息会被自动压缩。

### 3. 任务执行指南

`getSimpleDoingTasksSection()` 是七个模块中最长的，包含了非常详细的代码编写规范：

- 不要添加未要求的功能
- 不要过度抽象
- 编辑前先读取文件
- 失败后先诊断再重试
- 不引入安全漏洞

这些不是"建议"，而是 60 多条硬性规则——Claude Code 相信明确的约束比模糊的自由更能产生好代码。

### 4. 工具使用说明

`getUsingYourToolsSection(enabledTools)` 根据当前启用的工具动态生成使用说明。如果 `AskUserQuestionTool` 可用，就会生成相应的使用指导。

### 5. 代码风格

`getSimpleToneAndStyleSection()` 定义输出风格：直接、技术化、不啰嗦。

### 6. 输出效率

`getOutputEfficiencySection()` 指导模型如何高效使用 token。

### 7. 动态会话区

边界之后的内容，由 `resolveSystemPromptSections` 管理，包含：

- CLAUDE.md 内容（项目上下文）
- MCP 服务器指令
- Memory 模块加载的内容
- 语言偏好
- Output Style 配置
- Session-specific 指南（TODO、Agent 使用）

## 条件化注入：特性开关驱动的提示词

Claude Code 的很多功能通过 feature flag 控制。提示词中的相应指令也通过条件注入：

```typescript
// prompts.ts — 条件化注入
const proactiveModule = feature('PROACTIVE') || feature('KAIROS')
  ? require('../proactive/index.js')
  : null

const DISCOVER_SKILLS_TOOL_NAME = feature('EXPERIMENTAL_SKILL_SEARCH')
  ? require('../tools/DiscoverSkillsTool/prompt.js').DISCOVER_SKILLS_TOOL_NAME
  : null
```

使用 bun 的 `feature()` 宏，未启用的特性相关的代码在构建时直接被 Dead Code Elimination 移除。这意味着发布出去的 Claude Code 二进制中，不会包含未开放功能的提示词片段。

这种设计让 Claude Code 可以安全地在提示词层面做 A/B 测试——不同的用户组看到不同的指令，而不需要维护多套提示词文件。

## 总结

- `prompts.ts` 用 40+ 个独立函数组装系统提示词，每个碎片独立存在、独立决策。
- `SYSTEM_PROMPT_DYNAMIC_BOUNDARY` 将提示词分为静态可缓存区和动态不可缓存区，静态区使用 global scope 跨组织共享。
- 七大模块按职责分工：身份指令、系统环境、任务指南、工具说明、代码风格、输出效率、动态会话。
- 特性开关驱动的条件注入让 Claude Code 在提示词层面安全地进行 A/B 测试。
- 代码编写规范不是"建议"而是 60 多条硬性规则——明确约束 > 模糊自由。

> 下一篇：[缓存冻结](./02-cache-freezing.md)，看 DYNAMIC_BOUNDARY 如何最大化跨组织 Prompt Cache 命中率。

## 参考链接

- [Claude Code prompts.ts 源码](file:///E:/Projects/claude-code/src/constants/prompts.ts)
- [Claude Code systemPromptSections.ts](file:///E:/Projects/claude-code/src/constants/systemPromptSections.ts)
- [Claude Code cyberRiskInstruction.ts](file:///E:/Projects/claude-code/src/constants/cyberRiskInstruction.ts)
- [Anthropic Prompt Caching 文档](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching)
