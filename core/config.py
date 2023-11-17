import pathlib

import tomllib

_PATH = pathlib.Path("config.toml")

if not _PATH.exists():
    raise RuntimeError("No config file found.")

with _PATH.open("rb") as fp:
    config = tomllib.load(fp)
