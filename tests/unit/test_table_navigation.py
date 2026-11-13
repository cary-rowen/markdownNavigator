"""Tests for Markdown table parsing and navigation targets."""

import importlib.util
from pathlib import Path
import unittest


PATTERNS_PATH = Path(__file__).parents[2] / "addon" / "globalPlugins" / "markdownNavigator" / "patterns.py"
SPEC = importlib.util.spec_from_file_location("markdownNavigatorPatterns", PATTERNS_PATH)
assert SPEC and SPEC.loader
patterns = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(patterns)


class TestTableNavigation(unittest.TestCase):
	"""Verify table context and movement calculations without NVDA runtime dependencies."""

	def setUp(self):
		"""Create a table surrounded by non-table lines."""
		self.lines = [
			"before\n",
			"| H1 | H2 | H3 |\n",
			"| --- | --- | --- |\n",
			"| A1 | A2 | A3 |\n",
			"| B1 | B2 |\n",
			"after\n",
		]

	def test_context_and_edge_movements(self):
		"""Find the current cell and move to each table edge."""
		caretOffset = self.lines[3].index("A3")
		context = patterns.getTableContext(self.lines.__getitem__, len(self.lines), 3, caretOffset)

		self.assertIsNotNone(context)
		rows, currentRow, currentColumn = context
		self.assertEqual((len(rows), currentRow, currentColumn), (4, 2, 2))
		self.assertEqual(
			patterns.getTableCellForMovement(context, rowOffset=-1, toEdge=True)[1]["text"],
			"H3",
		)
		self.assertEqual(
			patterns.getTableCellForMovement(context, rowOffset=1)[1]["text"],
			"B2",
		)
		self.assertEqual(
			patterns.getTableCellForMovement(context, columnOffset=-1, toEdge=True)[1]["text"],
			"A1",
		)
		self.assertEqual(
			patterns.getTableCellForMovement(context, columnOffset=1, toEdge=True)[1]["text"],
			"A3",
		)

	def test_movement_stops_at_table_edges(self):
		"""Return no destination when movement would leave the table."""
		context = patterns.getTableContext(self.lines.__getitem__, len(self.lines), 1, 2)
		self.assertIsNone(patterns.getTableCellForMovement(context, rowOffset=-1))
		self.assertIsNone(patterns.getTableCellForMovement(context, columnOffset=-1))

	def test_caret_after_closing_pipe_uses_last_column(self):
		"""Treat the end-of-line caret position as the final table column."""
		lineIndex = 3
		caretOffset = self.lines[lineIndex].rindex("|") + 1
		context = patterns.getTableContext(
			self.lines.__getitem__,
			len(self.lines),
			lineIndex,
			caretOffset,
		)

		self.assertEqual(context[2], 2)
		self.assertEqual(
			patterns.getTableCellForMovement(context, columnOffset=-1)[1]["text"],
			"A2",
		)

	def test_empty_cell_remains_a_navigation_target(self):
		"""Keep empty Markdown cells in the parsed column layout."""
		cells = patterns.parseTableRow("| left |  | right |")
		self.assertEqual([cell["text"] for cell in cells], ["left", "", "right"])

	def test_escaped_pipe_stays_in_cell(self):
		"""Do not split a cell at an escaped pipe."""
		cells = patterns.parseTableRow(r"| left | a \| b | right |")
		self.assertEqual([cell["text"] for cell in cells], ["left", r"a \| b", "right"])

	def test_pipe_after_escaped_backslash_still_separates_cells(self):
		"""Split at a pipe preceded by an even number of backslashes."""
		cells = patterns.parseTableRow(r"| C:\\ | D:\\ |")
		self.assertEqual([cell["text"] for cell in cells], [r"C:\\", r"D:\\"])

	def test_row_without_closing_pipe_keeps_last_cell(self):
		"""Keep the final cell when a valid row omits its closing pipe."""
		cells = patterns.parseTableRow("| left | right")
		self.assertEqual([cell["text"] for cell in cells], ["left", "right"])


if __name__ == "__main__":
	unittest.main()
