from pydantic import BaseModel, Field, HttpUrl
from typing import List, Literal, Optional


class AnalyzeRequest(BaseModel):
    url: HttpUrl
    force: bool = False
    mode: Literal["editors_bench", "intent_accrual"] = "editors_bench"


class ScoreItem(BaseModel):
    criterion: Literal[
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
    score: float = Field(ge=0, le=10)
    rationale: str
    flags: List[str] = []


class Meta(BaseModel):
    title: Optional[str] = None
    author: Optional[str] = None
    thumbnail: Optional[str] = None
    fetched_at: str


class Overall(BaseModel):
    average: float
    method: Literal["mean_of_subscores"] = "mean_of_subscores"


class HeadlineSummary(BaseModel):
    one_sentence_summary: Optional[str] = None
    headline_body_match: bool


class RawInfo(BaseModel):
    url: str
    word_count: int


class AnalyzeResponse(BaseModel):
    meta: Meta
    scores: List[ScoreItem]
    overall: Overall
    headline_summary: HeadlineSummary
    raw: RawInfo
    version: str
    fromCache: bool = False
    mindsetEcho: Optional[str] = None
    mode: Literal["editors_bench", "intent_accrual"] = "editors_bench"
    intent: Optional[str] = None
    necessity_map: Optional[dict] = None


