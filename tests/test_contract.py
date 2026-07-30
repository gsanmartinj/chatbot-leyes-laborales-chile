"""Pruebas de la revisión de contratos que no necesitan modelo ni base vectorial.

El foco está en el filtro que impide que un hallazgo se apoye en una fuente
inventada: es lo único que separa "modo estricto" de una alucinación con cita.
"""

from __future__ import annotations

import pytest

from core.contract import (
    _indice_fragmento,
    _normalizar_hallazgo,
    _parse_json_array,
    _resolver_por_texto,
    split_clauses,
)

FRAGMENTOS = {
    1: {
        "source": "codigo_del_trabajo.pdf",
        "page": 12,
        "articulo": "22",
        "texto": "La jornada ordinaria de trabajo no excederá de cuarenta y cinco horas.",
    }
}


# --- Troceo en cláusulas ----------------------------------------------------
def test_contrato_numerado_con_ordinales() -> None:
    contrato = (
        "CONTRATO DE TRABAJO\n\n"
        "En Santiago, a 1 de enero de 2026, entre Empresa SpA y don Juan Pérez.\n\n"
        "PRIMERO: El trabajador se obliga a desempeñar el cargo de vendedor.\n\n"
        "SEGUNDO: La jornada será de 50 horas semanales.\n\n"
        "TERCERO: La remuneración será de $500.000 mensuales.\n"
    )
    clausulas = split_clauses(contrato)
    assert len(clausulas) == 4                    # preámbulo + 3 cláusulas
    assert clausulas[0].titulo == "CONTRATO DE TRABAJO"
    assert "vendedor" in clausulas[1].texto


def test_preambulo_corto_no_se_descarta() -> None:
    """Un umbral por longitud tiraba en silencio los preámbulos breves."""
    contrato = "CONTRATO\n\nPRIMERO: Cargo.\n\nSEGUNDO: Jornada.\n"
    assert split_clauses(contrato)[0].texto.startswith("CONTRATO")


def test_contrato_sin_numerar_cae_a_bloques() -> None:
    texto = "\n\n".join("Párrafo con contenido de relleno. " * 10 for _ in range(5))
    assert len(split_clauses(texto)) >= 2


def test_contrato_vacio() -> None:
    assert split_clauses("") == []


# --- Parseo de la respuesta del modelo --------------------------------------
@pytest.mark.parametrize(
    "salida, esperado",
    [
        ("[]", []),
        ('```json\n[{"problema":"x"}]\n```', [{"problema": "x"}]),
        ('Aquí van:\n[{"problema":"y"}]\nEspero que sirva.', [{"problema": "y"}]),
        ("no es json", None),
        ('{"problema":"un objeto, no un array"}', None),
        ("", None),
    ],
)
def test_parse_json_array(salida: str, esperado: object) -> None:
    assert _parse_json_array(salida) == esperado


@pytest.mark.parametrize(
    "bruto, esperado",
    [
        ({"fragmento": 2}, 2),
        ({"fragmento": "F3"}, 3),
        ({"fragmento": "[F4]"}, 4),
        ({"fragmento": None}, None),
        ({"fragmento": True}, None),      # un bool no es un índice
        ({}, None),
    ],
)
def test_indice_fragmento(bruto: dict, esperado: int | None) -> None:
    assert _indice_fragmento(bruto) == esperado


# --- El filtro anti-alucinación ---------------------------------------------
def test_resuelve_una_referencia_correcta() -> None:
    bruto = {"fuentes": ["codigo_del_trabajo.pdf, pág. 12, Art. 22"]}
    assert _resolver_por_texto(bruto, FRAGMENTOS) is FRAGMENTOS[1]


@pytest.mark.parametrize(
    "fuente, motivo",
    [
        ("Ley 21.220, pág. 3, Art. 99", "documento que no se entregó"),
        ("codigo_del_trabajo.pdf, pág. 99, Art. 22", "página que no corresponde"),
        ("codigo_del_trabajo.pdf, Art. 22", "sin página no se puede verificar"),
        ("Código del Trabajo, artículo 22", "nombre aproximado, sin página"),
        ("ley", "subcadena suelta: el agujero que esto vino a cerrar"),
    ],
)
def test_rechaza_referencias_no_verificables(fuente: str, motivo: str) -> None:
    assert _resolver_por_texto({"fuentes": [fuente]}, FRAGMENTOS) is None, motivo


def test_hallazgo_sin_respaldo_se_descarta() -> None:
    bruto = {"problema": "La jornada excede el máximo legal.", "fragmento": 99}
    assert _normalizar_hallazgo(bruto, FRAGMENTOS) is None


def test_hallazgo_sin_problema_se_descarta() -> None:
    assert _normalizar_hallazgo({"problema": "  ", "fragmento": 1}, FRAGMENTOS) is None


def test_la_cita_la_pone_la_app_no_el_modelo() -> None:
    """El modelo señala [F1]; la referencia se toma del fragmento real."""
    bruto = {
        "problema": "La jornada pactada excede el máximo legal.",
        "gravedad": "alta",
        "fragmento": 1,
        "fuentes": ["Ley inventada, pág. 500"],   # debe ignorarse
    }
    hallazgo = _normalizar_hallazgo(bruto, FRAGMENTOS)
    assert hallazgo is not None
    assert hallazgo["fuentes"] == ["codigo_del_trabajo.pdf, pág. 12, Art. 22"]


def test_gravedad_invalida_cae_a_media() -> None:
    bruto = {"problema": "Algo.", "gravedad": "catastrófica", "fragmento": 1}
    assert _normalizar_hallazgo(bruto, FRAGMENTOS)["gravedad"] == "media"
