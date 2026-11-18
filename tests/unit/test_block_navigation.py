"""Regression tests for Markdown container navigation."""

import importlib.util
from pathlib import Path
import unittest


PATTERNS_PATH = Path(__file__).parents[2] / "addon" / "globalPlugins" / "markdownNavigator" / "patterns.py"
SPEC = importlib.util.spec_from_file_location("markdownNavigatorBlockPatterns", PATTERNS_PATH)
assert SPEC and SPEC.loader
patterns = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patterns)


class TestBlockNavigation(unittest.TestCase):
	"""Check user-visible destinations for containers and nested lists."""

	def test_issue17_destinations(self) -> None:
		"""Exit each list at its own boundary, including both reported failures."""
		lines = [
			"The first list with sublists:",
			"* abc",
			"  * def",
			"  * ghi",
			"* jkl",
			"* mno",
			"  * pqr",
			"  * stu",
			"* vwx",
			"",
			"The second list:",
			"* 123",
			"  * 000",
			"* 456",
			"  * 789",
		]
		for start, direction, expected in (
			(12, 1, 13),
			(1, 1, 9),
			(3, 1, 4),
			(5, 1, 9),
			(7, -1, 6),
			(3, -1, 2),
			(8, -1, 1),
			(12, -1, 12),
		):
			with self.subTest(start=start, direction=direction):
				self.assertEqual(
					patterns.getBlockBoundary(lines.__getitem__, len(lines), start, direction),
					expected,
				)

	def test_deeper_lists_and_tabs(self) -> None:
		"""Keep descendants inside a list and use Markdown's four-column tab stops."""
		lines = ["1. parent", "\t- child", "        + grandchild", "    - sibling", "2. next"]
		self.assertEqual(patterns.getListBlockStarts(lines.__getitem__, len(lines)), [0, 1, 2])
		for start, direction, expected in ((1, 1, 4), (2, 1, 3), (3, -1, 1), (4, -1, 0)):
			with self.subTest(start=start, direction=direction):
				self.assertEqual(
					patterns.getBlockBoundary(lines.__getitem__, len(lines), start, direction),
					expected,
				)

	def test_other_blocks(self) -> None:
		"""Exit tables and blockquotes, but keep reverse navigation at their first line."""
		for block in (["| a |", "| b |"], ["> a", "> b"]):
			lines = ["before", *block, "after"]
			with self.subTest(block=block):
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 1, 1), 3)
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 2, -1), 1)
				self.assertIsNone(patterns.getBlockBoundary(lines.__getitem__, len(lines), 0, 1))

	def test_list_paragraph_continuations(self) -> None:
		"""Navigate from both list items and their wrapped text at the correct nesting level."""
		lines = [
			"* Item 1.",
			"Continuation 1.",
			"* Item 2",
			"Continuation 2.",
			"  * Item 2.1",
			"* Item 3",
			"",
		]
		for start, direction, expected in ((0, 1, 6), (1, 1, 6), (3, -1, 0), (5, -1, 0), (4, -1, 4)):
			with self.subTest(start=start, direction=direction):
				self.assertEqual(
					patterns.getBlockBoundary(lines.__getitem__, len(lines), start, direction),
					expected,
				)
		lines = ["* Parent", "  * Child", "wrapped", "still wrapped", "* Next"]
		self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 3, -1), 1)
		self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 2, 1), 4)

	def test_list_navigation_groups_continuations(self) -> None:
		"""Treat unindented paragraph continuations as part of the same list for L navigation."""
		lines = ["* Item 1", "Continuation paragraph of item 1", "* Item 2", ""]
		self.assertEqual(
			[patterns.isListBlockLine(lines.__getitem__, index) for index in range(len(lines))],
			[True, True, True, False],
		)
		self.assertEqual(patterns.getListBlockStarts(lines.__getitem__, len(lines)), [0])

	def test_list_navigation_includes_nested_blocks(self) -> None:
		"""Expose nested lists as separate L navigation targets."""
		lines = ["* ", "* item1", "  * subitem1", "*  item 2"]
		self.assertEqual(patterns.getListBlockStarts(lines.__getitem__, len(lines)), [0, 2])

		lines = ["* parent", "  * child", "* next", "  * child2"]
		self.assertEqual(patterns.getListBlockStarts(lines.__getitem__, len(lines)), [0, 1, 3])

	def test_list_navigation_ignores_fenced_code(self) -> None:
		"""Do not treat list-like text inside fenced code as a Markdown list."""
		for fence in ("```", "~~~"):
			lines = [fence, "* code", fence, "* item"]
			with self.subTest(fence=fence):
				self.assertEqual(patterns.getListBlockStarts(lines.__getitem__, len(lines)), [3])
				self.assertFalse(patterns.isListBlockLine(lines.__getitem__, 1))
				self.assertIsNone(patterns.getBlockBoundary(lines.__getitem__, len(lines), 1, 1))
		lines = ["```python", "```python", "* code", "```", "* item"]
		self.assertEqual(patterns.getListBlockStarts(lines.__getitem__, len(lines)), [4])

	def test_continuations_stop_at_block_boundaries(self) -> None:
		"""Keep adjacent blocks and standalone prose outside the list in either direction."""
		for boundary in ("", "# Heading", ">quote", "| a |", "---", "* * *", "<div>"):
			lines = ["* First", "wrapped", boundary, "outside", "* Second"]
			with self.subTest(boundary=boundary):
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 0, 1), 2)
				self.assertIsNone(patterns.getBlockBoundary(lines.__getitem__, len(lines), 3, 1))
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 4, -1), 4)
		for item in ("* \r\n", "* # Heading", "* ```py"):
			lines = [item, "outside", "* Second"]
			with self.subTest(item=item):
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 0, 1), 1)
				self.assertIsNone(patterns.getBlockBoundary(lines.__getitem__, len(lines), 1, 1))
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 2, -1), 2)

	def test_document_end(self) -> None:
		"""Distinguish a trailing empty line from a block ending without a newline."""
		for lines in (["* item"], ["* item\r\n", ""]):
			with self.subTest(lines=lines):
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 0, 1), 1)
				self.assertEqual(patterns.getBlockBoundary(lines.__getitem__, len(lines), 0, -1), 0)
