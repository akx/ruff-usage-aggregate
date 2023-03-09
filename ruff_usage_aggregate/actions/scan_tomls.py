import logging
import pathlib
import tomllib

from ruff_usage_aggregate.errors import NotRuffyError
from ruff_usage_aggregate.models import RuffConfig, ScanResult

log = logging.getLogger(__name__)


def scan_tomls(input_directory: pathlib.Path) -> ScanResult:
    sr = ScanResult()
    for pth in input_directory.glob("*.toml"):
        try:
            toml = tomllib.loads(pth.read_text())
        except Exception as e:
            log.error(f"Error parsing {pth}: {e}")
            continue
        if not isinstance(toml, dict):
            log.warning(f"Unexpected TOML type for {pth}: {type(toml)}")
            continue
        name = pth.name
        if name.endswith("ruff.toml"):
            # for a ruff.toml, the whole shebang is the config
            ruff_section = toml
        else:  # otherwise assume pyproject.toml
            ruff_section = toml.get("tool", {}).get("ruff")
        if not isinstance(ruff_section, dict):
            continue
        if not ruff_section:
            continue
        try:
            rc = RuffConfig.from_toml_section(name=name, ruff_section=ruff_section)
        except NotRuffyError:
            log.exception(f"Not ruffy: {pth}")
            continue
        sr.configs.append(rc)
    return sr
