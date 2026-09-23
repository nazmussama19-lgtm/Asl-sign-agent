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

def _extended(lm, tip, pip):
    """A finger is extended when its tip is clearly farther from the wrist than its middle joint."""
    return np.linalg.norm(lm[tip, :2] - lm[0, :2]) > 1.1 * np.linalg.norm(lm[pip, :2] - lm[0, :2])


def hand_shape(lm):
    """'index' when only the index is extended (Z), 'pinky' when only the little finger is (J), else None."""
    ext = [_extended(lm, t, p) for t, p in ((8, 6), (12, 10), (16, 14), (20, 18))]
    if ext == [True, False, False, False]:
        return "index"
    if ext == [False, False, False, True]:
        return "pinky"
    return None


def count_strokes(xs, min_stroke):
    """Number of back-and-forth strokes along x, ignoring wiggles shorter than min_stroke."""
    strokes, direction, extreme = 0, 0, xs[0] if len(xs) else 0.0
    for x in xs:
        if direction == 0:
            if abs(x - extreme) >= min_stroke:
                direction, strokes, extreme = (1 if x > extreme else -1), 1, x
        elif direction > 0:
            if x > extreme:
                extreme = x
            elif extreme - x >= min_stroke:
                direction, strokes, extreme = -1, strokes + 1, x
        else:
            if x < extreme:
                extreme = x
            elif x - extreme >= min_stroke:
                direction, strokes, extreme = 1, strokes + 1, x
    return strokes


class DynamicDetector:
    """J and Z from motion, checked against the hand shape so that ordinary movements are ignored.
    - J: starts from the I pose, only the little finger extended, the little finger does the moving.
    - Z: only the index extended, three real strokes (right, diagonal, right) and an overall
      downward path, like drawing a Z.
    While the hand moves, static letters are paused (see SentenceBuilder callers)."""

    def __init__(self, move_threshold=0.12, window=8, min_path=0.20, min_stroke=0.04, min_drop=0.03):
        self.speed_win = deque(maxlen=window)
        self.recent = deque(maxlen=window + 1)   # (fingertip, shape) of the last frames: the gesture's start
        self.move_threshold = move_threshold
        self.min_path = min_path
        self.min_stroke = min_stroke
        self.min_drop = min_drop
        self.active = False
        self.prev = None
        self._reset(None)

    def _reset(self, start_pose):
        self.start_pose = start_pose
        self.path_index = self.path_pinky = 0.0
        self.trail = []               # index fingertip positions during the gesture
        self.shapes = []              # hand shape of each frame during the gesture

    def update(self, landmarks, current_static_label):
        idx = landmarks[8, :2].astype(np.float32)
        pky = landmarks[20, :2].astype(np.float32)
        moving = False
        letter = None
        shape = hand_shape(landmarks)
        self.recent.append((idx.copy(), shape))
        if self.prev is not None:
            d_idx = float(np.linalg.norm(idx - self.prev[0]))
            d_pky = float(np.linalg.norm(pky - self.prev[1]))
            self.speed_win.append(max(d_idx, d_pky))
            if sum(self.speed_win) > self.move_threshold:
                moving = True
                if not self.active:
                    self.active = True
                    self._reset(current_static_label)      # pose just before the gesture
                    # motion is only confirmed after a few frames: start the trail where it began
                    self.trail = [p for p, _ in self.recent]
                    self.shapes = [sh for _, sh in self.recent]
                else:
                    self.trail.append(idx.copy())
                    self.shapes.append(shape)
                self.path_index += d_idx
                self.path_pinky += d_pky
            elif self.active:
                self.active = False
                letter = self._decide()
        self.prev = (idx.copy(), pky.copy())
        return moving, letter

    def _decide(self):
        if self.path_index + self.path_pinky <= self.min_path or not self.shapes:
            return None
        share = lambda s: sum(1 for v in self.shapes if v == s) / len(self.shapes)
        if self.start_pose == "I" and share("pinky") >= 0.5 and self.path_pinky >= 0.6 * self.path_index:
            return "J"
        xs = [p[0] for p in self.trail]
        drop = float(self.trail[-1][1] - self.trail[0][1])          # y grows downward
        if (share("index") >= 0.6 and count_strokes(xs, self.min_stroke) >= 3
                and drop >= self.min_drop and self.path_index > self.path_pinky):
            return "Z"
        return None


def is_thumbs_up(landmarks):
    """Pouce leve : pouce clairement au-dessus, les 4 autres doigts replies.
    landmarks : (21, 3) en coordonnees image (y croit vers le bas)."""
    lm = landmarks
    thumb_up = (lm[4, 1] < lm[3, 1] - 0.02) and (lm[4, 1] < lm[5, 1] - 0.05)
    folded = all(lm[t, 1] > lm[p, 1] for t, p in ((8, 6), (12, 10), (16, 14), (20, 18)))
    return bool(thumb_up and folded)
