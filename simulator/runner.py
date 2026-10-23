"""Run simulated agents against Warden.

Examples (from the repo root):
  # no server needed - everything in-process, in-memory DB
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode normal
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode s1 --variant plain
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode s1 --variant all --history 25
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode s1 --enforce           # Phase 6: nothing leaks
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode s1 --enforce --approve  # even if a human approves
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode s5 --enforce           # mimicry: restricted, work continues
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode s4 --compare          # slow drift, tight contract
  PYTHONPATH=backend python -m simulator.runner --inprocess --mode s4 --compare --broad  # slow drift, over-broad contract

  # against the running API (make dev)
  python -m simulator.runner --base-url http://localhost:8000 --mode normal --delay 0.4
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

# In-process scenarios need the backend package even when invoked from the
# repository root on Windows, where Make's PYTHONPATH separators differ.
BACKEND_DIR = str(Path(__file__).resolve().parents[1] / "backend")
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)

from simulator.agents.procurement import ProcurementAgent
from simulator.agents.support import SupportAgent
from simulator.client import WardenClient
from simulator.payloads.injections import VARIANTS
from simulator.scenarios import s1_injection, s4_slow_drift, s5_mimicry

COLORS = {"LOW": "\033[32m", "WATCH": "\033[33m", "ELEVATED": "\033[38;5;208m",
          "HIGH": "\033[31m", "CRITICAL": "\033[1;31m"}
RESET = "\033[0m"


def show(agent_id: str, d: dict) -> None:
    c = COLORS.get(d["band"], "")
    ev = d["event"]
    target = ev.get("resource") or ev.get("destination") or ""
    verdict = "" if d["decision"] == "ALLOW" else f"  => {d['decision']}" + (f" ({d['block_reason']})" if d.get("block_reason") else "")
    print(f"{c}{d['band']:<9}{RESET} risk={d['risk']:>5.1f}  {agent_id:<10} {ev['tool']:<26} {target}{verdict}")
    if d["alert_id"]:
        print(f"          -> {d['alert_id']}: {d['message']}")


def build_client(args):
    if args.inprocess:
        from app.config import Settings
        from app.services import build_services
        svc = build_services(Settings(db_path=":memory:", mode="enforce" if args.enforce else "shadow"))
        return WardenClient(service=svc), svc
    return WardenClient(base_url=args.base_url), None


def run_normal(client, args) -> list:
    agents = []
    for i in range(args.agents):
        cls = ProcurementAgent if i % 2 == 0 else SupportAgent
        a = cls(f"{'proc' if cls is ProcurementAgent else 'supp'}-{i // 2 + 1:02d}", client, seed=args.seed)
        a.register()
        agents.append(a)
    for _ in range(args.steps):
        for a in agents:
            show(a.agent_id, a.step())
    return agents


def run_s1(client, args, svc) -> None:
    """The problem statement's attack: poisoned PDF -> HR read -> exfiltration."""
    variants = list(VARIANTS) if args.variant == "all" else [args.variant]
    results = []
    for v in variants:
        if len(variants) == 1:
            print(f"== S1 injection, disguise '{v}', agent history {args.history} ==")
        r = s1_injection.run(client, v, args.history, args.seed, approve_stepups=args.approve,
                             legit_after=args.legit_after,
                             on_step=(lambda label, d: show("proc", d)) if len(variants) == 1 else None)
        results.append(r)
        if len(variants) == 1:
            note = ("enforcement stopped it" if args.enforce else "shadow mode observes only; try --enforce")
            print(f"\nBytes that left the organisation: {r['leaked_bytes']}  ({note})")
            if args.legit_after:
                print(f"Legitimate work afterwards: {r['legit_allowed']}/{r['legit_after']} actions allowed")
    if len(variants) > 1:
        print(f"S1 across disguises (agent history {args.history})\n")
        print(f"{'disguise':<14}{'HR read':>20}{'exfiltration':>22}{'leaked':>9}")
        for r in results:
            print(f"{r['variant']:<14}{r['hr_read_risk']:>10.1f} {r['hr_read_band']:<9}"
                  f"{r['exfil_risk']:>12.1f} {r['exfil_band']:<9}{r['leaked_bytes']:>6}B")
        same = len({(r['hr_read_risk'], r['exfil_risk']) for r in results}) == 1
        print(f"\nIdentical detection across all disguises: {same}")
    if svc is not None and len(variants) == 1:
        from app.risk.explain import render_text
        for a in svc.repo.list_alerts()[:2][::-1]:
            print("\n" + "=" * 100 + f"\n{a['id']}\n")
            print(render_text(svc.repo.get_alert(a["id"])["explanation"]))


def run_s5(client, args, svc) -> None:
    print(f"== S5 mimicry ({'enforce' if args.enforce else 'shadow'} mode) ==\n")
    r = s5_mimicry.run(client, seed=args.seed)
    for st in r["steps"]:
        verdict = st["decision"] + (f" ({st['block_reason']})" if st["block_reason"] else "")
        print(f"{st['band']:<9} risk={st['risk']:>5.1f}  {st['tool']:<14} => {verdict:<28} posture={st['posture']}   {st['label']}")
    print(f"\nLegitimate work before: {r['legit_before_allowed']}/{r['legit_before_total']}, "
          f"AFTER the agent was restricted: {r['legit_after_allowed']}/{r['legit_after_total']}")
    print(f"Bytes that left the organisation: {r['leaked_bytes']}   final posture: {r['final_posture']}")
    if svc is not None:
        tok = svc.broker.active(r["agent_id"])
        if tok:
            print(f"Token scope now: {', '.join(sorted(tok.scopes))}")


def _print_s4(title: str, r: dict) -> None:
    print(f"\n{title}")
    print(f"  first WATCH at capability {r['first_watch_capability']}, first ELEVATED at "
          f"{r['first_elevated_capability']}, legit-work alerts: {r['normal_alerts']} "
          f"(max normal risk {r['normal_max_risk']})")
    for c in r["per_capability"]:
        print(f"    capability {c['capability']}  {c['tool']:<32} first use {c['first_use_risk']:>5}   "
              f"last use {c['last_use_risk']:>5}  {c['last_band']}")


def run_s4(client, args, svc) -> None:
    """Slow drift: five plausible capabilities added one at a time."""
    kind = "OVER-BROAD contract (every step is permitted)" if args.broad else "tight contract"
    print(f"== S4 slow drift, {kind} ==")
    if not args.compare:
        _print_s4("full system", s4_slow_drift.run(client, broad_contract=args.broad, seed=args.seed))
        return
    if svc is None:
        print("--compare needs --inprocess (it rebuilds Warden with lenses switched off)")
        return
    from app.config import Settings
    from app.services import build_services
    configs = [("A  full system", {}),
               ("B  rolling baseline only (no drift, learns everything)", {"enable_drift": False, "learn_gate": False}),
               ("C  baseline with learn-gate, no drift", {"enable_drift": False})]
    for name, flags in configs:
        sv = build_services(Settings(db_path=":memory:", **flags))
        _print_s4(name, s4_slow_drift.run(WardenClient(service=sv), broad_contract=args.broad, seed=args.seed))


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("--mode", choices=["normal", "s1", "s4", "s5", "preview-attack"], default="normal")
    p.add_argument("--variant", default="plain", choices=["all", *VARIANTS])
    p.add_argument("--enforce", action="store_true", help="run Warden in enforce mode (--inprocess only)")
    p.add_argument("--approve", action="store_true", help="s1: a tired human approves every paused action")
    p.add_argument("--legit-after", type=int, default=0, help="s1: legitimate actions to attempt after the attack")
    p.add_argument("--broad", action="store_true", help="s4: use the over-broad contract")
    p.add_argument("--compare", action="store_true", help="s4: also run with lenses switched off (needs --inprocess)")
    p.add_argument("--history", type=int, default=0, help="normal actions before the attack")
    p.add_argument("--inprocess", action="store_true", help="no server; in-memory DB")
    p.add_argument("--base-url", default="http://localhost:8000")
    p.add_argument("--agents", type=int, default=4)
    p.add_argument("--steps", type=int, default=15)
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--delay", type=float, default=0.0)
    args = p.parse_args(argv)

    client, svc = build_client(args)
    if args.mode == "normal":
        run_normal(client, args)
    elif args.mode == "s4":
        run_s4(client, args, svc)
    elif args.mode == "s5":
        run_s5(client, args, svc)
    else:  # s1 (preview-attack kept as an alias)
        run_s1(client, args, svc)
    return 0


if __name__ == "__main__":
    sys.exit(main())
