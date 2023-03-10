from __future__ import annotations

import dataclasses
import logging
import statistics
from collections import Counter, defaultdict
from collections.abc import Iterable
from functools import cached_property
from typing import Any

from ruff_usage_aggregate.constants import UNSET
from ruff_usage_aggregate.errors import NotRuffyError

log = logging.getLogger(__name__)


@dataclasses.dataclass(frozen=True)
class ScanResult:
    configs_by_hash: dict[str, list[RuffConfig]] = dataclasses.field(default_factory=dict)

    @property
    def all_configs(self) -> Iterable[RuffConfig]:
        for config_list in self.configs_by_hash.values():
            yield from config_list

    @property
    def unique_configs(self) -> Iterable[RuffConfig]:
        for config_list in self.configs_by_hash.values():
            yield config_list[0]

    @property
    def n_unique(self) -> int:
        return len(self.configs_by_hash)

    @cached_property
    def n_total(self) -> int:
        return sum(len(config_list) for config_list in self.configs_by_hash.values())

    @cached_property
    def n_deduplicated(self) -> int:
        return sum(len(config_list) - 1 for config_list in self.configs_by_hash.values())

    @classmethod
    def from_config_list(cls, config_list: Iterable[RuffConfig]) -> ScanResult:
        configs_by_hash = defaultdict(list)
        for config in config_list:
            configs_by_hash[config.text_hash].append(config)
        return cls(configs_by_hash=configs_by_hash)

    @cached_property
    def aggregated_data(self) -> dict:
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
        for config in self.unique_configs:
            aggregated["extend_ignore"].update(config.extend_ignore or [UNSET])
            aggregated["extend_select"].update(config.extend_select or [UNSET])
            aggregated["fixable"].update(config.fixable or [UNSET])
            aggregated["ignore"].update(config.ignore or [UNSET])
            aggregated["line_length"][config.line_length or UNSET] += 1
            aggregated["target_version"][config.target_version or UNSET] += 1
            aggregated["select"].update(config.select or [UNSET])
            aggregated["unfixable"].update(config.unfixable or [UNSET])
            if config.per_file_ignores is not None:
                for ignores in config.per_file_ignores.values():
                    aggregated["per_file_ignores"].update(ignores)
            aggregated["fields_set"].update(config.fields_set)
        return aggregated

    @cached_property
    def most_common_set_values(self) -> dict[str, Any]:
        values = {}
        for field, counter in self.aggregated_data.items():
            for item, _count in counter.most_common():
                if item is not UNSET:
                    values[field] = item
                    break
        return values

    @cached_property
    def median_line_length(self) -> int:
        return statistics.median(c.line_length for c in self.unique_configs if c.line_length is not None)

    @cached_property
    def value_set_counters(self) -> dict:
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
        for config in self.unique_configs:
            for key in keys:
                v_set = getattr(config, key)
                if v_set is not None:
                    value_sets[key][frozenset(v_set)] += 1
                else:
                    value_sets[key][UNSET] += 1
        return value_sets


@dataclasses.dataclass()
class RuffConfig:
    """
    Ruff config scavenged from a file
    """

    name: str = "(unknown)"
    text_hash: str | None = None
    exclude: set[str] | None = None
    extend_exclude: set[str] | None = None
    extend_ignore: set[str] | None = None
    extend_select: set[str] | None = None
    fields_set: set[str] = dataclasses.field(default_factory=set)
    fixable: set[str] | None = None
    ignore: set[str] | None = None
    line_length: int | None = None
    per_file_ignores: dict[str, set[str]] | None = None
    select: set[str] | None = None
    target_version: str | None = None
    unfixable: set[str] | None = None

    @classmethod
    def from_toml_section(cls, *, name: str, text_hash: str | None = None, ruff_section: dict):
        ruff_section = ruff_section.copy()  # we'll mutate this
        rc = RuffConfig(name=name, text_hash=text_hash)
        if isinstance(select := ruff_section.pop("select", None), list):
            rc.select = set(select)
            rc.fields_set.add("select")
        if isinstance(extend_select := ruff_section.pop("extend-select", None), list):
            rc.extend_select = set(extend_select)
            rc.fields_set.add("extend-select")
        if isinstance(ignore := ruff_section.pop("ignore", None), list):
            rc.ignore = set(ignore)
            rc.fields_set.add("ignore")
        if isinstance(extend_ignore := ruff_section.pop("extend-ignore", None), list):
            rc.extend_ignore = set(extend_ignore)
            rc.fields_set.add("extend-ignore")
        if isinstance(exclude := ruff_section.pop("exclude", None), list):
            rc.exclude = set(exclude)
            rc.fields_set.add("exclude")
        if isinstance(extend_exclude := ruff_section.pop("extend-exclude", None), list):
            rc.extend_exclude = set(extend_exclude)
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
            rc.unfixable = set(unfixable)
            rc.fields_set.add("unfixable")
        if isinstance(fixable := ruff_section.pop("fixable", None), list):
            rc.fixable = set(fixable)
            rc.fields_set.add("fixable")
        if isinstance(per_file_ignores := ruff_section.pop("per-file-ignores", None), dict):
            pfi = {}
            for file, ignores in per_file_ignores.items():
                if isinstance(ignores, list):
                    pfi[file] = set(ignores)
            rc.per_file_ignores = pfi
            rc.fields_set.add("per-file-ignores")

        if not rc.fields_set:
            raise NotRuffyError(f"Invalid ruff section: {ruff_section}")

        if ruff_section:
            log.debug("Unrc.fields_set: %r", ruff_section)

        return rc
