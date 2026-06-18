from __future__ import annotations

from fastapi import HTTPException

from src.core.errors import ProjectNotFoundError, RunNotFoundError, SessionNotFoundError


NotFoundError = ProjectNotFoundError | SessionNotFoundError | RunNotFoundError | KeyError


def not_found_to_http_exception(exc: NotFoundError) -> HTTPException:
    """把 Runtime 的资源不存在异常统一转换成 FastAPI 404 响应。"""
    if isinstance(exc, KeyError):
        detail = str(exc.args[0]) if exc.args else "object not found"
    else:
        detail = str(exc)
    return HTTPException(status_code=404, detail=detail)
