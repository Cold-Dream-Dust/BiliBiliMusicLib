"""
LLM 服务 — OpenAI 兼容 API 调用 + Function Calling 联网搜索

工作流:
  用户模糊描述 → LLM 判断是否需要联网 → 需要时调用 web_search function
  → LLM 分析搜索结果 → 返回精准的 B站 搜索关键词
"""

from __future__ import annotations

import json
from typing import Optional

from openai import AsyncOpenAI

from config import settings

# ── System Prompt ──────────────────────────────────────
SYSTEM_PROMPT = """你是一个音乐/视频识别专家。用户会用模糊的语言描述想找的媒体资源。

你的任务：
1. 如果确定知道答案，直接给出精准的B站搜索关键词（中文）
2. 如果不确定或需要确认，使用 web_search 工具联网搜索
3. 返回 JSON 格式：
   {
     "keywords": "精准的B站中文搜索关键词",
     "confidence": 0.0-1.0,
     "explanation": "简短解释识别过程",
     "suggestions": ["备选搜索词1", "备选搜索词2"]
   }

注意：
- 关键词要从B站搜索角度考虑，使用中文，以便在B站搜索到相关视频
- 如果是歌曲，关键词应包含歌手名和歌名
- 如果有多个可能，在 suggestions 中给出备选"""


def _get_llm_client(
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> AsyncOpenAI:
    """创建 LLM 客户端"""
    return AsyncOpenAI(
        base_url=base_url or settings.llm_base_url,
        api_key=api_key or settings.llm_api_key,
    )


async def _web_search(query: str) -> str:
    """
    联网搜索（使用 DuckDuckGo）

    Args:
        query: 搜索关键词

    Returns:
        格式化的搜索结果文本
    """
    try:
        from duckduckgo_search import DDGS
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=5))
            if not results:
                return "未找到相关结果"

            lines = []
            for i, r in enumerate(results, 1):
                lines.append(f"{i}. {r.get('title', '')}")
                lines.append(f"   {r.get('body', '')[:200]}")
                lines.append(f"   URL: {r.get('href', '')}")
            return "\n".join(lines)
    except ImportError:
        return "web_search 不可用：请安装 duckduckgo_search"
    except Exception as e:
        return f"搜索出错: {e}"


# ── Function Calling 工具定义 ──────────────────────────
TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": "联网搜索以确认媒体资源信息。当你不确定用户描述的歌曲/视频具体名称时使用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "搜索关键词，例如: '周杰伦 茶叶 歌曲'",
                    }
                },
                "required": ["query"],
            },
        },
    }
]


async def identify_media(
    query: str,
    model: Optional[str] = None,
    base_url: Optional[str] = None,
    api_key: Optional[str] = None,
) -> dict:
    """
    通过 LLM 识别模糊媒体需求

    Args:
        query: 用户模糊描述
        model: LLM 模型名（可选，不传用设置）
        base_url: API 地址（可选）
        api_key: API Key（可选）

    Returns:
        {"keywords": str, "confidence": float, "explanation": str, "suggestions": list}
    """
    client = _get_llm_client(base_url, api_key)
    used_model = model or settings.llm_model

    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": query},
    ]

    # 第一轮：LLM 可能调用 function
    try:
        response = await client.chat.completions.create(
            model=used_model,
            messages=messages,
            tools=TOOLS,
            tool_choice="auto",
            temperature=0.3,
        )
    except Exception as e:
        print(f"[LLMService] API 调用失败: {e}")
        # 降级：直接用用户输入作为关键词
        return {
            "keywords": query,
            "confidence": 0.3,
            "explanation": f"LLM 调用失败: {e}",
            "suggestions": [],
        }

    assistant_msg = response.choices[0].message

    # 如果 LLM 调用了 web_search
    if assistant_msg.tool_calls:
        # 1) 先追加 assistant 消息（含 tool_calls），只追加一次
        tc_list = []
        for tc in assistant_msg.tool_calls:
            tc_list.append({
                "id": tc.id,
                "type": "function",
                "function": {
                    "name": tc.function.name,
                    "arguments": tc.function.arguments,
                },
            })
        asst_msg = {
            "role": "assistant",
            "content": assistant_msg.content,
            "tool_calls": tc_list,
        }
        # 保留 thinking 模式的 reasoning_content（DeepSeek 等需要）
        if hasattr(assistant_msg, "reasoning_content") and assistant_msg.reasoning_content:
            asst_msg["reasoning_content"] = assistant_msg.reasoning_content
        messages.append(asst_msg)

        # 2) 逐个执行 tool_call 并追加结果
        for tool_call in assistant_msg.tool_calls:
            if tool_call.function.name == "web_search":
                args = json.loads(tool_call.function.arguments)
                search_query = args.get("query", query)
                print(f"[LLMService] 联网搜索: {search_query}")

                search_results = await _web_search(search_query)

                messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.id,
                    "content": search_results,
                })

        # 第二轮：LLM 分析搜索结果
        try:
            response2 = await client.chat.completions.create(
                model=used_model,
                messages=messages,
                temperature=0.3,
            )
            assistant_msg = response2.choices[0].message
        except Exception as e:
            print(f"[LLMService] 第二轮调用失败: {e}")
            return {
                "keywords": query,
                "confidence": 0.4,
                "explanation": f"联网搜索后分析失败: {e}",
                "suggestions": [],
            }

    # 解析 LLM 的 JSON 响应
    content = assistant_msg.content or ""
    try:
        # 尝试提取 JSON
        content = content.strip()
        if "```json" in content:
            content = content.split("```json")[1].split("```")[0].strip()
        elif "```" in content:
            content = content.split("```")[1].split("```")[0].strip()

        result = json.loads(content)
    except json.JSONDecodeError:
        # 非 JSON 响应，当作纯文本关键词
        result = {
            "keywords": content.strip().strip('"'),
            "confidence": 0.6,
            "explanation": "LLM 直接识别",
            "suggestions": [],
        }

    return {
        "keywords": result.get("keywords", query),
        "confidence": float(result.get("confidence", 0.5)),
        "explanation": str(result.get("explanation", "")),
        "suggestions": result.get("suggestions", []) or [],
    }
