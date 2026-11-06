const assert = require("node:assert/strict");
const fs = require("node:fs");
const path = require("node:path");
const vm = require("node:vm");

const source = fs.readFileSync(path.join(__dirname, "../../Surge/Advertising/HongGuo.Diagnostic.js"), "utf8");
const endpoint = "https://api5-normal.fqnovel.com/novel/player/video_detail/v1/";
// Keep the established ad-pool regression matrix; control/background have additional independent tests below.
const baseKey = "hongguo.diagnostic.state.v3";
const key = baseKey + ".schema.ad";
const adEndpoint = "https://ad.zijieapi.com/api/ad/v1/patch/";
const allowedKeys = new Set(["metadata.control", "metadata.ad", "metadata.background", "schema.control", "schema.ad", "issues.control", "issues.ad", "issues.background"].map(k => baseKey + "." + k));
const secret = "SENSITIVE_SENTINEL_do_not_log", scalarSecret = 987654321012345;
const start = Date.UTC(2026, 10, 2), day = 86400000;
let checks = 0;

function run(options = {}) {
  const store = options.store || Object.create(null), logs = [], writes = [], done = [], forbidden = [];
  const now = options.now === undefined ? start : options.now;
  let bodyReads = 0;
  class Clock extends Date { static now() { return now; } }
  const request = { url: options.url === undefined ? adEndpoint + "?token=" + secret : options.url };
  Object.defineProperty(request, "headers", { get() { forbidden.push("request.headers"); throw Error(secret); } });
  const response = { status: options.status === undefined ? 200 : options.status };
  Object.defineProperty(response, "headers", { get() { forbidden.push("response.headers"); throw Error(secret); } });
  Object.defineProperty(response, "body", {
    get() { bodyReads++; if (options.forbidBody) throw Error(secret); return options.body === undefined ? '{"data":{}}' : options.body; },
    set() { forbidden.push("response.body mutation"); throw Error(secret); }
  });
  const context = {
    Date: Clock, $request: Object.freeze(request), $response: Object.freeze(response),
    $persistentStore: {
      read(k) { assert(allowedKeys.has(k)); if (options.failRead) throw Error(secret); return options.staleRead ? null : Object.hasOwn(store, k) ? store[k] : null; },
      write(value, k) {
        assert(allowedKeys.has(k)); writes.push(value);
        if (options.throwWrite) throw Error(secret);
        if (options.failWrite) return false;
        store[k] = value;
        return options.truthyWrite ? "true" : true;
      }
    },
    console: { log(line) { if (options.failConsole) throw Error(secret); logs.push(line); } },
    $done(result) { done.push(JSON.stringify(result)); }
  };
  if (options.requestPhase) delete context.$response;
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
    assert(saved.length <= (options.requestPhase ? 8192 : 4096));
    for (const raw of [secret, String(scalarSecret), "api5-normal", "/novel/", "enable_insert_ad", "session_token"])
      assert(!saved.includes(raw), "Persistent state must contain only counters, times and structure hashes");
  }
  checks++;
  const events = logs.filter(line => JSON.parse(line).result !== "diagnostic-skip");
  const issues = logs.filter(line => JSON.parse(line).result === "diagnostic-skip").map(JSON.parse);
  return { logs: events, issues, writes, store, bodyReads, entry: events.length ? JSON.parse(events[0]) : null };
}

const body = JSON.stringify({ token: secret, data: {
  items: [{ enable_insert_ad: true }, { enable_insert_ad: false }],
  [secret]: { disable_insert_ad: false },
  video_patch_ad_config: { ad_duration: scalarSecret, session_token: secret }
} });
const first = run({ body });
assert.equal(first.logs.length, 1);
assert.equal(first.entry.version, "2026.11.06.2");
assert.equal(first.entry.utc, "2026-11-02T00:00:00.000Z");
assert.equal(first.entry.host, "ad.zijieapi.com");
assert.equal(first.entry.category, "ad-api");
assert.equal(first.entry.phase, "response-schema");
assert(!Object.hasOwn(first.entry, "path"));
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
const hosts = Object.create(null), otherHost = "https://ads3-normal.zijieapi.com/api/ad/v1/patch/";
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


// The same module regex and script classifier must agree on body eligibility.
const moduleText = fs.readFileSync(path.join(__dirname, "../../Surge/Advertising/HongGuo.Diagnostic.sgmodule"), "utf8");
const scriptLines = moduleText.split("\n").filter(line => /^红果诊断-.* = type=/.test(line));
const scriptPattern = phase => new RegExp(scriptLines.find(line => line.includes(`type=http-${phase},`)).match(/,pattern=(.*?),script-path=/)[1]);
const requestPattern = scriptPattern("request"), responsePattern = scriptPattern("response");
const mitm = moduleText.match(/^hostname = %APPEND% (.*)$/m)[1].split(", ");
assert.equal(mitm.length, 27); assert.equal(new Set(mitm).size, 27);
const responseCases = [
  ["https://ad.zijieapi.com/api/ad/v1", "ad-api"],
  ["https://ads.zijieapi.com/api/ad/v1/recall_ads/banner/", "ad-api"],
  ["https://ads3-normal-hl.zijieapi.com/api/ad/v1/byte_union/recall_ads/", "ad-api"],
  ["https://ads5-normal-lq.zijieapi.com/api/ad/splash/novelapp/v15/", "ad-api"],
  ["https://ads5-normal-lf.zijieapi.com/api/ad/splash/stock/realtime/v15/", "ad-api"],
  ["https://ad.zijieapi.com/api/ad/union/sdk/get_ads/", "ad-api"],
  ["https://api3-normal.fqnovel.com/reading/reader/bonus/ad_reward/v5/", "ad-api"],
  ["https://api5-normal-lq.fqnovel.com/reading/commerceapi/ad/delivery_plan/v2/", "ad-api"],
  ["https://ad.zijieapi.com/api/incentive/marketing/done", "ad-api"],
  ["https://webcast.amemv.com/webcast/feed/", "live-api"],
  ["https://webcast-open.amemv.com/room/enter/", "live-api"],
  ["https://webcast-open.douyin.com/webcast/room/enter_preload/", "live-api"],
  ["https://webcast.amemv.com/webcast/room/realtime_status_center/info/", "live-api"],
  ["https://webcast-open.douyin.com/webcast/content_open/feed/", "live-api"],
  ["https://search.amemv.com/aweme/v1/live/search/", "live-search"],
];
for (const [base, category] of responseCases) {
  const url = base + "?token=" + secret;
  assert(responsePattern.test(url)); assert(requestPattern.test(url));
  const result = run({ url, body });
  assert.equal(result.entry.category, category);
  assert.equal(result.entry.phase, "response-schema");
  assert(!result.logs[0].includes(base) && !Object.hasOwn(result.entry, "path"));
  assert.equal(run({ url, body, requestPhase: true, forbidBody: true }).entry.category, category);
  assert(!responsePattern.test(base + "/" + secret));
}
const noBodyCases = [
  ["https://webcast-open.amemv.com/webcast/im/fetch/", "live-message-poll"],
  ["wss://webcast100-ws-open.douyin.com/webcast/im/push/v3/", "live-message-handshake-candidate"],
  ["https://webcast100-ws-c.amemv.com/webcast/im/push/v3/", "live-message-handshake-candidate"],
  ["https://lf3-webcastcdn-tos.douyinstatic.com/" + secret + ".js", "live-asset"],
  ["https://webcast.amemv.com/" + secret + "/private", "other-on-approved-host"],
  ["https://api5-normal.fqnovel.com/account/" + secret, "other-on-approved-host"],
];
for (const [url, category] of noBodyCases) {
  assert(requestPattern.test(url)); assert(!responsePattern.test(url));
  assert.equal(run({ url, forbidBody: true }).logs.length, 0);
  const result = run({ url, requestPhase: true, forbidBody: true });
  assert.equal(result.entry.category, category); assert.equal(result.entry.phase, "request");
  assert.deepEqual(Object.keys(result.entry).sort(), ["category", "endpoint", "host", "loggedRequestsToday", "observedRequestsToday", "phase", "pool", "result", "utc", "version"]);
}
for (const host of mitm) {
  const url = `https://${host}/${secret}?private=${secret}`;
  assert(requestPattern.test(url));
  assert.equal(run({ url, requestPhase: true, forbidBody: true }).logs.length, 1);
  for (const badUrl of [`https://${host}.evil.example/`, `https://user:password@${host}/`, `http://${host}/`]) {
    assert(!requestPattern.test(badUrl));
    assert.equal(run({ url: badUrl, requestPhase: true, forbidBody: true }).logs.length, 0);
  }
}
assert.equal(run({ url: "wss://ad.zijieapi.com/api/ad/v1/", requestPhase: true, forbidBody: true }).logs.length, 0);
// Ad metadata has its own best-effort 48/day budget and 1-second / 1-minute cooldowns.
const metadataStore = Object.create(null), metadataKey = baseKey + ".metadata.ad";
for (let i = 0; i < 48; i++) {
  const result = run({ requestPhase: true, forbidBody: true, store: metadataStore, now: start + i * 300000 });
  assert.equal(result.logs.length, 1); assert.equal(result.entry.loggedRequestsToday, i + 1);
}
assert.equal(run({ requestPhase: true, forbidBody: true, store: metadataStore, now: start + 48 * 300000 }).logs.length, 0);
assert.equal(JSON.parse(metadataStore[metadataKey]).logs, 48);
assert.equal(run({ requestPhase: true, forbidBody: true, store: metadataStore, now: start + day }).entry.loggedRequestsToday, 1);
assert.equal(run({ requestPhase: true, forbidBody: true, store: metadataStore, now: start + day + 500, url: otherHost }).logs.length, 0);
assert.equal(run({ requestPhase: true, forbidBody: true, store: metadataStore, now: start + day + 1000, url: otherHost }).logs.length, 1);
assert.equal(run({ requestPhase: true, forbidBody: true, store: metadataStore, now: start + day + 59999 }).logs.length, 0);
assert.equal(run({ requestPhase: true, forbidBody: true, store: metadataStore, now: start + day + 60000 }).logs.length, 1);
for (const failure of ["failRead", "failWrite", "throwWrite", "truthyWrite", "failConsole"])
  assert.equal(run({ requestPhase: true, forbidBody: true, [failure]: true }).logs.length, 0);
assert.equal(run({ requestPhase: true, forbidBody: true, store: { [metadataKey]: secret } }).logs.length, 0);
// Body/schema records cannot read bodies on unknown/message/media paths, even if invoked directly.
for (const [url] of noBodyCases) assert.equal(run({ url, forbidBody: true, body }).bodyReads, 0);


assert.equal(first.entry.httpStatus, 200);
assert.equal(run({ status: 403 }).entry.httpStatus, 403);
assert.equal(run({ status: secret }).entry.httpStatus, null);
for (const [body, reason] of [["{", "json-parse-failed"], ["null", "json-non-container"],
  [new Uint8Array([1]), "body-not-text"], ["x".repeat(262145), "body-too-large"]])
  assert.equal(run({ body }).issues[0].reason, reason);
for (const [path, endpointLabel] of [["/api/ad/v1/live_cmm/", "ad-live-cmm"], ["/api/ad/v1/patch/", "ad-patch"],
  ["/api/ad/v1/report/feedback/", "ad-feedback"]])
  assert.equal(run({ url: "https://ad.zijieapi.com" + path }).entry.endpoint, endpointLabel);
for (const [path, endpointLabel] of [["/webcast/room/enter/", "live-room-enter"], ["/room/info/", "live-room-info"],
  ["/webcast/openapi/feed/", "live-openapi-feed"]])
  assert.equal(run({ url: "https://webcast.amemv.com" + path }).entry.endpoint, endpointLabel);
const skips = Object.create(null);
run({ body: "{", store: skips });
assert.equal(run({ body: "{", store: skips, now: start + 60000 }).issues.length, 0);
assert.equal(run({ body: "{", store: skips, now: start + 300000 }).issues.length, 1);

// Optional manual summary validates every state field and never echoes unknown state.
const reportSource = fs.readFileSync(path.join(__dirname, "../../Surge/Advertising/HongGuo.Diagnostic.Report.js"), "utf8");
function report(store = {}, now = start) {
  const logs = [], done = [];
  class Clock extends Date { static now() { return now; } }
  const context = { Date: Clock, $persistentStore: { read(k) { return Object.hasOwn(store, k) ? store[k] : null; } },
    console: { log(line) { logs.push(line); } }, $done(result) { done.push(JSON.stringify(result)); } };
  for (const api of ["$request", "$response", "$httpClient", "$httpAPI", "fetch", "$notification"])
    Object.defineProperty(context, api, { get() { throw Error(secret); } });
  vm.runInNewContext(reportSource, context, { timeout: 2000 });
  assert.deepEqual(done, ["{}"]); assert.equal(logs.length, 1); assert(!logs[0].includes(secret));
  checks++;
  return JSON.parse(logs[0]);
}
assert.equal(report().responseSchema.ad.status, "no-observations");
assert.equal(report(first.store).responseSchema.ad.status, "current-utc-day");
assert.equal(report(first.store, start - 1).responseSchema.ad.status, "clock-backwards");
assert.equal(report(first.store, start - 1).responseSchema.ad.logsRemainingToday, null);
assert.equal(report(first.store, start + day).responseSchema.ad.status, "older-utc-day");
for (const corrupt of [secret, "{}", JSON.stringify({ ...JSON.parse(first.store[key]), fingerprints: null }),
  JSON.stringify({ ...JSON.parse(first.store[key]), extra: secret }),
  JSON.stringify({ ...JSON.parse(first.store[key]), fingerprints: [{ hash: secret, at: start }] })])
  assert(["invalid-state", "unavailable"].includes(report({ [key]: corrupt }).responseSchema.ad.status));


// New exact host: the MITM list, both module matchers and the JS allowlist agree.
const runtimeHost = "webcast5-open-lf.douyin.com";
const enter = `https://${runtimeHost}/webcast/room/enter/`, info = `https://${runtimeHost}/webcast/room/info/`;
const asset = "https://lf-webcast-sourcecdn-tos.bytegecko.com/resource.js";
const message = `https://${runtimeHost}/webcast/im/fetch/`;
const unknown = `https://${runtimeHost}/unknown/${secret}`;
const liveStream = `https://${runtimeHost}/video.flv?token=${secret}`;
const sourceHosts = [...source.slice(source.indexOf("const hostGroups ="), source.indexOf("const hostGroup =")).matchAll(/"([a-z0-9.-]+\.[a-z]+)"/g)].map(m => m[1]);
assert.deepEqual([...sourceHosts].sort(), [...mitm].sort());
for (const url of [enter, info, `https://${runtimeHost}/webcast/openapi/feed/`, `https://${runtimeHost}/room/enter_preload/`]) {
  assert(requestPattern.test(url)); assert(responsePattern.test(url));
  assert.equal(run({ url, requestPhase: true, forbidBody: true }).entry.pool, "control");
  assert.equal(run({ url }).entry.pool, "control");
}
for (const url of [message, unknown, liveStream]) {
  assert(requestPattern.test(url)); assert(!responsePattern.test(url));
  assert.equal(run({ url, requestPhase: true, forbidBody: true }).entry.pool, "background");
  assert.equal(run({ url, forbidBody: true }).logs.length, 0);
}
for (const host of [runtimeHost + ".evil.example", "x." + runtimeHost, "webcast6-open-lf.douyin.com", "webcast5-open-hl.douyin.com"]) {
  const url = `https://${host}/webcast/room/enter/`;
  assert(!requestPattern.test(url)); assert(!responsePattern.test(url));
  assert.equal(run({ url, requestPhase: true, forbidBody: true }).logs.length, 0);
  assert.equal(run({ url, forbidBody: true }).logs.length, 0);
}

// Resource/message/unknown/ad observations cannot consume or cool down control requests or schema.
const isolated = Object.create(null);
for (const url of [asset, message, unknown, adEndpoint]) run({ url, requestPhase: true, forbidBody: true, store: isolated });
for (const url of [enter, info, endpoint]) {
  const event = run({ url, requestPhase: true, forbidBody: true, store: isolated });
  assert.equal(event.logs.length, 1, "Distinct control endpoints must log in the same millisecond");
  assert.equal(event.entry.pool, "control");
}
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: isolated, now: start + 4999 }).issues[0].reason, "duplicate-endpoint");
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: isolated, now: start + 5000 }).logs.length, 1);
const isolatedSchemas = Object.create(null);
run({ store: isolatedSchemas }); // Ad response at this same millisecond.
for (const url of [enter, info, endpoint]) assert.equal(run({ url, store: isolatedSchemas }).logs.length, 1);
assert.equal(run({ url: enter, store: isolatedSchemas, now: start + 9999 }).issues[0].reason, "duplicate-shape");
assert.equal(run({ url: enter, store: isolatedSchemas, now: start + 10000 }).logs.length, 1);
// An HTTP status change is a distinct fixed signature, never a user-controlled value.
assert.equal(run({ url: enter, status: 403, store: isolatedSchemas, now: start + 10000 }).logs.length, 1);

const backgroundKey = baseKey + ".metadata.background", controlKey = baseKey + ".metadata.control";
const schemaKey = baseKey + ".schema.control", issueKey = baseKey + ".issues.control";
const exhaustBackground = Object.create(null);
for (let i = 0; i < 48; i++) assert.equal(run({ url: asset, requestPhase: true, forbidBody: true, store: exhaustBackground, now: start + i * 300000 }).logs.length, 1);
assert.equal(run({ url: asset, requestPhase: true, forbidBody: true, store: exhaustBackground, now: start + 48 * 300000 }).issues[0].reason, "daily-budget");
assert.equal(JSON.parse(exhaustBackground[backgroundKey]).logs, 48);
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: exhaustBackground, now: start + 48 * 300000 }).entry.loggedRequestsToday, 1);
assert.equal(run({ url: enter, store: exhaustBackground, now: start + 48 * 300000 }).entry.loggedResponsesToday, 1);
// Bad background state and exhausted/suppressed background issues do not freeze another pool.
const corruptBackground = { [backgroundKey]: secret, [baseKey + ".issues.background"]: secret };
assert.equal(run({ url: asset, requestPhase: true, forbidBody: true, store: corruptBackground }).logs.length, 0);
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: corruptBackground }).logs.length, 1);
const issueIsolation = Object.create(null);
run({ url: asset, requestPhase: true, forbidBody: true, store: issueIsolation });
assert.equal(run({ url: message, requestPhase: true, forbidBody: true, store: issueIsolation }).issues[0].reason, "global-cooldown");
assert.equal(run({ url: enter, body: "{", store: issueIsolation }).issues[0].reason, "json-parse-failed");
assert.equal(run({ body: "{", store: issueIsolation }).issues[0].reason, "json-parse-failed");
assert(Object.hasOwn(issueIsolation, baseKey + ".issues.background"));
assert(Object.hasOwn(issueIsolation, issueKey));
assert(Object.hasOwn(issueIsolation, baseKey + ".issues.ad"));

// Independent control budgets reset across UTC days, but not active per-endpoint cooldowns.
const controlBudget = Object.create(null);
for (let i = 0; i < 96; i++) assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: controlBudget, now: start + i * 5000 }).logs.length, 1);
assert.equal(run({ url: info, requestPhase: true, forbidBody: true, store: controlBudget, now: start + 480000 }).issues[0].reason, "daily-budget");
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: controlBudget, now: start + day }).entry.loggedRequestsToday, 1);
const controlSchemas = Object.create(null);
for (let i = 0; i < 48; i++) assert.equal(run({ url: enter, store: controlSchemas, now: start + i * 10000 }).logs.length, 1);
assert.equal(run({ url: info, store: controlSchemas, now: start + 480000 }).issues[0].reason, "daily-budget");
assert.equal(run({ url: enter, store: controlSchemas, now: start + day }).entry.loggedResponsesToday, 1);
const edge = Object.create(null), edgeStart = start + day - 1000;
run({ url: enter, requestPhase: true, forbidBody: true, store: edge, now: edgeStart });
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: edge, now: edgeStart + 1000 }).issues[0].reason, "duplicate-endpoint");
assert.equal(run({ url: info, requestPhase: true, forbidBody: true, store: edge, now: edgeStart + 1000 }).logs.length, 1);
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: edge, now: edgeStart + 5000 }).logs.length, 1);
assert.equal(run({ url: info, requestPhase: true, forbidBody: true, store: edge, now: edgeStart, }).logs.length, 0);

// Hypothesis fields expose type/hits only. IDs, URL values, query values and chat never appear.
const navNames = ["room", "room_info", "live_info", "live_room", "webcast_info", "jump_info", "jump_type", "navigation", "schema"];
const navBody = JSON.stringify({ data: Object.fromEntries(navNames.map((name, index) => [name,
  index % 2 ? `https://private.example/${secret}?account=${scalarSecret}` : { room_id: scalarSecret, user_id: secret, chat: secret, url: secret }])) });
const navigation = run({ url: enter, body: navBody });
assert.equal(navigation.entry.observedNavigationFieldHitsInResponse, navNames.length);
assert.equal(navigation.entry.fields.length, navNames.length);
for (const field of navigation.entry.fields) {
  assert(navNames.includes(field.field)); assert.equal(field.hits, 1);
  assert.equal(field.candidate, "unverified-live-navigation");
  assert.deepEqual(Object.keys(field.shape), ["type"]);
}
for (const forbidden of ["room_id", "user_id", '"chat"', '"url"', "private.example", String(scalarSecret)])
  assert(!navigation.logs[0].includes(forbidden));
const navStore = Object.create(null);
run({ url: enter, body: navBody, store: navStore });
const changedValues = navBody.replaceAll(secret, "CHANGED_PRIVATE_VALUE").replaceAll(String(scalarSecret), "123456789");
assert.equal(run({ url: enter, body: changedValues, store: navStore, now: start + 1000 }).logs.length, 0, "Value-only changes cannot create a new shape fingerprint");
const repeatedNav = run({ url: enter, body: '{"data":[{"jump_type":1},{"jump_type":2}]}' });
assert.equal(repeatedNav.entry.fields[0].hits, 2); assert.equal(repeatedNav.entry.observedNavigationFieldHitsInResponse, 2);
assert.equal(run({ url: message, body: navBody, forbidBody: true }).logs.length, 0);
assert.equal(run({ url: liveStream, body: navBody, forbidBody: true }).logs.length, 0);

// Known limitation: stale concurrent readers can both emit count=1; no false atomicity guarantee.
const racing = Object.create(null);
const raceA = run({ url: enter, requestPhase: true, forbidBody: true, store: racing, staleRead: true });
const raceB = run({ url: enter, requestPhase: true, forbidBody: true, store: racing, staleRead: true });
assert.deepEqual(raceA.entry, raceB.entry);
assert.equal(raceA.entry.loggedRequestsToday, 1); assert.equal(JSON.parse(racing[controlKey]).responses, 1);
assert.equal(run({ url: enter, requestPhase: true, forbidBody: true, store: racing, now: start + 325 }).issues[0].reason, "duplicate-endpoint");
// No 1-second cross-endpoint gate remains for control, even immediately after that race.
assert.equal(run({ url: info, requestPhase: true, forbidBody: true, store: racing, now: start + 325 }).logs.length, 1);

const splitReport = report({ ...controlBudget, ...controlSchemas, ...exhaustBackground }, start + day);
assert.equal(splitReport.requestMetadata.control.dailyLogLimit, 96);
assert.equal(splitReport.requestMetadata.background.dailyLogLimit, 48);
assert.equal(splitReport.responseSchema.control.dailyLogLimit, 48);
assert.equal(splitReport.responseSchema.ad.dailyLogLimit, 24); // Limits remain visible without observations.
assert.equal(splitReport.skippedDiagnosticSamples.background.dailyLogLimit, 24);
assert.equal(report({ [controlKey]: secret }).requestMetadata.control.status, "unavailable");
assert.equal(report({ [schemaKey]: JSON.stringify({ ...JSON.parse(controlSchemas[schemaKey]), extra: secret }) }).responseSchema.control.status, "invalid-state");

console.log(JSON.stringify({
  synthetic_invocations_passed: checks, unchanged_response_done_exactly_once: true,
  privacy_baits_and_invalid_urls_rejected: true, two_utc_day_budgets_and_cooldowns_passed: true,
  duplicate_field_counts_and_fingerprint_stability_passed: true, backwards_clock_and_storage_errors_passed: true,
  bounded_body_traversal_log_and_state_passed: true, exact_new_host_and_pool_isolation_passed: true,
  navigation_candidates_type_only_and_stale_read_race_documented: true, network_calls: 0,
  limitation: "Synthetic Node VM and stale-read concurrency-model checks only. Surge persistence is not atomic; concurrent runs can race counts, cooldowns and high-water state. No iOS/MITM verification."
}));
