"""Pruebas del resumen de documentos y de su caché.

El caché es delicado: si se pasa de listo, el chat deja de ver lo que el panel
acaba de subir, que es justo lo que el README promete que funciona. Por eso se
prueba tanto que evita el trabajo repetido como que se rinde cuando la base
cambió.
"""

from __future__ import annotations

import core.ingest as ing
from core.articles import DETECTOR_VERSION

VIEJA = DETECTOR_VERSION - 1


def meta(source: str, dv: object = DETECTOR_VERSION, **extra) -> dict:
    d = {"source": source, "page": 1, "seq": 0, "dv": dv}
    d.update(extra)
    return d


# --- Agregación (función pura) ---------------------------------------------
def test_agrupa_y_cuenta_por_documento() -> None:
    resumen = ing._resumir([meta("a.pdf"), meta("a.pdf"), meta("b.pdf")])
    assert resumen == [
        {"source": "a.pdf", "chunks": 2, "actualizado": True},
        {"source": "b.pdf", "chunks": 1, "actualizado": True},
    ]


def test_ordena_por_nombre() -> None:
    resumen = ing._resumir([meta("z.pdf"), meta("a.pdf"), meta("m.pdf")])
    assert [d["source"] for d in resumen] == ["a.pdf", "m.pdf", "z.pdf"]


def test_marca_desactualizado_por_version_anterior() -> None:
    resumen = ing._resumir([meta("a.pdf"), meta("a.pdf", dv=VIEJA)])
    assert resumen[0]["actualizado"] is False
    assert resumen[0]["chunks"] == 2       # sigue contándolos todos


def test_marca_desactualizado_si_falta_la_version() -> None:
    """Lo indexado antes de que existiera `dv` no lleva el campo."""
    sin_dv = {"source": "a.pdf", "page": 1, "seq": 0}
    assert ing._resumir([sin_dv])[0]["actualizado"] is False


def test_un_documento_al_dia_no_contagia_al_otro() -> None:
    resumen = ing._resumir([meta("a.pdf"), meta("b.pdf", dv=VIEJA)])
    estado = {d["source"]: d["actualizado"] for d in resumen}
    assert estado == {"a.pdf": True, "b.pdf": False}


def test_metadata_vacia_o_nula() -> None:
    assert ing._resumir([]) == []
    assert ing._resumir([None])[0]["source"] == "desconocido"


# --- Caché ------------------------------------------------------------------
class ColeccionFalsa:
    """Cuenta cuántas veces se le pide la metadata completa."""

    def __init__(self, metadatas: list[dict]) -> None:
        self.metadatas = metadatas
        self.escaneos = 0

    def get(self, *args, **kwargs):
        self.escaneos += 1
        return {"metadatas": self.metadatas}


class Banco:
    """Sustituye la colección y la huella de la base durante una prueba."""

    def __init__(self, metadatas: list[dict]) -> None:
        self.col = ColeccionFalsa(metadatas)
        self.huella = ("v1",)
        self._orig_get = ing.get_collection
        self._orig_huella = ing._huella_base
        self._orig_cache = ing._RESUMEN

    def __enter__(self) -> "Banco":
        ing.get_collection = lambda: self.col
        ing._huella_base = lambda: self.huella
        ing._RESUMEN = None
        return self

    def __exit__(self, *exc) -> None:
        ing.get_collection = self._orig_get
        ing._huella_base = self._orig_huella
        ing._RESUMEN = self._orig_cache


def test_no_reescanea_si_la_base_no_cambio() -> None:
    with Banco([meta("a.pdf")]) as b:
        for _ in range(10):
            ing.list_documents()
        assert b.col.escaneos == 1


def test_un_render_completo_cuesta_un_solo_escaneo() -> None:
    """El panel pide estado, tabla, desplegable y aviso: cuatro llamadas."""
    with Banco([meta("a.pdf")]) as b:
        ing.stats()
        ing.list_documents()
        ing.list_documents()
        ing.stale_documents()
        assert b.col.escaneos == 1


def test_reescanea_cuando_la_huella_cambia() -> None:
    """Es el caso de la escritura desde el otro proceso."""
    with Banco([meta("a.pdf")]) as b:
        assert [d["source"] for d in ing.list_documents()] == ["a.pdf"]
        b.col.metadatas = [meta("a.pdf"), meta("b.pdf")]
        b.huella = ("v2",)                       # el panel escribió
        assert [d["source"] for d in ing.list_documents()] == ["a.pdf", "b.pdf"]
        assert b.col.escaneos == 2


def test_invalidar_fuerza_un_reescaneo() -> None:
    with Banco([meta("a.pdf")]) as b:
        ing.list_documents()
        ing._invalidar_cache()
        ing.list_documents()
        assert b.col.escaneos == 2


def test_mutar_el_resultado_no_corrompe_el_cache() -> None:
    with Banco([meta("a.pdf")]):
        primero = ing.list_documents()
        primero.append({"source": "colado.pdf", "chunks": 1, "actualizado": True})
        primero[0]["chunks"] = 9999
        assert ing.list_documents() == [
            {"source": "a.pdf", "chunks": 1, "actualizado": True}
        ]


def test_stale_documents_usa_el_resumen() -> None:
    with Banco([meta("a.pdf"), meta("b.pdf", dv=VIEJA)]):
        assert ing.stale_documents() == ["b.pdf"]


def test_stats_suma_sobre_el_resumen() -> None:
    with Banco([meta("a.pdf"), meta("a.pdf"), meta("b.pdf")]):
        assert ing.stats() == {"documentos": 2, "fragmentos": 3}
