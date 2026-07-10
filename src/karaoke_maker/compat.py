from __future__ import annotations

try:
    from pydantic.v1 import BaseModel, Field, validator
except ImportError:  # pragma: no cover - used only with Pydantic 1.x
    from pydantic import BaseModel, Field, validator

__all__ = ["BaseModel", "Field", "validator"]
