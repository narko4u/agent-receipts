"""Produce one receipt for today from facts the agent can actually observe.

The subject is a commit in a public repository. The agent exports that commit,
builds a fresh environment with the project's own install command, runs the
suite, and records what came back. Nothing here reports a plan or an intention.

Reproduce with:
  git clone https://github.com/narko4u/witnessos-verifier && cd witnessos-verifier
  git checkout <commit>
  python -m venv .venv
  .venv/bin/pip install -e . pytest
  .venv/bin/python -m pytest -q
"""
import datetime as dt
import json
import pathlib
import platform
import re
import subprocess
import sys
import tarfile
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parent))
import receipt  # noqa: E402

SUBJECT_REPO = "narko4u/witnessos-verifier"
SUBJECT_TREE = pathlib.Path("/home/vault/work/witnessos-verifier")
BASE_PYTHON = "/home/vault/work/witnessos-verifier/.venv/bin/python"
RECIPE = "python -m venv .venv && .venv/bin/pip install -e . pytest && .venv/bin/python -m pytest -q"


def run(cmd, cwd=None, env=None, timeout=600):
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, env=env, timeout=timeout)


def export_commit(sha: str, dest: pathlib.Path) -> pathlib.Path:
    archive = subprocess.run(["git", "-C", str(SUBJECT_TREE), "archive", sha], capture_output=True, check=True)
    blob = dest / "tree.tar"
    blob.write_bytes(archive.stdout)
    with tarfile.open(blob) as tar:
        tar.extractall(dest, filter="data")
    return dest


def main() -> int:
    today = dt.datetime.now().astimezone().date().isoformat()
    existing = receipt.ROOT / "receipts" / f"{today}.json"
    if existing.exists() and "--force" not in sys.argv:
        draft = receipt.ROOT / "queue" / f"{today}.txt"
        print(draft.read_text(encoding="utf-8").strip() if draft.exists() else f"{today}: receipt already issued")
        return 0
    sha = run(["git", "rev-parse", "HEAD"], SUBJECT_TREE).stdout.strip()
    with tempfile.TemporaryDirectory() as tmp:
        tree = export_commit(sha, pathlib.Path(tmp))
        venv = tree / ".venv"
        run([BASE_PYTHON, "-m", "venv", str(venv)], timeout=300)
        install = run([str(venv / "bin/pip"), "install", "-q", "-e", ".", "pytest"], cwd=tree, timeout=900)
        if install.returncode != 0:
            print("install failed:", install.stdout[-400:], install.stderr[-400:])
            return 1
        done = run([str(venv / "bin/python"), "-m", "pytest", "-q"], cwd=tree, timeout=900)
        out = done.stdout + done.stderr
        passed = re.search(r"(\d+) passed", out)
        failed = re.search(r"(\d+) failed", out)
        skipped = re.search(r"(\d+) skipped", out)
        observed = {
            "passed": int(passed.group(1)) if passed else 0,
            "failed": int(failed.group(1)) if failed else 0,
            "skipped": int(skipped.group(1)) if skipped else 0,
            "exit_code": done.returncode,
        }
        pyver = run([str(venv / "bin/python"), "-c", "import platform;print(platform.python_version())"]).stdout.strip()
    payload = {
        "schema": "agent-receipt/v1",
        "issuer": "Security Division, Empire Labs Pty Ltd",
        "agent": "sovereign",
        "subject": {
            "repo": SUBJECT_REPO,
            "commit": sha,
            "url": f"https://github.com/{SUBJECT_REPO}/commit/{sha}",
        },
        "claims": [{
            "kind": "test_suite",
            "recipe": RECIPE,
            "scope": "clean export of the commit, fresh virtual environment, no working tree changes",
            "observed": observed,
            "environment": {"python": pyver, "platform": sys.platform},
        }],
        "limits": (
            "This record states what the agent observed at that commit. It does not prove the "
            "software is correct, complete or secure, and it says nothing about any other commit."
        ),
    }
    path = receipt.append(payload)
    day = path.stem
    seq = json.loads(path.read_text())["payload"]["seq"]
    post = (
        f"{day} receipt #{seq}: commit {sha[:7]} in witnessos-verifier, built from a clean export, "
        f"{observed['passed']} passed, {observed['failed']} failed, {observed['skipped']} skipped. "
        f"Signed, chained to the previous day, repeatable: github.com/narko4u/agent-receipts"
    )
    (receipt.ROOT / "queue" / f"{day}.txt").write_text(post + "\n", encoding="utf-8")
    print(path)
    print(json.dumps(observed))
    print(post + f"\n[{len(post)} chars]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
