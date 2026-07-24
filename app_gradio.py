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


# --- Funciones auxiliares -----------------------------------------------------
def _docs_table() -> List[List[object]]:
    """Filas para la tabla de documentos indexados."""
    return [[d["source"], d["chunks"]] for d in list_documents()]


def _stats_md() -> str:
    s = stats()
    return (
        f"### 📊 Estado de la base de datos\n"
        f"- **Documentos:** {s['documentos']}\n"
        f"- **Fragmentos indexados:** {s['fragmentos']}"
    )


def _doc_choices() -> List[str]:
    return [d["source"] for d in list_documents()]


# --- Acciones -----------------------------------------------------------------
def do_login(password: str):
    """Valida la contraseña y muestra/oculta el panel."""
    if password == ADMIN_PASSWORD:
        return (
            gr.update(visible=False),  # bloque de login
            gr.update(visible=True),   # panel de administración
            "",                         # mensaje de error (limpio)
            _stats_md(),
            _docs_table(),
            gr.update(choices=_doc_choices(), value=None),
        )
    return (
        gr.update(visible=True),
        gr.update(visible=False),
        "❌ Contraseña incorrecta.",
        _stats_md(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
    )


def do_ingest(files: List[str] | None):
    """Indexa los PDF subidos."""
    if not files:
        return (
            "⚠️ No seleccionaste ningún archivo.",
            _stats_md(),
            _docs_table(),
            gr.update(choices=_doc_choices(), value=None),
        )

    mensajes: List[str] = []
    for f in files:
        path = Path(f)
        try:
            res = ingest_pdf(path, source_name=path.name)
            mensajes.append(
                f"✅ **{path.name}**: {res['chunks']} fragmento(s) de "
                f"{res['pages']} página(s)."
            )
        except Exception as exc:  # noqa: BLE001
            mensajes.append(f"❌ **{path.name}**: {exc}")

    return (
        "\n\n".join(mensajes),
        _stats_md(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
    )


def do_delete(source: str | None):
    """Elimina un documento seleccionado."""
    if not source:
        return (
            "⚠️ Selecciona un documento para eliminar.",
            _stats_md(),
            _docs_table(),
            gr.update(choices=_doc_choices(), value=None),
        )
    try:
        delete_document(source)
        msg = f"🗑️ Eliminado: **{source}**"
    except Exception as exc:  # noqa: BLE001
        msg = f"❌ Error al eliminar **{source}**: {exc}"
    return (
        msg,
        _stats_md(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
    )


def do_refresh():
    """Refresca las estadísticas y la lista de documentos."""
    return (
        _stats_md(),
        _docs_table(),
        gr.update(choices=_doc_choices(), value=None),
    )


# --- Interfaz -----------------------------------------------------------------
with gr.Blocks(title="Admin · Leyes Laborales Chile", theme=gr.themes.Soft()) as demo:
    gr.Markdown(
        "# ⚙️ Panel de Administración\n"
        "### Base de datos de leyes laborales de Chile\n"
        "Sube PDF para alimentar la base que consulta el chat. Acceso restringido."
    )

    # Bloque de login (visible al inicio).
    with gr.Group(visible=True) as login_box:
        gr.Markdown("🔒 **Ingresa la contraseña de administrador**")
        password_in = gr.Textbox(
            label="Contraseña", type="password", placeholder="••••••••"
        )
        login_btn = gr.Button("Entrar", variant="primary")
        login_error = gr.Markdown("")

    # Panel de administración (oculto hasta autenticarse).
    with gr.Group(visible=False) as admin_box:
        stats_md = gr.Markdown()

        with gr.Tab("📤 Subir documentos"):
            files_in = gr.File(
                label="Selecciona uno o más PDF",
                file_count="multiple",
                file_types=[".pdf"],
                type="filepath",
            )
            ingest_btn = gr.Button("Indexar en la base de datos", variant="primary")
            ingest_out = gr.Markdown()

        with gr.Tab("📚 Documentos indexados"):
            docs_table = gr.Dataframe(
                headers=["Documento", "Fragmentos"],
                datatype=["str", "number"],
                interactive=False,
                label="Documentos en la base",
            )
            with gr.Row():
                delete_dropdown = gr.Dropdown(
                    label="Documento a eliminar", choices=[], value=None
                )
                delete_btn = gr.Button("🗑️ Eliminar", variant="stop")
            refresh_btn = gr.Button("🔄 Refrescar")
            delete_out = gr.Markdown()

    # --- Eventos --------------------------------------------------------------
    login_btn.click(
        do_login,
        inputs=[password_in],
        outputs=[login_box, admin_box, login_error, stats_md, docs_table, delete_dropdown],
    )
    password_in.submit(
        do_login,
        inputs=[password_in],
        outputs=[login_box, admin_box, login_error, stats_md, docs_table, delete_dropdown],
    )
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
        do_refresh,
        inputs=[],
        outputs=[stats_md, docs_table, delete_dropdown],
    )


if __name__ == "__main__":
    demo.launch()
