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

import re as _re

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


_BLOCK_TOKEN = "__miniyaml_block_%d__"
_BLOCK_HEADER = _re.compile(
    r"^(\s*)(-\s+)?([A-Za-z0-9_.\-]+)\s*:\s*([>|])([-+]?)\s*$")


def _extract_block_scalars(text):
    """Fold `key: >` and `key: |` blocks out of the text before tokenising.

    Block scalars carry prose, and prose is why they exist: a finding's
    rationale is a paragraph, not a phrase. The tokeniser below strips
    comments and blank lines, both of which are literal content inside a
    block, so the block has to come out first.

    Each block is replaced by a bare placeholder token and restored after the
    structure is parsed. Going via a placeholder rather than a quoted string
    keeps prose containing quotes and backslashes intact -- `_scalar` strips
    quotes but does not decode escapes, so round-tripping through one would
    corrupt exactly the text this exists to carry.
    """
    lines = text.splitlines()
    out, blocks, index = [], {}, 0

    while index < len(lines):
        match = _BLOCK_HEADER.match(lines[index])
        if not match:
            out.append(lines[index])
            index += 1
            continue

        prefix, dash, key, style, chomp = match.groups()
        dash = dash or ""
        # A block under a sequence entry is indented relative to the dash.
        base = len(prefix) + len(dash)
        index += 1

        body = []
        while index < len(lines):
            line = lines[index]
            if not line.strip():
                body.append("")
                index += 1
                continue
            if len(line) - len(line.lstrip(" ")) <= base:
                break
            body.append(line)
            index += 1

        while body and not body[-1].strip():
            body.pop()

        content = _fold(body, style)
        if chomp != "-" and content:
            content += "\n"
        elif chomp == "+":
            content += "\n"

        token = _BLOCK_TOKEN % len(blocks)
        blocks[token] = content
        out.append("%s%s%s: %s" % (prefix, dash, key, token))

    return "\n".join(out), blocks


def _fold(body, style):
    """Apply YAML block-scalar semantics to the collected lines."""
    if not body:
        return ""
    indents = [len(l) - len(l.lstrip(" ")) for l in body if l.strip()]
    strip = min(indents) if indents else 0
    rows = [l[strip:] if l.strip() else "" for l in body]

    if style == "|":
        return "\n".join(rows)

    # Folded: blank lines become newlines, other lines join with a space.
    parts, current = [], []
    for row in rows:
        if row:
            current.append(row)
        else:
            parts.append(" ".join(current))
            current = []
    parts.append(" ".join(current))
    return "\n".join(parts)


def _restore_blocks(value, blocks):
    """Put the folded prose back where its placeholder sits."""
    if isinstance(value, dict):
        return {k: _restore_blocks(v, blocks) for k, v in value.items()}
    if isinstance(value, list):
        return [_restore_blocks(v, blocks) for v in value]
    if isinstance(value, str) and value in blocks:
        return blocks[value]
    return value


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
    text, blocks = _extract_block_scalars(text)
    rows = list(_lines(text))
    if not rows:
        return None
    if rows[0][0] != 0:
        raise ManifestParseError("the document must start at column 0.")
    value, index = _parse_block(rows, 0, 0)
    if index != len(rows):
        raise ManifestParseError(
            "line %d could not be parsed." % rows[index][2])
    return _restore_blocks(value, blocks) if blocks else value


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
