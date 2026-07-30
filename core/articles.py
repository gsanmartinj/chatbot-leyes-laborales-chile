"""Reconocimiento de referencias a artículos en un texto.

Vive en su propio módulo porque lo usan las dos puntas del sistema: la ingesta,
para etiquetar cada fragmento con el artículo al que pertenece, y la búsqueda,
para detectar que la pregunta apunta a un artículo concreto.

Tres cosas que el texto legal chileno obliga a distinguir:

**1. Encabezado vs. remisión.**

    Art. 5. El empleador debe respetar las garantías del trabajador,
    conforme a los arts. 22 y 23 de este mismo Código.

Ahí solo hay un artículo, el 5. El "arts. 22 y 23" es una remisión. Tratarla
como inicio de artículo parte el texto por la mitad y etiqueta el resto del
artículo 5 como si fuera el 22.

**2. El salto de línea de un PDF no cierra la frase.** Es el caso que más
etiquetas erróneas produce, porque el PDF corta los renglones a mitad de
oración:

    ...empresas obligadas al cumplimiento de la reserva establecida en el
    artículo 157 bis, sólo podrán ser consideradas...

"artículo 157" abre renglón pero no abre frase. Por eso no basta con mirar el
carácter anterior: hay que mirar cómo termina la línea de arriba.

**3. "157", "157 bis" y "157 quinquies" son artículos DISTINTOS.** Quedarse con
el número colapsa cinco artículos de contenido propio bajo una misma cita, que
para un asistente legal es una respuesta incorrecta con apariencia de exacta.
Por eso la unidad de trabajo de este módulo es una *etiqueta* ("157 bis"), no
un número.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Iterator, Optional, Tuple

# Versión de las reglas de este módulo. Se guarda en los metadatos de cada
# fragmento indexado: cuando cambia, los documentos etiquetados con una versión
# anterior quedan marcados como desactualizados y la app ofrece reindexarlos.
# Sin esto, un cambio aquí deja la base con etiquetas que el código ya no sabe
# producir, y las búsquedas por artículo responden sobre datos fantasma.
DETECTOR_VERSION = 2

# Palabras ordinales usadas en la numeración de artículos ("Artículo primero").
ORDINALS = {
    "primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "séptimo": 7, "octavo": 8, "noveno": 9,
    "decimo": 10, "décimo": 10, "undecimo": 11, "undécimo": 11,
    "duodecimo": 12, "duodécimo": 12, "unico": 1, "único": 1,
}

# Sufijos que la técnica legislativa chilena usa para intercalar artículos sin
# renumerar el cuerpo legal. Se guardan sin tilde: "quáter" y "quater" son el
# mismo artículo y deben producir la misma etiqueta.
SUFIJOS = (
    "bis", "ter", "quater", "quinquies", "sexies", "septies", "octies",
    "nonies", "decies", "undecies", "duodecies", "terdecies",
)

# Ordenados de mayor a menor longitud: en una alternancia, "ter" antes que
# "terdecies" se llevaría solo las tres primeras letras.
_ORDINALES_RE = "|".join(sorted(ORDINALS, key=len, reverse=True))
_SUFIJOS_RE = "|".join(("qu[áa]ter", *(s for s in SUFIJOS if s != "quater")))

_NUM = r"(?P<num>\d{1,4}|" + _ORDINALES_RE + r")"
# "Artículo 1º" / "Artículo 1°". Son dos caracteres distintos y solo uno de los
# dos se comportaba bien: "º" (U+00BA) es categoría Unicode Lo, es decir una
# LETRA, así que un `\b` detrás del número nunca cerraba y el encabezado pasaba
# inadvertido. "°" (U+00B0) es un símbolo y sí cerraba. Ahora se aceptan ambos.
_ORD = r"[º°]?"
_SUF = r"(?:\s+(?P<suf>" + _SUFIJOS_RE + r"))?"
# Cierre propio en lugar de `\b`, por lo mismo que se explica arriba.
_COLA = r"(?!\w)"

_CUERPO = _NUM + _ORD + _SUF + _COLA

# Cita en cualquier posición y en cualquier número ("Artículo 12", "Arts. 3").
# Es la que lee la pregunta del usuario, donde conviene ser permisivo.
ARTICLE_RE = re.compile(r"\bart(?:[íi]culo)?s?\.?\s*" + _CUERPO, re.IGNORECASE)

# Igual, pero solo en singular: un encabezado nunca dice "artículos 22 y 23".
_ARTICLE_SINGULAR_RE = re.compile(r"\bart(?:[íi]culo)?\.?\s*" + _CUERPO, re.IGNORECASE)

# Cierres de frase. Si uno de estos precede a la mención, lo que sigue empieza
# algo nuevo.
_FIN_DE_FRASE = ".;:!?)»\"'"

# Caracteres que se saltan al mirar hacia atrás: adornos que pueden envolver un
# encabezado sin ser parte de la frase anterior.
_ADORNOS = " \t\"'«»-–—"

# Marcador explícito de encabezado: el ".-" con que la ley chilena abre el
# cuerpo del artículo ("Artículo 22.- La jornada..."). Una remisión casi nunca
# lo lleva, así que sirve de desempate cuando la línea anterior no cierra frase
# (por ejemplo, si el PDF intercala un pie de página).
_MARCADOR = re.compile(r"\s*\.\s*[-–—]")


def _plegar(texto: str) -> str:
    """Minúsculas y sin tildes: 'Quáter' y 'quater' son el mismo sufijo."""
    return "".join(
        c for c in unicodedata.normalize("NFD", texto or "")
        if unicodedata.category(c) != "Mn"
    ).lower()


def article_number(token: str) -> Optional[int]:
    """Convierte el token capturado ('12' o 'primero') a un número de artículo."""
    token = (token or "").lower()
    if token.isdigit():
        return int(token)
    return ORDINALS.get(token)


def article_label(num_token: str, suf_token: Optional[str] = None) -> Optional[str]:
    """Etiqueta canónica de un artículo: '157' o '157 bis'.

    Es la unidad con la que trabajan la ingesta y la búsqueda, y también lo que
    se muestra en la cita. Devuelve None si el número no es interpretable.
    """
    numero = article_number(num_token)
    if numero is None:
        return None
    if not suf_token:
        return str(numero)
    return f"{numero} {_plegar(suf_token)}"


def detect_article(texto: str) -> Optional[str]:
    """Etiqueta del primer artículo mencionado en el texto, o None.

    Permisiva a propósito: se usa sobre la pregunta del usuario, donde cualquier
    mención ("¿qué dice el art. 159 bis?") es justo lo que se busca.
    """
    match = ARTICLE_RE.search(texto or "")
    if not match:
        return None
    return article_label(match.group("num"), match.group("suf"))


def _linea_anterior_cierra(texto: str, pos_salto: int) -> bool:
    """¿La línea que termina en `pos_salto` cerraba una frase?

    Un `\\n` en texto extraído de PDF suele ser un corte de renglón a mitad de
    oración, no un fin de párrafo. La única forma de distinguirlo es mirar cómo
    acaba la línea de arriba: con punto (o en blanco) cierra; con una palabra
    cualquiera, la frase continúa en la línea siguiente.
    """
    j = pos_salto - 1
    while j >= 0 and texto[j] in " \t":
        j -= 1
    if j < 0:
        return True                      # no hay nada antes
    if texto[j] == "\n":
        return True                      # línea en blanco: separa bloques
    return texto[j] in _FIN_DE_FRASE


def _es_encabezado(texto: str, inicio: int, fin: int) -> bool:
    """¿La mención que ocupa [inicio, fin) abre un artículo, o solo lo cita?"""
    i = inicio - 1
    while i >= 0 and texto[i] in _ADORNOS:
        i -= 1

    if i < 0:
        return True                      # principio del texto

    if texto[i] != "\n":
        # En mitad de una línea solo cuenta si viene tras un cierre de frase.
        return texto[i] in _FIN_DE_FRASE

    # Abre renglón. Cuenta si la línea de arriba cerraba frase o estaba en
    # blanco; si no, se exige el ".-" del encabezado para aceptarlo.
    if _linea_anterior_cierra(texto, i):
        return True
    return _MARCADOR.match(texto, fin) is not None


def find_headings(texto: str) -> Iterator[Tuple[int, str]]:
    """Encabezados de artículo del texto, como pares (posición, etiqueta).

    Solo cuenta lo que parece abrir un artículo, no las remisiones a otros.
    """
    texto = texto or ""
    for match in _ARTICLE_SINGULAR_RE.finditer(texto):
        if not _es_encabezado(texto, match.start(), match.end()):
            continue
        etiqueta = article_label(match.group("num"), match.group("suf"))
        if etiqueta is not None:
            yield match.start(), etiqueta
