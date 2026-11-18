"""Tests for Markdown link activation targets."""

import importlib.util
from pathlib import Path
import unittest


PATTERNS_PATH = Path(__file__).parents[2] / "addon" / "globalPlugins" / "markdownNavigator" / "patterns.py"
SPEC = importlib.util.spec_from_file_location("markdownNavigatorLinkPatterns", PATTERNS_PATH)
assert SPEC and SPEC.loader
patterns = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patterns)


class TestLinkNavigation(unittest.TestCase):
	"""Verify Markdown links resolve to their intended activation targets."""

	def test_inline_link_contains_label_and_destination(self) -> None:
		"""Recognize an anchor link anywhere within its label or destination."""
		text = "See [Document Formatting](#DocumentFormattingSettings) now."
		linkEnd = text.index(")")
		for offset in (text.index("Document"), text.index("#Document"), text.index(")")):
			with self.subTest(offset=offset):
				self.assertEqual(
					patterns.getMarkdownLinkAtOffset(text, offset),
					(4, linkEnd, "#DocumentFormattingSettings"),
				)

	def test_external_links_and_nested_parentheses(self) -> None:
		"""Keep complete destinations when URLs contain parentheses or titles."""
		cases = {
			"[site](https://example.com/a_(b))": "https://example.com/a_(b)",
			'[site](<https://example.com/a b> "title")': "https://example.com/a b",
		}
		for text, destination in cases.items():
			with self.subTest(text=text):
				link = patterns.getMarkdownLinkAtOffset(text, 1)
				self.assertIsNotNone(link)
				self.assertEqual(link[2], destination)

	def test_images_and_malformed_links_are_ignored(self) -> None:
		"""Avoid activating image syntax and incomplete links as ordinary links."""
		self.assertIsNone(patterns.getMarkdownLinkAtOffset("![image](image.png)", 3))
		self.assertIsNone(patterns.getMarkdownLinkAtOffset("[broken](https://example.com", 2))

	def test_explicit_heading_anchor(self) -> None:
		"""Find only headings carrying the requested explicit anchor."""
		lines = ["# Overview", "#### Document Formatting {#DocumentFormattingSettings}\n"]
		getText = lines.__getitem__
		self.assertEqual(patterns.findHeadingAnchor(getText, len(lines), "DocumentFormattingSettings"), 1)
		self.assertIsNone(patterns.findHeadingAnchor(getText, len(lines), "Overview"))


if __name__ == "__main__":
	unittest.main()
