"""The entire adapter contract: yield Records, without calling Brain."""

from dataclasses import asdict, dataclass


class ImportProblem(Exception):
    """A safe diagnostic: never put credentials or source content in its message."""


@dataclass(frozen=True)
class Record:
    system: str
    external_id: str
    title: str
    text: str
    url: str | None = None
    kind: str = "document"

    def payload(self, scope: str) -> dict:
        return {**asdict(self), "scope": scope}
