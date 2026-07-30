"""Pruebas del detector de artículos.

Los casos vienen de texto real extraído de PDF de leychile.cl, que es donde el
detector falla: el PDF corta los renglones a mitad de frase, la numeración usa
dos caracteres de ordinal visualmente idénticos, y la ley intercala artículos
con sufijo en vez de renumerar.
"""

from __future__ import annotations

import pytest

from core.articles import detect_article, find_headings

ORD_LETRA = "º"    # º MASCULINE ORDINAL INDICATOR (categoría Lo: es letra)
ORD_GRADO = "°"    # ° DEGREE SIGN (categoría So: es símbolo)


def etiquetas(texto: str) -> list[str]:
    return [e for _, e in find_headings(texto)]


# --- Encabezados que deben reconocerse -------------------------------------
@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Artículo 22.- La jornada ordinaria no excederá de 45 horas.", ["22"]),
        ("Art. 5. El empleador debe respetar las garantías.", ["5"]),
        ("ARTÍCULO 1. Las relaciones laborales se regularán por este Código.", ["1"]),
        ("Artículo primero.- Apruébase el texto refundido.", ["1"]),
        ("Artículo único.- Modifícase el Código del Trabajo.", ["1"]),
        # Los dos ordinales deben comportarse igual. "º" es una letra para
        # Unicode, así que un `\b` detrás del número no cerraba y el encabezado
        # se perdía entero y en silencio.
        (f"Artículo 1{ORD_LETRA}.- Las relaciones laborales.", ["1"]),
        (f"Artículo 1{ORD_GRADO}.- Las relaciones laborales.", ["1"]),
        (f"Art. 4{ORD_LETRA} Para los efectos previstos en este Código.", ["4"]),
    ],
)
def test_reconoce_encabezados(texto: str, esperado: list[str]) -> None:
    assert etiquetas(texto) == esperado


# --- Remisiones que NO deben confundirse con encabezados -------------------
@pytest.mark.parametrize(
    "texto",
    [
        "Según lo dispuesto en el artículo 159, el contrato termina.",
        "Lo anterior se rige por el artículo 161 del mismo cuerpo legal.",
        "(art. 22)",
        "conforme a los arts. 22 y 23 de este mismo Código",
        "Se aplicarán los artículos 1 y 2 de esta ley.",
    ],
)
def test_ignora_remisiones(texto: str) -> None:
    assert etiquetas(texto) == []


def test_encabezado_y_remision_en_la_misma_frase() -> None:
    texto = (
        "Art. 5. El empleador debe respetar las garantías del trabajador,\n"
        "conforme a los arts. 22 y 23 de este mismo Código."
    )
    assert etiquetas(texto) == ["5"]


# --- El salto de línea del PDF no cierra la frase --------------------------
def test_corte_de_renglon_no_abre_articulo() -> None:
    """Caso literal de Ley 21.690, pág. 2.

    El PDF parte la oración y "artículo 157" queda abriendo renglón sin abrir
    frase. Tomarlo por encabezado etiquetaba como artículo 157 un texto que
    solo son instrucciones de modificación.
    """
    texto = (
        "empresas que presten servicios y que sean, a su vez, empresas\n"
        "obligadas al cumplimiento de la reserva establecida en el\n"
        "artículo 157 bis, sólo podrán ser consideradas para el cumplimiento\n"
        "subsidiario de otras empresas obligadas por la ley."
    )
    assert etiquetas(texto) == []


def test_linea_anterior_cerrada_si_abre_articulo() -> None:
    texto = (
        "...de conformidad a lo dispuesto en el artículo 24 de la ley 20.422.\n"
        " \n"
        " Artículo 157 sexies.- La infracción a la obligación establecida."
    )
    assert etiquetas(texto) == ["157 sexies"]


def test_marcador_desempata_tras_un_pie_de_pagina() -> None:
    """El pie de página deja una línea que no cierra frase; el '.-' sí decide."""
    texto = (
        "Biblioteca del Congreso Nacional de Chile - www.leychile.cl\n"
        "página 2 de 11\n"
        "Artículo 157 quinquies.- Las empresas sujetas a la obligación."
    )
    assert etiquetas(texto) == ["157 quinquies"]


# --- Sufijos: son artículos distintos --------------------------------------
@pytest.mark.parametrize(
    "texto, esperado",
    [
        ("Artículo 157 bis.- Las empresas de cien o más trabajadores.", "157 bis"),
        ("Artículo 157 ter.- El empleador deberá informar.", "157 ter"),
        ("Artículo 157 quáter.- Un reglamento determinará.", "157 quater"),
        ("Artículo 157 quinquies.- Las empresas sujetas.", "157 quinquies"),
        ("Artículo 157 sexies.- La infracción a la obligación.", "157 sexies"),
    ],
)
def test_sufijos_producen_articulos_distintos(texto: str, esperado: str) -> None:
    assert etiquetas(texto) == [esperado]


def test_quater_con_y_sin_tilde_es_el_mismo_articulo() -> None:
    con = etiquetas("Artículo 157 quáter.- Un reglamento determinará.")
    sin = etiquetas("Artículo 157 quater.- Un reglamento determinará.")
    assert con == sin == ["157 quater"]


def test_articulo_con_sufijo_no_se_confunde_con_el_base() -> None:
    """Lo que hacía que preguntar por el 157 devolviera texto del 157 bis."""
    base = etiquetas("Artículo 157.- Las empresas de cien o más trabajadores.")
    bis = etiquetas("Artículo 157 bis.- Regla distinta y contenido propio.")
    assert base == ["157"]
    assert bis == ["157 bis"]
    assert base != bis


def test_numero_seguido_de_palabra_corriente_no_es_sufijo() -> None:
    assert etiquetas("Artículo 157.- Las empresas y siguientes normas.") == ["157"]


# --- Detección sobre la pregunta del usuario -------------------------------
@pytest.mark.parametrize(
    "pregunta, esperado",
    [
        ("¿Qué dice el artículo 159?", "159"),
        ("que dice el art. 22", "22"),
        ("¿me pueden despedir por el artículo 161?", "161"),
        ("¿qué dice el artículo 157 bis?", "157 bis"),
        (f"¿qué dice el artículo 1{ORD_LETRA}?", "1"),
        (f"¿qué dice el artículo 1{ORD_GRADO}?", "1"),
        ("¿cuántos días de vacaciones tengo?", None),
        ("necesito el arte de negociar", None),
        ("", None),
    ],
)
def test_detect_article(pregunta: str, esperado: str | None) -> None:
    assert detect_article(pregunta) == esperado


def test_varios_articulos_seguidos_en_una_pagina() -> None:
    pagina = (
        f"Artículo 1{ORD_LETRA}.- Las relaciones laborales entre los empleadores\n"
        "y los trabajadores se regularán por este Código.\n"
        f"Artículo 2{ORD_LETRA}.- Reconócese la función social que cumple el\n"
        "trabajo y la libertad de las personas para contratar.\n"
        f"Artículo 3{ORD_LETRA}.- Para todos los efectos legales se entiende por\n"
        "empleador la persona natural o jurídica."
    )
    assert etiquetas(pagina) == ["1", "2", "3"]
