import streamlit as st

st.set_page_config(page_title="ASL Sign Agent", page_icon="🤟", layout="wide")

home     = st.Page("views/home.py", title="Home", icon=":material/home:", default=True)
s2t      = st.Page("views/sign_to_text.py", title="Sign to Text", icon=":material/front_hand:")
practice = st.Page("views/practice_mode.py", title="Practice", icon=":material/sports_score:")
t2s      = st.Page("views/text_to_sign.py", title="Text to Sign", icon=":material/keyboard:")
chart    = st.Page("views/chart.py", title="ASL Chart", icon=":material/sort_by_alpha:")
results  = st.Page("views/results.py", title="Results", icon=":material/monitoring:")

nav = st.navigation([home, s2t, practice, t2s, chart, results])
nav.run()
