from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(slots=True)
class Configuracion:
    clave: str
    valor: str

    @classmethod
    def from_row(cls, row: Mapping[str, Any]) -> Configuracion:
        return cls(clave=str(row["clave"]), valor=str(row["valor"]))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
