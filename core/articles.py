"""Reconocimiento de referencias a artículos en un texto.

Vive en su propio módulo porque lo usan las dos puntas del sistema: la ingesta,
para etiquetar cada fragmento con el artículo al que pertenece, y la búsqueda,
para detectar que la pregunta apunta a un artículo concreto. Estaba duplicado en
ambos módulos y las dos copias se habían desincronizado.
"""

from __future__ import annotations

import re
from typing import Optional

# Palabras ordinales usadas en la numeración de artículos ("Artículo primero").
ORDINALS = {
    "primero": 1, "segundo": 2, "tercero": 3, "cuarto": 4, "quinto": 5,
    "sexto": 6, "septimo": 7, "séptimo": 7, "octavo": 8, "noveno": 9,
    "decimo": 10, "décimo": 10, "undecimo": 11, "undécimo": 11,
    "duodecimo": 12, "duodécimo": 12, "unico": 1, "único": 1,
}

# Formas admitidas: "Artículo 12", "artículos 3", "Art. 12", "Arts. 3", "Art 7".
# Solo "art" es obligatorio; la terminación "ículo(s)", el punto y el espacio son
# opcionales, que es como aparecen en la mayoría de los textos legales chilenos
# (la versión anterior exigía la palabra completa y se perdía todos los "Art.").
ARTICLE_RE = re.compile(
    r"\bart(?:[íi]culo)?s?\.?\s*(\d{1,4}|" + "|".join(ORDINALS) + r")\b",
    re.IGNORECASE,
)


def article_number(token: str) -> Optional[int]:
    """Convierte el token capturado ('12' o 'primero') a un número de artículo."""
    token = token.lower()
    if token.isdigit():
        return int(token)
    return ORDINALS.get(token)


def detect_article(texto: str) -> Optional[int]:
    """Devuelve el número del primer artículo mencionado en el texto, o None."""
    match = ARTICLE_RE.search(texto or "")
    return article_number(match.group(1)) if match else None
