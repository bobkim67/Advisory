"""E-1 FastAPI app entry — minimal review-only surface.

Usage:
    uvicorn api.main:app --host 127.0.0.1 --port 8000

NOT production. All endpoints force is_production_selection=False /
dry_run_only=True. No downstream R-1F.* / R-1G.* CLI is auto-triggered.
"""
from __future__ import annotations

from fastapi import FastAPI

from .lasso import router as lasso_router


def build_app() -> FastAPI:
    app = FastAPI(
        title="TDF 2060 R-track 2 API (E-1)",
        version="0.1.0",
        description=(
            "Review-only API for R-track 2 lasso export + representative review. "
            "Every response forces is_production_selection=False, dry_run_only=True, "
            "phase_f_entered=False. NOT a recommendation / final SAA / "
            "production-ready label."
        ),
    )
    app.include_router(lasso_router)

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok", "scope": "review-only", "dry_run_only": "true"}

    return app


app = build_app()
