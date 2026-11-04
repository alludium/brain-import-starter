"""Plan → inspect → apply. Default commands never write to Brain."""

import argparse
import json
import sys
from pathlib import Path

from brain_import.brain import Brain
from brain_import.model import ImportProblem
from brain_import.plans import build, load, private_file, save, server_url, summary

DEFAULT_SERVER = "https://app.brain.alludium.ai/mcp"


def apply(plan, sha, confirmation, receipt_path, *, brain_factory=Brain):
    if confirmation != sha:
        raise ImportProblem("Plan digest differs from --confirm; inspect the plan again.")
    brain = brain_factory(plan["target"])
    brain.check_identity()
    # Open receipts before any writes; stop on the first error, preserving successes.
    with private_file(receipt_path) as receipts:
        for index, item in enumerate(plan["records"], start=1):
            out = brain.call("capture", item)
            if not isinstance(out.get("source_id"), str) or not isinstance(
                out.get("created"), bool
            ):
                raise ImportProblem(
                    "Capture returned an unexpected receipt; stop and check privately."
                )
            receipt = {
                "record": index,
                "plan_sha256": sha,
                "target": plan["target"],
                "system": item["system"],
                "external_id": item["external_id"],
                **{
                    k: out.get(k)
                    for k in ("source_id", "created", "scope", "revision_of", "structure_job_id")
                },
                "warning_count": len(out.get("warnings", [])),
            }
            receipts.write(json.dumps(receipt) + "\n")
            receipts.flush()
            print(
                json.dumps(
                    {
                        "record": index,
                        "source_id": out["source_id"],
                        "created": out["created"],
                        "warning_count": receipt["warning_count"],
                    }
                ),
                flush=True,
            )
            if out.get("scope") != item["scope"] or receipt["warning_count"]:
                raise ImportProblem(
                    "Capture stored with a different scope or warnings; review before continuing."
                )


def main():
    parser = argparse.ArgumentParser(
        description="Adapt your sources to Alludium Brain, through its CLI."
    )
    sub = parser.add_subparsers(dest="command", required=True)
    identity = sub.add_parser(
        "identity", help="Read current Brain account IDs; never imports content"
    )
    identity.add_argument("--server", default=DEFAULT_SERVER)
    plan = sub.add_parser(
        "plan", help="Read a selected source; save a local snapshot without Brain writes"
    )
    plan.add_argument("config", type=Path)
    plan.add_argument("--out", required=True, type=Path)
    inspect = sub.add_parser("inspect", help="Show plan metadata and digest, without document text")
    inspect.add_argument("plan", type=Path)
    run = sub.add_parser("apply", help="Send exactly the reviewed snapshot to Brain")
    run.add_argument("plan", type=Path)
    run.add_argument("--confirm", required=True, help="SHA-256 printed by plan/inspect")
    run.add_argument("--receipts", required=True, type=Path)
    args = parser.parse_args()
    try:
        if args.command == "identity":
            print(json.dumps(Brain({"server": server_url(args.server)}).identity(), indent=2))
        elif args.command == "plan":
            data = build(args.config)
            sha = save(data, args.out)
            print(json.dumps(summary(data, sha), indent=2, ensure_ascii=False))
        else:
            data, sha = load(args.plan)
            if args.command == "inspect":
                print(json.dumps(summary(data, sha), indent=2, ensure_ascii=False))
            else:
                apply(data, sha, args.confirm, args.receipts)
        return 0
    except ImportProblem as exc:
        print(str(exc), file=sys.stderr)
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        print(
            "Cannot read input or write output; check configuration, source format and file paths. "
            "Output files must be new. No raw input was logged.",
            file=sys.stderr,
        )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
