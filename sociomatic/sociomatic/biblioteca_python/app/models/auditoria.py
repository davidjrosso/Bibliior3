from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.models.row import row_value


@dataclass(slots=True)
class Auditoria:
    id: int | None
    accion: str
    detalle: str
    creado_en: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Auditoria:
        return cls(
            id=row_value(row, "id"),
            accion=str(row["accion"]),
            detalle=str(row_value(row, "detalle", "") or ""),
            creado_en=str(row["creado_en"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
