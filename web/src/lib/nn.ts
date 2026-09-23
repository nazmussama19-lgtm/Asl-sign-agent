// Inference for the two Keras models, in plain TypeScript (no TensorFlow.js).
// Weights come from tools/web_models.py; the forward pass mirrors its NumPy reference,
// which CI checks against Keras itself.

export interface WeightRef { offset: number; shape: number[] }
export interface LayerSpec {
  type: "Dense" | "BatchNormalization" | "Conv1D" | "GRU";
  name: string;
  activation?: string;
  epsilon?: number;
  units?: number;
  return_sequences?: boolean;
  weights: Record<string, WeightRef>;
}
export interface Manifest { layers: LayerSpec[]; floats: number }

interface Layer { spec: LayerSpec; w: Record<string, Float32Array> }

/** A tensor: row-major values with `rows` time steps (1 for plain vectors) of `cols` features. */
interface T { data: Float32Array; rows: number; cols: number }

export class Model {
  private layers: Layer[];

  constructor(manifest: Manifest, weights: Float32Array) {
    this.layers = manifest.layers.map((spec) => {
      const w: Record<string, Float32Array> = {};
      for (const [name, ref] of Object.entries(spec.weights)) {
        const size = ref.shape.reduce((a, b) => a * b, 1);
        w[name] = weights.subarray(ref.offset, ref.offset + size);
      }
      return { spec, w };
    });
  }

  static async load(baseUrl: string, name: string): Promise<Model> {
    const [manifest, buffer] = await Promise.all([
      fetch(`${baseUrl}/${name}.json`).then((r) => r.json() as Promise<Manifest>),
      fetch(`${baseUrl}/${name}.bin`).then((r) => r.arrayBuffer()),
    ]);
    return new Model(manifest, new Float32Array(buffer));
  }

  /** Forward pass for one sample. `input` is (features) or (steps x features), `steps` rows. */
  predict(input: ArrayLike<number>, steps = 1): Float32Array {
    let x: T = { data: Float32Array.from(input), rows: steps, cols: input.length / steps };
    for (const { spec, w } of this.layers) {
      if (spec.type === "Dense") x = dense(x, w.kernel, w.bias, spec.activation!);
      else if (spec.type === "BatchNormalization") x = batchNorm(x, w, spec.epsilon!);
      else if (spec.type === "Conv1D") x = conv1dSame(x, w.kernel, w.bias, spec.weights.kernel.shape, spec.activation!);
      else x = gru(x, w, spec.units!, spec.return_sequences!);
    }
    return x.data;
  }
}

function activate(v: Float32Array, cols: number, name: string): void {
  if (name === "relu") {
    for (let i = 0; i < v.length; i++) if (v[i] < 0) v[i] = 0;
  } else if (name === "softmax") {
    for (let r = 0; r < v.length; r += cols) {
      let max = -Infinity;
      for (let c = 0; c < cols; c++) max = Math.max(max, v[r + c]);
      let sum = 0;
      for (let c = 0; c < cols; c++) { v[r + c] = Math.exp(v[r + c] - max); sum += v[r + c]; }
      for (let c = 0; c < cols; c++) v[r + c] /= sum;
    }
  } else if (name === "tanh") {
    for (let i = 0; i < v.length; i++) v[i] = Math.tanh(v[i]);
  } else if (name !== "linear") {
    throw new Error("unsupported activation " + name);
  }
}

/** out[r] = x[r] @ kernel (cols x units) + bias */
function dense(x: T, kernel: Float32Array, bias: Float32Array, act: string): T {
  const units = bias.length;
  const out = new Float32Array(x.rows * units);
  for (let r = 0; r < x.rows; r++) {
    const o = r * units;
    out.set(bias, o);
    for (let i = 0; i < x.cols; i++) {
      const xi = x.data[r * x.cols + i];
      if (xi === 0) continue;
      const k = i * units;
      for (let u = 0; u < units; u++) out[o + u] += xi * kernel[k + u];
    }
  }
  activate(out, units, act);
  return { data: out, rows: x.rows, cols: units };
}

function batchNorm(x: T, w: Record<string, Float32Array>, eps: number): T {
  const { gamma, beta, moving_mean: mean, moving_variance: variance } = w;
  const out = new Float32Array(x.data.length);
  for (let i = 0; i < out.length; i++) {
    const c = i % x.cols;
    out[i] = ((x.data[i] - mean[c]) / Math.sqrt(variance[c] + eps)) * gamma[c] + beta[c];
  }
  return { data: out, rows: x.rows, cols: x.cols };
}

/** Stride 1, 'same' padding. kernel shape (K, Cin, Cout). */
function conv1dSame(x: T, kernel: Float32Array, bias: Float32Array, shape: number[], act: string): T {
  const [k, cin, cout] = shape;
  const left = Math.floor((k - 1) / 2);
  const out = new Float32Array(x.rows * cout);
  for (let t = 0; t < x.rows; t++) {
    const o = t * cout;
    out.set(bias, o);
    for (let j = 0; j < k; j++) {
      const src = t + j - left;
      if (src < 0 || src >= x.rows) continue;
      for (let i = 0; i < cin; i++) {
        const xi = x.data[src * cin + i];
        if (xi === 0) continue;
        const base = (j * cin + i) * cout;
        for (let u = 0; u < cout; u++) out[o + u] += xi * kernel[base + u];
      }
    }
  }
  activate(out, cout, act);
  return { data: out, rows: x.rows, cols: cout };
}

const sigmoid = (v: number) => 1 / (1 + Math.exp(-v));

/** Keras GRU with reset_after=True; gates are laid out z | r | h. */
function gru(x: T, w: Record<string, Float32Array>, units: number, returnSequences: boolean): T {
  const { kernel: W, recurrent_kernel: U, bias: b } = w;   // b: (2, 3*units) input bias then recurrent bias
  const g = 3 * units;
  let h = new Float32Array(units);
  const seq = returnSequences ? new Float32Array(x.rows * units) : null;
  const xi = new Float32Array(g);
  const hi = new Float32Array(g);
  for (let t = 0; t < x.rows; t++) {
    for (let c = 0; c < g; c++) { xi[c] = b[c]; hi[c] = b[g + c]; }
    for (let i = 0; i < x.cols; i++) {
      const v = x.data[t * x.cols + i];
      if (v === 0) continue;
      const base = i * g;
      for (let c = 0; c < g; c++) xi[c] += v * W[base + c];
    }
    for (let i = 0; i < units; i++) {
      const v = h[i];
      if (v === 0) continue;
      const base = i * g;
      for (let c = 0; c < g; c++) hi[c] += v * U[base + c];
    }
    const next = new Float32Array(units);
    for (let u = 0; u < units; u++) {
      const z = sigmoid(xi[u] + hi[u]);
      const r = sigmoid(xi[units + u] + hi[units + u]);
      const hh = Math.tanh(xi[2 * units + u] + r * hi[2 * units + u]);
      next[u] = z * h[u] + (1 - z) * hh;
    }
    h = next;
    seq?.set(h, t * units);
  }
  return seq ? { data: seq, rows: x.rows, cols: units } : { data: h, rows: 1, cols: units };
}
