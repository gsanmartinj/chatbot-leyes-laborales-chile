"""Ingesta de PDF a la base vectorial.

Flujo: PDF -> texto por página -> fragmentos (chunks) con solapamiento ->
embeddings -> almacenamiento en ChromaDB con metadatos para poder citar
(archivo de origen y número de página).
"""

from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict, List

from .articles import DETECTOR_VERSION, find_headings
from .config import CHUNK_OVERLAP, CHUNK_SIZE, PDF_DIR
from .db import get_collection
from .embeddings import embed_texts


def _clean(text: str) -> str:
    """Normaliza espacios en blanco del texto extraído del PDF."""
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _chunk_text(text: str, size: int = CHUNK_SIZE, overlap: int = CHUNK_OVERLAP) -> List[str]:
    """Divide un texto en fragmentos de ~`size` caracteres con `overlap` de solapamiento.

    Intenta cortar en un límite de palabra para no partir términos por la mitad.
    """
    text = text.strip()
    if not text:
        return []
    if len(text) <= size:
        return [text]

    chunks: List[str] = []
    start = 0
    n = len(text)
    while start < n:
        end = min(start + size, n)
        # Retroceder hasta un espacio cercano para no cortar una palabra.
        if end < n:
            space = text.rfind(" ", start + size - overlap, end)
            if space != -1 and space > start:
                end = space
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= n:
            break
        start = max(end - overlap, start + 1)
    return chunks


def extract_pages(pdf_path: str | Path) -> List[str]:
    """Extrae el texto de cada página del PDF (índice 0 = página 1).

    Público porque también lo usa la revisión de contratos (`core.contract`),
    que lee un PDF sin indexarlo.
    """
    from pypdf import PdfReader

    reader = PdfReader(str(pdf_path))
    return [_clean(page.extract_text() or "") for page in reader.pages]


def ingest_pdf(pdf_path: str | Path, source_name: str | None = None) -> Dict[str, int]:
    """Indexa un PDF en la base vectorial.

    Args:
        pdf_path: ruta al PDF a procesar.
        source_name: nombre con el que se guardará/citará. Por defecto, el nombre del archivo.

    Returns:
        dict con {"chunks": n_fragmentos, "pages": n_paginas}.
    """
    pdf_path = Path(pdf_path)
    source = source_name or pdf_path.name

    # `source` termina como nombre de fichero en data/pdfs/ y como clave de
    # borrado, así que no puede contener rutas: "../../x.pdf" escribiría (y luego
    # borraría) fuera de la carpeta de datos.
    if source in ("", ".", "..") or source != Path(source).name:
        raise ValueError(
            f"Nombre de documento no válido: {source!r}. "
            "Debe ser un nombre de archivo, sin carpetas."
        )

    pages = extract_pages(pdf_path)

    documents: List[str] = []
    metadatas: List[Dict[str, object]] = []
    ids: List[str] = []

    current_article: str | None = None  # última etiqueta vista (se arrastra entre páginas)
    seq = 0                              # orden global del fragmento (para reordenar luego)

    for page_num, page_text in enumerate(pages, start=1):
        # Posiciones y números de los encabezados de artículo en esta página.
        # `find_headings` descarta las remisiones a otros artículos ("conforme a
        # los arts. 22 y 23"), que no abren artículo y partirían el texto.
        markers = list(find_headings(page_text))

        # Cortar la página en tramos, uno por artículo, antes de trocear. Así cada
        # fragmento cae dentro de un solo artículo. Trocear la página entera y
        # luego preguntar "¿qué artículo estaba activo donde empieza este
        # fragmento?" perdía todos los artículos que empezaban dentro de él: con
        # CHUNK_SIZE=800 un fragmento abarca varios y solo se quedaba con uno.
        tramos: List[tuple[str | None, str]] = []
        # Lo que precede al primer encabezado continúa el artículo de la página
        # anterior (o no pertenece a ninguno, si aún no ha aparecido).
        primero = markers[0][0] if markers else len(page_text)
        if primero > 0:
            tramos.append((current_article, page_text[:primero]))
        for i, (pos, etiqueta) in enumerate(markers):
            fin = markers[i + 1][0] if i + 1 < len(markers) else len(page_text)
            tramos.append((etiqueta, page_text[pos:fin]))

        chunk_idx = 0
        for article, tramo in tramos:
            for chunk in _chunk_text(tramo):
                # `dv` deja constancia de con qué reglas se etiquetó esto: si el
                # detector cambia, `stale_documents()` lo delata en vez de dejar
                # la base respondiendo con etiquetas que ya nadie sabe reproducir.
                meta: Dict[str, object] = {
                    "source": source, "page": page_num, "seq": seq,
                    "dv": DETECTOR_VERSION,
                }
                if article is not None:
                    meta["articulo"] = article

                documents.append(chunk)
                metadatas.append(meta)
                ids.append(f"{source}::p{page_num}::c{chunk_idx}")
                seq += 1
                chunk_idx += 1

        if markers:
            current_article = markers[-1][1]

    if not documents:
        raise ValueError(
            "No se pudo extraer texto de este PDF. "
            "Puede ser un documento escaneado (imagen) sin texto seleccionable."
        )

    # El reemplazo de la versión anterior se hace aquí y no al principio: si el
    # PDF nuevo no tiene texto extraíble, la excepción de arriba salta antes de
    # borrar nada y el documento que ya estaba indexado sobrevive intacto.
    delete_document(source, remove_file=False)

    # Guardar una copia del PDF original en data/pdfs/.
    dest = PDF_DIR / source
    if pdf_path.resolve() != dest.resolve():
        shutil.copy2(pdf_path, dest)

    # Calcular embeddings e insertar en lotes para no saturar memoria.
    collection = get_collection()
    batch = 128
    for i in range(0, len(documents), batch):
        docs_b = documents[i : i + batch]
        collection.add(
            ids=ids[i : i + batch],
            documents=docs_b,
            metadatas=metadatas[i : i + batch],
            embeddings=embed_texts(docs_b),
        )

    return {"chunks": len(documents), "pages": len(pages)}


def list_documents() -> List[Dict[str, object]]:
    """Lista los documentos indexados con su número de fragmentos y su estado.

    Returns:
        lista de dicts {"source": nombre, "chunks": n, "actualizado": bool}
        ordenada por nombre. `actualizado` es False si el documento se indexó
        con una versión anterior del detector de artículos.
    """
    collection = get_collection()
    got = collection.get(include=["metadatas"])
    info: Dict[str, Dict[str, object]] = {}
    for meta in got.get("metadatas") or []:
        meta = meta or {}
        src = str(meta.get("source", "desconocido"))
        datos = info.setdefault(src, {"chunks": 0, "actualizado": True})
        datos["chunks"] = int(datos["chunks"]) + 1
        if meta.get("dv") != DETECTOR_VERSION:
            datos["actualizado"] = False
    return [
        {"source": src, "chunks": info[src]["chunks"],
         "actualizado": info[src]["actualizado"]}
        for src in sorted(info)
    ]


def stale_documents() -> List[str]:
    """Documentos indexados con reglas de detección anteriores a las vigentes.

    Sus etiquetas de artículo no se corresponden con lo que el código produce
    hoy, así que la búsqueda por artículo responde sobre datos obsoletos hasta
    que se reindexen.
    """
    return [str(d["source"]) for d in list_documents() if not d["actualizado"]]


def reindex(sources: List[str] | None = None) -> List[str]:
    """Vuelve a indexar documentos desde la copia guardada en data/pdfs/.

    Args:
        sources: documentos a reprocesar. Por defecto, los desactualizados.

    Returns:
        una línea de resultado por documento, para mostrar en la interfaz.
    """
    objetivos = stale_documents() if sources is None else sources
    mensajes: List[str] = []
    for src in objetivos:
        pdf = PDF_DIR / src
        if not pdf.exists():
            mensajes.append(
                f"**{src}** — no se conserva el PDF original; vuelva a subirlo."
            )
            continue
        try:
            res = ingest_pdf(pdf, source_name=src)
            mensajes.append(f"**{src}** — reindexado: {res['chunks']} fragmento(s).")
        except Exception as exc:  # noqa: BLE001
            mensajes.append(f"**{src}** — error al reindexar: {exc}")
    return mensajes


def delete_document(source: str, remove_file: bool = True) -> None:
    """Elimina de la base todos los fragmentos de un documento y (opcional) su PDF."""
    collection = get_collection()
    collection.delete(where={"source": source})
    if remove_file:
        pdf_file = PDF_DIR / source
        if pdf_file.exists():
            pdf_file.unlink()


def stats() -> Dict[str, int]:
    """Devuelve estadísticas globales de la base: nº de documentos y de fragmentos."""
    docs = list_documents()
    return {
        "documentos": len(docs),
        "fragmentos": sum(int(d["chunks"]) for d in docs),
    }
