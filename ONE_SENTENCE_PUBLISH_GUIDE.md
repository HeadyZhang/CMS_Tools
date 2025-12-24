# 一句话生成文章并发布到 WordPress - 技术实现指南

## 概述

本文档详细说明 GEO Chatbot 如何实现"一句话生成文章并发布到 WordPress"功能，并提供可落地的复现指导，让此功能可以迁移到其他 Chatbot 系统。

---

## 🎯 功能演示

**用户输入：**
```
在我的网站上发布一篇关于GEO的文章，标题叫《GEO实战指南2025》
```

**系统行为：**
1. LLM 理解用户意图
2. 自动生成文章内容
3. 调用 `create_article` 创建草稿
4. 调用 `publish_article` 发布上线
5. 返回文章链接给用户

---

## 🏗️ 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                         用户输入                                  │
│              "发布一篇关于GEO的文章"                               │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     ReAct Agent (核心)                           │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  System Prompt (包含工具描述 + ReAct 格式要求)            │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                │                                 │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  LLM (Claude/OpenAI)                                     │   │
│  │  输出: Thought → Action → Action Input                   │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                │                                 │
│                                ▼                                 │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  解析器 (_parse_llm_output)                              │   │
│  │  提取: action="create_article", action_input={...}       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Tool Registry (工具注册表)                    │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │create_article│ │publish_article│ │list_articles │ ...       │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     CMS Tools (WordPress API)                    │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │  POST /sites/{site_id}/posts/new                         │   │
│  │  POST /sites/{site_id}/posts/{id} (status=publish)       │   │
│  └─────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────┐
│                     WordPress.com                                │
│                  文章发布成功 ✓                                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🔑 核心组件详解

### 1. ReAct Agent (推理+行动框架)

**文件**: `core/agent.py`

ReAct (Reasoning + Acting) 是让 LLM 能够调用外部工具的关键框架。

#### 核心原理

```python
# ReAct 循环
while iteration < max_iterations:
    # 1. 调用 LLM，获取 Thought + Action
    llm_output = self._call_llm(messages)
    
    # 2. 解析输出
    thought, action, action_input, final_answer = self._parse_llm_output(llm_output)
    
    # 3. 如果有 Final Answer，返回结果
    if final_answer:
        return final_answer
    
    # 4. 如果有 Action，执行工具
    if action:
        observation = self._execute_action(action, action_input)
        
        # 5. 将 Observation 反馈给 LLM
        messages.append({"role": "user", "content": f"Observation: {observation}"})
```

#### System Prompt 模板 (关键!)

```python
SYSTEM_PROMPT_TEMPLATE = '''你是 {agent_name}，一个专业的助手。

## ReAct 框架

你使用 ReAct (Reasoning + Acting) 框架来解决问题。每次回复必须遵循以下格式:

### 当需要使用工具时:
```
Thought: [详细分析当前情况，说明为什么需要使用这个工具]
Action: [工具名称，必须是可用工具之一]
Action Input: [有效的 JSON 格式参数]
```

### 当任务完成时:
```
Thought: [总结整个过程和结果]
Final Answer: [给用户的完整回复]
```

## 可用工具

{tools_description}

## 重要规则

1. **每次只调用一个工具** - 等待 Observation 后再决定下一步
2. **Action Input 必须是有效 JSON** - 注意引号和格式
3. **必须有 Final Answer** - 每个任务最终都要给出明确回复
'''
```

#### 解析器 (关键修复点!)

```python
def _parse_llm_output(self, text: str):
    """
    解析 LLM 输出
    
    优先级: Action > Final Answer
    (如果有 Action 就先执行，不要直接跳到 Final Answer)
    """
    thought = None
    action = None
    action_input = None
    final_answer = None
    
    # 提取 Thought
    thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)', text, re.DOTALL)
    if thought_match:
        thought = thought_match.group(1).strip()
    
    # 优先检查 Action（而不是 Final Answer）
    action_match = re.search(r'Action:\s*(\w+)', text)
    if action_match:
        action = action_match.group(1)
        
        # 提取 Action Input (JSON)
        input_match = re.search(r'Action Input:\s*(\{[\s\S]*?\})', text)
        if input_match:
            action_input = json.loads(input_match.group(1))
        
        # 有 Action 就返回，不检查 Final Answer
        return thought, action, action_input, None
    
    # 没有 Action 才检查 Final Answer
    final_match = re.search(r'Final Answer:\s*(.+)', text, re.DOTALL)
    if final_match:
        final_answer = final_match.group(1).strip()
    
    return thought, action, action_input, final_answer
```

---

### 2. Tool Registry (工具注册系统)

**文件**: `tools/base.py`

工具注册系统管理所有可用工具，提供统一的调用接口。

#### 核心类

```python
class ToolRegistry:
    """工具注册表 - 单例模式"""
    
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def register(self, tool: BaseTool):
        """注册工具"""
        self._tools[tool.definition.name] = tool
    
    def execute(self, name: str, arguments: dict):
        """执行工具"""
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"工具不存在: {name}"}
        return tool(**arguments)
    
    def get_react_descriptions(self) -> str:
        """生成 ReAct 格式的工具描述（注入到 System Prompt）"""
        descriptions = []
        for tool in self._tools.values():
            descriptions.append(tool.definition.to_react_description())
        return "\n".join(descriptions)

# 全局注册表
registry = ToolRegistry()
```

#### 工具定义

```python
@dataclass
class ToolParameter:
    name: str           # 参数名
    type: str           # 类型: string, integer, boolean, array
    description: str    # 描述
    required: bool = False
    default: Any = None

@dataclass
class ToolDefinition:
    name: str                      # 工具名称
    description: str               # 工具描述
    category: ToolCategory         # 分类
    parameters: List[ToolParameter]  # 参数列表
    
    def to_react_description(self) -> str:
        """生成 ReAct 格式描述"""
        params_desc = []
        for param in self.parameters:
            req = "(必填)" if param.required else "(可选)"
            params_desc.append(f"  - {param.name} ({param.type}) {req}: {param.description}")
        
        return f"""**{self.name}**
{self.description}
参数:
{chr(10).join(params_desc)}"""
```

#### 注册装饰器

```python
def register_tool(tool_class):
    """装饰器：自动注册工具类"""
    instance = tool_class()
    registry.register(instance)
    return tool_class

# 使用示例
@register_tool
class CreateArticleTool(BaseTool):
    @property
    def definition(self) -> ToolDefinition:
        return ToolDefinition(
            name="create_article",
            description="在 WordPress 中创建新文章",
            category=ToolCategory.CMS,
            parameters=[
                ToolParameter("title", "string", "文章标题", required=True),
                ToolParameter("content", "string", "文章内容", required=True),
                ToolParameter("status", "string", "状态", default="draft"),
            ]
        )
    
    def execute(self, **kwargs):
        return create_article(**kwargs)
```

---

### 3. CMS Tools (WordPress API 封装)

**文件**: `geo_agent/tools/cms_tools.py`

封装 WordPress.com REST API，提供简洁的 Python 接口。

#### API 请求封装

```python
WP_ACCESS_TOKEN = os.getenv("WP_ACCESS_TOKEN")
WP_SITE_ID = os.getenv("WP_SITE_ID")
WP_API_BASE = "https://public-api.wordpress.com/rest/v1.1"

def _make_request(method: str, endpoint: str, data: dict = None, params: dict = None):
    """统一的 API 请求函数"""
    url = f"{WP_API_BASE}{endpoint}"
    headers = {
        "Authorization": f"Bearer {WP_ACCESS_TOKEN}",
        "Content-Type": "application/json"
    }
    
    try:
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=30)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, json=data, timeout=30)
        
        result = response.json()
        
        if response.status_code in [200, 201]:
            return {"success": True, "data": result}
        else:
            return {"success": False, "error": result.get("message", str(result))}
            
    except Exception as e:
        return {"success": False, "error": str(e)}
```

#### 核心工具函数

```python
def create_article(title, content, status="draft", categories=None, tags=None):
    """创建文章"""
    payload = {
        "title": title,
        "content": content,
        "status": status
    }
    if categories:
        payload["categories"] = ",".join(categories)
    if tags:
        payload["tags"] = ",".join(tags)
    
    result = _make_request("POST", f"/sites/{WP_SITE_ID}/posts/new", data=payload)
    
    if result["success"]:
        post = result["data"]
        return {
            "success": True,
            "data": {
                "post_id": post["ID"],
                "title": post["title"],
                "status": post["status"],
                "url": post["URL"],
                "edit_url": f"https://wordpress.com/post/{WP_SITE_ID}/{post['ID']}"
            }
        }
    return result

def publish_article(post_id, schedule_time=None):
    """发布文章"""
    payload = {"status": "publish"}
    if schedule_time:
        payload["status"] = "future"
        payload["date"] = schedule_time
    
    result = _make_request("POST", f"/sites/{WP_SITE_ID}/posts/{post_id}", data=payload)
    
    if result["success"]:
        post = result["data"]
        return {
            "success": True,
            "data": {
                "post_id": post["ID"],
                "status": post["status"],
                "url": post["URL"],
                "message": "文章已发布"
            }
        }
    return result
```

---

## 📋 复现步骤

### Step 1: 创建工具注册系统

```python
# tools/base.py

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, Any, List, Optional

@dataclass
class ToolParameter:
    name: str
    type: str
    description: str
    required: bool = False
    default: Any = None

@dataclass
class ToolDefinition:
    name: str
    description: str
    parameters: List[ToolParameter]
    
    def to_react_description(self) -> str:
        params = "\n".join([
            f"  - {p.name} ({p.type}): {p.description}"
            for p in self.parameters
        ])
        return f"**{self.name}**\n{self.description}\n参数:\n{params}"

class BaseTool(ABC):
    @property
    @abstractmethod
    def definition(self) -> ToolDefinition:
        pass
    
    @abstractmethod
    def execute(self, **kwargs) -> Dict[str, Any]:
        pass
    
    def __call__(self, **kwargs):
        return self.execute(**kwargs)

class ToolRegistry:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._tools = {}
        return cls._instance
    
    def register(self, tool: BaseTool):
        self._tools[tool.definition.name] = tool
    
    def execute(self, name: str, arguments: dict):
        tool = self._tools.get(name)
        if not tool:
            return {"success": False, "error": f"工具不存在: {name}"}
        return tool(**arguments)
    
    def get_react_descriptions(self) -> str:
        return "\n\n".join([
            t.definition.to_react_description() 
            for t in self._tools.values()
        ])

registry = ToolRegistry()

def register_tool(cls):
    registry.register(cls())
    return cls
```

### Step 2: 实现 CMS 工具

```python
# tools/cms.py

import os
import requests
from tools.base import BaseTool, ToolDefinition, ToolParameter, register_tool

WP_TOKEN = os.getenv("WP_ACCESS_TOKEN")
WP_SITE_ID = os.getenv("WP_SITE_ID")
WP_API = "https://public-api.wordpress.com/rest/v1.1"

def wp_request(method, endpoint, data=None):
    headers = {"Authorization": f"Bearer {WP_TOKEN}"}
    url = f"{WP_API}{endpoint}"
    
    if method == "POST":
        resp = requests.post(url, headers=headers, json=data, timeout=30)
    else:
        resp = requests.get(url, headers=headers, timeout=30)
    
    if resp.status_code in [200, 201]:
        return {"success": True, "data": resp.json()}
    return {"success": False, "error": resp.text}

@register_tool
class CreateArticleTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="create_article",
            description="在 WordPress 创建新文章",
            parameters=[
                ToolParameter("title", "string", "文章标题", required=True),
                ToolParameter("content", "string", "文章内容 HTML", required=True),
                ToolParameter("status", "string", "状态: draft/publish", default="draft"),
            ]
        )
    
    def execute(self, title, content, status="draft", **kwargs):
        result = wp_request("POST", f"/sites/{WP_SITE_ID}/posts/new", {
            "title": title,
            "content": content,
            "status": status
        })
        if result["success"]:
            post = result["data"]
            return {
                "success": True,
                "data": {
                    "post_id": post["ID"],
                    "title": post["title"],
                    "url": post["URL"]
                }
            }
        return result

@register_tool
class PublishArticleTool(BaseTool):
    @property
    def definition(self):
        return ToolDefinition(
            name="publish_article",
            description="发布草稿文章",
            parameters=[
                ToolParameter("post_id", "integer", "文章 ID", required=True),
            ]
        )
    
    def execute(self, post_id, **kwargs):
        result = wp_request("POST", f"/sites/{WP_SITE_ID}/posts/{post_id}", {
            "status": "publish"
        })
        if result["success"]:
            return {
                "success": True,
                "data": {
                    "post_id": post_id,
                    "url": result["data"]["URL"],
                    "message": "文章已发布"
                }
            }
        return result
```

### Step 3: 实现 ReAct Agent

```python
# agent.py

import re
import json
import requests
from tools.base import registry

class ReActAgent:
    SYSTEM_PROMPT = '''你是一个智能助手，使用 ReAct 框架解决问题。

## 格式要求

使用工具时:
```
Thought: [分析情况]
Action: [工具名称]
Action Input: {"param": "value"}
```

任务完成时:
```
Thought: [总结]
Final Answer: [回复用户]
```

## 可用工具

{tools}

## 规则
1. 每次只调用一个工具
2. Action Input 必须是有效 JSON
3. 等待 Observation 后再继续
'''

    def __init__(self, api_key, model="claude-sonnet-4-20250514"):
        self.api_key = api_key
        self.model = model
        self.messages = []
        
        # 构建 System Prompt
        tools_desc = registry.get_react_descriptions()
        self.system_prompt = self.SYSTEM_PROMPT.format(tools=tools_desc)
    
    def _call_llm(self, messages):
        """调用 Claude API"""
        resp = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": self.api_key,
                "Content-Type": "application/json",
                "anthropic-version": "2023-06-01"
            },
            json={
                "model": self.model,
                "max_tokens": 4000,
                "system": self.system_prompt,
                "messages": messages
            },
            timeout=120
        )
        return resp.json()["content"][0]["text"]
    
    def _parse_output(self, text):
        """解析 LLM 输出"""
        # 提取 Thought
        thought_match = re.search(r'Thought:\s*(.+?)(?=Action:|Final Answer:|$)', text, re.DOTALL)
        thought = thought_match.group(1).strip() if thought_match else None
        
        # 优先检查 Action
        action_match = re.search(r'Action:\s*(\w+)', text)
        if action_match:
            action = action_match.group(1)
            input_match = re.search(r'Action Input:\s*(\{[\s\S]*?\})', text)
            action_input = json.loads(input_match.group(1)) if input_match else {}
            return thought, action, action_input, None
        
        # 检查 Final Answer
        final_match = re.search(r'Final Answer:\s*(.+)', text, re.DOTALL)
        final_answer = final_match.group(1).strip() if final_match else None
        
        return thought, None, None, final_answer
    
    def chat(self, user_message, max_iterations=10):
        """处理用户消息"""
        self.messages.append({"role": "user", "content": user_message})
        
        for _ in range(max_iterations):
            # 调用 LLM
            output = self._call_llm(self.messages)
            thought, action, action_input, final_answer = self._parse_output(output)
            
            # 任务完成
            if final_answer:
                self.messages.append({"role": "assistant", "content": output})
                return final_answer
            
            # 执行工具
            if action:
                observation = registry.execute(action, action_input)
                observation_str = json.dumps(observation, ensure_ascii=False)
                
                self.messages.append({"role": "assistant", "content": output})
                self.messages.append({"role": "user", "content": f"Observation: {observation_str}"})
        
        return "处理超时"
```

### Step 4: 使用示例

```python
# main.py

import os
from agent import ReActAgent

# 设置环境变量
os.environ["WP_ACCESS_TOKEN"] = "your-token"
os.environ["WP_SITE_ID"] = "your-site-id"

# 导入工具 (触发注册)
import tools.cms

# 创建 Agent
agent = ReActAgent(api_key="your-claude-api-key")

# 一句话发布文章
response = agent.chat("在我的网站上发布一篇关于Python的教程文章")
print(response)
```

---

## ⚙️ 配置清单

| 配置项 | 环境变量 | 必填 | 说明 |
|--------|----------|------|------|
| WordPress Token | `WP_ACCESS_TOKEN` | ✅ | OAuth 访问令牌 |
| WordPress Site ID | `WP_SITE_ID` | ✅ | 网站唯一标识 |
| Claude API Key | `ANTHROPIC_API_KEY` | ✅ | LLM API 密钥 |

---

## 🔧 关键成功因素

### 1. System Prompt 设计
- 明确的 ReAct 格式要求
- 完整的工具描述和参数说明
- 清晰的规则约束

### 2. 解析器优先级
- **Action 优先于 Final Answer**
- 防止 LLM 跳过工具调用直接给出答案

### 3. 工具返回格式
- 统一的 `{"success": bool, "data/error": ...}` 格式
- 足够的上下文信息供 LLM 决策

### 4. 迭代循环
- 支持多轮工具调用
- Observation 反馈机制

---

## 📁 最小化文件结构

```
your_chatbot/
├── agent.py              # ReAct Agent 实现
├── tools/
│   ├── __init__.py
│   ├── base.py           # 工具注册系统
│   └── cms.py            # CMS 工具
└── main.py               # 入口
```

---

## 🚀 快速验证

```bash
# 设置环境变量
export WP_ACCESS_TOKEN="your-token"
export WP_SITE_ID="your-site-id"
export ANTHROPIC_API_KEY="your-api-key"

# 运行
python main.py
```

---

## 📝 总结

实现"一句话发布文章"的核心要素：

1. **ReAct 框架** - 让 LLM 能够推理并调用工具
2. **工具注册系统** - 统一管理和调用工具
3. **CMS API 封装** - 与 WordPress 交互
4. **正确的解析器** - 优先执行 Action，避免跳过工具调用

只需约 300 行 Python 代码即可实现完整功能！

