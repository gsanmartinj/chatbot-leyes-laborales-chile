"""Panel de administración (Gradio) — Gestión de la base de datos.

Protegido con la autenticación propia de Gradio: sin sesión válida el servidor
no atiende ninguna llamada, ni siquiera a los endpoints de carga y borrado.
Permite subir PDF (que alimentan la base vectorial compartida), listar los
documentos indexados y eliminarlos. La app de chat (Streamlit) lee de la misma
base.

Ejecutar:
    python app_gradio.py
"""

from __future__ import annotations

import secrets
from pathlib import Path
from typing import List

import gradio as gr

from core.config import ADMIN_PASSWORD, ADMIN_PASSWORD_POR_DEFECTO, ADMIN_USER
from core.ingest import (
    delete_document,
    ingest_pdf,
    list_documents,
    reindex,
    stale_documents,
    stats,
)
from ui.gradio_ui import CSS, header_html, stats_html


# --- Autenticación ------------------------------------------------------------
def check_auth(username: str, password: str) -> bool:
    """Valida las credenciales del panel.

    Se entrega a `demo.launch(auth=...)`, que la aplica a nivel de servidor. El
    login anterior solo alternaba la visibilidad de los bloques, de modo que
    `do_ingest` y `do_delete` seguían siendo invocables sin contraseña por quien
    llamara directamente a la API.

    `compare_digest` evita filtrar la clave por el tiempo de comparación.
    """
    return secrets.compare_digest(username or "", ADMIN_USER) and secrets.compare_digest(
        password or "", ADMIN_PASSWORD
    )


# --- Funciones auxiliares -----------------------------------------------------
def _docs_table() -> List[List[object]]:
    """Filas para la tabla de documentos indexados."""
    return [
        [d["source"], d["chunks"], "Al día" if d["actualizado"] else "Reindexar"]
        for d in list_documents()
    ]


def _stats() -> str:
    s = stats()
    return stats_html(s["documentos"], s["fragmentos"])


def _doc_choices() -> List[str]:
    return [d["source"] for d in list_documents()]


def _aviso_desactualizados() -> str:
    """Advierte de los documentos etiquetados con reglas anteriores.

    Sus etiquetas de artículo no son las que produce el código actual, así que
    la búsqueda por artículo responde sobre datos obsoletos hasta reindexarlos.
    """
    pendientes = stale_documents()
    if not pendientes:
        return ""
    return (
        f"**{len(pendientes)} documento(s) se indexaron con una versión anterior "
        "del detector de artículos.** Sus citas por artículo pueden ser "
        "incorrectas. Use «Reindexar desactualizados» para corregirlas: "
        + ", ".join(f"*{p}*" for p in pendientes)
    )


def _refresh_outputs(mensaje: str):
    """Salidas comunes: mensaje + estado + tabla + desplegable + aviso."""
    return (
        mensaje,
        _stats(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
        _aviso_desactualizados(),
    )


# --- Acciones -----------------------------------------------------------------
def do_ingest(files: List[str] | None):
    """Indexa los PDF subidos."""
    if not files:
        return _refresh_outputs("No seleccionó ningún archivo.")

    mensajes: List[str] = []
    for f in files:
        path = Path(f)
        try:
            res = ingest_pdf(path, source_name=path.name)
            mensajes.append(
                f"**{path.name}** — {res['chunks']} fragmento(s) de "
                f"{res['pages']} página(s)."
            )
        except Exception as exc:  # noqa: BLE001
            mensajes.append(f"**{path.name}** — error: {exc}")

    return _refresh_outputs("\n\n".join(mensajes))


def do_delete(source: str | None):
    """Elimina un documento seleccionado."""
    if not source:
        return _refresh_outputs("Seleccione un documento para eliminar.")
    try:
        delete_document(source)
        msg = f"Eliminado: **{source}**"
    except Exception as exc:  # noqa: BLE001
        msg = f"Error al eliminar **{source}**: {exc}"
    return _refresh_outputs(msg)


def do_reindex():
    """Reprocesa los documentos indexados con reglas de detección anteriores."""
    pendientes = stale_documents()
    if not pendientes:
        return _refresh_outputs("No hay documentos desactualizados.")
    return _refresh_outputs("\n\n".join(reindex(pendientes)))


def do_refresh():
    """Refresca las estadísticas y la lista de documentos."""
    return (
        _stats(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
        _aviso_desactualizados(),
    )


# --- Interfaz -----------------------------------------------------------------
with gr.Blocks(title="Administración · Base Documental") as demo:
    gr.HTML(header_html())

    stats_md = gr.HTML()
    stale_md = gr.Markdown(elem_id="lex-msg-stale")

    with gr.Tab("Cargar documentos"):
        files_in = gr.File(
            label="Archivos PDF",
            file_count="multiple",
            file_types=[".pdf"],
            type="filepath",
        )
        ingest_btn = gr.Button("Indexar en la base de datos", variant="primary")
        ingest_out = gr.Markdown(elem_id="lex-msg-ingest")

    with gr.Tab("Documentos indexados"):
        docs_table = gr.Dataframe(
            headers=["Documento", "Fragmentos", "Etiquetado"],
            datatype=["str", "number", "str"],
            interactive=False,
            label="Contenido de la base",
        )
        with gr.Row():
            delete_dropdown = gr.Dropdown(
                label="Documento a eliminar", choices=[], value=None, scale=3
            )
            delete_btn = gr.Button("Eliminar", variant="stop", scale=1)
        with gr.Row():
            refresh_btn = gr.Button("Refrescar", variant="secondary")
            reindex_btn = gr.Button("Reindexar desactualizados", variant="secondary")
        delete_out = gr.Markdown(elem_id="lex-msg-delete")

    # --- Eventos --------------------------------------------------------------
    salidas_completas = [stats_md, docs_table, delete_dropdown, stale_md]

    # El estado se carga al abrir la página; a ella solo se llega autenticado.
    demo.load(do_refresh, inputs=[], outputs=salidas_completas)

    ingest_btn.click(
        do_ingest, inputs=[files_in], outputs=[ingest_out, *salidas_completas]
    )
    delete_btn.click(
        do_delete, inputs=[delete_dropdown], outputs=[delete_out, *salidas_completas]
    )
    reindex_btn.click(do_reindex, inputs=[], outputs=[delete_out, *salidas_completas])
    refresh_btn.click(do_refresh, inputs=[], outputs=salidas_completas)


if __name__ == "__main__":
    if ADMIN_PASSWORD_POR_DEFECTO:
        print(
            "\n  AVISO: ADMIN_PASSWORD sigue siendo la clave de ejemplo.\n"
            "  Copie .env.example a .env y cambie el valor antes de abrir este\n"
            "  panel fuera de este equipo.\n"
        )

    # En Gradio 6 el CSS se entrega en launch(), no en el constructor de Blocks.
    demo.launch(
        css=CSS,
        auth=check_auth,
        auth_message="Panel reservado a la administración de la base documental.",
    )
