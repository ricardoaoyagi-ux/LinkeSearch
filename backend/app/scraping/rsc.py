"""Minimal React Server Components (RSC) stream -> safe HTML converter.

LinkedIn's SDUI endpoints answer with RSC "flight" rows (`<hexid>:<json>`). Elements are
`["$", tag, key, props]`; strings starting with `$` reference other rows. Only a small allowlist of
text-formatting tags is emitted, everything else is flattened to its children.
"""

import html
import json
import re

_ROW_RE = re.compile(r"^([0-9a-f]+):(.*)$")
_REF_RE = re.compile(r"^\$[LF@]?([0-9a-f]+)$")
_ALLOWED_TAGS = {"p", "br", "ul", "ol", "li", "strong", "b", "em", "i", "u", "h3", "h4", "div"}
_DROPPED_TAGS = {"button", "svg", "img", "script", "style", "figure", "a", "input"}
_VOID_TAGS = {"br"}
_HEADING_TEXT = "About the job"
_MAX_DEPTH = 200


def parse_rows(stream: str) -> dict[str, object]:
    rows: dict[str, object] = {}
    for line in stream.splitlines():
        match = _ROW_RE.match(line)
        if not match:
            continue
        key, raw = match.groups()
        if raw.startswith("I["):  # client component import
            rows[key] = {"$import": True}
            continue
        if raw.startswith("T"):  # text chunk: T<hexlen>,<text>
            rows[key] = raw.split(",", 1)[1] if "," in raw else ""
            continue
        try:
            rows[key] = json.loads(raw)
        except json.JSONDecodeError:
            continue
    return rows


class _Renderer:
    def __init__(self, rows: dict[str, object]):
        self.rows = rows

    def render(self, node: object, depth: int = 0) -> str:
        if depth > _MAX_DEPTH or node is None or isinstance(node, bool):
            return ""
        if isinstance(node, (int, float)):
            return str(node)
        if isinstance(node, str):
            return self._render_string(node, depth)
        if isinstance(node, list):
            if len(node) == 4 and node[0] == "$" and isinstance(node[3], dict | type(None)):
                return self._render_element(node[1], node[3] or {}, depth)
            return "".join(self.render(child, depth + 1) for child in node)
        return ""

    def _render_string(self, value: str, depth: int) -> str:
        if value.startswith("$$"):
            return html.escape(value[1:])
        if value.startswith("$"):
            match = _REF_RE.match(value)
            if match and match.group(1) in self.rows:
                target = self.rows[match.group(1)]
                if isinstance(target, dict) and target.get("$import"):
                    return ""
                return self.render(target, depth + 1)
            return ""
        return html.escape(value)

    def _render_element(self, tag: object, props: dict, depth: int) -> str:
        children = props.get("children")
        if children is None:
            # Client components often carry their content in a nested props object (e.g. textProps)
            children = next((v["children"] for v in props.values() if isinstance(v, dict) and "children" in v), None)
        if isinstance(tag, str) and not tag.startswith("$"):
            if tag in _DROPPED_TAGS:
                return ""
            if tag in ("h1", "h2") and _text_of(children) == _HEADING_TEXT:
                return ""
            inner = self.render(children, depth + 1)
            if tag in _VOID_TAGS:
                return f"<{tag}>"
            if tag in _ALLOWED_TAGS:
                return f"<{tag}>{inner}</{tag}>"
            return inner
        return self.render(children, depth + 1)


def _text_of(children: object) -> str:
    if isinstance(children, str):
        return children.strip()
    if isinstance(children, list) and len(children) == 1 and isinstance(children[0], str):
        return children[0].strip()
    return ""


def _tidy(markup: str) -> str:
    markup = re.sub(r"<div>\s*</div>", "", markup)
    markup = re.sub(r"(<br>\s*){3,}", "<br><br>", markup)
    return markup.strip()


def rsc_to_html(stream: str) -> str:
    rows = parse_rows(stream)
    if "0" not in rows:
        return ""
    return _tidy(_Renderer(rows).render(rows["0"]))
