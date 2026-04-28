"""LLM-as-Judge evaluation — Pydantic models, prompts, and judge functions.

Based on G-Eval (NeurIPS 2023) chain-of-thought approach.
Scale 1-5 for highest human-LLM alignment (arxiv 2601.03444).
"""
import json
import os
from typing import Optional

from pydantic import BaseModel, Field


# ---- Pydantic Models for Judge Responses ----

class QualityScore(BaseModel):
    """LLM judge response for quality evaluation."""
    reasoning: str = Field(description="Phân tích ngắn gọn 2-3 câu")
    relevance: int = Field(ge=1, le=5, description="Mức độ liên quan 1-5")
    completeness: int = Field(ge=1, le=5, description="Mức độ đầy đủ 1-5")
    fluency: int = Field(ge=1, le=5, description="Mức độ tự nhiên 1-5")
    actionability: int = Field(ge=1, le=5, description="Tính hữu dụng thực tế 1-5")


class FaithfulnessScore(BaseModel):
    """LLM judge response for faithfulness evaluation."""
    reasoning: str = Field(description="Giải thích ngắn")
    faithfulness: int = Field(ge=1, le=5, description="Độ trung thực 1-5")


# ---- LLM-as-Judge Prompts ----

JUDGE_PROMPT_QUALITY = """Bạn là chuyên gia đánh giá chatbot thời tiết Hà Nội. Hãy đánh giá câu trả lời dưới đây.
Đây là chatbot thời tiết chuyên về Hà Nội với các thuật ngữ chuyên ngành như "nồm ẩm", "gió Lào", "rét đậm", "sương mù".

## Câu hỏi của người dùng:
{question}

## Câu trả lời của chatbot:
{response}

## Hướng dẫn đánh giá:
Hãy suy nghĩ từng bước trước khi cho điểm.

**RELEVANCE (Mức độ liên quan):**
- 5: Trả lời chính xác, đúng trọng tâm câu hỏi
- 4: Trả lời đúng nhưng có thông tin thừa nhỏ
- 3: Trả lời một phần, bỏ sót điểm quan trọng
- 2: Trả lời lạc đề hoặc sai hướng
- 1: Hoàn toàn không liên quan hoặc từ chối trả lời

**COMPLETENESS (Đầy đủ):**
- 5: Đầy đủ tất cả thông tin quan trọng (nhiệt độ, độ ẩm, gió, mưa, khuyến nghị nếu cần)
- 4: Đầy đủ, thiếu chi tiết nhỏ không quan trọng
- 3: Thiếu một số thông tin quan trọng
- 2: Thiếu nhiều thông tin cần thiết
- 1: Gần như không có thông tin hữu ích

**FLUENCY (Tự nhiên):**
- 5: Rất tự nhiên, chuyên nghiệp, dễ đọc
- 4: Tự nhiên, có lỗi nhỏ không đáng kể
- 3: Chấp nhận được, có vài chỗ gượng
- 2: Khó đọc, nhiều lỗi ngữ pháp/từ vựng
- 1: Không thể đọc được

**ACTIONABILITY (Tính hữu dụng):**
- 5: Có khuyến nghị cụ thể, thực tế (mang ô, mặc áo khoác, tránh ra ngoài 10-14h, uống nhiều nước)
- 4: Có khuyến nghị nhưng chung chung (nên cẩn thận, chú ý thời tiết)
- 3: Ít khuyến nghị, chủ yếu liệt kê số liệu
- 2: Không có khuyến nghị dù câu hỏi cần (ví dụ: hỏi có nên ra ngoài không mà chỉ trả lời nhiệt độ)
- 1: Thông tin không dùng được, không giúp người dùng ra quyết định"""

JUDGE_PROMPT_FAITHFULNESS = """Bạn là chuyên gia kiểm tra tính chính xác của chatbot thời tiết Hà Nội.

## Câu hỏi của người dùng:
{question}

## Dữ liệu thời tiết thực tế (từ database):
{tool_output}

## Câu trả lời của chatbot:
{response}

## Nhiệm vụ:
Kiểm tra xem câu trả lời có chứa thông tin SAI hoặc BỊA ĐẶT không có trong dữ liệu thực tế không.

## Quy tắc chấm điểm:
CÁC TRƯỜNG HỢP CHẤP NHẬN ĐƯỢC (KHÔNG trừ điểm):
- Làm tròn số: 28.14°C → 28.1°C, 86.5% → 87% (sai lệch ≤ 0.5 đơn vị)
- Diễn giải weather_main sang tiếng Việt: "Clouds" → "nhiều mây", "Rain" → "mưa"
- Diễn giải mức gió: "2.5 m/s" → "gió nhẹ" (theo Beaufort)
- Đánh giá chung dựa trên số liệu: "trời mát" khi temp 22-26°C
- Trích xuất giá trị đúng từ forecast array cho đúng ngày/giờ được hỏi

CÁC TRƯỜNG HỢP SAI (PHẢI trừ điểm):
- Số liệu khác hẳn: tool nói 2.1 m/s nhưng chatbot nói 4.5 m/s (>100% sai lệch)
- Bịa ngày không có trong data: tool chỉ có 3 ngày nhưng chatbot trình bày 5 ngày
- Nhầm lẫn giá trị: dùng wind_gust thay cho wind_speed, hay avg_temp thay cho temp_max
- Tạo thông tin không có cơ sở: UV index, áp suất khi tool không trả về

**FAITHFULNESS (Độ trung thực):**
- 5: Tất cả thông tin đều chính xác, không có gì bịa đặt
- 4: Hầu hết chính xác, có 1 chi tiết nhỏ không chính xác
- 3: Có 1-2 thông tin sai hoặc không có trong dữ liệu
- 2: Có nhiều thông tin sai hoặc bịa đặt
- 1: Phần lớn thông tin sai hoặc không có cơ sở"""


def call_judge_quality(client, prompt, model=None) -> Optional[QualityScore]:
    """Call LLM judge for quality scoring with structured output."""
    if model is None:
        model = os.getenv("JUDGE_MODEL", os.getenv("MODEL", "gpt-4o-mini"))
    try:
        resp = client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
            response_format=QualityScore,
        )
        return resp.choices[0].message.parsed
    except Exception:
        # Fallback: try without structured output (for APIs that don't support it)
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            return QualityScore(**data)
        except Exception:
            return None


def call_judge_faithfulness(client, prompt, model=None) -> Optional[FaithfulnessScore]:
    """Call LLM judge for faithfulness scoring with structured output."""
    if model is None:
        model = os.getenv("JUDGE_MODEL", os.getenv("MODEL", "gpt-4o-mini"))
    try:
        resp = client.beta.chat.completions.parse(
            model=model,
            messages=[{"role": "user", "content": prompt}],
            temperature=0,
            max_tokens=400,
            response_format=FaithfulnessScore,
        )
        return resp.choices[0].message.parsed
    except Exception:
        # Fallback: try without structured output
        try:
            resp = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=0,
                max_tokens=400,
                response_format={"type": "json_object"},
            )
            data = json.loads(resp.choices[0].message.content)
            return FaithfulnessScore(**data)
        except Exception:
            return None


def llm_judge(question, response, tool_output=None, client=None) -> dict:
    """Run LLM-as-Judge evaluation. Returns dict with validated scores 1-5."""
    if client is None:
        from openai import OpenAI
        client = OpenAI(
            base_url=os.getenv("JUDGE_API_BASE") or os.getenv("API_BASE"),
            api_key=os.getenv("JUDGE_API_KEY") or os.getenv("API_KEY"),
        )

    # Quality judge (always run)
    quality = call_judge_quality(client, JUDGE_PROMPT_QUALITY.format(
        question=question, response=response,
    ))

    # Faithfulness judge (only if tool output available)
    # PR-C.5 (2026-04-27): bỏ `[:8000]` truncation. Bug cũ: judge mất context
    # khi tool_output > 8K chars → score sai. Feed full. Nếu vượt judge
    # context window (GPT-4o 128K) → caller chunked judging ở backends/judge.py.
    faith = None
    if tool_output and len(tool_output.strip()) > 10:
        faith = call_judge_faithfulness(client, JUDGE_PROMPT_FAITHFULNESS.format(
            question=question, response=response,
            tool_output=tool_output,
        ))

    return {
        "relevance": quality.relevance if quality else None,
        "completeness": quality.completeness if quality else None,
        "fluency": quality.fluency if quality else None,
        "actionability": quality.actionability if quality else None,
        "faithfulness": faith.faithfulness if faith else None,
        "judge_reasoning": quality.reasoning if quality else "",
        "faith_reasoning": faith.reasoning if faith else "",
    }
