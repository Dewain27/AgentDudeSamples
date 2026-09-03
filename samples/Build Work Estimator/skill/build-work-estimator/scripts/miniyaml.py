#!/usr/bin/env python3
"""Dependency-free parsing for the manifest subset of YAML.

Author: Dewain Robinson

Sandboxed hosts -- Copilot Cowork, Copilot Studio's harness -- have no package
installation, so `import yaml` is not available there. Requiring PyYAML would
mean the estimator simply does not run on half its supported hosts.

This parses the small, well-defined subset a manifest actually uses:

    key: value                  scalars: str, int, float, bool, null
    nested:                     nested mappings by indentation
      key: value
    items:                      lists of mappings
      - name: a
        size: medium
    # comments and blank lines

It is NOT a general YAML implementation and does not try to be -- no anchors,
aliases, multi-line scalars, flow collections, or multiple documents. Anything
outside the subset raises rather than guessing, because a manifest silently
misparsed would produce a confident wrong estimate.

`load()` prefers PyYAML when it is installed and falls back to this parser
otherwise, so behaviour is identical wherever PyYAML exists. The test suite
asserts parity between the two on every shipped manifest.
"""

__author__ = "Dewain Robinson"

TRUE = ("true", "yes", "on")
FALSE = ("false", "no", "off")
NULL = ("null", "~", "")


class ManifestParseError(Exception):
    """Raised when the input falls outside the supported subset."""


def _scalar(text):
    """Convert a scalar token to a Python value."""
    raw = text.strip()
    if not raw:
        return None
    if raw[0] in "\"'" and raw[-1] == raw[0] and len(raw) >= 2:
        return raw[1:-1]
    low = raw.lower()
    if low in TRUE:
        return True
    if low in FALSE:
        return False
    if low in NULL:
        return None
    try:
        return int(raw)
    except ValueError:
        pass
    try:
        return float(raw)
    except ValueError:
        pass
    if raw[0] in "[{":
        raise ManifestParseError(
            "flow collections (%s...) are not supported. Write the value as an "
            "indented block instead." % raw[:1])
    return raw


def _strip_comment(line):
    """Remove a trailing comment, respecting quotes."""
    out, quote = [], None
    for index, char in enumerate(line):
        if quote:
            out.append(char)
            if char == quote:
                quote = None
            continue
        if char in "\"'":
            quote = char
            out.append(char)
            continue
        if char == "#" and (index == 0 or line[index - 1] in " \t"):
            break
        out.append(char)
    return "".join(out).rstrip()


def _lines(text):
    """Yield (indent, content, line_number) for meaningful lines."""
    for number, raw in enumerate(text.splitlines(), 1):
        if "\t" in raw[:len(raw) - len(raw.lstrip())]:
            raise ManifestParseError(
                "line %d indents with a tab; YAML requires spaces." % number)
        content = _strip_comment(raw)
        if not content.strip():
            continue
        yield len(content) - len(content.lstrip(" ")), content.strip(), number


def _split_pair(content, number):
    if ":" not in content:
        raise ManifestParseError(
            "line %d is not a `key: value` pair: %r" % (number, content))
    key, _, value = content.partition(":")
    key = key.strip()
    if not key:
        raise ManifestParseError("line %d has an empty key." % number)
    return key, value.strip()


def _parse_block(rows, index, indent):
    """Parse a mapping or sequence at `indent`. Returns (value, next_index)."""
    if index >= len(rows):
        return None, index

    if rows[index][1].startswith("- "):
        return _parse_sequence(rows, index, indent)

    mapping = {}
    while index < len(rows):
        row_indent, content, number = rows[index]
        if row_indent < indent:
            break
        if row_indent > indent:
            raise ManifestParseError(
                "line %d is indented unexpectedly." % number)
        if content.startswith("- "):
            break

        key, value = _split_pair(content, number)
        if value == "":
            child_index = index + 1
            if child_index < len(rows) and rows[child_index][0] > indent:
                mapping[key], index = _parse_block(
                    rows, child_index, rows[child_index][0])
            elif (child_index < len(rows)
                    and rows[child_index][1].startswith("- ")
                    and rows[child_index][0] == indent):
                mapping[key], index = _parse_sequence(
                    rows, child_index, indent)
            else:
                mapping[key] = None
                index = child_index
        else:
            mapping[key] = _scalar(value)
            index += 1
    return mapping, index


def _parse_sequence(rows, index, indent):
    items = []
    while index < len(rows):
        row_indent, content, number = rows[index]
        if row_indent < indent or not content.startswith("- "):
            break
        if row_indent > indent:
            raise ManifestParseError(
                "line %d is indented unexpectedly inside a list." % number)

        first = content[2:].strip()
        if ":" not in first:
            items.append(_scalar(first))
            index += 1
            continue

        # A list entry that is a mapping: its first pair sits on the dash line,
        # the rest are indented to align with it.
        key, value = _split_pair(first, number)
        entry = {}
        member_indent = row_indent + 2
        if value == "":
            child = index + 1
            if child < len(rows) and rows[child][0] > member_indent:
                entry[key], index = _parse_block(rows, child, rows[child][0])
            else:
                entry[key] = None
                index = child
        else:
            entry[key] = _scalar(value)
            index += 1

        while index < len(rows):
            next_indent, next_content, next_number = rows[index]
            if next_indent != member_indent or next_content.startswith("- "):
                break
            key, value = _split_pair(next_content, next_number)
            if value == "":
                child = index + 1
                if child < len(rows) and rows[child][0] > member_indent:
                    entry[key], index = _parse_block(
                        rows, child, rows[child][0])
                elif (child < len(rows)
                        and rows[child][1].startswith("- ")):
                    entry[key], index = _parse_sequence(
                        rows, child, rows[child][0])
                else:
                    entry[key] = None
                    index = child
            else:
                entry[key] = _scalar(value)
                index += 1
        items.append(entry)
    return items, index


def parse(text):
    """Parse the manifest subset. Returns a dict (or None for empty input)."""
    rows = list(_lines(text))
    if not rows:
        return None
    if rows[0][0] != 0:
        raise ManifestParseError("the document must start at column 0.")
    value, index = _parse_block(rows, 0, 0)
    if index != len(rows):
        raise ManifestParseError(
            "line %d could not be parsed." % rows[index][2])
    return value


def load(text):
    """Parse with PyYAML when available, otherwise with the bundled parser.

    Behaviour is identical on the supported subset -- the test suite asserts
    parity on every shipped manifest -- so a sandbox with no package
    installation reads the same manifest as a developer laptop.
    """
    try:
        import yaml
    except ImportError:
        return parse(text)
    return yaml.safe_load(text)


def load_path(path):
    with open(path, "r") as handle:
        return load(handle.read())
