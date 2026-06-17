# -*- coding: utf-8 -*-
"""校验所有 SVG 配图的 XML 合法性，并自动修复常见问题。

背景：之前的 system-prompt-structure.svg 因为 `& How` 未转义为 `&amp;`
导致整张 SVG 在浏览器中无法渲染。本脚本自动检测并修复这类问题。

用法：
    python scripts/validate_svg.py                  # 检查所有 SVG
    python scripts/validate_svg.py --fix             # 自动修复可识别的问题
    python scripts/validate_svg.py path/to/file.svg # 检查指定文件
"""
import os
import sys
import glob
import argparse
import xml.etree.ElementTree as ET


ASSETS_DIRS = [
    r"e:\Learning\AgentDevGuide\assets\01-llm-basics",
    r"e:\Learning\AgentDevGuide\assets\02-model-access",
    r"e:\Learning\AgentDevGuide\assets\03-prompt-engineering",
    r"e:\Learning\AgentDevGuide\assets\04-tool-use",
    r"e:\Learning\AgentDevGuide\assets\05-agent-loop",
    r"e:\Learning\AgentDevGuide\assets\06-rag-pipeline",
]


def check_svg(path):
    """返回 (ok, error_msg, parsed_root)"""
    try:
        tree = ET.parse(path)
        return True, None, tree.getroot()
    except ET.ParseError as e:
        return False, str(e), None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", None


def auto_fix_common_issues(content):
    """修复 SVG 中常见的未转义字符。返回 (new_content, fixes_applied)"""
    fixes = []

    # 修复 1：text 节点内未转义的 & (后续跟非实体引用的字符)
    # 例如 "What & How"  →  "What &amp; How"
    # 但要保留已经合法的实体：&amp; &lt; &gt; &quot; &apos; &nbsp; &#1234;
    import re
    pattern = re.compile(r'&(?!(?:amp|lt|gt|quot|apos|nbsp|#\d+|#x[0-9a-fA-F]+);)')

    if pattern.search(content):
        new_content = pattern.sub('&amp;', content)
        fixes.append(f"修复未转义的 & （{len(pattern.findall(content))} 处）")
        content = new_content

    return content, fixes


def main():
    ap = argparse.ArgumentParser(description='SVG 配图合法性校验')
    ap.add_argument('--fix', action='store_true', help='自动修复可识别的问题')
    ap.add_argument('files', nargs='*', help='要检查的 SVG 文件（默认检查所有 assets/）')
    args = ap.parse_args()

    # 收集目标文件
    if args.files:
        svg_files = args.files
    else:
        svg_files = []
        for d in ASSETS_DIRS:
            if os.path.isdir(d):
                svg_files.extend(glob.glob(os.path.join(d, '*.svg')))

    if not svg_files:
        print("[INFO] 没有找到 SVG 文件")
        return 0

    print(f"检查 {len(svg_files)} 个 SVG 文件 {'(auto-fix 模式)' if args.fix else ''}\n")

    total_errors = 0
    total_fixed = 0

    for path in sorted(svg_files):
        if not os.path.exists(path):
            print(f"[MISS] {path}")
            continue

        ok, err, _ = check_svg(path)
        if ok:
            print(f"[OK]   {os.path.basename(path)}")
            continue

        total_errors += 1
        print(f"[FAIL] {os.path.basename(path)}")
        print(f"       错误: {err}")

        if args.fix:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()

            new_content, fixes = auto_fix_common_issues(content)

            if fixes:
                # 修复后重新校验
                re_ok, re_err, _ = check_svg_from_string(new_content)
                if re_ok:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    total_fixed += 1
                    print(f"       ✓ 已修复: {'; '.join(fixes)}")
                else:
                    print(f"       ✗ 修复后仍无法解析: {re_err}")
            else:
                print(f"       ✗ 未识别出可自动修复的问题")

    print(f"\n{'='*60}")
    print(f"总计: {len(svg_files)} 个文件，{total_errors} 个错误" +
          (f"，已修复 {total_fixed} 个" if args.fix else ''))

    return 0 if total_errors == 0 or (args.fix and total_fixed == total_errors) else 1


def check_svg_from_string(content):
    """从字符串校验 SVG"""
    try:
        root = ET.fromstring(content)
        return True, None, root
    except ET.ParseError as e:
        return False, str(e), None
    except Exception as e:
        return False, f"{type(e).__name__}: {e}", None


if __name__ == '__main__':
    sys.exit(main())
