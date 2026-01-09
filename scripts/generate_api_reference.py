#!/usr/bin/env python3
"""Generate API reference markdown using mkdoxy and Doxygen."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

from mkdoxy.cache import Cache
from mkdoxy.doxyrun import DoxygenRun
from mkdoxy.doxygen import Doxygen
from mkdoxy.generatorAuto import GeneratorAuto
from mkdoxy.generatorBase import GeneratorBase
from mkdoxy.xml_parser import XmlParser

DOCS_DIR = Path("docs")
DOXYGEN_OUTPUT_DIR = Path(".doxygen")

PROJECTS = {
    "core": {
        "src_dirs": [
            "src/nebula_core/nebula_core_common/include",
            "src/nebula_core/nebula_core_decoders/include",
            "src/nebula_core/nebula_core_hw_interfaces/include",
            "src/nebula_core/nebula_core_ros/include",
        ],
        "doxy_cfg": {
            "FILE_PATTERNS": "*.hpp *.h",
            "RECURSIVE": "YES",
            "EXTRACT_ALL": "YES",
            "INLINE_SOURCES": "YES",
            "ENABLE_PREPROCESSING": "YES",
            "MACRO_EXPANSION": "YES",
        },
    },
    "hesai": {
        "src_dirs": [
            "src/nebula_hesai/nebula_hesai_common/include",
            "src/nebula_hesai/nebula_hesai_decoders/include",
            "src/nebula_hesai/nebula_hesai_hw_interfaces/include",
            "src/nebula_hesai/nebula_hesai/include",
        ],
        "doxy_cfg": {
            "FILE_PATTERNS": "*.hpp *.h",
            "RECURSIVE": "YES",
            "EXTRACT_ALL": "YES",
            "INLINE_SOURCES": "YES",
            "ENABLE_PREPROCESSING": "YES",
            "MACRO_EXPANSION": "YES",
        },
    },
    "velodyne": {
        "src_dirs": [
            "src/nebula_velodyne/nebula_velodyne_common/include",
            "src/nebula_velodyne/nebula_velodyne_decoders/include",
            "src/nebula_velodyne/nebula_velodyne_hw_interfaces/include",
            "src/nebula_velodyne/nebula_velodyne/include",
        ],
        "doxy_cfg": {
            "FILE_PATTERNS": "*.hpp *.h",
            "RECURSIVE": "YES",
            "EXTRACT_ALL": "YES",
            "INLINE_SOURCES": "YES",
            "ENABLE_PREPROCESSING": "YES",
            "MACRO_EXPANSION": "YES",
        },
    },
    "robosense": {
        "src_dirs": [
            "src/nebula_robosense/nebula_robosense_common/include",
            "src/nebula_robosense/nebula_robosense_decoders/include",
            "src/nebula_robosense/nebula_robosense_hw_interfaces/include",
            "src/nebula_robosense/nebula_robosense/include",
        ],
        "doxy_cfg": {
            "FILE_PATTERNS": "*.hpp *.h",
            "RECURSIVE": "YES",
            "EXTRACT_ALL": "YES",
            "INLINE_SOURCES": "YES",
            "ENABLE_PREPROCESSING": "YES",
            "MACRO_EXPANSION": "YES",
        },
    },
    "continental": {
        "src_dirs": [
            "src/nebula_continental/nebula_continental_common/include",
            "src/nebula_continental/nebula_continental_decoders/include",
            "src/nebula_continental/nebula_continental_hw_interfaces/include",
            "src/nebula_continental/nebula_continental/include",
        ],
        "doxy_cfg": {
            "FILE_PATTERNS": "*.hpp *.h",
            "RECURSIVE": "YES",
            "EXTRACT_ALL": "YES",
            "INLINE_SOURCES": "YES",
            "ENABLE_PREPROCESSING": "YES",
            "MACRO_EXPANSION": "YES",
        },
    },
}


def build_project(project_name: str, config: dict) -> None:
    source_dirs = " ".join(config["src_dirs"])
    doxy_dir = DOXYGEN_OUTPUT_DIR / project_name

    if doxy_dir.exists():
        shutil.rmtree(doxy_dir)
    doxy_dir.mkdir(parents=True, exist_ok=True)

    doxygen_run = DoxygenRun(
        "doxygen",
        source_dirs,
        str(doxy_dir),
        config["doxy_cfg"],
    )
    doxygen_run.checkAndRun()

    cache = Cache()
    parser = XmlParser(cache=cache, debug=False)
    doxygen = Doxygen(doxygen_run.getOutputFolder(), parser=parser, cache=cache)

    generator_base = GeneratorBase(ignore_errors=False, debug=False)
    generator_auto = GeneratorAuto(
        generatorBase=generator_base,
        tempDoxyDir=str(DOCS_DIR),
        siteDir=str(DOCS_DIR),
        apiPath=project_name,
        doxygen=doxygen,
        useDirectoryUrls=True,
    )

    default_template_config = {"indent_level": 0}
    generator_auto.fullDoc(default_template_config)
    generator_auto.summary(default_template_config)


def main() -> None:
    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    DOXYGEN_OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    for project_name, config in PROJECTS.items():
        project_output = DOCS_DIR / project_name
        if project_output.exists():
            shutil.rmtree(project_output)
        project_output.mkdir(parents=True, exist_ok=True)
        build_project(project_name, config)


if __name__ == "__main__":
    main()
