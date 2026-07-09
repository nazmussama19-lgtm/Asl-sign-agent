import io
import unicodedata
import streamlit as st
from ui import inject_css, app_header, find_sign_images, get_best_photos, get_word_sign_gifs
from word_signs import WORD_TO_SIGN

inject_css()
app_header("Text to Sign Language", "Signes-mots quand ils existent, epellation pour le reste - comme les signeurs.")

# Meilleures vraies photos (lettres) ; photos brutes en secours
signs = get_best_photos()
if not signs:
    signs = find_sign_images()
letters_map = {k: v for k, v in signs.items() if len(k) == 1}
space_img = signs.get("ESPACE")
gifs = get_word_sign_gifs()

if not letters_map:
    st.warning("Signes introuvables : place le dossier Asl_Sign_Data a cote du projet (voir README).")
    st.stop()
if gifs:
    st.caption(f"{len(gifs)} signes-mots disponibles (animations) - les autres mots sont epeles lettre par lettre.")
else:
    st.caption("Aucun signe-mot genere pour l'instant (lance make_word_previews.py) : tout est epele.")

# ---------------- Entree ----------------
c_txt, c_opt = st.columns([3, 1.4], gap="large")
with c_txt:
    st.markdown('<div class="asl-label">Ton texte</div>', unsafe_allow_html=True)
    text = st.text_area("t", "HELLO MY FRIEND", height=110, label_visibility="collapsed",
                        placeholder="Ecris une phrase...")
with c_opt:
    st.markdown('<div class="asl-label">Options</div>', unsafe_allow_html=True)
    lang = st.selectbox("Langue du texte", ["Francais", "English"])
    do_translate = st.checkbox("Traduire vers " + ("l'anglais" if lang == "Francais" else "le francais"),
                               value=False, help="Traduction gratuite (internet requis).")
    speed = st.slider("Vitesse (s / lettre)", 0.3, 2.0, 0.8, 0.1)

def clean_word(w):
    t = unicodedata.normalize("NFD", w)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return "".join(c for c in t.upper() if c.isalpha())

def build_items(sentence):
    """Decoupe la phrase en elements : signe-mot anime OU suite de lettres, avec espaces."""
    items = []
    words = [clean_word(w) for w in sentence.split()]
    words = [w for w in words if w]
    for wi, w in enumerate(words):
        sign = WORD_TO_SIGN.get(w)
        if sign and sign in gifs:
            items.append({"type": "sign", "name": sign, "path": gifs[sign], "disp": w})
        else:
            for ch in w:
                if ch in letters_map:
                    items.append({"type": "letter", "ch": ch})
        if wi < len(words) - 1:
            items.append({"type": "space"})
    return items

if st.button("Traduire en signes", type="primary", use_container_width=True):
    final = text
    st.session_state.t2s_translated = None
    if do_translate and text.strip():
        try:
            from deep_translator import GoogleTranslator
            src, tgt = ("fr", "en") if lang == "Francais" else ("en", "fr")
            final = GoogleTranslator(source=src, target=tgt).translate(text)
            st.session_state.t2s_translated = final
        except Exception:
            st.warning("Traduction indisponible : j'utilise le texte original.")
    items = build_items(final)
    if not items:
        st.info("Rien a signer : ecris quelques mots.")
    else:
        st.session_state.t2s_items = items
        st.session_state.t2s_idx = 0
        st.session_state.t2s_ticks = 0
        st.session_state.t2s_playing = True
        st.session_state.t2s_gif = None

items = st.session_state.get("t2s_items")

# ---------------- Lecteur hybride ----------------
if items:
    if st.session_state.get("t2s_translated"):
        st.caption("Traduction : " + st.session_state.t2s_translated)

    col_play, col_side = st.columns([1.1, 1], gap="large")

    with col_play:
        @st.fragment(run_every=f"{speed}s")
        def _player():
            idx = min(st.session_state.get("t2s_idx", 0), len(items) - 1)
            it = items[idx]
            if it["type"] == "sign":
                st.image(it["path"], caption="Signe : " + it["disp"], use_container_width=True)
                dwell = max(2, round(2.0 / speed))      # les signes restent plus longtemps
            elif it["type"] == "space":
                if space_img:
                    st.image(space_img, caption="ESPACE", use_container_width=True)
                else:
                    st.markdown('<div class="asl-panel" style="text-align:center;padding:3rem;">'
                                '<span style="font-size:3rem;">\u2423</span><br>ESPACE</div>',
                                unsafe_allow_html=True)
                dwell = 1
            else:
                st.image(letters_map[it["ch"]], caption="Lettre " + it["ch"], use_container_width=True)
                dwell = 1

            st.progress((idx + 1) / len(items))

            # bandeau des elements, courant surligne
            html = ""
            for i, x in enumerate(items):
                cur = (i == idx)
                if x["type"] == "sign":
                    style = ("background:linear-gradient(120deg,#5B4BE6,#06B6D4);color:#fff;"
                             if cur else "background:#ECECF5;color:#5B6270;")
                    html += (f'<span style="{style}border-radius:999px;padding:3px 10px;'
                             f'font-weight:700;margin:2px;display:inline-block;">{x["disp"]}</span>')
                elif x["type"] == "space":
                    html += '<span style="padding:0 6px;color:#B6BACF;">\u00b7</span>'
                else:
                    style = ("background:linear-gradient(120deg,#5B4BE6,#06B6D4);color:#fff;border-radius:6px;"
                             if cur else "color:#5B6270;")
                    html += f'<span style="{style}padding:2px 5px;margin:1px;display:inline-block;font-family:monospace;font-weight:700;">{x["ch"]}</span>'
            st.markdown('<div class="asl-panel" style="line-height:2.1;">' + html + "</div>", unsafe_allow_html=True)

            if st.session_state.get("t2s_playing", False):
                st.session_state.t2s_ticks = st.session_state.get("t2s_ticks", 0) + 1
                if st.session_state.t2s_ticks >= dwell:
                    st.session_state.t2s_ticks = 0
                    if idx + 1 < len(items):
                        st.session_state.t2s_idx = idx + 1
                    else:
                        st.session_state.t2s_playing = False
        _player()

        b1, b2 = st.columns(2)
        if b1.button(("Pause" if st.session_state.get("t2s_playing") else "Lecture"), use_container_width=True):
            if not st.session_state.get("t2s_playing") and st.session_state.get("t2s_idx", 0) >= len(items) - 1:
                st.session_state.t2s_idx = 0
            st.session_state.t2s_playing = not st.session_state.get("t2s_playing", False)
            st.session_state.t2s_ticks = 0
            st.rerun()
        if b2.button("Recommencer", use_container_width=True):
            st.session_state.t2s_idx = 0
            st.session_state.t2s_ticks = 0
            st.session_state.t2s_playing = True
            st.rerun()

    with col_side:
        st.markdown('<div class="asl-label">Exporter</div>', unsafe_allow_html=True)
        st.caption("GIF anime de la phrase : signes-mots en mouvement + lettres epelees.")
        if st.button("Generer le GIF", use_container_width=True):
            with st.spinner("Creation du GIF..."):
                from PIL import Image, ImageDraw, ImageSequence
                frames, durations = [], []

                def letter_frame(img_path, label):
                    canvas = Image.new("RGB", (320, 352), (247, 248, 253))
                    if img_path:
                        canvas.paste(Image.open(img_path).convert("RGB").resize((320, 320)), (0, 0))
                    d = ImageDraw.Draw(canvas)
                    d.rectangle([0, 320, 320, 352], fill=(20, 21, 43))
                    d.text((10, 328), label, fill=(255, 255, 255))
                    return canvas

                for it in items:
                    if it["type"] == "sign":
                        gif = Image.open(it["path"])
                        for fr in ImageSequence.Iterator(gif):
                            f = fr.convert("RGB").resize((320, 352))
                            frames.append(f); durations.append(80)
                    elif it["type"] == "space":
                        frames.append(letter_frame(space_img, "ESPACE"))
                        durations.append(int(speed * 700))
                    else:
                        frames.append(letter_frame(letters_map[it["ch"]], it["ch"]))
                        durations.append(int(speed * 1000))
                buf = io.BytesIO()
                frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                               duration=durations, loop=0)
                st.session_state.t2s_gif = buf.getvalue()
        if st.session_state.get("t2s_gif"):
            st.image(st.session_state.t2s_gif)
            st.download_button("Telecharger le GIF", st.session_state.t2s_gif,
                               file_name="signes.gif", mime="image/gif", use_container_width=True)
else:
    st.info("Ecris un texte puis clique sur Traduire en signes.", icon="\u270D\uFE0F")

st.markdown("---")
st.caption("Priorite aux signes-mots (animations issues du dataset Google ASL Signs) ; les mots sans signe "
           "connu sont epeles avec l'alphabet (photos reelles). J et Z impliquent un mouvement.")
