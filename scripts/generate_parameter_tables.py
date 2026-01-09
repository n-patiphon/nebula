#!/usr/bin/env python3
"""Generate markdown tables from JSON schemas for parameters docs."""

from __future__ import annotations

import argparse
import ast
import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Iterable

from tabulate import tabulate

MACRO_PATTERN = re.compile(r"\{\{\s*json_to_markdown\((.*?)\)\s*\}\}", re.DOTALL)
DEFAULT_JSON_PATH = ["definitions", 0, "properties"]


def format_param_type(param_type: str) -> str:
    if param_type == "number":
        return "float"
    return param_type


def ensure_word_breaks(text: Any) -> Any:
    """For URLs/paths, insert HTML word break marks. Does not affect other or non-string inputs."""
    if not isinstance(text, str):
        return text

    return text.replace("/", "/<wbr>")


def format_param_range(param: dict) -> str:
    list_of_range = []
    if "enum" in param.keys():
        list_of_range.append(", ".join(map(str, param["enum"])))
    if "minimum" in param.keys():
        list_of_range.append("≥ " + str(param["minimum"]))
    if "exclusiveMinimum" in param.keys():
        list_of_range.append("> " + str(param["exclusiveMinimum"]))
    if "maximum" in param.keys():
        list_of_range.append("≤ " + str(param["maximum"]))
    if "exclusiveMaximum" in param.keys():
        list_of_range.append("< " + str(param["exclusiveMaximum"]))
    if "exclusive" in param.keys():
        list_of_range.append("≠ " + str(param["exclusive"]))

    if len(list_of_range) == 0:
        return "N/A"

    range_in_text = ""
    for item in list_of_range:
        if range_in_text != "":
            range_in_text += "<br/>"
        range_in_text += str(item)
    return range_in_text


def get_json_path(json_data: dict, json_path: list) -> dict:
    for elem in json_path:
        if isinstance(elem, int):
            json_data = list(json_data.values())[elem]
        else:
            json_data = json_data[elem]
    return json_data


def extract_parameter_info(
    parameters: dict,
    namespace: str = "",
    file_directory: str = "",
    include_refs: bool = False,
) -> list[dict[str, Any]]:
    params = []
    for key, value in parameters.items():
        value = value

        if "$ref" in value.keys():
            if not include_refs:
                continue

            ref: str = value["$ref"]
            ref_path, ref_json_path = ref.split("#")
            ref_path = os.path.join(file_directory, ref_path)
            ref_json_path = ref_json_path.split("/")
            if ref_json_path[0] == "":
                ref_json_path = ref_json_path[1:]

            with open(ref_path, encoding="utf-8") as file_handle:
                data = json.load(file_handle)
            param = get_json_path(data, ref_json_path)

            param.update({key: val for key, val in value.items() if key != "$ref"})

            param_dict = {key: param}

            extracted_from_ref = extract_parameter_info(
                param_dict, namespace, os.path.split(ref_path)[0], include_refs
            )

            params.extend(extracted_from_ref)
        elif value["type"] != "object":
            param = {
                "Name": namespace + key,
                "Type": format_param_type(value["type"]),
                "Description": value.get("description", ""),
                "Default": ensure_word_breaks(value.get("default", "")),
                "Range": format_param_range(value),
            }
            params.append(param)
        else:
            params.extend(
                extract_parameter_info(
                    value["properties"], key + ".", file_directory, include_refs
                )
            )
    return params


def format_json(json_data: Iterable[dict[str, Any]]) -> str:
    return tabulate(json_data, headers="keys", tablefmt="github")


def parse_macro_args(arg_string: str) -> tuple[str, list[Any], bool]:
    call = ast.parse(f"f({arg_string})", mode="eval").body
    args = [ast.literal_eval(arg) for arg in call.args]

    json_schema_file_path = args[0]
    json_path = args[1] if len(args) > 1 else DEFAULT_JSON_PATH
    include_refs = args[2] if len(args) > 2 else True

    return json_schema_file_path, json_path, include_refs


def render_table(json_schema_file_path: str, json_path: list[Any], include_refs: bool) -> str:
    with open(json_schema_file_path, encoding="utf-8") as file_handle:
        data = json.load(file_handle)

    params = get_json_path(data, json_path)
    param_info = extract_parameter_info(
        params,
        file_directory=os.path.split(json_schema_file_path)[0],
        include_refs=include_refs,
    )
    return format_json(param_info)


def replace_macros(markdown: str) -> str:
    def replacer(match: re.Match) -> str:
        json_schema_file_path, json_path, include_refs = parse_macro_args(match.group(1))
        return render_table(json_schema_file_path, json_path, include_refs)

    return MACRO_PATTERN.sub(replacer, markdown)


def build_argument_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source-dir", default="docs", help="Source docs directory.")
    parser.add_argument(
        "--output-dir",
        default="docs_generated",
        help="Output directory containing expanded markdown.",
    )
    return parser


def main() -> None:
    parser = build_argument_parser()
    args = parser.parse_args()

    source_root = Path(args.source_dir)
    output_root = Path(args.output_dir)

    if output_root.exists():
        shutil.rmtree(output_root)

    shutil.copytree(source_root, output_root)

    markdown_files = output_root.rglob("*.md")

    for file_path in markdown_files:
        content = file_path.read_text(encoding="utf-8")
        if "json_to_markdown" not in content:
            continue

        updated = replace_macros(content)
        file_path.write_text(updated, encoding="utf-8")


if __name__ == "__main__":
    main()
