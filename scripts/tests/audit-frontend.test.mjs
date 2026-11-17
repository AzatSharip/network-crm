import { test } from "node:test";
import assert from "node:assert/strict";
import { assess } from "../audit-frontend.mjs";
const url = "https://github.com/advisories/GHSA-fc5q-39xc-vjpf";
function fixture() {
  return {
    report: {
      auditReportVersion: 2,
      metadata: { vulnerabilities: { high: 2, critical: 0 } },
      vulnerabilities: {
        picomatch: {
          severity: "high",
          nodes: ["node_modules/picomatch"],
          via: [{ name: "picomatch", url }],
        },
        vite: {
          severity: "high",
          nodes: ["node_modules/vite"],
          via: ["picomatch"],
        },
      },
    },
    lock: {
      packages: {
        "node_modules/picomatch": { dev: true, version: "4.0.7" },
        "node_modules/vite": { dev: true, version: "8.3.8" },
      },
    },
  };
}
const date = "2026-11-17";
test("exact build-only advisory and its dependency chain are explicit exceptions", () => {
  const { report, lock } = fixture();
  assert.deepEqual(assess(report, lock, date).exceptions, [
    "picomatch",
    "vite",
  ]);
});
test("a newly introduced advisory remains blocking, even on the same dependency", () => {
  const { report, lock } = fixture();
  report.vulnerabilities.picomatch.via.push({
    name: "picomatch",
    url: "https://github.com/advisories/GHSA-unknown",
  });
  assert.deepEqual(assess(report, lock, date).blocked, ["picomatch", "vite"]);
});
test("runtime promotion or a changed package version cannot reuse the exception", () => {
  for (const change of [{ dev: false }, { version: "4.0.8" }]) {
    const { report, lock } = fixture();
    Object.assign(lock.packages["node_modules/picomatch"], change);
    assert.deepEqual(assess(report, lock, date).blocked, ["picomatch", "vite"]);
  }
});
test("expired exception is blocking", () => {
  const { report, lock } = fixture();
  assert.deepEqual(assess(report, lock, "2026-12-17").blocked, [
    "picomatch",
    "vite",
  ]);
});
test("missing node metadata, cycles and malformed/network-error reports fail closed", () => {
  const { report, lock } = fixture();
  delete lock.packages["node_modules/picomatch"];
  assert.deepEqual(assess(report, lock, date).blocked, ["picomatch", "vite"]);
  report.vulnerabilities.picomatch.via = ["vite"];
  assert.deepEqual(assess(report, lock, date).blocked, ["picomatch", "vite"]);
  assert.throws(() => assess({ error: "network" }, lock, date));
  assert.throws(() => assess({ ...report, vulnerabilities: {} }, lock, date));
});
test("clean report needs no exception", () => {
  assert.deepEqual(
    assess(
      {
        auditReportVersion: 2,
        metadata: { vulnerabilities: { high: 0, critical: 0 } },
        vulnerabilities: {},
      },
      { packages: {} },
      date,
    ).exceptions,
    [],
  );
});
