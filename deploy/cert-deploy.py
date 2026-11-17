#!/usr/bin/env python3
"""Deploy only this CRM certificate, validating the pair before a graceful reload."""

import argparse
import json
import os
import stat
import subprocess
import tempfile
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", required=True)
    args = parser.parse_args()
    path = Path(args.config)
    st = path.stat()
    if st.st_uid != 0 or stat.S_IMODE(st.st_mode) != 0o600:
        raise RuntimeError("Config must be root-owned mode 0600")
    cfg = json.loads(path.read_text())
    lineage = Path(cfg["lineage"])
    if Path(os.environ.get("RENEWED_LINEAGE", "")) != lineage:
        raise RuntimeError("Unexpected certificate lineage")
    target = Path(cfg["target"])
    if not target.is_absolute() or target.is_symlink() or not target.is_dir():
        raise RuntimeError("Dedicated certificate directory must already exist")

    def run(*args):
        return subprocess.check_output(args, stderr=subprocess.STDOUT)

    run("openssl", "x509", "-in", str(lineage / "cert.pem"), "-noout", "-checkend", "604800")
    run(
        "openssl",
        "verify",
        "-verify_hostname",
        cfg["hostname"],
        "-CApath",
        "/etc/ssl/certs",
        "-untrusted",
        str(lineage / "chain.pem"),
        str(lineage / "cert.pem"),
    )
    if run("openssl", "x509", "-in", str(lineage / "cert.pem"), "-pubkey", "-noout") != run(
        "openssl", "pkey", "-in", str(lineage / "privkey.pem"), "-pubout"
    ):
        raise RuntimeError("Certificate/key mismatch")
    names = ("fullchain.pem", "privkey.pem")
    old = {n: (target / n).read_bytes() if (target / n).exists() else None for n in names}

    def write(name, data):
        fd, temp = tempfile.mkstemp(prefix=".crm-cert-", dir=target)
        try:
            os.fchmod(fd, 0o600 if name == "privkey.pem" else 0o644)
            os.fchown(fd, 101, 101)
            with os.fdopen(fd, "wb") as stream:
                stream.write(data)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp, target / name)
        finally:
            Path(temp).unlink(missing_ok=True)

    try:
        for name in names:
            write(name, (lineage / name).read_bytes())
        # Kept false during private staging; enable only after the gateway change is approved.
        if cfg.get("reload", False):
            run("docker", "exec", cfg["container"], "nginx", "-t")
            run("docker", "exec", cfg["container"], "nginx", "-s", "reload")
    except Exception:
        for name, data in old.items():
            if data is not None:
                write(name, data)
            else:
                (target / name).unlink(missing_ok=True)
        raise
    print("CRM certificate pair validated and deployed")


if __name__ == "__main__":
    main()
