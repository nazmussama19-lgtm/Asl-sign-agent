"""Shared UI: visual identity, letter tiles, cached models and sign images."""
import os, glob, string, html
import json
import streamlit as st

# ---------------- Visual identity: "Arena", light ----------------
# Violet for what is done and for actions, cyan for "the letter being read right now",
# a sharp display face (Chakra Petch) for titles, tiles and scores, Manrope for reading.
INK = "#151833"
VIOLET = "#6B5BFF"
CYAN = "#12B8C4"
CYAN_INK = "#0A7780"
CYAN_TINT = "#E3F9FA"
PAPER = "#F5F6FB"
MIST = "#ECEEF8"
MUTED = "#636985"
LINE = "#E0E3F0"
DISPLAY = "'Chakra Petch', system-ui, sans-serif !important"


def inject_css():
    st.markdown(f'''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Chakra+Petch:wght@500;600;700&family=Manrope:wght@400;500;600;700&display=swap');
    .stApp *:not([data-testid="stIconMaterial"]):not(code):not(pre):not(pre *) {{
        font-family: 'Manrope', system-ui, sans-serif; }}
    h1, h2, h3, h4, h1 *, h2 *, h3 * {{ font-family: {DISPLAY}; color:{INK}; letter-spacing:-0.01em; }}
    #MainMenu, footer, [data-testid="stToolbar"] {{ visibility:hidden; }}
    [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {{ visibility:visible !important; }}
    .block-container {{ padding-top:2.4rem; padding-bottom:4rem; max-width:1120px; }}
    section[data-testid="stSidebar"] {{ background:#fff; border-right:1px solid {LINE}; }}
    section[data-testid="stSidebar"] h3 {{ font-size:1rem; }}
    a {{ color:{VIOLET}; }}
    .stButton > button, .stDownloadButton > button {{ border-radius:8px; font-weight:600; }}
    :focus-visible {{ outline:2px solid {VIOLET} !important; outline-offset:2px; }}
    .stMain [data-testid="stPageLink"] p {{ font-weight:600; color:{INK}; font-size:1.02rem; }}
    .stMain [data-testid="stPageLink"] [data-testid="stIconMaterial"] {{ color:{VIOLET}; }}
    [data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{ font-family:{DISPLAY}; font-weight:600; color:{INK}; }}

    /* page header */
    .stMarkdown h1.asl-title {{ font-size:2.4rem; line-height:1.1; font-weight:700; margin:0 0 .45rem 0; padding:0; color:{INK}; }}
    .asl-sub {{ color:{MUTED}; font-size:1.05rem; line-height:1.55; margin:0 0 1.8rem 0; max-width:62ch; }}
    .stMarkdown h2.asl-h2 {{ font-size:1.5rem; line-height:1.2; font-weight:700; color:{INK}; margin:2.6rem 0 .3rem 0; padding:0; }}
    .stMarkdown h3.asl-h3 {{ font-size:1.05rem; line-height:1.3; font-weight:600; color:{INK}; margin:0 0 .5rem 0; padding:0; }}

    /* letter tiles: done = violet, now = cyan, next = empty slot */
    .tiles {{ display:flex; flex-wrap:wrap; gap:.4rem; align-items:center; }}
    .tile {{ font-family:{DISPLAY}; font-weight:600; display:inline-flex; align-items:center; justify-content:center;
        border-radius:7px; width:2.6rem; height:3rem; font-size:1.4rem; background:#fff; color:#A3A8C3;
        border:1px solid {LINE}; }}
    .tiles.lg .tile {{ width:4.3rem; height:5rem; font-size:2.5rem; border-radius:10px; }}
    .tiles.sm .tile {{ width:1.9rem; height:2.25rem; font-size:1rem; border-radius:6px; }}
    .tile.done {{ background:{VIOLET}; border-color:{VIOLET}; color:#fff; }}
    .tile.now {{ background:{CYAN_TINT}; border:2px solid {CYAN}; color:{CYAN_INK}; }}
    .tile.gap {{ width:.8rem; border:none; background:transparent; }}
    .tile.word {{ width:auto; padding:0 .8rem; font-size:1rem; }}
    .tiles.sm .tile.word {{ font-size:.85rem; padding:0 .55rem; }}

    /* reading panels */
    .panel {{ background:#fff; border:1px solid {LINE}; border-radius:12px; padding:1.1rem 1.2rem; }}
    .panel-label {{ font-size:.9rem; font-weight:600; color:{MUTED}; margin:0 0 .45rem 0; }}
    .readout {{ font-family:{DISPLAY}; font-size:1.6rem; font-weight:600; color:{INK}; min-height:2.1rem; word-break:break-word; }}
    .readout.empty {{ color:#B3B8D0; font-weight:500; }}

    /* home */
    .hero {{ display:grid; grid-template-columns: minmax(0,1.15fr) minmax(0,1fr); gap:2.6rem;
        align-items:center; padding:1.2rem 0 2.2rem 0; border-bottom:1px solid {LINE}; }}
    .stMarkdown .hero h1 {{ font-size:3.2rem; padding:0; line-height:1.02; font-weight:700; margin:0 0 1rem 0; color:{INK}; }}
    .hero p {{ font-size:1.1rem; line-height:1.6; color:{MUTED}; margin:0; max-width:46ch; }}
    .demo-card {{ background:#fff; border:1px solid {LINE}; border-radius:16px; padding:1.5rem; }}
    .demo-step {{ font-size:.88rem; color:{MUTED}; margin:1.1rem 0 .45rem 0; }}
    .demo-step:first-child {{ margin-top:0; }}
    .bubble {{ background:{MIST}; border-radius:12px 12px 12px 4px; padding:.7rem 1rem; font-size:1.02rem;
        color:{INK}; display:inline-block; }}
    .steps {{ list-style:none; counter-reset:s; display:grid; grid-template-columns:repeat(3,minmax(0,1fr));
        gap:1.4rem 2rem; padding:0; margin:1rem 0 0 0; }}
    .steps li {{ counter-increment:s; position:relative; padding-left:2.5rem; color:{MUTED}; line-height:1.5; }}
    .steps li::before {{ content:counter(s); position:absolute; left:0; top:-.05rem; width:1.75rem; height:2rem;
        border-radius:6px; background:{MIST}; color:{VIOLET}; font-family:{DISPLAY}; font-weight:700;
        display:flex; align-items:center; justify-content:center; font-size:1rem; }}
    .steps b {{ color:{INK}; display:block; font-weight:600; }}
    .facts {{ display:grid; grid-template-columns:repeat(4,minmax(0,1fr)); gap:1rem; margin:1.8rem 0 0 0; }}
    .facts span {{ color:{MUTED}; font-size:.9rem; line-height:1.4; border-left:2px solid {VIOLET}; padding-left:.8rem; }}
    .facts b {{ display:block; font-family:{DISPLAY}; color:{INK}; font-size:1.7rem; font-weight:600; line-height:1.15; }}
    .chk {{ display:flex; gap:.75rem; padding:.55rem 0; }}
    .chk .dot {{ width:1.1rem; height:1.1rem; border-radius:4px; flex:0 0 1.1rem; margin-top:.2rem; }}
    .chk .ok {{ background:{VIOLET}; }}
    .chk .ko {{ border:2px solid #C3C7DA; }}
    .chk .t {{ font-weight:600; color:{INK}; }}
    .chk .d {{ color:{MUTED}; font-size:.92rem; }}

    /* practice */
    .score {{ display:flex; flex-wrap:wrap; gap:.6rem 2rem; margin:0 0 1.2rem 0; }}
    .score div {{ color:{MUTED}; font-size:.85rem; }}
    .score b {{ display:block; font-family:{DISPLAY}; color:{INK}; font-size:1.8rem; font-weight:600; line-height:1.1; }}
    .score div.hot b {{ color:{CYAN}; }}
    .feed {{ font-weight:600; min-height:1.6rem; margin-top:1rem; }}
    .feed.ok {{ color:#0E8A5F; }} .feed.err {{ color:#C0304A; }}
    .rate {{ display:flex; align-items:center; gap:.8rem; margin:.3rem 0; }}
    .rate .l {{ width:1.6rem; font-family:{DISPLAY}; font-weight:600; color:{INK}; }}
    .rate .bar {{ flex:1; background:{MIST}; border-radius:3px; height:.6rem; overflow:hidden; }}
    .rate .bar div {{ height:100%; background:{VIOLET}; }}
    .rate .n {{ width:8.5rem; color:{MUTED}; font-size:.85rem; }}

    /* text to sign */
    .stage {{ display:flex; flex-direction:column; align-items:center; justify-content:center; gap:.6rem;
        height:360px; margin-bottom:.8rem; }}
    .stage img {{ max-height:290px; max-width:100%; object-fit:contain; }}
    .stage .cap {{ color:{MUTED}; font-size:.95rem; }}

    /* chart */
    .sign-grid {{ display:grid; grid-template-columns:repeat(auto-fill, minmax(118px, 1fr)); gap:.8rem; }}
    .sign-card {{ background:#fff; border:1px solid {LINE}; border-radius:12px; padding:.7rem .6rem .55rem;
        display:flex; flex-direction:column; align-items:center; gap:.35rem; }}
    .sign-card img {{ height:118px; max-width:100%; object-fit:contain; }}
    .sign-card .row {{ display:flex; justify-content:space-between; align-items:center; width:100%; }}
    .sign-card .k {{ font-family:{DISPLAY}; font-weight:700; font-size:1.3rem; color:{INK}; }}
    .sign-card a {{ font-size:.85rem; }}
    .sign-card .face {{ height:118px; width:100%; display:flex; align-items:center; justify-content:center;
        border-radius:8px; background:{MIST}; font-family:{DISPLAY}; font-weight:700; font-size:1.35rem; color:{VIOLET}; }}
    .sign-grid.words {{ grid-template-columns:repeat(auto-fill, minmax(150px, 1fr)); }}
    .sign-face {{ height:220px; display:flex; align-items:center; justify-content:center; border-radius:12px;
        background:{MIST}; font-family:{DISPLAY}; font-weight:700; font-size:2rem; color:{VIOLET}; }}

    @media (max-width: 760px) {{
        .hero {{ grid-template-columns:1fr; gap:1.6rem; }}
        .stMarkdown .hero h1 {{ font-size:2.3rem; }}
        .steps {{ grid-template-columns:1fr; }}
        .facts {{ grid-template-columns:repeat(2,minmax(0,1fr)); }}
        .tiles.lg .tile {{ width:3.2rem; height:3.8rem; font-size:1.9rem; }}
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


def predict_one(model, x):
    """Probabilities for a single sample. Calling the model directly skips the batching machinery of
    model.predict(), which is several times slower for one frame at a time."""
    return model(x, training=False).numpy()[0]


# Webcam stream: 640x480 at 15 fps is plenty for hand landmarks and keeps the upload and the
# server-side processing light on a small cloud machine.
CAMERA = {"video": {"width": {"ideal": 640}, "height": {"ideal": 480},
                    "frameRate": {"ideal": 15, "max": 20}}, "audio": False}


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
