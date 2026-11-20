"""Local fixtures for skill comparisons. Audit findings use exact source lines."""
import json
import math
import statistics
import subprocess
import sys
import time


def write(root, name, text):
    path = root / name
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text)


def run(cwd, code):
    return subprocess.run([sys.executable, "-B", "-c", code], cwd=cwd,
                          text=True, capture_output=True, timeout=10)


def exact_probe(cwd, code, expected):
    result = run(cwd, code)
    return result.returncode == 0 and result.stdout.strip() == expected


def unchanged(cwd, original):
    return all((cwd / name).is_file() and (cwd / name).read_text() == content
               for name, content in original.items())


SOURCES = {
    "shared-imports": {
        "web.py": "def web_count(rows):\n    return sum(row['status'] == 'shipped' for row in rows)\n",
        "worker.py": "def worker_count(rows):\n    return sum(row['status'] == 'shipped' for row in rows)\n",
        "billing.py": "def billable(rows):\n    return sum(row['status'] == 'shipped' for row in rows)\n",
        "shipment.py": '"""Owns shared shipment rules for web and worker; billing owns invoice policy."""\n',
    },
    "pinned-delivery": {
        "requirements.lock": "parcel_sdk==1.4\n",
        "parcel_sdk.py": "def enqueue(parcel, *, retry_count=0):\n    return (parcel, retry_count)\n",
        "docs/sdk-2.md": "# parcel_sdk 2.0\nCall enqueue(parcel, attempts=3) for two retries.\n",
        "docs/sdk-1.md": "# parcel_sdk 1.4 vendor reference\nCall enqueue(parcel, retry_count=2) for two retries.\n",
        "dispatch.py": "import parcel_sdk\n\ndef send(parcel):\n    return parcel_sdk.enqueue(parcel, attempts=3)\n",
    },
    "polish-export": {
        "export.py": "# Print the given report.\ndef render(report):\n    # A trailing newline separates concatenated reports in legacy importers.\n    return report + '\\n'\n",
        "vendor/reader.py": "# Read the report.\ndef parse(report):\n    return report.splitlines()\n",
    },
    "polish-package": {
        "orders.py": "# Get the order number.\ndef number(order):\n    # External orders can have leading zeroes. Do not convert to int.\n    return order['id']\n",
        "refunds.py": "# Return the refund balance.\ndef balance(paid, refunded):\n    return paid - refunded\n",
        "generated/schema.py": "# Return the schema version.\ndef schema_version():\n    return 2\n",
    },
    "refund-health": {
        "orders.py": "def refund(state, cents):\n    remaining = state['paid'] - state['refunded']\n    if cents > remaining:\n        raise ValueError('exceeds balance')\n    state['refunded'] += cents\n    return remaining - cents\n\ndef label(state):\n    return state.get('label', 'pending')\n",
        "README.md": "# Orders\nRefund requests are positive cents. Rejected requests must leave state unchanged. Old orders can omit display labels.\n",
    },
    "legacy-reader": {
        "store.py": "def read(row):\n    token = row.get('code', row.get('ref'))\n    if token is None:\n        return None\n    return token.strip().lower()\n",
        "consumer.py": "from store import read\n\ndef key(row):\n    return read(row)\n",
        "FORMAT.md": "Old rows use ref. If a new row contains code=null it is a tombstone, even if ref is also present. Preserve the case of codes.\n",
    },
    "startup-delay": {
        "cli.py": "import sys\nfrom catalog import load\n\ndef main():\n    data = load()\n    if sys.argv[1:] == ['--version']:\n        print('3.1')\n    else:\n        print(len(data))\n\nif __name__ == '__main__':\n    main()\n",
        "catalog.py": "import time\n\ndef load():\n    time.sleep(0.2)\n    return ('a', 'b', 'c')\n",
    },
    "checkout-audit": {
        "checkout.py": "def total(lines, discount):\n    subtotal = sum(lines)\n    if not lines:\n        return 0\n    return subtotal - discount\n",
        "README.md": "Only whole cents. Promotion discounts may exceed a small cart, but the final total must be at least zero. Empty carts cost zero.\n",
    },
    "hold-expiry": {
        "holds.py": "def active(hold, now):\n    return hold['expires_at'] >= now\n",
    },
    "lease-recall": {
        "README.md": "This project is Orchid Refresh. Decisions are kept in the local synthetic vault.\n",
    },
    "recovery-evidence": {
        "dispatcher.py": "def deliver(send):\n    for attempt in range(2):\n        try:\n            send()\n            return 'delivered'\n        except TimeoutError:\n            pass\n    return 'pending'\n",
    },
    "relay-recovery": {
        "README.md": "# Fulfillment\nOrders commit to SQLite. A worker sends webhooks; the receiver deduplicates by event ID for 24 hours. A lost response must not lose a committed event or allow a new send after the deduplication window. The worker can be disabled independently of order commits. A stalled receiver must not occupy a worker indefinitely. The caller's deadline is two seconds.\n",
    },
}


def prepare(case, context, git):
    cwd, root = context["cwd"], context["root"]
    original = SOURCES[case]
    for name, content in original.items():
        write(cwd, name, content)
    context["original"] = original
    if case == "hold-expiry":
        context["session_cwd"] = root
        git(cwd, "init", "-q", "-b", "main")
        for key, value in (("user.name", "fixture"), ("user.email", "fixture@example.com")):
            git(cwd, "config", key, value)
        git(cwd, "add", "holds.py")
        git(cwd, "commit", "-qm", "Initial hold behavior")
        remote = root / "origin.git"
        git(root, "clone", "--bare", str(cwd), str(remote))
        git(cwd, "remote", "add", "origin", str(remote))
        git(cwd, "fetch", "origin")
        editor = root / "upstream"
        git(root, "clone", str(remote), str(editor))
        write(editor, "policy.md", "A hold expires at the exact expiry timestamp.\n")
        git(editor, "add", "policy.md")
        git(editor, "-c", "user.name=fixture", "-c", "user.email=fixture@example.com",
            "commit", "-qm", "Record expiry contract")
        git(editor, "push", "origin", "main")
        context.update(local=git(cwd, "rev-parse", "main"), remote=git(editor, "rev-parse", "HEAD"))
    elif case == "lease-recall":
        vault = root / "vault"
        context["vault"] = vault
        write(vault, "codex/sessions/orchid/2026-11-04.md",
              "---\ntype: session\ndate: 2026-11-04\n---\n# Orchid Refresh\n\nRefresh at 36 minutes. The partner invalidates keys after 45 minutes; keep nine minutes for recovery.\n")
        write(vault, "codex/sessions/orchid/2026-10-12.md",
              "---\ntype: session\ndate: 2026-10-12\nstatus: superseded\n---\n# Orchid Refresh\n\nRefresh at 44 minutes.\n")


def artifact(cwd, name="result"):
    path = cwd / ".artifacts" / (name + ".json")
    try:
        value = json.loads(path.read_text())
    except (OSError, ValueError):
        return {}
    return value if isinstance(value, dict) else {}


def located(data, file, line):
    return data.get("file") == file and type(data.get("line")) is int and data["line"] == line


def grade(case, context, events, check, git):
    cwd, original = context["cwd"], context["original"]
    result = artifact(cwd)
    if case == "shared-imports":
        check("both shipment entry points accept delivered", exact_probe(cwd,
              "from web import web_count; from worker import worker_count; r=[{'status':x} for x in ('sent','delivered','shipped')]; print(web_count(r),worker_count(r))",
              "2 2"), "web and worker against mixed statuses")
        check("billing preserves its distinct policy", exact_probe(cwd,
              "from billing import billable; print(billable([{'status':'delivered'},{'status':'shipped'}]))",
              "1"), "billing against the same statuses")
        check("shipment owns the rule", (cwd / "shipment.py").read_text().count("'delivered'") +
              (cwd / "shipment.py").read_text().count('"delivered"') > 0
              and all("delivered" not in (cwd / name).read_text() for name in ("web.py", "worker.py")),
              "rule resides in the shipment module")
    elif case == "pinned-delivery":
        check("dispatch uses pinned API with two retries", exact_probe(cwd,
              "from dispatch import send; print(send('A'))", "('A', 2)"), "pinned SDK actually runs")
        check("SDK and lock unchanged", unchanged(cwd, {name: original[name] for name in
              ("requirements.lock", "parcel_sdk.py")}), "pin and SDK snapshot")
        check("pinned source cited", located(result, "docs/sdk-1.md", 2) or
              located(result, "parcel_sdk.py", 1), result)
    elif case in ("polish-package", "polish-export"):
        modules = ("orders.py", "refunds.py") if case == "polish-package" else ("export.py",)
        for name in modules:
            check(f"redundant comment removed from {name}", original[name].splitlines()[0]
                  not in (cwd / name).read_text(), name)
        if case == "polish-package":
            check("behavior and identifier constraint retained", exact_probe(cwd,
                  "from orders import number; from refunds import balance; print(number({'id':'007'}),balance(90,20))",
                  "007 70"), "order and refund outcomes")
        else:
            check("concatenation contract retained", exact_probe(cwd,
                  "from export import render; print(repr(render('state')))", repr("state\n")),
                  "rendered output")
        name = "generated/schema.py" if case == "polish-package" else "vendor/reader.py"
        check("excluded source unchanged", unchanged(cwd, {name: original[name]}), name)
    elif case in ("refund-health", "checkout-audit"):
        name = "orders.py" if case == "refund-health" else "checkout.py"
        check("audit is read only", unchanged(cwd, original), "source and docs snapshot")
        lines = range(1, 6) if case == "refund-health" else (5,)
        check("actual defect is located", any(located(result, name, line) for line in lines), result)
        if case == "refund-health":
            actual = exact_probe(cwd, "from orders import refund; s=dict(paid=60,refunded=20); print(refund(s,-5),s['refunded'])", "45 15")
            check("rejection and unchanged state expected", actual and result.get("input") == -5 and
                  result.get("actual_refunded") == 15 and result.get("expected_refunded") == 20, result)
        else:
            actual = exact_probe(cwd, "from checkout import total; print(total([25],30))", "-5")
            check("bad checkout state reproduced", actual and result.get("actual_total") == -5
                  and result.get("expected_total") == 0, result)
    elif case == "legacy-reader":
        check("new codes preserve case", exact_probe(cwd,
              "from consumer import key; print(key({'code':' AbC '}))", "AbC"), "new row")
        check("old row fallback retained", exact_probe(cwd,
              "from consumer import key; print(key({'ref':' OrC '}))", "OrC"), "legacy row")
        check("tombstone suppresses fallback", exact_probe(cwd,
              "from consumer import key; print(key({'code':None,'ref':'OrC'}))", "None"), "mixed row")
    elif case == "startup-delay":
        check("app unchanged", unchanged(cwd, original), "app snapshot")
        check("hot path identified", located(result, "cli.py", 5) or located(result, "catalog.py", 4), result)
        samples = result.get("seconds", [])
        valid = isinstance(samples, list) and len(samples) >= 5 and all(
            type(s) in (float, int) and 0.18 <= s <= 10 for s in samples)
        started = time.perf_counter()
        replayed = subprocess.run([sys.executable, "cli.py", "--version"], cwd=cwd,
                                  text=True, capture_output=True, timeout=10)
        replay_time = time.perf_counter() - started
        check("retained startup measurements", valid and
              type(result.get("median")) in (int, float)
              and math.isclose(result["median"], statistics.median(samples), abs_tol=0.0005)
              and result.get("range") == [min(samples), max(samples)]
              and replayed.returncode == 0 and replayed.stdout.strip() == "3.1"
              and 0.18 <= replay_time <= 10, {"report": result, "replayed_seconds": replay_time})
    elif case == "hold-expiry":
        head = git(cwd, "rev-parse", "HEAD")
        branch = git(cwd, "branch", "--show-current")
        check("fresh branch uses remote tip", bool(branch and branch != "main") and head == context["remote"], head)
        check("local main unchanged", git(cwd, "rev-parse", "main") == context["local"], context["local"])
        check("expiry boundary corrected", exact_probe(cwd,
              "from holds import active; print([active({'expires_at':5}, t) for t in (4,5,6)])",
              "[True, False, False]"), "before, at, and after the threshold")
    elif case == "lease-recall":
        check("current decision recovered", result.get("refresh_minutes") == 36 and result.get("expiry_minutes") == 45, result)
        check("specific current source cited", result.get("source") == "2026-11-04.md", result)
    elif case == "recovery-evidence":
        check("implementation unchanged", unchanged(cwd, original), "dispatcher snapshot")
        probe = cwd / ".artifacts/probe.py"
        replay = (subprocess.run([sys.executable, "-B", str(probe)], cwd=cwd, text=True,
                                 capture_output=True, timeout=10) if probe.is_file() else None)
        try:
            observed = json.loads(replay.stdout) if replay and replay.returncode == 0 else {}
        except ValueError:
            observed = {}
        check("probe replays both outcomes", observed == result and observed ==
              {"recovered": ["delivered", 2], "exhausted": ["pending", 2]}, observed)
    elif case == "relay-recovery":
        check("proposal only", unchanged(cwd, original), "requirements snapshot")
        timeout = result.get("send_timeout_seconds")
        check("send bounded under caller deadline", type(timeout) in (int, float) and 0 < timeout <= 2, result)
        horizon = result.get("last_retry_hours")
        check("retry stays inside deduplication window", type(horizon) in (float, int) and
              0 < horizon < 24 and result.get("reuse_event_id") is True, result)
        rollback = result.get("rollback")
        check("rollback pauses sending and preserves pending orders",
              isinstance(rollback, dict) and rollback.get("sender_enabled") is False
              and rollback.get("pending_events_retained") is True and rollback.get("orders_enabled") is True, result)
