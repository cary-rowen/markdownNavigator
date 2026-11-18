# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA - Regex Patterns
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

import re
from collections.abc import Callable

# Regex Definitions
RE_HEADING = re.compile(r"^\s*#{1,6}\s")
RE_LIST_ITEM = re.compile(r"^\s*([\*\-\+]|\d+\.)\s")
RE_BLOCKQUOTE = re.compile(r"^\s*>\s")
RE_TABLE = re.compile(r"^\s*\|")
RE_CODE_BLOCK = re.compile(r"^\s*`{3,}")
RE_CODE_FENCE = re.compile(r"^\s*(`{3,}|~{3,})(.*)$")
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
RE_HEADING_ANCHOR = re.compile(r"^\s*#{1,6}\s+.*?\s+\{#([^}\s]+)\}\s*$")


def getHeadingRegex(level):
	return re.compile(r"^\s*#{%d}\s" % level)


def _findClosingDelimiter(text: str, opening: int, left: str, right: str) -> int | None:
	"""Return the matching delimiter while ignoring escaped characters."""
	depth = 0
	index = opening
	while index < len(text):
		if text[index] == "\\":
			index += 2
			continue
		if text[index] == left:
			depth += 1
		elif text[index] == right:
			depth -= 1
			if depth == 0:
				return index
		index += 1
	return None


def _getLinkDestination(text: str) -> str | None:
	"""Extract an inline link destination from its parenthesized content."""
	text = text.strip()
	if text.startswith("<"):
		end = text.find(">")
		return text[1:end] if end > 0 else None
	return text.split(None, 1)[0] if text else None


def getMarkdownLinkAtOffset(text: str, offset: int) -> tuple[int, int, str, str] | None:
	"""Return the inline link and label containing a character offset."""
	for start, character in enumerate(text):
		if character != "[" or (start > 0 and text[start - 1] == "!"):
			continue
		labelEnd = _findClosingDelimiter(text, start, "[", "]")
		if labelEnd is None or labelEnd + 1 >= len(text) or text[labelEnd + 1] != "(":
			continue
		destinationEnd = _findClosingDelimiter(text, labelEnd + 1, "(", ")")
		if destinationEnd is None:
			continue
		destination = _getLinkDestination(text[labelEnd + 2 : destinationEnd])
		if destination is not None and start <= offset <= destinationEnd:
			return start, destinationEnd, destination, text[start + 1 : labelEnd]
	return None


def findHeadingAnchor(getText: Callable[[int], str], nLines: int, anchor: str) -> int | None:
	"""Return the line containing an explicit Markdown heading anchor."""
	for lineIndex in range(nLines):
		match = RE_HEADING_ANCHOR.match(getText(lineIndex))
		if match and match.group(1) == anchor:
			return lineIndex
	return None


def _classifyListLine(text: str) -> tuple[int | None, bool]:
	"""Return the marker's indentation, if present, and whether the line contains paragraph text."""
	if RE_SEPARATOR.match(text):
		return None, False
	indent = None
	text = text.expandtabs(4)
	if match := RE_LIST_ITEM.match(text):
		indent = len(text) - len(text.lstrip(" "))
		text = text[match.end() :]
	text = text.strip()
	return indent, bool(
		text
		and not text.startswith((">", "|", "```", "~~~", "<"))
		and not re.match(r"#{1,6}(?:\s|$)|=+$|[-+*]$|\d{1,9}\)(?:\s|$)", text)
		and not RE_SEPARATOR.match(text),
	)


def _getCodeFence(text: str) -> str | None:
	"""Return a Markdown code fence marker, if present."""
	match = RE_CODE_FENCE.match(text)
	return match.group(1) if match else None


def _isClosingCodeFence(text: str, fence: str) -> bool:
	"""Return whether text closes the given code fence."""
	match = RE_CODE_FENCE.match(text)
	return bool(
		match
		and not match.group(2).strip()
		and match.group(1)[0] == fence[0]
		and len(match.group(1)) >= len(fence),
	)


def _isInsideCodeFence(getText: Callable[[int], str], lineIndex: int) -> bool:
	"""Return whether a line is inside a fenced code block."""
	fence = None
	for index in range(lineIndex):
		marker = _getCodeFence(getText(index))
		if marker is None:
			continue
		if fence is None:
			fence = marker
		elif _isClosingCodeFence(getText(index), fence):
			fence = None
	return fence is not None


def _listItemForLine(getText: Callable[[int], str], lineIndex: int) -> tuple[int, int, bool] | None:
	"""Find the owning marker and return its line, indentation and whether its paragraph can continue."""
	for index in range(lineIndex, -1, -1):
		indent, paragraph = _classifyListLine(getText(index))
		if indent is not None and (index == lineIndex or paragraph):
			return index, indent, paragraph
		if not paragraph:
			break
	return None


def isListBlockLine(getText: Callable[[int], str], lineIndex: int) -> bool:
	"""Return whether a line belongs to a list block, including a paragraph continuation."""
	return not _isInsideCodeFence(getText, lineIndex) and _listItemForLine(getText, lineIndex) is not None


def getListBlockStarts(getText: Callable[[int], str], nLines: int) -> list[int]:
	"""Return the first line of each list block, including nested list blocks."""
	starts = []
	activeIndents = []
	fence = None
	for lineIndex in range(nLines):
		marker = _getCodeFence(getText(lineIndex))
		if fence is not None:
			if marker and _isClosingCodeFence(getText(lineIndex), fence):
				fence = None
			activeIndents.clear()
			continue
		if marker:
			fence = marker
			activeIndents.clear()
			continue
		indent, paragraph = _classifyListLine(getText(lineIndex))
		if indent is None:
			if not paragraph:
				activeIndents.clear()
			continue
		while activeIndents and indent < activeIndents[-1]:
			activeIndents.pop()
		if not activeIndents or indent > activeIndents[-1]:
			activeIndents.append(indent)
			starts.append(lineIndex)
	return starts


def getBlockBoundary(
	getText: Callable[[int], str],
	nLines: int,
	lineIndex: int,
	direction: int,
) -> int | None:
	"""Return the block start or the line after it; nLines denotes the document end."""
	if _isInsideCodeFence(getText, lineIndex):
		return None
	currentText = getText(lineIndex)
	for regex in (RE_TABLE, RE_BLOCKQUOTE):
		if regex.match(currentText):
			while 0 <= lineIndex + direction < nLines and regex.match(getText(lineIndex + direction)):
				lineIndex += direction
			return lineIndex + 1 if direction > 0 else lineIndex

	item = _listItemForLine(getText, lineIndex)
	if item is None:
		return None
	start, indent, canContinue = item
	if direction < 0:
		while previous := _listItemForLine(getText, start - 1):
			previousLine, previousIndent, _ = previous
			if previousIndent < indent:
				break
			start = previousLine
		return start

	for index in range(lineIndex + 1, nLines):
		markerIndent, paragraph = _classifyListLine(getText(index))
		if markerIndent is None and not (canContinue and paragraph):
			return index
		if markerIndent is not None and markerIndent < indent:
			return index
		canContinue = paragraph
	return nLines


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
