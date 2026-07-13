"""Government Jobs & Exams Intelligence Tracker - entry point.

Usage:
  python main.py                  run the full daily pipeline
  python main.py --login-mstodo   one-time Microsoft To Do device login
  python main.py --status ID "Applied"   update tracked status for a record
  python main.py --merge KEEP_ID DUP_ID  merge a duplicate into the record to keep
  python main.py --list-urgent    print deadlines within 7 days and exit
"""
import argparse
import os
import sys


def load_env(path=".env"):
    """Tiny .env loader so no extra dependency is needed."""
    if not os.path.exists(path):
        return
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip())


def main():
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    load_env()
    ap = argparse.ArgumentParser()
    ap.add_argument("--login-mstodo", action="store_true")
    ap.add_argument("--status", nargs=2, metavar=("ID", "STATUS"))
    ap.add_argument("--merge", nargs=2, metavar=("KEEP_ID", "DUP_ID"))
    ap.add_argument("--list-urgent", action="store_true")
    args = ap.parse_args()

    if args.login_mstodo:
        from src.notify import mstodo
        sys.exit(0 if mstodo.login_interactive() else 1)

    from src.pipeline import load_config, run
    from src.database import Store

    if args.status:
        cfg = load_config()
        store = Store(cfg["paths"]["database"])
        ok = store.set_status(args.status[0], args.status[1])
        print("updated" if ok else "notification id not found")
        sys.exit(0 if ok else 1)

    if args.merge:
        cfg = load_config()
        store = Store(cfg["paths"]["database"])
        keep, dup = args.merge
        ok = store.merge(keep, dup)
        if ok:
            n = store.get(keep)
            print(f"merged. keeping: {n.job_name} [{keep}]")
            print("future scrapes of the duplicate will update this record.")
        else:
            print("merge failed - check both ids exist (see docs/data.json or the CSV)")
        sys.exit(0 if ok else 1)

    if args.list_urgent:
        cfg = load_config()
        store = Store(cfg["paths"]["database"])
        for n in sorted(store.all(), key=lambda n: n.days_left() or 9999):
            dl = n.days_left()
            if dl is not None and 0 <= dl <= 7:
                print(f"{dl:2d}d  {n.application_end}  {n.job_name}  [{n.notification_id}]")
        sys.exit(0)

    print(run())


if __name__ == "__main__":
    main()
