from html.parser import HTMLParser
from pathlib import Path
import re
from urllib.parse import parse_qs, urlsplit

from django.core.paginator import Paginator
from django.contrib.staticfiles import finders
from django.template.loader import render_to_string
from django.test import RequestFactory, SimpleTestCase


class PageMarkup(HTMLParser):
    def __init__(self, markup):
        super().__init__()
        self.elements = []
        self.feed(markup)

    def handle_starttag(self, tag, attrs):
        self.elements.append((tag, dict(attrs)))


class InterfaceComponentTests(SimpleTestCase):
    def test_pagination_preserves_filters_and_replaces_page(self):
        request = RequestFactory().get("/example/", {"status": ["Active", "Pending"], "q": 'A&B "test"', "page": "2"})
        page = Paginator(list(range(25)), 10).page(2)
        markup = render_to_string("includes/pagination.html", {"page_obj": page, "request": request})
        links = [attrs for tag, attrs in PageMarkup(markup).elements if tag == "a"]
        self.assertEqual(len(links), 4)
        for link in links:
            self.assertTrue(link["href"].startswith("?"))
            query = parse_qs(urlsplit(link["href"]).query)
            self.assertEqual(query["status"], ["Active", "Pending"])
            self.assertEqual(query["q"], ['A&B "test"'])
            self.assertEqual(len(query["page"]), 1)
        self.assertIn('aria-current="page"', markup)
        self.assertIn("Page 2 of 3", markup)

    def test_pagination_first_last_and_single_page_states(self):
        paginator = Paginator(list(range(25)), 10)
        first = render_to_string("includes/pagination.html", {"page_obj": paginator.page(1)})
        last = render_to_string("includes/pagination.html", {"page_obj": paginator.page(3)})
        self.assertNotIn('rel="prev"', first)
        self.assertIn('href="?page=2"', first)
        self.assertNotIn('rel="next"', last)
        single = render_to_string("includes/pagination.html", {"page_obj": Paginator([], 10).page(1)})
        self.assertNotIn("<nav", single)

    def test_empty_state_escapes_content(self):
        markup = render_to_string("includes/empty_state.html", {"empty_title": "No visits", "empty_message": "<script>test</script>"})
        self.assertIn("No visits", markup)
        self.assertNotIn("<script>", markup)
        self.assertIn("&lt;script&gt;", markup)

    def test_shared_palettes_keep_text_and_control_contrast(self):
        stylesheet = Path(finders.find("css/includes/site.css")).read_text()

        def luminance(color):
            channels = [int(color[index:index + 2], 16) / 255 for index in (1, 3, 5)]
            linear = [channel / 12.92 if channel <= 0.04045 else ((channel + 0.055) / 1.055) ** 2.4 for channel in channels]
            return sum(value * weight for value, weight in zip(linear, (0.2126, 0.7152, 0.0722)))

        selectors = (r':root\s*\{([^}]+)', r'\[data-theme="dark"\]\s*\{([^}]+)')
        for selector in selectors:
            palette = dict(re.findall(r'--([\w-]+):\s*(#[0-9a-fA-F]{6})', re.search(selector, stylesheet).group(1)))
            pairs = [(foreground, background, 4.5) for foreground in ("ink", "muted", "link") for background in ("paper", "surface")]
            pairs += [("error", "error-bg", 4.5), ("button-ink", "button", 4.5), ("line", "paper", 3), ("focus", "surface", 3)]
            for foreground, background, minimum in pairs:
                with self.subTest(selector=selector, foreground=foreground, background=background):
                    darkest, lightest = sorted((luminance(palette[foreground]), luminance(palette[background])))
                    self.assertGreaterEqual((lightest + 0.05) / (darkest + 0.05), minimum)
