import os
import numpy as np
import streamlit as st
from ui import inject_css, app_header, get_model

inject_css()
app_header("Resultats et Evaluation", "Performance du modele de reconnaissance, calculee en direct.")

need = ["asl_mediapipe_mlp_model.h5", "labels.json", "asl_mediapipe_keypoints_dataset.csv"]
if not all(os.path.exists(f) for f in need):
    st.error("Fichiers manquants. Copie le modele, labels.json et le CSV des landmarks dans le dossier de l'app (voir README).")
    st.stop()

from asl_core import normalize_landmarks

@st.cache_data(show_spinner=True)
def compute_eval():
    import pandas as pd
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import confusion_matrix, f1_score, accuracy_score
    df = pd.read_csv("asl_mediapipe_keypoints_dataset.csv")
    Xraw = df.iloc[:, :-1].values.astype(np.float32)
    y = df["label"].values
    X = np.array([normalize_landmarks(r.reshape(21, 3)) for r in Xraw], dtype=np.float32)
    enc = LabelEncoder(); yidx = enc.fit_transform(y)
    _, Xte, _, yte = train_test_split(X, yidx, test_size=0.2, random_state=42, stratify=yidx)
    model = get_model()
    pred = np.argmax(model.predict(Xte, verbose=0), axis=1)
    return accuracy_score(yte, pred), confusion_matrix(yte, pred), f1_score(yte, pred, average=None), list(enc.classes_)

with st.spinner("Calcul de l'evaluation (une fois, puis mis en cache)..."):
    acc, cm, f1, classes = compute_eval()

c1, c2, c3 = st.columns(3)
c1.metric("Precision (test)", f"{acc*100:.2f}%")
c2.metric("Nombre de classes", len(classes))
c3.metric("F1 minimum", f"{f1.min():.2f}")

import matplotlib.pyplot as plt
st.markdown("##### Matrice de confusion")
fig1, ax1 = plt.subplots(figsize=(10, 8))
im = ax1.imshow(cm, cmap="Blues"); fig1.colorbar(im, ax=ax1)
ax1.set_xticks(range(len(classes))); ax1.set_xticklabels(classes, rotation=90)
ax1.set_yticks(range(len(classes))); ax1.set_yticklabels(classes)
ax1.set_xlabel("Predit"); ax1.set_ylabel("Reel")
st.pyplot(fig1)

st.markdown("##### F1-score par classe")
order = np.argsort(f1)
fig2, ax2 = plt.subplots(figsize=(10, 4))
ax2.bar([classes[i] for i in order], [f1[i] for i in order], color="#5B4BE6")
ax2.set_ylabel("F1-score"); ax2.set_ylim(0, 1)
plt.setp(ax2.get_xticklabels(), rotation=90)
st.pyplot(fig2)

st.caption("Note : chiffres mesures en distribution. Pour une evaluation realiste, prevoir un test "
           "inter-personnes sur tes propres signes.")
