import json
from typing import Any, Dict
from openai import OpenAI
from .config import get_settings


PROMPT_RULES_HEADER = """You score news articles using ONLY the provided article text and features.\nDo not use external knowledge. Be concise, neutral, explainable.\nReturn JSON only. Each rationale is max 3 sentences and must cite specific text snippets or sections.\nMANDATORY: Return exactly these 11 criteria keys: clarity_coherence, five_w_one_h, attribution_evidence, hedging_overclaim, balance_opposing, inversion_touch, context_proportionality, multidisciplinarity, civic_utility, transparency_cues, language_credibility. No extra or missing keys."""

INTENT_LABELS = ["hard_news","explainer","opinion","brief","feature","live_blog"]

# Necessity weights per intent (w in [0,1])
NEED_WEIGHTS = {
    "hard_news": {"clarity_coherence":0.9,"five_w_one_h":1.0,"attribution_evidence":1.0,"hedging_overclaim":0.9,"balance_opposing":0.7,"inversion_touch":0.5,"context_proportionality":0.8,"multidisciplinarity":0.4,"civic_utility":0.5,"transparency_cues":0.7,"language_credibility":0.8},
    "explainer": {"clarity_coherence":1.0,"five_w_one_h":0.6,"attribution_evidence":0.8,"hedging_overclaim":0.7,"balance_opposing":0.6,"inversion_touch":0.6,"context_proportionality":1.0,"multidisciplinarity":0.8,"civic_utility":0.6,"transparency_cues":0.6,"language_credibility":0.8},
    "opinion": {"clarity_coherence":0.9,"five_w_one_h":0.4,"attribution_evidence":0.6,"hedging_overclaim":0.8,"balance_opposing":0.5,"inversion_touch":0.7,"context_proportionality":0.7,"multidisciplinarity":0.6,"civic_utility":0.3,"transparency_cues":0.7,"language_credibility":0.9},
    "brief": {"clarity_coherence":0.9,"five_w_one_h":0.9,"attribution_evidence":0.8,"hedging_overclaim":0.8,"balance_opposing":0.4,"inversion_touch":0.3,"context_proportionality":0.6,"multidisciplinarity":0.2,"civic_utility":0.4,"transparency_cues":0.6,"language_credibility":0.8},
    "feature": {"clarity_coherence":0.9,"five_w_one_h":0.5,"attribution_evidence":0.7,"hedging_overclaim":0.7,"balance_opposing":0.6,"inversion_touch":0.7,"context_proportionality":0.8,"multidisciplinarity":0.7,"civic_utility":0.5,"transparency_cues":0.6,"language_credibility":0.8},
    "live_blog": {"clarity_coherence":0.7,"five_w_one_h":0.8,"attribution_evidence":0.8,"hedging_overclaim":0.7,"balance_opposing":0.4,"inversion_touch":0.3,"context_proportionality":0.6,"multidisciplinarity":0.3,"civic_utility":0.5,"transparency_cues":0.6,"language_credibility":0.8},
}

A_ADD = 5.0
B_SUB = 6.0
NEED_MATRIX_VERSION = "nmv1"


def build_user_prompt(meta: Dict[str, Any], text: str, features: Dict[str, Any], rules: str, mode: str) -> str:
    # Mindset profile blended from slider
    mind = _mindset_profile(0.4)
    if mode == "intent_accrual":
        mode_instructions = (
            "JUDGING_MODE: Intent-Aware Accrual\n"
            f"- First classify article INTENT as one of: {', '.join(INTENT_LABELS)}. Return it in root field _intent.\n"
            "- For that INTENT, construct a necessity weight map w in [0,1] for the 11 criteria (use newsroom best practice). Return it in root field _necessity_map.\n"
            f"- Use Base=5. Compute adds/subtracts scaled by w. Caps A={A_ADD}, B={B_SUB}. Final score = clamp(0,10, 5 + A*w*e - B*w*v).\n"
            "- When w < 0.3, absence should not be penalized unless there is explicit harm/mislead.\n"
            "- RATIONALE STYLE: For each criterion, write a direct explanation in plain language (max 3 sentences). Cite short quotes from the article in \"...\" if useful. Do NOT mention math, intent labels, weights, or starting at 5.\n"
            "- STRICT: Do NOT output tokens like 'Intent=', 'Need=', 'Start 5', '+a', '-b', or 'Final:'.\n"
        )
    else:
        mode_instructions = (
            "JUDGING_MODE: Editor's Bench\n"
            "- Apply the strict rubric directly; do not assume unstated elements.\n"
            "- Score 0–10 purely on observed compliance.\n"
            "- RATIONALE STYLE: For each criterion, write a direct explanation in plain language (max 3 sentences). Cite short quotes from the article in \"...\" if useful. Do NOT mention math, intent labels, weights, or starting at 5.\n"
            "- STRICT: Do NOT output tokens like 'Intent=', 'Need=', 'Start 5', '+a', '-b', or 'Final:'.\n"
        )
    return (
        f"ARTICLE_META:\n- Title: {meta.get('title','')}\n- Author: {meta.get('author','')}\n- Published: {meta.get('published','')}\n\n"
        f"ARTICLE_TEXT:\n{text}\n\nFEATURES:\n{json.dumps(features, ensure_ascii=False)}\n\nRULES:\n{rules}\n\nMODE: {mode}\n{mode_instructions}\n\n"
        f"MINDSET_PROFILE:\n{mind}\n\n"
        "OUTPUT FORMAT (JSON):\n{\n  \"scores\": [\n    {\"criterion\":\"clarity_coherence\",\"score\":0,\"rationale\":\"\",\"flags\":[\"\"]}\n  ],\n  \"overall\":{\"average\":0},\n  \"headline_summary\":{\"one_sentence_summary\":\"\",\"headline_body_match\":true}\n}"
    )


def _mindset_profile(inf: float) -> str:
    # Blend descriptive self-instructions; not numeric rules, but stance.
    if inf <= 0.2:
        return (
            "You are a forensic editor. Credit only what is explicit in the text. "
            "Skeptical stance: when unsure, do NOT award credit. Evidence means named sources, direct quotes, or explicit data within 3 sentences. "
            "Prefer terse, concrete rationales pointing to exact snippets. Penalize rhetoric and overclaiming."
        )
    if inf >= 0.7:
        return (
            "You are a senior analyst. Read intent and plausible implications. "
            "Generous stance: when the article signals rigor (method, sourcing pattern, institutional context), provisionally award credit with explicit caveats. "
            "Accept credible paraphrase/implicit support. Emphasize synthesis, context, and proportionality. Rationales remain grounded in the text."
        )
    # Balanced middle
    return (
        "You are a professional editor. Allow reasonable implication and domain conventions, but avoid inventing facts. "
        "Balanced stance: weigh strengths and weaknesses; if evidence is likely intended but not spelled out, give partial credit and explain. "
        "Tone is explanatory, citing specific places in the text."
    )


CRITERIA_KEYS = [
    "clarity_coherence",
    "five_w_one_h",
    "attribution_evidence",
    "hedging_overclaim",
    "balance_opposing",
    "inversion_touch",
    "context_proportionality",
    "multidisciplinarity",
    "civic_utility",
    "transparency_cues",
    "language_credibility",
]


def _sanitize_rationale(text: str) -> str:
    # Remove legacy math/intent tokens and formatting markers
    if not text:
        return ""
    import re
    t = text
    # Case-insensitive strip of tokens regardless of spacing
    patterns = [
        r"(?i)intent\s*=\s*[^;:.]+[;:.]?",
        r"(?i)need\s*=\s*[^;:.]+[;:.]?",
        r"(?i)start\s*:??\s*5\b[;:.]?",
        r"(?i)final\s*:\s*\d+\s*/\s*10\b[;:.]?",
        r"(?i)\+a\s+for",
        r"(?i)-b\s+for",
    ]
    for p in patterns:
        t = re.sub(p, "", t)
    # Normalize whitespace and punctuation spacing
    t = re.sub(r"\s{2,}", " ", t)
    t = re.sub(r"\s*;+\s*", "; ", t)
    t = re.sub(r"\s*:\s*", ": ", t)
    t = t.strip(" .;:,")
    # Trim to max 3 sentences
    sentences = re.split(r"(?<=[.!?])\s+", t.strip())
    t = " ".join([s.strip() for s in sentences if s.strip()][:3])
    return t


def _normalize_scores(obj: Dict[str, Any]) -> Dict[str, Any]:
    # Ensure exactly 11 criteria keys are present and valid
    out = {"scores": [], "headline_summary": obj.get("headline_summary")}
    scores = obj.get("scores") or []
    by_key = {s.get("criterion"): s for s in scores if isinstance(s, dict)}
    for key in CRITERIA_KEYS:
        s = by_key.get(key) or {"criterion": key, "score": 0, "rationale": "", "flags": []}
        # Clamp score 0..10
        try:
            val = float(s.get("score", 0))
        except Exception:
            val = 0.0
        # No global bias; use the mindset profile to influence evaluation instead
        s["score"] = max(0, min(10, val))
        # Ensure rationale style: plain, concise, no math/intent tokens, max 3 sentences
        raw_rationale = (s.get("rationale") or "")[:800]
        s["rationale"] = _sanitize_rationale(raw_rationale)
        s["flags"] = s.get("flags") or []
        out["scores"].append(s)
    if not out["headline_summary"]:
        out["headline_summary"] = {"one_sentence_summary": "", "headline_body_match": True}
    return out


def call_openai(text: str, meta: Dict[str, Any], features: Dict[str, Any], rules: str, mode: str = "editors_bench") -> Dict[str, Any]:
    settings = get_settings()
    mindset = _mindset_profile(0.4)
    if settings.use_mock_openai:
        # Deterministic mock: generate simple mid-scores with brief rationales
        crits = [
            "clarity_coherence","five_w_one_h","attribution_evidence","hedging_overclaim",
            "balance_opposing","inversion_touch","context_proportionality","multidisciplinarity",
            "civic_utility","transparency_cues","language_credibility"
        ]
        scores = []
        for c in crits:
            sc = 5 + round((inference-0.5)*4, 1)
            scores.append({"criterion": c, "score": max(0, min(10, sc)), "rationale": "Mock rationale based on features.", "flags": []})
        return {
            "scores": scores,
            "headline_summary": {"one_sentence_summary": "Mock one-sentence summary.", "headline_body_match": True},
            "_mindset": mindset,
        }

    client = OpenAI(api_key=settings.openai_api_key)
    messages = [
        {"role": "system", "content": PROMPT_RULES_HEADER},
        {"role": "user", "content": build_user_prompt(meta, text, features, rules, mode)},
    ]

    # Default to gpt-4o-mini unless overridden later
    # Decoding shaped by inference: lower randomness when literal, more when interpretive
    temperature = 0.35
    presence_penalty = 0.1
    frequency_penalty = 0.1

    resp = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        temperature=temperature,
        presence_penalty=presence_penalty,
        frequency_penalty=frequency_penalty,
        response_format={"type": "json_object"},
    )
    content = resp.choices[0].message.content
    # Guardrails: parse JSON, normalize; if fails, retry once
    try:
        parsed = json.loads(content)
        out = _normalize_scores(parsed)
        out["_mindset"] = mindset
        return out
    except Exception:
        resp2 = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.2,
        )
        try:
            parsed2 = json.loads(resp2.choices[0].message.content)
            out2 = _normalize_scores(parsed2)
            out2["_mindset"] = mindset
            return out2
        except Exception:
            return {"error": "invalid_json_from_model", "raw": resp2.choices[0].message.content}


