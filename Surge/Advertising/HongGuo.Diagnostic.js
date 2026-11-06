// Read-only schema diagnostics: no values, credentials, network calls or response edits.
(function () {
  const version = "2026.11.06.1";
  const storeKey = "hongguo.diagnostic.state.v2";
  const dayMs = 86400000, gapMs = 60000, shapeGapMs = 1800000;
  const maxCount = 999999, maxTime = 8640000000000000;
  const limit = { body: 262144, nodes: 5000, depth: 16, children: 128, fields: 32, logs: 24, state: 4096, line: 8192 };
  // Exact hosts from the 7.4.3 IPA report, plus the four previously approved API hosts.
  const hostGroups = {
    fqnovel: ["api3-normal.fqnovel.com", "api5-normal.fqnovel.com", "api3-normal-lq.fqnovel.com", "api5-normal-lq.fqnovel.com"],
    ad: ["ad.zijieapi.com", "ads.zijieapi.com", "ads3-normal.zijieapi.com", "ads5-normal.zijieapi.com",
      "ads3-normal-lf.zijieapi.com", "ads3-normal-hl.zijieapi.com", "ads3-normal-lq.zijieapi.com",
      "ads5-normal-lf.zijieapi.com", "ads5-normal-hl.zijieapi.com", "ads5-normal-lq.zijieapi.com"],
    live: ["webcast.amemv.com", "webcast-open.amemv.com", "webcast-open.douyin.com"],
    search: ["search.amemv.com"],
    websocket: ["webcast100-ws-open.douyin.com", "webcast100-ws-c.amemv.com"],
    asset: ["lf-webcast-gr-sourcecdn.bytegecko.com", "lf-webcast-sourcecdn-tos.bytegecko.com",
      "lf1-webcastcdn-tos.douyinstatic.com", "lf3-webcastcdn-tos.douyinstatic.com",
      "lf6-webcastcdn-tos.douyinstatic.com", "lf9-webcastcdn-tos.douyinstatic.com"]
  };
  const hostGroup = new Map();
  for (const group of Object.keys(hostGroups)) for (const host of hostGroups[group]) hostGroup.set(host, group);

  function classify(url) {
    if (typeof url !== "string" || url.length > 4096 || /[\s\x00-\x1f\x7f]/.test(url)) return null;
    const m = /^(https|wss):\/\/([a-z0-9.-]+)(\/[^?#]*)(?:\?[^#]*)?$/.exec(url);
    if (!m || !hostGroup.has(m[2])) return null;
    const group = hostGroup.get(m[2]), path = m[3];
    if (m[1] === "wss" && group !== "websocket") return null;
    let category = "other-on-approved-host", body = false;
    if (group === "asset") category = "live-asset";
    else if (group === "websocket") category = "live-message-handshake-candidate";
    else if (group === "live" && /^\/webcast\/im(?:\/|$)/.test(path)) category = "live-message-poll";
    else if (group === "fqnovel" && path === "/novel/player/video_detail/v1/") {
      category = "player-detail"; body = true;
    } else if ((group === "ad" || group === "fqnovel") &&
      (/^\/api\/ad\/(?:v1(?:\/(?:recall_ads\/banner|byte_union\/recall_ads|inspire_send|dislike|report(?:\/feedback)?|inspire|banner|aggregate|live_cmm|patch|inspire_preload))?\/?|splash\/(?:novelapp|stock\/realtime)\/v15\/|union\/sdk\/get_ads\/)$/.test(path) ||
      path === "/api/incentive/marketing/done" ||
      /^\/reading\/(?:reader\/bonus\/ad_reward|commerceapi\/ad\/delivery_plan)\/v[0-9]+\/$/.test(path))) {
      category = "ad-api"; body = true;
    } else if (group === "live" && /^\/(?:webcast\/)?(?:feed|openapi\/feed|content_open\/feed|room\/(?:enter|info|enter_preload|realtime_status_center\/info))\/$/.test(path)) {
      category = "live-api"; body = true;
    } else if (group === "search" && path === "/aweme/v1/live/search/") {
      category = "live-search"; body = true;
    }
    let endpoint = category;
    if (category === "ad-api") {
      const labels = new Map([
        ["/api/ad/v1", "ad-root"], ["/api/ad/v1/banner", "ad-banner"],
        ["/api/ad/v1/inspire", "ad-inspire"], ["/api/ad/v1/inspire_send", "ad-inspire-send"],
        ["/api/ad/v1/inspire_preload", "ad-inspire-preload"], ["/api/ad/v1/patch", "ad-patch"],
        ["/api/ad/v1/live_cmm", "ad-live-cmm"], ["/api/ad/v1/aggregate", "ad-aggregate"],
        ["/api/ad/v1/recall_ads/banner", "ad-recall-banner"], ["/api/ad/v1/byte_union/recall_ads", "ad-recall-union"],
        ["/api/ad/v1/dislike", "ad-dislike"], ["/api/ad/v1/report", "ad-report"],
        ["/api/ad/v1/report/feedback", "ad-feedback"], ["/api/ad/splash/novelapp/v15", "ad-splash-novelapp"],
        ["/api/ad/splash/stock/realtime/v15", "ad-splash-stock"], ["/api/ad/union/sdk/get_ads", "ad-sdk"],
        ["/api/incentive/marketing/done", "ad-marketing-done"]
      ]);
      endpoint = labels.get(path.replace(/\/$/, "")) ||
        (/^\/reading\/reader\/bonus\/ad_reward\//.test(path) ? "ad-reward" : "ad-delivery-plan");
    } else if (category === "live-api") {
      const labels = new Map([
        ["/feed/", "live-feed"], ["/openapi/feed/", "live-openapi-feed"], ["/content_open/feed/", "live-content-feed"],
        ["/room/enter/", "live-room-enter"], ["/room/info/", "live-room-info"],
        ["/room/enter_preload/", "live-room-enter-preload"], ["/room/realtime_status_center/info/", "live-room-status"]
      ]);
      endpoint = labels.get(path.replace(/^\/webcast/, "")) || "live-api";
    }
    // Never return a user-controlled raw path or query; all output labels are fixed.
    return { host: m[2], category, endpoint, body };
  }

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

  function readState(raw, now, day, logLimit = limit.logs, stateLimit = limit.state) {
    if (raw === null) return { v: 1, day, responses: 0, fieldHits: 0, logs: 0, observedAt: now, emittedAt: -1, fingerprints: [] };
    if (typeof raw !== "string" || raw.length > stateLimit) return null;
    const s = JSON.parse(raw);
    if (!s || typeof s !== "object" || s.v !== 1 ||
      Object.keys(s).sort().join() !== "day,emittedAt,fieldHits,fingerprints,logs,observedAt,responses,v" ||
      !integer(s.day, 0, 100000000) || !integer(s.responses, 0, maxCount) ||
      !integer(s.fieldHits, 0, maxCount) || !integer(s.logs, 0, logLimit) ||
      !integer(s.observedAt, 0, maxTime) || !integer(s.emittedAt, -1, s.observedAt) ||
      Math.floor(s.observedAt / dayMs) !== s.day || !Array.isArray(s.fingerprints) || s.fingerprints.length > logLimit) return null;
    const seen = new Set();
    for (const item of s.fingerprints) {
      if (!item || typeof item !== "object" || Object.keys(item).sort().join() !== "at,hash" ||
        typeof item.hash !== "string" || !/^[0-9a-f]{16}$/.test(item.hash) ||
        !integer(item.at, 0, s.emittedAt) || seen.has(item.hash)) return null;
      seen.add(item.hash);
    }
    return s;
  }

  function diagnosticSkip(route, now, phase, reason) {
    // Separate, bounded local error/limit samples. Storage failures deliberately remain silent.
    const key = storeKey + ".issues", day = Math.floor(now / dayMs);
    const state = readState($persistentStore.read(key), now, day);
    if (!state || day < state.day || now < state.observedAt) return;
    if (day > state.day) { state.day = day; state.responses = 0; state.fieldHits = 0; state.logs = 0; }
    state.observedAt = now; state.responses = add(state.responses, 1);
    state.fingerprints = state.fingerprints.filter(item => now - item.at < 300000);
    const hash = fingerprint(route.host + "\n" + route.endpoint + "\n" + phase + "\n" + reason);
    const eligible = state.logs < 24 && (state.emittedAt < 0 || now - state.emittedAt >= 60000) &&
      state.fingerprints.length < 24 && !state.fingerprints.some(item => item.hash === hash);
    let line = null;
    if (eligible) {
      line = JSON.stringify({ version, utc: new Date(now).toISOString(), phase, host: route.host,
        category: route.category, endpoint: route.endpoint, result: "diagnostic-skip", reason });
      state.logs++; state.emittedAt = now; state.fingerprints.push({ hash, at: now });
    }
    const saved = JSON.stringify(state);
    if (saved.length > 4096 || $persistentStore.write(saved, key) !== true) return;
    if (line !== null) console.log(line);
  }

  function requestMetadata(route, now) {
    const key = storeKey + ".metadata", day = Math.floor(now / dayMs);
    const state = readState($persistentStore.read(key), now, day, 96, 8192);
    if (!state || day < state.day || now < state.observedAt) return;
    if (day > state.day) { state.day = day; state.responses = 0; state.fieldHits = 0; state.logs = 0; }
    state.observedAt = now; state.responses = add(state.responses, 1);
    state.fingerprints = state.fingerprints.filter(item => now - item.at < 300000);
    const hash = fingerprint(route.host + "\n" + route.endpoint);
    const eligible = state.logs < 96 && (state.emittedAt < 0 || now - state.emittedAt >= 1000) &&
      state.fingerprints.length < 96 && !state.fingerprints.some(item => item.hash === hash);
    let line = null;
    if (eligible) {
      line = JSON.stringify({ version, utc: new Date(now).toISOString(), phase: "request", host: route.host,
        category: route.category, endpoint: route.endpoint, result: "observed-request", observedRequestsToday: state.responses, loggedRequestsToday: state.logs + 1 });
      state.logs++; state.emittedAt = now; state.fingerprints.push({ hash, at: now });
    }
    const saved = JSON.stringify(state);
    if (saved.length > 8192 || $persistentStore.write(saved, key) !== true) return;
    if (line !== null) console.log(line);
    else diagnosticSkip(route, now, "request", state.logs >= 96 ? "daily-budget" :
      now - state.emittedAt < 1000 ? "global-cooldown" : state.fingerprints.length >= 96 ? "cooldown-capacity" : "duplicate-category");
  }

  try {
    const route = classify($request.url);
    if (!route) return;
    const requestPhase = typeof $response === "undefined";
    // Response guards run before accessing any response body, including IM/chat, assets and unknown routes.
    if (!requestPhase && !route.body) return;
    const now = Date.now();
    if (!integer(now, 0, maxTime)) return;
    if (requestPhase) { requestMetadata(route, now); return; }
    const day = Math.floor(now / dayMs), state = readState($persistentStore.read(storeKey), now, day);
    // A backwards clock must not reset the daily budget or shorten a cooldown.
    if (!state || day < state.day || now < state.observedAt) return;
    const body = $response.body;
    if (!bodyFits(body)) { diagnosticSkip(route, now, "response", typeof body !== "string" ? "body-not-text" : "body-too-large"); return; }
    let parsed;
    try { parsed = JSON.parse(body); }
    catch (_) { diagnosticSkip(route, now, "response", "json-parse-failed"); return; }
    if (parsed === null || typeof parsed !== "object") { diagnosticSkip(route, now, "response", "json-non-container"); return; }
    const observed = inspect(parsed);
    if (day > state.day) { state.day = day; state.responses = 0; state.fieldHits = 0; state.logs = 0; }
    state.observedAt = now;
    state.responses = add(state.responses, 1);
    // Counts cover parsed responses and target fields reached by the bounded traversal, not requests or ads.
    state.fieldHits = add(state.fieldHits, observed.fieldHits);
    state.fingerprints = state.fingerprints.filter(item => now - item.at < shapeGapMs);
    const hash = fingerprint(route.host + "\n" + route.endpoint + "\n" + observed.schema);
    const eligible = state.logs < limit.logs && (state.emittedAt < 0 || now - state.emittedAt >= gapMs) &&
      state.fingerprints.length < limit.logs && !state.fingerprints.some(item => item.hash === hash);
    let line = null;
    if (eligible) {
      line = JSON.stringify({ version, utc: new Date(now).toISOString(), phase: "response-schema", host: route.host, category: route.category, endpoint: route.endpoint, result: "parsed-json",
        httpStatus: integer($response.status, 100, 599) ? $response.status : null,
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
    else diagnosticSkip(route, now, "response", state.logs >= limit.logs ? "daily-budget" :
      now - state.emittedAt < gapMs ? "global-cooldown" : state.fingerprints.length >= limit.logs ? "cooldown-capacity" : eligible ? "log-size-limit" : "duplicate-shape");
  } catch (_) {
    // Never echo parse/storage errors, which may contain response or account data.
  } finally {
    $done({});
  }
})();
