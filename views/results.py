import os
import numpy as np
import streamlit as st
from ui import inject_css, app_header, section, get_model, INK, VIOLET, MUTED, LINE

inject_css()
app_header("Results", "How well the models recognize signs.")

CSV = "asl_mediapipe_keypoints_dataset.csv"

# Test-set report of notebook 01 (71,762 test samples), used when the landmark CSV is not shipped.
REPORT_ACCURACY = 0.9923
REPORT_F1 = {
    "A": 1.00, "B": 1.00, "C": 0.99, "D": 0.99, "E": 0.99, "F": 1.00, "G": 1.00, "H": 1.00,
    "I": 0.98, "J": 0.98, "K": 1.00, "L": 1.00, "M": 0.97, "N": 0.96, "O": 0.99, "P": 0.99,
    "Q": 0.99, "R": 0.99, "S": 0.99, "T": 1.00, "U": 0.99, "V": 0.99, "W": 0.99, "X": 0.99,
    "Y": 1.00, "Z": 0.99, "del": 0.99, "space": 0.99,
}


@st.cache_data(show_spinner=False)
def compute_eval():
    import pandas as pd
    from sklearn.preprocessing import LabelEncoder
    from sklearn.model_selection import train_test_split
    from sklearn.metrics import confusion_matrix, f1_score, accuracy_score
    from asl_core import normalize_landmarks
    df = pd.read_csv(CSV)
    Xraw = df.iloc[:, :-1].values.astype(np.float32)
    y = df["label"].values
    X = np.array([normalize_landmarks(r.reshape(21, 3)) for r in Xraw], dtype=np.float32)
    enc = LabelEncoder(); yidx = enc.fit_transform(y)
    _, Xte, _, yte = train_test_split(X, yidx, test_size=0.2, random_state=42, stratify=yidx)
    pred = np.argmax(get_model().predict(Xte, verbose=0), axis=1)
    return accuracy_score(yte, pred), confusion_matrix(yte, pred), f1_score(yte, pred, average=None), list(enc.classes_)


live = os.path.exists(CSV) and os.path.exists("asl_mediapipe_mlp_model.h5")
if live:
    with st.spinner("Evaluating the model (once, then cached)..."):
        acc, cm, f1, classes = compute_eval()
else:
    acc, cm = REPORT_ACCURACY, None
    classes = list(REPORT_F1)
    f1 = np.array([REPORT_F1[c] for c in classes])

section("Letters (static signs)")
c1, c2, c3 = st.columns(3)
c1.metric("Test accuracy", f"{acc*100:.2f}%")
c2.metric("Classes", len(classes), help="A to Z, plus the space and delete signs.")
c3.metric("Lowest F1-score", f"{f1.min():.2f}", help="Letter: " + classes[int(np.argmin(f1))])
if not live:
    st.caption("Scores from the evaluation in notebook 01 (71,762 test samples). Add the landmark CSV "
               "produced by that notebook to recompute them live, with the confusion matrix.")

import matplotlib.pyplot as plt
plt.rcParams.update({"font.size": 10, "axes.edgecolor": LINE, "axes.labelcolor": INK,
                     "xtick.color": MUTED, "ytick.color": MUTED})

st.markdown('<h3 class="asl-h3" style="margin-top:1.4rem">F1-score by sign</h3>', unsafe_allow_html=True)
order = np.argsort(f1)
fig2, ax2 = plt.subplots(figsize=(10, 3.4))
xs = range(len(order))
ax2.vlines(xs, 0.9, [f1[i] for i in order], color=LINE, linewidth=2)
ax2.scatter(xs, [f1[i] for i in order], color=VIOLET, s=36, zorder=3)
ax2.set_xticks(list(xs)); ax2.set_xticklabels([classes[i] for i in order], rotation=90)
ax2.set_ylim(0.9, 1.005); ax2.set_ylabel("F1-score")
ax2.spines[["top", "right"]].set_visible(False)
st.pyplot(fig2)
st.caption("The axis starts at 0.90 to make the differences visible: every sign scores above 0.95.")

if cm is not None:
    st.markdown('<h3 class="asl-h3" style="margin-top:1.4rem">Confusion matrix</h3>', unsafe_allow_html=True)
    fig1, ax1 = plt.subplots(figsize=(10, 8))
    im = ax1.imshow(cm, cmap="Blues"); fig1.colorbar(im, ax=ax1)
    ax1.set_xticks(range(len(classes))); ax1.set_xticklabels(classes, rotation=90)
    ax1.set_yticks(range(len(classes))); ax1.set_yticklabels(classes)
    ax1.set_xlabel("Predicted"); ax1.set_ylabel("Actual")
    st.pyplot(fig1)

section("Word signs")
st.markdown("Trained on the Google ASL Signs dataset, which covers up to **250 signs**. Evaluated on "
            "**24 signs**, the Conv1D + GRU model reaches **86% accuracy**. This demo ships a lighter "
            "**9-sign** model to keep the app small and fast.")

st.caption("Letter scores are measured on images from the same dataset as training. Accuracy on new "
           "signers, lighting and cameras is usually lower: the Practice mode collects your own "
           "labeled samples to measure it.")
