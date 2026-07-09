"""Selectionne et ameliore les meilleures VRAIES photos de signes du dataset.

Pour chaque classe :
1. SELECTION : on note des centaines d'images (luminosite proche de l'ideal, contraste,
   nettete) puis on confirme avec MediaPipe que la main est bien detectee ; on garde la meilleure.
2. AMELIORATION : balance des blancs, contraste local (CLAHE), correction d'exposition,
   nettete douce, recadrage centre sur la main. 100% local et gratuit.
"""
import os, glob
import numpy as np

TARGET_BRIGHTNESS = 135.0

def _score_cheap(img):
    gray = img.mean(axis=2)
    b = gray.mean()
    contrast = gray.std()
    gy, gx = np.gradient(gray)
    sharp = (gx ** 2 + gy ** 2).mean()
    return (-abs(b - TARGET_BRIGHTNESS) * 1.2) + min(contrast, 60) * 0.8 + min(sharp, 400) * 0.05

def _enhance(img_bgr):
    import cv2
    img = img_bgr.astype(np.float32)
    # balance des blancs (gris-monde)
    means = img.reshape(-1, 3).mean(axis=0)
    img *= means.mean() / np.maximum(means, 1e-3)
    img = np.clip(img, 0, 255).astype(np.uint8)
    # contraste local (CLAHE sur la luminance)
    lab = cv2.cvtColor(img, cv2.COLOR_BGR2LAB)
    l, a, b = cv2.split(lab)
    l = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8)).apply(l)
    img = cv2.cvtColor(cv2.merge((l, a, b)), cv2.COLOR_LAB2BGR)
    # exposition vers la cible (gamma)
    mean = img.mean()
    if mean > 1:
        gamma = np.log(TARGET_BRIGHTNESS / 255.0) / np.log(max(mean, 1) / 255.0)
        gamma = float(np.clip(gamma, 0.55, 1.8))
        lut = np.clip(((np.arange(256) / 255.0) ** gamma) * 255.0, 0, 255).astype(np.uint8)
        img = cv2.LUT(img, lut)
    # nettete douce (masque flou)
    blur = cv2.GaussianBlur(img, (0, 0), 1.2)
    img = cv2.addWeighted(img, 1.35, blur, -0.35, 0)
    return img

def _crop_on_hand(img, hands_detector):
    import cv2
    res = hands_detector.process(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    h, w = img.shape[:2]
    if not res.multi_hand_landmarks:
        return img, False
    pts = np.array([[p.x * w, p.y * h] for p in res.multi_hand_landmarks[0].landmark])
    cx, cy = pts.mean(axis=0)
    half = max(pts[:, 0].ptp(), pts[:, 1].ptp()) * 0.72 + 8
    half = min(max(half, 40), min(w, h) / 2)
    x0 = int(np.clip(cx - half, 0, w - 1)); x1 = int(np.clip(cx + half, 1, w))
    y0 = int(np.clip(cy - half, 0, h - 1)); y1 = int(np.clip(cy + half, 1, h))
    side = min(x1 - x0, y1 - y0)
    return img[y0:y0 + side, x0:x0 + side], True

def generate_best_photos(dataset_dir, out_dir, per_class_scan=200, size=480):
    """Genere la meilleure photo amelioree par classe. Retourne {classe: chemin}."""
    import cv2
    import mediapipe as mp
    os.makedirs(out_dir, exist_ok=True)
    hands = mp.solutions.hands.Hands(static_image_mode=True, min_detection_confidence=0.6, max_num_hands=1)
    out = {}
    classes = [d for d in sorted(os.listdir(dataset_dir))
               if os.path.isdir(os.path.join(dataset_dir, d)) and d != "nothing"]
    for label in classes:
        files = sorted(glob.glob(os.path.join(dataset_dir, label, "*.jpg")) +
                       glob.glob(os.path.join(dataset_dir, label, "*.png")))
        if not files:
            continue
        step = max(1, len(files) // per_class_scan)
        sampled = files[::step][:per_class_scan]
        scored = []
        for f in sampled:
            img = cv2.imread(f)
            if img is None:
                continue
            scored.append((_score_cheap(img), f))
        scored.sort(reverse=True)
        chosen = None
        for _, f in scored[:12]:            # confirmer la main sur les 12 meilleures
            img = cv2.imread(f)
            crop, ok = _crop_on_hand(img, hands)
            if ok:
                chosen = crop
                break
        if chosen is None and scored:
            chosen = cv2.imread(scored[0][1])
        if chosen is None:
            continue
        enhanced = _enhance(chosen)
        enhanced = cv2.resize(enhanced, (size, size), interpolation=cv2.INTER_CUBIC)
        path = os.path.join(out_dir, label + ".png")
        cv2.imwrite(path, enhanced)
        out[label] = path
    hands.close()
    return out
