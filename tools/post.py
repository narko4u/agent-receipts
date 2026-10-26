"""Publish today's receipt to X, behind a gate.

The gate runs before any network write. It refuses a post that is too long,
that omits the canonical evidence link, or that mentions anything internal:
private repository names, local paths, credential shapes. Failing the gate is a
success from a safety point of view, so it exits non-zero and says why.

Exit codes: 0 posted, 2 gate refused, 3 credits depleted, 4 other API error.
"""
import json
import pathlib
import re
import subprocess
import sys

EVIDENCE = "github.com/narko4u/agent-receipts"
MAX = 280

DENY = [
    r"witnessos-gateway",
    r"/home/",
    r"/mnt/",
    r"\bsk-[A-Za-z0-9]",
    r"\bghp_[A-Za-z0-9]",
    r"\bxox[bap]-",
    r"\bAKIA[0-9A-Z]{12,}",
    r"\b(ABN|ACN)\b",
    r"\bpassword\b",
    r"\btoken\b",
]


def gate(text: str) -> list:
    problems = []
    if len(text) > MAX:
        problems.append(f"{len(text)} chars exceeds {MAX}")
    if EVIDENCE not in text:
        problems.append("missing the canonical evidence link")
    for pattern in DENY:
        if re.search(pattern, text, re.IGNORECASE):
            problems.append(f"denied pattern: {pattern}")
    return problems


def post(text: str) -> int:
    done = subprocess.run(["xurl", "post", text], capture_output=True, text=True, timeout=90)
    try:
        payload = json.loads(done.stdout)
    except json.JSONDecodeError:
        print(f"post failed, unparseable reply: {done.stdout[:200]} {done.stderr[:200]}")
        return 4
    if payload.get("data", {}).get("id"):
        print(f"posted id={payload['data']['id']}")
        return 0
    detail = payload.get("detail") or payload.get("errors") or payload
    print(f"post refused by X: {json.dumps(detail)[:200]}")
    return 3 if payload.get("status") == 402 else 4


def main() -> int:
    text = pathlib.Path(sys.argv[1]).read_text(encoding="utf-8").strip() if len(sys.argv) > 1 else sys.stdin.read().strip()
    problems = gate(text)
    if problems:
        print("gate refused: " + "; ".join(problems))
        return 2
    return post(text)


if __name__ == "__main__":
    sys.exit(main())
