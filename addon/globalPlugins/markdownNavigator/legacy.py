# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA - Legacy Navigation Module
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

"""Legacy navigation functions using line-by-line scanning.

This module provides fallback navigation methods that work when
FastDocumentManager fails. These methods are less efficient but
more compatible with various text controls.

To remove legacy support in the future, simply delete this file
and remove the imports/calls from navigator.py.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import addonHandler
import re
import controlTypes
import textInfos
import ui
import speech
from logHandler import log
from _ctypes import COMError
from . import patterns
from textUtils import WideStringOffsetConverter
from NVDAObjects.IAccessible import IA2TextTextInfo

addonHandler.initTranslation()

if TYPE_CHECKING:
	from NVDAObjects import NVDAObject


def _step_line(ti: textInfos.TextInfo, direction: int) -> bool:
	"""Move TextInfo to the next or previous line using hybrid approach.

	Tries efficient UNIT_LINE movement first, then falls back to robust
	character stepping to handle Ghost Loops in RichEdit controls.
	
	:return: True if moved successfully, False if at EOF/BOF.
	"""
	tiOriginal = ti.copy()

	# Plan A: Efficient Line Movement
	try:
		res = ti.move(textInfos.UNIT_LINE, direction)
		if res != 0:
			ti.expand(textInfos.UNIT_LINE)

			# Verify physical movement
			moved = False
			if direction == 1:
				if ti.compareEndPoints(tiOriginal, "startToStart") > 0:
					moved = True
			else:
				if ti.compareEndPoints(tiOriginal, "startToStart") < 0:
					moved = True

			if moved:
				return True

			# Ghost Loop detected: move() returned non-zero but position didn't change
			# Reset and try Plan B
			ti.setEndPoint(tiOriginal, "startToStart")
			ti.setEndPoint(tiOriginal, "endToEnd")
		else:
			# move() returned 0, likely EOF/BOF
			return False

	except (RuntimeError, ValueError, COMError):
		# Boundary or IPC failure - don't try Plan B
		return False

	# Plan B: Robust Character Stepping (RichEdit anti-ghost logic)
	if direction == 1:
		try:
			ti.collapse(end=True)
		except (RuntimeError, ValueError, COMError):
			return False
		collapsedAnchorPoint = ti.copy()
		if ti.move(textInfos.UNIT_CHARACTER, 1) == 0:
			return False
	else:
		try:
			ti.collapse(end=False)
		except (RuntimeError, ValueError, COMError):
			return False
		if ti.move(textInfos.UNIT_CHARACTER, -1) == 0:
			return False

	ti.expand(textInfos.UNIT_LINE)

	# Final verification
	if direction == 1:
		if ti.compareEndPoints(tiOriginal, "startToStart") <= 0:
			return False
		if ti.compareEndPoints(collapsedAnchorPoint, "startToStart") < 0:
			return False
	else:
		if ti.compareEndPoints(tiOriginal, "startToStart") >= 0:
			return False

	return True


def navigate_legacy(
	obj: NVDAObject,
	gesture,
	regex: re.Pattern,
	direction: int,
	name: str,
	focus_element: bool,
	notFoundMessage: str | None,
) -> None:
	"""Legacy navigation method using line-by-line scanning."""
	try:
		ti = obj.makeTextInfo(textInfos.POSITION_CARET)
	except (NotImplementedError, LookupError):
		log.debugWarning("MarkdownNavigator: Could not get caret text info.")
		gesture.send()
		return
	ti.collapse()
	if focus_element:
		tiLine = ti.copy()
		tiLine.expand(textInfos.UNIT_LINE)
		text = tiLine.text
		tiLineStart = tiLine.copy()
		tiLineStart.collapse()
		tiToCaret = tiLineStart.copy()
		tiToCaret.setEndPoint(ti, "endToEnd")
		caret_offset = len(tiToCaret.text)
		target_match = None
		matches = list(regex.finditer(text))
		if direction == 1:
			for m in matches:
				if m.start() > caret_offset:
					target_match = m
					break
		else:
			for m in reversed(matches):
				if m.start() < caret_offset:
					target_match = m
					break
		if target_match:
			tiLine.collapse()
			tiLine.move(textInfos.UNIT_CHARACTER, target_match.start())
			tiLine.updateCaret()
			speech.speak([target_match.group()])
			return
		tiScan = tiLine.copy()
		found = False
		while _step_line(tiScan, direction):
			text = tiScan.text
			matches = list(regex.finditer(text))
			if matches:
				found = True
				m = matches[0] if direction == 1 else matches[-1]
				tiScan.collapse()
				tiScan.move(textInfos.UNIT_CHARACTER, m.start())
				tiScan.updateCaret()
				speech.speak([m.group()])
				break
		if not found:
			msg = notFoundMessage if notFoundMessage else (_("no next %s found") % name if direction == 1 else _("no previous %s found") % name)
			ui.message(msg)
	else:
		tiScan = ti.copy()
		tiScan.expand(textInfos.UNIT_LINE)
		found = False
		while _step_line(tiScan, direction):
			text = tiScan.text
			if regex.search(text):
				found = True
				tiScan.collapse()
				tiScan.updateCaret()
				tiScan.expand(textInfos.UNIT_LINE)
				speech.speakTextInfo(tiScan, unit=textInfos.UNIT_LINE, reason=controlTypes.OutputReason.CARET)
				break
		if not found:
			msg = notFoundMessage if notFoundMessage else (_("no next %s found") % name if direction == 1 else _("no previous %s found") % name)
			ui.message(msg)


def navigate_block_legacy(
	obj: NVDAObject,
	gesture,
	regex: re.Pattern,
	direction: int,
	name: str,
	notFoundMessage: str | None,
) -> None:
	"""Legacy block navigation using line-by-line scanning."""
	try:
		tiScan = obj.makeTextInfo(textInfos.POSITION_CARET)
	except (NotImplementedError, LookupError):
		gesture.send()
		return
	tiScan.collapse()
	tiLine = tiScan.copy()
	tiLine.expand(textInfos.UNIT_LINE)
	in_block = bool(regex.match(tiLine.text))

	if direction == -1 and in_block:
		tiPrev = tiLine.copy()
		if _step_line(tiPrev, -1):
			if regex.match(tiPrev.text):
				target_ti = tiLine.copy()
				while True:
					temp_ti = target_ti.copy()
					if not _step_line(temp_ti, -1):
						break
					if not regex.match(temp_ti.text):
						break
					target_ti = temp_ti
				target_ti.collapse()
				target_ti.updateCaret()
				target_ti.expand(textInfos.UNIT_LINE)
				speech.speakTextInfo(target_ti, unit=textInfos.UNIT_LINE, reason=controlTypes.OutputReason.CARET)
				return

	tiScan = tiLine.copy()
	found = False
	while _step_line(tiScan, direction):
		text = tiScan.text
		is_match = bool(regex.match(text))
		if in_block:
			if not is_match:
				in_block = False
		else:
			if is_match:
				if direction == -1:
					target_ti = tiScan.copy()
					while True:
						temp_ti = target_ti.copy()
						if not _step_line(temp_ti, -1):
							break
						if not regex.match(temp_ti.text):
							break
						target_ti = temp_ti
					tiScan = target_ti
				found = True
				tiScan.collapse()
				tiScan.updateCaret()
				tiScan.expand(textInfos.UNIT_LINE)
				speech.speakTextInfo(tiScan, unit=textInfos.UNIT_LINE, reason=controlTypes.OutputReason.CARET)
				break
	if not found:
		msg = notFoundMessage if notFoundMessage else (_("no next %s found") % name if direction == 1 else _("no previous %s found") % name)
		ui.message(msg)


def navigate_code_legacy(
	obj: NVDAObject,
	gesture,
	direction: int,
	name: str,
	notFoundMessage: str | None = None,
) -> None:
	"""Legacy code block navigation using line-by-line scanning."""
	try:
		ti = obj.makeTextInfo(textInfos.POSITION_CARET)
	except (NotImplementedError, LookupError):
		gesture.send()
		return
	ti.collapse()
	tiOriginal = ti.copy()
	tiLine = ti.copy()
	tiLine.expand(textInfos.UNIT_LINE)
	on_boundary = bool(patterns.RE_CODE_BLOCK.match(tiLine.text))
	# Base for scanning
	tiScan = tiLine.copy()
	if on_boundary:
		should_skip = True
		if direction == -1 and len(tiLine.text.strip()) > 3:
			should_skip = False
		if should_skip:
			while _step_line(tiScan, direction):
				if patterns.RE_CODE_BLOCK.match(tiScan.text):
					break
	else:
		tiCurrentLine = tiOriginal.copy()
		tiCurrentLine.expand(textInfos.UNIT_LINE)
		text = tiCurrentLine.text
		tiLineStart = tiCurrentLine.copy()
		tiLineStart.collapse()
		tiToCaret = tiLineStart.copy()
		tiToCaret.setEndPoint(tiOriginal, "endToEnd")
		caret_offset = len(tiToCaret.text)
		matches = list(patterns.RE_INLINE_CODE.finditer(text))
		target_match = None
		if direction == 1:
			for m in matches:
				if m.start() > caret_offset:
					target_match = m
					break
		else:
			for m in reversed(matches):
				if m.start() < caret_offset:
					target_match = m
					break
		if target_match:
			tiCurrentLine.collapse()
			tiCurrentLine.move(textInfos.UNIT_CHARACTER, target_match.start())
			tiCurrentLine.updateCaret()
			speech.speak([target_match.group()])
			return

	found = False
	while _step_line(tiScan, direction):
		text = tiScan.text
		if patterns.RE_CODE_BLOCK.match(text):
			# Logic for Previous Direction (-1):
			if direction == -1:
				has_info = len(text.strip()) > 3
				if has_info:
					found = True
				else:
					tiScanUp = tiScan.copy()
					while _step_line(tiScanUp, -1):
						if patterns.RE_CODE_BLOCK.match(tiScanUp.text):
							tiScan = tiScanUp
							break
					found = True
			else:
				found = True
			if found:
				tiScan.collapse()
				tiScan.updateCaret()
				tiScan.expand(textInfos.UNIT_LINE)
				speech.speakTextInfo(tiScan, unit=textInfos.UNIT_LINE, reason=controlTypes.OutputReason.CARET)
				break
		matches = list(patterns.RE_INLINE_CODE.finditer(text))
		if matches:
			found = True
			m = matches[0] if direction == 1 else matches[-1]
			tiScan.collapse()
			tiScan.move(textInfos.UNIT_CHARACTER, m.start())
			tiScan.updateCaret()
			speech.speak([m.group()])
			break
	if not found:
		msg = notFoundMessage if notFoundMessage else (_("no next %s found") % name if direction == 1 else _("no previous %s found") % name)
		ui.message(msg)


def _parse_table_row(text: str) -> list[dict]:
	"""Parses a Markdown table row into a list of cell dictionaries."""
	cells = []
	# Split by pipe, but keep the delimiter to calculate offsets
	# Regex looks for | not preceded by \
	pattern = re.compile(r'(?<!\\)\|')
	matches = list(pattern.finditer(text))
	if not matches:
		return []
	for i in range(len(matches) - 1):
		start_pipe = matches[i]
		end_pipe = matches[i + 1]
		cell_start = start_pipe.end()
		cell_end = end_pipe.start()
		cell_text = text[cell_start:cell_end]
		stripped = cell_text.strip()
		content_start = cell_start + cell_text.find(stripped) if stripped else cell_start
		content_end = content_start + len(stripped)
		cells.append({
			'start': cell_start,
			'end': cell_end,
			'content_start': content_start,
			'content_end': content_end,
			'text': stripped
		})
	return cells


def navigate_table_legacy(
	obj: NVDAObject,
	gesture,
	row_dir: int,
	col_dir: int,
) -> None:
	"""Legacy table navigation using line-by-line scanning and IA2 text info optimization where possible."""
	# Web special handling: Use Flat IA 2 Info
	isWeb = getattr(obj.appModule, 'appName', '').lower() in ('chrome', 'msedge')
	try:
		if isWeb and hasattr(obj, 'IAccessibleTextObject'):
			ti = IA2TextTextInfo(obj, textInfos.POSITION_CARET)
		else:
			ti = obj.makeTextInfo(textInfos.POSITION_CARET)
	except (NotImplementedError, LookupError):
		gesture.send()
		return

	ti.collapse()
	tiLine = ti.copy()
	tiLine.expand(textInfos.UNIT_LINE)
	if not patterns.RE_TABLE.match(tiLine.text):
		gesture.send()
		return

	# 1. Parse current row
	cells = _parse_table_row(tiLine.text)
	if not cells:
		gesture.send()
		return

	# 2. Determine current column
	# Calculate relative offset
	# If it's Flat Info, _startOffset is the global UTF-16 offset
	# Create converter for current line to handle Emoji math
	line_converter = WideStringOffsetConverter(tiLine.text)

	if isWeb and isinstance(ti, IA2TextTextInfo):
		# caret_abs, line_start_abs are UTF-16
		caret_abs = ti._startOffset
		line_start_abs = tiLine._startOffset
		caret_utf16_relative = caret_abs - line_start_abs
		# Convert to Python Char Offset for comparison with regex results
		caret_char_relative = line_converter.encodedToStrOffsets(caret_utf16_relative, caret_utf16_relative)[0]
	else:
		# Fallback logic - tiToCaret handles text length (Python Chars)
		tiLineStart = tiLine.copy()
		tiLineStart.collapse()
		tiToCaret = tiLineStart.copy()
		tiToCaret.setEndPoint(ti, "endToEnd")
		caret_char_relative = len(tiToCaret.text)

	current_col = -1
	for i, cell in enumerate(cells):
		if caret_char_relative >= cell['start'] and caret_char_relative <= cell['end']:
			current_col = i
			break
	if current_col == -1:
		current_col = 0

	target_col = current_col

	# 3. Horizontal Move
	if col_dir != 0:
		target_col = current_col + col_dir
		if target_col < 0 or target_col >= len(cells):
			ui.message(_("Edge of table"))
			return
		target_cell = cells[target_col]
		target_char_offset = target_cell['content_start']  # relative to line start (Python Char)

		if isWeb and isinstance(tiLine, IA2TextTextInfo):
			# Convert to UTF-16 offset
			target_utf16_offset = line_converter.strToEncodedOffsets(target_char_offset)

			new_abs = tiLine._startOffset + target_utf16_offset
			tiNew = tiLine.copy()
			tiNew._startOffset = new_abs
			tiNew._endOffset = new_abs  # collapse
			tiNew.updateCaret()
		else:
			tiLineStart = tiLine.copy()
			tiLineStart.collapse()
			tiLineStart.move(textInfos.UNIT_CHARACTER, target_char_offset)
			tiLineStart.updateCaret()

		speech.speak([target_cell['text']])
		return

	# 4. Vertical Move
	if row_dir != 0:
		tiScan = tiLine.copy()
		if not _step_line(tiScan, row_dir):
			ui.message(_("Edge of table"))
			return
		if not patterns.RE_TABLE.match(tiScan.text):
			ui.message(_("Edge of table"))
			return
		new_cells = _parse_table_row(tiScan.text)
		if not new_cells:
			ui.message(_("Edge of table"))
			return
		if target_col >= len(new_cells):
			target_col = len(new_cells) - 1
		target_cell = new_cells[target_col]
		target_char_offset = target_cell['content_start']

		if isWeb and isinstance(tiScan, IA2TextTextInfo):
			# Need converter for the NEW line -> tiScan.text
			scan_converter = WideStringOffsetConverter(tiScan.text)
			target_utf16_offset = scan_converter.strToEncodedOffsets(target_char_offset)

			new_abs = tiScan._startOffset + target_utf16_offset
			tiNew = tiScan.copy()
			tiNew._startOffset = new_abs
			tiNew._endOffset = new_abs
			tiNew.updateCaret()
		else:
			tiScan.collapse()
			tiScan.move(textInfos.UNIT_CHARACTER, target_char_offset)
			tiScan.updateCaret()

		speech.speak([target_cell['text']])
		return