# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA - Regex Patterns
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

import re

# Regex Definitions
RE_HEADING = re.compile(r"^\s*#{1,6}\s")
RE_LIST_ITEM = re.compile(r"^\s*([\*\-\+]|\d+\.)\s")
RE_BLOCKQUOTE = re.compile(r"^\s*>\s")
RE_TABLE = re.compile(r"^\s*\|")
RE_CODE_BLOCK = re.compile(r"^\s*`{3,}")
RE_INLINE_CODE = re.compile(r"(?<!`)`[^`\n]+`(?!`)")
# Non-greedy matching for inline elements
# Negative lookbehind (?<!!) ensures we don't match images ![...]
RE_LINK = re.compile(r"(?<!!)\[.+?\]\(.+?\)")
RE_IMAGE = re.compile(r"!\[.+?\]\(.+?\)")
RE_SEPARATOR = re.compile(r"^\s*([-*_])\s*\1\s*\1[\-\*_\s]*$")
RE_CHECKBOX = re.compile(r"^\s*([\*\-\+]|\d+\.)\s*\[[ xX]\]")
RE_BOLD = re.compile(r"(\*\*|__)(?=\S)(.+?)(?<=\S)\1")
RE_ITALIC = re.compile(r"(?<!\*)\*(?=[^\s*])(.+?)(?<=[^\s*])\*(?!\*)|(?<!_)_(?=[^\s_])(.+?)(?<=[^\s_])_(?!_)")
RE_STRIKETHROUGH = re.compile(r"(~~)(?=\S)(.+?)(?<=\S)\1")
RE_FOOTNOTE = re.compile(r"\[\^.+?\](:)?")
RE_LATEX_MATH = re.compile(r"\$\$[\s\S]*?\$\$|(?<!\$)\$(?!\$)(.+?)(?<!\$)\$(?!\$)")


def getHeadingRegex(level):
	return re.compile(r"^\s*#{%d}\s" % level)


def parseTableRow(text):
	"""Parse a Markdown table row into cell offset dictionaries."""
	cells = []
	separators = []
	precedingBackslashes = 0
	for offset, character in enumerate(text):
		if character == "|":
			if precedingBackslashes % 2 == 0:
				separators.append(offset)
			precedingBackslashes = 0
		elif character == "\\":
			precedingBackslashes += 1
		else:
			precedingBackslashes = 0
	if not separators:
		return []
	lineEnd = len(text.rstrip("\r\n"))
	if text[separators[-1] + 1 : lineEnd].strip():
		separators.append(lineEnd)
	for startPipe, endPipe in zip(separators, separators[1:]):
		cell_start = startPipe + 1
		cell_end = endPipe
		cell_text = text[cell_start:cell_end]
		stripped = cell_text.strip()
		content_start = cell_start + cell_text.find(stripped) if stripped else cell_start
		cells.append(
			{
				"start": cell_start,
				"end": cell_end,
				"content_start": content_start,
				"text": stripped,
			},
		)
	return cells


def getTableContext(getText, nLines, lineIndex, caretOffset):
	"""Return the contiguous table rows and the current cell coordinates."""
	currentText = getText(lineIndex)
	currentCells = parseTableRow(currentText) if RE_TABLE.match(currentText) else []
	if not currentCells:
		return None

	firstLine = lineIndex
	while firstLine > 0:
		text = getText(firstLine - 1)
		if not RE_TABLE.match(text) or not parseTableRow(text):
			break
		firstLine -= 1

	rows = []
	for candidateLine in range(firstLine, nLines):
		text = getText(candidateLine)
		cells = parseTableRow(text) if RE_TABLE.match(text) else []
		if not cells:
			break
		rows.append((candidateLine, cells))

	currentColumn = len(currentCells) - 1 if caretOffset > currentCells[-1]["end"] else 0
	for column, cell in enumerate(currentCells):
		if cell["start"] <= caretOffset <= cell["end"]:
			currentColumn = column
			break
	return rows, lineIndex - firstLine, currentColumn


def getTableCellForMovement(context, rowOffset=0, columnOffset=0, toEdge=False):
	"""Return the target table cell for a relative or edge movement."""
	rows, currentRow, currentColumn = context
	targetRow = currentRow
	targetColumn = currentColumn
	if rowOffset:
		targetRow = (0 if rowOffset < 0 else len(rows) - 1) if toEdge else currentRow + rowOffset
	elif columnOffset:
		currentCells = rows[currentRow][1]
		targetColumn = (
			(0 if columnOffset < 0 else len(currentCells) - 1) if toEdge else currentColumn + columnOffset
		)

	if targetRow < 0 or targetRow >= len(rows):
		return None
	targetCells = rows[targetRow][1]
	if targetColumn < 0 or targetColumn >= len(targetCells):
		if rowOffset and targetCells:
			targetColumn = len(targetCells) - 1
		else:
			return None
	return rows[targetRow][0], targetCells[targetColumn]
