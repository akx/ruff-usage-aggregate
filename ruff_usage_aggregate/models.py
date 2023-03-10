from __future__ import annotations

import dataclasses
import logging
from collections import Counter

from ruff_usage_aggregate.constants import UNSET
from ruff_usage_aggregate.errors import NotRuffyError

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
            "fields_set": Counter(),
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
            aggregated["fields_set"].update(config.fields_set)
        return aggregated

    def get_value_set_counters(self) -> dict:
        keys = {
            "extend_ignore",
            "extend_select",
            "fields_set",
            "fixable",
            "ignore",
            "select",
            "unfixable",
        }
        value_sets = {key: Counter() for key in keys}
        for config in self.configs:
            for key in keys:
                value_sets[key][frozenset(getattr(config, key))] += 1
        return value_sets


@dataclasses.dataclass()
class RuffConfig:
    """
    Ruff config scavenged from a file
    """

    name: str = "(unknown)"
    text_hash: str | None = None
    duplicates_set: set[str] = dataclasses.field(default_factory=set)
    exclude: set[str] = dataclasses.field(default_factory=set)
    extend_exclude: set[str] = dataclasses.field(default_factory=set)
    extend_ignore: set[str] = dataclasses.field(default_factory=set)
    extend_select: set[str] = dataclasses.field(default_factory=set)
    fields_set: set[str] = dataclasses.field(default_factory=set)
    fixable: set[str] = dataclasses.field(default_factory=set)
    ignore: set[str] = dataclasses.field(default_factory=set)
    line_length: int | None = None
    per_file_ignores: dict[str, set[str]] = dataclasses.field(default_factory=dict)
    select: set[str] = dataclasses.field(default_factory=set)
    target_version: str | None = None
    unfixable: set[str] = dataclasses.field(default_factory=set)

    @classmethod
    def from_toml_section(cls, ruff_section: dict):
        ruff_section = ruff_section.copy()  # we'll mutate this
        rc = RuffConfig()
        if isinstance(select := ruff_section.pop("select", None), list):
            rc.select.update(select)
            rc.fields_set.add("select")
        if isinstance(extend_select := ruff_section.pop("extend-select", None), list):
            rc.extend_select.update(extend_select)
            rc.fields_set.add("extend-select")
        if isinstance(ignore := ruff_section.pop("ignore", None), list):
            rc.ignore.update(ignore)
            rc.fields_set.add("ignore")
        if isinstance(extend_ignore := ruff_section.pop("extend-ignore", None), list):
            rc.extend_ignore.update(extend_ignore)
            rc.fields_set.add("extend-ignore")
        if isinstance(exclude := ruff_section.pop("exclude", None), list):
            rc.exclude.update(exclude)
            rc.fields_set.add("exclude")
        if isinstance(extend_exclude := ruff_section.pop("extend-exclude", None), list):
            rc.extend_exclude.update(extend_exclude)
            rc.fields_set.add("extend-exclude")
        if isinstance(line_length := ruff_section.pop("line-length", None), int):
            rc.line_length = line_length
            rc.fields_set.add("line-length")
        if isinstance(line_length := ruff_section.pop("max-line-length", None), int):
            rc.line_length = line_length
            rc.fields_set.add("max-line-length")
        if isinstance(target_version := ruff_section.pop("target-version", None), str):
            rc.target_version = target_version
            rc.fields_set.add("target-version")
        if isinstance(unfixable := ruff_section.pop("unfixable", None), list):
            rc.unfixable.update(unfixable)
            rc.fields_set.add("unfixable")
        if isinstance(fixable := ruff_section.pop("fixable", None), list):
            rc.fixable.update(fixable)
            rc.fields_set.add("fixable")
        if isinstance(per_file_ignores := ruff_section.pop("per-file-ignores", None), dict):
            for file, ignores in per_file_ignores.items():
                if isinstance(ignores, list):
                    rc.per_file_ignores[file] = set(ignores)
            rc.fields_set.add("per-file-ignores")

        if not rc.fields_set:
            raise NotRuffyError(f"Invalid ruff section: {ruff_section}")

        if ruff_section:
            log.debug("Unrc.fields_set: %r", ruff_section)

        return rc
