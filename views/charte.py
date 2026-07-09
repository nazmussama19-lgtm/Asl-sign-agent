import string
import streamlit as st
from ui import inject_css, app_header, find_alphabet_images, get_word_sign_gifs

inject_css()
app_header("Charte de l'alphabet ASL", "Les 26 signes de l'alphabet americain (dactylologie).")

imgs = find_alphabet_images()
if not imgs:
    st.warning("Images introuvables. Place le dossier Asl_Sign_Data a cote du projet, "
               "ou depose 26 images (A.jpg ... Z.jpg) dans asl_app/assets/alphabet/.")
    st.stop()

letters = list(string.ascii_uppercase)
per_row = 6
for i in range(0, 26, per_row):
    cols = st.columns(per_row)
    for col, L in zip(cols, letters[i:i+per_row]):
        with col:
            if L in imgs:
                st.image(imgs[L], caption=L, use_container_width=True)
                st.markdown('<div style="text-align:center;margin-top:-0.6rem;">'
                            '<a href="https://www.signasl.org/sign/' + L.lower() + '" target="_blank" '
                            'style="font-size:.78rem;color:#5B4BE6;">Video \u2197</a></div>',
                            unsafe_allow_html=True)
            else:
                st.markdown("**" + L + "** (manquante)")

st.caption("Images tirees de ton propre jeu de donnees. J et Z sont montres par une pose representative.")

gifs = get_word_sign_gifs()
if gifs:
    st.markdown("---")
    st.markdown('<div class="asl-header"><span class="bar"></span><h2>Signes-mots</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="asl-sub">Animations generees depuis les landmarks du dataset Google ASL Signs : reproduis le mouvement.</div>', unsafe_allow_html=True)
    names = sorted(gifs)
    per_row = 4
    from word_signs import sign_video_url
    for i in range(0, len(names), per_row):
        cols = st.columns(per_row)
        for col, name in zip(cols, names[i:i + per_row]):
            with col:
                st.image(gifs[name], caption=name.upper(), use_container_width=True)
                st.markdown('<div style="text-align:center;margin-top:-0.6rem;">'
                            '<a href="' + sign_video_url(name) + '" target="_blank" '
                            'style="font-size:.82rem;color:#5B4BE6;">Video reelle \u2197</a></div>',
                            unsafe_allow_html=True)
    st.caption("\u00ab Video reelle \u00bb ouvre le dictionnaire SignASL.org : plusieurs personnes "
               "signent chaque mot en video. (Contenus proteges : lies, non embarques.)")
