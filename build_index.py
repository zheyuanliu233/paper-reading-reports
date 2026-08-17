#!/usr/bin/env python3
"""Build a two-level paper index and inject related comparison links."""

from __future__ import annotations

import argparse
import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path


VALUE_SPLIT_RE = re.compile(r"[,，;；|]")
GENERATED_COMPARISON_RE = re.compile(
    r"\n?<!-- GENERATED_COMPARISON_LINKS_START -->.*?"
    r"<!-- GENERATED_COMPARISON_LINKS_END -->\n?",
    re.DOTALL,
)


class MetadataParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.meta: dict[str, str] = {}
        self.title_parts: list[str] = []
        self.links: list[str] = []
        self.in_title = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        values = {key.lower(): value or "" for key, value in attrs}
        lowered = tag.lower()
        if lowered == "meta" and values.get("name"):
            self.meta[values["name"].lower()] = values.get("content", "").strip()
        elif lowered == "title":
            self.in_title = True
        elif lowered == "a" and values.get("href"):
            self.links.append(values["href"].strip())

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
    topics: tuple[str, ...]
    tags: tuple[str, ...]
    href: str
    path: Path


@dataclass(frozen=True)
class Comparison:
    title: str
    summary: str
    href: str
    paper_slugs: tuple[str, ...]


def parse_html(path: Path) -> MetadataParser:
    parser = MetadataParser()
    parser.feed(path.read_text(encoding="utf-8", errors="ignore"))
    return parser


def split_values(raw: str) -> tuple[str, ...]:
    seen: set[str] = set()
    values: list[str] = []
    for item in VALUE_SPLIT_RE.split(raw):
        value = item.strip().lstrip("#")
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            values.append(value)
    return tuple(values)


def collect_reports(topic_dir: Path) -> list[Report]:
    reports: list[Report] = []
    for path in sorted((topic_dir / "reports").glob("*.html")):
        parsed = parse_html(path)
        meta = parsed.meta
        slug = meta.get("paper-slug") or path.stem
        title = meta.get("paper-title") or parsed.title or slug
        all_tags = split_values(meta.get("paper-tags", ""))
        explicit_topics = split_values(meta.get("paper-topics", ""))
        topics = explicit_topics or ("未分类",)
        topic_keys = {topic.casefold() for topic in topics}
        method_tags = tuple(tag for tag in all_tags if tag.casefold() not in topic_keys)
        reports.append(
            Report(
                slug=slug,
                title=title,
                summary=meta.get("paper-summary", ""),
                venue=meta.get("paper-venue", ""),
                topics=topics,
                tags=method_tags,
                href=f"reports/{path.name}",
                path=path,
            )
        )
    return reports


def collect_comparisons(topic_dir: Path) -> list[Comparison]:
    comparisons: list[Comparison] = []
    for path in sorted((topic_dir / "comparisons").glob("*.html")):
        parsed = parse_html(path)
        linked_slugs = []
        for href in parsed.links:
            match = re.search(r"(?:^|/)reports/([^/#?]+)\.html", href)
            if match:
                linked_slugs.append(match.group(1))
        explicit_slugs = split_values(parsed.meta.get("paper-slugs", ""))
        paper_slugs = explicit_slugs or tuple(dict.fromkeys(linked_slugs))
        comparisons.append(
            Comparison(
                title=parsed.meta.get("page-title") or parsed.title or path.stem,
                summary=parsed.meta.get("page-summary", ""),
                href=f"comparisons/{path.name}",
                paper_slugs=paper_slugs,
            )
        )
    return comparisons


def esc(value: str) -> str:
    return html.escape(value, quote=True)


def render_report_card(report: Report, repository: str) -> str:
    tags = "".join(f'<span class="tag">{esc(tag)}</span>' for tag in report.tags)
    tag_list = f'<div class="tag-list">{tags}</div>' if tags else '<div class="tag-list"></div>'
    edit_url = (
        f"https://github.com/{repository}/edit/main/{report.href}" if repository else ""
    )
    return f'''      <article class="paper-card"
        data-slug="{esc(report.slug)}"
        data-title="{esc(report.title)}"
        data-summary="{esc(report.summary)}"
        data-venue="{esc(report.venue)}"
        data-topics="{esc('|'.join(report.topics))}"
        data-tags="{esc('|'.join(report.tags))}"
        data-edit-url="{esc(edit_url)}">
        <a class="paper-card-link" href="{esc(report.href)}">
          {tag_list}
          <h3>{esc(report.title)}</h3>
          <p>{esc(report.summary)}</p>
          <div class="venue">{esc(report.venue)}</div>
        </a>
        <button class="edit-taxonomy" type="button" aria-label="编辑 {esc(report.title)} 的分类和标签">编辑分类</button>
      </article>'''


def render_topic_seed(reports: list[Report]) -> str:
    counts: dict[str, int] = {}
    for report in reports:
        for topic in report.topics:
            counts[topic] = counts.get(topic, 0) + 1
    return "\n".join(
        f'      <button class="topic-folder" type="button" data-topic="{esc(topic)}">'
        f'<span class="folder-tab"></span><strong>{esc(topic)}</strong>'
        f'<span>{count} 篇论文</span></button>'
        for topic, count in sorted(counts.items(), key=lambda item: item[0].casefold())
    )


def comparison_links_for(report: Report, comparisons: list[Comparison]) -> list[Comparison]:
    return [item for item in comparisons if report.slug in item.paper_slugs]


def inject_comparison_links(reports: list[Report], comparisons: list[Comparison]) -> None:
    for report in reports:
        text = report.path.read_text(encoding="utf-8", errors="ignore")
        text = GENERATED_COMPARISON_RE.sub("\n", text)
        related = comparison_links_for(report, comparisons)
        if related:
            links = "".join(
                f'<a href="../{esc(item.href)}">{esc(item.title)}</a>' for item in related
            )
            block = (
                "\n<!-- GENERATED_COMPARISON_LINKS_START -->\n"
                '<nav class="related-comparisons" aria-label="相关对比报告">'
                '<span>相关对比</span>' + links + "</nav>\n"
                "<!-- GENERATED_COMPARISON_LINKS_END -->\n"
            )
            header_end = text.lower().find("</header>")
            if header_end >= 0:
                text = text[:header_end] + block + text[header_end:]
            else:
                body_start = text.lower().find("<body>")
                insert_at = body_start + len("<body>") if body_start >= 0 else 0
                text = text[:insert_at] + block + text[insert_at:]
        report.path.write_text(text, encoding="utf-8")


def existing_site_metadata(topic_dir: Path) -> tuple[str, str, str]:
    index = topic_dir / "index.html"
    if not index.exists():
        return "", "", ""
    parsed = parse_html(index)
    return (
        parsed.meta.get("topic-title", ""),
        parsed.meta.get("topic-description", ""),
        parsed.meta.get("source-repository", ""),
    )


def build(
    topic_dir: Path,
    title: str | None,
    description: str | None,
    repository: str | None,
    template: Path,
) -> Path:
    if not topic_dir.is_dir():
        raise SystemExit(f"Topic directory does not exist: {topic_dir}")
    reports = collect_reports(topic_dir)
    comparisons = collect_comparisons(topic_dir)
    inject_comparison_links(reports, comparisons)
    previous_title, previous_description, previous_repository = existing_site_metadata(topic_dir)
    site_title = title or previous_title or topic_dir.name.replace("-", " ").title()
    site_description = description if description is not None else previous_description
    source_repository = repository if repository is not None else previous_repository

    output = template.read_text(encoding="utf-8")
    replacements = {
        "{{TOPIC_DISPLAY_NAME}}": esc(site_title),
        "{{TOPIC_DESCRIPTION}}": esc(site_description),
        "{{SOURCE_REPOSITORY}}": esc(source_repository),
        "{{PAPER_COUNT}}": str(len(reports)),
        "{{TOPIC_FOLDERS}}": render_topic_seed(reports),
        "{{PAPER_CARDS}}": "\n".join(render_report_card(item, source_repository) for item in reports),
    }
    for placeholder, value in replacements.items():
        output = output.replace(placeholder, value)

    destination = topic_dir / "index.html"
    destination.write_text(output, encoding="utf-8")
    print(
        f"Built {destination} with {len(reports)} report(s), "
        f"{len({topic for report in reports for topic in report.topics})} topic(s), "
        f"and {len(comparisons)} comparison(s)."
    )
    return destination


def main() -> None:
    default_template = Path(__file__).resolve().parent / "assets" / "templates" / "index.html"
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("topic_dir", type=Path)
    parser.add_argument("--title", help="Site title; existing index metadata is reused when omitted")
    parser.add_argument("--description", help="Site description; existing metadata is reused when omitted")
    parser.add_argument("--repository", help="GitHub owner/repo used by permanent edit links")
    parser.add_argument("--template", type=Path, default=default_template)
    args = parser.parse_args()
    build(
        args.topic_dir.resolve(),
        args.title,
        args.description,
        args.repository,
        args.template.resolve(),
    )


if __name__ == "__main__":
    main()
