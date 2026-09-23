// Port of Python's difflib.get_close_matches (SequenceMatcher without junk), so the agent's
// spelling corrections match the Python version exactly. Words are short (< 20 chars), so
// small typed arrays are used instead of maps.

function matchingCharacters(a: string, b: string, b2j: number[][]): number {
  let total = 0;
  const lb = b.length;
  let prev = new Int32Array(lb + 1);
  let next = new Int32Array(lb + 1);
  const queue: number[] = [0, a.length, 0, lb];
  while (queue.length) {
    const bhi = queue.pop()!, blo = queue.pop()!, ahi = queue.pop()!, alo = queue.pop()!;
    // find_longest_match: prev[j + 1] = length of the match ending at a[i - 1], b[j]
    let besti = alo, bestj = blo, bestsize = 0;
    prev.fill(0);
    for (let i = alo; i < ahi; i++) {
      next.fill(0);
      const js = b2j[a.charCodeAt(i)];
      if (js) {
        for (const j of js) {
          if (j < blo) continue;
          if (j >= bhi) break;
          const k = prev[j] + 1;
          next[j + 1] = k;
          if (k > bestsize) { besti = i - k + 1; bestj = j - k + 1; bestsize = k; }
        }
      }
      const tmp = prev; prev = next; next = tmp;
    }
    while (besti > alo && bestj > blo && a[besti - 1] === b[bestj - 1]) { besti--; bestj--; bestsize++; }
    while (besti + bestsize < ahi && bestj + bestsize < bhi && a[besti + bestsize] === b[bestj + bestsize]) bestsize++;
    if (bestsize) {
      total += bestsize;
      if (alo < besti && blo < bestj) queue.push(alo, besti, blo, bestj);
      if (besti + bestsize < ahi && bestj + bestsize < bhi) queue.push(besti + bestsize, ahi, bestj + bestsize, bhi);
    }
  }
  return total;
}

// Character counters shared between calls (reset after use) to avoid large allocations.
const counts = new Int32Array(65536);
const avail = new Int32Array(65536);

/** Best matches of `word` among `possibilities`, like difflib.get_close_matches. */
export function getCloseMatches(word: string, possibilities: string[], n = 3, cutoff = 0.6): string[] {
  const b = word;
  const b2j: number[][] = [];
  for (let j = 0; j < b.length; j++) {
    const c = b.charCodeAt(j);
    (b2j[c] ??= []).push(j);
    counts[c]++;
  }
  const scored: [number, string][] = [];
  for (const a of possibilities) {
    const total = a.length + b.length;
    if (!total) continue;
    if ((2 * Math.min(a.length, b.length)) / total < cutoff) continue;
    // quick_ratio: size of the multiset intersection
    let matches = 0;
    for (let i = 0; i < a.length; i++) {
      const c = a.charCodeAt(i);
      if (avail[c] < counts[c]) { avail[c]++; matches++; }
    }
    for (let i = 0; i < a.length; i++) avail[a.charCodeAt(i)] = 0;
    if ((2 * matches) / total < cutoff) continue;
    const ratio = (2 * matchingCharacters(a, b, b2j)) / total;
    if (ratio >= cutoff) scored.push([ratio, a]);
  }
  for (let j = 0; j < b.length; j++) counts[b.charCodeAt(j)] = 0;
  // heapq.nlargest on (score, word) tuples: highest score first, ties broken by the larger word
  scored.sort((x, y) => (y[0] - x[0]) || (y[1] > x[1] ? 1 : y[1] < x[1] ? -1 : 0));
  return scored.slice(0, n).map(([, w]) => w);
}
