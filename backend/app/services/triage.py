from __future__ import annotations

import json
import logging
import re
from typing import Any, Optional

import httpx
from pydantic import BaseModel, Field, ValidationError, field_validator

from app.config import settings
from app.schemas import CATEGORY_TO_SPECIALTY, Category, Severity, Specialty


logger = logging.getLogger(__name__)

ALLOWED_CATEGORIES = [item.value for item in Category]
ALLOWED_SEVERITIES = [item.value for item in Severity]
ALLOWED_SPECIALTIES = [item.value for item in Specialty]
MAX_IMAGE_DATA_URL_CHARS = 900_000

CATEGORY_HINTS: list[tuple[tuple[str, ...], Category]] = [
    (("refrigerat", "walk_in", "walk-in", "cooler", "freezer", "ice machine"), Category.commercial_refrigeration),
    (("hvac", "exhaust", "rooftop", "air condition", "make-up air"), Category.hvac),
    (("plumb", "leak", "drain", "pipe", "sink", "faucet", "grease"), Category.plumbing),
    (("electric", "breaker", "outlet", "spark", "wiring"), Category.electrical),
    (("oven", "range", "fryer", "grill", "stove", "cooking"), Category.cooking_equipment),
    (("dish", "warewash"), Category.dishwashing),
    (("general", "facilit", "door", "fixture"), Category.general_maintenance),
]

SPECIALTY_HINTS: list[tuple[tuple[str, ...], Specialty]] = [
    (("refrigerat",), Specialty.refrigeration),
    (("hvac",), Specialty.hvac),
    (("plumb",), Specialty.plumbing),
    (("electric",), Specialty.electrical),
    (("cook", "oven", "range", "fryer"), Specialty.cooking_equipment),
    (("dish", "warewash"), Specialty.dishwashing),
    (("general", "facilit"), Specialty.general_facilities),
]


class TriageResult(BaseModel):
    category: Category
    severity: Severity
    possible_issue: str = Field(min_length=8, max_length=280)
    recommended_specialty: Specialty
    observations: list[str] = Field(min_length=1, max_length=4)
    immediate_action: str = Field(min_length=8, max_length=280)
    source: str = "openrouter"
    model_id: Optional[str] = None

    @field_validator("possible_issue")
    @classmethod
    def advisory_issue(cls, value: str) -> str:
        cleaned = value.strip()
        lowered = cleaned.lower()
        if not lowered.startswith(("possible", "likely", "may", "could", "appears")):
            cleaned = f"Possible {cleaned[0].lower() + cleaned[1:]}" if cleaned else cleaned
        return cleaned[:280]

    @field_validator("immediate_action")
    @classmethod
    def safe_action(cls, value: str) -> str:
        banned = ("guarantee", "definitely fixed", "safe to ignore", "open the electrical")
        lowered = value.lower()
        if any(term in lowered for term in banned):
            return "Keep the area clear, avoid using the equipment, and wait for an onsite technician to verify."
        return value.strip()[:280]

    @field_validator("observations", mode="before")
    @classmethod
    def coerce_observations(cls, value: Any) -> list[str]:
        if isinstance(value, str):
            parts = [part.strip(" -•") for part in re.split(r"[\n;]|,(?=\s)", value) if part.strip()]
            return parts[:4] or [value.strip()]
        if isinstance(value, list):
            return [str(item).strip() for item in value if str(item).strip()][:4]
        return ["A technician should verify the issue onsite."]


JSON_SCHEMA = {
    "name": "maintenance_assessment",
    "strict": False,
    "schema": {
        "type": "object",
        "additionalProperties": False,
        "properties": {
            "category": {"type": "string"},
            "severity": {"type": "string"},
            "possible_issue": {"type": "string"},
            "recommended_specialty": {"type": "string"},
            "observations": {"type": "array", "items": {"type": "string"}},
            "immediate_action": {"type": "string"},
        },
        "required": [
            "category",
            "severity",
            "possible_issue",
            "recommended_specialty",
            "observations",
            "immediate_action",
        ],
    },
}

SYSTEM_PROMPT = """You are an advisory restaurant maintenance triage assistant.
Analyze the staff report and optional photo. Return JSON only.
Do not claim certainty. Phrase possible_issue as a possibility.
Never give unsafe repair instructions or guarantees.

Use exactly these values:
category: commercial_refrigeration | hvac | plumbing | electrical | cooking_equipment | dishwashing | general_maintenance
severity: critical | high | medium | low
recommended_specialty: refrigeration | hvac | plumbing | electrical | cooking_equipment | dishwashing | general_facilities
observations: 2 to 4 short strings
"""


KEYWORD_RULES: list[tuple[tuple[str, ...], Category, Severity, str]] = [
    (
        ("walk-in", "walk in", "refrigerat", "cooler", "freezer", "not getting cold", "ice machine"),
        Category.commercial_refrigeration,
        Severity.critical,
        "cooling system malfunction",
    ),
    (("hvac", "ac unit", "air conditioning", "hood", "exhaust", "rooftop"), Category.hvac, Severity.high, "HVAC or exhaust malfunction"),
    (("leak", "drain", "pipe", "plumbing", "sink", "water on the floor", "grease trap"), Category.plumbing, Severity.high, "plumbing leak or drain backup"),
    (("spark", "outlet", "breaker", "electrical", "power", "lights out"), Category.electrical, Severity.high, "electrical supply issue"),
    (("oven", "range", "fryer", "grill", "stove", "not heating"), Category.cooking_equipment, Severity.high, "cooking equipment heating failure"),
    (("dishwasher", "dish machine", "warewash", "not rinsing"), Category.dishwashing, Severity.medium, "warewashing equipment malfunction"),
]


def fallback_triage(description: str, urgency: str) -> TriageResult:
    text = description.lower()
    category = Category.general_maintenance
    severity = Severity(urgency) if urgency in ALLOWED_SEVERITIES else Severity.medium
    issue = "equipment malfunction requiring onsite inspection"
    for keywords, matched_category, matched_severity, matched_issue in KEYWORD_RULES:
        if any(keyword in text for keyword in keywords):
            category = matched_category
            issue = matched_issue
            if matched_severity.value == "critical" or urgency == "critical":
                severity = Severity.critical
            elif urgency in ALLOWED_SEVERITIES:
                severity = max(
                    Severity(urgency),
                    matched_severity,
                    key=lambda item: ["low", "medium", "high", "critical"].index(item.value),
                )
            else:
                severity = matched_severity
            break

    specialty = CATEGORY_TO_SPECIALTY[category]
    return TriageResult(
        category=category,
        severity=severity,
        possible_issue=f"Possible {issue}",
        recommended_specialty=specialty,
        observations=[
            "Assessment generated from the written report while AI analysis was unavailable.",
            "A technician should verify the equipment onsite before any repair.",
        ],
        immediate_action="Stop using the equipment if unsafe, protect nearby product, and wait for a qualified technician.",
        source="fallback",
        model_id=None,
    )


def _hint_match(value: str, hints: list[tuple[tuple[str, ...], Any]], default: Any) -> Any:
    raw = value.lower().replace(" ", "_")
    for keys, mapped in hints:
        if any(key in raw for key in keys):
            return mapped
    return default


def _normalize_parsed(parsed: dict[str, Any], urgency: str) -> dict[str, Any]:
    category = _hint_match(str(parsed.get("category") or ""), CATEGORY_HINTS, Category.general_maintenance)
    if str(parsed.get("category") or "").lower() in ALLOWED_CATEGORIES:
        category = Category(str(parsed["category"]).lower())
    specialty_raw = str(parsed.get("recommended_specialty") or "")
    specialty = _hint_match(specialty_raw, SPECIALTY_HINTS, CATEGORY_TO_SPECIALTY[category])
    if specialty_raw.lower() in ALLOWED_SPECIALTIES:
        specialty = Specialty(specialty_raw.lower())
    severity_raw = str(parsed.get("severity") or urgency).lower()
    if severity_raw not in ALLOWED_SEVERITIES:
        severity_raw = urgency if urgency in ALLOWED_SEVERITIES else "medium"
    possible_issue = str(parsed.get("possible_issue") or "Possible equipment issue requiring onsite inspection")
    immediate_action = str(
        parsed.get("immediate_action")
        or "Stop using the equipment if unsafe and wait for a qualified technician."
    )
    observations = parsed.get("observations") or [
        "The report was classified from the description and any attached photo.",
        "A technician should verify the issue onsite.",
    ]
    return {
        "category": category.value,
        "severity": severity_raw,
        "possible_issue": possible_issue,
        "recommended_specialty": specialty.value,
        "observations": observations,
        "immediate_action": immediate_action,
    }


def _extract_json(text: str) -> dict[str, Any]:
    text = text.strip()
    if text.startswith("```"):
        text = re.sub(r"^```(?:json)?", "", text).strip()
        text = re.sub(r"```$", "", text).strip()
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Model did not return JSON")
    parsed = json.loads(match.group(0))
    if not isinstance(parsed, dict):
        raise ValueError("Model JSON was not an object")
    return parsed


def _message_text(message: dict[str, Any]) -> str:
    content = message.get("content")
    if isinstance(content, str) and content.strip():
        return content
    if isinstance(content, list):
        chunks = [str(part.get("text") or "") for part in content if isinstance(part, dict)]
        joined = "\n".join(chunk for chunk in chunks if chunk).strip()
        if joined:
            return joined
    for key in ("reasoning", "reasoning_content"):
        value = message.get(key)
        if isinstance(value, str) and value.strip():
            return value
    return ""


def _usable_image(image_data_url: Optional[str]) -> Optional[str]:
    if not image_data_url:
        return None
    if len(image_data_url) > MAX_IMAGE_DATA_URL_CHARS:
        logger.warning("Skipping oversized image for OpenRouter (%s chars)", len(image_data_url))
        return None
    return image_data_url


async def _call_openrouter(
    description: str,
    urgency: str,
    location_note: str,
    image_data_url: Optional[str],
    use_schema: bool,
) -> tuple[dict[str, Any], Optional[str]]:
    user_content: list[dict[str, Any]] = [
        {
            "type": "text",
            "text": (
                f"Restaurant maintenance report\n"
                f"Urgency selected by staff: {urgency}\n"
                f"Location: {location_note or 'Not specified'}\n"
                f"Description: {description}\n"
                "Return JSON with category, severity, possible_issue, recommended_specialty, observations, immediate_action."
            ),
        }
    ]
    if image_data_url:
        user_content.append({"type": "image_url", "image_url": {"url": image_data_url}})

    payload: dict[str, Any] = {
        "model": settings.openrouter_model,
        "temperature": 0.2,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": user_content},
        ],
    }
    if use_schema:
        payload["response_format"] = {"type": "json_object"}

    headers = {
        "Authorization": f"Bearer {settings.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": settings.openrouter_http_referer,
        "X-Title": settings.openrouter_app_title,
    }
    async with httpx.AsyncClient(timeout=settings.openrouter_timeout_seconds) as client:
        response = await client.post(f"{settings.openrouter_base_url}/chat/completions", headers=headers, json=payload)
        if response.status_code >= 400:
            raise httpx.HTTPStatusError(
                f"OpenRouter {response.status_code}: {response.text[:500]}",
                request=response.request,
                response=response,
            )
        body = response.json()
    choices = body.get("choices") or []
    if not choices:
        raise ValueError(f"OpenRouter returned no choices: {json.dumps(body)[:400]}")
    content = _message_text(choices[0].get("message") or {})
    if not content:
        raise ValueError("OpenRouter returned an empty message")
    model_id = body.get("model") or settings.openrouter_model
    return _extract_json(content), model_id


async def analyze_issue(
    description: str,
    urgency: str,
    location_note: str,
    image_data_url: Optional[str],
) -> TriageResult:
    if not settings.openrouter_api_key:
        return fallback_triage(description, urgency)

    last_error: Exception | None = None
    image = _usable_image(image_data_url)
    attempts = [(image, True), (image, False), (None, True), (None, False)]
    seen: set[tuple[bool, bool]] = set()
    for img, use_schema in attempts:
        key = (bool(img), use_schema)
        if key in seen:
            continue
        seen.add(key)
        try:
            parsed, model_id = await _call_openrouter(description, urgency, location_note, img, use_schema)
            result = TriageResult.model_validate(
                {**_normalize_parsed(parsed, urgency), "source": "openrouter", "model_id": model_id}
            )
            expected = CATEGORY_TO_SPECIALTY[result.category]
            if result.recommended_specialty != expected:
                result.recommended_specialty = expected
            if len(result.observations) < 2:
                result.observations = [
                    *result.observations,
                    "A technician should verify the issue onsite before any repair.",
                ][:4]
            return result
        except (httpx.HTTPError, KeyError, json.JSONDecodeError, ValidationError, ValueError) as exc:
            last_error = exc
            logger.warning("OpenRouter triage attempt failed (image=%s schema=%s): %s", bool(img), use_schema, exc)
            continue

    fallback = fallback_triage(description, urgency)
    if last_error:
        fallback.observations = [
            "Live AI triage was unavailable, so a conservative local assessment was used.",
            *fallback.observations[1:],
        ]
    return fallback
