from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping

from app.models.row import row_value


@dataclass(slots=True)
class Socio:
    id: int | None
    nro_socio: int
    dni: str
    apellido: str
    nombre: str
    telefono: str
    email: str
    direccion: str
    barrio: str
    localidad: str
    fecha_nacimiento: str | None
    ocupacion: str
    estado: str
    cobrador: int
    fecha_alta: str
    fecha_baja: str | None
    creado_en: str
    actualizado_en: str

    @property
    def activo(self) -> bool:
        return self.fecha_baja is None

    @property
    def nombre_completo(self) -> str:
        return f"{self.apellido}, {self.nombre}".strip(", ")

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Socio:
        return cls(
            id=row_value(row, "id"),
            nro_socio=int(row["nro_socio"]),
            dni=str(row["dni"]),
            apellido=str(row["apellido"]),
            nombre=str(row["nombre"]),
            telefono=str(row_value(row, "telefono", "") or ""),
            email=str(row_value(row, "email", "") or ""),
            direccion=str(row_value(row, "direccion", "") or ""),
            barrio=str(row_value(row, "barrio", "") or ""),
            localidad=str(row_value(row, "localidad", "") or ""),
            fecha_nacimiento=row_value(row, "fecha_nacimiento"),
            ocupacion=str(row_value(row, "ocupacion", "") or ""),
            estado=str(row["estado"]),
            cobrador=int(row["cobrador"]),
            fecha_alta=str(row["fecha_alta"]),
            fecha_baja=row_value(row, "fecha_baja"),
            creado_en=str(row["creado_en"]),
            actualizado_en=str(row["actualizado_en"]),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
