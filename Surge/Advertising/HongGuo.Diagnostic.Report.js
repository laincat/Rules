// Manual, local-only summary. Never echo raw persistent data or request information.
(function () {
  const version = "2026.11.06.1", dayMs = 86400000, maxTime = 8640000000000000;
  const integer = (n, lo, hi) => Number.isSafeInteger(n) && n >= lo && n <= hi;
  function summary(key, logLimit, sizeLimit, now) {
    try {
      const raw = $persistentStore.read(key);
      if (raw === null) return { status: "no-observations" };
      if (typeof raw !== "string" || raw.length > sizeLimit) return { status: "invalid-state" };
      const s = JSON.parse(raw);
      if (!s || typeof s !== "object" || s.v !== 1 ||
        Object.keys(s).sort().join() !== "day,emittedAt,fieldHits,fingerprints,logs,observedAt,responses,v" ||
        !integer(s.day, 0, 100000000) || !integer(s.observedAt, 0, maxTime) ||
        Math.floor(s.observedAt / dayMs) !== s.day || !integer(s.emittedAt, -1, s.observedAt) ||
        !integer(s.responses, 0, 999999) || !integer(s.fieldHits, 0, 999999) ||
        !integer(s.logs, 0, logLimit) || !Array.isArray(s.fingerprints) || s.fingerprints.length > logLimit) return { status: "invalid-state" };
      const seen = new Set();
      for (const item of s.fingerprints) {
        if (!item || typeof item !== "object" || Object.keys(item).sort().join() !== "at,hash" ||
          typeof item.hash !== "string" || !/^[0-9a-f]{16}$/.test(item.hash) ||
          !integer(item.at, 0, s.emittedAt) || seen.has(item.hash)) return { status: "invalid-state" };
        seen.add(item.hash);
      }
      const currentDay = Math.floor(now / dayMs) === s.day;
      return { status: now < s.observedAt ? "clock-backwards" : currentDay ? "current-utc-day" : "older-utc-day",
        lastObservedUtc: new Date(s.observedAt).toISOString(),
        lastLoggedUtc: s.emittedAt < 0 ? null : new Date(s.emittedAt).toISOString(),
        observedOnRecordedUtcDay: s.responses, targetFieldHitsOnRecordedUtcDay: s.fieldHits,
        loggedOnRecordedUtcDay: s.logs, dailyLogLimit: logLimit,
        logsRemainingToday: now < s.observedAt ? null : currentDay ? logLimit - s.logs : logLimit };
    } catch (_) { return { status: "unavailable" }; }
  }
  try {
    const now = Date.now();
    if (!integer(now, 0, maxTime)) return;
    console.log(JSON.stringify({ version, report: "hongguo-local-summary", generatedUtc: new Date(now).toISOString(),
      requestMetadata: summary("hongguo.diagnostic.state.v2.metadata", 96, 8192, now),
      responseSchema: summary("hongguo.diagnostic.state.v2", 24, 4096, now),
      skippedDiagnosticSamples: summary("hongguo.diagnostic.state.v2.issues", 24, 4096, now),
      note: "Sampled diagnostic counts, not ad counts or full history. Request and schema logs are separate. Disable the diagnostic module after testing." }));
  } catch (_) {
    // Do not echo exceptions or raw state.
  } finally { $done({}); }
})();
