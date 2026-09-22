import os
import html
import time
import numpy as np
import streamlit as st
from ui import (inject_css, app_header, section, tiles_html, rtc_config, camera_help,
                get_model, get_labels, find_sign_images, get_word_sign_gifs)
from asl_core import normalize_landmarks, SentenceBuilder, DynamicDetector, is_thumbs_up
from agent import InterpretingAgent
from conversation import (respond, compare, detect_lang, available_providers, is_available,
                          model_for, setting, LABELS, CLOUD)
from word_signs import build_frame_features, CustomSignStore, WordSignRecognizer, GestureEpisode
from personal import PersonalLetters
import json as _json
import streamlit.components.v1 as components

inject_css()
app_header("Sign to Text", "Sign in front of the camera. The agent builds the text, interprets it "
           "after a pause, and answers you.")

DASH = "—"
# video overlay colors (BGR): ink, violet, cyan
INK_BGR, VIOLET_BGR, CYAN_BGR = (51, 24, 21), (255, 91, 107), (196, 184, 18)


def speak_in_browser(text, lang):
    """Read text out loud with the browser's speech API (free, nothing to install)."""
    payload = _json.dumps(text)
    components.html(
        "<script>try{var u=new SpeechSynthesisUtterance(" + payload + ");"
        "u.lang='" + lang + "';u.rate=1.0;"
        "window.parent.speechSynthesis.cancel();"
        "window.parent.speechSynthesis.speak(u);}catch(e){}</script>",
        height=0)


if not (os.path.exists("asl_mediapipe_mlp_model.h5") and os.path.exists("labels.json")):
    st.error("The letter model is missing. Put asl_mediapipe_mlp_model.h5 and labels.json in the app folder "
             "(see README).")
    st.stop()

missing = []
try:
    import cv2
except Exception:
    missing.append("opencv-contrib-python")
try:
    import mediapipe as mp
except Exception:
    missing.append("mediapipe")
try:
    import av
    from streamlit_webrtc import webrtc_streamer, VideoProcessorBase
    WEBRTC_OK = True
except Exception:
    WEBRTC_OK = False
    missing.append("streamlit-webrtc")

if not WEBRTC_OK or missing:
    st.warning("Missing packages: " + ", ".join(sorted(set(missing)))
               + ". Install them with pip install -r requirements.txt, then restart the app.")
    st.stop()

# ---------------- Sidebar settings ----------------
st.sidebar.markdown("### Recognition")
conf = st.sidebar.slider("Confidence threshold", 0.50, 0.99, 0.80, 0.01,
    help="A letter is only accepted above this confidence.")
stab = st.sidebar.slider("Stability (frames)", 2, 8, 4, 1,
    help="How many consecutive frames must agree before a letter is written.")
cooldown = st.sidebar.slider("Repeat delay (s)", 0.2, 1.5, 0.6, 0.1,
    help="Minimum time between two letters, to avoid accidental doubles.")
dyn_on = st.sidebar.checkbox("Detect J and Z (motion)", value=True)
move_sens = st.sidebar.slider("Motion sensitivity", 0.05, 0.30, 0.12, 0.01)
words_on = st.sidebar.checkbox("Word signs", value=False,
    help="Recognize whole words signed with one gesture (sequence model + your custom signs). "
         "When off, only letters are read.")
personal_on = st.sidebar.checkbox("Use my letter examples", value=True,
    help="Your recorded examples override the model for the letters you taught it.")

st.sidebar.markdown("### Agent")
auto_on = st.sidebar.checkbox("Interpret automatically", value=True,
    help="When on, the agent interprets your sentence after a pause. Otherwise use the Interpret button.")
pause_s = st.sidebar.slider("Pause before interpreting (s)", 1.0, 8.0, 5.0, 0.5, disabled=not auto_on)

st.sidebar.markdown("### Conversation")
conv_on = st.sidebar.checkbox("Reply to my sentences", value=True)
voice_on = st.sidebar.checkbox("Read replies out loud", value=True,
    help="Uses your browser's voice (free, nothing to install).")
providers = available_providers()


def _provider_label(p):
    if p == "auto":
        return LABELS["auto"]
    m = model_for(p)
    return LABELS[p] + (f" ({m})" if m else "")


brain = st.sidebar.selectbox("AI model", providers, format_func=_provider_label,
    help="Auto tries Groq, then Groq (fast), Gemini, Ollama and finally the local rules. "
         "Only the models configured for this app are listed.")
can_compare = is_available("groq") and is_available("gemini")
compare_on = st.sidebar.toggle("Compare Groq and Gemini", value=False, disabled=not can_compare,
    help="Sends each sentence to both models and shows the two answers side by side. "
         "Uses both quotas." if can_compare else "Needs both GROQ_API_KEY and GEMINI_API_KEY.")
MAX_CLOUD = int(setting("MAX_CLOUD_REPLIES", "40") or 40)

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
FONT = cv2.FONT_HERSHEY_SIMPLEX


def put_label(img, text, org, scale=0.7, color=(255, 255, 255), thick=2, bg=INK_BGR):
    (tw, th), base = cv2.getTextSize(text, FONT, scale, thick)
    x, y = org
    cv2.rectangle(img, (x - 5, y - th - 7), (x + tw + 5, y + base + 3), bg, -1)
    cv2.putText(img, text, (x, y), FONT, scale, color, thick, cv2.LINE_AA)


def draw_bar(img, x, y, w, h, frac, color):
    frac = max(0.0, min(1.0, frac))
    cv2.rectangle(img, (x, y), (x + w, y + h), (70, 60, 50), -1)
    cv2.rectangle(img, (x, y), (x + int(w * frac), y + h), color, -1)


class ASLProcessor(VideoProcessorBase):
    def __init__(self):
        self.model = get_model()
        self.labels = get_labels()
        self.hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7, max_num_hands=1)
        self.builder = SentenceBuilder()
        self.detector = DynamicDetector()
        self.agent = InterpretingAgent()
        self.dyn_enabled = True
        self.thumb_frames = 0
        self.last_accept_t = 0.0
        self.accept_flash = None          # (word, time) confirmation banner
        self.words_enabled = False
        self.personal_enabled = True
        self.word_recognizer = WordSignRecognizer()
        self.custom_store = CustomSignStore()
        self.episode = GestureEpisode(min_frames=12)
        self.personal = PersonalLetters()
        self.word_flash = None            # (word, time)
        self.custom_record = None         # (name, remaining)
        self.personal_capture = None      # (letter, remaining, next_t)

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = self.hands.process(rgb)
        hand = res.multi_hand_landmarks[0] if res.multi_hand_landmarks else None
        top_label = "nothing"; conf_ = 0.0; pred = None; moving = False; dyn_letter = None
        coords = None

        # word signs: two-hand features + gesture episode
        if self.words_enabled and res.multi_hand_landmarks:
            left = right = None
            handed = res.multi_handedness or []
            for hl2, hd in zip(res.multi_hand_landmarks, handed):
                arr = np.array([[p.x, p.y, p.z] for p in hl2.landmark], dtype=np.float32)
                lab2 = hd.classification[0].label if hd.classification else "Right"
                if lab2 == "Left":
                    left = arr
                else:
                    right = arr
            two_hand_feat = build_frame_features(left, right)
        else:
            two_hand_feat = None

        if hand is not None:
            mp_draw.draw_landmarks(img, hand, mp_hands.HAND_CONNECTIONS)
            coords = np.array([[p.x, p.y, p.z] for p in hand.landmark], dtype=np.float32)
            feats63 = normalize_landmarks(coords)
            pred = self.model.predict(feats63.reshape(1, -1), verbose=0)[0]
            idx = int(np.argmax(pred)); conf_ = float(pred[idx]); top_label = self.labels[idx]
            # few-shot personalization: a close personal example wins
            if self.personal_enabled:
                top_label, conf_, _pers = self.personal.refine(feats63.flatten(), top_label, conf_)
            # personal example capture in progress
            if self.personal_capture is not None:
                letter, remaining, next_t = self.personal_capture
                if time.time() >= next_t and conf_ > 0.0:
                    self.personal.add(letter, feats63.flatten())
                    remaining -= 1
                    self.personal_capture = (letter, remaining, time.time() + 0.6) if remaining > 0 else None
            if self.dyn_enabled:
                moving, dyn_letter = self.detector.update(coords, top_label if conf_ >= 0.6 else None)

        # thumbs up: accept the first suggestion
        thumbs = hand is not None and is_thumbs_up(coords)
        self.thumb_frames = self.thumb_frames + 1 if thumbs else 0
        if self.thumb_frames >= 8 and (time.time() - self.last_accept_t) > 1.5:
            sugg = self.agent.get_suggestions()
            if sugg:
                self.builder.accept_word(sugg[0])
                self.accept_flash = (sugg[0], time.time())
                self.last_accept_t = time.time()
            self.thumb_frames = 0

        commit_label = top_label
        if thumbs:
            commit_label = "nothing"          # no letter while the thumb is up
        if self.dyn_enabled and top_label in ("J", "Z"):
            commit_label = "nothing"

        if self.dyn_enabled and moving:
            self.builder.update("nothing", 0.0)
        else:
            self.builder.update(commit_label, conf_)
        if self.words_enabled:
            done_seq = self.episode.step(moving and hand is not None,
                                         two_hand_feat if two_hand_feat is not None else np.zeros(126, dtype=np.float32))
            if done_seq is not None:
                if self.custom_record is not None:
                    name, remaining = self.custom_record
                    n = self.custom_store.add(name, done_seq)
                    remaining -= 1
                    self.custom_record = (name, remaining) if remaining > 0 else None
                    self.word_flash = ("saved " + name + f" ({n})", time.time())
                    dyn_letter = None
                else:
                    cname, _score = self.custom_store.match(done_seq)
                    word = cname
                    if word is None and self.word_recognizer.available:
                        word, _c = self.word_recognizer.predict(done_seq)
                    if word is not None:
                        self.builder.commit_word(word)
                        self.word_flash = (word, time.time())
                        dyn_letter = None          # a word sign wins over J/Z

        if dyn_letter is not None:
            self.builder.commit(dyn_letter)

        sentence = self.builder.get()
        self.agent.observe(sentence, hand is not None)

        if moving:
            put_label(img, "MOTION (J/Z)", (15, 34), 0.7, INK_BGR, 2, CYAN_BGR)
        elif pred is not None and conf_ >= 0.80:
            put_label(img, f"{top_label}  {conf_*100:.0f}%", (15, 34), 0.7, (255, 255, 255), 2, VIOLET_BGR)
        if pred is not None and not moving:
            top3 = np.argsort(pred)[::-1][:3]
            for i, ci in enumerate(top3):
                yb = 62 + i * 30
                put_label(img, str(self.labels[ci]), (15, yb + 18), 0.6)
                draw_bar(img, 70, yb, 180, 20, float(pred[ci]), VIOLET_BGR)
                put_label(img, f"{pred[ci]*100:3.0f}%", (260, yb + 18), 0.55)
        h, w, _ = img.shape

        if self.word_flash and time.time() - self.word_flash[1] < 1.6:
            put_label(img, "Word sign: " + str(self.word_flash[0]).upper(), (w - 380, 34), 0.75,
                      INK_BGR, 2, CYAN_BGR)
        if self.custom_record is not None:
            put_label(img, f"Recording '{self.custom_record[0]}': do the gesture ({self.custom_record[1]} left)",
                      (20, h - 80), 0.6, INK_BGR, 2, CYAN_BGR)
        if self.personal_capture is not None:
            put_label(img, f"Hold the letter {self.personal_capture[0]} ({self.personal_capture[1]} examples left)",
                      (20, h - 80), 0.6, INK_BGR, 2, CYAN_BGR)

        # current suggestion + acceptance gesture
        sugg_now = self.agent.get_suggestions()
        if sugg_now and hand is not None:
            put_label(img, "Thumbs up = " + sugg_now[0], (w - 300, 34), 0.65)
        if self.accept_flash:
            word, t0 = self.accept_flash
            if time.time() - t0 < 1.5:
                put_label(img, "Accepted: " + word, (w - 300, 68), 0.65, (255, 255, 255), 2, VIOLET_BGR)
            else:
                self.accept_flash = None

        cv2.rectangle(img, (0, h - 60), (w, h), INK_BGR, -1)
        put_label(img, sentence[-40:], (20, h - 20), 1.0, (255, 255, 255), 2, INK_BGR)
        return av.VideoFrame.from_ndarray(img, format="bgr24")


col_v, col_s = st.columns([3, 2], gap="large")
with col_v:
    ctx = webrtc_streamer(
        key="asl-demo",
        video_processor_factory=ASLProcessor,
        rtc_configuration=rtc_config(),
        media_stream_constraints={"video": True, "audio": False},
    )
    if auto_on:
        st.caption(f"Lower your hand for about {pause_s:.0f} s and the agent interprets the sentence. "
                   "Thumbs up accepts the suggested word.")
    else:
        st.caption("Automatic interpretation is off: click Interpret when you are done.")
    camera_help()

if ctx and ctx.video_processor:
    vp = ctx.video_processor
    vp.builder.conf_threshold = conf
    vp.builder.stab_threshold = stab
    vp.builder.cooldown = cooldown
    vp.dyn_enabled = dyn_on
    vp.detector.move_threshold = move_sens
    vp.agent.auto = auto_on
    vp.agent.pause_s = pause_s
    vp.personal_enabled = personal_on
    if vp.words_enabled != words_on:
        vp.words_enabled = words_on
        vp.hands = mp_hands.Hands(min_detection_confidence=0.7, min_tracking_confidence=0.7,
                                  max_num_hands=2 if words_on else 1)
    if words_on and not vp.word_recognizer.available and not vp.custom_store.names():
        st.sidebar.caption("Word-sign model not found (run notebook 03). Your custom signs still work.")


def _panel(label, body_html):
    st.markdown(f'<div class="panel-label">{label}</div><div class="panel">{body_html}</div>',
                unsafe_allow_html=True)


with col_s:
    @st.fragment(run_every="0.5s")
    def _agent_panel():
        empty = f'<div class="readout empty">{DASH}</div>'
        if not (ctx and ctx.video_processor):
            _panel("Letters read live", '<div class="readout empty">Click Start to turn on the camera.</div>')
            st.markdown("")
            _panel("Agent interpretation", empty)
            return
        vp = ctx.video_processor
        raw = vp.builder.get()
        interp, journal, sugg = vp.agent.state()
        shown = raw[-22:]
        n_letters = len(shown.replace(" ", ""))
        _panel("Letters read live",
               tiles_html(shown, done=n_letters - 1, now=n_letters - 1, size="sm") if raw.strip() else empty)
        st.markdown("")
        _panel("Agent interpretation",
               f'<div class="readout">{html.escape(interp)}</div>' if interp else empty)
        if sugg:
            st.caption("Suggestions: " + ", ".join(sugg))
        if journal:
            with st.expander("Agent reasoning"):
                for line in journal:
                    st.markdown("- " + line)

    _agent_panel()

    b1, b2, b3, b4 = st.columns(4)
    if b1.button("Space", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.builder.add_space()
    if b2.button("Delete", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.builder.delete()
    if b3.button("Clear", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.builder.clear()
    if b4.button("Interpret", type="primary", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.agent.interpret_now(ctx.video_processor.builder.get())

    c1, c2 = st.columns(2)
    if c1.button("Read out loud", use_container_width=True) and ctx and ctx.video_processor:
        interp_now, _, _ = ctx.video_processor.agent.state()
        if interp_now:
            speak_in_browser(interp_now, "fr-FR" if detect_lang(interp_now) == "fr" else "en-US")
    if c2.button("Clear conversation", use_container_width=True):
        st.session_state.conv_history = []
        st.session_state.pending_speech = None

# ================= Conversation (full width) =================
if conv_on:
    section("Conversation", "Sign a sentence, then pause: the agent answers and speaks.")

    def _meta_line(r):
        line = f"Answered by {r.engine} in {r.seconds:.1f} s"
        return line + (". " + r.note if r.note else "")

    @st.fragment(run_every="0.6s")
    def _conversation_panel():
        if "conv_history" not in st.session_state:
            st.session_state.conv_history = []
        used = st.session_state.get("cloud_replies", 0)
        allow_cloud = used < MAX_CLOUD

        # a new interpretation -> the agent replies
        if ctx and ctx.video_processor:
            vp = ctx.video_processor
            interp_now, _, _ = vp.agent.state()
            if interp_now:
                user_msg = vp.agent.consume_interpretation()
                if user_msg:
                    past = [(h["user"], h["reply"].text) for h in st.session_state.conv_history]
                    with st.spinner("Thinking..."):
                        if compare_on and allow_cloud:
                            replies = compare(user_msg, past)
                            ok = [r for r in replies if r.text]
                            main = ok[0] if ok else respond(user_msg, past, "rules")
                        else:
                            replies = []
                            main = respond(user_msg, past, brain, allow_cloud=allow_cloud)
                    st.session_state.cloud_replies = used + sum(1 for r in (replies or [main]) if r.provider in CLOUD)
                    st.session_state.conv_history.append({"user": user_msg, "reply": main, "compare": replies})
                    st.session_state.pending_speech = (main.text, main.lang)
                    vp.builder.clear()          # ready for the next sentence

        chat = st.container(height=380)
        with chat:
            if not st.session_state.conv_history:
                st.caption("Your conversation will appear here.")
            for h in st.session_state.conv_history:
                with st.chat_message("user"):
                    st.write(h["user"])
                with st.chat_message("assistant"):
                    if h["compare"]:
                        cols = st.columns(len(h["compare"]))
                        for col, r in zip(cols, h["compare"]):
                            with col:
                                st.markdown(f"**{r.engine}**")
                                st.write(r.text or r.note)
                                st.caption(f"{r.seconds:.1f} s")
                    else:
                        st.write(h["reply"].text)
                        st.caption(_meta_line(h["reply"]))

        if not allow_cloud:
            st.caption(f"This session reached its {MAX_CLOUD} AI replies: the agent now answers with "
                       "local rules. Reload the page to start a new session.")
        if voice_on and st.session_state.get("pending_speech"):
            txt, lg = st.session_state.pending_speech
            st.session_state.pending_speech = None
            speak_in_browser(txt, lg)

    _conversation_panel()

# ================= Personalization =================
if ctx and ctx.video_processor:
    _vp = ctx.video_processor
    section("Personalization")
    ecol1, ecol2 = st.columns(2, gap="large")
    with ecol1:
        with st.expander("Create a custom sign (3 gestures)"):
            st.caption("Name your sign, click Record, then do the gesture 3 times with a short pause "
                       "between each. It is then recognized as a whole word.")
            cname = st.text_input("Sign name", value="", key="cs_name", placeholder="e.g. STOP, OK, COFFEE")
            cc1, cc2 = st.columns(2)
            if cc1.button("Record 3 gestures", use_container_width=True,
                          disabled=not (words_on and cname.strip())):
                _vp.custom_record = (cname.strip().upper(), 3)
            existing = _vp.custom_store.names()
            if existing:
                st.write("Saved signs: " + ", ".join(f"{k} ({v})" for k, v in existing.items()))
                to_del = cc2.selectbox("Delete a sign", ["-"] + list(existing), key="cs_del",
                                       label_visibility="collapsed")
                if to_del != "-":
                    _vp.custom_store.delete(to_del)
                    st.rerun()
            if not words_on:
                st.info("Turn on Word signs in the sidebar first.")
    with ecol2:
        with st.expander("A letter doesn't work for me (5 examples)"):
            st.caption("Pick the letter, click Record, then hold the pose in front of the camera: "
                       "5 examples of your hand correct the model right away.")
            letter = st.selectbox("Letter", list("ABCDEFGHIKLMNOPQRSTUVWXY"), key="pl_letter")
            pc1, pc2 = st.columns(2)
            if pc1.button("Record 5 examples", use_container_width=True):
                _vp.personal_capture = (letter, 5, time.time() + 1.0)
            counts = _vp.personal.counts()
            if counts:
                st.write("Your examples: " + ", ".join(f"{k} ({v})" for k, v in sorted(counts.items())))
                if pc2.button("Reset all", use_container_width=True):
                    _vp.personal.reset()
                    st.rerun()

# ================= Learn the signs =================
section("Learn the signs", "Pick a letter to see how to sign it.")

signs = find_sign_images()
for _n, _p in sorted(get_word_sign_gifs().items()):
    signs["WORD: " + _n.upper()] = _p
csel, cimg, ctip = st.columns([1, 1, 2], gap="large")
with csel:
    choice = st.selectbox("Sign", list(signs.keys()), index=0)
with cimg:
    st.image(signs[choice], caption=choice, use_container_width=True)
with ctip:
    tip = "Hold the pose steady in front of the camera: the letter is written once it stays stable."
    if choice.startswith("WORD: "):
        tip = ("Word sign: copy the movement shown in the animation. Turn on Word signs in the sidebar "
               "to try it live.")
    tips = {
        "SPACE": "The 'space' sign from the dataset adds a space between two words.",
        "DELETE": "The 'del' sign erases the last letter.",
        "J": "J is a movement: start from the I pose (little finger up) and draw a hook. Keep J/Z detection on.",
        "Z": "Z is a movement: draw a Z in the air with your index finger. Keep J/Z detection on.",
    }
    st.markdown('<div class="panel">' + tips.get(choice, tip) + '</div>', unsafe_allow_html=True)
    from word_signs import sign_video_url
    _w = choice.replace("WORD: ", "").lower()
    if choice.startswith("WORD: ") or len(choice) == 1:
        st.markdown(f'<p style="margin-top:.8rem"><a href="{sign_video_url(_w)}" target="_blank">'
                    'Watch real people sign it on SignASL.org</a></p>', unsafe_allow_html=True)
