from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.models.row import row_value


@dataclass(slots=True)
class Cobrador:
    id: int
    nombre: str
    activo: bool
    creado_en: str
    actualizado_en: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Cobrador:
        return cls(
            id=int(row["id"]),
            nombre=str(row["nombre"]),
            activo=bool(int(row_value(row, "activo", 0) or 0)),
            creado_en=str(row["creado_en"]),
            actualizado_en=str(row["actualizado_en"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
