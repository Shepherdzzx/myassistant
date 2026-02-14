# 🤖 Shell Assistant

 一个基于Openrouter模型的智能Shell助手，支持自动Markdown渲染输出。

## 🚀 功能特性

- 🧠 上下文记忆的多轮对话
- 🖥️ 安全的Shell命令执行
- 📝 自动Markdown渲染
- 📂 代码文件加载分析

## 📦 安装依赖

建议:创建虚拟环境

```
python - m venv venv
source venv/bin/activate #Linux/MacOS
#或 windows: venv\Scripts\activate
```

安装依赖

```
pip install -r requirements.txt
```

## ⚡ 快速开始

设置API密钥

```
export DASHSCOPE_API_KEY="your-api-key"
```

作者懒得改DASHSCOPE_API_KEY为OPENROUTER了,反正也没人用(

运行助手

```
python3 cli.py
```

命令行参数:

* --api-key：手动输入 key（优先级低于环境变量）
* --model：指定模型（如 "qwen/qwen3-max-thinking"、"openai/gpt-4o"）
* --shell-execution：启用 Shell 命令执行
* --enable-vector-memory：启用向量记忆
* --memory-stats：显示记忆统计后退出
* --clear-memories：清空所有记忆后退出

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
