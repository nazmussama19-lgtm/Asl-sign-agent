"""The NumPy forward pass used to export the web models must match Keras exactly.
Skipped when TensorFlow or h5py is not installed (the dedicated CI job installs both)."""
import os, sys
import numpy as np
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
tf = pytest.importorskip("tensorflow")
pytest.importorskip("h5py")
from tools.web_models import MODELS, load, forward  # noqa: E402


@pytest.mark.parametrize("name", list(MODELS))
def test_numpy_forward_matches_keras(name):
    model = tf.keras.models.load_model(MODELS[name])
    layers = load(MODELS[name])
    rng = np.random.RandomState(0)
    shape = (63,) if name == "letters" else (32, 126)
    for _ in range(5):
        x = rng.normal(0, 1, shape).astype(np.float32)
        ref = model(x[None, ...], training=False).numpy()[0]
        assert np.allclose(forward(layers, x), ref, atol=1e-5), name
