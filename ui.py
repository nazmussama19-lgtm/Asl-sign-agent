import os, glob, string
import json
import streamlit as st

def inject_css():
    st.markdown('''
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@500;600;700&family=Inter:wght@400;500;600;700&display=swap');
    html, body, [class*="css"] { font-family: 'Inter', sans-serif; }
    h1, h2, h3, .asl-hero h1, .asl-header h2 { font-family: 'Space Grotesk', sans-serif; letter-spacing:-0.01em; }
    #MainMenu {visibility:hidden;} footer {visibility:hidden;}
    [data-testid="stToolbar"] {visibility:hidden;}
    /* bouton pour rouvrir le menu, bien visible */
    [data-testid="stSidebarCollapsedControl"], [data-testid="collapsedControl"] {
        visibility:visible !important; color:#14152B !important;
        background:#F2F3FB !important; border-radius:8px; padding:2px;
    }
    [data-testid="stSidebarCollapsedControl"] svg, [data-testid="collapsedControl"] svg { fill:#14152B !important; }
    .block-container { padding-top:2.2rem; padding-bottom:3rem; max-width:1120px; }
    section[data-testid="stSidebar"] { background:#14152B; }
    section[data-testid="stSidebar"] * { color:#D9DBEC !important; }
    .asl-hero { background: linear-gradient(120deg, #5B4BE6 0%, #6D5CF0 45%, #06B6D4 100%);
        border-radius:24px; padding:3.2rem 2.6rem; color:#fff; margin-bottom:1.6rem;
        box-shadow:0 22px 48px rgba(91,75,230,0.28); }
    .asl-hero h1 { font-size:2.7rem; font-weight:700; margin:.2rem 0 .5rem 0; color:#fff; }
    .asl-hero p { font-size:1.12rem; line-height:1.55; opacity:.96; margin:0; max-width:660px; }
    .asl-badge { display:inline-flex; align-items:center; gap:.5rem; background:rgba(255,255,255,.16);
        padding:.35rem .85rem; border-radius:999px; font-size:.82rem; font-weight:600; margin-bottom:1.1rem; }
    @keyframes asl-pulse { 0%{box-shadow:0 0 0 0 rgba(34,245,160,.6)} 70%{box-shadow:0 0 0 12px rgba(34,245,160,0)} 100%{box-shadow:0 0 0 0 rgba(34,245,160,0)} }
    .live-dot { width:10px; height:10px; border-radius:50%; background:#22F5A0; display:inline-block; animation:asl-pulse 1.8s infinite; }
    @media (prefers-reduced-motion: reduce){ .live-dot{ animation:none } }
    .asl-card { background:#fff; border:1px solid #ECECF5; border-radius:18px; padding:1.6rem;
        box-shadow:0 6px 20px rgba(20,21,43,0.05); height:100%; }
    .asl-card .ico { font-size:1.9rem; }
    .asl-card h3 { margin:.5rem 0 .4rem 0; font-size:1.15rem; font-weight:700; color:#14152B; }
    .asl-card p { color:#5B6270; font-size:.95rem; margin:0; line-height:1.5; }
    .asl-header { display:flex; align-items:center; gap:.7rem; margin-bottom:.2rem; }
    .asl-header .bar { width:6px; height:30px; border-radius:6px; background:linear-gradient(#5B4BE6,#06B6D4); }
    .asl-header h2 { margin:0; font-size:1.8rem; font-weight:700; color:#14152B; }
    .asl-sub { color:#6B7280; margin:.15rem 0 1.5rem 1.3rem; font-size:1rem; }
    .asl-label { font-size:.78rem; font-weight:700; text-transform:uppercase; letter-spacing:.05em; color:#8A90A8; margin-bottom:.5rem; }
    .asl-panel { background:#F7F8FD; border:1px solid #ECECF5; border-radius:16px; padding:1.3rem; }
    .asl-out { font-size:1.5rem; font-weight:600; color:#14152B; min-height:2rem; word-break:break-word; }
    .stButton>button { border-radius:11px; font-weight:600; border:1px solid #E4E4EF;
        transition: transform .12s ease, box-shadow .12s ease; }
    .stButton>button:hover { transform: translateY(-1px); box-shadow:0 6px 16px rgba(91,75,230,.18); }
    a { color:#5B4BE6; }

    .asl-card { transition: transform .15s ease, box-shadow .15s ease; }
    .asl-card:hover { transform: translateY(-3px); box-shadow:0 14px 30px rgba(20,21,43,0.10); }

    /* pipeline (accueil) */
    .pipe { display:flex; flex-wrap:wrap; align-items:center; gap:.45rem; justify-content:center;
        background:#14152B; border-radius:18px; padding:1.1rem 1rem; }
    .pipe .step { background:rgba(255,255,255,.07); border:1px solid rgba(255,255,255,.12);
        color:#E7E9F7; border-radius:999px; padding:.42rem .95rem; font-size:.88rem; font-weight:600;
        font-family:'Space Grotesk',sans-serif; white-space:nowrap; }
    .pipe .step b { background:linear-gradient(120deg,#8B7CFF,#22D3EE);
        -webkit-background-clip:text; background-clip:text; color:transparent; }
    .pipe .arr { color:#5B6280; font-weight:700; }

    /* chiffres cles (accueil) */
    .stats { display:flex; flex-wrap:wrap; gap:1rem; justify-content:space-between; margin:.4rem 0 .2rem 0; }
    .stat { flex:1; min-width:150px; background:#fff; border:1px solid #ECECF5; border-radius:16px;
        padding:1rem 1.2rem; text-align:center; }
    .stat .n { font-family:'Space Grotesk',sans-serif; font-size:1.7rem; font-weight:700;
        background:linear-gradient(120deg,#5B4BE6,#06B6D4); -webkit-background-clip:text;
        background-clip:text; color:transparent; }
    .stat .l { color:#6B7280; font-size:.82rem; }

    /* checklist demarrage (accueil) */
    .chk { display:flex; align-items:flex-start; gap:.7rem; padding:.5rem .2rem; }
    .chk .dot { width:22px; height:22px; border-radius:50%; flex:0 0 22px; display:flex;
        align-items:center; justify-content:center; font-size:.8rem; font-weight:800; margin-top:.1rem; }
    .chk .ok { background:#E7FBF2; color:#0E9F6E; border:1.5px solid #9AE6C6; }
    .chk .ko { background:#F4F5FB; color:#8A90A8; border:1.5px dashed #C9CCE0; }
    .chk .t { font-weight:600; color:#14152B; }
    .chk .d { color:#6B7280; font-size:.86rem; }
    </style>
    ''', unsafe_allow_html=True)

def app_header(title, subtitle):
    st.markdown(f'<div class="asl-header"><span class="bar"></span><h2>{title}</h2></div>', unsafe_allow_html=True)
    st.markdown(f'<div class="asl-sub">{subtitle}</div>', unsafe_allow_html=True)

@st.cache_resource(show_spinner=False)
def get_model():
    import tensorflow as tf
    return tf.keras.models.load_model("asl_mediapipe_mlp_model.h5")

@st.cache_data(show_spinner=False)
def get_labels():
    with open("labels.json") as f:
        return json.load(f)

@st.cache_data(show_spinner=False)
def find_alphabet_images():
    # Retourne {lettre: chemin_image}. Cherche d'abord assets/alphabet, puis le dataset Kaggle.
    letters = list(string.ascii_uppercase)
    if os.path.isdir("assets/alphabet"):
        m = {}
        for L in letters:
            for ext in ("jpg", "jpeg", "png"):
                p = os.path.join("assets/alphabet", L + "." + ext)
                if os.path.exists(p):
                    m[L] = p; break
        if len(m) >= 20:
            return m
    candidates = [
        "../../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "../../Asl_Sign_Data", "../Asl_Sign_Data", "Asl_Sign_Data",
    ]
    for base in candidates:
        if os.path.isdir(os.path.join(base, "A")):
            m = {}
            for L in letters:
                imgs = glob.glob(os.path.join(base, L, "*.jpg")) + glob.glob(os.path.join(base, L, "*.png"))
                if imgs:
                    m[L] = sorted(imgs)[0]
            if len(m) >= 20:
                return m
    return {}


@st.cache_data(show_spinner=False)
def find_sign_images():
    # Lettres A-Z + signes speciaux (espace, suppression) depuis le dataset ou assets/alphabet.
    base_map = find_alphabet_images()
    out = {}
    for L in sorted(base_map):
        out[L] = base_map[L]
    candidates = [
        "../../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "../../Asl_Sign_Data", "../Asl_Sign_Data", "Asl_Sign_Data",
    ]
    specials = {"space": "ESPACE", "del": "SUPPRIMER"}
    for basedir in candidates:
        if os.path.isdir(os.path.join(basedir, "A")):
            for folder, label in specials.items():
                d = os.path.join(basedir, folder)
                if os.path.isdir(d):
                    imgs = glob.glob(os.path.join(d, "*.jpg")) + glob.glob(os.path.join(d, "*.png"))
                    if imgs:
                        out[label] = sorted(imgs)[0]
            break
    return out


def _dataset_base():
    candidates = [
        "../../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "../Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "Asl_Sign_Data/asl_alphabet_train/asl_alphabet_train",
        "../../Asl_Sign_Data", "../Asl_Sign_Data", "Asl_Sign_Data",
    ]
    for base in candidates:
        if os.path.isdir(os.path.join(base, "A")):
            return base
    return None

@st.cache_resource(show_spinner="Selection et amelioration des meilleures photos de signes (une seule fois, ~1 min)...")
def get_best_photos():
    """Meilleures VRAIES photos du dataset, ameliorees (lumiere, contraste, cadrage).
    Retourne {lettre: chemin} + ESPACE / SUPPRIMER. Vide si le dataset est absent."""
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
            mapping["ESPACE"] = os.path.join(out_dir, f)
        elif name == "del":
            mapping["SUPPRIMER"] = os.path.join(out_dir, f)
        elif len(name) == 1:
            mapping[name.upper()] = os.path.join(out_dir, f)
    return mapping


@st.cache_data(show_spinner=False)
def get_word_sign_gifs():
    """GIFs animes des signes-mots (generes par make_word_previews.py). {signe: chemin}."""
    d = "assets/word_signs_gifs"
    if not os.path.isdir(d):
        return {}
    return {f[:-4]: os.path.join(d, f) for f in sorted(os.listdir(d)) if f.endswith(".gif")}
