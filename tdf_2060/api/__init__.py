"""E-1 R-track 2 lasso export API.

Minimal FastAPI surface for the R-track 2 lasso → representative review chain.
**NOT production**: every response forces ``is_production_selection=False``,
``dry_run_only=True``, ``phase_f_entered=False``. NOT a recommendation /
final SAA / production-ready label.
"""
from .main import app, build_app  # re-export for uvicorn

__all__ = ["app", "build_app"]
