#!/usr/bin/env python3
"""Build a searchable, tag-filterable paper-reading index from report metadata."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


TAG_SPLIT_RE = re.compile(r"[,，;；|]")


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        if tag.lower() == "meta" and values.get("name"):
            self.meta[values["name"].lower()] = values.get("content", "").strip()
        elif tag.lower() == "title":
            self.in_title = True

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "title":
            self.in_title = False

    def handle_data(self, data: str) -> None:
        if self.in_title:
            self.title_parts.append(data)

    @property
    def title(self) -> str:
        return " ".join("".join(self.title_parts).split())


@dataclass(frozen=True)
class Report:
    slug: str
    title: str
    summary: str
    venue: str
    tags: tuple[str, ...]
    href: str


@dataclass(frozen=True)
class Comparison:
    title: str
    summary: str
    href: str


def parse_html(path: Path) -> MetadataParser:
    parser = MetadataParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return parser


def split_tags(raw: str) -> tuple[str, ...]:
    seen: set[str] = set()
    tags: list[str] = []
    for item in TAG_SPLIT_RE.split(raw):
        tag = item.strip().lstrip("#")
        key = tag.casefold()
        if tag and key not in seen:
            seen.add(key)
            tags.append(tag)
    return tuple(tags)


def collect_reports(topic_dir: Path) -> list[Report]:
    reports: list[Report] = []
    for path in sorted((topic_dir / "reports").glob("*.html")):
        parsed = parse_html(path)
        meta = parsed.meta
        slug = meta.get("paper-slug") or path.stem
        title = meta.get("paper-title") or parsed.title or slug
        reports.append(
            Report(
                slug=slug,
                title=title,
                summary=meta.get("paper-summary", ""),
                venue=meta.get("paper-venue", ""),
                tags=split_tags(meta.get("paper-tags", "")),
                href=f"reports/{path.name}",
            )
        )
    return reports


def collect_comparisons(topic_dir: Path) -> list[Comparison]:
    comparisons: list[Comparison] = []
    for path in sorted((topic_dir / "comparisons").glob("*.html")):
        parsed = parse_html(path)
        comparisons.append(
            Comparison(
                title=parsed.meta.get("page-title") or parsed.title or path.stem,
                summary=parsed.meta.get("page-summary", ""),
                href=f"comparisons/{path.name}",
            )
        )
    return comparisons


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_report_card(report: Report) -> str:
    tags = "".join(f'<span class="tag">{esc(tag)}</span>' for tag in report.tags)
    tag_list = f'<div class="tag-list">{tags}</div>' if tags else ""
    return f'''      <a class="card paper-card" href="{esc(report.href)}"
         data-title="{esc(report.title)}"
         data-summary="{esc(report.summary)}"
         data-venue="{esc(report.venue)}"
         data-tags="{esc('|'.join(report.tags))}">
        {tag_list}
        <h3>{esc(report.title)}</h3>
        <p>{esc(report.summary)}</p>
        <div class="venue">{esc(report.venue)}</div>
      </a>'''


def render_comparison_card(comparison: Comparison) -> str:
    summary = f"<p>{esc(comparison.summary)}</p>" if comparison.summary else ""
    return f'''      <a class="card" href="{esc(comparison.href)}">
        <div class="tag-list"><span class="tag cmp">对比</span></div>
        <h3>{esc(comparison.title)}</h3>
        {summary}
      </a>'''


def existing_topic_metadata(topic_dir: Path) -> tuple[str, str]:
    index = topic_dir / "index.html"
    if not index.exists():
        return "", ""
    parsed = parse_html(index)
    return parsed.meta.get("topic-title", ""), parsed.meta.get("topic-description", "")


def build(topic_dir: Path, title: str | None, description: str | None, template: Path) -> Path:
    if not topic_dir.is_dir():
        raise SystemExit(f"Topic directory does not exist: {topic_dir}")
    reports = collect_reports(topic_dir)
    comparisons = collect_comparisons(topic_dir)
    previous_title, previous_description = existing_topic_metadata(topic_dir)
    topic_title = title or previous_title or topic_dir.name.replace("-", " ").title()
    topic_description = description if description is not None else previous_description

    output = template.read_text(encoding="utf-8")
    replacements = {
        "{{TOPIC_DISPLAY_NAME}}": topic_title,
        "{{TOPIC_DESCRIPTION}}": topic_description,
        "{{PAPER_COUNT}}": str(len(reports)),
        "{{PAPER_CARDS}}": "\n".join(render_report_card(item) for item in reports),
        "{{COMPARISON_CARDS}}": "\n".join(render_comparison_card(item) for item in comparisons),
        "{{COMPARISON_SECTION_HIDDEN}}": " hidden" if not comparisons else "",
    }
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, value if placeholder.endswith("CARDS}}") else esc(value))

    destination = topic_dir / "index.html"
    destination.write_text(output, encoding="utf-8")
    print(f"Built {destination} with {len(reports)} report(s) and {len(comparisons)} comparison(s).")
    return destination


def main() -> None:
    default_template = Path(__file__).resolve().parent / "assets" / "templates" / "index.html"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic_dir", type=Path)
    parser.add_argument("--title", help="Topic title; existing index metadata is reused when omitted")
    parser.add_argument("--description", help="Topic description; existing index metadata is reused when omitted")
    parser.add_argument("--template", type=Path, default=default_template)
    args = parser.parse_args()
    build(args.topic_dir.resolve(), args.title, args.description, args.template.resolve())


if __name__ == "__main__":
    main()
