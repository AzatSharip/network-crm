#!/usr/bin/env node
// Keep runtime audit strict; scope one temporary, non-runtime advisory by exact identity.
import { readFileSync } from "node:fs";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { resolve } from "node:path";

const advisory = "https://github.com/advisories/GHSA-fc5q-39xc-vjpf";
const expires = "2026-12-17";

export function assess(
  report,
  lock,
  date = new Date().toISOString().slice(0, 10),
) {
  if (
    report?.error ||
    report?.auditReportVersion !== 2 ||
    !report?.metadata?.vulnerabilities ||
    !report.vulnerabilities ||
    !lock?.packages
  )
    throw new Error("Incomplete audit/lockfile report");
  const findings = report.vulnerabilities;
  const exceptions = [],
    blocked = [];
  function permitted(name, seen = new Set()) {
    if (seen.has(name)) return false;
    const finding = findings[name];
    if (
      !finding ||
      !finding.nodes?.length ||
      !finding.via?.length ||
      date >= expires
    )
      return false;
    if (!finding.nodes.every((node) => lock.packages[node]?.dev === true))
      return false;
    const visited = new Set([...seen, name]);
    return finding.via.every((via) =>
      typeof via === "string"
        ? permitted(via, visited)
        : name === "picomatch" &&
          via.name === "picomatch" &&
          via.url === advisory &&
          finding.nodes.every(
            (node) => lock.packages[node]?.version === "4.0.7",
          ),
    );
  }
  for (const [name, finding] of Object.entries(findings)) {
    if (!["high", "critical"].includes(finding.severity)) continue;
    (permitted(name) ? exceptions : blocked).push(name);
  }
  // Do not accept an empty/partial findings map when summary says blocking findings exist.
  const summaryCount =
    report.metadata.vulnerabilities.high +
    report.metadata.vulnerabilities.critical;
  if (
    !Number.isFinite(summaryCount) ||
    summaryCount !== exceptions.length + blocked.length
  )
    throw new Error("Audit summary and findings disagree");
  return { exceptions, blocked, expires, advisory };
}

function audit(directory, args) {
  const result = spawnSync("npm", ["audit", "--json", ...args], {
    cwd: directory,
    encoding: "utf8",
    timeout: 120000,
  });
  if (result.error || ![0, 1].includes(result.status))
    throw new Error("npm audit execution failed");
  const report = JSON.parse(result.stdout);
  if (
    report.error ||
    report.auditReportVersion !== 2 ||
    !report.metadata?.vulnerabilities
  )
    throw new Error("npm audit returned an error or incomplete report");
  return report;
}

export function main() {
  const directory = fileURLToPath(new URL("../frontend/", import.meta.url));
  const runtime = audit(directory, ["--omit=dev"]);
  if (
    runtime.metadata.vulnerabilities.high ||
    runtime.metadata.vulnerabilities.critical
  )
    throw new Error(
      "Runtime dependency audit has high/critical vulnerabilities",
    );
  const report = audit(directory, []);
  const lock = JSON.parse(
    readFileSync(resolve(directory, "package-lock.json"), "utf8"),
  );
  const result = assess(report, lock);
  console.log(
    JSON.stringify(
      {
        runtime: runtime.metadata.vulnerabilities,
        full: report.metadata.vulnerabilities,
        ...result,
      },
      null,
      2,
    ),
  );
  if (result.blocked.length)
    throw new Error("Unaccepted high/critical dependency findings");
  if (result.exceptions.length)
    console.log(
      "KNOWN BUILD-ONLY RISK, NOT FIXED: exact advisory accepted until " +
        expires +
        "; see docs/SECURITY.md.",
    );
}

if (
  process.argv[1] &&
  resolve(process.argv[1]) === fileURLToPath(import.meta.url)
) {
  try {
    main();
  } catch (error) {
    console.error(error.message);
    process.exitCode = 1;
  }
}
