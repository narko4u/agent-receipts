"""Build, sign and chain an agent receipt.

The signing key lives outside the repository, at ~/.hermes/keys/receipt-signing.pem
(mode 0600). Only the public key is published. Signed bytes are the canonical
JSON of the payload: sorted keys, no whitespace, UTF-8.
"""
import base64
import datetime as dt
import hashlib
import json
import os
import pathlib
import subprocess
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent.parent
KEY = pathlib.Path(os.environ.get("RECEIPT_KEY", str(pathlib.Path.home() / ".hermes/keys/receipt-signing.pem")))
KEY_ID = "receipt-signing-v1"


def canonical(payload: dict) -> bytes:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


def sha256_bytes(data: bytes) -> str:
    return "sha256:" + hashlib.sha256(data).hexdigest()


def sign(payload: dict) -> str:
    data = canonical(payload)
    with tempfile.TemporaryDirectory() as tmp:
        msg = pathlib.Path(tmp, "msg")
        sig = pathlib.Path(tmp, "sig")
        msg.write_bytes(data)
        subprocess.run(
            ["openssl", "pkeyutl", "-sign", "-inkey", str(KEY), "-rawin", "-in", str(msg), "-out", str(sig)],
            check=True, capture_output=True,
        )
        return base64.b64encode(sig.read_bytes()).decode("ascii")


def receipts() -> list:
    return sorted((ROOT / "receipts").glob("*.json"))


def last() -> tuple:
    files = receipts()
    if not files:
        return None, None
    newest = files[-1]
    raw = newest.read_bytes()
    return json.loads(raw)["payload"], sha256_bytes(raw)


def append(payload: dict) -> pathlib.Path:
    payload = dict(payload)
    prev_payload, prev_digest = last()
    payload["seq"] = (prev_payload["seq"] + 1) if prev_payload else 1
    payload["prev"] = prev_digest
    payload.setdefault("issued_at", dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"))
    envelope = {"payload": payload, "signature": {"alg": "ed25519", "key_id": KEY_ID, "sig_b64": sign(payload)}}
    day = payload["issued_at"][:10]
    out = ROOT / "receipts" / f"{day}.json"
    out.write_text(json.dumps(envelope, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")
    return out
