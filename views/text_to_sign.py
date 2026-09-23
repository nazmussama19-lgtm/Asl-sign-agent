import io
import html
import unicodedata
import urllib.request
import streamlit as st
from ui import inject_css, app_header, find_sign_images, get_best_photos, get_word_sign_gifs, uses_remote_images, img_src
from word_signs import WORD_TO_SIGN, sign_video_url

inject_css()
app_header("Text to Sign", "Type a sentence: known word signs are animated, every other word is "
           "fingerspelled, the way signers do it.")

# Best real photos (letters) when the dataset is installed; otherwise drawings or raw photos
signs = get_best_photos() or find_sign_images()
letters_map = {k: v for k, v in signs.items() if len(k) == 1}
space_img = signs.get("SPACE")
gifs = get_word_sign_gifs()

# ---------------- Input ----------------
c_txt, c_opt = st.columns([3, 1.4], gap="large")
with c_txt:
    text = st.text_area("Your text", "HELLO MY FRIEND", height=110, placeholder="Type a sentence...")
with c_opt:
    lang = st.selectbox("Text language", ["English", "French"])
    do_translate = st.checkbox("Translate to " + ("French" if lang == "English" else "English") + " first",
                               value=False, help="Free online translation (needs internet).")
    speed = st.slider("Speed (seconds per letter)", 0.3, 2.0, 0.8, 0.1)
if gifs:
    st.caption(f"{len(gifs)} word signs are animated. Other words are spelled letter by letter.")
else:
    st.caption("Word-sign animations are not installed here, so every word is fingerspelled.")


def clean_word(w):
    t = unicodedata.normalize("NFD", w)
    t = "".join(c for c in t if unicodedata.category(c) != "Mn")
    return "".join(c for c in t.upper() if c.isalpha())


def build_items(sentence):
    """Split the sentence into items: animated word sign OR a run of letters, with spaces."""
    items = []
    words = [w for w in (clean_word(w) for w in sentence.split()) if w]
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


def word_links(sentence):
    """Words of the sentence that have a real ASL sign but no animation here: (word, sign)."""
    seen, out = set(), []
    for w in (clean_word(w) for w in sentence.split()):
        sign = WORD_TO_SIGN.get(w)
        if sign and sign not in gifs and sign not in seen:
            seen.add(sign)
            out.append((w, sign))
    return out


if st.button("Show in sign language", type="primary", use_container_width=True):
    final = text
    st.session_state.t2s_translated = None
    if do_translate and text.strip():
        try:
            from deep_translator import GoogleTranslator
            src, tgt = ("en", "fr") if lang == "English" else ("fr", "en")
            final = GoogleTranslator(source=src, target=tgt).translate(text)
            st.session_state.t2s_translated = final
        except Exception:
            st.warning("Translation is unavailable right now: showing the original text.")
    items = build_items(final)
    if not items:
        st.info("Nothing to sign yet: type a few words.")
    else:
        st.session_state.t2s_items = items
        st.session_state.t2s_words = word_links(final)
        st.session_state.t2s_idx = 0
        st.session_state.t2s_ticks = 0
        st.session_state.t2s_playing = True
        st.session_state.t2s_gif = None

items = st.session_state.get("t2s_items")


def _strip_html(items, idx):
    """The sentence as tiles, current item highlighted."""
    out = []
    for i, x in enumerate(items):
        cls = "now" if i == idx else ("done" if i < idx else "")
        if x["type"] == "sign":
            out.append(f'<span class="tile word {cls}">{html.escape(x["disp"])}</span>')
        elif x["type"] == "space":
            out.append('<span class="tile gap"></span>')
        else:
            out.append(f'<span class="tile {cls}">{x["ch"]}</span>')
    return '<div class="tiles sm">' + "".join(out) + "</div>"


def _stage(src, caption):
    """The sign currently shown, at a fixed readable size."""
    inner = (f'<img src="{img_src(src)}" alt="{html.escape(caption)}">' if src
             else '<div class="readout empty">Space</div>')
    st.markdown(f'<div class="panel stage">{inner}<div class="cap">{html.escape(caption)}</div></div>',
                unsafe_allow_html=True)


# ---------------- Player ----------------
if items:
    if st.session_state.get("t2s_translated"):
        st.caption("Translation: " + st.session_state.t2s_translated)

    col_play, col_side = st.columns([1.1, 1], gap="large")

    with col_play:
        @st.fragment(run_every=f"{speed}s")
        def _player():
            idx = min(st.session_state.get("t2s_idx", 0), len(items) - 1)
            it = items[idx]
            if it["type"] == "sign":
                _stage(it["path"], "Sign: " + it["disp"])
                dwell = max(2, round(2.0 / speed))      # word signs stay longer
            elif it["type"] == "space":
                _stage(space_img, "Space")
                dwell = 1
            else:
                _stage(letters_map[it["ch"]], "Letter " + it["ch"])
                dwell = 1

            st.progress((idx + 1) / len(items))
            st.markdown(_strip_html(items, idx), unsafe_allow_html=True)

            if st.session_state.get("t2s_playing", False):
                st.session_state.t2s_ticks = st.session_state.get("t2s_ticks", 0) + 1
                if st.session_state.t2s_ticks >= dwell:
                    st.session_state.t2s_ticks = 0
                    if idx + 1 < len(items):
                        st.session_state.t2s_idx = idx + 1
                    else:
                        st.session_state.t2s_playing = False
        _player()

        links = st.session_state.get("t2s_words") or []
        if links:
            st.markdown('<h3 class="asl-h3" style="margin-top:1rem">Word signs in this sentence</h3>',
                        unsafe_allow_html=True)
            st.caption("These words have their own sign in ASL. They are spelled above; watch the real sign here.")
            for w, sign in links:
                st.markdown(f"- **{w}**: [watch real signers]({sign_video_url(sign)})")

        b1, b2 = st.columns(2)
        if b1.button(("Pause" if st.session_state.get("t2s_playing") else "Play"), use_container_width=True):
            if not st.session_state.get("t2s_playing") and st.session_state.get("t2s_idx", 0) >= len(items) - 1:
                st.session_state.t2s_idx = 0
            st.session_state.t2s_playing = not st.session_state.get("t2s_playing", False)
            st.session_state.t2s_ticks = 0
            st.rerun()
        if b2.button("Restart", use_container_width=True):
            st.session_state.t2s_idx = 0
            st.session_state.t2s_ticks = 0
            st.session_state.t2s_playing = True
            st.rerun()

    with col_side:
        st.markdown('<h3 class="asl-h3">Export</h3>', unsafe_allow_html=True)
        st.caption("Download the sentence as an animated GIF to share it.")
        if st.button("Create GIF", use_container_width=True):
            with st.spinner("Creating the GIF..."):
                from PIL import Image, ImageDraw, ImageSequence

                @st.cache_data(show_spinner=False)
                def _image_bytes(src):
                    if str(src).startswith("http"):
                        req = urllib.request.Request(src, headers={"User-Agent": "asl-sign-agent/1.0"})
                        with urllib.request.urlopen(req, timeout=15) as r:
                            return r.read()
                    with open(src, "rb") as f:
                        return f.read()

                def letter_frame(src, label):
                    canvas = Image.new("RGB", (320, 352), (250, 251, 253))
                    if src:
                        img = Image.open(io.BytesIO(_image_bytes(src))).convert("RGBA")
                        img.thumbnail((300, 300))
                        canvas.paste(img, ((320 - img.width) // 2, (320 - img.height) // 2), img)
                    d = ImageDraw.Draw(canvas)
                    d.rectangle([0, 320, 320, 352], fill=(16, 32, 74))
                    d.text((10, 328), label, fill=(255, 255, 255))
                    return canvas

                frames, durations = [], []
                try:
                    for it in items:
                        if it["type"] == "sign":
                            gif = Image.open(it["path"])
                            for fr in ImageSequence.Iterator(gif):
                                frames.append(fr.convert("RGB").resize((320, 352))); durations.append(80)
                        elif it["type"] == "space":
                            frames.append(letter_frame(space_img, "SPACE"))
                            durations.append(int(speed * 700))
                        else:
                            frames.append(letter_frame(letters_map[it["ch"]], it["ch"]))
                            durations.append(int(speed * 1000))
                    buf = io.BytesIO()
                    frames[0].save(buf, format="GIF", save_all=True, append_images=frames[1:],
                                   duration=durations, loop=0)
                    st.session_state.t2s_gif = buf.getvalue()
                except Exception:
                    st.warning("The sign images could not be loaded, so the GIF was not created. Try again in a moment.")
        if st.session_state.get("t2s_gif"):
            st.image(st.session_state.t2s_gif, width=320)
            st.download_button("Download GIF", st.session_state.t2s_gif,
                               file_name="signs.gif", mime="image/gif", use_container_width=True)
else:
    st.info("Type a sentence, then click Show in sign language.")

note = ("Letters: public-domain drawings from Wikimedia Commons." if uses_remote_images()
        else "Letters: real photos from the ASL Alphabet dataset.")
st.caption("Word signs come first (animations from the Google ASL Signs dataset), other words are "
           "fingerspelled. J and Z involve a movement. " + note)
