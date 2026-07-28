"""Build the PASS/FAIL report consumed by the CLI and the `report` CI job.

specs/flash-pipeline/spec.md: "le pipeline ne prétend jamais à un succès
partiel" — this module enforces that by construction: `status` is derived
from the recorded steps, never set independently.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class StepResult:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class FlashReport:
    serial: str
    steps: list[StepResult] = field(default_factory=list)
    version_before: int | None = None
    version_after: int | None = None
    crc_before: int | None = None
    crc_after: int | None = None
    backup_sha256: str | None = None

    def add_step(self, name: str, ok: bool, detail: str = "") -> None:
        self.steps.append(StepResult(name=name, ok=ok, detail=detail))

    @property
    def status(self) -> str:
        """PASS only if every recorded step succeeded and at least one ran."""
        if not self.steps:
            return "FAIL"
        return "PASS" if all(step.ok for step in self.steps) else "FAIL"

    def to_dict(self) -> dict[str, Any]:
        return {
            "status": self.status,
            "serial": self.serial,
            "steps": [asdict(step) for step in self.steps],
            "version_before": _hex_or_none(self.version_before),
            "version_after": _hex_or_none(self.version_after),
            "crc_before": _hex_or_none(self.crc_before),
            "crc_after": _hex_or_none(self.crc_after),
            "backup_sha256": self.backup_sha256,
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2)


def _hex_or_none(value: int | None) -> str | None:
    return None if value is None else f"0x{value:04X}"
