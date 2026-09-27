"""DockTech freight forecasting module."""
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .service import ForecastService, ForecastResult

__all__ = ["ForecastService", "ForecastResult"]


def __getattr__(name: str):
    if name in {"ForecastService", "ForecastResult"}:
        from .service import ForecastService, ForecastResult
        return {"ForecastService": ForecastService, "ForecastResult": ForecastResult}[name]
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
