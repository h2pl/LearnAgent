# memdir 持久化：Claude Code 如何把记忆存进文件系统

> Claude Code 没有选择数据库，而是用文件系统作为记忆的持久层。`memdir` 目录里的每个 `.md` 文件都是一条记忆，配合路径不可信校验和 `using` 资源管理，确保记忆在跨会话间安全存活。

你好，我是江小湖。

上一章 [上下文工程](../07-context-engineering/README.md) 讲了如何把 200K 的会话压缩到预算内。但压缩只能解决**当前**对话的问题——一旦会话结束，所有上下文归零。要让 Agent 真正"长记性"，需要一种**跨会话的持久化**机制。

Claude Code 的方案不是数据库，而是文件系统。这个选择本身就在回答一个设计问题：**记忆的持久层应该用什么？**

## 目录

- [为什么不用数据库](#为什么不用数据库)
- [memdir 目录结构](#memdir-目录结构)
- [路径不可信校验](#路径不可信校验)
- [using 资源管理](#using-资源管理)
- [记忆写入流程](#记忆写入流程)
- [总结](#总结)
- [参考链接](#参考链接)

## 为什么不用数据库

在大多数 Agent 框架里，记忆持久化首选是数据库——SQLite、PostgreSQL、或者向量数据库。但 Claude Code 选择了**文件系统**，原因有五个：

| 维度 | 文件系统 | 数据库 |
|------|----------|--------|
| **可观测性** | 直接 `cat` 查看 | 需要查询工具 |
| **版本控制** | 天然可 `git diff` | 需 schema 迁移 |
| **调试** | 打开文件就能读 | 需要连客户端 |
| **工具复用** | 已有文件操作工具 | 需专用 DB 工具 |
| **零依赖** | 不需要服务 | 需启动/维护 |

Claude Code 是一个常驻终端的工具，用户对它有**完全的可见性**要求。如果记忆藏在数据库里，用户想查自己有什么记忆，需要额外学一套查询语法。而文件系统——人人都会用 `ls` 和 `cat`。

**关键设计点**：记忆文件是 `.md` 格式。这不是随意选的——markdown 是人可读的，用户可以直接打开文件理解 Agent 记住了什么。这种设计在"开发者工具"的语境下特别合理。

## memdir 目录结构

`memdir` 目录位于用户的项目根目录下：

```
~/memdir/                          # 记忆根目录
├── memories/                      # 用户记忆
│   ├── 2024-06-01-user-preference.md
│   ├── 2024-06-15-project-convention.md
│   └── 2024-07-03-api-key-warning.md
├── sessions/                      # 会话级记忆（临时）
│   └── <session-id>/
│       └── context-summary.md
└── index.json                     # 记忆索引（快速检索）
```

每个 `.md` 文件是一个**记忆单元**，包含：

- **frontmatter**：创建时间、标签、来源会话、权重
- **正文**：记忆的内容，人可读
- **关联性**：与其他记忆的链接（双向引用）

```markdown
---
created: 2024-06-15T14:32:00Z
source_session: abc123
tags: [preference, coding-style]
weight: 0.85
---

# 用户偏好：使用 4 空格缩进

用户明确要求项目使用 4 空格缩进，而非 Tab。
此偏好适用于所有后续文件编辑操作。

## 关联
- [[2024-06-01-user-preference.md]]
```

**设计要点**：
- 记忆文件是**自描述**的，即使脱离系统也能被理解
- `weight` 是记忆的权重，用于检索排序（0-1，越高越重要）
- `source_session` 记录记忆的来源，方便追溯
- 关联机制让记忆形成**知识图谱**而非扁平列表

## 路径不可信校验

记忆文件路径来自用户输入（如"记住这个文件"），必须做安全校验。Claude Code 用 `pathIsUntrusted` 标记所有外部路径，然后做三道检查：

```typescript
// 路径不可信校验（简化版）
function validateMemoryPath(inputPath: string): string {
  // 1. 拒绝绝对路径：只能写相对路径
  if (path.isAbsolute(inputPath)) {
    throw new Error('Memory paths must be relative');
  }
  
  // 2. 解析并规范化（解决 ./ 和 ../）
  const normalized = path.normalize(inputPath);
  
  // 3. 拒绝路径遍历：不能跳出 memdir
  if (normalized.startsWith('..') || normalized.includes('../')) {
    throw new Error('Path traversal detected');
  }
  
  // 4. 限制扩展名：只允许 .md
  if (!normalized.endsWith('.md')) {
    throw new Error('Memory files must be .md');
  }
  
  return path.join(MEMDIR_ROOT, normalized);
}
```

**三道防线**：

1. **输入层过滤**：拒绝绝对路径，只允许相对路径。这防止了 `"/etc/passwd"` 这种直接写入系统文件的攻击。

2. **路径遍历拦截**：`path.normalize` 会把 `../../../etc/passwd` 解析成绝对路径，然后 `startsWith('..')` 就能拦截。但注意：如果 `normalized` 已经被 `path.join` 解析成了绝对路径，这个检查就不够了。更安全的做法是用 `path.resolve` 算出最终绝对路径，然后检查是否以 `MEMDIR_ROOT` 开头。

3. **扩展名白名单**：只允许 `.md`，防止写入可执行文件或其他格式。

**为什么重要**：记忆写入是 Agent 的核心权限之一。如果路径校验不严，攻击者可以通过构造特殊的记忆请求，让 Agent 覆写系统文件或窃取敏感信息。

## using 资源管理

记忆文件的操作需要保证**原子性和一致性**——写入过程中如果程序崩溃，不能留下半成品文件。Claude Code 使用了类似 C# `using` 语句的资源管理模式：

```typescript
// 记忆写入：原子文件操作（简化版）
async function writeMemory(
  relativePath: string,
  content: string
): Promise<void> {
  const fullPath = validateMemoryPath(relativePath);
  const dir = path.dirname(fullPath);
  
  // 确保目录存在
  await fs.mkdir(dir, { recursive: true });
  
  // 使用临时文件 + 原子重命名
  const tempPath = `${fullPath}.tmp.${Date.now()}`;
  
  try {
    // 写入临时文件
    await fs.writeFile(tempPath, content, 'utf-8');
    
    // 原子重命名：要么全成功，要么全失败
    await fs.rename(tempPath, fullPath);
  } catch (error) {
    // 清理临时文件
    try { await fs.unlink(tempPath); } catch {}
    throw error;
  }
  
  // 更新索引
  await updateMemoryIndex(fullPath, content);
}
```

**using 模式的三个要点**：

1. **临时文件 + 原子重命名**：先写 `.tmp` 文件，写完再 `rename`。这保证读取方永远不会看到半成品。

2. **清理回调**：如果写入失败，确保临时文件被删除。Claude Code 用一个 `cleanup` 数组来收集所有需要回滚的操作，在 `finally` 块里统一执行。

3. **索引同步**：文件写入后，需要同步更新 `index.json`。索引是内存中的快速检索结构，文件是持久化结构。两者必须保持一致，否则会出现"文件存在但检索不到"的问题。

**更完整的资源管理**：

```typescript
// 使用资源作用域（简化版）
async function withMemoryFile<T>(
  relativePath: string,
  operation: (handle: MemoryFileHandle) => Promise<T>
): Promise<T> {
  const fullPath = validateMemoryPath(relativePath);
  const cleanup: Array<() => Promise<void>> = [];
  
  try {
    const handle = await openMemoryFile(fullPath);
    cleanup.push(() => handle.close());
    
    const result = await operation(handle);
    
    // 写入成功，提交索引更新
    await commitMemoryIndex();
    return result;
  } catch (error) {
    // 写入失败，回滚所有操作
    await rollbackMemoryIndex();
    throw error;
  } finally {
    // 无论成功失败，都执行清理
    for (const fn of cleanup.reverse()) {
      try { await fn(); } catch {}
    }
  }
}
```

## 记忆写入流程

当 Claude Code 决定"记住"某件事时，完整的流程是：

```
用户行为或 Agent 反思
        ↓
生成记忆内容（frontmatter + 正文）
        ↓
校验记忆路径（validateMemoryPath）
        ↓
使用 withMemoryFile 原子写入
        ↓
更新内存索引（index.json）
        ↓
触发关联扫描（updateRelatedMemories）
```

**关联扫描**是 memdir 的一个巧妙设计。当新记忆写入时，系统会扫描已有记忆，找到语义相关的内容，在双向链接中互相引用。这让记忆形成**网状结构**，而不是孤立列表。

**老化机制**：记忆不是永久保存的。Claude Code 会根据以下因素降低记忆权重：

- **时间衰减**：越老的记忆权重越低
- **访问频率**：经常被检索的记忆保持高权重
- **冲突检测**：如果新记忆与旧记忆矛盾，旧记忆权重被调低

```typescript
// 记忆老化计算（简化版）
function calculateMemoryWeight(
  memory: MemoryFile
): number {
  const ageDays = (Date.now() - memory.created) / (1000 * 60 * 60 * 24);
  const ageDecay = Math.exp(-0.1 * ageDays); // 指数衰减
  const accessBoost = Math.log1p(memory.accessCount) * 0.2;
  
  return Math.min(1, memory.baseWeight * ageDecay + accessBoost);
}
```

## 总结

- Claude Code 用**文件系统**而非数据库作为记忆持久层，原因是可观测性、可调试性和零依赖。
- `memdir` 目录里的 `.md` 文件是**自描述**的记忆单元，包含 frontmatter、正文和关联链接。
- **路径不可信校验**通过三道防线（绝对路径拒绝、路径遍历拦截、扩展名白名单）防止恶意写入。
- **using 资源管理**用临时文件 + 原子重命名保证写入原子性，用 cleanup 回调保证资源释放。
- 记忆写入后触发**关联扫描**和**老化计算**，形成网状知识图谱并自动管理新鲜度。

> 下一篇：[记忆检索与 autoDream](./02-retrieval-dream.md)，看 Claude Code 如何在 42 个工具中找到记忆相关的调用，以及 autoDream 如何在后台反思提炼记忆。

## 参考链接

- [Claude Code 记忆系统源码](file:///E:/Projects/claude-code/src/memdir/)
- [Claude Code 状态管理源码](file:///E:/Projects/claude-code/src/bootstrap/state.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
