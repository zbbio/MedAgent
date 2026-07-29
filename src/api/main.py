"""FastAPI entry point for MedAgent."""

from __future__ import annotations

import asyncio
import logging
import os
import uuid
from contextlib import asynccontextmanager
from pathlib import Path
from time import perf_counter
from typing import Callable

import uvicorn
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from ..agent.core import MedAgent
from ..config import config
from ..generation.llm_client import LLMServiceError, LLMTimeoutError
from .runtime import (
    GenerationGate,
    LoginRateLimiter,
    QueueFullError,
    QueueWaitTimeoutError,
    ServiceMetrics,
)
from .schemas import (
    AnswerResponse,
    AuthStatusResponse,
    HealthResponse,
    LoginRequest,
    QuestionRequest,
    StatsResponse,
)
from .security import (
    COOKIE_NAME,
    is_authenticated,
    issue_session_token,
    verify_password,
)


logger = logging.getLogger("medagent.api")
logging.basicConfig(
    level=os.getenv("LOG_LEVEL", "INFO"),
    format="%(asctime)s %(levelname)s %(name)s %(message)s",
)

FRONTEND_DIST = (Path(__file__).resolve().parents[2] / "frontend" / "dist").resolve()


class AppError(RuntimeError):
    def __init__(self, status_code: int, code: str, message: str) -> None:
        super().__init__(message)
        self.status_code = status_code
        self.code = code
        self.message = message


def create_app(
    agent_factory: Callable[[], MedAgent] = MedAgent,
    *,
    validate_config: bool = True,
) -> FastAPI:
    @asynccontextmanager
    async def lifespan(application: FastAPI):
        if validate_config:
            config.validate_startup(require_llm=True)
        application.state.agent = agent_factory()
        application.state.gate = GenerationGate(
            config.MAX_CONCURRENT_GENERATIONS,
            config.MAX_PENDING_GENERATIONS,
            config.QUEUE_WAIT_SECONDS,
        )
        application.state.metrics = ServiceMetrics()
        application.state.login_limiter = LoginRateLimiter(
            config.LOGIN_MAX_ATTEMPTS,
            config.LOGIN_WINDOW_SECONDS,
        )
        try:
            yield
        finally:
            close = getattr(application.state.agent, "close", None)
            if close:
                result = close()
                if asyncio.iscoroutine(result):
                    await result

    application = FastAPI(
        title="MedAgent - 智能医学助手",
        description="基于 RAG 的医学问答系统",
        version="1.1.0",
        lifespan=lifespan,
    )
    application.add_middleware(
        CORSMiddleware,
        allow_origins=config.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["GET", "POST", "OPTIONS"],
        allow_headers=["Content-Type", "X-Request-ID"],
    )

    @application.middleware("http")
    async def request_context(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex
        request.state.request_id = request_id
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response

    @application.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError):
        return _error_response(request, exc.status_code, exc.code, exc.message)

    @application.exception_handler(HTTPException)
    async def http_error_handler(request: Request, exc: HTTPException):
        message = exc.detail if isinstance(exc.detail, str) else "请求失败"
        return _error_response(request, exc.status_code, f"http_{exc.status_code}", message)

    @application.exception_handler(RequestValidationError)
    async def validation_error_handler(request: Request, exc: RequestValidationError):
        return _error_response(request, 422, "validation_error", "请求数据格式不正确")

    def require_auth(request: Request) -> None:
        if not is_authenticated(request):
            raise AppError(401, "authentication_required", "请先登录")

    @application.post("/api/auth/login", response_model=AuthStatusResponse)
    async def login(request: Request, payload: LoginRequest, response: Response):
        client_id = request.client.host if request.client else "unknown"
        limiter: LoginRateLimiter = request.app.state.login_limiter
        if await limiter.is_blocked(client_id):
            raise AppError(
                429,
                "login_rate_limited",
                "登录失败次数过多，请稍后再试",
            )
        if not verify_password(payload.password):
            await limiter.record_failure(client_id)
            raise AppError(401, "invalid_password", "访问密码错误")
        await limiter.reset(client_id)
        response.set_cookie(
            key=COOKIE_NAME,
            value=issue_session_token(),
            max_age=config.SESSION_TTL_SECONDS,
            httponly=True,
            secure=config.COOKIE_SECURE,
            samesite="lax",
            path="/",
        )
        return AuthStatusResponse(authenticated=True)

    @application.post("/api/auth/logout", response_model=AuthStatusResponse)
    async def logout(response: Response):
        response.delete_cookie(
            COOKIE_NAME,
            path="/",
            secure=config.COOKIE_SECURE,
            httponly=True,
            samesite="lax",
        )
        return AuthStatusResponse(authenticated=False)

    @application.get("/api/auth/status", response_model=AuthStatusResponse)
    async def auth_status(request: Request):
        return AuthStatusResponse(authenticated=is_authenticated(request))

    @application.get("/api/health", response_model=HealthResponse)
    async def health_check():
        return HealthResponse(status="healthy", version="1.1.0")

    @application.post(
        "/api/ask",
        response_model=AnswerResponse,
        dependencies=[Depends(require_auth)],
    )
    async def ask_question(request: Request, payload: QuestionRequest):
        _validate_question(payload)
        if not config.llm_usage_is_authorized():
            raise AppError(
                503,
                "llm_credential_not_authorized",
                "当前 Token Plan 凭证不允许用于医学问答后端，请配置授权的按量付费密钥",
            )
        started = perf_counter()
        metrics: ServiceMetrics = request.app.state.metrics
        try:
            async with asyncio.timeout(config.REQUEST_TIMEOUT_SECONDS):
                async with request.app.state.gate.slot() as queue_ms:
                    result = await request.app.state.agent.answer(
                        question=payload.question.strip(),
                        history=[item.model_dump() for item in payload.history],
                        use_rag=payload.use_rag,
                    )
            result["timings"]["queue_ms"] = queue_ms
            total_ms = round((perf_counter() - started) * 1000, 2)
            result["timings"]["request_total_ms"] = total_ms
            await metrics.record(
                "success",
                duration_ms=total_ms,
                timings=result["timings"],
            )
            logger.info(
                "request_id=%s outcome=success route=%s total_ms=%.2f queue_ms=%.2f",
                request.state.request_id,
                result.get("route", "unknown"),
                total_ms,
                queue_ms,
            )
            return AnswerResponse(
                answer=result["answer"],
                thinking=result.get("thinking", ""),
                citations=result.get("citations", []),
                route=result.get("route", "unknown"),
                timings=result["timings"],
                request_id=request.state.request_id,
            )
        except (QueueFullError, QueueWaitTimeoutError) as exc:
            await metrics.record(
                "http_429",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
            raise AppError(429, "generation_busy", f"{exc}，请稍后重试") from exc
        except LLMTimeoutError as exc:
            await metrics.record(
                "http_504",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
            raise AppError(504, exc.code, str(exc)) from exc
        except TimeoutError as exc:
            await metrics.record(
                "http_504",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
            raise AppError(504, "request_timeout", "回答生成超时，请稍后重试") from exc
        except LLMServiceError as exc:
            await metrics.record(
                "errors",
                duration_ms=round((perf_counter() - started) * 1000, 2),
                upstream_rate_limited=exc.rate_limited,
            )
            raise AppError(503, exc.code, str(exc)) from exc
        except Exception as exc:
            await metrics.record(
                "errors",
                duration_ms=round((perf_counter() - started) * 1000, 2),
            )
            logger.exception("request_id=%s unhandled ask error", request.state.request_id)
            raise AppError(500, "internal_error", "服务器处理失败，请联系管理员") from exc

    @application.get(
        "/api/stats",
        response_model=StatsResponse,
        dependencies=[Depends(require_auth)],
    )
    async def get_stats(request: Request):
        corpus = await asyncio.to_thread(request.app.state.agent.retriever.stats)
        gate = request.app.state.gate.snapshot()
        metrics = await request.app.state.metrics.snapshot()
        return StatsResponse(
            **corpus,
            provider=config.LLM_PROVIDER,
            model=config.LLM_MODEL,
            generation=gate,
            metrics=metrics,
        )

    if (FRONTEND_DIST / "assets").exists():
        application.mount(
            "/assets",
            StaticFiles(directory=str(FRONTEND_DIST / "assets")),
            name="assets",
        )

    @application.get("/", response_class=FileResponse)
    async def root():
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        raise AppError(404, "frontend_missing", "前端尚未构建")

    @application.get("/{path:path}", response_class=FileResponse)
    async def serve_spa(path: str):
        candidate = (FRONTEND_DIST / path).resolve()
        if FRONTEND_DIST in candidate.parents and candidate.is_file():
            return FileResponse(candidate)
        index = FRONTEND_DIST / "index.html"
        if index.exists():
            return FileResponse(index)
        raise AppError(404, "not_found", "资源不存在")

    return application


def _validate_question(payload: QuestionRequest) -> None:
    question = payload.question.strip()
    if not question:
        raise AppError(422, "empty_question", "问题不能为空")
    if len(question) > config.MAX_QUESTION_CHARS:
        raise AppError(
            413,
            "question_too_long",
            f"问题长度不能超过 {config.MAX_QUESTION_CHARS} 字符",
        )
    if len(payload.history) > config.MAX_HISTORY_ITEMS:
        raise AppError(
            413,
            "history_too_long",
            f"历史消息不能超过 {config.MAX_HISTORY_ITEMS} 条",
        )
    history_chars = sum(len(item.content) for item in payload.history)
    if history_chars > config.MAX_HISTORY_CHARS:
        raise AppError(
            413,
            "history_too_large",
            f"历史消息总长度不能超过 {config.MAX_HISTORY_CHARS} 字符",
        )


def _error_response(
    request: Request,
    status_code: int,
    code: str,
    message: str,
) -> JSONResponse:
    request_id = getattr(request.state, "request_id", uuid.uuid4().hex)
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": code,
                "message": message,
                "request_id": request_id,
            }
        },
        headers={"X-Request-ID": request_id},
    )


app = create_app()


if __name__ == "__main__":
    uvicorn.run(
        "src.api.main:app",
        host=config.API_HOST,
        port=config.API_PORT,
        reload=True,
    )
