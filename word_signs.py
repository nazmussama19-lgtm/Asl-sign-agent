"""Signes-mots : caracteristiques de sequences, reconnaissance GRU et signes personnalises.

IMPORTANT : build_frame_features / resample doivent rester IDENTIQUES a ceux du notebook
d'entrainement (03_entrainement_signes_mots.ipynb). Toute divergence detruit la precision
silencieusement (meme lecon que pour la normalisation des lettres).
"""
import os, json, time, threading
import numpy as np

SEQ_LEN = 32
FRAME_DIM = 126          # main gauche (63) + main droite (63), zeros si absente

def _norm_hand(lm):
    """(21,3) -> (63,) recentre poignet + echelle poignet->base majeur (comme les lettres)."""
    h = lm.astype(np.float32).copy()
    h -= h[0]
    s = np.linalg.norm(h[9, :2])
    if s < 1e-6:
        s = 1e-6
    return (h / s).flatten()

def build_frame_features(left, right):
    """left/right : (21,3) ou None -> (126,)."""
    l = _norm_hand(left) if left is not None else np.zeros(63, dtype=np.float32)
    r = _norm_hand(right) if right is not None else np.zeros(63, dtype=np.float32)
    return np.concatenate([l, r])

def resample_sequence(frames, n=SEQ_LEN):
    """(T,126) -> (n,126) par interpolation lineaire sur l'axe temporel."""
    arr = np.asarray(frames, dtype=np.float32)
    if len(arr) == 0:
        return np.zeros((n, FRAME_DIM), dtype=np.float32)
    if len(arr) == 1:
        return np.repeat(arr, n, axis=0)
    src = np.linspace(0, len(arr) - 1, n)
    lo = np.floor(src).astype(int); hi = np.ceil(src).astype(int)
    w = (src - lo)[:, None]
    return (arr[lo] * (1 - w) + arr[hi] * w).astype(np.float32)

# ---------------- Signes personnalises (aucun reentrainement) ----------------
CUSTOM_PATH = "assets/custom_signs.json"

class CustomSignStore:
    """Templates de sequences enregistres par l'utilisateur ; reconnaissance par
    similarite cosinus sur sequences reechantillonnees. Local, instantane."""
    def __init__(self):
        self.lock = threading.Lock()
        self.templates = {}          # nom -> liste de (32*126,) aplatis
        self._load()

    def _load(self):
        if os.path.exists(CUSTOM_PATH):
            try:
                with open(CUSTOM_PATH) as f:
                    raw = json.load(f)
                self.templates = {k: [np.array(v, dtype=np.float32) for v in lst]
                                  for k, lst in raw.items()}
            except Exception:
                self.templates = {}

    def _save(self):
        os.makedirs("assets", exist_ok=True)
        with open(CUSTOM_PATH, "w") as f:
            json.dump({k: [v.tolist() for v in lst] for k, lst in self.templates.items()}, f)

    def add(self, name, frames):
        seq = resample_sequence(frames).flatten()
        with self.lock:
            self.templates.setdefault(name, []).append(seq)
            self._save()
            return len(self.templates[name])

    def delete(self, name):
        with self.lock:
            self.templates.pop(name, None)
            self._save()

    def names(self):
        with self.lock:
            return {k: len(v) for k, v in self.templates.items()}

    def match(self, frames, threshold=0.86):
        """Retourne (nom, score) si un signe personnalise correspond, sinon (None, score)."""
        q = resample_sequence(frames).flatten()
        qn = np.linalg.norm(q)
        if qn < 1e-6:
            return None, 0.0
        best_name, best = None, -1.0
        with self.lock:
            for name, lst in self.templates.items():
                if len(lst) < 2:      # exiger au moins 2 exemples
                    continue
                for t in lst:
                    tn = np.linalg.norm(t)
                    if tn < 1e-6:
                        continue
                    sim = float(np.dot(q, t) / (qn * tn))
                    if sim > best:
                        best, best_name = sim, name
        if best >= threshold:
            return best_name, best
        return None, best

# ---------------- Reconnaissance GRU (modele entraine sur le dataset) ----------------
class WordSignRecognizer:
    """Charge sign_words_model.h5 + sign_words_labels.json s'ils existent."""
    def __init__(self):
        self.model = None
        self.labels = []
        if os.path.exists("sign_words_model.h5") and os.path.exists("sign_words_labels.json"):
            try:
                import tensorflow as tf
                self.model = tf.keras.models.load_model("sign_words_model.h5")
                with open("sign_words_labels.json") as f:
                    self.labels = json.load(f)
            except Exception:
                self.model = None

    @property
    def available(self):
        return self.model is not None

    def predict(self, frames, threshold=0.70):
        if self.model is None:
            return None, 0.0
        x = resample_sequence(frames)[None, ...]
        pred = self.model.predict(x, verbose=0)[0]
        i = int(np.argmax(pred)); conf = float(pred[i])
        if conf >= threshold:
            return self.labels[i], conf
        return None, conf

# ---------------- Suivi d'episode de geste ----------------
class GestureEpisode:
    """Accumule les frames pendant un mouvement ; restitue la sequence a la fin."""
    def __init__(self, min_frames=12):
        self.min_frames = min_frames
        self.frames = []
        self.active = False

    def step(self, moving, feat):
        """Retourne la sequence terminee (liste de (126,)) ou None."""
        if moving:
            self.active = True
            self.frames.append(feat)
            return None
        if self.active:
            self.active = False
            seq, self.frames = self.frames, []
            if len(seq) >= self.min_frames:
                return seq
        return None


# ---------------- Correspondance texte -> signe (pour Text to Sign hybride) ----------------
SIGN_SYNONYMS = {
    "hello": ["hello", "hi", "bonjour", "salut", "coucou"],
    "thankyou": ["thankyou", "thank", "thanks", "merci"],
    "please": ["please", "stp", "svp"],
    "yes": ["yes", "oui"],
    "no": ["no", "non"],
    "happy": ["happy", "heureux", "heureuse", "content", "contente"],
    "sad": ["sad", "triste"],
    "fine": ["fine", "bien"],
    "bad": ["bad", "mauvais", "mal"],
    "drink": ["drink", "boire", "bois"],
    "water": ["water", "eau"],
    "food": ["food", "eat", "manger", "mange", "nourriture"],
    "like": ["like", "aime", "aimer", "adore"],
    "see": ["see", "voir", "vois"],
    "look": ["look", "regarde", "regarder"],
    "go": ["go", "aller", "va", "vas"],
    "wait": ["wait", "attends", "attendre", "attend"],
    "sleep": ["sleep", "dormir", "dors"],
    "home": ["home", "maison"],
    "now": ["now", "maintenant"],
    "later": ["later", "apres", "plustard"],
    "where": ["where", "ou"],
    "who": ["who", "qui"],
    "why": ["why", "pourquoi"],
}
WORD_TO_SIGN = {}
for _sign, _words in SIGN_SYNONYMS.items():
    for _w in _words:
        WORD_TO_SIGN[_w.upper()] = _sign


# Mot affiche sur le dictionnaire video en ligne (vraies personnes qui signent)
SIGN_VIDEO_WORD = {"thankyou": "thank-you"}   # cas particuliers d'URL

def sign_video_url(sign):
    """Lien vers les videos reelles du signe (dictionnaire SignASL, plusieurs signeurs)."""
    word = SIGN_VIDEO_WORD.get(sign, sign)
    return "https://www.signasl.org/sign/" + word
