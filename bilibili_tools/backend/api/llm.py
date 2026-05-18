"""
LLM API 路由

POST /api/llm/identify — LLM 识别模糊媒体需求 → 返回搜索关键词
"""

from fastapi import APIRouter, HTTPException

from models.schemas import LlmIdentifyRequest, LlmIdentifyResponse
from services.llm_service import identify_media

router = APIRouter()


@router.post("/llm/identify", response_model=LlmIdentifyResponse)
async def identify(req: LlmIdentifyRequest):
    """
    通过 LLM 识别用户模糊描述的媒体资源，返回精准的B站搜索关键词。

    请求体:
    - **query**: 用户模糊描述（例如 "周杰伦一首和茶叶有关的歌"）
    - **model/base_url/api_key**: 可选覆盖设置中的 LLM 配置
    """
    try:
        result = await identify_media(
            query=req.query,
            model=req.model,
            base_url=req.base_url,
            api_key=req.api_key,
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"LLM 识别失败: {e}")

    return LlmIdentifyResponse(
        keywords=result.get("keywords", req.query),
        confidence=result.get("confidence", 0.0),
        explanation=result.get("explanation", ""),
        suggestions=result.get("suggestions", []),
    )
