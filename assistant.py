import json
import os
import readline
import subprocess
from typing import Dict, List, Optional

import requests

from memory import VectorMemory

# 添加rich库导入
try:
    from rich.console import Console
    from rich.markdown import Markdown
    from rich.theme import Theme

    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False
    print("警告: 未安装rich库，将使用普通文本输出", file=sys.stderr)


class ShellAssistant:
    def __init__(
        self,
        api_key: str,
        model: str = "arcee-ai/trinity-large-preview:free",
        max_history: int = 10,
        enable_vector_memory: bool = True,
    ):
        self.api_key = api_key
        self.model = model
        self.base_url = "https://openrouter.ai/api/v1/chat/completions"
        self.history: List[Dict] = []
        self.max_history = max_history
        self.context_file = os.path.expanduser("~/.shell_assistant_context.json")
        self.safe_commands = {
            "ls",
            "pwd",
            "echo",
            "cat",
            "grep",
            "find",
            "head",
            "tail",
            "wc",
            "sort",
            "uniq",
            "diff",
            "mkdir",
            "rmdir",
            "cp",
            "mv",
            "rm",
            "touch",
            "chmod",
            "chown",
            "date",
            "cal",
            "bc",
            "man",
            "which",
            "whoami",
            "id",
            "ps",
            "top",
            "df",
            "du",
            "free",
            "ping",
            "curl",
            "wget",
            "git",
            "tar",
            "zip",
            "unzip",
            "gzip",
        }
        self.enable_vector_memory = enable_vector_memory
        if self.enable_vector_memory:
            self.vector_memory = VectorMemory()
            print("Vector memory enabled")

        # 初始化rich控制台（如果可用）
        if RICH_AVAILABLE:
            custom_theme = Theme(
                {
                    "markdown.h1": "bold blue",
                    "markdown.h2": "bold cyan",
                    "markdown.h3": "bold green",
                    "markdown.code_block": "dim white on black",
                    "markdown.block_quote": "italic dim white",
                }
            )
            self.console = Console(theme=custom_theme, force_terminal=True)
        else:
            self.console = None

        self._load_context()
        readline.parse_and_bind("tab: complete")
        self.history_file = os.path.expanduser("~/.shell_assistant_history")
        if os.path.exists(self.history_file):
            readline.read_history_file(self.history_file)

    def _render_output(self, content: str):
        """渲染输出内容"""
        if RICH_AVAILABLE and self.console:
            try:
                markdown = Markdown(content)
                self.console.print(markdown)
            except Exception:
                # 如果渲染失败，回退到普通输出
                print(content)
        else:
            print(content)

    def _load_context(self):
        """从文件加载对话上下文"""
        try:
            if os.path.exists(self.context_file):
                with open(self.context_file, "r") as f:
                    self.history = json.load(f)
                    self.history = self.history[-self.max_history * 2 :]
        except (json.JSONDecodeError, IOError) as e:
            print(f"Warning: Failed to load context - {str(e)}")
            self.history = []

    def _save_context(self):
        """保存对话上下文到文件"""
        try:
            with open(self.context_file, "w") as f:
                json.dump(self.history, f)
        except IOError as e:
            print(f"Warning: Failed to save context - {str(e)}")

    def _setup_readline_history(self):
        """设置命令历史记录文件"""
        self.history_file = os.path.expanduser("~/.shell_assistant_history")
        if os.path.exists(self.history_file):
            readline.read_history_file(self.history_file)

    def _save_history(self):
        """保存命令历史"""
        readline.write_history_file(self.history_file)

    def _is_safe_command(self, command: str) -> bool:
        """检查命令是否在安全命令列表中"""
        cmd = command.strip().split()[0] if command.strip() else ""
        return cmd in self.safe_commands

    def execute_command(self, command: str) -> str:
        """执行Shell命令并返回输出"""
        if not command:
            return ""

        try:
            if not self._is_safe_command(command):
                return f"Error: Command '{command.split()[0]}' is not in the allowed list. For security reasons, I can only execute basic shell commands."

            if command.startswith("cd "):
                try:
                    path = command[3:].strip()
                    os.chdir(path)
                    return f"Changed directory to {os.getcwd()}"
                except Exception as e:
                    return f"Error changing directory: {str(e)}"

            process = subprocess.Popen(
                command,
                shell=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
            )

            stdout, stderr = process.communicate()

            if stderr:
                return f"Error: {stderr.strip()}"
            return stdout.strip()
        except Exception as e:
            return f"Error executing command: {str(e)}"

    def _stream_response(self, messages: List[Dict]) -> str:
        """流式获取模型响应"""
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://localhost:3000",
            "X-Title": "Shell Assistant",
        }
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        try:
            full_response = ""
            with requests.post(
                self.base_url, headers=headers, json=payload, stream=True
            ) as response:
                response.raise_for_status()

                for chunk in response.iter_lines():
                    if chunk:
                        chunk_str = chunk.decode("utf-8")
                        if chunk_str.startswith("data: "):
                            data = chunk_str[6:]
                            if data == "[DONE]":
                                break
                            try:
                                event = json.loads(data)
                                if "choices" in event and len(event["choices"]) > 0:
                                    delta = event["choices"][0].get("delta", {})
                                    content = delta.get("content", "")
                                    if content:
                                        full_response += content
                                        yield content
                            except json.JSONDecodeError:
                                pass
                return full_response
        except requests.exceptions.RequestException as e:
            yield f"\nError communicating with API: {str(e)}"
            return f"Error communicating with API: {str(e)}"

    def _trim_history(self):
        """修剪历史记录，确保不超过最大限制"""
        if len(self.history) > self.max_history * 2:
            self.history = self.history[-self.max_history * 2 :]

    def _detect_language(self, filename: str) -> str:
        """根据文件扩展名推测语言类型"""
        ext_map = {
            ".py": "Python",
            ".js": "JavaScript",
            ".ts": "TypeScript",
            ".java": "Java",
            ".cpp": "C++",
            ".c": "C",
            ".go": "Go",
            ".rs": "Rust",
            ".rb": "Ruby",
            ".php": "PHP",
            ".html": "HTML",
            ".css": "CSS",
            ".sql": "SQL",
            ".md": "Markdown",
            ".sh": "Shell",
            ".json": "JSON",
            ".xml": "XML",
            ".yaml": "YAML",
            ".yml": "YAML",
            ".txt": "Text",
            ".csv": "CSV",
            ".ini": "INI",
            ".cfg": "Config",
            ".toml": "TOML",
        }
        _, ext = os.path.splitext(filename)
        return ext_map.get(ext.lower(), "Unknown")

    def _load_code_file(self, file_path: str):
        """加载代码文件时也存入向量记忆"""
        if not os.path.exists(file_path):
            print(f"[Error] File not found: {file_path}")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                code_content = f.read()

            language = self._detect_language(file_path)

            message = (
                f"The following is a {language} source code file named `{os.path.basename(file_path)}`:\n"
                "```\n"
                f"{code_content}\n"
                "```"
            )

            self.history.append({"role": "user", "content": message})

            # 存入向量记忆
            if self.enable_vector_memory:
                self.vector_memory.store_code_memory(
                    role="user",
                    content=message,
                    file_path=file_path,
                    language=language,
                    metadata={"type": "code_load"},
                )

            self._trim_history()
            self._save_context()

            lines = code_content.split("\n")[:10]
            preview = "\n".join(lines)
            if len(code_content.split("\n")) > 10:
                preview += "\n..."
            print(f"[Info] Loaded file '{file_path}' ({language}) into context.")
            print(f"\nPreview of loaded code:\n{preview}\n")
        except Exception as e:
            print(f"[Error] Failed to load file: {e}")

    def get_memory_stats(self):
        """获取记忆库统计信息"""
        if not self.enable_vector_memory:
            return {"error": "Vector memory not enabled"}

        return self.vector_memory.get_memory_stats()

    def clear_all_memories(self):
        """清空所有记忆"""
        if not self.enable_vector_memory:
            print("[Warning] Vector memory not enabled")
            return

        self.vector_memory.clear_memory()
        self.history = []
        print("[Info] All memories and conversation history cleared")

    def chat(self, prompt: str, execute_shell: bool = False) -> str:
        """增强版对话函数，集成向量记忆"""

        # 1. 检索相关记忆
        relevant_memories = []
        if self.enable_vector_memory and len(prompt) > 10:
            relevant_memories = self.vector_memory.search_relevant_memories(
                prompt, top_k=3
            )

        # 2. 构建增强的prompt
        context = ""
        if relevant_memories:
            context = (
                "相关历史对话:\n"
                + "\n".join(
                    [
                        f"- {mem['metadata']['role']}: {mem['content'][:150]}..."
                        for mem in relevant_memories
                    ]
                )
                + "\n\n"
            )

        enhanced_prompt = context + f"当前问题: {prompt}"

        # 3. 调用LLM（使用增强后的prompt）
        self.history.append({"role": "user", "content": enhanced_prompt})

        response = ""
        # print("Assistant: ", end="", flush=True)

        # 4. 流式获取响应
        full_response = ""
        print("Assistant: ", end="", flush=True)
        for chunk in self._stream_response(self.history):
            full_response += chunk
            print(chunk, end="", flush=True)
        print()
        if RICH_AVAILABLE and self.console:
            try:
                self.console.print(Markdown(full_response))
            except Exception as e:
                print(f"Markdown rendering failed: {e}")
                pass

        # 5. 存储到向量记忆
        if self.enable_vector_memory:
            # 存储用户问题
            self.vector_memory.store_memory(
                role="user", content=prompt, metadata={"type": "query"}
            )

            # 存储AI回答
            self.vector_memory.store_memory(
                role="assistant", content=full_response, metadata={"type": "response"}
            )

        # 6. 更新对话历史
        if full_response:
            self.history.append({"role": "assistant", "content": full_response})
            self._trim_history()
            self._save_context()

        return full_response

    def run(self, shell_execution: bool = False):
        """启动交互式命令行界面"""
        print(f"""
        Shell Assistant (Qwen Model)
        -------------------------------------------------
        - 支持上下文记忆的多轮对话（最多保留{self.max_history}轮）
        - 输入普通文本进行对话
        - 输入!后跟命令执行Shell命令 (如: !ls -l)
        - 输入/load <file_path> 加载代码文件到上下文
        - 输入/clear 清除对话历史
        - 输入/history 查看当前对话历史
        - 输入/exit 退出程序
        -------------------------------------------------
        """)

        try:
            while True:
                try:
                    user_input = input("You: ").strip()
                    self._save_history()

                    if not user_input:
                        continue

                    if user_input.lower() == "/exit":
                        print("Goodbye!")
                        break

                    if user_input.lower() == "/clear":
                        self.history = []
                        print("\n对话历史已清除\n")
                        self._save_context()
                        continue

                    if user_input.lower() == "/history":
                        print("\n当前对话历史:")
                        for idx, msg in enumerate(self.history):
                            prefix = "User" if msg["role"] == "user" else "AI"
                            # 对于历史记录，使用普通显示
                            print(
                                f"{idx + 1}. {prefix}: {msg['content'][:200]}{'...' if len(msg['content']) > 200 else ''}"
                            )
                        print()
                        continue

                    if user_input.lower().startswith("/load "):
                        file_path = user_input[6:].strip()
                        self._load_code_file(file_path)
                        continue

                    self.chat(user_input, shell_execution)
                except KeyboardInterrupt:
                    print("\n(输入/exit退出)\n")
                    continue
        finally:
            self._save_history()
            self._save_context()
