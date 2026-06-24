# 启动入口

> Claude Code 的真正入口不是 `main.tsx`，而是 `cli.tsx`。它通过 Fast-path 分发，让 `--version` 等简单命令在 12ms 内零模块加载退出。

你好，我是江小湖。

上一章 [三大框架对比](../01-architecture-overview/03-comparison.md) 提到，Claude Code 的启动性能碾压 Hermes 和 OpenClaw。这一篇从启动的源头讲起：用户敲下 `claude` 后，第一个被调用的文件是什么？它是如何决定走哪条路的？

## 目录

- [为什么入口不是 main.tsx](#为什么入口不是-maintx)
- [Fast-path 分发](#fast-path-分发)
- [子命令按需加载](#子命令按需加载)
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
## 为什么入口不是 main.tsx

大多数人会以为 `claude` 命令的入口是 `src/main.tsx`，因为它的文件名最像主文件。但实际上，真正的入口是 `src/entrypoints/cli.tsx`。

`main.tsx` 有 4683 行，包含完整的 Commander 配置、工具系统、权限系统、React/Ink UI 渲染等。如果每个命令都要先加载它，那 `--version` 这种只需要打印一行版本号的命令，就要白白浪费 135ms。

`cli.tsx` 的作用就是做一道"预审"。它先判断用户想干什么，再决定加载哪些模块。

```typescript
// entrypoints/cli.tsx（简化）
async function main(): Promise<void> {
  const args = process.argv.slice(2);

  // Fast-path for --version：零导入，直接退出
  if (args.length === 1 && args[0] === '--version') {
    console.log(`${MACRO.VERSION} (Claude Code)`);
    return; // 12ms 内完成
  }

  // 子命令按需加载
  if (args[0] === 'daemon') {
    const { daemonMain } = await import('../daemon/main.js');
    await daemonMain(args.slice(1));
    return;
  }

  // 默认路径：加载完整 REPL
  const { main: cliMain } = await import('../main.js');
  await cliMain();
}
```

这段代码只有几十行，不包含任何重型 import。它通过动态 `import()` 实现按需加载，只有确认是交互式 REPL 才加载 `main.tsx`。

## Fast-path 分发

`cli.tsx` 的 Fast-path 分发遵循一个原则：**能跳过就跳过**。

用户敲 `claude --version`，只想在 0.1 秒内看到版本号。用户敲 `claude daemon`，只想启动守护进程。这些需求都不需要完整的交互式 CLI。

所以 `cli.tsx` 为常见命令提供了快速通道：

| 命令 | 处理方式 | 加载模块 |
|------|---------|----------|
| `--version` / `-v` | 直接打印，return | 零 |
| `daemon` | 动态导入 `daemon/main.js` | 仅守护进程 |
| `remote-control` / `rc` | 动态导入 `bridge/bridgeMain.js` | 仅桥接层 |
| `ps` / `logs` | 动态导入 `cli/bg.js` | 仅后台管理 |
| 默认（无子命令） | 动态导入 `main.js` | 完整 CLI |

这个设计让"非 REPL"命令的启动成本降到最低。`--version` 实测 12ms 完成，因为 Node.js/Bun 只需要解析和执行这几十行代码。

## 子命令按需加载

除了 Fast-path，`cli.tsx` 还支持一些内部子命令。这些子命令通常用于脚本或后台任务，启动速度同样敏感。

```typescript
// entrypoints/cli.tsx（子命令处理简化）
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
```

每个子命令只加载自己需要的模块。`remote-control` 加载桥接层，`ps` 加载后台管理。它们之间互不干扰。

这种按需加载有两个好处：

- **启动快**：不需要加载完整 CLI
- **内存少**：只加载必要的依赖

## 总结

- Claude Code 的真正入口是 `entrypoints/cli.tsx`，不是 `main.tsx`。
- `cli.tsx` 通过 Fast-path 分发，让 `--version` 等简单命令零模块加载、12ms 退出。
- 子命令按需加载，只导入必要的模块。
- 这个设计体现了 Claude Code 的启动哲学：**能跳过就跳过**。

> 下一篇：[启动优化](./02-optimization.md)，看 `main.tsx` 如何通过并行预取把启动时间从 250ms 降到 135ms。

## 参考链接

- [Claude Code 源码入口](file:///E:/Projects/claude-code/src/entrypoints/cli.tsx)
- [Anthropic Claude Code 官方文档](https://docs.anthropic.com/en/docs/claude-code/overview)
