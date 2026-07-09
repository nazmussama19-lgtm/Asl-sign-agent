import os, time
import numpy as np
import streamlit as st
from ui import inject_css, app_header, get_model, get_labels
from asl_core import normalize_landmarks
from practice import PracticeEngine, pick_word, load_stats, reset_stats, LETTERS

inject_css()

# ---------- Style dedie (plus audacieux) ----------
st.markdown("""
<style>
.pr-arena { border-radius: 22px; padding: 1.6rem 1.8rem; margin-bottom: 1rem;
  border: 2px solid transparent;
  background: linear-gradient(#14152B,#14152B) padding-box,
              linear-gradient(120deg,#5B4BE6,#06B6D4) border-box;
  box-shadow: 0 18px 44px rgba(20,21,43,.35); }
.pr-chips { display:flex; gap: 1.6rem; flex-wrap: wrap; margin-bottom: 1rem; }
.pr-chip .lab { font-size:.68rem; letter-spacing:.09em; text-transform:uppercase; color:#8A90A8; }
.pr-chip .val { font-family:'Space Grotesk',sans-serif; font-size:1.9rem; font-weight:700; color:#fff; line-height:1.1; }
.pr-chip .val.accent { background: linear-gradient(120deg,#8B7CFF,#22D3EE);
  -webkit-background-clip:text; background-clip:text; color:transparent; }
.pr-tiles { display:flex; gap:.55rem; flex-wrap:wrap; margin:.4rem 0 .6rem 0; }
.pr-tile { width:58px; height:58px; border-radius:14px; display:flex; align-items:center; justify-content:center;
  font-family:'Space Grotesk',sans-serif; font-size:1.7rem; font-weight:700; }
.pr-done { background: linear-gradient(135deg,#5B4BE6,#06B6D4); color:#fff;
  box-shadow: 0 6px 16px rgba(6,182,212,.35); }
.pr-cur { background:#fff; color:#14152B; animation: prpulse 1.4s infinite; }
.pr-next { background:transparent; border:2px solid #2A2C4A; color:#8A90A8; }
@keyframes prpulse { 0%{box-shadow:0 0 0 0 rgba(34,211,238,.55)} 70%{box-shadow:0 0 0 14px rgba(34,211,238,0)} 100%{box-shadow:0 0 0 0 rgba(34,211,238,0)} }
@media (prefers-reduced-motion: reduce){ .pr-cur{ animation:none } }
.pr-feed { font-family:'Space Grotesk',sans-serif; font-weight:700; font-size:1.05rem; min-height:1.6rem; }
.pr-ok { color:#22F5A0; } .pr-err { color:#FF7B8A; }
.pr-bar { background:#ECECF5; border-radius:8px; height:12px; overflow:hidden; }
.pr-bar > div { height:100%; background: linear-gradient(90deg,#5B4BE6,#06B6D4); }
</style>
""", unsafe_allow_html=True)

app_header("Entrainement", "Des defis gamifies, un suivi de tes lettres faibles, et une collecte locale pour personnaliser le modele.")

if not (os.path.exists("asl_mediapipe_mlp_model.h5") and os.path.exists("labels.json")):
    st.error("Modele introuvable. Copie asl_mediapipe_mlp_model.h5 et labels.json dans le dossier de l'app.")
    st.stop()
try:
    import cv2, mediapipe as mp, av
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
except Exception:
    st.warning("Dependances webcam manquantes (pip install -r requirements_app.txt).")
    st.stop()

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
FONT = cv2.FONT_HERSHEY_SIMPLEX

def put_label(img, text, org, scale=0.8, color=(255,255,255), thick=2, bg=(0,0,0)):
    (tw, th), base = cv2.getTextSize(text, FONT, scale, thick)
    x, y = org
    cv2.rectangle(img, (x-6, y-th-8), (x+tw+6, y+base+4), bg, -1)
    cv2.putText(img, text, (x, y), FONT, scale, color, thick, cv2.LINE_AA)

class PracticeProcessor(VideoProcessorBase):
    def __init__(self):
        self.model = get_model()
        self.labels = get_labels()
        self.hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=1)
        self.engine = PracticeEngine()

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        res = self.hands.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
        label, conf, feats = "nothing", 0.0, None
        if res.multi_hand_landmarks:
            hl = res.multi_hand_landmarks[0]
            mp_draw.draw_landmarks(img, hl, mp_hands.HAND_CONNECTIONS)
            coords = np.array([[p.x, p.y, p.z] for p in hl.landmark], dtype=np.float32)
            feats = normalize_landmarks(coords)
            pred = self.model.predict(feats.reshape(1, -1), verbose=0)[0]
            i = int(np.argmax(pred)); conf = float(pred[i]); label = self.labels[i]
        self.engine.update(label, conf, feats)

        s = self.engine.snapshot()
        h, w, _ = img.shape
        if s["active"] and s["word"] and not s["completed"]:
            put_label(img, "Signe :  " + s["word"][s["idx"]], (20, 46), 1.1, (255,255,255), 2, (20,21,43))
        ev = s["last_event"]
        if ev and time.time() - ev[2] < 1.0:
            if ev[0] == "ok":
                cv2.rectangle(img, (0,0), (w-1,h-1), (120,235,60), 10)
            else:
                cv2.rectangle(img, (0,0), (w-1,h-1), (80,80,235), 10)
        if label != "nothing" and conf >= 0.75:
            put_label(img, f"{label} ({conf*100:.0f}%)", (20, h-24), 0.7, (255,255,255), 2, (0,0,0))
        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ---------- Controles ----------
c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2])
mode = c1.radio("Mode", ["Mots", "Lettres adaptatives"], horizontal=True)
lang = c2.selectbox("Langue", ["fr", "en"], format_func=lambda x: "Francais" if x == "fr" else "English")
diff = c3.selectbox("Difficulte", ["Facile", "Moyen", "Difficile"])
start = c4.button("Demarrer / Nouveau defi", type="primary", use_container_width=True)

col_v, col_g = st.columns([1.05, 1], gap="large")
with col_v:
    ctx = webrtc_streamer(key="asl-practice", video_processor_factory=PracticeProcessor,
                          rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
                          media_stream_constraints={"video": True, "audio": False})
    st.caption("Signe la lettre demandee : bord vert = reussi, rouge = essaie encore. Le mot avance lettre par lettre.")

if ctx and ctx.video_processor and start:
    eng = ctx.video_processor.engine
    if not st.session_state.get("pr_session_started"):
        eng.new_session()
        st.session_state.pr_session_started = True
    word = pick_word("letters" if mode.startswith("Lettres") else "words", lang, diff, eng.stats)
    eng.new_word(word)
    st.session_state.pr_celebrated = None

with col_g:
    @st.fragment(run_every="0.4s")
    def _game_panel():
        if not (ctx and ctx.video_processor):
            st.info("Lance la camera puis clique sur Demarrer.")
            return
        eng = ctx.video_processor.engine
        s = eng.snapshot()

        mins, secs = divmod(int(s["elapsed"]), 60)
        fire = " \U0001F525" if s["streak"] >= 3 else ""
        chips = (
            f'<div class="pr-chip"><div class="lab">Score</div><div class="val accent">{s["score"]}</div></div>'
            f'<div class="pr-chip"><div class="lab">Serie</div><div class="val">{s["streak"]}{fire}</div></div>'
            f'<div class="pr-chip"><div class="lab">Mots</div><div class="val">{s["words"]}</div></div>'
            f'<div class="pr-chip"><div class="lab">Vitesse</div><div class="val">{s["lpm"]:.0f}<span style="font-size:.9rem;color:#8A90A8"> l/min</span></div></div>'
            f'<div class="pr-chip"><div class="lab">Temps</div><div class="val">{mins}:{secs:02d}</div></div>'
        )
        tiles = ""
        if s["word"]:
            for i, ch in enumerate(s["word"]):
                cls = "pr-done" if i < s["idx"] else ("pr-cur" if i == s["idx"] and not s["completed"] else "pr-next")
                tiles += f'<div class="pr-tile {cls}">{ch}</div>'
        else:
            tiles = '<div style="color:#8A90A8">Clique sur Demarrer / Nouveau defi</div>'

        feed = ""
        ev = s["last_event"]
        if ev and time.time() - ev[2] < 1.6:
            if ev[0] == "ok":
                feed = f'<span class="pr-ok">\u2714 {ev[1]} reussie !</span>'
            else:
                feed = f'<span class="pr-err">\u2718 {ev[1]} detectee \u2014 vise {s["word"][s["idx"]] if s["word"] and s["idx"] < len(s["word"]) else ""}</span>'
        if s["completed"]:
            feed = '<span class="pr-ok">\U0001F3C6 Mot termine ! +50 points \u2014 defi suivant...</span>'

        st.markdown(f'<div class="pr-arena"><div class="pr-chips">{chips}</div>'
                    f'<div class="pr-tiles">{tiles}</div>'
                    f'<div class="pr-feed">{feed}</div></div>', unsafe_allow_html=True)

        # celebration + enchainement automatique
        if s["completed"]:
            tag = s["word"] + str(s["words"])
            if st.session_state.get("pr_celebrated") != tag:
                st.session_state.pr_celebrated = tag
                st.session_state.pr_next_at = time.time() + 1.6
                st.balloons()
            elif time.time() >= st.session_state.get("pr_next_at", 0):
                word = pick_word("letters" if mode.startswith("Lettres") else "words", lang, diff, eng.stats)
                eng.new_word(word)
    _game_panel()

# ---------- Statistiques personnelles ----------
st.markdown("---")
st.markdown('<div class="asl-header"><span class="bar"></span><h2>Mes statistiques</h2></div>', unsafe_allow_html=True)
st.markdown('<div class="asl-sub">Ton profil d&#39;apprentissage \u2014 le mode adaptatif s&#39;appuie sur ces donnees.</div>', unsafe_allow_html=True)

@st.fragment(run_every="3s")
def _stats_panel():
    stats = load_stats()
    letters = stats.get("letters", {})
    totals = stats.get("totals", {})
    conf = stats.get("confusion", {})
    if not letters:
        st.info("Joue quelques defis : tes statistiques par lettre apparaitront ici.")
        return
    a, b, c = st.columns(3)
    a.metric("Mots reussis (total)", totals.get("words", 0))
    b.metric("Meilleure serie", totals.get("best_streak", 0))
    c.metric("Echantillons collectes", totals.get("samples", 0))

    st.markdown("##### Taux de reussite par lettre")
    rows = sorted(((L, d["c"] / d["a"], d["a"]) for L, d in letters.items() if d["a"] > 0), key=lambda x: x[1])
    html = ""
    for L, rate, n in rows:
        html += (f'<div style="display:flex;align-items:center;gap:.7rem;margin:.25rem 0;">'
                 f'<div style="width:26px;font-weight:700;font-family:Space Grotesk,sans-serif;">{L}</div>'
                 f'<div class="pr-bar" style="flex:1;"><div style="width:{rate*100:.0f}%"></div></div>'
                 f'<div style="width:110px;color:#5B6270;font-size:.85rem;">{rate*100:.0f}% \u00b7 {n} essais</div></div>')
    st.markdown(html, unsafe_allow_html=True)

    if conf:
        top = sorted(conf.items(), key=lambda kv: -kv[1])[:5]
        st.markdown("##### Tes confusions les plus frequentes")
        ARROW = " \u2192 "
        st.markdown("  \u00b7  ".join("**" + k.replace(">", ARROW) + f"** ({v}\u00d7)" for k, v in top))

    st.caption("Les echantillons (landmarks etiquetes) sont enregistres uniquement sur ta machine "
               "(assets/user_samples.csv). Ils serviront a la personnalisation du modele et a "
               "l'evaluation inter-personnes.")
    if st.button("Reinitialiser mes statistiques et echantillons"):
        reset_stats()
        st.rerun()
_stats_panel()
