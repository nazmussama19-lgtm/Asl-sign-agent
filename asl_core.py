import threading, time
from collections import deque
import numpy as np

def normalize_landmarks(landmarks):
    lm = landmarks.astype(np.float32).copy()
    lm -= lm[0]
    scale = np.linalg.norm(lm[9, :2])
    if scale < 1e-6:
        scale = 1e-6
    lm /= scale
    return lm.flatten()

class SentenceBuilder:
    def __init__(self, conf_threshold=0.80, stab_window=5, stab_threshold=4, cooldown=0.6):
        self.conf_threshold = conf_threshold
        self.stab_threshold = stab_threshold
        self.cooldown = cooldown
        self.window = deque(maxlen=stab_window)
        self.sentence = ""
        self.committed = None
        self.last_commit = 0.0
        self.lock = threading.Lock()

    def update(self, label, conf):
        with self.lock:
            top = label if conf >= self.conf_threshold else "nothing"
            self.window.append(top)
            stable = top if self.window.count(top) >= self.stab_threshold else None
            if stable is not None and stable != self.committed:
                if stable == "nothing":
                    self.committed = None
                elif (time.time() - self.last_commit) >= self.cooldown:
                    self._apply(stable)
                    self.committed = stable
                    self.last_commit = time.time()
            return self.sentence

    def commit(self, letter):
        with self.lock:
            if (time.time() - self.last_commit) >= self.cooldown:
                self._apply(letter)
                self.committed = letter
                self.last_commit = time.time()
            return self.sentence

    def _apply(self, token):
        if token == "space":
            self.sentence += " "
        elif token == "del":
            self.sentence = self.sentence[:-1]
        elif token == "nothing":
            pass
        else:
            self.sentence += token

    def commit_word(self, word):
        """Ajoute un mot entier (signe-mot reconnu) suivi d'un espace."""
        with self.lock:
            if self.sentence and not self.sentence.endswith(" "):
                self.sentence += " "
            self.sentence += word.upper() + " "
            self.committed = None
            self.last_commit = time.time()

    def accept_word(self, word):
        """Remplace le mot en cours par la suggestion acceptee (pouce leve) + espace."""
        with self.lock:
            parts = self.sentence.split(" ")
            parts[-1] = word
            self.sentence = " ".join(parts) + " "
            self.committed = None
            self.last_commit = time.time()

    def add_space(self):
        with self.lock: self.sentence += " "
    def delete(self):
        with self.lock: self.sentence = self.sentence[:-1]
    def clear(self):
        with self.lock:
            self.sentence = ""
            self.committed = None
    def get(self):
        with self.lock: return self.sentence

class DynamicDetector:
    """Detection de J et Z par mouvement, avec PORTE DE POSE (strategie la plus fiable) :
    - J : le geste doit partir de la pose 'I' (auriculaire leve), trajet de l'auriculaire dominant.
    - Z : index dominant + au moins 2 changements de direction horizontale (zigzag).
    Pendant tout mouvement, les lettres statiques sont bloquees (anti-parasites)."""

    def __init__(self, move_threshold=0.12, window=8, min_path=0.20):
        self.speed_win = deque(maxlen=window)
        self.move_threshold = move_threshold
        self.min_path = min_path
        self.active = False
        self.prev = None
        self.start_pose = None
        self.path_index = 0.0
        self.path_pinky = 0.0
        self.dir_changes = 0
        self.last_dx_sign = 0

    def update(self, landmarks, current_static_label):
        idx = landmarks[8, :2].astype(np.float32)
        pky = landmarks[20, :2].astype(np.float32)
        moving = False
        letter = None
        if self.prev is not None:
            d_idx = float(np.linalg.norm(idx - self.prev[0]))
            d_pky = float(np.linalg.norm(pky - self.prev[1]))
            self.speed_win.append(max(d_idx, d_pky))
            if sum(self.speed_win) > self.move_threshold:
                moving = True
                if not self.active:
                    self.active = True
                    self.start_pose = current_static_label     # pose juste avant le geste
                    self.path_index = self.path_pinky = 0.0
                    self.dir_changes = 0
                    self.last_dx_sign = 0
                self.path_index += d_idx
                self.path_pinky += d_pky
                dx = float(idx[0] - self.prev[0][0])
                s = 1 if dx > 0.004 else (-1 if dx < -0.004 else 0)
                if s != 0:
                    if self.last_dx_sign != 0 and s != self.last_dx_sign:
                        self.dir_changes += 1
                    self.last_dx_sign = s
            else:
                if self.active:
                    self.active = False
                    total = self.path_index + self.path_pinky
                    if total > self.min_path:
                        if self.start_pose == "I" and self.path_pinky >= 0.6 * self.path_index:
                            letter = "J"
                        elif self.dir_changes >= 2 and self.path_index > self.path_pinky:
                            letter = "Z"
        self.prev = (idx.copy(), pky.copy())
        return moving, letter


def is_thumbs_up(landmarks):
    """Pouce leve : pouce clairement au-dessus, les 4 autres doigts replies.
    landmarks : (21, 3) en coordonnees image (y croit vers le bas)."""
    lm = landmarks
    thumb_up = (lm[4, 1] < lm[3, 1] - 0.02) and (lm[4, 1] < lm[5, 1] - 0.05)
    folded = all(lm[t, 1] > lm[p, 1] for t, p in ((8, 6), (12, 10), (16, 14), (20, 18)))
    return bool(thumb_up and folded)
