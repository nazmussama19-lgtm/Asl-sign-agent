"""Shared UI: visual identity, spelled-letter tiles, cached models and sign images."""
import os, glob, string, html
import json
import streamlit as st

# ---------------- Visual identity ----------------
# Deaf-awareness blue for actions, a highlighter yellow for "the letter being read right now",
# navy ink on cool paper. One typeface family designed for legibility (Braille Institute).
INK = "#10204A"
COBALT = "#2446E0"
SIGNAL = "#FFD23F"
PAPER = "#FAFBFD"
MIST = "#EEF2F8"
MUTED = "#56607A"
LINE = "#D5DCE8"

def inject_css():
    st.markdown(f'''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Atkinson+Hyperlegible+Mono:wght@500;700&family=Atkinson+Hyperlegible+Next:wght@400;500;700;800&display=swap');
    html, body, .stApp, .stMarkdown, .stButton button, label, input, textarea, select,
    [data-baseweb="select"], [data-testid="stMetricValue"], [data-testid="stCaptionContainer"] {{
        font-family: 'Atkinson Hyperlegible Next', system-ui, sans-serif; }}
    h1, h2, h3, h4 {{ font-family: 'Atkinson Hyperlegible Next', system-ui, sans-serif !important;
        color:{INK}; letter-spacing:-0.015em; }}
    #MainMenu, footer, [data-testid="stToolbar"] {{ visibility:hidden; }}
    [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{ visibility:visible !important; }}
    .block-container {{ padding-top:2.4rem; padding-bottom:4rem; max-width:1120px; }}
    section[data-testid="stSidebar"] {{ background:{MIST}; border-right:1px solid {LINE}; }}
    a {{ color:{COBALT}; }}
    .stButton > button {{ border-radius:10px; font-weight:700; }}
    :focus-visible {{ outline:3px solid {COBALT} !important; outline-offset:2px; }}

    /* page header */
    .stMarkdown h1.asl-title {{ font-size:2.35rem; line-height:1.1; font-weight:800; margin:0 0 .45rem 0; padding:0; color:{INK}; }}
    .asl-sub {{ color:{MUTED}; font-size:1.08rem; line-height:1.5; margin:0 0 1.8rem 0; max-width:62ch; }}
    .stMarkdown h2.asl-h2 {{ font-size:1.5rem; line-height:1.2; font-weight:800; color:{INK}; margin:2.6rem 0 .3rem 0; padding:0; }}
    .stMarkdown h3.asl-h3 {{ font-size:1.05rem; line-height:1.3; font-weight:700; color:{INK}; margin:0 0 .5rem 0; padding:0; }}

    /* spelled-letter tiles: the signature element, one tile per fingerspelled letter */
    .tiles {{ display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }}
    .tile {{ font-family:'Atkinson Hyperlegible Mono', ui-monospace, monospace; font-weight:700;
        display:inline-flex; align-items:center; justify-content:center; border-radius:8px;
        width:2.6rem; height:2.9rem; font-size:1.45rem; background:#fff; color:{INK};
        border:1.5px solid {LINE}; }}
    .tiles.lg .tile {{ width:4.4rem; height:5rem; font-size:2.7rem; border-radius:12px; border-width:2px; }}
    .tiles.sm .tile {{ width:1.9rem; height:2.2rem; font-size:1.05rem; border-radius:6px; }}
    .tile.done {{ background:{COBALT}; border-color:{COBALT}; color:#fff; }}
    .tile.now {{ background:{SIGNAL}; border-color:{INK}; color:{INK}; }}
    .tile.gap {{ width:.9rem; border:none; background:transparent; }}
    .tile.word {{ width:auto; padding:0 .8rem; font-size:1rem; }}
    .tiles.sm .tile.word {{ font-size:.85rem; padding:0 .55rem; }}

    /* reading panels */
    .panel {{ background:#fff; border:1.5px solid {LINE}; border-radius:12px; padding:1.1rem 1.2rem; }}
    .panel-label {{ font-size:.92rem; font-weight:700; color:{MUTED}; margin:0 0 .45rem 0; }}
    .readout {{ font-size:1.55rem; font-weight:700; color:{INK}; min-height:2.1rem; word-break:break-word; }}
    .readout.empty {{ color:#A7B0C4; font-weight:500; }}
    .engine {{ color:{MUTED}; font-size:.82rem; margin:-.35rem 0 .6rem 3.1rem; }}

    /* home */
    .hero {{ display:grid; grid-template-columns: minmax(0,1.15fr) minmax(0,1fr); gap:2.6rem;
        align-items:center; padding:1.2rem 0 2.2rem 0; border-bottom:1.5px solid {LINE}; }}
    .stMarkdown .hero h1 {{ font-size:3.1rem; padding:0; line-height:1.03; font-weight:800; margin:0 0 1rem 0; color:{INK}; }}
    .hero p {{ font-size:1.14rem; line-height:1.55; color:{MUTED}; margin:0; max-width:46ch; }}
    .demo-card {{ background:{MIST}; border-radius:16px; padding:1.5rem; }}
    .demo-step {{ font-size:.9rem; color:{MUTED}; margin:1rem 0 .4rem 0; }}
    .demo-step:first-child {{ margin-top:0; }}
    .bubble {{ background:#fff; border:1.5px solid {LINE}; border-radius:14px 14px 14px 4px;
        padding:.7rem 1rem; font-size:1.05rem; color:{INK}; display:inline-block; }}
    .steps {{ list-style:none; counter-reset:s; display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
        gap:1.4rem 2rem; padding:0; margin:1rem 0 0 0; }}
    .steps li {{ counter-increment:s; position:relative; padding-left:2.4rem; color:{MUTED}; line-height:1.45; }}
    .steps li::before {{ content:counter(s); position:absolute; left:0; top:-.1rem; width:1.7rem; height:1.9rem;
        border-radius:6px; background:{INK}; color:#fff; font-family:'Atkinson Hyperlegible Mono', monospace;
        font-weight:700; display:flex; align-items:center; justify-content:center; font-size:.95rem; }}
    .steps b {{ color:{INK}; display:block; }}
    .facts {{ display:flex; flex-wrap:wrap; gap:.5rem 2.2rem; margin:1.6rem 0 0 0; color:{MUTED}; }}
    .facts b {{ color:{INK}; font-size:1.25rem; margin-right:.3rem; }}
    .chk {{ display:flex; gap:.75rem; padding:.55rem 0; }}
    .chk .dot {{ width:1.25rem; height:1.25rem; border-radius:50%; flex:0 0 1.25rem; margin-top:.15rem; }}
    .chk .ok {{ background:{COBALT}; }}
    .chk .ko {{ border:2px solid #B4BDD0; }}
    .chk .t {{ font-weight:700; color:{INK}; }}
    .chk .d {{ color:{MUTED}; font-size:.92rem; }}

    /* practice */
    .score {{ display:flex; flex-wrap:wrap; gap:.6rem 2rem; margin:0 0 1.1rem 0; }}
    .score div {{ color:{MUTED}; font-size:.9rem; }}
    .score b {{ display:block; color:{INK}; font-size:1.7rem; line-height:1.15; }}
    .feed {{ font-weight:700; min-height:1.6rem; margin-top:.9rem; }}
    .feed.ok {{ color:#0F7B4F; }} .feed.err {{ color:#B42335; }}
    .rate {{ display:flex; align-items:center; gap:.8rem; margin:.25rem 0; }}
    .rate .l {{ width:1.6rem; font-family:'Atkinson Hyperlegible Mono', monospace; font-weight:700; color:{INK}; }}
    .rate .bar {{ flex:1; background:{MIST}; border-radius:4px; height:.7rem; overflow:hidden; }}
    .rate .bar div {{ height:100%; background:{COBALT}; }}
    .rate .n {{ width:8.5rem; color:{MUTED}; font-size:.85rem; }}

    .stage {{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.6rem;
        height:360px; margin-bottom:.8rem; }}
    .stage img {{ max-height:290px; max-width:100%; object-fit:contain; }}
    .stage .cap {{ color:{MUTED}; font-size:.95rem; }}
    [data-testid="stMetricValue"] {{ font-weight:800; color:{INK}; }}

    /* chart */
    .sign-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(118px, 1fr)); gap:.8rem; }}
    .sign-card {{ background:#fff; border:1.5px solid {LINE}; border-radius:12px; padding:.7rem .6rem .55rem;
        display:flex; flex-direction:column; align-items:center; gap:.35rem; }}
    .sign-card img {{ height:118px; max-width:100%; object-fit:contain; }}
    .sign-card .row {{ display:flex; justify-content:space-between; align-items:center; width:100%; }}
    .sign-card .k {{ font-family:'Atkinson Hyperlegible Mono', monospace; font-weight:700; font-size:1.25rem; color:{INK}; }}
    .sign-card a {{ font-size:.85rem; }}

    @media (max-width: 760px) {{
        .hero {{ grid-template-columns:1fr; gap:1.6rem; }}
        .stMarkdown .hero h1 {{ font-size:2.2rem; }}
        .steps {{ grid-template-columns:1fr; }}
        .tiles.lg .tile {{ width:3.2rem; height:3.7rem; font-size:2rem; }}
    }}
    </style>
    ''', unsafe_allow_html=True)


def app_header(title, subtitle):
    st.markdown(f'<h1 class="asl-title">{html.escape(title)}</h1><p class="asl-sub">{subtitle}</p>',
                unsafe_allow_html=True)


def section(title, subtitle=""):
    sub = f'<p class="asl-sub" style="margin-bottom:1.2rem">{subtitle}</p>' if subtitle else ""
    st.markdown(f'<h2 class="asl-h2">{html.escape(title)}</h2>{sub}', unsafe_allow_html=True)


def tiles_html(text, done=0, now=None, size=""):
    """Render text as fingerspelling tiles. `done` letters are filled blue, index `now` is highlighted."""
    out, idx = [], 0
    for ch in text:
        if ch == " ":
            out.append('<span class="tile gap"></span>')
            continue
        cls = "done" if idx < done else ("now" if idx == now else "")
        out.append(f'<span class="tile {cls}">{html.escape(ch)}</span>')
        idx += 1
    return f'<div class="tiles {size}">' + "".join(out) + "</div>"


# ---------------- Webcam connection ----------------
def rtc_config():
    """STUN always; TURN relay when configured (needed behind strict firewalls / mobile networks)."""
    from conversation import setting
    servers = [{"urls": ["stun:stun.l.google.com:19302"]}]
    urls, user, cred = setting("TURN_URLS"), setting("TURN_USERNAME"), setting("TURN_CREDENTIAL")
    if urls and user and cred:
        servers.append({"urls": [u.strip() for u in urls.split(",") if u.strip()],
                        "username": user, "credential": cred})
    return {"iceServers": servers}


def camera_help():
    from conversation import setting
    with st.expander("Camera not starting?"):
        st.markdown(
            "- Click **Start**, then allow camera access when your browser asks. If you blocked it, "
            "use the camera icon in the address bar to allow it and reload the page.\n"
            "- Close other apps that use the camera (video calls, OBS...).\n"
            "- If the video stays black on a work or mobile network, the connection needs a relay server.")
        if not setting("TURN_URLS"):
            st.caption("No relay (TURN) server is configured for this deployment yet: see the README, "
                       "section Deployment.")


# ---------------- Models ----------------
@st.cache_resource(show_spinner=False)
def get_model():
    import tensorflow as tf
    return tf.keras.models.load_model("asl_mediapipe_mlp_model.h5")


@st.cache_data(show_spinner=False)
def get_labels():
    with open("labels.json") as f:
        return json.load(f)


# ---------------- Sign images ----------------
# Public-domain line drawings of the ASL alphabet (Wikimedia Commons, wpclipart.com).
# Used when neither assets/alphabet/ nor the Kaggle photo dataset is present, e.g. on Streamlit Cloud.
COMMONS = "https://commons.wikimedia.org/wiki/Special:FilePath/Sign_language_{}.svg?width=300"

DATASET_CANDIDATES = [
    "../../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
    "../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
    "Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
    "../../Asl_Sign_Data", "../Asl_Sign_Data", "Asl_Sign_Data",
]


def _dataset_base():
    for base in DATASET_CANDIDATES:
        if os.path.isdir(os.path.join(base, "A")):
            return base
    return None


@st.cache_data(show_spinner=False)
def find_alphabet_images():
    """{letter: image path or URL}. Order: assets/alphabet, then the Kaggle dataset, then Wikimedia."""
    letters = list(string.ascii_uppercase)
    if os.path.isdir("assets/alphabet"):
        m = {}
        for L in letters:
            for ext in ("jpg", "jpeg", "png", "svg"):
                p = os.path.join("assets/alphabet", L + "." + ext)
                if os.path.exists(p):
                    m[L] = p
                    break
        if len(m) >= 20:
            return m
    base = _dataset_base()
    if base:
        m = {}
        for L in letters:
            imgs = glob.glob(os.path.join(base, L, "*.jpg")) + glob.glob(os.path.join(base, L, "*.png"))
            if imgs:
                m[L] = sorted(imgs)[0]
        if len(m) >= 20:
            return m
    return {L: COMMONS.format(L) for L in letters}


@st.cache_data(show_spinner=False)
def img_src(path):
    """Usable <img src>: URLs as they are, local files inlined as data URIs."""
    p = str(path)
    if p.startswith("http"):
        return p
    import base64, mimetypes
    mime = mimetypes.guess_type(p)[0] or "image/png"
    with open(p, "rb") as f:
        return "data:" + mime + ";base64," + base64.b64encode(f.read()).decode()


def uses_remote_images():
    return any(str(p).startswith("http") for p in find_alphabet_images().values())


@st.cache_data(show_spinner=False)
def find_sign_images():
    """Letters A-Z plus the two special signs (SPACE, DELETE) when the photo dataset provides them."""
    out = dict(find_alphabet_images())
    base = _dataset_base()
    if base:
        for folder, label in {"space": "SPACE", "del": "DELETE"}.items():
            d = os.path.join(base, folder)
            imgs = glob.glob(os.path.join(d, "*.jpg")) + glob.glob(os.path.join(d, "*.png"))
            if imgs:
                out[label] = sorted(imgs)[0]
    return out


@st.cache_resource(show_spinner="Picking and enhancing the best sign photos (once, about a minute)...")
def get_best_photos():
    """Best real photos from the dataset, enhanced (light, contrast, framing).
    Returns {letter: path} + SPACE / DELETE. Empty when the dataset is absent."""
    out_dir = "assets/best_signs"
    have = len([f for f in os.listdir(out_dir) if f.endswith(".png")]) if os.path.isdir(out_dir) else 0
    if have < 26:
        base = _dataset_base()
        if base is None:
            return {}
        from sign_photos import generate_best_photos
        generate_best_photos(base, out_dir)
    mapping = {}
    for f in os.listdir(out_dir):
        if not f.endswith(".png"):
            continue
        name = f[:-4]
        if name == "space":
            mapping["SPACE"] = os.path.join(out_dir, f)
        elif name == "del":
            mapping["DELETE"] = os.path.join(out_dir, f)
        elif len(name) == 1:
            mapping[name.upper()] = os.path.join(out_dir, f)
    return mapping


@st.cache_data(show_spinner=False)
def get_word_sign_gifs():
    """Animated word-sign GIFs (generated by make_word_previews.py). {sign: path}."""
    d = "assets/word_signs_gifs"
    if not os.path.isdir(d):
        return {}
    return {f[:-4]: os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".gif")}


@st.cache_data(show_spinner=False)
def word_sign_labels():
    """Word signs the bundled recognition model knows."""
    try:
        with open("sign_words_labels.json") as f:
            return json.load(f)
    except Exception:
        return []
