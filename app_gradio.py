"""Panel de administración (Gradio) — Gestión de la base de datos.

Protegido con contraseña. Permite subir PDF (que alimentan la base vectorial
compartida), listar los documentos indexados y eliminarlos. La app de chat
(Streamlit) lee de la misma base.

Ejecutar:
    python app_gradio.py
"""

from __future__ import annotations

from pathlib import Path
from typing import List

import gradio as gr

from core.config import ADMIN_PASSWORD
from core.ingest import delete_document, ingest_pdf, list_documents, stats
from ui.gradio_ui import CSS, header_html, stats_html


# --- Funciones auxiliares -----------------------------------------------------
def _docs_table() -> List[List[object]]:
    """Filas para la tabla de documentos indexados."""
    return [[d["source"], d["chunks"]] for d in list_documents()]


def _stats() -> str:
    s = stats()
    return stats_html(s["documentos"], s["fragmentos"])


def _doc_choices() -> List[str]:
    return [d["source"] for d in list_documents()]


def _refresh_outputs(mensaje: str):
    """Salidas comunes: mensaje + estado + tabla + desplegable."""
    return (
        mensaje,
        _stats(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
    )


# --- Acciones -----------------------------------------------------------------
def do_login(password: str):
    """Valida la contraseña y muestra/oculta el panel."""
    ok = password == ADMIN_PASSWORD
    return (
        gr.update(visible=not ok),          # bloque de login
        gr.update(visible=ok),              # panel de administración
        "" if ok else "Contraseña incorrecta.",
        _stats(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
    )


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


def do_refresh():
    """Refresca las estadísticas y la lista de documentos."""
    return (
        _stats(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
    )


# --- Interfaz -----------------------------------------------------------------
with gr.Blocks(title="Administración · Base Documental") as demo:
    gr.HTML(header_html())

    # Bloque de login (visible al inicio).
    with gr.Group(visible=True, elem_id="lex-login") as login_box:
        gr.HTML('<div class="lex-lock">Acceso restringido</div>')
        password_in = gr.Textbox(
            label="Contraseña", type="password", placeholder="••••••••"
        )
        login_btn = gr.Button("Ingresar", variant="primary")
        login_error = gr.Markdown("", elem_id="lex-msg-login")

    # Panel de administración (oculto hasta autenticarse).
    with gr.Column(visible=False) as admin_box:
        stats_md = gr.HTML()

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
                headers=["Documento", "Fragmentos"],
                datatype=["str", "number"],
                interactive=False,
                label="Contenido de la base",
            )
            with gr.Row():
                delete_dropdown = gr.Dropdown(
                    label="Documento a eliminar", choices=[], value=None, scale=3
                )
                delete_btn = gr.Button("Eliminar", variant="stop", scale=1)
            refresh_btn = gr.Button("Refrescar", variant="secondary")
            delete_out = gr.Markdown(elem_id="lex-msg-delete")

    # --- Eventos --------------------------------------------------------------
    login_outputs = [
        login_box, admin_box, login_error, stats_md, docs_table, delete_dropdown
    ]
    login_btn.click(do_login, inputs=[password_in], outputs=login_outputs)
    password_in.submit(do_login, inputs=[password_in], outputs=login_outputs)

    ingest_btn.click(
        do_ingest,
        inputs=[files_in],
        outputs=[ingest_out, stats_md, docs_table, delete_dropdown],
    )
    delete_btn.click(
        do_delete,
        inputs=[delete_dropdown],
        outputs=[delete_out, stats_md, docs_table, delete_dropdown],
    )
    refresh_btn.click(
        do_refresh, inputs=[], outputs=[stats_md, docs_table, delete_dropdown]
    )


if __name__ == "__main__":
    # En Gradio 6 el CSS se entrega en launch(), no en el constructor de Blocks.
    demo.launch(css=CSS)
