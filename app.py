import streamlit as st

st.set_page_config(page_title="ASL Translator", page_icon="🤟", layout="wide")

accueil  = st.Page("views/accueil.py", title="Accueil", icon="🏠", default=True)
s2t      = st.Page("views/sign_to_text.py", title="Sign to Text", icon="✋")
practice = st.Page("views/entrainement.py", title="Entrainement", icon="🎮")
t2s      = st.Page("views/text_to_sign.py", title="Text to Sign", icon="⌨️")
charte   = st.Page("views/charte.py", title="Charte ASL", icon="🔤")
res      = st.Page("views/resultats.py", title="Resultats", icon="📊")

nav = st.navigation([accueil, s2t, practice, t2s, charte, res])
nav.run()
