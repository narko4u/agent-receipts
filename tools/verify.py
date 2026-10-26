"""Verify agent receipts without trusting the issuer.

Checks, in order:
  1. the signature over the canonical payload, using the published public key
  2. the hash chain: each record's prev must equal sha256 of the previous file
  3. sequence numbers are contiguous from 1

Optional --gh also confirms the subject commit exists at the stated repository,
using the public GitHub API. That is a courtesy check, not part of the seal.

Usage: python3 tools/verify.py [receipts/2026-10-26.json ...] [--gh]
"""
import base64
import hashlib
import json
import pathlib
import subprocess
import sys
import tempfile
import urllib.request

ROOT = pathlib.Path(__file__).resolve().parent.parent
PUB = ROOT / "keys" / "receipt-signing.pub.pem"


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_file(path: pathlib.Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def check_signature(payload: dict, sig_b64: str) -> bool:
    with tempfile.TemporaryDirectory() as tmp:
        msg = pathlib.Path(tmp, "msg")
        sig = pathlib.Path(tmp, "sig")
        msg.write_bytes(canonical(payload))
        sig.write_bytes(base64.b64decode(sig_b64))
        done = subprocess.run(
            ["openssl", "pkeyutl", "-verify", "-pubin", "-inkey", str(PUB), "-rawin", "-in", str(msg), "-sigfile", str(sig)],
            capture_output=True, text=True,
        )
        return done.returncode == 0


def check_remote(subject: dict) -> bool:
    url = f"https://api.github.com/repos/{subject['repo']}/commits/{subject['commit']}"
    req = urllib.request.Request(url, headers={"Accept": "application/vnd.github+json", "User-Agent": "agent-receipts-verify"})
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status == 200
    except Exception:
        return False


def main(argv: list) -> int:
    want_gh = "--gh" in argv
    paths = [pathlib.Path(a) for a in argv if not a.startswith("--")]
    if not paths:
        paths = sorted((ROOT / "receipts").glob("*.json"))
    failures = 0
    prev_digest = None
    prev_seq = 0
    for path in paths:
        env = json.loads(path.read_text(encoding="utf-8"))
        payload, sig = env["payload"], env["signature"]
        ok_sig = check_signature(payload, sig["sig_b64"])
        chain_ok = payload.get("prev") == prev_digest
        seq_ok = payload.get("seq") == prev_seq + 1
        extra = ""
        if want_gh:
            extra = f" commit_exists={check_remote(payload['subject'])}"
        verdict = "OK" if (ok_sig and chain_ok and seq_ok) else "FAIL"
        if verdict == "FAIL":
            failures += 1
        print(f"{verdict} {path.name} seq={payload.get('seq')} sig={ok_sig} chain={chain_ok} seq_contiguous={seq_ok}{extra}")
        prev_digest = sha256_file(path)
        prev_seq = payload.get("seq", 0)
    print(f"{len(paths)} checked, {failures} failed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
