# 🤖 Shell Assistant

 一个基于阿里云Qwen模型的智能Shell助手，支持自动Markdown渲染输出。

## 🚀 功能特性

- 🧠 上下文记忆的多轮对话
- 🖥️ 安全的Shell命令执行
- 📝 自动Markdown渲染
- 📂 代码文件加载分析

## 📦 安装依赖

```
pip install rich requests
```

## ⚡ 快速开始

设置API密钥

```
export DASHSCOPE_API_KEY="your-api-key"
```

运行助手

```
python3 cli.py --shell-execution
```

## 🎯 使用方法

    对话模式

 You: 解释Python装饰器
 Assistant: 自动渲染的Markdown回答...

    命令执行

 You: !ls -la
 Assistant: 执行命令结果...

    加载文件

 You: /load assistant.py
 Assistant: 加载文件内容到上下文


## 🛠️ 命令列表

 • /exit - 退出程序
 • /clear - 清除对话历史
 • /history - 查看对话历史
 • /load <文件路径> - 加载代码文件
