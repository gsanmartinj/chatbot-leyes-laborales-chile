"""Estilos y componentes visuales del chat (Streamlit).

Dirección de diseño: **editorial jurídico**. Papel cálido con grano, tipografía
serif de carácter (Fraunces para títulos, Newsreader para prosa), acento
bordeaux y ocre. La barra lateral se invierte a tinta oscura para dar contraste
compositivo. Sin emojis decorativos: la jerarquía la marca la tipografía.
"""

from __future__ import annotations

# Textura de papel: ruido fractal en SVG embebido (sin peticiones externas).
_GRAIN = (
    "url(\"data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' "
    "width='180' height='180'%3E%3Cfilter id='n'%3E%3CfeTurbulence "
    "type='fractalNoise' baseFrequency='.8' numOctaves='3'/%3E%3C/filter%3E"
    "%3Crect width='100%25' height='100%25' filter='url(%23n)' opacity='.42'/"
    "%3E%3C/svg%3E\")"
)

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Fraunces:ital,opsz,wght@0,9..144,300..900;1,9..144,300..700&family=Newsreader:ital,opsz,wght@0,6..72,200..700;1,6..72,200..600&display=swap');

:root{
  --paper:#F4F0E6;
  --paper-card:#FCFAF4;
  --paper-2:#E9E3D3;
  --ink:#171B24;
  --ink-2:#3E4655;
  --ink-3:#767E8E;
  --accent:#A03033;
  --accent-2:#C9575A;
  --ochre:#B58A34;
  --rule:rgba(23,27,36,.13);
  --serif:'Newsreader',Georgia,'Times New Roman',serif;
  --display:'Fraunces',Georgia,serif;
}

/* ---------- lienzo ---------- */
.stApp{
  background:
    radial-gradient(1100px 560px at 82% -12%, rgba(181,138,52,.15), transparent 62%),
    radial-gradient(880px 480px at -5% 2%, rgba(160,48,51,.08), transparent 58%),
    var(--paper);
  color:var(--ink);
}
.stApp::before{
  content:"";position:fixed;inset:0;z-index:0;pointer-events:none;
  opacity:.55;mix-blend-mode:multiply;background-image:__GRAIN__;
}
.block-container{position:relative;z-index:1;max-width:820px;padding-top:2.2rem;padding-bottom:7rem;}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stBottom"] > div,[data-testid="stBottomBlockContainer"]{background:transparent;}

/* ---------- cabecera ---------- */
.lex-head{margin:.4rem 0 2.4rem;}
.lex-eyebrow{
  font-family:var(--display);font-size:.7rem;font-weight:600;letter-spacing:.26em;
  text-transform:uppercase;color:var(--accent);margin-bottom:1rem;
  animation:lexUp .7s cubic-bezier(.22,1,.36,1) both;
}
/* Streamlit aplica sus propios estilos a h1: hace falta !important. */
.lex-title,.stApp h1.lex-title{
  font-family:var(--display)!important;font-optical-sizing:auto;font-weight:350!important;
  font-size:clamp(2.9rem,8.5vw,5.2rem)!important;line-height:.9!important;
  letter-spacing:-.028em!important;color:var(--ink)!important;
  margin:0!important;padding:0!important;
  animation:lexUp .7s cubic-bezier(.22,1,.36,1) .07s both;
}
.lex-title em{font-style:italic;font-weight:400;color:var(--accent);}
/* Ocultar el enlace de ancla que Streamlit añade a los encabezados. */
.lex-head [data-testid="stHeaderActionElements"]{display:none!important;}
.lex-rule{
  height:1px;background:linear-gradient(90deg,var(--ink) 0%,var(--rule) 42%,transparent 100%);
  margin:1.5rem 0 1.1rem;transform-origin:left;
  animation:lexWipe .9s cubic-bezier(.22,1,.36,1) .18s both;
}
.lex-sub{
  font-family:var(--serif)!important;font-size:1.045rem!important;line-height:1.6!important;
  color:var(--ink-2)!important;max-width:53ch;margin:0!important;
  animation:lexUp .7s cubic-bezier(.22,1,.36,1) .24s both;
}
.lex-sub b{color:var(--ink);font-weight:600;}

/* ---------- banda de estado ---------- */
.lex-strip{
  display:flex;flex-wrap:wrap;gap:2.2rem;align-items:baseline;
  border-top:1px solid var(--rule);border-bottom:1px solid var(--rule);
  padding:.85rem 0;margin:1.9rem 0 2.1rem;
  animation:lexUp .7s cubic-bezier(.22,1,.36,1) .32s both;
}
.lex-stat{display:flex;flex-direction:column;gap:.18rem;}
.lex-stat .n{font-family:var(--display)!important;font-size:1.5rem;font-weight:400;line-height:1;color:var(--ink);}
.lex-stat .l{font-family:var(--display)!important;font-size:.62rem;font-weight:600;letter-spacing:.19em;text-transform:uppercase;color:var(--ink-3);}
.lex-stat.engine .n{font-size:.95rem;color:var(--accent);letter-spacing:.01em;}
.lex-warn{
  font-family:var(--serif)!important;font-size:.97rem!important;line-height:1.55;color:#7A4B12!important;
  background:rgba(181,138,52,.11);border-left:2px solid var(--ochre);
  padding:.85rem 1.1rem;border-radius:0 4px 4px 0;margin:0 0 1.8rem;
}

/* ---------- sugerencias ---------- */
.lex-hint{
  font-family:var(--display);font-size:.63rem;font-weight:600;letter-spacing:.2em;
  text-transform:uppercase;color:var(--ink-3);margin:.3rem 0 .7rem;
}

/* ---------- mensajes ---------- */
[data-testid="stChatMessage"]{
  background:transparent;border:0;padding:0;gap:.9rem;margin:0 0 1.5rem;
  animation:lexIn .5s cubic-bezier(.22,1,.36,1) both;
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarAssistant"]){
  background:var(--paper-card);border:1px solid var(--rule);border-left:3px solid var(--accent);
  border-radius:2px 9px 9px 2px;padding:1.35rem 1.55rem;
  box-shadow:0 1px 0 rgba(23,27,36,.03),0 22px 44px -32px rgba(23,27,36,.55);
}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]){padding:.35rem 0 .1rem;}
[data-testid="stChatMessage"]:has([data-testid="stChatMessageAvatarUser"]) p{
  font-family:var(--display);font-size:1.16rem;font-weight:400;line-height:1.45;
  color:var(--ink);letter-spacing:-.012em;
}
/* Avatares: se oculta el icono nativo y se dibuja un glifo tipográfico. */
[data-testid="stChatMessageAvatarAssistant"],[data-testid="stChatMessageAvatarUser"]{
  border-radius:3px;flex-shrink:0;position:relative;
  font-family:var(--display)!important;font-size:1rem;line-height:1;
}
[data-testid="stChatMessageAvatarAssistant"] *,[data-testid="stChatMessageAvatarUser"] *{display:none!important;}
[data-testid="stChatMessageAvatarAssistant"]::after,[data-testid="stChatMessageAvatarUser"]::after{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
}
[data-testid="stChatMessageAvatarAssistant"]{background:var(--accent)!important;color:#FCFAF4!important;border:0!important;}
[data-testid="stChatMessageAvatarAssistant"]::after{content:"§";font-weight:500;}
[data-testid="stChatMessageAvatarUser"]{background:transparent!important;color:var(--ink-3)!important;border:1px solid var(--rule)!important;}
[data-testid="stChatMessageAvatarUser"]::after{content:"◆";font-size:.72rem;}

[data-testid="stChatMessage"] p{font-family:var(--serif);font-size:1.055rem;line-height:1.68;color:var(--ink-2);}
[data-testid="stChatMessage"] strong{color:var(--ink);font-weight:600;}
[data-testid="stChatMessage"] em{color:var(--ink-2);}
[data-testid="stChatMessage"] li{font-family:var(--serif);font-size:1.03rem;line-height:1.6;color:var(--ink-2);}
[data-testid="stChatMessage"] hr{border:0;border-top:1px solid var(--rule);margin:1.15rem 0 .85rem;}
[data-testid="stChatMessage"] blockquote{
  border-left:2px solid var(--ochre);background:rgba(181,138,52,.075);
  padding:.7rem 1rem;margin:.75rem 0;border-radius:0 4px 4px 0;
}
[data-testid="stChatMessage"] blockquote p{font-size:.99rem;color:var(--ink-2);}

/* ---------- controles ---------- */
[data-testid="stChatInput"]{
  background:var(--paper-card);border:1px solid var(--rule);border-radius:5px;
  box-shadow:0 24px 54px -38px rgba(23,27,36,.85);transition:border-color .2s,box-shadow .2s;
}
[data-testid="stChatInput"]:focus-within{border-color:var(--accent);box-shadow:0 0 0 3px rgba(160,48,51,.13);}
[data-testid="stChatInput"] textarea{font-family:var(--serif);font-size:1.03rem;color:var(--ink);}
[data-testid="stChatInput"] textarea::placeholder{color:var(--ink-3);font-style:italic;}

.stButton>button{
  font-family:var(--display);font-size:.86rem;font-weight:500;letter-spacing:.005em;
  background:transparent;color:var(--ink-2);border:1px solid var(--rule);border-radius:3px;
  padding:.5rem .95rem;text-align:left;transition:all .18s ease;
}
.stButton>button:hover{background:var(--ink);color:var(--paper);border-color:var(--ink);transform:translateY(-1px);}
.stButton>button:focus:not(:active){color:var(--paper);background:var(--ink);border-color:var(--ink);}

[data-testid="stSpinner"] p{font-family:var(--display);font-size:.8rem;letter-spacing:.1em;text-transform:uppercase;color:var(--ink-3);}
[data-testid="stSpinner"] svg{stroke:var(--accent);}

/* ---------- barra lateral (tinta) ---------- */
[data-testid="stSidebar"]{background:#12151C;border-right:1px solid rgba(0,0,0,.4);}
[data-testid="stSidebar"] .lex-side-t{
  font-family:var(--display);font-size:.66rem;font-weight:600;letter-spacing:.22em;
  text-transform:uppercase;color:var(--accent-2);margin:.4rem 0 1rem;
}
[data-testid="stSidebar"] p,[data-testid="stSidebar"] li{
  font-family:var(--serif);font-size:.95rem;line-height:1.62;color:#B9B3A4;
}
[data-testid="stSidebar"] strong{color:#EDE8DA;font-weight:600;}
[data-testid="stSidebar"] em{color:#8F8879;}
[data-testid="stSidebar"] code{background:rgba(255,255,255,.07);color:var(--ochre);padding:.08rem .32rem;border-radius:3px;font-size:.86em;}
[data-testid="stSidebar"] hr{border-top:1px solid rgba(255,255,255,.1);}
[data-testid="stSidebar"] .stButton>button{color:#B9B3A4;border-color:rgba(255,255,255,.16);}
[data-testid="stSidebar"] .stButton>button:hover{background:var(--accent);border-color:var(--accent);color:#FCFAF4;}

/* ---------- movimiento ---------- */
@keyframes lexUp{from{opacity:0;transform:translateY(14px);}to{opacity:1;transform:none;}}
@keyframes lexIn{from{opacity:0;transform:translateY(9px);}to{opacity:1;transform:none;}}
@keyframes lexWipe{from{transform:scaleX(0);opacity:0;}to{transform:scaleX(1);opacity:1;}}
@media (prefers-reduced-motion:reduce){*{animation:none!important;transition:none!important;}}
</style>
""".replace("__GRAIN__", _GRAIN)


# Preguntas de ejemplo: orientan a quien no sabe cómo formular su consulta.
SUGGESTIONS = [
    "¿Cuántos días de vacaciones me corresponden?",
    "¿Cuál es la jornada máxima de trabajo?",
    "¿Qué me deben pagar si me despiden?",
    "¿Qué dice el artículo 1?",
]


def header_html() -> str:
    """Cabecera editorial del chat."""
    return """
<div class="lex-head">
  <div class="lex-eyebrow">Asistente de consulta documental</div>
  <div class="lex-title">Derechos<br><em>Laborales</em></div>
  <div class="lex-rule"></div>
  <p class="lex-sub">Consultas sobre trabajo en Chile, respondidas a partir de la
  normativa cargada en el sistema. Cada respuesta indica <b>el documento, la
  página y el artículo</b> de donde proviene.</p>
</div>
"""


def strip_html(documentos: int, fragmentos: int, motor: str) -> str:
    """Banda con el estado de la base de datos y el motor activo."""
    return f"""
<div class="lex-strip">
  <div class="lex-stat"><span class="n">{documentos}</span><span class="l">Documentos</span></div>
  <div class="lex-stat"><span class="n">{fragmentos}</span><span class="l">Fragmentos</span></div>
  <div class="lex-stat engine"><span class="n">{motor}</span><span class="l">Motor</span></div>
</div>
"""


def warn_html(mensaje: str) -> str:
    """Aviso destacado (por ejemplo, base de datos vacía)."""
    return f'<p class="lex-warn">{mensaje}</p>'
