import string
import streamlit as st
from ui import (inject_css, app_header, section, find_alphabet_images, get_word_sign_gifs,
                word_sign_labels, uses_remote_images, img_src)
from word_signs import sign_video_url

inject_css()
app_header("ASL Chart", "The 26 letters of the American Sign Language alphabet (fingerspelling).")


def grid(entries, link_label="Watch", extra_class=""):
    """entries: (key, image or None, link) -> responsive grid of sign cards."""
    cards = []
    for key, img, link in entries:
        face = (f'<img src="{img_src(img)}" alt="ASL sign for {key}" loading="lazy">' if img
                else f'<div class="face">{key}</div>')
        cards.append(f'<div class="sign-card">{face}<div class="row"><span class="k">{key if img else ""}</span>'
                     f'<a href="{link}" target="_blank">{link_label}</a></div></div>')
    st.markdown(f'<div class="sign-grid {extra_class}">{"".join(cards)}</div>', unsafe_allow_html=True)


imgs = find_alphabet_images()
grid([(L, imgs[L], sign_video_url(L.lower())) for L in string.ascii_uppercase if L in imgs])

if uses_remote_images():
    st.caption("Drawings: public domain, from Wikimedia Commons (wpclipart.com). J and Z are movements: "
               "the drawing shows the starting pose. Watch opens a video of real signers on SignASL.org.")
else:
    st.caption("Photos from the ASL Alphabet dataset. J and Z are movements: the photo shows a representative "
               "pose. Watch opens a video of real signers on SignASL.org.")

# Word signs the app recognizes: animation when generated locally, otherwise a link to real signers
gifs = get_word_sign_gifs()
words = sorted(set(word_sign_labels()) | set(gifs))
if words:
    section("Word signs", "The whole words this demo recognizes. Watch real people sign each one, then "
            "turn on Word signs in the Sign to Text sidebar to try it.")
    grid([(w.upper(), gifs.get(w), sign_video_url(w)) for w in words],
         link_label="Watch real signers", extra_class="words")
    st.caption("Videos open the SignASL.org dictionary, where several people sign each word. "
               "They are linked, not embedded.")
