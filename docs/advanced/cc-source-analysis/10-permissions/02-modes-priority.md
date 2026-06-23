# 7 模式 8 优先级：Claude Code 的权限控制策略矩阵

> Claude Code 不是"要么全允许、要么全拒绝"的二元权限。它定义了 7 种运行模式和 8 级优先级，让权限控制从"开关"变成"策略矩阵"——不同场景下，不同工具、不同操作有不同的权限策略。

你好，我是江小湖。

上一篇 [三层防护](./01-three-layers.md) 讲到 Claude Code 的权限系统有三道防线。但三道防线只是"机制"——真正决定"什么操作在什么情况下允许"的，是**运行模式**和**优先级**。

7 种模式 × 8 级优先级，组合出一个灵活的权限控制矩阵。

## 目录

- [7 种运行模式](#7-种运行模式)
- [8 级优先级](#8-级优先级)
- [模式与优先级的组合矩阵](#模式与优先级的组合矩阵)
- [规则冲突解决](#规则冲突解决)
- [模式切换与边界保护](#模式切换与边界保护)
- [总结](#总结)
- [参考链接](#参考链接)

## 7 种运行模式

Claude Code 定义了 7 种运行模式，每种模式对应一种"信任级别"和"自动化程度"：

| 模式 | 信任级别 | 自动化程度 | 适用场景 |
|------|----------|------------|----------|
| **ask** | 最低 | 无 | 每次操作都询问用户 |
| **plan** | 低 | 低 | 先制定计划，每步执行前确认 |
| **default** | 中 | 中 | 标准模式，只读自动，写入需确认 |
| **auto** | 中高 | 中高 | 安全写入自动通过，危险操作确认 |
| **diff** | 中 | 中 | 显示 diff 后再应用修改 |
| **full-auto** | 高 | 高 | 几乎所有操作自动通过（不推荐） |
| **bypass** | 最高 | 最高 | 完全绕过权限检查（仅调试） |

### 模式详解

**ask 模式**：最保守的模式。任何工具调用前都会询问用户，即使是 `read_file` 也不例外。这适用于：
- 完全不信任 Agent 的场景
- 用户想完全控制每一步
- 学习/教学场景，让用户看到每个操作

```typescript
// ask 模式：所有工具调用前确认
const askMode: PermissionMode = {
  name: 'ask',
  autoApprove: [], // 空列表：没有自动通过的工具
  requireConfirmation: ['*'], // 通配符：所有工具都需要确认
};
```

**plan 模式**：Agent 先制定计划（如"我要修改 3 个文件"），用户确认计划后，Agent 按步骤执行。每步执行前可以再次确认。

```typescript
// plan 模式：计划制定 + 步骤确认
const planMode: PermissionMode = {
  name: 'plan',
  autoApprove: ['read_file', 'grep', 'glob'], // 只读工具自动
  requireConfirmation: ['edit_file', 'bash', 'delete_file'], // 写入需确认
  planApproval: true, // 需要计划级别的确认
};
```

**default 模式**：Claude Code 的标准模式。只读操作（read_file、grep）自动通过；安全写入（edit_file、create_file）自动通过；危险操作（delete_file、bash）需要确认。

```typescript
// default 模式：标准权限策略
const defaultMode: PermissionMode = {
  name: 'default',
  autoApprove: ['read_file', 'grep', 'glob', 'edit_file', 'create_file'],
  requireConfirmation: ['delete_file', 'bash', 'agent_tool', 'send_email'],
  dangerousConfirm: ['rm', 'curl', 'wget'], // 危险命令需要额外确认
};
```

**auto 模式**：更激进一些。安全写入自动通过，大部分操作都不需要确认。但不可逆操作（删除、发送）仍然需要确认。这是日常开发中最常用的模式。

```typescript
// auto 模式：高自动化
const autoMode: PermissionMode = {
  name: 'auto',
  autoApprove: ['read_file', 'grep', 'glob', 'edit_file', 'create_file', 'bash'],
  requireConfirmation: ['delete_file', 'agent_tool', 'send_email'],
  mlClassifier: true, // 启用 ML 分类器做额外检查
};
```

**diff 模式**：专注于代码审查。Agent 生成修改后，先展示 diff，用户确认后才应用。这适用于代码审查场景。

```typescript
// diff 模式：显示 diff 后确认
const diffMode: PermissionMode = {
  name: 'diff',
  autoApprove: ['read_file', 'grep', 'glob'],
  requireDiff: ['edit_file', 'create_file'], // 需要展示 diff
  requireConfirmation: ['delete_file', 'bash'],
};
```

**full-auto 模式**：几乎完全自动。只有少数极端危险操作（如 `rm -rf /`）会被拦截。这个模式只有在用户明确选择时才启用，且有醒目的警告提示。

```typescript
// full-auto 模式：最高自动化（不推荐）
const fullAutoMode: PermissionMode = {
  name: 'full-auto',
  autoApprove: ['*'], // 几乎所有工具自动
  forbid: ['delete_file', 'send_email'], // 只有极少数工具被禁止
  warning: 'Running in full-auto mode. Dangerous operations are still blocked.',
};
```

**bypass 模式**：完全绕过权限检查。仅用于内部调试，普通用户无法启用。启用时会在日志中记录警告。

```typescript
// bypass 模式：仅调试（不对外暴露）
const bypassMode: PermissionMode = {
  name: 'bypass',
  bypassAll: true,
  auditLog: true, // 强制审计日志
  warning: 'SECURITY: Permission checks bypassed.',
};
```

## 8 级优先级

权限规则可能有冲突——比如一个规则说"允许编辑文件"，另一个规则说"禁止编辑 `.env` 文件"。Claude Code 用 8 级优先级来裁决冲突：

| 优先级 | 级别 | 来源 | 示例 |
|--------|------|------|------|
| 1 | **Forbid** | 最高 | 禁止删除任何文件 |
| 2 | **Global Policy** | 全局策略 | 禁止访问 SSH 密钥 |
| 3 | **Project Policy** | 项目策略 | 禁止修改 `package.json` |
| 4 | **Session Policy** | 会话策略 | 本次会话禁止发送邮件 |
| 5 | **Mode Default** | 模式默认 | auto 模式默认允许 Bash |
| 6 | **Tool Default** | 工具默认 | `read_file` 默认允许 |
| 7 | **User Override** | 用户覆盖 | 用户临时允许某个操作 |
| 8 | **Allow** | 最低 | 允许所有操作（兜底） |

**优先级规则：数字越小，优先级越高**。高优先级规则可以覆盖低优先级规则。

### 优先级应用示例

假设当前是 `auto` 模式，用户尝试执行 `bash` 命令 `rm -rf ./build`：

```typescript
// 权限决策过程（简化版）
function resolvePermission(
  tool: string,
  args: Record<string, unknown>,
  context: ExecutionContext
): PermissionDecision {
  const rules = [
    // 优先级 1: Forbid（绝对禁止）
    { priority: 1, rule: 'forbid_rm_rf_root', check: () => args.command?.includes('rm -rf /') },
    
    // 优先级 2: Global Policy（全局策略）
    { priority: 2, rule: 'no_ssh_keys', check: () => args.path?.includes('.ssh') },
    
    // 优先级 3: Project Policy（项目策略）
    { priority: 3, rule: 'no_delete_node_modules', check: () => args.path?.includes('node_modules') },
    
    // 优先级 4: Session Policy（会话策略）
    { priority: 4, rule: 'session_no_bash', check: () => context.sessionPolicy?.noBash },
    
    // 优先级 5: Mode Default（模式默认）
    { priority: 5, rule: 'auto_allow_bash', check: () => context.mode === 'auto' },
    
    // 优先级 6: Tool Default（工具默认）
    { priority: 6, rule: 'bash_dangerous', check: () => true }, // Bash 默认需要确认
    
    // 优先级 7: User Override（用户覆盖）
    { priority: 7, rule: 'user_allowed_build', check: () => context.userOverrides?.includes('build_commands') },
    
    // 优先级 8: Allow（兜底）
    { priority: 8, rule: 'allow_all', check: () => true },
  ];
  
  // 按优先级排序，找到第一个匹配的规则
  const matched = rules
    .sort((a, b) => a.priority - b.priority)
    .find(rule => rule.check());
  
  return {
    decision: matched.priority <= 4 ? 'deny' : 'allow',
    reason: matched.rule,
    priority: matched.priority,
  };
}
```

**决策过程**：
1. 检查是否是 `rm -rf /` → 不是，继续
2. 检查是否访问 SSH 密钥 → 不是，继续
3. 检查是否删除 `node_modules` → 不是，继续
4. 检查会话是否禁止 Bash → 假设没有，继续
5. 检查 auto 模式是否允许 Bash → 是，但优先级 5 不是最高
6. 检查 Bash 工具默认规则 → 需要确认（优先级 6）
7. 检查用户是否覆盖了规则 → 假设没有
8. 最终决策：虽然 auto 模式"允许" Bash（优先级 5），但 Bash 工具的默认规则"需要确认"（优先级 6）。实际上，在 auto 模式下，Bash 是自动允许的，所以最终决策是 **允许**。

等等，这个例子有问题。让我重新梳理：

在 auto 模式下，Bash 是自动允许的。但 `rm -rf ./build` 包含 `rm` 命令，这在所有模式下都是危险操作。所以实际决策应该是：
- 优先级 1 的 `forbid_rm_rf_root`：不匹配（不是 `rm -rf /`）
- 优先级 5 的 `auto_allow_bash`：匹配，允许
- 但 Bash 命令里有 `rm`，需要额外的命令级检查

这说明 8 级优先级只是"框架"，具体规则还需要结合工具内部的命令级检查。

## 模式与优先级的组合矩阵

把 7 种模式和 8 级优先级组合，得到一个完整的权限矩阵：

```
              | ask  | plan | default | auto | diff | full-auto | bypass |
--------------|------|------|---------|------|------|-----------|--------|
Forbid        |  ✓   |  ✓   |    ✓    |  ✓   |  ✓   |     ✓     |   ✓    |
Global Policy |  ✓   |  ✓   |    ✓    |  ✓   |  ✓   |     ✓     |   ✓    |
Project Policy|  ✓   |  ✓   |    ✓    |  ✓   |  ✓   |     ✓     |   ✓    |
Session Policy|  ✓   |  ✓   |    ✓    |  ✓   |  ✓   |     ✓     |   ✓    |
Mode Default  | 全部问| 计划问|  读写分 | 大部分|  diff  |   几乎全  |   无   |
Tool Default  | 全部问| 全部问|  按工具 | 按工具| 按工具 |   按工具  |   无   |
User Override |  ✓   |  ✓   |    ✓    |  ✓   |  ✓   |     ✓     |   ✓    |
Allow         |  ✓   |  ✓   |    ✓    |  ✓   |  ✓   |     ✓     |   ✓    |
```

**矩阵解读**：
- 前 4 级（Forbid 到 Session Policy）在所有模式下都生效，不受模式影响。这是"安全基线"。
- 第 5 级（Mode Default）是模式的核心差异所在。ask 模式全部要确认，auto 模式大部分自动。
- 第 6 级（Tool Default）在工具层面做微调。比如 `read_file` 在 ask 模式下仍然需要确认（虽然它是只读的）。
- 第 7 级（User Override）允许用户临时覆盖任何规则。
- 第 8 级（Allow）是兜底规则，如果前面都没有拒绝，就允许。

## 规则冲突解决

当多个规则同时匹配时，Claude Code 的冲突解决策略是：

```typescript
// 规则冲突解决（简化版）
function resolveConflicts(rules: MatchedRule[]): PermissionDecision {
  // 1. 按优先级排序
  const sorted = rules.sort((a, b) => a.priority - b.priority);
  
  // 2. 取最高优先级的规则
  const highestPriority = sorted[0];
  
  // 3. 检查是否有同优先级的冲突规则
  const samePriority = sorted.filter(r => r.priority === highestPriority.priority);
  
  if (samePriority.length > 1) {
    // 同优先级冲突：Deny 优先于 Allow（安全原则）
    const hasDeny = samePriority.some(r => r.decision === 'deny');
    if (hasDeny) {
      return { decision: 'deny', reason: 'Conflict resolution: deny wins', priority: highestPriority.priority };
    }
  }
  
  return {
    decision: highestPriority.decision,
    reason: highestPriority.reason,
    priority: highestPriority.priority,
  };
}
```

**冲突解决三原则**：

1. **优先级优先**：高优先级规则覆盖低优先级规则。这是主要的冲突解决机制。

2. **Deny 优先于 Allow**：如果同优先级有冲突（一个说允许，一个说拒绝），**拒绝优先**。这是安全领域的"最小权限原则"。

3. **显式优于隐式**：用户明确设置的规则（如 User Override）优于系统默认规则（如 Mode Default）。

**实际冲突案例**：

```
场景：用户正在使用 auto 模式，尝试删除一个文件

规则 A（优先级 3 - Project Policy）：
  "项目根目录下的 .config 目录不可删除"
  → 匹配：是（文件在 .config 内）
  → 决策：Deny

规则 B（优先级 5 - Mode Default）：
  "auto 模式允许 delete_file 工具"
  → 匹配：是
  → 决策：Allow

规则 C（优先级 6 - Tool Default）：
  "delete_file 是危险工具，需要确认"
  → 匹配：是
  → 决策：Confirm（需要确认）

冲突解决：
  - 规则 A 优先级最高（3），决策是 Deny
  - 最终决策：Deny（因为项目策略禁止删除 .config）
  - 即使 auto 模式"允许"删除，项目策略仍然优先
```

## 模式切换与边界保护

用户可以在会话中切换模式（如从 default 切换到 auto）。但模式切换不是无限制的——Claude Code 有**边界保护机制**：

```typescript
// 模式切换边界保护（简化版）
async function switchMode(
  currentMode: PermissionMode,
  targetMode: PermissionMode,
  context: ExecutionContext
): Promise<ModeSwitchResult> {
  // 1. 检查是否允许切换
  if (!isModeSwitchAllowed(currentMode, targetMode)) {
    return { success: false, reason: 'Mode switch not allowed' };
  }
  
  // 2. 危险模式需要额外确认
  if (isDangerousMode(targetMode)) {
    const confirmed = await confirmDangerousModeSwitch(targetMode);
    if (!confirmed) {
      return { success: false, reason: 'User denied mode switch' };
    }
  }
  
  // 3. 切换模式时，清理相关缓存
  await clearPermissionCache(context.sessionId);
  
  // 4. 记录模式切换日志
  await logModeSwitch({
    from: currentMode.name,
    to: targetMode.name,
    timestamp: Date.now(),
    user: context.userId,
  });
  
  return { success: true, newMode: targetMode };
}
```

**边界保护策略**：

1. **单向切换限制**：某些模式切换是不允许的。比如从 `bypass` 模式不能切换到任何其他模式（必须先退出重启），防止权限检查被绕过后的状态混淆。

2. **危险模式确认**：切换到 `full-auto` 或 `bypass` 需要用户额外确认，且显示醒目的警告信息。

3. **缓存清理**：模式切换时，清理权限检查缓存。因为不同模式的缓存结果不兼容。

4. **审计日志**：所有模式切换都记录到审计日志中，包括时间、用户、从哪个模式切换到哪个模式。

**模式切换的持久化**：用户切换模式后，选择是否记住这个偏好。如果记住，下次启动时自动使用这个模式。但 `full-auto` 和 `bypass` 的偏好不会被记住（每次启动都默认回退到 `default`）。

## 总结

- Claude Code 有 **7 种运行模式**（ask/plan/default/auto/diff/full-auto/bypass），从"最保守"到"最开放"覆盖不同信任级别。
- **8 级优先级**（Forbid → Global Policy → Project Policy → Session Policy → Mode Default → Tool Default → User Override → Allow）裁决规则冲突。
- **冲突解决三原则**：高优先级覆盖低优先级、同优先级 Deny 优先于 Allow、显式规则优于隐式规则。
- **模式切换**有边界保护：单向限制、危险模式确认、缓存清理、审计日志。
- 权限控制从"开关"升级为**策略矩阵**，不同场景灵活配置，同时保持安全基线不变。

> 下一篇：[ML 分类器与 Bash 安全](./03-ml-classifier.md)，看 Claude Code 如何在 auto 模式下用机器学习判断 Bash 命令是否安全。

## 参考链接

- [Claude Code 权限模式源码](file:///E:/Projects/claude-code/src/utils/permissions/PermissionMode.js)
- [Claude Code 优先级规则源码](file:///E:/Projects/claude-code/src/utils/permissions/priorityRules.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
