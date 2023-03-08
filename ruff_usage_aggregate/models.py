from __future__ import annotations

import dataclasses
import logging
from collections import Counter

from ruff_usage_aggregate.constants import UNSET

log = logging.getLogger(__name__)


@dataclasses.dataclass()
class ScanResult:
    configs: list[RuffConfig] = dataclasses.field(default_factory=list)

    def aggregate(self) -> dict:
        aggregated = {
            "extend_ignore": Counter(),
            "extend_select": Counter(),
            "fixable": Counter(),
            "ignore": Counter(),
            "line_length": Counter(),
            "per_file_ignores": Counter(),
            "select": Counter(),
            "target_version": Counter(),
            "unfixable": Counter(),
        }
        for config in self.configs:
            aggregated["extend_ignore"].update(config.extend_ignore or [UNSET])
            aggregated["extend_select"].update(config.extend_select or [UNSET])
            aggregated["fixable"].update(config.fixable or [UNSET])
            aggregated["ignore"].update(config.ignore or [UNSET])
            aggregated["line_length"][config.line_length or UNSET] += 1
            aggregated["target_version"][config.target_version or UNSET] += 1
            aggregated["select"].update(config.select or [UNSET])
            aggregated["unfixable"].update(config.unfixable or [UNSET])
            for ignores in config.per_file_ignores.values():
                aggregated["per_file_ignores"].update(ignores)
        return aggregated


@dataclasses.dataclass()
class RuffConfig:
    """
    Ruff config scavenged from a file
    """

    url: str
    extend_ignore: set[str] = dataclasses.field(default_factory=set)
    extend_select: set[str] = dataclasses.field(default_factory=set)
    fixable: set[str] = dataclasses.field(default_factory=set)
    ignore: set[str] = dataclasses.field(default_factory=set)
    line_length: int | None = None
    per_file_ignores: dict[str, set[str]] = dataclasses.field(default_factory=dict)
    select: set[str] = dataclasses.field(default_factory=set)
    target_version: str | None = None
    unfixable: set[str] = dataclasses.field(default_factory=set)

    @classmethod
    def from_toml_section(cls, url: str, ruff_section: dict):
        ruff_section = ruff_section.copy()  # we'll mutate this
        rc = RuffConfig(url)
        if isinstance(select := ruff_section.pop("select", None), list):
            rc.select.update(select)
        if isinstance(extend_select := ruff_section.pop("extend-select", None), list):
            rc.extend_select.update(extend_select)
        if isinstance(ignore := ruff_section.pop("ignore", None), list):
            rc.ignore.update(ignore)
        if isinstance(extend_ignore := ruff_section.pop("extend-ignore", None), list):
            rc.extend_ignore.update(extend_ignore)
        if isinstance(line_length := ruff_section.pop("line-length", None), int):
            rc.line_length = line_length
        if isinstance(line_length := ruff_section.pop("max-line-length", None), int):
            rc.line_length = line_length
        if isinstance(target_version := ruff_section.pop("target-version", None), str):
            rc.target_version = target_version
        if isinstance(unfixable := ruff_section.pop("unfixable", None), list):
            rc.unfixable.update(unfixable)
        if isinstance(fixable := ruff_section.pop("fixable", None), list):
            rc.fixable.update(fixable)
        if isinstance(per_file_ignores := ruff_section.pop("per-file-ignores", None), dict):
            for file, ignores in per_file_ignores.items():
                if isinstance(ignores, list):
                    rc.per_file_ignores[file] = set(ignores)

        if ruff_section:
            log.debug("Unprocessed: %r", ruff_section)

        return rc
