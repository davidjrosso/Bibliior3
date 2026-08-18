from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Literal, Mapping

from app.models.row import row_value


EstadoCuota = Literal["pendiente", "pagada"]


@dataclass(slots=True)
class Cuota:
    id: int | None
    socio_id: int
    periodo: str
    monto: float
    estado: EstadoCuota
    fecha_pago: str | None
    observacion: str
    creado_en: str
    actualizado_en: str

    @property
    def pagada(self) -> bool:
        return self.estado == "pagada"

    @property
    def pendiente(self) -> bool:
        return self.estado == "pendiente"

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Cuota:
        return cls(
            id=row_value(row, "id"),
            socio_id=int(row["socio_id"]),
            periodo=str(row["periodo"]),
            monto=float(row["monto"]),
            estado=str(row["estado"]),  # type: ignore[arg-type]
            fecha_pago=row_value(row, "fecha_pago"),
            observacion=str(row_value(row, "observacion", "") or ""),
            creado_en=str(row["creado_en"]),
            actualizado_en=str(row["actualizado_en"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
