"""Reconocimiento de referencias a artículos en un texto.

Vive en su propio módulo porque lo usan las dos puntas del sistema: la ingesta,
para etiquetar cada fragmento con el artículo al que pertenece, y la búsqueda,
para detectar que la pregunta apunta a un artículo concreto. Estaba duplicado en
ambos módulos y las dos copias se habían desincronizado.

La distinción importante es entre **encabezado** y **cita**:

    Art. 5. El empleador debe respetar las garantías del trabajador,
    conforme a los arts. 22 y 23 de este mismo Código.

Ahí solo hay un artículo, el 5. El "arts. 22 y 23" es una remisión, y los textos
legales están llenos de ellas. Tratarlas como inicio de artículo parte el texto
por la mitad y etiqueta el resto del artículo 5 como si fuera el 22.
`find_headings` las descarta con dos señales: los encabezados van en singular y
abren frase; las citas van en plural o dentro de la frase.
"""

from __future__ import annotations

import re
from typing import Iterator, Optional, Tuple

# Palabras ordinales usadas en la numeración de artículos ("Artículo primero").
ORDINALS = {
    "primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "séptimo": 7, "octavo": 8, "noveno": 9,
    "decimo": 10, "décimo": 10, "undecimo": 11, "undécimo": 11,
    "duodecimo": 12, "duodécimo": 12, "unico": 1, "único": 1,
}

_NUMERO = r"(\d{1,4}|" + "|".join(ORDINALS) + r")"

# Cita en cualquier posición y en cualquier número: "Artículo 12", "artículos 3",
# "Art. 12", "Arts. 3", "Art 7". Es la que se usa para leer la pregunta del
# usuario, donde conviene ser permisivo. La versión anterior exigía la palabra
# completa y se perdía todos los "Art.", que es como aparecen en la mayoría de
# los textos legales chilenos.
ARTICLE_RE = re.compile(r"\bart(?:[íi]culo)?s?\.?\s*" + _NUMERO + r"\b", re.IGNORECASE)

# Igual, pero solo en singular: un encabezado nunca dice "artículos 22 y 23".
_ARTICLE_SINGULAR_RE = re.compile(
    r"\bart(?:[íi]culo)?\.?\s*" + _NUMERO + r"\b", re.IGNORECASE
)

# Un encabezado abre frase: o empieza renglón, o viene tras punto, punto y coma
# o dos puntos. Una remisión ("conforme a los arts. 22") va precedida de una
# preposición o un artículo determinado, nunca de un cierre de frase.
_FIN_DE_FRASE = ".;:)»\"'"


def article_number(token: str) -> Optional[int]:
    """Convierte el token capturado ('12' o 'primero') a un número de artículo."""
    token = token.lower()
    if token.isdigit():
        return int(token)
    return ORDINALS.get(token)


def detect_article(texto: str) -> Optional[int]:
    """Devuelve el número del primer artículo mencionado en el texto, o None.

    Permisiva a propósito: se usa sobre la pregunta del usuario, donde cualquier
    mención ("¿qué dice el art. 159?") es lo que se busca.
    """
    match = ARTICLE_RE.search(texto or "")
    return article_number(match.group(1)) if match else None


def _abre_frase(texto: str, inicio: int) -> bool:
    """¿La posición `inicio` está al principio de una frase o de un renglón?"""
    i = inicio - 1
    # Saltar los espacios y tabuladores que preceden a la palabra.
    while i >= 0 and texto[i] in " \t":
        i -= 1
    if i < 0:
        return True                      # principio del texto
    if texto[i] == "\n":
        return True                      # principio de renglón
    return texto[i] in _FIN_DE_FRASE     # tras cierre de frase


def find_headings(texto: str) -> Iterator[Tuple[int, int]]:
    """Encabezados de artículo del texto, como pares (posición, número).

    Solo cuenta lo que parece abrir un artículo, no las remisiones a otros.
    """
    for match in _ARTICLE_SINGULAR_RE.finditer(texto or ""):
        if not _abre_frase(texto, match.start()):
            continue
        numero = article_number(match.group(1))
        if numero is not None:
            yield match.start(), numero
