#!/usr/bin/env python3
"""
Shell Assistant CLI
"""

import argparse
import os
import sys
from cgi import print_form
from getpass import getpass

from assistant import ShellAssistant


def main():
    parser = argparse.ArgumentParser(description="Shell Assistant with AI capabilities")
    parser.add_argument("--api-key", type=str, help="DashScope API key")
    parser.add_argument(
        "--model",
        type=str,
        default="arcee-ai/trinity-large-preview:free",
        help="Model to use (default: qwen3-coder-plus)",
    )
    parser.add_argument(
        "--max-history",
        type=int,
        default=10,
        help="Maximum number of conversation rounds to keep (default: 10)",
    )
    parser.add_argument(
        "--shell-execution", action="store_true", help="Enable shell command execution"
    )
    parser.add_argument(
        "--enable-vector-memory",
        action="store_true",
        help="Enable vector memory system",
    )
    parser.add_argument(
        "--memory-stats", action="store_true", help="Show memory statistics"
    )
    parser.add_argument(
        "--clear-memories", action="store_true", help="Clear all memories"
    )
    args = parser.parse_args()

    # 获取API密钥
    api_key = args.api_key or os.getenv("DASHSCOPE_API_KEY")
    if not api_key:
        api_key = getpass("请输入您的 DashScope API 密钥: ")
        if not api_key:
            print("错误: 必须提供API密钥")
            sys.exit(1)

    # 创建助手实例
    assistant = ShellAssistant(
        api_key=api_key, model=args.model, max_history=args.max_history
    )

    # 运行助手
    try:
        assistant.run(shell_execution=args.shell_execution)
    except KeyboardInterrupt:
        print("\n再见!")
        sys.exit(0)
    except Exception as e:
        print(f"发生错误: {e}")
        sys.exit(1)
    finally:
        if args.memory_stats:
            assistant.get_memory_stats()
            sys.exit(0)
        if args.clear_memories:
            assistant.clear_all_memories()
            sys.exit(0)


if __name__ == "__main__":
    main()
