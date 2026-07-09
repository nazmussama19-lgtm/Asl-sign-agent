"""Personnalisation few-shot des lettres : « cette lettre ne marche pas chez moi ».

L'utilisateur enregistre ~5 exemples de SA main pour une lettre ; a l'inference,
un plus-proche-voisin sur les landmarks normalises corrige le MLP quand un exemple
personnel est tres proche. Aucun reentrainement, effet immediat, local.
"""
import os, threading
import numpy as np

PERSONAL_PATH = "assets/personal_letters.csv"

class PersonalLetters:
    def __init__(self, distance_threshold=0.32):
        self.lock = threading.Lock()
        self.threshold = distance_threshold
        self.X = np.zeros((0, 63), dtype=np.float32)
        self.y = []
        self._load()

    def _load(self):
        if os.path.exists(PERSONAL_PATH):
            try:
                rows = [l.strip().split(",") for l in open(PERSONAL_PATH) if l.strip()]
                self.y = [r[0] for r in rows]
                self.X = np.array([[float(v) for v in r[1:64]] for r in rows], dtype=np.float32)
            except Exception:
                self.X = np.zeros((0, 63), dtype=np.float32); self.y = []

    def add(self, letter, feats):
        with self.lock:
            self.X = np.vstack([self.X, feats.reshape(1, 63)])
            self.y.append(letter)
            os.makedirs("assets", exist_ok=True)
            with open(PERSONAL_PATH, "a") as f:
                f.write(letter + "," + ",".join(f"{v:.5f}" for v in feats.flatten()) + "\n")
            return sum(1 for l in self.y if l == letter)

    def counts(self):
        with self.lock:
            out = {}
            for l in self.y:
                out[l] = out.get(l, 0) + 1
            return out

    def reset(self):
        with self.lock:
            self.X = np.zeros((0, 63), dtype=np.float32); self.y = []
            if os.path.exists(PERSONAL_PATH):
                os.remove(PERSONAL_PATH)

    def refine(self, feats, mlp_label, mlp_conf):
        """Si un exemple personnel est tres proche, il l'emporte sur le MLP."""
        with self.lock:
            if len(self.y) == 0:
                return mlp_label, mlp_conf, False
            d = np.linalg.norm(self.X - feats.reshape(1, 63), axis=1)
            i = int(np.argmin(d))
            if d[i] <= self.threshold:
                return self.y[i], max(mlp_conf, 0.95), True
        return mlp_label, mlp_conf, False
