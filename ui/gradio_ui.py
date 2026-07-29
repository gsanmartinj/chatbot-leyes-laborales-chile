"""Estilos y componentes visuales del panel de administración (Gradio).

Misma familia visual que el chat (Fraunces + Newsreader, acento bordeaux) pero
invertida a tinta oscura: el panel es la trastienda del sistema, no la cara
pública. Los selectores se apoyan en `elem_id`/`elem_classes` propios para no
depender de las clases internas de Gradio.
"""

from __future__ import annotations

CSS = """
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..700&family=Newsreader:opsz,wght@6..72,200..700&display=swap');

:root,.gradio-container{
  --lex-ink:#12151C;
  --lex-panel:#191D26;
  --lex-panel-2:#20252F;
  --lex-line:rgba(233,228,214,.13);
  --lex-paper:#E9E4D6;
  --lex-dim:#9B9486;
  --lex-accent:#C9575A;
  --lex-ochre:#C89B3C;
  --lex-serif:'Newsreader',Georgia,serif;
  --lex-display:'Fraunces',Georgia,serif;
}

body,gradio-app,.app{background:var(--lex-ink)!important;}

.gradio-container{
  background:
    radial-gradient(900px 480px at 88% -8%, rgba(201,87,90,.12), transparent 60%),
    radial-gradient(700px 400px at -5% 3%, rgba(200,155,60,.07), transparent 58%),
    var(--lex-ink)!important;
  color:var(--lex-paper)!important;
  font-family:var(--lex-serif)!important;
  max-width:920px!important;margin:0 auto!important;
}
.gradio-container .prose,.gradio-container p,.gradio-container span,.gradio-container label{color:var(--lex-paper);}
footer{display:none!important;}

/* ---------- cabecera ---------- */
#lex-top{margin:1.6rem 0 2rem;}
#lex-top .eyebrow{
  font-family:var(--lex-display);font-size:.66rem;font-weight:600;letter-spacing:.24em;
  text-transform:uppercase;color:var(--lex-accent);margin-bottom:.75rem;
}
#lex-top h1{
  font-family:var(--lex-display);font-weight:350;font-size:clamp(2.1rem,5.5vw,3.1rem);
  line-height:.95;letter-spacing:-.025em;color:#F3EFE2;margin:0;
}
#lex-top h1 em{font-style:italic;color:var(--lex-accent);}
#lex-top .rule{height:1px;background:linear-gradient(90deg,var(--lex-paper),var(--lex-line) 45%,transparent);margin:1.15rem 0 .9rem;}
#lex-top .sub{font-family:var(--lex-serif);font-size:1rem;line-height:1.55;color:var(--lex-dim);max-width:56ch;margin:0;}

/* ---------- bloques ---------- */
.gradio-container .block,.gradio-container .form,.gradio-container .panel{
  background:var(--lex-panel)!important;border:1px solid var(--lex-line)!important;
  border-radius:5px!important;box-shadow:none!important;
}
#lex-stats{
  font-family:var(--lex-display);border-top:1px solid var(--lex-line);
  border-bottom:1px solid var(--lex-line);padding:.8rem 0;margin:.4rem 0 1.4rem;
}
#lex-stats b{color:#F3EFE2;font-weight:500;font-size:1.25rem;}
#lex-stats span{color:var(--lex-dim);font-size:.63rem;letter-spacing:.19em;text-transform:uppercase;}

/* ---------- campos ---------- */
.gradio-container input,.gradio-container textarea,.gradio-container select{
  background:var(--lex-panel-2)!important;color:var(--lex-paper)!important;
  border:1px solid var(--lex-line)!important;border-radius:4px!important;
  font-family:var(--lex-serif)!important;font-size:1rem!important;
}
.gradio-container input:focus,.gradio-container textarea:focus{
  border-color:var(--lex-accent)!important;box-shadow:0 0 0 3px rgba(201,87,90,.15)!important;outline:none!important;
}
.gradio-container label span{
  font-family:var(--lex-display)!important;font-size:.68rem!important;font-weight:600!important;
  letter-spacing:.16em!important;text-transform:uppercase!important;color:var(--lex-dim)!important;
}

/* ---------- botones ---------- */
.gradio-container button{
  font-family:var(--lex-display)!important;font-weight:500!important;letter-spacing:.01em!important;
  border-radius:4px!important;transition:all .18s ease!important;
}
.gradio-container button.primary{
  background:var(--lex-accent)!important;border:1px solid var(--lex-accent)!important;color:#FCFAF4!important;
}
.gradio-container button.primary:hover{background:#B0454A!important;transform:translateY(-1px);}
.gradio-container button.secondary{
  background:transparent!important;border:1px solid var(--lex-line)!important;color:var(--lex-paper)!important;
}
.gradio-container button.secondary:hover{background:var(--lex-panel-2)!important;border-color:var(--lex-dim)!important;}
.gradio-container button.stop{background:transparent!important;border:1px solid rgba(201,87,90,.5)!important;color:var(--lex-accent)!important;}
.gradio-container button.stop:hover{background:var(--lex-accent)!important;color:#FCFAF4!important;}

/* ---------- pestañas ---------- */
.gradio-container [role="tab"]{
  font-family:var(--lex-display)!important;font-size:.8rem!important;letter-spacing:.05em!important;
  color:var(--lex-dim)!important;background:transparent!important;border:0!important;
  border-bottom:2px solid transparent!important;border-radius:0!important;
}
.gradio-container [role="tab"][aria-selected="true"],.gradio-container [role="tab"].selected{
  color:#F3EFE2!important;border-bottom-color:var(--lex-accent)!important;background:transparent!important;
}
.gradio-container .tab-nav,.gradio-container .tabs>div:first-child{border-bottom:1px solid var(--lex-line)!important;}

/* ---------- zona de archivos y tabla ---------- */
.gradio-container .file-preview,.gradio-container [data-testid="block-label"]{background:transparent!important;}
.gradio-container table{font-family:var(--lex-serif)!important;border-color:var(--lex-line)!important;}
.gradio-container thead th{
  background:var(--lex-panel-2)!important;color:var(--lex-dim)!important;
  font-family:var(--lex-display)!important;font-size:.66rem!important;letter-spacing:.14em!important;
  text-transform:uppercase!important;border-color:var(--lex-line)!important;
}
.gradio-container tbody td{background:var(--lex-panel)!important;color:var(--lex-paper)!important;border-color:var(--lex-line)!important;}

/* ---------- mensajes de salida ---------- */
#lex-msg-ingest,#lex-msg-delete{font-family:var(--lex-serif);font-size:.98rem;line-height:1.6;}
#lex-msg-ingest strong,#lex-msg-delete strong{color:#F3EFE2;}

@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
"""


def header_html() -> str:
    """Cabecera del panel de administración."""
    return """
<div id="lex-top">
  <div class="eyebrow">Panel reservado · Administración</div>
  <h1>Base <em>Documental</em></h1>
  <div class="rule"></div>
  <p class="sub">Cargue aquí los documentos que alimentan el asistente. Cada PDF
  se divide en fragmentos, se indexa y queda disponible de inmediato para las
  consultas del chat.</p>
</div>
"""


def stats_html(documentos: int, fragmentos: int) -> str:
    """Banda con el estado de la base de datos."""
    return f"""
<div id="lex-stats">
  <b>{documentos}</b> <span>Documentos</span>
  &nbsp;&nbsp;·&nbsp;&nbsp;
  <b>{fragmentos}</b> <span>Fragmentos indexados</span>
</div>
"""
