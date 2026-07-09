import os
import numpy as np
import streamlit as st
from ui import inject_css, app_header, get_model, get_labels, find_sign_images
from asl_core import normalize_landmarks, SentenceBuilder, DynamicDetector, is_thumbs_up
from agent import InterpretingAgent
from conversation import respond, ollama_model
from word_signs import build_frame_features, CustomSignStore, WordSignRecognizer, GestureEpisode
from personal import PersonalLetters
import json as _json
import streamlit.components.v1 as components

inject_css()
app_header("Sign Language to Text", "L'agent observe tes signes, construit le texte et l'interprete.")

TIRET = "\u2014"

def speak_in_browser(text, lang):
    """Lit un texte a voix haute via l'API du navigateur (gratuit, aucune dependance)."""
    payload = _json.dumps(text)
    components.html(
        "<script>try{var u=new SpeechSynthesisUtterance(" + payload + ");"
        "u.lang='" + lang + "';u.rate=1.0;"
        "window.parent.speechSynthesis.cancel();"
        "window.parent.speechSynthesis.speak(u);}catch(e){}</script>",
        height=0)

if not (os.path.exists("asl_mediapipe_mlp_model.h5") and os.path.exists("labels.json")):
    st.error("Modele introuvable. Copie asl_mediapipe_mlp_model.h5 et labels.json dans le dossier de l'app (voir README).")
    st.stop()

missing = []
try:
    import cv2
except Exception:
    missing.append("opencv-python")
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
    st.warning("Dependances manquantes : " + ", ".join(sorted(set(missing)))
               + ". Installe-les (pip install -r requirements_app.txt) puis relance.")
    st.stop()

# --- Reglages en direct ---
st.sidebar.markdown("### Reglages de la demo")
conf = st.sidebar.slider("Seuil de confiance", 0.50, 0.99, 0.80, 0.01)
stab = st.sidebar.slider("Stabilite (frames)", 2, 8, 4, 1)
cooldown = st.sidebar.slider("Delai anti-repetition (s)", 0.2, 1.5, 0.6, 0.1)
dyn_on = st.sidebar.checkbox("Detection J/Z (mouvement)", value=True)
move_sens = st.sidebar.slider("Sensibilite mouvement", 0.05, 0.30, 0.12, 0.01)
st.sidebar.markdown("### Agent")
auto_on = st.sidebar.checkbox("Interpretation automatique", value=True,
    help="Si active, l'agent interprete tout seul apres une pause. Sinon, utilise le bouton Interpreter.")
pause_s = st.sidebar.slider("Delai avant interpretation auto (s)", 1.0, 8.0, 5.0, 0.5,
    disabled=not auto_on)
st.sidebar.markdown("### Conversation")
conv_on = st.sidebar.checkbox("Mode conversation", value=True,
    help="L'agent repond a tes phrases signees (regles locales, ou Ollama si installe).")
voice_on = st.sidebar.checkbox("Lecture vocale des reponses", value=True,
    help="Utilise la voix du navigateur (gratuit, aucune installation).")
_ollama = ollama_model()
st.sidebar.caption("Moteur : " + ("Ollama local (" + _ollama + ")" if _ollama else "regles locales (gratuit)"))
st.sidebar.markdown("### Niveau superieur (beta)")
words_on = st.sidebar.checkbox("Signes-mots", value=False,
    help="Reconnaissance de mots entiers signes d'un geste (modele sequentiel + signes personnalises). "
         "Desactive = comportement lettres strictement identique.")
personal_on = st.sidebar.checkbox("Personnalisation des lettres", value=True,
    help="Tes exemples personnels corrigent le modele pour les lettres que tu as enregistrees.")

mp_hands = mp.solutions.hands
mp_draw = mp.solutions.drawing_utils
FONT = cv2.FONT_HERSHEY_SIMPLEX

def put_label(img, text, org, scale=0.7, color=(255,255,255), thick=2, bg=(0,0,0)):
    (tw, th), base = cv2.getTextSize(text, FONT, scale, thick)
    x, y = org
    cv2.rectangle(img, (x-5, y-th-7), (x+tw+5, y+base+3), bg, -1)
    cv2.putText(img, text, (x, y), FONT, scale, color, thick, cv2.LINE_AA)

def draw_bar(img, x, y, w, h, frac, color):
    frac = max(0.0, min(1.0, frac))
    cv2.rectangle(img, (x,y), (x+w, y+h), (60,60,60), -1)
    cv2.rectangle(img, (x,y), (x+int(w*frac), y+h), color, -1)

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
        self.accept_flash = None   # (mot, heure) pour le bandeau de confirmation
        # --- niveau superieur ---
        self.words_enabled = False
        self.personal_enabled = True
        self.word_recognizer = WordSignRecognizer()
        self.custom_store = CustomSignStore()
        self.episode = GestureEpisode(min_frames=12)
        self.personal = PersonalLetters()
        self.word_flash = None            # (mot, heure)
        self.custom_record = None         # (nom, restants)
        self.personal_capture = None      # (lettre, restants, prochain_t)

    def recv(self, frame):
        img = frame.to_ndarray(format="bgr24")
        img = cv2.flip(img, 1)
        rgb = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
        res = self.hands.process(rgb)
        hand = res.multi_hand_landmarks[0] if res.multi_hand_landmarks else None
        top_label = "nothing"; conf_ = 0.0; pred = None; moving = False; dyn_letter = None

        # --- signes-mots : caracteristiques deux mains + episode de geste ---
        word_seq = None
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
            # personnalisation few-shot : un exemple personnel proche l'emporte
            if self.personal_enabled:
                top_label, conf_, _pers = self.personal.refine(feats63.flatten(), top_label, conf_)
            # capture d'exemples personnels en cours
            if self.personal_capture is not None:
                import time as _t
                letter, remaining, next_t = self.personal_capture
                if _t.time() >= next_t and conf_ > 0.0:
                    self.personal.add(letter, feats63.flatten())
                    remaining -= 1
                    self.personal_capture = (letter, remaining, _t.time() + 0.6) if remaining > 0 else None
            if self.dyn_enabled:
                moving, dyn_letter = self.detector.update(coords, top_label if conf_ >= 0.6 else None)

        # --- Pouce leve : accepter la suggestion n.1 ---
        import time as _t
        thumbs = hand is not None and is_thumbs_up(coords)
        if thumbs:
            self.thumb_frames += 1
        else:
            self.thumb_frames = 0
        if (self.thumb_frames >= 8 and (_t.time() - self.last_accept_t) > 1.5):
            sugg = self.agent.get_suggestions()
            if sugg:
                self.builder.accept_word(sugg[0])
                self.accept_flash = (sugg[0], _t.time())
                self.last_accept_t = _t.time()
            self.thumb_frames = 0

        commit_label = top_label
        if thumbs:
            commit_label = "nothing"          # pas de lettre pendant le pouce leve
        if self.dyn_enabled and top_label in ("J", "Z"):
            commit_label = "nothing"

        if self.dyn_enabled and moving:
            self.builder.update("nothing", 0.0)
        else:
            self.builder.update(commit_label, conf_)
        if self.words_enabled:
            done_seq = self.episode.step(moving and hand is not None, two_hand_feat if two_hand_feat is not None else np.zeros(126, dtype=np.float32))
            if done_seq is not None:
                import time as _t
                if self.custom_record is not None:
                    name, remaining = self.custom_record
                    n = self.custom_store.add(name, done_seq)
                    remaining -= 1
                    self.custom_record = (name, remaining) if remaining > 0 else None
                    self.word_flash = ("enregistre " + name + f" ({n})", _t.time())
                    dyn_letter = None
                else:
                    cname, _score = self.custom_store.match(done_seq)
                    word = cname
                    if word is None and self.word_recognizer.available:
                        word, _c = self.word_recognizer.predict(done_seq)
                    if word is not None:
                        self.builder.commit_word(word)
                        self.word_flash = (word, _t.time())
                        dyn_letter = None          # le signe-mot prime sur J/Z

        if dyn_letter is not None:
            self.builder.commit(dyn_letter)

        sentence = self.builder.get()
        self.agent.observe(sentence, hand is not None)

        if moving:
            put_label(img, "MOUVEMENT (J/Z)", (15, 34), 0.7, (255,255,255), 2, (150,90,0))
        elif pred is not None and conf_ >= 0.80:
            put_label(img, f"{top_label}  {conf_*100:.0f}%", (15, 34), 0.7, (255,255,255), 2, (16,90,40))
        if pred is not None and not moving:
            top3 = np.argsort(pred)[::-1][:3]
            for i, ci in enumerate(top3):
                yb = 62 + i*30
                put_label(img, str(self.labels[ci]), (15, yb+18), 0.6)
                draw_bar(img, 70, yb, 180, 20, float(pred[ci]), (0,200,0))
                put_label(img, f"{pred[ci]*100:3.0f}%", (260, yb+18), 0.55)
        h, w, _ = img.shape

        # signes-mots / captures
        import time as _t
        if self.word_flash and _t.time() - self.word_flash[1] < 1.6:
            put_label(img, "Signe-mot : " + str(self.word_flash[0]).upper(), (w - 420, 34), 0.75,
                      (255, 255, 255), 2, (110, 40, 140))
        if self.custom_record is not None:
            put_label(img, f"Enregistrement '{self.custom_record[0]}' : fais le geste ({self.custom_record[1]} restants)",
                      (20, h - 80), 0.6, (255, 255, 255), 2, (140, 90, 10))
        if self.personal_capture is not None:
            put_label(img, f"Tiens la lettre {self.personal_capture[0]} ({self.personal_capture[1]} exemples restants)",
                      (20, h - 80), 0.6, (255, 255, 255), 2, (140, 90, 10))

        # suggestion en cours + geste d'acceptation
        sugg_now = self.agent.get_suggestions()
        if sugg_now and hand is not None:
            put_label(img, "Pouce leve -> " + sugg_now[0], (w - 330, 34), 0.65,
                      (255, 255, 255), 2, (90, 60, 10))
        if self.accept_flash and (cv2.getTickCount() / cv2.getTickFrequency() or True):
            word, t0 = self.accept_flash
            import time as _t
            if _t.time() - t0 < 1.5:
                put_label(img, "Suggestion acceptee : " + word, (w - 380, 68), 0.65,
                          (255, 255, 255), 2, (16, 110, 40))
            else:
                self.accept_flash = None

        cv2.rectangle(img, (0, h-60), (w, h), (0,0,0), -1)
        put_label(img, sentence[-40:], (20, h-20), 1.0, (255,255,255), 2, (0,0,0))
        return av.VideoFrame.from_ndarray(img, format="bgr24")

col_v, col_s = st.columns([3, 2], gap="large")
with col_v:
    ctx = webrtc_streamer(
        key="asl-demo",
        video_processor_factory=ASLProcessor,
        rtc_configuration={"iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]},
        media_stream_constraints={"video": True, "audio": False},
    )
    if auto_on:
        st.caption(f"Retire ta main ~{pause_s:.0f} s : l'agent interprete automatiquement. "
                   "Pouce leve = accepter la suggestion affichee. Tu peux aussi cliquer sur Interpreter.")
    else:
        st.caption("Interpretation automatique desactivee : clique sur Interpreter quand tu as fini.")

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
        st.sidebar.caption("Signes-mots : modele absent (lance le notebook 03) - "
                           "les signes personnalises restent disponibles.")

with col_s:
    @st.fragment(run_every="0.5s")
    def _agent_panel():
        if not (ctx and ctx.video_processor):
            st.markdown('<div class="asl-panel"><div class="asl-out">' + TIRET + '</div></div>', unsafe_allow_html=True)
            return
        vp = ctx.video_processor
        raw = vp.builder.get() or TIRET
        interp, journal, sugg = vp.agent.state()

        st.markdown('<div class="asl-label">Lettres reconnues (en direct)</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="asl-panel"><div class="asl-out">{raw}</div></div>', unsafe_allow_html=True)

        st.markdown('<div class="asl-label" style="margin-top:1rem;">Interpretation de l&#39;agent</div>', unsafe_allow_html=True)
        st.markdown(f'<div class="asl-panel"><div class="asl-out">{interp if interp else TIRET}</div></div>', unsafe_allow_html=True)

        if sugg:
            st.caption("Suggestions : " + "  \u00b7  ".join(sugg))
        if journal:
            with st.expander("Journal de l'agent (raisonnement)"):
                for line in journal:
                    st.markdown("- " + line)

    _agent_panel()

    b1, b2, b3, b4 = st.columns(4)
    if b1.button("Espace", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.builder.add_space()
    if b2.button("Effacer", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.builder.delete()
    if b3.button("Tout", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.builder.clear()
    if b4.button("Interpreter", type="primary", use_container_width=True) and ctx and ctx.video_processor:
        ctx.video_processor.agent.interpret_now(ctx.video_processor.builder.get())

    c1, c2 = st.columns(2)
    if c1.button("Lire a voix haute", use_container_width=True) and ctx and ctx.video_processor:
        interp_now, _, _ = ctx.video_processor.agent.state()
        if interp_now:
            from conversation import detect_lang
            speak_in_browser(interp_now, "fr-FR" if detect_lang(interp_now) == "fr" else "en-US")
    if c2.button("Effacer la conversation", use_container_width=True):
        st.session_state.conv_history = []
        st.session_state.pending_speech = None

# ================= Conversation (pleine largeur) =================
if conv_on:
    st.markdown("---")
    st.markdown('<div class="asl-header"><span class="bar"></span><h2>Conversation</h2></div>', unsafe_allow_html=True)
    st.markdown('<div class="asl-sub">Signe une phrase puis fais une pause : l&#39;agent repond et parle.</div>', unsafe_allow_html=True)

    @st.fragment(run_every="0.6s")
    def _conversation_panel():
        if "conv_history" not in st.session_state:
            st.session_state.conv_history = []

        # nouvelle interpretation -> reponse de l'agent
        if ctx and ctx.video_processor:
            vp = ctx.video_processor
            interp_now, _, _ = vp.agent.state()
            if interp_now:
                user_msg = vp.agent.consume_interpretation()
                if user_msg:
                    reply, tts_lang, engine = respond(user_msg,
                        [(u, a) for u, a, _ in st.session_state.conv_history])
                    st.session_state.conv_history.append((user_msg, reply, tts_lang))
                    st.session_state.pending_speech = (reply, tts_lang)
                    vp.builder.clear()          # pret pour la phrase suivante

        # fil de discussion : pleine largeur, zone defilante, tout l'historique
        chat = st.container(height=360)
        with chat:
            if not st.session_state.conv_history:
                st.caption("La conversation apparaitra ici.")
            for u, a, _ in st.session_state.conv_history:
                with st.chat_message("user"):
                    st.write(u)
                with st.chat_message("assistant"):
                    st.write(a)

        if voice_on and st.session_state.get("pending_speech"):
            txt, lg = st.session_state.pending_speech
            st.session_state.pending_speech = None
            speak_in_browser(txt, lg)
    _conversation_panel()

# ================= Niveau superieur : personnalisation =================
if ctx and ctx.video_processor:
    _vp = ctx.video_processor
    ecol1, ecol2 = st.columns(2, gap="large")
    with ecol1:
        with st.expander("Creer un signe personnalise (3 gestes)"):
            st.caption("Nomme ton signe, clique Enregistrer, puis fais le geste 3 fois "
                       "(pause entre chaque). Reconnu ensuite comme un mot entier.")
            cname = st.text_input("Nom du signe", value="", key="cs_name",
                                  placeholder="ex: CAVA, STOP, OK...")
            cc1, cc2 = st.columns(2)
            if cc1.button("Enregistrer (3 gestes)", use_container_width=True,
                          disabled=not (words_on and cname.strip())):
                _vp.custom_record = (cname.strip().upper(), 3)
            existing = _vp.custom_store.names()
            if existing:
                st.write("Signes enregistres : " + ", ".join(f"{k} ({v})" for k, v in existing.items()))
                to_del = cc2.selectbox("Supprimer", ["-"] + list(existing), key="cs_del",
                                       label_visibility="collapsed")
                if to_del != "-":
                    _vp.custom_store.delete(to_del)
                    st.rerun()
            if not words_on:
                st.info("Active la case Signes-mots dans la barre laterale.")
    with ecol2:
        with st.expander("Cette lettre ne marche pas chez moi (5 exemples)"):
            st.caption("Choisis la lettre, clique, puis tiens la pose devant la camera : "
                       "5 exemples de TA main corrigeront le modele immediatement.")
            letter = st.selectbox("Lettre", list("ABCDEFGHIKLMNOPQRSTUVWXY"), key="pl_letter")
            pc1, pc2 = st.columns(2)
            if pc1.button("Enregistrer 5 exemples", use_container_width=True):
                import time as _t
                _vp.personal_capture = (letter, 5, _t.time() + 1.0)
            counts = _vp.personal.counts()
            if counts:
                st.write("Exemples personnels : " + ", ".join(f"{k} ({v})" for k, v in sorted(counts.items())))
                if pc2.button("Tout reinitialiser", use_container_width=True):
                    _vp.personal.reset()
                    st.rerun()

# ================= Apprendre les signes =================
st.markdown("---")
st.markdown('<div class="asl-header"><span class="bar"></span><h2>Apprendre les signes</h2></div>', unsafe_allow_html=True)
st.markdown('<div class="asl-sub">Choisis une lettre (ou espace / suppression) pour voir comment la signer.</div>', unsafe_allow_html=True)

signs = find_sign_images()
from ui import get_word_sign_gifs
_gifs = get_word_sign_gifs()
for _n, _p in sorted(_gifs.items()):
    signs["MOT : " + _n.upper()] = _p
if not signs:
    st.info("Images des signes introuvables : place le dossier Asl_Sign_Data a cote du projet (voir README).")
else:
    csel, cimg, ctip = st.columns([1, 1, 2], gap="large")
    with csel:
        choice = st.selectbox("Signe", list(signs.keys()), index=0)
    with cimg:
        st.image(signs[choice], caption=choice, use_container_width=True)
    with ctip:
        default_tip = ("Tiens la pose stable face a la camera : la lettre est validee quand la barre "
                       "de stabilite se remplit.")
        if choice.startswith("MOT : "):
            default_tip = ("Signe-mot : reproduis le MOUVEMENT montre par l'animation. "
                           "Active la case Signes-mots (barre laterale) pour le tester en direct.")
        tips = {
            "ESPACE": "Signe 'space' du jeu de donnees : il ajoute un espace entre deux mots.",
            "SUPPRIMER": "Signe 'del' : il efface la derniere lettre du texte.",
            "J": "J est un geste : pars de la pose du I (auriculaire leve) puis trace un crochet. Active la detection J/Z.",
            "Z": "Z est un geste : trace un Z avec l'index (zigzag). Active la detection J/Z.",
        }
        st.markdown('<div class="asl-panel">' + tips.get(choice, default_tip) + '</div>', unsafe_allow_html=True)
        if choice.startswith("MOT : "):
            from word_signs import sign_video_url
            _w = choice.replace("MOT : ", "").lower()
            st.markdown('<a href="' + sign_video_url(_w) + '" target="_blank" '
                        'style="color:#5B4BE6;font-weight:600;">Voir une vraie personne signer ce mot \u2197</a>',
                        unsafe_allow_html=True)
