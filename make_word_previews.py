"""Genere des animations (GIF) des signes-mots a partir des landmarks du dataset.

A lancer UNE FOIS apres download_signs_dataset.py :
    python make_word_previews.py
Sortie : assets/word_signs_gifs/<signe>.gif (utilises par Text to Sign, la Charte
et la section Apprendre les signes).
"""
import os, glob
import numpy as np

DATA = "data_signs"
OUT = "assets/word_signs_gifs"
SIZE = 320
FPS_MS = 80

CONNECTIONS = [(0,1),(1,2),(2,3),(3,4),(0,5),(5,6),(6,7),(7,8),(5,9),(9,10),(10,11),(11,12),
               (9,13),(13,14),(14,15),(15,16),(13,17),(17,18),(18,19),(19,20),(0,17)]
INDIGO = (91, 75, 230); CYAN = (6, 182, 212); DARK = (20, 21, 43); BG = (247, 248, 253)

def load_hands(path):
    import pandas as pd
    df = pd.read_parquet(path, columns=["frame", "type", "landmark_index", "x", "y"])
    df = df[df["type"].isin(["left_hand", "right_hand"])]
    frames = []
    for _, g in df.groupby("frame"):
        hands = {}
        for t, gg in g.groupby("type"):
            arr = gg.sort_values("landmark_index")[["x", "y"]].to_numpy(dtype=np.float32)
            if len(arr) == 21 and not np.isnan(arr).all():
                hands[t] = np.nan_to_num(arr, nan=0.0)
        frames.append(hands)
    return frames

def score_sequence(frames):
    if not (14 <= len(frames) <= 70):
        return -1
    return sum(1 for h in frames if h) / max(len(frames), 1)

def render_gif(frames, out_path, label):
    from PIL import Image, ImageDraw
    pts_all = [p for h in frames for arr in h.values() for p in arr]
    if not pts_all:
        return False
    pts_all = np.array(pts_all)
    mn, mx = pts_all.min(axis=0), pts_all.max(axis=0)
    span = float(max(mx[0] - mn[0], mx[1] - mn[1], 1e-4))
    scale = SIZE * 0.72 / span
    off = (SIZE - (mx - mn) * scale) / 2.0

    imgs = []
    for hands in frames:
        img = Image.new("RGB", (SIZE, SIZE + 32), BG)
        d = ImageDraw.Draw(img)
        for arr in hands.values():
            P = (arr - mn) * scale + off
            for a, b in CONNECTIONS:
                d.line([tuple(P[a]), tuple(P[b])], fill=INDIGO, width=7)
            for i, p in enumerate(P):
                r = 6
                fill = CYAN if i in (4, 8, 12, 16, 20) else (255, 255, 255)
                d.ellipse([p[0]-r, p[1]-r, p[0]+r, p[1]+r], fill=fill, outline=INDIGO, width=2)
        d.rectangle([0, SIZE, SIZE, SIZE + 32], fill=DARK)
        d.text((10, SIZE + 8), label.upper(), fill=(255, 255, 255))
        imgs.append(img)
    imgs[0].save(out_path, save_all=True, append_images=imgs[1:], duration=FPS_MS, loop=0)
    return True

def main():
    import pandas as pd
    subset = pd.read_csv(os.path.join(DATA, "subset.csv"))
    os.makedirs(OUT, exist_ok=True)
    for sign, g in subset.groupby("sign"):
        dest = os.path.join(OUT, sign + ".gif")
        if os.path.exists(dest):
            print(sign, ": deja fait"); continue
        best, best_score = None, -1
        for row in g.itertuples():
            p = os.path.join(DATA, "raw", f"{row.sequence_id}.parquet")
            if not os.path.exists(p):
                continue
            fr = load_hands(p)
            s = score_sequence(fr)
            if s > best_score:
                best, best_score = fr, s
        if best and render_gif(best, dest, sign):
            print(sign, f": GIF genere ({len(best)} images, score {best_score:.2f})")
        else:
            print(sign, ": aucune sequence exploitable")
    print("Termine ->", OUT)

if __name__ == "__main__":
    main()
