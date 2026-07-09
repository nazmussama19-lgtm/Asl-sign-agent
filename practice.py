"""Moteur du mode entrainement gamifie.

- Defis de mots (FR/EN, 3 difficultes) et drill de lettres ADAPTATIF (les lettres
  faibles de l'utilisateur reviennent plus souvent).
- Validation lettre par lettre en temps reel, score avec multiplicateur de serie,
  vitesse (lettres/minute), statistiques personnelles persistantes.
- COLLECTE INTEGREE : chaque tentative enregistre localement les landmarks normalises
  etiquetes (cible, prediction, succes) -> base pour la personnalisation few-shot et
  l'evaluation inter-personnes. Tout reste sur la machine.
"""
import os, json, time, random, threading
from collections import deque

LETTERS = "ABCDEFGHIKLMNOPQRSTUVWXY"   # sans J/Z (lettres gestuelles, hors perimetre du drill)

WORDS = {
    "en": {
        "Facile":   ["CAT", "DOG", "SUN", "YES", "HI", "LOVE", "GOOD", "FUN", "TOP", "WIN"],
        "Moyen":    ["HELLO", "WORLD", "HAPPY", "MUSIC", "SMILE", "DREAM", "LIGHT", "PEACE", "DANCE", "STORY"],
        "Difficile":["FRIENDS", "MORNING", "AWESOME", "VICTORY", "HARMONY", "STRENGTH", "CREATIVE", "SUNSHINE"],
    },
    "fr": {
        "Facile":   ["CHAT", "AMI", "OUI", "VIE", "ROI", "MER", "FEU", "LUNE", "PAIN", "MAIN"],
        "Moyen":    ["SOLEIL", "BONNE", "MERCI", "AMOUR", "REVER", "DANSE", "MONDE", "COEUR", "SALUT", "MUSIQUE"],
        "Difficile":["VICTOIRE", "COURAGE", "LUMIERE", "SOURIRE", "HARMONIE", "CREATIF", "MONTAGNE", "AVENTURE"],
    },
}

STATS_PATH = "assets/practice_stats.json"
SAMPLES_PATH = "assets/user_samples.csv"

def load_stats():
    if os.path.exists(STATS_PATH):
        try:
            with open(STATS_PATH) as f:
                return json.load(f)
        except Exception:
            pass
    return {"letters": {}, "confusion": {}, "totals": {"words": 0, "best_streak": 0, "samples": 0}}

def reset_stats():
    for p in (STATS_PATH, SAMPLES_PATH):
        if os.path.exists(p):
            os.remove(p)

def pick_word(mode, lang, difficulty, stats):
    """Choisit le prochain defi. Mode lettres = adaptatif (lettres faibles favorisees)."""
    if mode == "letters":
        weights = []
        for L in LETTERS:
            s = stats["letters"].get(L, {"a": 0, "c": 0})
            err_rate = 1.0 - (s["c"] / s["a"]) if s["a"] > 0 else 0.5   # inconnu = a travailler
            weights.append(0.15 + err_rate)                              # jamais zero
        return random.choices(LETTERS, weights=weights, k=1)[0]
    pool = [w for w in WORDS[lang][difficulty] if all(c in LETTERS for c in w)]
    return random.choice(pool)

class PracticeEngine:
    """Recoit les predictions du fil video, valide lettre par lettre, tient le score,
    les stats et la collecte. Thread-safe."""

    def __init__(self):
        self.lock = threading.Lock()
        self.stats = load_stats()
        self.window = deque(maxlen=5)
        self._reset_session()
        self.word = ""
        self.active = False
        self.completed = False
        self._sample_buffer = []

    def _reset_session(self):
        self.idx = 0
        self.score = 0
        self.streak = 0
        self.session_best_streak = 0
        self.session_words = 0
        self.start_t = None
        self.end_t = None
        self.last_decision_t = 0.0
        self.last_event = None      # ("ok"|"err", lettre, t)

    def new_session(self):
        with self.lock:
            self._reset_session()

    def new_word(self, word):
        with self.lock:
            self.word = word
            self.idx = 0
            self.completed = False
            self.active = True
            self.start_t = time.time()
            self.end_t = None
            self.window.clear()

    def update(self, label, conf, feats):
        """Appele a chaque image par le fil video. feats = landmarks normalises (63,)."""
        with self.lock:
            if not self.active or self.completed or not self.word:
                return
            now = time.time()
            top = label if (conf >= 0.75 and label in LETTERS) else "nothing"
            self.window.append(top)
            stable = top if (top != "nothing" and self.window.count(top) >= 4) else None
            if stable is None or (now - self.last_decision_t) < 0.8:
                return

            target = self.word[self.idx]
            st = self.stats["letters"].setdefault(target, {"a": 0, "c": 0})
            st["a"] += 1
            correct = (stable == target)
            if feats is not None:
                self._sample_buffer.append(
                    [f"{v:.5f}" for v in feats] + [target, stable, "1" if correct else "0", f"{now:.0f}"])
            if correct:
                st["c"] += 1
                self.streak += 1
                self.session_best_streak = max(self.session_best_streak, self.streak)
                self.stats["totals"]["best_streak"] = max(self.stats["totals"]["best_streak"], self.streak)
                self.score += 10 + 2 * min(self.streak, 10)     # multiplicateur de serie plafonne
                self.idx += 1
                self.last_event = ("ok", target, now)
                if self.idx >= len(self.word):
                    self.completed = True
                    self.end_t = now
                    self.score += 50                             # bonus de mot
                    self.session_words += 1
                    self.stats["totals"]["words"] += 1
                    self._flush()
            else:
                key = target + ">" + stable
                self.stats["confusion"][key] = self.stats["confusion"].get(key, 0) + 1
                self.streak = 0
                self.last_event = ("err", stable, now)
            self.last_decision_t = now
            self.window.clear()

    def _flush(self):
        """Ecrit stats + echantillons collectes (appele sous verrou)."""
        try:
            os.makedirs("assets", exist_ok=True)
            if self._sample_buffer:
                new = not os.path.exists(SAMPLES_PATH)
                with open(SAMPLES_PATH, "a") as f:
                    if new:
                        f.write(",".join([f"f{i}" for i in range(63)]
                                         + ["target", "predicted", "correct", "ts"]) + "\n")
                    for row in self._sample_buffer:
                        f.write(",".join(row) + "\n")
                self.stats["totals"]["samples"] = self.stats["totals"].get("samples", 0) + len(self._sample_buffer)
                self._sample_buffer = []
            with open(STATS_PATH, "w") as f:
                json.dump(self.stats, f)
        except Exception:
            pass

    def snapshot(self):
        with self.lock:
            elapsed = 0.0
            if self.start_t:
                elapsed = (self.end_t or time.time()) - self.start_t
            lpm = (self.idx / elapsed * 60) if elapsed > 1 else 0.0
            return {
                "word": self.word, "idx": self.idx, "completed": self.completed,
                "active": self.active, "score": self.score, "streak": self.streak,
                "best_streak": self.session_best_streak, "words": self.session_words,
                "elapsed": elapsed, "lpm": lpm, "last_event": self.last_event,
                "stats": {"letters": dict(self.stats["letters"]),
                          "confusion": dict(self.stats["confusion"]),
                          "totals": dict(self.stats["totals"])},
            }
