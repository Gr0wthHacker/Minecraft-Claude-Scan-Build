"""Plan, approve, emit, generate, slice and ship all three theme-park zones.

**THE WHOLE POINT IS THAT IT IS ONE COMMAND.** The sequence is plan -> approve -> emit -> gen
per config -> layers --floor -> ship, and it has to be re-run in full every time any generator or
theme changes, because a plan is a SITING and a siting moves when a module's measured footprint
moves. Run by hand it was got wrong twice in one session: once by slicing at `--floor 203`, which
is the plane you STAND on rather than the course the floor blocks OCCUPY, and filed the entire
park's paving into the basement layer; and once by shipping layers cut from a plan two theme edits
old. A step that has to be remembered is a step that gets lost.

    python tools/parkship.py            # all three zones
    python tools/parkship.py --zone midway --no-ship

**THE APPROVE GATE IS STILL A GATE.** Without `--approve` this prints the plan and stops, which
is exactly what the gate is for - `planner.emit` refuses an unapproved plan, and routing around
that automatically would make the gate decorative. Read the plan, then re-run with `--approve`.
"""
from __future__ import annotations

import argparse
import subprocess
import sys

# zone -> (theme/brief, island, plan name, capture)
ZONES = {
    "midway":   ("theme park midway",   "newisle",     "park_centre", "out/newisle.litematic"),
    "frontier": ("theme park frontier", "islandleft",  "park_left",   "out/islandleft.litematic"),
    "hollow":   ("theme park hollow",   "islandright", "park_right",  "out/islandright.litematic"),
}
# The build PLANE is the course you stand on; the FLOOR is the course the floor blocks occupy,
# one under it. Getting these the same way round is what put 5,549 blocks of paving into a layer
# called "Machines".
PLANE = 203
FLOOR = PLANE - 1


def run(*args, quiet=False):
    r = subprocess.run([sys.executable, "-m", "mcbuild", *args],
                       capture_output=True, text=True)
    if r.returncode:
        sys.stderr.write(r.stdout + r.stderr)
        raise SystemExit(f"failed: mcbuild {' '.join(args)}")
    if not quiet:
        print(r.stdout.rstrip())
    return r.stdout


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--zone", choices=sorted(ZONES), action="append")
    ap.add_argument("--no-ship", action="store_true")
    ap.add_argument("--approve", action="store_true",
                    help="pass the human gate. Without it this stops after printing the plan, "
                         "which is the point of the gate: a plan nobody read is not approved.")
    a = ap.parse_args()

    for zone in (a.zone or list(ZONES)):
        brief, island, name, world = ZONES[zone]
        print(f"\n=== {zone} =====================================================")
        out = run("plan", brief, "--world", world, "--island", island,
                  "--name", name, "--plane", str(PLANE))
        # NO SITE is not fatal - a plot that cannot take everything is a real answer and the
        # curation is a human decision - but it must be LOUD, because a quietly missing ride is
        # how the midway shipped with no rides on it.
        missed = [ln.strip() for ln in out.splitlines() if "NO SITE" in ln]
        if not a.approve:
            if missed:
                print("  NOT SITED:")
                for m in missed:
                    print(f"    {m}")
            print(f"  stopping at the gate - re-run with --approve to emit and ship {name}")
            continue
        run("plan", "--approve", name, quiet=True)
        cfgs = run("plan", "--emit", name, quiet=True)
        n = 0
        for line in cfgs.splitlines():
            line = line.strip()
            if line.endswith(".yaml"):
                run("gen", line, quiet=True)
                n += 1
        print(f"  generated {n} config(s)")
        args = ["layers", name, "--floor", str(FLOOR)]
        if not a.no_ship:
            args.append("--ship")
        run(*args)
        if missed:
            print("  NOT SITED:")
            for m in missed:
                print(f"    {m}")


if __name__ == "__main__":
    main()
