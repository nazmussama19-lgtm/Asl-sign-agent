import os, time
import numpy as np
import streamlit as st
from ui import inject_css, app_header, section, tiles_html, rtc_config, camera_help, get_model, get_labels
from asl_core import normalize_landmarks
from practice import PracticeEngine, pick_word, load_stats, reset_stats

inject_css()
app_header("Practice", "Spell the word on screen, one letter at a time. Adaptive drills bring back "
           "the letters you miss most.")

if not (os.path.exists("asl_mediapipe_mlp_model.h5") and os.path.exists("labels.json")):
    st.error("The letter model is missing. Put asl_mediapipe_mlp_model.h5 and labels.json in the app folder.")
    st.stop()
try:
    import cv2, mediapipe as mp, av
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
except Exception:
    st.warning("Webcam packages are missing: run pip install -r requirements.txt, then restart the app.")
    st.stop()

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
FONT = cv2.FONT_HERSHEY_SIMPLEX
INK_BGR, VIOLET_BGR, CYAN_BGR = (51, 24, 21), (255, 91, 107), (196, 184, 18)
OK_BGR, ERR_BGR = (79, 123, 15), (53, 35, 180)


def put_label(img, text, org, scale=0.8, color=(255, 255, 255), thick=2, bg=INK_BGR):
    (tw, th), base = cv2.getTextSize(text, FONT, scale, thick)
    x, y = org
    cv2.rectangle(img, (x - 6, y - th - 8), (x + tw + 6, y + base + 4), bg, -1)
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
            put_label(img, "Sign:  " + s["word"][s["idx"]], (20, 46), 1.1, INK_BGR, 2, CYAN_BGR)
        ev = s["last_event"]
        if ev and time.time() - ev[2] < 1.0:
            cv2.rectangle(img, (0, 0), (w - 1, h - 1), OK_BGR if ev[0] == "ok" else ERR_BGR, 10)
        if label != "nothing" and conf >= 0.75:
            put_label(img, f"{label} ({conf*100:.0f}%)", (20, h - 24), 0.7)
        return av.VideoFrame.from_ndarray(img, format="bgr24")


# ---------- Controls ----------
c1, c2, c3, c4 = st.columns([1.2, 1, 1, 1.2])
mode = c1.radio("Mode", ["Words", "Adaptive letters"], horizontal=True)
lang = c2.selectbox("Word language", ["en", "fr"], format_func=lambda x: "English" if x == "en" else "French")
level = c3.selectbox("Difficulty", ["Easy", "Medium", "Hard"])
start = c4.button("Start a new challenge", type="primary", use_container_width=True)
kind = "letters" if mode == "Adaptive letters" else "words"

col_v, col_g = st.columns([1.05, 1], gap="large")
with col_v:
    ctx = webrtc_streamer(key="asl-practice", video_processor_factory=PracticeProcessor,
                          rtc_configuration=rtc_config(),
                          media_stream_constraints={"video": True, "audio": False})
    st.caption("Sign the highlighted letter. A green frame means correct, red means try again.")
    camera_help()

if ctx and ctx.video_processor and start:
    eng = ctx.video_processor.engine
    if not st.session_state.get("pr_session_started"):
        eng.new_session()
        st.session_state.pr_session_started = True
    eng.new_word(pick_word(kind, lang, level, eng.stats))
    st.session_state.pr_celebrated = None

with col_g:
    @st.fragment(run_every="0.4s")
    def _game_panel():
        if not (ctx and ctx.video_processor):
            st.info("Click Start under the video to turn on the camera, then start a challenge.")
            return
        eng = ctx.video_processor.engine
        s = eng.snapshot()

        mins, secs = divmod(int(s["elapsed"]), 60)
        score = (f'<div class="score"><div><b>{s["score"]}</b>points</div>'
                 f'<div class="hot"><b>{s["streak"]}</b>streak</div>'
                 f'<div><b>{s["words"]}</b>words</div>'
                 f'<div><b>{s["lpm"]:.0f}</b>letters / min</div>'
                 f'<div><b>{mins}:{secs:02d}</b>time</div></div>')
        if s["word"]:
            board = tiles_html(s["word"], done=s["idx"], now=None if s["completed"] else s["idx"], size="lg")
        else:
            board = '<p class="asl-sub" style="margin:0">Click Start a new challenge.</p>'

        feed = '<div class="feed"></div>'
        ev = s["last_event"]
        if s["completed"]:
            feed = '<div class="feed ok">Word complete, +50 points. Next challenge coming up.</div>'
        elif ev and time.time() - ev[2] < 1.6:
            if ev[0] == "ok":
                feed = f'<div class="feed ok">{ev[1]} is correct.</div>'
            else:
                target = s["word"][s["idx"]] if s["word"] and s["idx"] < len(s["word"]) else ""
                feed = f'<div class="feed err">That looked like {ev[1]}. Aim for {target}.</div>'

        st.markdown(f'<div class="panel">{score}{board}{feed}</div>', unsafe_allow_html=True)

        # celebrate, then chain the next challenge
        if s["completed"]:
            tag = s["word"] + str(s["words"])
            if st.session_state.get("pr_celebrated") != tag:
                st.session_state.pr_celebrated = tag
                st.session_state.pr_next_at = time.time() + 1.6
                st.balloons()
            elif time.time() >= st.session_state.get("pr_next_at", 0):
                eng.new_word(pick_word(kind, lang, level, eng.stats))
    _game_panel()

# ---------- Personal statistics ----------
section("Your progress", "The adaptive mode uses these numbers to pick your next letters.")


@st.fragment(run_every="3s")
def _stats_panel():
    stats = load_stats()
    letters = stats.get("letters", {})
    totals = stats.get("totals", {})
    conf = stats.get("confusion", {})
    if not letters:
        st.info("Play a few challenges: your success rate for each letter will show up here.")
        return
    a, b, c = st.columns(3)
    a.metric("Words completed", totals.get("words", 0))
    b.metric("Best streak", totals.get("best_streak", 0))
    c.metric("Samples collected", totals.get("samples", 0))

    st.markdown('<h3 class="asl-h3" style="margin-top:1.2rem">Success rate by letter</h3>', unsafe_allow_html=True)
    rows = sorted(((L, d["c"] / d["a"], d["a"]) for L, d in letters.items() if d["a"] > 0), key=lambda x: x[1])
    st.markdown("".join(
        f'<div class="rate"><div class="l">{L}</div><div class="bar"><div style="width:{rate*100:.0f}%"></div></div>'
        f'<div class="n">{rate*100:.0f}% of {n} tries</div></div>' for L, rate, n in rows), unsafe_allow_html=True)

    if conf:
        top = sorted(conf.items(), key=lambda kv: -kv[1])[:5]
        st.markdown('<h3 class="asl-h3" style="margin-top:1.2rem">Letters you mix up most</h3>', unsafe_allow_html=True)
        st.markdown("\n".join(f"- You aimed for **{k.split('>')[0]}**, the model saw **{k.split('>')[1]}** ({v} times)"
                              for k, v in top))

    st.caption("Labeled samples are saved only on the machine running the app (assets/user_samples.csv). "
               "They power personalization and cross-person evaluation.")
    if st.button("Reset my statistics and samples"):
        reset_stats()
        st.rerun()


_stats_panel()
