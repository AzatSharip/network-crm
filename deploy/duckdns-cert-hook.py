#!/usr/bin/env python3
"""Certbot TXT-only hook. Root-owned external config; no A/AAAA writes or secret logging."""

import argparse
import json
import os
import re
import stat
import subprocess
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path


def protected_json(path):
    path = Path(path)
    st = path.stat()
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
        raise RuntimeError("Configuration must be root-owned mode 0600")
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["auth", "cleanup"])
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    cfg = protected_json(args.config)
    hostname, parent = cfg["hostname"], cfg["parent"]
    if not re.fullmatch(r"[a-z0-9-]+\.duckdns\.org", parent) or not re.fullmatch(
        r"[a-z0-9-]+\." + re.escape(parent), hostname
    ):
        raise RuntimeError("Unexpected DNS scope")
    if os.environ.get("CERTBOT_DOMAIN") != hostname:
        raise RuntimeError("Unexpected certificate domain")
    credential = protected_json(cfg["credential_file"])
    if credential.get("domain") != parent:
        raise RuntimeError("Credential domain mismatch")
    validation = os.environ.get("CERTBOT_VALIDATION", "")
    if not re.fullmatch(r"[A-Za-z0-9_-]{20,512}", validation):
        raise RuntimeError("Invalid DNS challenge")

    def visible(resolver):
        result = subprocess.run(
            [
                "dig",
                "+time=3",
                "+tries=1",
                "+short",
                "@" + resolver,
                "_acme-challenge." + hostname,
                "TXT",
            ],
            capture_output=True,
            text=True,
            timeout=5,
            check=True,
        )
        return result.stdout.replace('"', "").splitlines()

    # TXT is shared across the parent in DuckDNS. Certbot's global lock serializes issuance.
    if args.mode == "cleanup" and not all(validation in visible(r) for r in ["1.1.1.1", "8.8.8.8"]):
        print("TXT changed or unavailable; refusing to clear another challenge")
        return
    fields = {
        "domains": parent.removesuffix(".duckdns.org"),
        "token": credential["token"],
        "txt": validation,
    }
    if args.mode == "cleanup":
        fields["clear"] = "true"
    url = "https://www.duckdns.org/update?" + urllib.parse.urlencode(fields)
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
    with opener.open(url, timeout=20) as response:
        if response.read(256).decode().splitlines()[0] != "OK":
            raise RuntimeError("DuckDNS rejected TXT request")
    if args.mode == "auth":
        deadline = time.monotonic() + 240
        while time.monotonic() < deadline:
            if all(validation in visible(r) for r in ["1.1.1.1", "8.8.8.8"]):
                print("TXT challenge verified on both resolvers")
                return
            time.sleep(5)
        raise RuntimeError("TXT propagation timeout")
    print("TXT challenge cleaned")


if __name__ == "__main__":
    try:
        main()
    except Exception:
        print(
            "DNS challenge failed; inspect protected configuration (sensitive URL suppressed)",
            file=sys.stderr,
        )
        raise SystemExit(1) from None
