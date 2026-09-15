from html import escape
from pathlib import Path
from xml.etree.ElementTree import Element, ParseError

import pymupdf
from defusedxml import DefusedXmlException
from defusedxml.ElementTree import parse as parse_xml

_MAX_DEPTH = 200
_MAX_TEXT_CHARS = 2000
_MAX_PAGES = 5000

# No font-size declarations here: mupdf's Story layout engine silently stops
# paginating (reporting a page as "complete" while most content overflows
# off-page, undetected) once a document needs more than ~2 pages if any
# element sets an explicit font-size. Visual hierarchy comes from
# font-weight/color/text-transform instead, relying on the engine's default
# sizes (h1 defaults to 24pt, everything else to 12pt).
_CSS = """
body { font-family: sans-serif; color: #1c2420; }
h1 { margin: 0 0 4px 0; word-break: break-all; }
.path { color: #6b7a72; margin: 0 0 14px 0; word-break: break-all; }
.node { margin: 0 0 2px 0; }
.tag { font-weight: bold; color: #14532d; }
.attr { color: #6b7a72; }
.text { color: #1c2420; }
.children { margin: 2px 0 2px 0; padding-left: 16px; border-left: 1px solid #dfe7e2; }
"""


class InvalidXmlError(ValueError):
    pass


def _local_name(tag: str) -> str:
    return tag.rsplit("}", 1)[-1] if "}" in tag else tag


def _truncate(text: str) -> str:
    if len(text) <= _MAX_TEXT_CHARS:
        return text
    return f"{text[:_MAX_TEXT_CHARS]}… ({len(text):,} chars total, truncated)"


def _render_element(el: Element, depth: int) -> str:
    if depth > _MAX_DEPTH:
        return "<div>&hellip;</div>"

    tag = escape(_local_name(el.tag))
    attrs = " ".join(f'{escape(_local_name(k))}="{escape(str(v))}"' for k, v in el.attrib.items())
    attrs_html = f' <span class="attr">{attrs}</span>' if attrs else ""

    children = list(el)
    text = (el.text or "").strip()

    if not children:
        text_html = f": <span class=\"text\">{escape(_truncate(text))}</span>" if text else ""
        return f'<div class="node"><span class="tag">{tag}</span>{attrs_html}{text_html}</div>'

    inner = "".join(_render_element(child, depth + 1) for child in children)
    text_html = f'<div class="text">{escape(_truncate(text))}</div>' if text else ""
    return (
        f'<div class="node"><span class="tag">{tag}</span>{attrs_html}{text_html}'
        f'<div class="children">{inner}</div></div>'
    )


class XmlConverter:
    def convert(self, xml_path: Path, out_path: Path, source_name: str | None = None) -> Path:
        try:
            tree = parse_xml(xml_path)
        except (ParseError, DefusedXmlException) as exc:
            raise InvalidXmlError(f"invalid or unsafe XML: {exc}") from exc

        root = tree.getroot()
        title = escape(_local_name(root.tag))
        body = _render_element(root, 0)
        subtitle = escape(source_name or xml_path.name)
        html = f"<style>{_CSS}</style><h1>{title}</h1><div class=\"path\">{subtitle}</div><div class=\"children\">{body}</div>"

        out_path.parent.mkdir(parents=True, exist_ok=True)
        story = pymupdf.Story(html=html)
        writer = pymupdf.DocumentWriter(out_path)
        mediabox = pymupdf.paper_rect("a4")
        where = mediabox + (36, 36, -36, -36)
        more = 1
        pages = 0
        while more and pages < _MAX_PAGES:
            device = writer.begin_page(mediabox)
            more, _ = story.place(where)
            story.draw(device)
            writer.end_page()
            pages += 1
        writer.close()
        return out_path
