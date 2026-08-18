from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.models.row import row_value


@dataclass(slots=True)
class TipoSocio:
    id: str
    nombre: str
    monto: float
    activo: bool
    creado_en: str
    actualizado_en: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> TipoSocio:
        return cls(
            id=str(row["id"]),
            nombre=str(row["nombre"]),
            monto=float(row_value(row, "monto", 0) or 0),
            activo=bool(int(row_value(row, "activo", 0) or 0)),
            creado_en=str(row["creado_en"]),
            actualizado_en=str(row["actualizado_en"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
