"""Public API schemas."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field


class HistoryItem(BaseModel):
    role: Literal["user", "assistant"]
    content: str


class QuestionRequest(BaseModel):
    question: str
    history: list[HistoryItem] = Field(default_factory=list)
    use_rag: bool = True


class AnswerResponse(BaseModel):
    answer: str
    thinking: str = ""
    citations: list[dict[str, Any]] = Field(default_factory=list)
    route: str
    timings: dict[str, float] = Field(default_factory=dict)
    request_id: str


class LoginRequest(BaseModel):
    password: str = Field(min_length=1, max_length=256)


class AuthStatusResponse(BaseModel):
    authenticated: bool


class HealthResponse(BaseModel):
    status: str
    version: str


class StatsResponse(BaseModel):
    total_documents: int
    bm25_chunks: int
    textbook_sources: int
    vector_documents: int
    knowledge_mode: Literal["local_and_pubmed", "pubmed_only"]
    provider: str
    model: str
    retrievers: dict[str, str]
    generation: dict[str, Any]
    metrics: dict[str, Any]
