#!/usr/bin/env python3
"""
Publish a Markdown file to Zhihu article editor using browser automation.

This script does not rely on a private Zhihu API. It opens the article editor
in a persistent Chromium profile, reuses your login session, fills the title
and body, and leaves the page in draft mode by default. Use --publish to click
the publish button automatically after content is filled.
"""

from __future__ import annotations

import argparse
import html
import re
import sys
import time
from pathlib import Path


EDITOR_URLS = [
    "https://zhuanlan.zhihu.com/write",
    "https://www.zhihu.com/creator/content/article/write",
    "https://www.zhihu.com/creator",
]

TITLE_SELECTORS = [
    "input[placeholder*='标题']",
    "textarea[placeholder*='标题']",
    "[contenteditable='true'][data-placeholder*='标题']",
]

EDITOR_SELECTORS = [
    ".public-DraftEditor-content [contenteditable='true']",
    ".DraftEditor-root [contenteditable='true']",
    "[contenteditable='true'][data-placeholder*='写']",
    "[contenteditable='true'][data-placeholder*='内容']",
    "div[contenteditable='true']",
]

PUBLISH_SELECTORS = [
    "button:has-text('发布')",
    "button:has-text('发表')",
    "button:has-text('发布文章')",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Open Zhihu editor and fill title/content from a markdown file."
    )
    parser.add_argument("md_file", help="Path to the markdown file.")
    parser.add_argument(
        "--title",
        help="Override title. Defaults to YAML front matter title, first H1, or file stem.",
    )
    parser.add_argument(
        "--profile-dir",
        default=str(Path.home() / ".cache" / "zhihu_publisher"),
        help="Persistent Chromium profile directory.",
    )
    parser.add_argument(
        "--publish",
        action="store_true",
        help="Click the publish button after filling content.",
    )
    parser.add_argument(
        "--mode",
        choices=("plain", "html"),
        default="plain",
        help="plain: insert Markdown text directly; html: convert simple Markdown to HTML before inserting.",
    )
    parser.add_argument(
        "--wait-login-seconds",
        type=int,
        default=180,
        help="How long to wait for you to complete login manually.",
    )
    return parser.parse_args()


def load_markdown(path: Path) -> tuple[str, str]:
    text = path.read_text(encoding="utf-8")
    title = None
    body = text

    if text.startswith("---\n"):
        end = text.find("\n---\n", 4)
        if end != -1:
            front_matter = text[4:end]
            body = text[end + 5 :].lstrip()
            for line in front_matter.splitlines():
                if line.lower().startswith("title:"):
                    title = line.split(":", 1)[1].strip().strip("'\"")
                    break

    if title is None:
        lines = body.splitlines()
        if lines and lines[0].startswith("# "):
            title = lines[0][2:].strip()
            body = "\n".join(lines[1:]).lstrip()

    if title is None:
        title = path.stem

    return title, body


def markdown_to_html(markdown_text: str) -> str:
    # Minimal fallback converter to avoid hard dependency on python-markdown.
    lines = markdown_text.splitlines()
    html_lines: list[str] = []
    in_code = False
    code_lang = ""

    for raw_line in lines:
        line = raw_line.rstrip("\n")
        if line.startswith("```"):
            if not in_code:
                code_lang = line[3:].strip()
                lang_attr = f' class="language-{html.escape(code_lang)}"' if code_lang else ""
                html_lines.append(f"<pre><code{lang_attr}>")
                in_code = True
            else:
                html_lines.append("</code></pre>")
                in_code = False
                code_lang = ""
            continue

        if in_code:
            html_lines.append(html.escape(line))
            continue

        if not line.strip():
            html_lines.append("")
            continue

        heading_match = re.match(r"^(#{1,6})\s+(.*)$", line)
        if heading_match:
            level = len(heading_match.group(1))
            content = html.escape(heading_match.group(2).strip())
            html_lines.append(f"<h{level}>{content}</h{level}>")
            continue

        list_match = re.match(r"^[-*]\s+(.*)$", line)
        if list_match:
            html_lines.append(f"<li>{html.escape(list_match.group(1).strip())}</li>")
            continue

        html_lines.append(f"<p>{html.escape(line)}</p>")

    rendered = "\n".join(html_lines)
    rendered = re.sub(r"(<li>.*?</li>\n?)+", lambda m: f"<ul>\n{m.group(0)}</ul>", rendered, flags=re.S)
    rendered = rendered.replace("\n\n", "\n")
    return rendered


def require_playwright():
    try:
        from playwright.sync_api import sync_playwright  # type: ignore
    except Exception as exc:  # pragma: no cover - dependency guard
        raise SystemExit(
            "Missing dependency: playwright\n"
            "Install with:\n"
            "  pip install playwright\n"
            "  python -m playwright install chromium"
        ) from exc
    return sync_playwright


def first_locator(page, selectors: list[str]):
    for selector in selectors:
        locator = page.locator(selector)
        try:
            if locator.count() > 0:
                return locator.first
        except Exception:
            continue
    return None


def wait_for_editor(page, timeout_s: int):
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        title_locator = first_locator(page, TITLE_SELECTORS)
        editor_locator = first_locator(page, EDITOR_SELECTORS)
        if title_locator is not None and editor_locator is not None:
            return title_locator, editor_locator
        time.sleep(1)
    raise TimeoutError(
        "Could not find Zhihu editor fields. "
        "If login is required, complete it in the browser and retry."
    )


def fill_title(locator, title: str):
    locator.click()
    try:
        locator.fill("")
        locator.fill(title)
    except Exception:
        locator.evaluate("(el) => { if ('value' in el) el.value = ''; }")
        locator.type(title)


def fill_editor_plain(locator, body: str):
    locator.click()
    locator.evaluate("(el) => { el.innerHTML = ''; el.innerText = ''; }")
    locator.press("Control+A")
    locator.press("Backspace")
    locator.type(body, delay=5)


def fill_editor_html(locator, body_html: str):
    locator.click()
    locator.evaluate(
        """(el, bodyHtml) => {
            el.focus();
            if ('innerHTML' in el) {
                el.innerHTML = '';
            }
            document.execCommand('selectAll', false);
            document.execCommand('delete', false);
            document.execCommand('insertHTML', false, bodyHtml);
        }""",
        body_html,
    )


def click_publish(page):
    locator = first_locator(page, PUBLISH_SELECTORS)
    if locator is None:
        raise RuntimeError("Could not find publish button on the current Zhihu page.")
    locator.click()


def main() -> int:
    args = parse_args()
    md_path = Path(args.md_file).expanduser().resolve()
    if not md_path.is_file():
        print(f"Markdown file not found: {md_path}", file=sys.stderr)
        return 1

    title, body = load_markdown(md_path)
    if args.title:
        title = args.title

    sync_playwright = require_playwright()

    with sync_playwright() as playwright:
        context = playwright.chromium.launch_persistent_context(
            user_data_dir=args.profile_dir,
            headless=False,
        )
        page = context.pages[0] if context.pages else context.new_page()

        last_error = None
        for url in EDITOR_URLS:
            try:
                page.goto(url, wait_until="domcontentloaded", timeout=30000)
                title_locator, editor_locator = wait_for_editor(page, args.wait_login_seconds)
                fill_title(title_locator, title)
                if args.mode == "html":
                    fill_editor_html(editor_locator, markdown_to_html(body))
                else:
                    fill_editor_plain(editor_locator, body)

                if args.publish:
                    click_publish(page)
                    print("Content filled and publish button clicked.")
                else:
                    print("Content filled. Draft page is open for manual review.")
                print(f"Profile dir: {args.profile_dir}")
                print("Keep the browser open if you want to continue editing.")
                return 0
            except Exception as exc:
                last_error = exc
                continue
        print(f"Failed to open Zhihu editor or fill content: {last_error}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
