"""Tests des modules coeur (sans webcam ni TensorFlow)."""
import os, sys, time
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from asl_core import normalize_landmarks, SentenceBuilder, is_thumbs_up
from agent import interpret, suggest, collapse_repeats
from word_signs import build_frame_features, resample_sequence, CustomSignStore
from personal import PersonalLetters, PERSONAL_PATH
from practice import PracticeEngine, pick_word, load_stats, STATS_PATH, SAMPLES_PATH, LETTERS


def test_normalize_invariances():
    lm = np.random.rand(21, 3).astype(np.float32)
    base = normalize_landmarks(lm)
    shifted = normalize_landmarks(lm + np.array([0.3, -0.2, 0.1], dtype=np.float32))
    scaled = normalize_landmarks(lm * 2.5)
    assert np.allclose(base, shifted, atol=1e-5)      # invariance translation
    assert np.allclose(base, scaled, atol=1e-4)       # invariance echelle
    assert base.shape == (63,)


def test_agent_interpretation():
    cases = {
        "HELLLO": "Hello",
        "HELLOWORLD": "Hello world",
        "THAANKYOU": "Thank you",
        "ILOVE U": "I love you",
        "SEE U TMRW": "See you tomorrow",
        "MERCIBEAUCOUP": "Merci beaucoup",
        "CAVABIEN": "Ca va bien",
    }
    for raw, expected in cases.items():
        out, journal = interpret(raw)
        assert out == expected, f"{raw} -> {out} (attendu {expected})"
        assert journal


def test_agent_helpers():
    assert collapse_repeats("HELLLLO") == "HELLO"
    assert "HELLO" in suggest("HEL")


def test_sentence_builder_space_del():
    b = SentenceBuilder(cooldown=0.0, stab_window=1, stab_threshold=1)
    for tok in ["H", "I", "space", "A", "del"]:
        b.update(tok, 0.99)
        b.committed = None            # forcer des commits successifs pour le test
    assert b.get() == "HI "


def test_thumbs_up_geometry():
    lm = np.zeros((21, 3), dtype=np.float32)
    lm[0] = [0.5, 0.9, 0]; lm[3] = [0.45, 0.65, 0]; lm[4] = [0.45, 0.5, 0]; lm[5] = [0.5, 0.7, 0]
    for t, p in ((8, 6), (12, 10), (16, 14), (20, 18)):
        lm[p] = [0.55, 0.75, 0]; lm[t] = [0.55, 0.85, 0]
    assert is_thumbs_up(lm)
    for t, p in ((8, 6), (12, 10), (16, 14), (20, 18)):
        lm[t] = [0.55, 0.55, 0]
    assert not is_thumbs_up(lm)


def test_word_sign_features_and_matching():
    l = np.random.rand(21, 3).astype(np.float32)
    f = build_frame_features(l, None)
    assert f.shape == (126,) and np.allclose(f[63:], 0)
    assert resample_sequence([f] * 7).shape == (32, 126)

    rng = np.random.RandomState(0)
    base = rng.rand(20, 126).astype(np.float32)
    store = CustomSignStore()
    store.templates = {
        "A": [resample_sequence(base + rng.normal(0, 0.01, base.shape).astype(np.float32)).flatten()
              for _ in range(2)],
        "B": [resample_sequence(rng.rand(20, 126).astype(np.float32)).flatten() for _ in range(2)],
    }
    name, score = store.match(base)
    assert name == "A" and score > 0.9


def test_personal_letters_override(tmp_path=None):
    if os.path.exists(PERSONAL_PATH):
        os.remove(PERSONAL_PATH)
    pl = PersonalLetters()
    feats = np.random.rand(63).astype(np.float32)
    pl.add("M", feats)
    lab, conf, used = pl.refine(feats + 0.01, "N", 0.5)
    assert lab == "M" and used and conf >= 0.95
    lab2, _, used2 = pl.refine(np.random.rand(63).astype(np.float32) * 5, "N", 0.5)
    assert lab2 == "N" and not used2
    pl.reset()


def test_practice_engine_flow():
    for p in (STATS_PATH, SAMPLES_PATH):
        if os.path.exists(p):
            os.remove(p)
    eng = PracticeEngine()
    eng.new_session(); eng.new_word("HI")
    feats = np.zeros(63, dtype=np.float32)
    for label in ["H", "K", "I"]:
        for _ in range(5):
            eng.update(label, 0.95, feats)
        time.sleep(0.85)
    s = eng.snapshot()
    assert s["completed"] and s["idx"] == 2
    assert s["stats"]["confusion"].get("I>K") == 1
    assert "J" not in LETTERS and "Z" not in LETTERS
    assert pick_word("letters", "fr", "Easy", load_stats()) in LETTERS
    for p in (STATS_PATH, SAMPLES_PATH):
        if os.path.exists(p):
            os.remove(p)


# ---------------- J / Z detection ----------------
from asl_core import DynamicDetector, hand_shape, count_strokes  # noqa: E402


def _hand(extended, dx=0.0, dy=0.0):
    """Synthetic hand: wrist at the bottom, fingers pointing up; `extended` = (index, middle, ring, pinky)."""
    lm = np.zeros((21, 3), dtype=np.float32)
    lm[0] = [0.5, 0.8, 0]
    lm[1:5] = [[0.44, 0.74, 0], [0.40, 0.70, 0], [0.38, 0.66, 0], [0.37, 0.63, 0]]   # thumb, folded aside
    for f, (base, ext) in enumerate(zip((5, 9, 13, 17), extended)):
        x = 0.44 + 0.04 * f
        lm[base] = [x, 0.62, 0]                                   # MCP
        lm[base + 1] = [x, 0.55, 0]                               # PIP
        if ext:
            lm[base + 2], lm[base + 3] = [x, 0.49, 0], [x, 0.43, 0]
        else:                                                     # curled back toward the palm
            lm[base + 2], lm[base + 3] = [x, 0.60, 0], [x, 0.64, 0]
    lm[:, 0] += dx
    lm[:, 1] += dy
    return lm


INDEX, PINKY, OPEN = (True, False, False, False), (False, False, False, True), (True, True, True, True)


def _run(frames, label=None):
    det = DynamicDetector()
    out = None
    for lm in frames + [frames[-1]] * 12:                       # then hold still so the gesture ends
        _, letter = det.update(lm, label)
        out = letter or out
    return out


def _z_path(shape, steps=8):
    pts = []
    for i in range(steps):                                       # top stroke, left to right
        pts.append((i * 0.02, 0.0))
    for i in range(steps):                                       # diagonal, back to the left and down
        pts.append((0.14 - i * 0.02, i * 0.012))
    for i in range(steps):                                       # bottom stroke, left to right
        pts.append((i * 0.02, 0.096))
    return [_hand(shape, dx, dy) for dx, dy in pts]


def test_hand_shapes_and_strokes():
    assert hand_shape(_hand(INDEX)) == "index"
    assert hand_shape(_hand(PINKY)) == "pinky"
    assert hand_shape(_hand(OPEN)) is None
    assert count_strokes([0, 0.1, 0.0, 0.1], 0.04) == 3
    assert count_strokes([0, 0.01, 0.0, 0.012, 0.001], 0.04) == 0      # jitter is not a stroke


def test_z_needs_the_z_shape():
    assert _run(_z_path(INDEX)) == "Z"
    assert _run(_z_path(OPEN)) is None                                  # zigzag with an open hand
    sideways = [_hand(INDEX, i * 0.02, 0) for i in range(12)]           # one stroke only
    assert _run(sideways) is None


def test_j_needs_the_i_pose_and_little_finger():
    hook = [_hand(PINKY, -i * 0.01 * (i > 6), i * 0.02) for i in range(12)]
    assert _run(hook, label="I") == "J"
    assert _run(hook, label="A") is None
