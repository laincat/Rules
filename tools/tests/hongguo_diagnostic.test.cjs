const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../../Surge/Advertising/HongGuo.Diagnostic.js"), "utf8");
const endpoint = "https://api5-normal.fqnovel.com/novel/player/video_detail/v1/";
const key = "hongguo.diagnostic.state.v1";
const secret = "SENSITIVE_SENTINEL_do_not_log", scalarSecret = 987654321012345;
const start = Date.UTC(2026, 10, 2), day = 86400000;
let checks = 0;

function run(options = {}) {
  const store = options.store || Object.create(null), logs = [], writes = [], done = [], forbidden = [];
  const now = options.now === undefined ? start : options.now;
  let bodyReads = 0;
  class Clock extends Date { static now() { return now; } }
  const request = { url: options.url === undefined ? endpoint + "?token=" + secret : options.url };
  Object.defineProperty(request, "headers", { get() { forbidden.push("request.headers"); throw Error(secret); } });
  const response = {};
  Object.defineProperty(response, "headers", { get() { forbidden.push("response.headers"); throw Error(secret); } });
  Object.defineProperty(response, "body", {
    get() { bodyReads++; if (options.forbidBody) throw Error(secret); return options.body === undefined ? '{"data":{}}' : options.body; },
    set() { forbidden.push("response.body mutation"); throw Error(secret); }
  });
  const context = {
    Date: Clock, $request: Object.freeze(request), $response: Object.freeze(response),
    $persistentStore: {
      read(k) { assert.equal(k, key); if (options.failRead) throw Error(secret); return Object.hasOwn(store, k) ? store[k] : null; },
      write(value, k) {
        assert.equal(k, key); writes.push(value);
        if (options.throwWrite) throw Error(secret);
        if (options.failWrite) return false;
        store[k] = value;
        return options.truthyWrite ? "true" : true;
      }
    },
    console: { log(line) { if (options.failConsole) throw Error(secret); logs.push(line); } },
    $done(result) { done.push(JSON.stringify(result)); }
  };
  for (const api of ["$httpClient", "$httpAPI", "$notification", "$surge", "fetch", "XMLHttpRequest", "setTimeout"])
    Object.defineProperty(context, api, { get() { forbidden.push(api); throw Error(secret); } });
  vm.runInNewContext(source, context, { timeout: 2000 });
  assert.deepEqual(done, ["{}"], "Every invocation must finish exactly once with an untouched response");
  assert.deepEqual(forbidden, [], "No headers, response mutations, network or other APIs");
  if (options.forbidBody) assert.equal(bodyReads, 0, "Guard must reject before reading the body");
  for (const line of logs) {
    assert(line.length <= 8192);
    assert(!line.includes(secret) && !line.includes(String(scalarSecret)));
    assert(!line.includes("?token") && !line.includes('"value"'));
  }
  for (const saved of writes) {
    assert(saved.length <= 4096);
    for (const raw of [secret, String(scalarSecret), "api5-normal", "/novel/", "enable_insert_ad", "session_token"])
      assert(!saved.includes(raw), "Persistent state must contain only counters, times and structure hashes");
  }
  checks++;
  return { logs, writes, store, bodyReads, entry: logs.length ? JSON.parse(logs[0]) : null };
}

const body = JSON.stringify({ token: secret, data: {
  items: [{ enable_insert_ad: true }, { enable_insert_ad: false }],
  [secret]: { disable_insert_ad: false },
  video_patch_ad_config: { ad_duration: scalarSecret, session_token: secret }
} });
const first = run({ body });
assert.equal(first.logs.length, 1);
assert.equal(first.entry.version, "2026.11.02.1");
assert.equal(first.entry.utc, "2026-11-02T00:00:00.000Z");
assert.equal(first.entry.host, "api5-normal.fqnovel.com");
assert.equal(first.entry.path, "/novel/player/video_detail/v1/");
assert.equal(first.entry.observedParsedResponsesToday, 1);
assert.equal(first.entry.observedTargetFieldHitsToday, 5);
assert.equal(first.entry.observedTargetFieldHitsInResponse, 5);
assert.equal(first.entry.loggedResponsesToday, 1);
assert.deepEqual(first.entry.fields.find(f => f.field === "enable_insert_ad"), {
  path: "$.data.items[].enable_insert_ad", field: "enable_insert_ad", shape: { type: "boolean" }, hits: 2
});
assert(first.entry.fields.some(f => f.field === "disable_insert_ad" && f.path === "$.data.*.disable_insert_ad"));
assert(!first.logs[0].includes("session_token"));

for (const host of ["api3-normal.fqnovel.com", "api5-normal.fqnovel.com", "api3-normal-lq.fqnovel.com", "api5-normal-lq.fqnovel.com"])
  assert.equal(run({ url: `https://${host}/novel/player/video_detail/v1/`, body }).logs.length, 1);
for (const url of [
  "https://api5-normal.fqnovel.com.evil.example/novel/player/video_detail/v1/",
  endpoint.replace("video_detail", "video_model"), endpoint + "extra", endpoint + "#fragment",
  endpoint.replace("https:", "http:"), endpoint.replace("https://", "https://user:password@"),
  endpoint.replace(".com/", ".com:443/"), endpoint + "\n", endpoint + "?token=x\r\n", endpoint + "?q=" + "x".repeat(4100)
]) assert.equal(run({ url, body, forbidBody: true }).logs.length, 0);

for (const bad of ['{"bad":' + secret, " ".repeat(262145), JSON.stringify({ padding: "😀".repeat(70000) }),
  new Uint8Array([1, 2]), "null", "7", '"string"'])
  assert.equal(run({ body: bad }).logs.length, 0);
for (const failure of ["failRead", "failWrite", "throwWrite", "truthyWrite", "failConsole"])
  assert.equal(run({ body, [failure]: true }).logs.length, 0);
for (const corrupt of [secret, "x".repeat(4097), "{}", "null", '{"v":2}', JSON.stringify({ secret })])
  assert.equal(run({ body, store: { [key]: corrupt }, forbidBody: true }).logs.length, 0);
assert.equal(run({ body, now: NaN, forbidBody: true }).logs.length, 0);
assert.equal(run({ body, now: -1, forbidBody: true }).logs.length, 0);

// Values, dynamic object keys, key order and duplicate occurrences do not change a shape fingerprint.
const sameShape = Object.create(null);
const shapeA = JSON.stringify({ data: { items: [{ enable_insert_ad: true }], video_patch_ad_config: { ad_duration: 1, private_a: secret } } });
const shapeB = JSON.stringify({ data: { video_patch_ad_config: { private_b: "different", ad_duration: 99 }, items: [{ enable_insert_ad: false }, { enable_insert_ad: true }] } });
assert.equal(run({ body: shapeA, store: sameShape }).logs.length, 1);
assert.equal(run({ body: shapeB, store: sameShape, now: start + 60000 }).logs.length, 0);
const duplicate = run({ body: shapeB, store: sameShape, now: start + 1800000 });
assert.equal(duplicate.logs.length, 1);
assert.equal(duplicate.entry.fields.find(f => f.field === "enable_insert_ad").hits, 2);
assert.equal(duplicate.entry.observedParsedResponsesToday, 3);
assert.equal(duplicate.entry.observedTargetFieldHitsToday, 11);

// A second allowlisted host is independently useful, but it still shares the global 60-second gate.
const hosts = Object.create(null), otherHost = endpoint.replace("api5-normal", "api3-normal");
assert.equal(run({ body, store: hosts }).logs.length, 1);
assert.equal(run({ body, store: hosts, url: otherHost, now: start + 59999 }).logs.length, 0);
assert.equal(run({ body, store: hosts, url: otherHost, now: start + 60000 }).logs.length, 1);

function variedBody(i) {
  const types = [null, true, 42, "redacted", [], {}];
  return JSON.stringify({ data: { enable_insert_ad: types[i % 6], disable_insert_ad: types[Math.floor(i / 6) % 6] } });
}
const budget = Object.create(null);
for (let i = 0; i < 24; i++) assert.equal(run({ body: variedBody(i), store: budget, now: start + i * 60000 }).logs.length, 1);
const exhausted = run({ body: variedBody(24), store: budget, now: start + 24 * 60000 });
assert.equal(exhausted.logs.length, 0);
let state = JSON.parse(budget[key]);
assert.equal(state.logs, 24); assert.equal(state.responses, 25); assert.equal(state.fieldHits, 50);
assert.equal(state.fingerprints.length, 24);
for (let i = 0; i < 24; i++) {
  const next = run({ body: variedBody(i), store: budget, now: start + day + i * 60000 });
  assert.equal(next.logs.length, 1);
  assert.equal(next.entry.loggedResponsesToday, i + 1);
  assert.equal(next.entry.observedParsedResponsesToday, i + 1);
}
assert.equal(run({ body: variedBody(24), store: budget, now: start + day + 24 * 60000 }).logs.length, 0);

// Midnight resets daily counters, never the global or per-shape cooldown.
const midnight = Object.create(null), late = start + day - 10000;
assert.equal(run({ body: variedBody(0), store: midnight, now: late }).logs.length, 1);
assert.equal(run({ body: variedBody(1), store: midnight, now: late + 20000 }).logs.length, 0);
assert.equal(run({ body: variedBody(1), store: midnight, now: late + 60000 }).logs.length, 1);
assert.equal(run({ body: variedBody(0), store: midnight, now: late + 1799999 }).logs.length, 0);
assert.equal(run({ body: variedBody(0), store: midnight, now: late + 1800000 }).logs.length, 1);
const highWater = midnight[key];
assert.equal(run({ body, store: midnight, now: start, forbidBody: true }).logs.length, 0);
assert.equal(midnight[key], highWater, "A previous day cannot reset a newer day's state");
assert.equal(run({ body: variedBody(2), store: midnight, now: late + 1799999, forbidBody: true }).logs.length, 0);
const recovered = run({ body: variedBody(2), store: midnight, now: late + 1860000 });
assert.equal(recovered.entry.loggedResponsesToday, 3);

// Near-midnight fingerprints are retained without evicting entries still cooling down.
const full = Object.create(null), nearMidnight = start + day - 24 * 60000;
for (let i = 0; i < 24; i++) run({ body: variedBody(i), store: full, now: nearMidnight + i * 60000 });
assert.equal(run({ body: variedBody(24), store: full, now: start + day }).logs.length, 0);
assert.equal(JSON.parse(full[key]).fingerprints.length, 24);
assert.equal(run({ body: variedBody(24), store: full, now: nearMidnight + 1800000 }).logs.length, 1);

// Saturation keeps long-running daily counters small and exact up to their documented ceiling.
state = { v: 1, day: Math.floor(start / day), responses: 999998, fieldHits: 999998, logs: 0, observedAt: start, emittedAt: -1, fingerprints: [] };
const saturated = { [key]: JSON.stringify(state) };
run({ body, store: saturated });
run({ body, store: saturated, now: start + 60000 });
assert.equal(JSON.parse(saturated[key]).responses, 999999);
assert.equal(JSON.parse(saturated[key]).fieldHits, 999999);

let deep = { enable_insert_ad: true };
for (let i = 0; i < 25; i++) deep = { [secret]: deep };
const deepResult = run({ body: JSON.stringify(deep) });
assert.equal(deepResult.entry.truncated, true); assert.deepEqual(deepResult.entry.fields, []);
const wide = Object.fromEntries(Array.from({ length: 130 }, (_, i) => [`private_${i}`, { enable_insert_ad: true }]));
const wideResult = run({ body: JSON.stringify(wide) });
assert.equal(wideResult.entry.truncated, true);
assert.equal(wideResult.entry.fields[0].hits, 128);
const manyNodes = Object.fromEntries(Array.from({ length: 128 }, (_, i) => [`private_${i}`, Array.from({ length: 128 }, () => ({}))]));
assert.equal(run({ body: JSON.stringify(manyNodes) }).entry.truncated, true);
const dense = { data: {}, result: {}, results: {}, detail: {}, details: {}, video_detail: {}, series: {}, items: {} };
for (const outer of Object.values(dense))
  for (const k of ["data", "result", "results", "detail", "details", "video_detail", "series", "items"])
    outer[k] = { video_patch_ad_config: { enable_insert_ad: false, disable_insert_ad: true, ad_duration: scalarSecret, extra: secret } };
const bounded = run({ body: JSON.stringify(dense) });
assert.equal(bounded.entry.truncated, true); assert(bounded.entry.fields.length <= 32);
assert(bounded.logs[0].length <= 8192);
const proto = run({ body: '{"data":{"__proto__":{"disable_insert_ad":false},"constructor":{"enable_insert_ad":true}}}' });
assert(!proto.logs[0].includes("__proto__") && !proto.logs[0].includes("constructor"));
assert.equal(run({ body: '{"account":{"private_name":"hidden"}}' }).entry.fields.length, 0);
assert(!/\$(?:httpClient|httpAPI|notification|surge)\b/.test(source));

console.log(JSON.stringify({
  synthetic_invocations_passed: checks, unchanged_response_done_exactly_once: true,
  privacy_baits_and_invalid_urls_rejected: true, two_utc_day_budgets_and_cooldowns_passed: true,
  duplicate_field_counts_and_fingerprint_stability_passed: true, backwards_clock_and_storage_errors_passed: true,
  bounded_body_traversal_log_and_state_passed: true, network_calls: 0,
  limitation: "Synthetic sequential Node VM checks only. Surge persistence is not atomic; concurrent runs can race counts, cooldowns and high-water state. No iOS/MITM verification."
}));
