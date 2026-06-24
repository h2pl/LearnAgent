# Ink 渲染器：React 如何在终端里"画 UI"

> `src/ink/ink.tsx` 不是简单的 `console.log` 美化——它是 1723 行的完整终端渲染引擎。从自定义 React Reconciler 到屏幕字符池、增量 diff 输出到焦点管理和鼠标点击的 hit-testing，Claude Code 把浏览器 React 的核心概念搬进了终端。

你好，我是江小湖。

上一章 [CLI 命令系统](../15-cli-commands/README.md) 讲到 `/init`、`/config` 等命令通过 `local-jsx` 类型返回 React 组件来渲染 UI。但 React 怎么在终端里渲染？DOM 没有，CSS 没有，甚至没有像素——终端只有字符网格。

答案是 Ink——Claude Code 的**自研终端 React 渲染器**。本文拆解它如何把 React 的 Virtual DOM 映射到字符终端。

## 目录

- [从 React DOM 到 React Terminal](#从-react-dom-到-react-terminal)
- [Ink 核心引擎：六层架构](#ink-核心引擎六层架构)
- [Custom Reconciler：如何把 div 变成字符](#custom-reconciler如何把-div-变成字符)
- [Screen 屏幕缓冲：字符池与增量 diff](#screen-屏幕缓冲字符池与增量-diff)
- [渲染管线：从 Fiber Tree 到 stdout](#渲染管线从-fiber-tree-到-stdout)
- [焦点管理：终端里的 Tab 键](#焦点管理终端里的-tab-键)
- [总结](#总结)
- [参考链接](#参考链接)

## 从 React DOM 到 React Terminal

浏览器 React 的渲染链是：

```text
React Component Tree → React DOM Reconciler → DOM API → Browser Pixels
```

Ink 替换了整个下半截：

```text
React Component Tree → Ink Reconciler → Yoga Layout → Terminal Screen Buffer → stdout ANSI
```

关键差异：

| 层面 | 浏览器 React | Ink |
|------|------------|-----|
| Layout Engine | CSS (browser's own) | Yoga Layout (cross-platform Flexbox) |
| Output | DOM nodes → pixels | Character grid → ANSI escape sequences |
| Event Model | DOM events (onClick, onKeyDown) | Keypress parsing + hit-testing |
| Styling | CSS properties | Ink styles (color, bold, italic, etc.) |
| Component Primitives | div, span, input | Box, Text, Newline |

## Ink 核心引擎：六层架构

`src/ink/` 目录（43 个文件）可以分六层：

```text
┌──────────────────────────────────────────────┐
│ 1. Components (18 files, React)              │  ← App.tsx, Box.tsx, Text.tsx...
├──────────────────────────────────────────────┤
│ 2. Reconciler (reconciler.ts, dom.ts)        │  ← 自定义 React Renderer
├──────────────────────────────────────────────┤
│ 3. Layout Engine (Yoga via native-ts)        │  ← Flexbox 布局计算
├──────────────────────────────────────────────┤
│ 4. Screen Buffer (screen.ts, 50KB)           │  ← 字符网格 + 增量 diff
├──────────────────────────────────────────────┤
│ 5. Output Pipeline (output.ts, render-node)  │  ← DOM → ANSI → stdout
├──────────────────────────────────────────────┤
│ 6. Input & Events (App.tsx, parse-keypress)  │  ← stdin keypress → React events
└──────────────────────────────────────────────┘
```

### 层 1：组件

组件层是对浏览器 React 的终端等价物。`Box.tsx`（21KB）替代 `div`，`Text.tsx`（17KB）替代 `span`，`ScrollBox.tsx`（32KB）实现终端内的滚动区域。

### 层 2：Reconciler

`reconciler.ts`（514 行）实现了 React Reconciler 的所有接口，把 React 的 Fiber tree 操作翻译成对 `dom.ts` 的调用：

```typescript
// reconciliar.ts — 核心接口简化

const reconciler = createReconciler({
  createInstance(type, props) {
    return createNode(type)  // 创建 DOM 节点（字符盒模型）
  },
  createTextInstance(text) {
    return createTextNode(text)  // 创建文本节点
  },
  appendChild(parent, child) {
    appendChildNode(parent, child)  // 挂载子节点
  },
  removeChild(parent, child) {
    removeChildNode(parent, child)  // 移除子节点
  },
  commitUpdate(instance, updatePayload, type, oldProps, newProps) {
    // diff props → 更新样式/属性
  },
  // ... 共约 20 个接口方法
})
```

注意这里的"DOM"不是浏览器 DOM——它是 `dom.ts` 定义的终端字符盒模型。

### 层 3：Layout Engine

Yoga Layout 是 Facebook 开源的跨平台 Flexbox 引擎（C++ 原生实现，通过 `native-ts/yoga-layout` 绑定）。Ink 用 Yoga 计算每个组件在字符网格中的绝对坐标：

```typescript
// 每个 Box 组件计算 layout 后得到：
{
  left: 0,    // 列偏移
  top: 3,     // 行偏移
  width: 80,  // 字符宽
  height: 5,  // 字符高
}
```

### 层 4：Screen Buffer

`screen.ts`（50KB，1427 行）维护一个二维字符网格。每个 cell 存储字符引用、样式引用、超链接引用——都用索引（整数）而非字符串，通过共享池（`CharPool`、`StylePool`、`HyperlinkPool`）实现内存复用。

### 层 5：Output Pipeline

`render-node-to-output.ts`（64KB）把 DOM 树转换为 ANSI escape sequence 输出。`output.ts`（26KB）管理实际的 stdout 写入和增量 diff。

### 层 6：Input & Events

`App.tsx`（98KB，658 行）管理 stdin 事件循环、keypress 解析、鼠标事件、focus/blur 事件和文本选择。

## Custom Reconciler：如何把 div 变成字符

### 关键抽象：DOM 不是 DOM

`dom.ts` 定义了 Ink 自己的"DOM"：

```typescript
// dom.ts — 核心接口简化

type DOMElement = {
  nodeName: ElementNames  // 'Box' | 'Text' | 'Newline' | 'ScrollBox' ...
  style: Styles           // { color, backgroundColor, bold, ... }
  attributes: Record<string, DOMNodeAttribute>
  childNodes: DOMNode[]
  yogaNode: YogaNode      // Flexbox 节点引用
  // 渲染时计算：
  x: number               // 绝对列坐标
  y: number               // 绝对行坐标
  width: number           // 字符宽
  height: number          // 字符高
}

type TextNode = {
  nodeName: '#text'
  nodeValue: string
  style: TextStyles
  yogaNode: YogaNode
}
```

每个 `<Box>` 被创建为一个 `DOMElement`（nodeName='Box'），每个文本内容被创建为一个 `TextNode`。

### 布局管线

1. **Reconciler 创建节点** → `createInstance('Box')` 返回 `DOMElement`
2. **Yoga 计算 layout** → 所有节点获得 `x/y/width/height`
3. **Render to output** → 把 DOM 树"画"到 Screen Buffer 上
4. **Diff & Write** → 只输出变化的部分到 stdout

## Screen 屏幕缓冲：字符池与增量 diff

`screen.ts` 是整个渲染引擎的核心——它在 50KB 文件中实现了终端屏幕的完整虚拟化。

### CharPool：字符串到整数的池化

每个终端的 cell 存一个字符。如果直接用字符串存储，每个 cell 就是一个 JS 字符串对象（~40 字节）。50 行 × 200 列的终端 = 10,000 cells = 400KB 只是字符。

`CharPool` 用整数索引替代字符串：

```typescript
class CharPool {
  private strings: string[] = [' ', '']   // 索引 0=空格, 1=空
  private ascii: Int32Array                // ASCII 快路径：charCode→索引

  intern(char: string): number {
    if (char.length === 1 && char.charCodeAt(0) < 128) {
      return this.ascii[char.charCodeAt(0)]  // O(1) 查找
    }
    return this.stringMap.get(char)          // Map 查找
  }
}
```

**ASCII 快路径**是最关键的性能优化——大多数终端的字符是 ASCII（代码、英文文本），不需要走 Map 查找。`ascii` 是一个 `Int32Array`，O(1) 索引。

### StylePool 和 HyperlinkPool

同样的池化思想应用于样式和超链接：

```typescript
// 每个 cell 存三个索引：
{
  charId: 42,        // CharPool 索引
  styleId: 3,        // StylePool 索引
  hyperlinkId: 0,    // 0 = 无超链接
}
```

这样每个 cell 只需要 3 个整数（~12 字节），而非 3 个字符串对象（~120 字节）——**节省 10 倍内存**。

### 增量 diff：只输出变化

`output.ts` 实现了完整的增量 diff 算法。两个连续的 frame 之间：

```typescript
// 简化逻辑
function diffFrames(prev: Screen, next: Screen): Patch[] {
  const patches = []
  for (let row = 0; row < height; row++) {
    for (let col = 0; col < width; col++) {
      if (prev.cells[row][col] !== next.cells[row][col]) {
        patches.push({
          type: 'cell_change',
          row, col,
          char: next.chars.get(next.cells[row][col].charId),
          style: next.styles.get(next.cells[row][col].styleId)
        })
      }
    }
  }
  return patches  // 只包含实际变化的 cells
}
```

不是每帧都重新绘制整个屏幕——只输出变化的部分。在 50fps 的渲染速度下，这节省了大量的 stdout 写入。

## 渲染管线：从 Fiber Tree 到 stdout

完整的渲染管线（每次 frame）：

```text
┌─────────────────────────────────────────────────────────────┐
│ 1. React State Change (setState / props change)             │
├─────────────────────────────────────────────────────────────┤
│ 2. React Reconciler computes diff (Fiber Tree → DOM Tree)   │
├─────────────────────────────────────────────────────────────┤
│ 3. Yoga Layout re-layouts affected subtrees                 │
├─────────────────────────────────────────────────────────────┤
│ 4. renderNodeToOutput: DOM Tree → Screen Buffer             │
│    - 遍历 DOM 树，将每个 element 渲染到 cell grid           │
├─────────────────────────────────────────────────────────────┤
│ 5. Screen Diff: current Screen vs new Screen                │
├─────────────────────────────────────────────────────────────┤
│ 6. Output Patch: ANSI escape sequences → stdout             │
│    - 光标移动到 target cell                                 │
│    - 输出字符 + 样式 ANSI                                    │
│    - 回到 park position（隐藏光标位置）                     │
└─────────────────────────────────────────────────────────────┘
```

### Frame Rate 管理

`ink.tsx` 用 `FRAME_INTERVAL_MS`（16.67ms ≈ 60fps）控制帧率。但实际的渲染是**按需触发**的——只有 state 变化时才 schedule render。Ink 类中的 `scheduleRender` 是一个 throttled 函数：

```typescript
class Ink {
  private scheduleRender: (() => void) & { cancel?: () => void }

  // 只有 state 变化时才 schedule
  // React Reconciler 的 onCommit 回调触发
}
```

### Alt Screen 模式

Claude Code 使用终端"alt screen"模式——切换到独立的屏幕缓冲区，退出后恢复原状：

```typescript
// 进入 alt screen: ENTER_ALT_SCREEN
// 退出 alt screen: EXIT_ALT_SCREEN
// Cursor parking: 光标隐藏在右下角，避免闪烁
```

## 焦点管理：终端里的 Tab 键

终端的键盘输入和浏览器不同——没有内置的 focus/tab 顺序。Ink 自己实现了焦点系统：

### FocusManager

`focus.ts` 实现了一个完整的焦点管理器：

```typescript
class FocusManager {
  private focusableNodes: DOMElement[] = []  // 所有可聚焦节点
  private activeNode: DOMElement | null = null

  focusNext()    // Tab → 下一个可聚焦节点
  focusPrevious() // Shift+Tab → 上一个
  activate(node)  // Click/Enter → 激活节点
}
```

### 与 React 的集成

Ink 通过在 `FocusManager` 的变更时触发 Reconciler commit 来让 React 感知焦点变化：

```typescript
// focus.ts
this.activeNode = nextNode
// → 标记 dirty
// → schedule render
// → React 组件可以通过 FocusContext 读取焦点状态
```

这样 `<Button>` 可以在被 focus 时显示高亮边框——完全和浏览器 React 一样的模式。

### 鼠标点击的 hit-testing

`hit-test.ts` 把鼠标坐标 `(col, row)` 反向映射到 DOM 节点：

```typescript
function hitTest(x: number, y: number, root: DOMElement): DOMElement | null {
  // 遍历 DOM 树，从叶子到根
  // 返回第一个包含 (x, y) 坐标的节点
  // onClick 事件沿树冒泡
}
```

这实现了完整的鼠标交互——在终端里也能"点击按钮"。

## 总结

Ink 不是"语法高亮的颜色库"，而是一个**完整的终端 React 渲染器**。关键设计：

1. **Custom Reconciler**——替换 React DOM Reconciler，Fiber tree → Yoga layout → Screen Buffer
2. **三层池化**——CharPool/StylePool/HyperlinkPool 用整数索引替代字符串，每个 cell 仅 12 字节
3. **增量 diff 输出**——不是每帧重绘全屏，只输出变化的 ANSI escape sequences
4. **自研焦点系统**——终端没有 Tab 导航和焦点管理，Ink 从零实现了完整的 FocusManager
5. **鼠标 hit-testing**——把鼠标坐标反向映射到 React 组件树，支持 onClick/onHover

这些设计让 Claude Code 能用 React 组件写全功能的终端 UI（/init 的多步表单、/config 的选项面板、/doctor 的诊断报告），而不需要退回到手动拼接 ANSI 代码。

下一篇文章 [组件树与交互](./02-components.md) 拆解 98KB 的 App.tsx 和 89 个 React 组件如何组织终端界面。

## 参考链接

- `src/ink/ink.tsx` — Ink 核心引擎（1723 行，253KB）
- `src/ink/reconciler.ts` — 自定义 React Reconciler（514 行）
- `src/ink/screen.ts` — 屏幕缓冲与字符池（1427 行，50KB）
- `src/ink/dom.ts` — 终端 DOM 抽象（15KB）
- `src/ink/output.ts` — 增量 diff 输出（26KB）
- `src/ink/focus.ts` — 焦点管理器
- `src/ink/hit-test.ts` — 鼠标点击的 hit-testing
