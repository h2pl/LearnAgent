# 初始化与 REPL

> 加载完模块后，Claude Code 还需要初始化配置、信任对话、全局状态和 UI。Sticky-on Latch 在这里保护 50-70K token 的提示缓存不被中途切换破坏。

你好，我是江小湖。

前两篇讲了入口分发和启动优化。这一篇讲最后一个阶段：模块加载完成后，`main.tsx` 如何初始化各种系统，最终渲染出 REPL 界面。

## 目录

- [Commander 参数解析](#commander-参数解析)
- [init.ts 的初始化链](#inits-的初始化链)
- [信任对话与遥测](#信任对话与遥测)
- [Sticky-on Latch 保护缓存](#sticky-on-latch-保护缓存)
- [启动 REPL](#启动-repl)
- [总结](#总结)
- [参考链接](#参考链接)

<p align="center">
  <img src="../../../../assets/cc-source-analysis/02-startup-flow/startup-pipeline.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析系列配图</em>
</p>



<p align="center">
  <img src="../../../../assets/cc-source-analysis/02-startup-flow/init-flow.svg" alt="" width="90%"/>
  <br/>
  <em>Claude Code 源码解析 02-startup-flow 配图</em>
</p>
## Commander 参数解析

`main.tsx` 用 Commander 定义了 50 多个命令行选项：

```typescript
// main.tsx（简化）
const program = new CommanderCommand()
  .name('claude')
  .description('Claude Code - starts an interactive session')
  .option('-p, --print', 'Print response and exit')
  .option('--model <model>', 'Model for the current session')
  .option('--permission-mode <mode>', 'Permission mode')
  .option('--bare', 'Run in bare mode')
  // ... 50+ 个选项
  .action(async (prompt, options) => {
    // 启动逻辑
  });
```

这些选项覆盖运行模式、模型选择、权限模式、输出控制等。参数解析完成后，进入 action handler，这是真正开始初始化的位置。

## init.ts 的初始化链

action handler 首先调用 `init()`，这是一个被 `memoize` 包装过的初始化函数：

```typescript
// entrypoints/init.ts（简化）
export const init = memoize(async (): Promise<void> => {
  enableConfigs();
  applySafeConfigEnvironmentVariables();
  applyExtraCACertsFromConfig();
  configureGlobalMTLS();
  configureGlobalAgents();
  preconnectAnthropicApi();
  setShellIfWindows();
});
```

`memoize` 确保 `init()` 在整个进程生命周期内只执行一次。即使多个子系统调用它，也不会重复初始化。

初始化链的顺序很重要：

1. **启用配置系统**：读取配置文件和环境变量
2. **应用安全环境变量**：在信任对话前就能生效的配置
3. **应用 CA 证书**：必须在 TLS 连接前完成
4. **配置 mTLS**：客户端证书认证
5. **配置全局 HTTP 代理**
6. **预连接 Anthropic API**：提前完成 TCP+TLS 握手
7. **Windows shell 设置**

## 信任对话与遥测

在初始化完成后，`main.tsx` 会检查用户是否已经接受过信任对话：

```typescript
if (!checkHasTrustDialogAccepted()) {
  await showTrustDialog();
}
initializeTelemetryAfterTrust();
```

信任对话是一个用户授权步骤，告知用户 Claude Code 会访问文件系统和网络。只有在用户同意后，遥测系统才会初始化。这个顺序是合规设计：不获取未授权的数据。

## Sticky-on Latch 保护缓存

全局状态 `bootstrap/state.ts` 中有一组 Sticky-on Latch 字段，专门用来保护提示缓存：

```typescript
// bootstrap/state.ts（简化）
type State = {
  afkModeHeaderLatched: boolean | null;       // auto mode beta header
  fastModeHeaderLatched: boolean | null;      // fast mode beta header
  cacheEditingHeaderLatched: boolean | null;  // cached microcompact header
  thinkingClearLatched: boolean | null;       // thinking clear header
};
```

这些字段初始为 `null`，一旦启用就保持为 `true`。即使用户中途按 Shift+Tab 切换 auto mode，header 仍然保持发送。

**为什么这样做？**

Claude Code 的系统提示词有约 50-70K token，缓存在服务器端。如果请求中的 header 变化，缓存就会失效，下次请求需要重新计算，输入成本增加约 12 倍。Sticky-on Latch 通过"一旦开启就保持"的策略，避免缓存失效。

## 启动 REPL

最后一步是 `launchRepl()`：

```typescript
await launchRepl(prompt, options);
startDeferredPrefetches();
```

`launchRepl()` 负责：

- 加载会话历史（如果有）
- 初始化 React/Ink 渲染环境
- 渲染 REPL 界面
- 把控制权交给用户

`startDeferredPrefetches()` 在 REPL 渲染后启动，利用用户思考的时间完成非关键预取。

## 总结

- `main.tsx` 用 Commander 解析 50 多个命令行选项。
- `init.ts` 按严格顺序初始化配置、证书、代理和 API 连接。
- 信任对话必须在遥测初始化之前完成。
- Sticky-on Latch 保护 50-70K token 的提示缓存，避免 header 切换导致缓存失效。
- `launchRepl()` 最终渲染 REPL 界面，把控制权交给用户。

> 下一章进入 [Agent 循环](../03-agent-loop/01-loop.md)，看 Claude Code 最核心的 88 行 while 循环是怎么运行的。

## 参考链接

- [Claude Code 主入口](file:///E:/Projects/claude-code/src/main.tsx)
- [Claude Code 初始化逻辑](file:///E:/Projects/claude-code/src/entrypoints/init.ts)
- [Claude Code 全局状态](file:///E:/Projects/claude-code/src/bootstrap/state.ts)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
