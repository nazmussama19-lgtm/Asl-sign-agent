import os
import streamlit as st
from ui import inject_css, get_word_sign_gifs, _dataset_base

inject_css()

# ---------------- Hero ----------------
st.markdown('''
<div class="asl-hero">
  <div class="asl-badge"><span class="live-dot"></span> Temps reel &nbsp;\u00b7&nbsp; 100% local &nbsp;\u00b7&nbsp; gratuit</div>
  <h1>Un agent IA qui lit la langue des signes</h1>
  <p>Signe devant ta webcam : l\'application reconnait l\'alphabet ASL et des signes-mots,
  reconstruit tes phrases, te repond et parle \u2014 sans qu\'aucune image ne quitte ta machine.</p>
</div>
''', unsafe_allow_html=True)

# ---------------- Pipeline ----------------
st.markdown('''
<div class="pipe">
  <span class="step">\U0001F4F7 Camera</span><span class="arr">\u2192</span>
  <span class="step">\u270B <b>21 points</b> MediaPipe</span><span class="arr">\u2192</span>
  <span class="step">\U0001F9E0 Lettres <b>&amp;</b> signes-mots</span><span class="arr">\u2192</span>
  <span class="step">\U0001F916 <b>Agent</b> : segmente, corrige</span><span class="arr">\u2192</span>
  <span class="step">\U0001F4AC Conversation</span><span class="arr">\u2192</span>
  <span class="step">\U0001F50A Voix</span>
</div>
''', unsafe_allow_html=True)

# ---------------- Chiffres cles ----------------
n_words = len(get_word_sign_gifs())
st.markdown(f'''
<div class="stats">
  <div class="stat"><div class="n">28</div><div class="l">signes statiques (A\u2013Z, espace, suppression)</div></div>
  <div class="stat"><div class="n">{n_words if n_words else 24}</div><div class="l">signes-mots (dataset Google ASL Signs)</div></div>
  <div class="stat"><div class="n">23\u202f000</div><div class="l">mots FR + EN dans la memoire de l\'agent</div></div>
  <div class="stat"><div class="n">0\u20ac</div><div class="l">aucune API payante, tout tourne en local</div></div>
</div>
''', unsafe_allow_html=True)

st.markdown("")

# ---------------- Cartes des fonctionnalites ----------------
def card(icon, title, text):
    st.markdown(f'''<div class="asl-card"><div class="ico">{icon}</div>
    <h3>{title}</h3><p>{text}</p></div>''', unsafe_allow_html=True)

r1 = st.columns(3)
with r1[0]:
    card("\u270B", "Sign to Text",
         "Epelle ou signe des mots entiers : l\'agent construit la phrase, l\'interprete tout seul apres une pause, repond et la lit a voix haute.")
    st.page_link("views/sign_to_text.py", label="Ouvrir la demo", icon="\u27A1\uFE0F")
with r1[1]:
    card("\U0001F3AE", "Entrainement",
         "Defis gamifies, score et series, mode adaptatif qui cible tes lettres faibles, et statistiques personnelles persistantes.")
    st.page_link("views/entrainement.py", label="S\'entrainer", icon="\u27A1\uFE0F")
with r1[2]:
    card("\u2328\uFE0F", "Text to Sign",
         "Tape une phrase (FR ou EN) : signes-mots animes quand ils existent, epellation sinon \u2014 avec export GIF a partager.")
    st.page_link("views/text_to_sign.py", label="Traduire", icon="\u27A1\uFE0F")

r2 = st.columns(3)
with r2[0]:
    card("\U0001F9E9", "Personnalisation",
         "Cree tes propres signes en 3 gestes, et corrige les lettres qui marchent mal chez toi avec 5 exemples \u2014 sans reentrainement.")
    st.page_link("views/sign_to_text.py", label="Personnaliser (dans la demo)", icon="\u27A1\uFE0F")
with r2[1]:
    card("\U0001F524", "Charte ASL",
         "Les 26 lettres en photos reelles, les signes-mots en animations, et des liens vers de vraies personnes qui signent.")
    st.page_link("views/charte.py", label="Apprendre les signes", icon="\u27A1\uFE0F")
with r2[2]:
    card("\U0001F4CA", "Resultats",
         "Precision, matrice de confusion et F1 par lettre, calcules en direct depuis le modele \u2014 avec une lecture critique honnete.")
    st.page_link("views/resultats.py", label="Voir les metriques", icon="\u27A1\uFE0F")

# ---------------- Demarrage : etat de l\'installation ----------------
st.markdown("---")
st.markdown('<div class="asl-header"><span class="bar"></span><h2>Demarrage</h2></div>', unsafe_allow_html=True)
st.markdown('<div class="asl-sub">Etat de ton installation \u2014 tout est optionnel sauf le premier point.</div>', unsafe_allow_html=True)

def check(ok, title, ok_msg, ko_msg):
    dot = '<div class="dot ok">\u2713</div>' if ok else '<div class="dot ko">\u25CB</div>'
    msg = ok_msg if ok else ko_msg
    st.markdown(f'<div class="chk">{dot}<div><div class="t">{title}</div><div class="d">{msg}</div></div></div>',
                unsafe_allow_html=True)

c1, c2 = st.columns(2, gap="large")
with c1:
    check(os.path.exists("asl_mediapipe_mlp_model.h5") and os.path.exists("labels.json"),
          "Modele de lettres",
          "Pret : la reconnaissance de l\'alphabet fonctionne.",
          "Copie asl_mediapipe_mlp_model.h5 et labels.json ici (voir README).")
    check(_dataset_base() is not None,
          "Dataset d\'images (Asl_Sign_Data)",
          "Trouve : Charte, Text to Sign et photos ameliorees disponibles.",
          "Place le dossier Asl_Sign_Data a cote du projet pour les images.")
    check(os.path.exists("sign_words_model.h5"),
          "Modele de signes-mots",
          "Pret : active la case Signes-mots dans la demo.",
          "Lance download_signs_dataset.py puis le notebook 03 (voir README).")
with c2:
    check(len(get_word_sign_gifs()) > 0,
          "Animations des signes-mots",
          "Pretes : visibles dans la Charte et Text to Sign.",
          "Apres le telechargement, lance : python make_word_previews.py")
    try:
        from conversation import ollama_model
        _oll = ollama_model()
    except Exception:
        _oll = None
    check(_oll is not None,
          "Ollama (conversation avancee)",
          f"Detecte ({_oll}) : l\'agent l\'utilise automatiquement.",
          "Optionnel : installe Ollama + un modele pour des reponses plus riches (sinon, regles locales).")
    check(True, "Confidentialite",
          "Toutes les images et donnees restent sur cette machine. Aucune API payante.",
          "")

st.caption("Projet de M2 \u2014 reconnaissance d\'epellation ASL et signes-mots. L\'epellation est un "
           "sous-ensemble de la langue des signes : ce projet n\'en traduit pas la grammaire complete.")
