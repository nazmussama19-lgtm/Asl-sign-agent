"""Export the Keras models for the web demo, with a NumPy forward pass used as the reference.

    python tools/web_models.py            # needs numpy + h5py only (no TensorFlow)

Writes, for each model, web/public/models/<name>.json (layer list + offsets) and <name>.bin
(float32 weights, little endian), plus web/src/lib/__fixtures__/models.json: random inputs and
the NumPy outputs, which the JavaScript tests must reproduce. tests/test_web_models.py checks
the NumPy forward pass against Keras itself when TensorFlow is installed (CI).
"""
import json
import os

import h5py
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODELS = {"letters": "asl_mediapipe_mlp_model.h5", "words": "sign_words_model.h5"}
SKIP = {"InputLayer", "Dropout"}          # no effect at inference


def load(path):
    """Layers of a Sequential .h5 as [{type, name, config, weights: {name: array}}]."""
    f = h5py.File(os.path.join(ROOT, path), "r")
    cfg = json.loads(f.attrs["model_config"])["config"]["layers"]
    layers = []
    for layer in cfg:
        if layer["class_name"] in SKIP:
            continue
        c = layer["config"]
        g = f["model_weights"][c["name"]]
        weights = {}

        def visit(name, obj):
            if isinstance(obj, h5py.Dataset):
                weights[name.split("/")[-1].split(":")[0]] = np.array(obj, dtype=np.float32)
        g.visititems(visit)
        layers.append({"type": layer["class_name"], "name": c["name"], "config": c, "weights": weights})
    return layers


# ---------------- NumPy forward pass (inference mode) ----------------
def _act(x, name):
    if name == "relu":
        return np.maximum(x, 0)
    if name == "softmax":
        e = np.exp(x - x.max(axis=-1, keepdims=True))
        return e / e.sum(axis=-1, keepdims=True)
    if name == "tanh":
        return np.tanh(x)
    if name == "sigmoid":
        return 1 / (1 + np.exp(-x))
    if name == "linear":
        return x
    raise ValueError(name)


def _conv1d_same(x, kernel, bias):
    """x (T, Cin), kernel (K, Cin, Cout), stride 1, 'same' padding."""
    k = kernel.shape[0]
    left = (k - 1) // 2
    xp = np.pad(x, ((left, k - 1 - left), (0, 0)))
    out = np.zeros((x.shape[0], kernel.shape[2]), dtype=np.float32)
    for j in range(k):
        out += xp[j:j + x.shape[0]] @ kernel[j]
    return out + bias


def _gru(x, w, units, return_sequences):
    """Keras GRU, reset_after=True, gate order z, r, h. x (T, Cin)."""
    W, U, b = w["kernel"], w["recurrent_kernel"], w["bias"]
    h = np.zeros(units, dtype=np.float32)
    seq = []
    for t in range(x.shape[0]):
        xi = x[t] @ W + b[0]
        hi = h @ U + b[1]
        z = _act(xi[:units] + hi[:units], "sigmoid")
        r = _act(xi[units:2 * units] + hi[units:2 * units], "sigmoid")
        hh = np.tanh(xi[2 * units:] + r * hi[2 * units:])
        h = z * h + (1 - z) * hh
        seq.append(h)
    return np.stack(seq) if return_sequences else h


def forward(layers, x):
    """One sample: (63,) for letters, (32, 126) for words."""
    x = np.asarray(x, dtype=np.float32)
    for L in layers:
        t, c, w = L["type"], L["config"], L["weights"]
        if t == "Dense":
            x = _act(x @ w["kernel"] + w["bias"], c["activation"])
        elif t == "BatchNormalization":
            x = (x - w["moving_mean"]) / np.sqrt(w["moving_variance"] + c["epsilon"]) * w["gamma"] + w["beta"]
        elif t == "Conv1D":
            x = _act(_conv1d_same(x, w["kernel"], w["bias"]), c["activation"])
        elif t == "GRU":
            x = _gru(x, w, c["units"], c["return_sequences"])
        else:
            raise ValueError("unsupported layer " + t)
    return x


# ---------------- Export ----------------
ORDER = {"Dense": ["kernel", "bias"], "BatchNormalization": ["gamma", "beta", "moving_mean", "moving_variance"],
         "Conv1D": ["kernel", "bias"], "GRU": ["kernel", "recurrent_kernel", "bias"]}


def export(name, layers, out_dir):
    blobs, manifest, offset = [], [], 0
    for L in layers:
        entry = {"type": L["type"], "name": L["name"], "weights": {}}
        for key in ("activation", "epsilon", "units", "return_sequences", "kernel_size"):
            if key in L["config"]:
                entry[key] = L["config"][key]
        for wname in ORDER[L["type"]]:
            arr = np.ascontiguousarray(L["weights"][wname], dtype="<f4")
            entry["weights"][wname] = {"offset": offset, "shape": list(arr.shape)}
            blobs.append(arr.tobytes())
            offset += arr.size
        manifest.append(entry)
    with open(os.path.join(out_dir, name + ".bin"), "wb") as f:
        f.write(b"".join(blobs))
    with open(os.path.join(out_dir, name + ".json"), "w") as f:
        json.dump({"layers": manifest, "floats": offset}, f, indent=1)
    return offset


def main():
    out_dir = os.path.join(ROOT, "web", "public", "models")
    fix_dir = os.path.join(ROOT, "web", "src", "lib", "__fixtures__")
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(fix_dir, exist_ok=True)
    rng = np.random.RandomState(7)
    fixtures = {}
    for name, path in MODELS.items():
        layers = load(path)
        n = export(name, layers, out_dir)
        shape = (63,) if name == "letters" else (32, 126)
        inputs = [rng.normal(0, 1, shape).astype(np.float32).round(5) for _ in range(3)]
        fixtures[name] = [{"input": x.flatten().tolist(),
                           "output": forward(layers, x).round(7).tolist()} for x in inputs]
        print(f"{name}: {len(layers)} layers, {n} weights -> web/public/models/{name}.bin")
    with open(os.path.join(fix_dir, "models.json"), "w") as f:
        json.dump(fixtures, f)
    for src, dst in (("labels.json", "letters_labels.json"), ("sign_words_labels.json", "words_labels.json")):
        with open(os.path.join(ROOT, src)) as fi, open(os.path.join(out_dir, dst), "w") as fo:
            fo.write(fi.read())


if __name__ == "__main__":
    main()
