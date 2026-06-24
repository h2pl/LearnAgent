# 02 — 启动流程

<p align="center">
  <img src="../../../../assets/cc-source-analysis/02-startup-flow/startup-pipeline.svg" alt="启动流程" width="90%"/>
  <br/>
  <em>135ms 冷启动的 5 个阶段与优化策略</em>
</p>



<p align="center">
  <img src="../../../../assets/cc-source-analysis/02-startup-flow/init-flow.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析 02-startup-flow 配图</em>
</p>
## 导读

Claude Code 的启动过程是一个精心设计的性能优化案例。从用户敲下 `claude` 到看到 REPL 界面，整个流程被压缩到约 135ms（冷启动），这背后是一套"能并行就并行、能延迟就延迟、能跳过就跳过"的工程哲学。

读完本章，你将理解：
- 5 阶段启动流程：Fast-path 分发 → 并行预取 → 模块加载 → 初始化 → REPL 启动
- Fast-path 设计：`--version` 12ms 退出，零模块加载
- 并行预取策略：MDM 子进程、Keychain 读取与 import 并行
- Sticky-on Latch：保护 50-70K token 缓存不被中途打断
- 延迟初始化：REPL 渲染后才启动后台预取，利用"用户正在打字"的时间窗口

**TL;DR**：
1. 启动流程分 5 阶段，每个阶段都有明确的性能目标和优化策略
2. Fast-path 设计让简单命令（如 `--version`）零导入快速退出，12ms 完成
3. 并行预取是关键：在 ~135ms 的 import 期间，同时启动 MDM 子进程和 Keychain 读取
4. Sticky-on Latch 保护缓存：一旦启用某个 beta header，就保持开启，避免中途切换导致缓存失效
5. 延迟初始化利用"用户正在打字"的时间窗口，把非关键工作推到 REPL 渲染后

---

## 一、源码定位

### 1.1 关键文件路径

| 文件 | 行数 | 职责 |
|------|------|------|
| `src/entrypoints/cli.tsx` | 303 | 真正的入口，Fast-path 分发 |
| `src/main.tsx` | 4683 | 主启动逻辑，Commander 初始化 |
| `src/entrypoints/init.ts` | 340 | 初始化：配置、网络、API 预连接 |
| `src/bootstrap/state.ts` | 1758 | 全局状态定义（~150 个字段） |
| `src/utils/startupProfiler.ts` | - | 启动性能分析器 |

### 1.2 启动流程图

```
用户输入 `claude`
    ↓
┌─────────────────────────────────────────┐
│  阶段 1: Fast-path 分发 (cli.tsx)       │
│  - 检查 --version → 12ms 退出           │
│  - 检查子命令 → daemon/remote/ps 等     │
│  - 都不匹配 → import main.tsx           │
└─────────────────────────────────────────┘
    ↓ ~12ms 或 ~135ms
┌─────────────────────────────────────────┐
│  阶段 2: 并行预取 (main.tsx 顶部)       │
│  - profileCheckpoint('main_tsx_entry')  │
│  - startMdmRawRead() ← 启动 MDM 子进程  │
│  - startKeychainPrefetch() ← Keychain   │
│  - 然后才开始 import（~180 行）         │
└─────────────────────────────────────────┘
    ↓ ~135ms（import 期间，预取并行进行）
┌─────────────────────────────────────────┐
│  阶段 3: 模块加载 (main.tsx import)     │
│  - ~180 行 import 语句                  │
│  - 加载 Commander、React、工具系统等    │
│  - profileCheckpoint('imports_loaded')  │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  阶段 4: 初始化 (init.ts)               │
│  - enableConfigs()                      │
│  - applySafeConfigEnvironmentVariables()│
│  - configureGlobalMTLS()                │
│  - configureGlobalAgents()              │
│  - preconnectAnthropicApi() ← TCP+TLS   │
└─────────────────────────────────────────┘
    ↓
┌─────────────────────────────────────────┐
│  阶段 5: REPL 启动 (main.tsx action)    │
│  - 信任对话（首次）                     │
│  - 加载设置、迁移                       │
│  - 渲染 React/Ink UI                    │
│  - startDeferredPrefetches() ← 延迟初始化│
└─────────────────────────────────────────┘
```

---

## 二、核心实现剖析

### 2.1 阶段 1: Fast-path 分发

`cli.tsx` 是真正的入口，不是 `main.tsx`。它的设计原则是：**能跳过就跳过**。

```typescript
// entrypoints/cli.tsx - 简化版
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // Fast-path for --version: 零导入，直接退出
  if (args.length === 1 && (args[0] === '--version' || args[0] === '-v')) {
    console.log(`${MACRO.VERSION} (Claude Code)`);
    return; // 12ms 完成
  }

  // Fast-path for 各种子命令
  if (args[0] === 'daemon') {
    const { daemonMain } = await import('../daemon/main.js');
    await daemonMain(args.slice(1));
    return;
  }

  if (args[0] === 'remote-control' || args[0] === 'rc') {
    const { bridgeMain } = await import('../bridge/bridgeMain.js');
    await bridgeMain(args.slice(1));
    return;
  }

  if (args[0] === 'ps' || args[0] === 'logs') {
    const bg = await import('../cli/bg.js');
    await bg.psHandler(args.slice(1));
    return;
  }

  // 都不匹配，才加载完整 CLI
  const { main: cliMain } = await import('../main.js');
  await cliMain();
}
```

**设计要点**：
- `--version` 零导入：不加载任何模块，直接打印版本号退出
- 子命令按需加载：`daemon`、`remote-control`、`ps` 等子命令只加载自己需要的模块
- 完整 CLI 是最后手段：只有检测到是交互式 REPL，才加载 `main.tsx`

**为什么这样设计**：
- 用户敲 `claude --version` 只是想查版本，不需要加载 51 万行代码
- 子命令（如 `claude daemon`）通常用于脚本或后台任务，启动速度敏感
- 完整 CLI 加载需要 ~135ms，能跳过就跳过

### 2.2 阶段 2: 并行预取

一旦决定加载完整 CLI，`main.tsx` 顶部的 3 个副作用导入是关键：

```typescript
// main.tsx 顶部 - 这 3 行必须在所有 import 之前
import { profileCheckpoint, profileReport } from './utils/startupProfiler.js';
profileCheckpoint('main_tsx_entry');

import { startMdmRawRead } from './utils/settings/mdm/rawRead.js';
startMdmRawRead(); // 启动 MDM 子进程（plutil/reg query）

import { startKeychainPrefetch } from './utils/secureStorage/keychainPrefetch.js';
startKeychainPrefetch(); // 启动 macOS Keychain 读取（OAuth + legacy API key）

// 然后才开始 ~180 行 import
import { Command as CommanderCommand } from '@commander-js/extra-typings';
import chalk from 'chalk';
import React from 'react';
// ... 180+ 行 import
```

**设计要点**：
- MDM 子进程（`plutil`/`reg query`）启动慢，提前启动
- macOS Keychain 读取也慢（~65ms），提前启动
- 这两个操作与 ~180 行 import **并行进行**
- import 完成时，预取也完成了，几乎零等待

**为什么这样设计**：
- 如果不并行，启动时间 = import 时间 + MDM 时间 + Keychain 时间 ≈ 135ms + 50ms + 65ms = 250ms
- 并行后，启动时间 = max(import, MDM, Keychain) ≈ 135ms
- 节省了 ~115ms，接近减半

**代码注释原文**：
> "startMdmRawRead fires MDM subprocesses (plutil/reg query) so they run in parallel with the remaining ~135ms of imports below"
> 
> "startKeychainPrefetch fires both macOS keychain reads (OAuth + legacy API key) in parallel — isRemoteManagedSettingsEligible() otherwise reads them sequentially via sync spawn inside applySafeConfigEnvironmentVariables() (~65ms on every macOS startup)"

### 2.3 阶段 3: 模块加载

`main.tsx` 有 ~180 行 import，这是启动过程中最重的部分：

```typescript
// main.tsx - 部分 import
import { getOauthConfig } from './constants/oauth.js';
import { getSystemContext, getUserContext } from './context.js';
import { init, initializeTelemetryAfterTrust } from './entrypoints/init.js';
import { launchRepl } from './replLauncher.js';
import { fetchBootstrapData } from './services/api/bootstrap.js';
import { getTools } from './tools.js';
import { canUserConfigureAdvisor, getInitialAdvisorSetting } from './utils/advisor.js';
import { checkHasTrustDialogAccepted, getGlobalConfig } from './utils/config.js';
import { getInitialEffortSetting, parseEffortValue } from './utils/effort.js';
import { getInitialFastModeSetting, isFastModeEnabled } from './utils/fastMode.js';
import { findGitRoot, getBranch, getIsGit } from './utils/git.js';
import { getDefaultMainLoopModel, getUserSpecifiedModelSetting } from './utils/model/model.js';
import { PERMISSION_MODES } from './utils/permissions/PermissionMode.js';
import { checkAndDisableBypassPermissions, getAutoModeEnabledStateIfCached } from './utils/permissions/permissionSetup.js';
import { processSessionStartHooks, processSetupHooks } from './utils/sessionStart.js';
import { cacheSessionTitle, getSessionIdFromLog, loadTranscriptFromFile } from './utils/sessionStorage.js';
import { getInitialSettings, getSettingsForSource } from './utils/settings/settings.js';
// ... 还有 160+ 行
```

**设计要点**：
- 所有 import 都是静态的，Bun 打包时会优化
- import 顺序有讲究：先基础工具，后业务逻辑
- 有些 import 是 lazy require（避免循环依赖）：

```typescript
// Lazy require to avoid circular dependency
const getTeammateUtils = () => require('./utils/teammate.js');
const getTeammatePromptAddendum = () => require('./utils/swarm/teammatePromptAddendum.js');

// Dead code elimination: conditional import for COORDINATOR_MODE
const coordinatorModeModule = feature('COORDINATOR_MODE') 
  ? require('./coordinator/coordinatorMode.js') 
  : null;
```

**为什么这样设计**：
- 静态 import 让打包工具可以优化，减少运行时开销
- Lazy require 避免循环依赖，但会牺牲一些性能
- `feature()` 是 Bun 的编译时特性开关，未启用的功能会被 DCE（Dead Code Elimination）删除

### 2.4 阶段 4: 初始化

`init.ts` 的 `init()` 函数负责初始化核心系统：

```typescript
// entrypoints/init.ts - 简化版
export const init = memoize(async (): Promise<void> => {
  const initStartTime = Date.now();
  
  // 1. 启用配置系统
  enableConfigs();
  
  // 2. 应用安全的环境变量（信任对话前）
  applySafeConfigEnvironmentVariables();
  
  // 3. 应用 CA 证书（必须在 TLS 连接前）
  applyExtraCACertsFromConfig();
  
  // 4. 配置 mTLS
  configureGlobalMTLS();
  
  // 5. 配置 HTTP 代理
  configureGlobalAgents();
  
  // 6. 预连接 Anthropic API（TCP+TLS 握手 ~100-200ms）
  preconnectAnthropicApi();
  
  // 7. 设置 Windows shell
  setShellIfWindows();
  
  // 8. 注册清理回调
  registerCleanup(shutdownLspServerManager);
  registerCleanup(cleanupSessionTeams);
});
```

**设计要点**：
- `memoize` 确保 `init()` 只执行一次
- `preconnectAnthropicApi()` 提前启动 TCP+TLS 握手，与后续工作并行
- CA 证书必须在 TLS 连接前应用，因为 Bun 在启动时缓存 TLS 证书存储

**为什么这样设计**：
- API 预连接是关键：TCP+TLS 握手需要 ~100-200ms，提前启动可以隐藏这个延迟
- 注释原文："Preconnect to the Anthropic API — overlap TCP+TLS handshake (~100-200ms) with the ~100ms of action-handler work before the API request"

### 2.5 阶段 5: REPL 启动

`main.tsx` 的 `run()` 函数初始化 Commander，定义所有选项，然后进入 action handler：

```typescript
// main.tsx - 简化版
async function run(): Promise<CommanderCommand> {
  const program = new CommanderCommand()
    .name('claude')
    .description('Claude Code - starts an interactive session')
    .option('-p, --print', 'Print response and exit')
    .option('--model <model>', 'Model for the current session')
    .option('--permission-mode <mode>', 'Permission mode')
    // ... 50+ 个选项
    .action(async (prompt, options) => {
      // 1. 检查 --bare 模式
      if (options.bare) {
        process.env.CLAUDE_CODE_SIMPLE = '1';
      }
      
      // 2. 检测客户端类型
      const clientType = determineClientType();
      setClientType(clientType);
      
      // 3. 运行迁移
      runMigrations();
      
      // 4. 加载远程管理设置（非阻塞）
      void loadRemoteManagedSettings();
      
      // 5. 检查信任对话
      if (!checkHasTrustDialogAccepted()) {
        await showTrustDialog();
      }
      
      // 6. 初始化遥测（信任后）
      initializeTelemetryAfterTrust();
      
      // 7. 启动 REPL
      await launchRepl(prompt, options);
      
      // 8. 延迟预取（REPL 渲染后）
      startDeferredPrefetches();
    });
  
  return program;
}
```

**设计要点**：
- 信任对话必须在遥测初始化之前
- `startDeferredPrefetches()` 在 REPL 渲染后才启动，利用"用户正在打字"的时间窗口

**延迟预取的内容**：

```typescript
// main.tsx - startDeferredPrefetches()
export function startDeferredPrefetches(): void {
  // 跳过条件：性能测试或 --bare 模式
  if (isEnvTruthy(process.env.CLAUDE_CODE_EXIT_AFTER_FIRST_RENDER) || isBareMode()) {
    return;
  }

  // 进程启动预取（用户正在打字时完成）
  void initUser();
  void getUserContext();
  prefetchSystemContextIfSafe();
  void getRelevantTips();
  
  // 云提供商认证预取
  if (isEnvTruthy(process.env.CLAUDE_CODE_USE_BEDROCK)) {
    void prefetchAwsCredentialsAndBedRockInfoIfSafe();
  }
  if (isEnvTruthy(process.env.CLAUDE_CODE_USE_VERTEX)) {
    void prefetchGcpCredentialsIfSafe();
  }
  
  // 文件计数（3 秒超时）
  void countFilesRoundedRg(getCwd(), AbortSignal.timeout(3000), []);
  
  // 分析和特性标志初始化
  void initializeAnalyticsGates();
  void prefetchOfficialMcpUrls();
  void refreshModelCapabilities();
  
  // 文件变化检测器
  void settingsChangeDetector.initialize();
  void skillChangeDetector.initialize();
}
```

**为什么这样设计**：
- 这些工作都不是 REPL 渲染必需的
- 用户看到 REPL 后，通常需要几秒钟思考要问什么
- 这几秒钟就是预取的"免费"时间窗口
- 等用户开始打字时，预取已经完成了

### 2.6 Sticky-on Latch: 保护缓存

Sticky-on Latch 是 Claude Code 的一个精妙设计，用于保护 50-70K token 的提示缓存。

```typescript
// bootstrap/state.ts - Sticky-on Latch 字段
type State = {
  // Sticky-on latch for AFK_MODE_BETA_HEADER
  // 一旦启用 auto mode，就保持发送 header，避免 Shift+Tab 切换导致缓存失效
  afkModeHeaderLatched: boolean | null;
  
  // Sticky-on latch for FAST_MODE_BETA_HEADER
  // 一旦启用 fast mode，就保持发送 header，避免冷却进入/退出导致缓存失效
  fastModeHeaderLatched: boolean | null;
  
  // Sticky-on latch for cache-editing beta header
  // 一旦启用 cached microcompact，就保持发送 header，避免中途 GrowthBook/settings 切换导致缓存失效
  cacheEditingHeaderLatched: boolean | null;
  
  // Sticky-on latch for clearing thinking
  // 一旦 >1h 没有 API 调用（确认缓存失效），就保持清除 thinking，避免重新开启导致缓存失效
  thinkingClearLatched: boolean | null;
};
```

**设计要点**：
- 这些字段初始为 `null`，一旦设为 `true`，就保持 `true`
- 即使中途切换模式（如 Shift+Tab 切换 auto mode），header 也保持发送
- 这样服务器端的提示缓存就不会因为 header 变化而失效

**为什么这样设计**：
- 提示缓存有 50-70K token，价值很高
- 如果中途切换 header，缓存就会失效，下次请求需要重新计算
- 重新计算的成本是 12x（输入 token 成本增加 12 倍）
- Sticky-on Latch 通过"一旦开启就保持"的策略，避免缓存失效

**代码注释原文**：
> "Sticky-on latch for AFK_MODE_BETA_HEADER. Once auto mode is first activated, keep sending the header for the rest of the session so Shift+Tab toggles don't bust the ~50-70K token prompt cache."

---

## 三、关键设计点

### 3.1 Fast-path 分发

**设计原则**：能跳过就跳过。

- `--version` 零导入，12ms 退出
- 子命令按需加载，不加载完整 CLI
- 只有交互式 REPL 才加载完整 CLI

**反例**：如果不做 Fast-path 分发
- 用户敲 `claude --version`，需要加载 51 万行代码，~135ms
- 体验差，用户会觉得"这个工具启动真慢"

### 3.2 并行预取

**设计原则**：能并行就并行。

- MDM 子进程、Keychain 读取与 import 并行
- API 预连接与 action handler 并行
- 延迟预取与用户打字时间并行

**反例**：如果不做并行预取
- 启动时间 = import + MDM + Keychain + API 预连接 ≈ 135ms + 50ms + 65ms + 150ms = 400ms
- 体验差，用户会觉得"这个工具启动真慢"

### 3.3 延迟初始化

**设计原则**：能延迟就延迟。

- 非关键工作推到 REPL 渲染后
- 利用"用户正在打字"的时间窗口
- 性能测试时自动跳过

**反例**：如果不做延迟初始化
- REPL 渲染前要做大量预取，启动时间增加
- 用户看到 REPL 界面的时间延迟
- 性能测试时，启动时间不稳定

### 3.4 Sticky-on Latch

**设计原则**：一旦开启就保持，避免缓存失效。

- Beta header 一旦启用，就保持发送
- 即使中途切换模式，header 也不变
- 保护 50-70K token 的提示缓存

**反例**：如果不做 Sticky-on Latch
- 用户切换模式（如 Shift+Tab），header 变化
- 服务器端提示缓存失效
- 下次请求需要重新计算，成本增加 12x

---

## 四、对比其他实现

### 4.1 vs Hermes

| 维度 | Claude Code | Hermes |
|------|------------|--------|
| Fast-path | ✅ 多种 Fast-path | ❌ 无 |
| 并行预取 | ✅ MDM + Keychain + API | ❌ 无 |
| 延迟初始化 | ✅ REPL 渲染后 | ❌ 无 |
| 启动时间 | ~135ms | ~3-5s |

**评价**：Hermes 是 Python，启动慢是语言特性，不是设计问题。但 Claude Code 的 Fast-path 和并行预取确实值得学习。

### 4.2 vs OpenClaw

| 维度 | Claude Code | OpenClaw |
|------|------------|----------|
| Fast-path | ✅ 多种 Fast-path | ❌ 无 |
| 并行预取 | ✅ MDM + Keychain + API | ❌ 无 |
| 延迟初始化 | ✅ REPL 渲染后 | ❌ 无 |
| 启动时间 | ~135ms | 8-12s |

**评价**：OpenClaw 启动慢是因为 Python + 大量依赖。Claude Code 的优化策略在 TypeScript 生态中是标杆。

### 4.3 vs LearnAgent 自建

| 维度 | Claude Code | LearnAgent |
|------|------------|------------|
| Fast-path | ✅ 多种 Fast-path | ❌ 无 |
| 并行预取 | ✅ MDM + Keychain + API | ❌ 无 |
| 延迟初始化 | ✅ REPL 渲染后 | ❌ 无 |
| 启动时间 | ~135ms | ~1-2s |

**评价**：LearnAgent 是教学项目，不需要这些优化。但如果要做生产级项目，这些优化是必须的。

---

## 五、面试考点

### 5.1 高频问题

**Q1: Claude Code 的启动流程分几个阶段？**

A: 5 个阶段：
1. Fast-path 分发（cli.tsx）
2. 并行预取（main.tsx 顶部）
3. 模块加载（main.tsx import）
4. 初始化（init.ts）
5. REPL 启动（main.tsx action handler）

**Q2: 为什么 `--version` 能 12ms 退出？**

A: 因为 Fast-path 设计。`cli.tsx` 检测到 `--version` 后，零导入，直接打印版本号退出。不加载 `main.tsx` 的 ~180 行 import。

**Q3: 并行预取的关键是什么？**

A: 在 ~135ms 的 import 期间，同时启动 MDM 子进程（~50ms）和 Keychain 读取（~65ms）。import 完成时，预取也完成了，几乎零等待。启动时间从 250ms 降到 135ms。

**Q4: 什么是 Sticky-on Latch？**

A: Sticky-on Latch 是保护提示缓存的设计。Beta header 一旦启用，就保持发送，即使中途切换模式。这样服务器端的提示缓存就不会因为 header 变化而失效，避免 12x 的成本增加。

**Q5: 延迟初始化的原理是什么？**

A: 非关键工作（如用户信息、系统上下文、文件计数）推到 REPL 渲染后才启动。用户看到 REPL 后，通常需要几秒钟思考要问什么，这几秒钟就是预取的"免费"时间窗口。等用户开始打字时，预取已经完成了。

---

## 六、本章小结

### Takeaway

1. **Fast-path 分发**：能跳过就跳过，`--version` 零导入 12ms 退出
2. **并行预取**：能并行就并行，MDM + Keychain + API 与 import 并行
3. **延迟初始化**：能延迟就延迟，利用"用户正在打字"的时间窗口
4. **Sticky-on Latch**：一旦开启就保持，保护 50-70K token 缓存

### 思考题

1. 如果让你设计一个 CLI 工具的启动流程，你会怎么优化？
2. Fast-path 分发的适用场景有哪些？除了 `--version`，还有哪些命令适合 Fast-path？
3. 并行预取的关键是什么？如果预取失败了怎么办？
4. Sticky-on Latch 的缺点是什么？有没有更好的方案？
5. 延迟初始化的"免费"时间窗口有多长？如果用户打字很快怎么办？

---

## 七、参考资料

- [Claude Code 源码](file:///E:/Projects/claude-code/src/entrypoints/cli.tsx)
- [main.tsx](file:///E:/Projects/claude-code/src/main.tsx)
- [init.ts](file:///E:/Projects/claude-code/src/entrypoints/init.ts)
- [bootstrap/state.ts](file:///E:/Projects/claude-code/src/bootstrap/state.ts)
