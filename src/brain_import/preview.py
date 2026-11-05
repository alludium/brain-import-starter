"""No-write matching via the exact capture payload and the backend's shared matcher."""

from brain_import.brain import Brain, capture_session
from brain_import.model import ImportProblem
from brain_import.plans import validate


def preview_plan(plan, *, brain_factory=Brain, progress=None):
    validate(plan)
    brain = brain_factory(plan["target"])
    brain.check_identity()
    if any(r.get("import_review") for r in plan["records"]):
        brain.require_preview(with_review=True)
    else:
        brain.require_preview()
    results = []
    with capture_session(brain):
        for i, item in enumerate(plan["records"]):
            result = brain.call("capture", {**item, "dry_run": True})
            if result.get("dry_run") is not True or result.get("writes") is not False:
                raise ImportProblem(
                    "Server did not return a dry-run receipt. Update Brain before importing."
                )
            if result.get("disposition") not in {"new", "revision", "unchanged"} or not isinstance(
                result.get("items"), list
            ):
                raise ImportProblem("Unexpected preview response; update Brain before importing.")
            results.append({"title": item["title"], "external_id": item["external_id"], **result})
            if progress:
                progress(i + 1, len(plan["records"]))
    return results
