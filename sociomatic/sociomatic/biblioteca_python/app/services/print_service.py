from app.models import config_model, cuota_model, socio_model
from app.models.helpers import next_period
from app.views.print_view import render_morosos, render_print


def cuotas_html(conn, query: dict) -> str:
    periodo = query.get("periodo", [next_period()])[0]
    cobrador = int(query.get("cobrador", ["1"])[0])
    cobradores_activos = {row["id"] for row in config_model.listar_cobradores(conn, solo_activos=True)}
    if cobrador not in cobradores_activos:
        raise ValueError("Cobrador invalido.")
    rows = cuota_model.cuotas_para_imprimir(conn, periodo, cobrador)
    return render_print(periodo, config_model.cobrador_nombre(conn, cobrador), rows)


def morosos_html(conn) -> str:
    config = config_model.get_config(conn)
    limite = int(config.get("moroso_cuotas_limite", "4"))
    return render_morosos(socio_model.listar_morosos(conn), limite)
