import string
import streamlit as st
from ui import inject_css, app_header, section, find_alphabet_images, get_word_sign_gifs, uses_remote_images, img_src
from word_signs import sign_video_url

inject_css()
app_header("ASL Chart", "The 26 letters of the American Sign Language alphabet (fingerspelling).")


def grid(entries):
    """entries: (key, image, link) -> responsive grid of sign cards."""
    cards = "".join(
        f'<div class="sign-card"><img src="{img_src(img)}" alt="ASL sign for {key}" loading="lazy">'
        f'<div class="row"><span class="k">{key}</span>'
        f'<a href="{link}" target="_blank">Watch</a></div></div>'
        for key, img, link in entries)
    st.markdown(f'<div class="sign-grid">{cards}</div>', unsafe_allow_html=True)


imgs = find_alphabet_images()
grid([(L, imgs[L], sign_video_url(L.lower())) for L in string.ascii_uppercase if L in imgs])

if uses_remote_images():
    st.caption("Drawings: public domain, from Wikimedia Commons (wpclipart.com). J and Z are movements: "
               "the drawing shows the starting pose. Watch opens a video of real signers on SignASL.org.")
else:
    st.caption("Photos from the ASL Alphabet dataset. J and Z are movements: the photo shows a representative "
               "pose. Watch opens a video of real signers on SignASL.org.")

gifs = get_word_sign_gifs()
if gifs:
    section("Word signs", "Animations built from the landmarks of the Google ASL Signs dataset: copy the movement.")
    grid([(name.upper(), gifs[name], sign_video_url(name)) for name in sorted(gifs)])
