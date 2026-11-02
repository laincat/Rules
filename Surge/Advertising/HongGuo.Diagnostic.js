// Read-only schema diagnostics: no values, credentials, network calls or response edits.
(function () {
  const version = "2026.11.02.1";
  const storeKey = "hongguo.diagnostic.state.v1";
  const dayMs = 86400000, gapMs = 60000, shapeGapMs = 1800000;
  const maxCount = 999999, maxTime = 8640000000000000;
  const limit = { body: 262144, nodes: 5000, depth: 16, children: 128, fields: 32, logs: 24, state: 4096, line: 8192 };
  const targets = new Set([
    "enable_insert_ad", "disable_insert_ad", "insert_ad_rit_type",
    "video_patch_ad_config", "ad_duration", "ad_repeat_info", "chapter_middle_ad_config"
  ]);
  const structural = new Set([
    "data", "result", "results", "detail", "details", "video_detail",
    "video_detail_info", "video_detail_list", "series", "series_info",
    "book_info", "list", "items", "extra", "config", "ad_config"
  ]);
  const integer = (n, lo, hi) => Number.isSafeInteger(n) && n >= lo && n <= hi;
  const type = value => value === null ? "null" : Array.isArray(value) ? "array" : typeof value;
  const label = key => targets.has(key) || structural.has(key) ? key : "*";
  const add = (a, b) => Math.min(maxCount, a + b);

  function bodyFits(body) {
    if (typeof body !== "string" || body.length > limit.body) return false;
    let bytes = 0;
    for (let i = 0; i < body.length; i++) {
      const c = body.charCodeAt(i);
      if (c < 128) bytes++;
      else if (c < 2048) bytes += 2;
      else if (c >= 0xd800 && c <= 0xdbff && i + 1 < body.length &&
        body.charCodeAt(i + 1) >= 0xdc00 && body.charCodeAt(i + 1) <= 0xdfff) { bytes += 4; i++; }
      else bytes += 3;
      if (bytes > limit.body) return false;
    }
    return true;
  }

  function shape(value) {
    const result = { type: type(value) };
    if (Array.isArray(value)) result.itemTypes = Array.from(new Set(value.slice(0, 16).map(type))).sort();
    else if (value !== null && typeof value === "object") {
      const keys = Object.keys(value);
      result.knownFields = keys.filter(k => targets.has(k) || structural.has(k)).sort()
        .map(k => ({ field: k, type: type(value[k]) }));
      result.otherFieldCount = Math.min(maxCount, keys.filter(k => !targets.has(k) && !structural.has(k)).length);
    }
    return result;
  }

  function inspect(parsed) {
    const stack = [{ value: parsed, path: "$", depth: 0 }], found = new Map();
    let visited = 0, fieldHits = 0, truncated = false;
    while (stack.length && visited < limit.nodes) {
      const node = stack.pop(); visited++;
      if (node.value === null || typeof node.value !== "object") continue;
      if (node.depth >= limit.depth) { truncated = true; continue; }
      const array = Array.isArray(node.value);
      const keys = array ? Object.keys(node.value) : Object.keys(node.value).sort();
      if (keys.length > limit.children) truncated = true;
      for (const key of keys.slice(0, limit.children)) {
        const value = node.value[key], path = node.path + (array ? "[]" : "." + label(key));
        if (!array && targets.has(key)) {
          fieldHits = add(fieldHits, 1);
          const finding = { path, field: key, shape: shape(value) }, signature = JSON.stringify(finding);
          if (found.has(signature)) found.get(signature).hits = add(found.get(signature).hits, 1);
          else if (found.size < limit.fields) found.set(signature, Object.assign(finding, { hits: 1 }));
          else truncated = true;
        }
        if (value !== null && typeof value === "object") {
          if (stack.length + visited < limit.nodes) stack.push({ value, path, depth: node.depth + 1 });
          else truncated = true;
        }
      }
    }
    if (stack.length) truncated = true;
    const fields = Array.from(found.entries()).sort((a, b) => a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0).map(x => x[1]);
    const schemas = () => fields.map(f => ({ path: f.path, field: f.field, shape: f.shape }));
    // Reserve room for hit counts and the fixed log envelope; counts do not change the fingerprint.
    while (JSON.stringify(schemas()).length + fields.length * 24 > 6000) { fields.pop(); truncated = true; }
    return { fields, fieldHits, truncated, schema: JSON.stringify({ fields: schemas(), truncated }) };
  }

  function fingerprint(schema) {
    let a = 2166136261, b = 2246822519;
    for (let i = 0; i < schema.length; i++) {
      a = Math.imul(a ^ schema.charCodeAt(i), 16777619);
      b = Math.imul(b ^ schema.charCodeAt(i), 3266489917);
    }
    return (a >>> 0).toString(16).padStart(8, "0") + (b >>> 0).toString(16).padStart(8, "0");
  }

  function readState(raw, now, day) {
    if (raw === null) return { v: 1, day, responses: 0, fieldHits: 0, logs: 0, observedAt: now, emittedAt: -1, fingerprints: [] };
    if (typeof raw !== "string" || raw.length > limit.state) return null;
    const s = JSON.parse(raw);
    if (!s || typeof s !== "object" || s.v !== 1 ||
      Object.keys(s).sort().join() !== "day,emittedAt,fieldHits,fingerprints,logs,observedAt,responses,v" ||
      !integer(s.day, 0, 100000000) || !integer(s.responses, 0, maxCount) ||
      !integer(s.fieldHits, 0, maxCount) || !integer(s.logs, 0, limit.logs) ||
      !integer(s.observedAt, 0, maxTime) || !integer(s.emittedAt, -1, s.observedAt) ||
      Math.floor(s.observedAt / dayMs) !== s.day || !Array.isArray(s.fingerprints) || s.fingerprints.length > limit.logs) return null;
    const seen = new Set();
    for (const item of s.fingerprints) {
      if (!item || typeof item !== "object" || Object.keys(item).sort().join() !== "at,hash" ||
        typeof item.hash !== "string" || !/^[0-9a-f]{16}$/.test(item.hash) ||
        !integer(item.at, 0, s.emittedAt) || seen.has(item.hash)) return null;
      seen.add(item.hash);
    }
    return s;
  }

  try {
    const url = $request.url;
    if (typeof url !== "string" || url.length > 4096 || /[\s\x00-\x1f\x7f]/.test(url)) return;
    const match = /^https:\/\/(api[35]-normal(?:-lq)?\.fqnovel\.com)(\/novel\/player\/video_detail\/v1\/)(?:\?[^#]*)?$/.exec(url);
    if (!match) return;
    const now = Date.now();
    if (!integer(now, 0, maxTime)) return;
    const day = Math.floor(now / dayMs), state = readState($persistentStore.read(storeKey), now, day);
    // A backwards clock must not reset the daily budget or shorten a cooldown.
    if (!state || day < state.day || now < state.observedAt) return;
    const body = $response.body;
    if (!bodyFits(body)) return;
    const parsed = JSON.parse(body);
    if (parsed === null || typeof parsed !== "object") return;
    const observed = inspect(parsed);
    if (day > state.day) { state.day = day; state.responses = 0; state.fieldHits = 0; state.logs = 0; }
    state.observedAt = now;
    state.responses = add(state.responses, 1);
    // Counts cover parsed responses and target fields reached by the bounded traversal, not requests or ads.
    state.fieldHits = add(state.fieldHits, observed.fieldHits);
    state.fingerprints = state.fingerprints.filter(item => now - item.at < shapeGapMs);
    const hash = fingerprint(match[1] + "\n" + observed.schema);
    const eligible = state.logs < limit.logs && (state.emittedAt < 0 || now - state.emittedAt >= gapMs) &&
      state.fingerprints.length < limit.logs && !state.fingerprints.some(item => item.hash === hash);
    let line = null;
    if (eligible) {
      line = JSON.stringify({ version, utc: new Date(now).toISOString(), host: match[1], path: match[2],
        observedParsedResponsesToday: state.responses, observedTargetFieldHitsToday: state.fieldHits,
        loggedResponsesToday: state.logs + 1, observedTargetFieldHitsInResponse: observed.fieldHits,
        fields: observed.fields, truncated: observed.truncated });
      if (line.length > limit.line) line = null;
      else { state.logs++; state.emittedAt = now; state.fingerprints.push({ hash, at: now }); }
    }
    const saved = JSON.stringify(state);
    if (saved.length > limit.state || $persistentStore.write(saved, storeKey) !== true) return;
    // shortcut: Surge storage has no compare-and-swap; concurrent runs can race these best-effort limits.
    if (line !== null) console.log(line);
  } catch (_) {
    // Never echo parse/storage errors, which may contain response or account data.
  } finally {
    $done({});
  }
})();
