import http.client
import json5
import json
import ssl
import re
import logging
import time
from urllib.parse import urlparse

# 从配置文件导入API相关变量
from config import API_FLOW_ID, API_KEY, API_SECRET, XUN_FEI_URL

# ssl._create_default_https_context = ssl._create_unverified_context

DEFAULT_API_PATH = "/workflow/v1/chat/completions"
REQUEST_TIMEOUT_SECONDS = 300
logger = logging.getLogger(__name__)

def _build_connection():
    parsed = urlparse(XUN_FEI_URL)
    if parsed.scheme in ("http", "https"):
        host = parsed.hostname
        port = parsed.port
        path = parsed.path or DEFAULT_API_PATH
        if path.endswith(DEFAULT_API_PATH + DEFAULT_API_PATH):
            path = DEFAULT_API_PATH
        connection_cls = (
            http.client.HTTPSConnection
            if parsed.scheme == "https"
            else http.client.HTTPConnection
        )
        return connection_cls(host, port=port, timeout=REQUEST_TIMEOUT_SECONDS), path

    return http.client.HTTPSConnection(
        XUN_FEI_URL,
        timeout=REQUEST_TIMEOUT_SECONDS,
    ), DEFAULT_API_PATH

def call_api(payload):
    headers = {
        "Content-Type": "application/json",
        "Accept": "text/event-stream",
        "Authorization": "Bearer " + API_KEY + ":" + API_SECRET,
    }

    conn, request_path = _build_connection()
    started_at = time.perf_counter()
    try:
        logger.info(
            "Calling workflow API | path=%s timeout=%ss payload_bytes=%s",
            request_path,
            REQUEST_TIMEOUT_SECONDS,
            len(payload.encode("utf-8")),
        )
        conn.request("POST", request_path, payload, headers)
        res = conn.getresponse()
        data = res.read().decode("utf-8").strip()
    except Exception as e:
        elapsed = time.perf_counter() - started_at
        logger.exception(
            "Workflow API transport failure | path=%s elapsed=%.2fs timeout=%ss",
            request_path,
            elapsed,
            REQUEST_TIMEOUT_SECONDS,
        )
        raise RuntimeError(f"API transport error on {request_path}: {e}") from e
    finally:
        conn.close()

    elapsed = time.perf_counter() - started_at
    logger.info(
        "Workflow API response received | path=%s status=%s elapsed=%.2fs body_bytes=%s",
        request_path,
        res.status,
        elapsed,
        len(data.encode("utf-8")),
    )

    if res.status >= 400:
        raise RuntimeError(f"API request failed: {res.status} {data}")

    if data.startswith("data:"):
        data = data.split("data:", 1)[1].strip()

    try:
        json_data = json.loads(data)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"API response is not valid JSON: {data[:200]}") from e

    error_code = json_data.get("code")
    if error_code not in (None, 0):
        message = json_data.get("message") or "Unknown upstream error"
        logger.warning(
            "Workflow API business error | path=%s code=%s message=%s",
            request_path,
            error_code,
            message,
        )
        raise RuntimeError(f"API business error {error_code}: {message}")

    try:
        result = json_data["choices"][0]["delta"]["content"]
    except (KeyError, IndexError, TypeError) as e:
        raise RuntimeError(f"API response missing expected fields: {json_data}") from e

    return result


def compose_payload(review_type, title="", grade="", content=""):
    user_input = "请根据提供的结构化字段评审教案，并返回 JSON 结果。"

    data = {
    "flow_id": API_FLOW_ID,
    "uid": "1234",
    "parameters": {
        "AGENT_USER_INPUT": user_input,
        "type": review_type,
        "grade": grade,
        "topic": title,
        "content": content,
        },
    "ext": {"bot_id": "adjfidjf", "caller": "workflow"},
    "stream": False,
    }
    return json.dumps(data)


def _parse_agent_json_content(raw_text):
    text = (raw_text or "").strip()
    if not text:
        raise ValueError("Empty content returned from review API")

    # 兼容 markdown 代码块包装
    text = re.sub(r"^```(?:json)?\s*", "", text, flags=re.IGNORECASE)
    text = re.sub(r"\s*```$", "", text)

    candidates = [text]

    # 取首个 JSON 对象片段
    first = text.find("{")
    last = text.rfind("}")
    if first != -1 and last != -1 and first < last:
        candidates.append(text[first:last + 1])

    tried = set()
    for candidate in candidates:
        current = candidate.strip()
        while current and current not in tried:
            tried.add(current)
            try:
                return json5.loads(current)
            except Exception:
                # 兼容 {{{...}}} / {{...}} 等额外包裹
                if current.startswith("{{") and current.endswith("}}"):
                    current = current[1:-1].strip()
                    continue
                break

    preview = text[:200].replace("\n", "\\n")
    raise ValueError(f"Failed to parse review JSON content: {preview}")


def _split_sentences(text):
    parts = re.split(r"(?<=[。；;!?！？])", text or "")
    return [part.strip() for part in parts if part and part.strip()]


def _estimate_score_from_text(review_text, content):
    explicit_score = _extract_score_from_text(review_text)
    if explicit_score is not None:
        return explicit_score

    base_score = 78

    positive_markers = (
        "明确",
        "清晰",
        "扎实",
        "完整",
        "合理",
        "亮点",
        "符合",
        "有效",
        "较好",
        "以生为本",
    )
    negative_markers = (
        "不足",
        "问题",
        "不匹配",
        "缺乏",
        "流于",
        "偏重",
        "单一",
        "薄弱",
        "欠缺",
        "建议",
    )

    score = base_score
    for marker in positive_markers:
        if marker in review_text:
            score += 2
    for marker in negative_markers:
        if marker in review_text:
            score -= 3

    content_length = len(content or "")
    if content_length >= 1000:
        score += 2
    elif content_length < 300:
        score -= 4

    return max(60, min(95, score))


def _extract_score_from_text(review_text):
    total_score_match = re.search(r"(?:总分|综合评分|评分)[：:]\s*(\d{1,3})", review_text)
    if total_score_match:
        return max(0, min(100, int(total_score_match.group(1))))

    twenty_point_scores = [int(value) for value in re.findall(r"(\d{1,2})\s*/\s*20", review_text)]
    if twenty_point_scores:
        average_score = sum(twenty_point_scores) / len(twenty_point_scores)
        return max(0, min(100, round(average_score * 5)))

    average_match = re.search(r"均分[（(]?\s*(\d+(?:\.\d+)?)\s*[)）]?", review_text)
    if average_match:
        return max(0, min(100, round(float(average_match.group(1)) * 5)))

    return None


def _build_plaintext_review_result(raw_text, content):
    review_text = (raw_text or "").strip()
    if not review_text:
        raise ValueError("Empty content returned from review API")

    sentences = _split_sentences(review_text)
    suggestion = ""
    for sentence in sentences:
        if "建议" in sentence:
            suggestion = sentence
            break

    if not suggestion:
        suggestion = "建议补充教学目标、教学活动和评价方式之间的对应关系，并进一步细化课堂实施步骤。"

    return {
        "score": _estimate_score_from_text(review_text, content),
        "review_result": review_text,
        "suggestion": suggestion,
    }

def review_lesson_plan(title, grade, content):
    payload = compose_payload("review", title, grade, content)
    try:
        data = call_api(payload)
        try:
            result = _parse_agent_json_content(data)
        except ValueError as exc:
            logger.warning("Workflow returned plain text review, using compatibility parser | error=%s", exc)
            result = _build_plaintext_review_result(data, content)
        score = result.get("score")
        review_result = result.get("review_result")
        suggestion = result.get("suggestion")
        if score is None:
            raise ValueError("Missing score in review response")
        return score, review_result, suggestion
    except Exception as e:
        return _fallback_review_result(content, str(e))


def review_writting(topic, content):
    return review_lesson_plan(topic, "", content)


def _fallback_review_result(content, reason=""):
    english_words = re.findall(r"[A-Za-z]+(?:'[A-Za-z]+)?", content or "")
    cjk_chars = re.findall(r"[\u4e00-\u9fff]", content or "")
    word_count = len(english_words) + len(cjk_chars)

    if word_count >= 120:
        score = 88
    elif word_count >= 80:
        score = 80
    elif word_count >= 50:
        score = 72
    else:
        score = 62

    review_result = (
        "评审服务当前不稳定，已为你生成本地兜底评审结果。"
        "你的教案框架基本完整，建议继续加强教学目标、活动设计与评价闭环。"
    )

    suggestion = (
        "1. 明确教学目标与重难点；2. 补充课堂活动的步骤和时间分配；"
        "3. 加强师生活动与学习评价对应关系；4. 检查表达是否清晰、完整、可执行。"
    )

    if reason:
        review_result += f"（原因：{reason[:80]}）"

    return score, review_result, suggestion
