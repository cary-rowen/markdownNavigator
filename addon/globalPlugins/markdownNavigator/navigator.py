# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

from __future__ import annotations
from typing import TYPE_CHECKING

import addonHandler
import controlTypes
import textInfos
import ui
import re
import winsound
import config
import os
import nvwave
import globalVars
from scriptHandler import script
import speech
from logHandler import log
from baseObject import ScriptableObject
from . import patterns
from _ctypes import COMError
from NVDAObjects.IAccessible import IA2TextTextInfo

from .document import FastDocumentManager

addonHandler.initTranslation()

if TYPE_CHECKING:
	pass


class MarkdownEditorOverlay(ScriptableObject):
	"""Overlay class to add Markdown navigation capabilities to EditableText objects."""

	markdownBrowseMode: bool = False

	@script(
		# Translators: Description for the toggle script.
		description=_("Toggles Markdown Browse Mode. When enabled, keys like H, I, T navigate content."),
		gesture="kb:NVDA+shift+space",
	)
	def script_toggleMarkdownBrowseMode(self, gesture) -> None:
		self.markdownBrowseMode = not self.markdownBrowseMode
		self._reportBrowseModeState()

	def _reportBrowseModeState(self) -> None:
		if config.conf["virtualBuffers"]["passThroughAudioIndication"]:
			sound = "browseMode.wav" if self.markdownBrowseMode else "focusMode.wav"
			nvwave.playWaveFile(os.path.join(globalVars.appDir, "waves", sound))
		else:
			if self.markdownBrowseMode:
				# Translators: Message when mode is enabled.
				ui.message(_("Markdown Browse Mode On"))
			else:
				# Translators: Message when mode is disabled.
				ui.message(_("Markdown Browse Mode Off"))

	def getScript(self, gesture):
		"""Handle browse mode specific gesture trapping."""
		script = super().getScript(gesture)
		if not getattr(self, "markdownBrowseMode", False):
			return script

		if script:
			return script

		# Trap non-command gestures if configured
		if config.conf["virtualBuffers"]["trapNonCommandGestures"] and gesture.isCharacter:
			return self.script_trapNonCommandGesture

		return None

	def script_trapNonCommandGesture(self, gesture) -> None:
		winsound.MessageBeep()

	def _navigate(
		self,
		gesture,
		regex: re.Pattern,
		direction: int,
		name: str,
		focus_element: bool = False,
		notFoundMessage: str | None = None,
	) -> None:
		"""Core navigation logic.

		Uses FastDocumentManager for batch text processing to reduce IPC calls.
		Falls back to legacy navigation if FastDocumentManager fails.

		:param gesture: The gesture that triggered navigation.
		:param regex: Compiled regex pattern to match.
		:param direction: Direction (1=forward, -1=backward).
		:param name: Human-readable name of the element type.
		:param focus_element: Whether to position caret at match (True for inline elements).
		:param notFoundMessage: Custom message when element not found.
		"""
		if not getattr(self, "markdownBrowseMode", False):
			gesture.send()
			return
		try:
			with FastDocumentManager(self) as fdm:
				self._navigateFast(fdm, regex, direction, name, focus_element, notFoundMessage)
		except (RuntimeError, NotImplementedError, LookupError, COMError) as e:
			log.debugWarning(f"MarkdownNavigator: FastDocumentManager failed ({e}), falling back to legacy")
			from .legacy import navigate_legacy

			navigate_legacy(self, gesture, regex, direction, name, focus_element, notFoundMessage)

	def _navigateFast(
		self,
		fdm: FastDocumentManager,
		regex: re.Pattern,
		direction: int,
		name: str,
		focus_element: bool,
		notFoundMessage: str | None,
	) -> None:
		from textUtils import WideStringOffsetConverter

		if focus_element:
			currentLineText = fdm.getText()
			lineStartOffset = fdm.getLineOffset()
			# Check if we can use Flat Injection (Web Optimization)
			isWeb = getattr(self.appModule, "appName", "").lower() in ("chrome", "msedge")

			# Calculate caret offset within current line
			# Note: getLineOffset returns Python string offset
			try:
				pretext = fdm.originalCaret.copy()
				pretext.setEndPoint(fdm.document, "startToStart")
				docCaretPos = len(pretext.text)
				caret_offset = docCaretPos - lineStartOffset
			except Exception:
				caret_offset = 0

			matches = list(regex.finditer(currentLineText))
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
				lineInfo = fdm.getTextInfo()

				if isWeb and isinstance(lineInfo, IA2TextTextInfo):
					# Web Optimization: Calculate Global UTF-16 Offset and Inject
					prefix = currentLineText[: target_match.start()]
					converter = WideStringOffsetConverter(prefix)
					utf16_delta = converter.encodedStringLength

					new_abs = lineInfo._startOffset + utf16_delta
					match_len_utf16 = WideStringOffsetConverter(target_match.group()).encodedStringLength

					lineInfo._startOffset = new_abs
					lineInfo._endOffset = new_abs + match_len_utf16

					# Update caret
					lineInfo.updateCaret()
					# Speak content
					speech.speak([target_match.group()])
					return
				else:
					# Fallback / Desktop
					lineInfo.collapse()
					lineInfo.move(textInfos.UNIT_CHARACTER, target_match.start())
					lineInfo.updateCaret()
					speech.speak([target_match.group()])
					return

			found = False
			while fdm.move(direction) != 0:
				text = fdm.getText()
				matches = list(regex.finditer(text))
				if matches:
					found = True
					m = matches[0] if direction == 1 else matches[-1]
					lineInfo = fdm.getTextInfo()

					if isWeb and isinstance(lineInfo, IA2TextTextInfo):
						# Web Optimization: Offset Injection
						prefix = text[: m.start()]
						converter = WideStringOffsetConverter(prefix)
						utf16_delta = converter.encodedStringLength

						new_abs = lineInfo._startOffset + utf16_delta
						match_len_utf16 = WideStringOffsetConverter(m.group()).encodedStringLength

						lineInfo._startOffset = new_abs
						lineInfo._endOffset = new_abs + match_len_utf16

						lineInfo.updateCaret()
						speech.speak([m.group()])
						break
					else:
						# Fallback / Desktop
						lineInfo.collapse()
						lineInfo.move(textInfos.UNIT_CHARACTER, m.start())
						lineInfo.updateCaret()
						speech.speak([m.group()])
						break

			if not found:
				msg = (
					notFoundMessage
					if notFoundMessage
					else (
						_("no next %s found") % name if direction == 1 else _("no previous %s found") % name
					)
				)
				ui.message(msg)
		else:
			found = False
			while fdm.move(direction) != 0:
				text = fdm.getText()
				if regex.search(text):
					found = True
					lineInfo = fdm.updateCaret()
					speech.speakTextInfo(
						lineInfo,
						unit=textInfos.UNIT_LINE,
						reason=controlTypes.OutputReason.CARET,
					)
					break
			if not found:
				msg = (
					notFoundMessage
					if notFoundMessage
					else (
						_("no next %s found") % name if direction == 1 else _("no previous %s found") % name
					)
				)
				ui.message(msg)

	def _navigateBlock(
		self,
		gesture,
		regex: re.Pattern,
		direction: int,
		name: str,
		notFoundMessage: str | None = None,
	) -> None:
		"""Navigation for block elements (tables, code blocks, blockquotes, etc.)."""
		if not getattr(self, "markdownBrowseMode", False):
			gesture.send()
			return
		try:
			with FastDocumentManager(self) as fdm:
				self._navigateBlockFast(fdm, regex, direction, name, notFoundMessage)
		except (RuntimeError, NotImplementedError, LookupError, COMError) as e:
			log.debugWarning(f"MarkdownNavigator: FastDocumentManager failed for block nav ({e})")
			from .legacy import navigate_block_legacy

			navigate_block_legacy(self, gesture, regex, direction, name, notFoundMessage)

	def _navigateBlockFast(
		self,
		fdm: FastDocumentManager,
		regex: re.Pattern,
		direction: int,
		name: str,
		notFoundMessage: str | None,
	) -> None:
		currentLineText = fdm.getText()
		in_block = bool(regex.match(currentLineText))
		# When navigating backward while inside a block, first locate block start
		if direction == -1 and in_block:
			prevLine = fdm.lineIndex - 1
			if prevLine >= 0 and regex.match(fdm.getText(prevLine)):
				# Find block start
				startLine = fdm.lineIndex
				while startLine > 0:
					if not regex.match(fdm.getText(startLine - 1)):
						break
					startLine -= 1
				lineInfo = fdm.updateCaret(startLine)
				speech.speakTextInfo(
					lineInfo,
					unit=textInfos.UNIT_LINE,
					reason=controlTypes.OutputReason.CARET,
				)
				return

		found = False
		while fdm.move(direction) != 0:
			text = fdm.getText()
			is_match = bool(regex.match(text))
			if in_block:
				if not is_match:
					in_block = False
			else:
				if is_match:
					targetLine = fdm.lineIndex
					if direction == -1:
						while targetLine > 0 and regex.match(fdm.getText(targetLine - 1)):
							targetLine -= 1
					found = True
					lineInfo = fdm.updateCaret(targetLine)
					speech.speakTextInfo(
						lineInfo,
						unit=textInfos.UNIT_LINE,
						reason=controlTypes.OutputReason.CARET,
					)
					break
		if not found:
			msg = (
				notFoundMessage
				if notFoundMessage
				else (_("no next %s found") % name if direction == 1 else _("no previous %s found") % name)
			)
			ui.message(msg)

	def _navigateCode(self, gesture, direction, name, notFoundMessage=None):
		if not getattr(self, "markdownBrowseMode", False):
			gesture.send()
			return
		try:
			with FastDocumentManager(self) as fdm:
				self._navigateCodeFast(fdm, direction, name, notFoundMessage)
		except (RuntimeError, NotImplementedError, LookupError, COMError) as e:
			log.debugWarning(
				f"MarkdownNavigator: FastDocumentManager failed for code nav ({e}), falling back",
			)
			from .legacy import navigate_code_legacy

			navigate_code_legacy(self, gesture, direction, name, notFoundMessage)

	def _navigateCodeFast(self, fdm, direction, name, notFoundMessage):
		"""Implementing Code Block Navigation with FastDocumentManager"""
		from textUtils import WideStringOffsetConverter

		isWeb = getattr(self.appModule, "appName", "").lower() in ("chrome", "msedge")

		currentLineText = fdm.getText()
		fdm.getTextInfo()  # For fallback anchor

		# Check if within code block boundary
		on_boundary = bool(patterns.RE_CODE_BLOCK.match(currentLineText))

		# === 1. Inline Code Search in Current Line (if not skipping block) ===
		# If we are already on the boundary and intend to move down, we might intend to skip a block.
		# But if it's not a boundary, or the intention is to find inline code, search the current line first.
		should_skip_block = False

		if on_boundary:
			# Logic: If at boundary
			# Down (1): Skip entire block (look for next closure/start)
			# Up (-1): If it's a closure marker (only ```), look back for the start?
			# If it's a start marker (```python), don't skip (because we're at the start, going back means leaving the block)
			has_info = len(currentLineText.strip()) > 3
			if direction == 1:
				should_skip_block = True
				log.debug("MarkdownNavigator: At parsing boundary, verifying skip intent...")
			else:  # direction == -1
				if has_info:  # Start tag
					should_skip_block = False  # Don't skip upwards from start tag
				else:
					should_skip_block = True  # End tag, skip upwards to start
		else:
			# Not on boundary, searching current line for inline code
			# Get cursor offset
			lineStartOffset = fdm.getLineOffset()
			caret_char_offset = fdm.initialCaretOffset - lineStartOffset
			if caret_char_offset < 0:
				caret_char_offset = 0

			matches = list(patterns.RE_INLINE_CODE.finditer(currentLineText))
			target_match = None
			if direction == 1:
				for m in matches:
					if m.start() > caret_char_offset:
						target_match = m
						break
			else:
				for m in reversed(matches):
					if m.start() < caret_char_offset:
						target_match = m
						break

			if target_match:
				log.debug(f"MarkdownNavigator: Found Inline Code in current line at {target_match.start()}")
				lineInfo = fdm.getTextInfo()

				if isWeb and isinstance(lineInfo, IA2TextTextInfo):
					prefix = currentLineText[: target_match.start()]
					converter = WideStringOffsetConverter(prefix)
					utf16_delta = converter.encodedStringLength
					new_abs = lineInfo._startOffset + utf16_delta
					match_len_utf16 = WideStringOffsetConverter(target_match.group()).encodedStringLength
					lineInfo._startOffset = new_abs
					lineInfo._endOffset = new_abs + match_len_utf16
					lineInfo.updateCaret()
					speech.speak([target_match.group()])
					return
				else:
					lineInfo.collapse()
					lineInfo.move(textInfos.UNIT_CHARACTER, target_match.start())
					lineInfo.updateCaret()
					speech.speak([target_match.group()])
					return

		found = False

		# If skipping block, consume lines until we hit another boundary
		if should_skip_block:
			log.debug("MarkdownNavigator: Skipping logic active.")
			# Simple skip logic: Keep searching until the next RE_CODE_BLOCK is found.
			# Note: This assumes it's paired.
			pass  # Loop below handles it

		while fdm.move(direction) != 0:
			text = fdm.getText()

			# Check for Code Block Boundary
			if patterns.RE_CODE_BLOCK.match(text):
				if direction == -1:
					has_info = len(text.strip()) > 3
					if has_info:  # Found Start Block
						found = True
						log.debug("MarkdownNavigator: Found Prev Code Block Start")
					else:  # Found End Block
						scanLine = fdm.lineIndex
						while scanLine > 0:
							scanLine -= 1  # manual peek
							prevText = fdm.getText(scanLine)
							if patterns.RE_CODE_BLOCK.match(prevText) and len(prevText.strip()) > 3:
								# Found start
								fdm.updateCaret(scanLine)  # Move fdm there
								found = True
								break
						if found:
							break
						# If not found start, maybe just stop at this end tag?
						found = True
				else:  # Next
					found = True

				if found:
					lineInfo = fdm.updateCaret()
					speech.speakTextInfo(
						lineInfo,
						unit=textInfos.UNIT_LINE,
						reason=controlTypes.OutputReason.CARET,
					)
					break

			# Check for Inline Code (only if not skipping block? Legacy checked both)
			# If we are inside a code block, inline code check might be redundant or noisy.
			if not should_skip_block:
				matches = list(patterns.RE_INLINE_CODE.finditer(text))
				if matches:
					found = True
					m = matches[0] if direction == 1 else matches[-1]
					log.debug(f"MarkdownNavigator: Found Inline Code at {m.start()}")

					lineInfo = fdm.getTextInfo()
					if isWeb and isinstance(lineInfo, IA2TextTextInfo):
						prefix = text[: m.start()]
						converter = WideStringOffsetConverter(prefix)
						utf16_delta = converter.encodedStringLength
						new_abs = lineInfo._startOffset + utf16_delta
						match_len_utf16 = WideStringOffsetConverter(m.group()).encodedStringLength
						lineInfo._startOffset = new_abs
						lineInfo._endOffset = new_abs + match_len_utf16
						lineInfo.updateCaret()
						speech.speak([m.group()])
					else:
						lineInfo.collapse()
						lineInfo.move(textInfos.UNIT_CHARACTER, m.start())
						lineInfo.updateCaret()
						speech.speak([m.group()])
					break

		if not found:
			msg = (
				notFoundMessage
				if notFoundMessage
				else (_("no next %s found") % name if direction == 1 else _("no previous %s found") % name)
			)
			ui.message(msg)

	def _parse_table_row(self, text):
		"""
		Parses a Markdown table row.
		Returns a list of dicts: {'start': int, 'end': int, 'content_start': int, 'content_end': int, 'text': str}
		Indices are relative to the start of the line.
		"""
		cells = []
		# Split by pipe, but keep the delimiter to calculate offsets
		# Regex looks for | not preceded by \
		pattern = re.compile(r"(?<!\\)\|")
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
			cells.append(
				{
					"start": cell_start,
					"end": cell_end,
					"content_start": content_start,
					"content_end": content_end,
					"text": stripped,
				},
			)
		return cells

	def _navigateTable(self, gesture, row_dir, col_dir):
		if not getattr(self, "markdownBrowseMode", False):
			gesture.send()
			return
		try:
			with FastDocumentManager(self) as fdm:
				self._navigateTableFast(fdm, row_dir, col_dir)
		except (RuntimeError, NotImplementedError, LookupError, COMError) as e:
			log.debugWarning(
				f"MarkdownNavigator: FastDocumentManager failed for table nav ({e}), falling back to legacy",
			)
			from .legacy import navigate_table_legacy

			navigate_table_legacy(self, gesture, row_dir, col_dir)

	def _navigateTableFast(self, fdm, row_dir, col_dir):
		isWeb = getattr(self.appModule, "appName", "").lower() in ("chrome", "msedge")

		currentLineText = fdm.getText()
		if not patterns.RE_TABLE.match(currentLineText):
			ui.message(_("Not inside a table"))
			return

		# 1. Parse current row (Logical Line)
		# FastDocumentManager returns the full logical line, ignoring soft wraps.
		cells = self._parse_table_row(currentLineText)
		if not cells:
			ui.message(_("Not inside a table"))
			return

		# Determine current column
		# Need current caret offset relative to line start
		lineStartOffset = fdm.getLineOffset()
		caret_char_offset = fdm.initialCaretOffset - lineStartOffset
		if caret_char_offset < 0:
			caret_char_offset = 0

		current_col = -1
		for i, cell in enumerate(cells):
			if caret_char_offset >= cell["start"] and caret_char_offset <= cell["end"]:
				current_col = i
				break
		if current_col == -1:
			current_col = 0

		target_col = current_col

		# Horizontal Move
		if col_dir != 0:
			target_col = current_col + col_dir
			if target_col < 0 or target_col >= len(cells):
				ui.message(_("Edge of table"))
				return
			target_cell = cells[target_col]

			self._moveToTableCell(fdm, target_cell, isWeb)
			return

		# Vertical Move
		if row_dir != 0:
			while fdm.move(row_dir) != 0:
				text = fdm.getText()
				if not patterns.RE_TABLE.match(text):
					break

				new_cells = self._parse_table_row(text)
				if not new_cells:
					break

				if target_col >= len(new_cells):
					target_col = len(new_cells) - 1
				target_cell = new_cells[target_col]

				self._moveToTableCell(fdm, target_cell, isWeb)
				return

			ui.message(_("Edge of table"))
			return

	def _moveToTableCell(self, fdm, target_cell, isWeb):
		from textUtils import WideStringOffsetConverter

		target_char_offset = target_cell["content_start"]
		tiLine = fdm.getTextInfo()

		if isWeb and isinstance(tiLine, IA2TextTextInfo):
			# Convert to UTF-16 offset
			# tiLine._startOffset is Global UTF-16 Start of Line
			text = fdm.getText()
			prefix = text[:target_char_offset]
			converter = WideStringOffsetConverter(prefix)
			target_utf16_offset = converter.encodedStringLength

			new_abs = tiLine._startOffset + target_utf16_offset
			tiNew = tiLine.copy()
			tiNew._startOffset = new_abs
			tiNew._endOffset = new_abs
			tiNew.updateCaret()
		else:
			tiLine.collapse()
			tiLine.move(textInfos.UNIT_CHARACTER, target_char_offset)
			tiLine.updateCaret()

		speech.speak([target_cell["text"]])

	@script(gesture="kb:control+alt+leftArrow")
	def script_prevTableCell(self, gesture):
		self._navigateTable(gesture, 0, -1)

	@script(gesture="kb:control+alt+rightArrow")
	def script_nextTableCell(self, gesture):
		self._navigateTable(gesture, 0, 1)

	@script(gesture="kb:control+alt+upArrow")
	def script_tableRowUp(self, gesture):
		self._navigateTable(gesture, -1, 0)

	@script(gesture="kb:control+alt+downArrow")
	def script_tableRowDown(self, gesture):
		self._navigateTable(gesture, 1, 0)

	def _find_block_boundary(self, direction, name_start, name_end):
		if not getattr(self, "markdownBrowseMode", False):
			return False

		try:
			with FastDocumentManager(self) as fdm:
				currentLineText = fdm.getText()
				matched_regex = None
				BLOCK_PATTERNS = [patterns.RE_LIST_ITEM, patterns.RE_TABLE, patterns.RE_BLOCKQUOTE]
				for regex in BLOCK_PATTERNS:
					if regex.match(currentLineText):
						matched_regex = regex
						break

				if not matched_regex:
					ui.message(_("Not inside a list, table, or blockquote"))
					return True

				last_matching_line = fdm.lineIndex

				while fdm.move(direction) != 0:
					text = fdm.getText()
					if not matched_regex.match(text):
						break
					last_matching_line = fdm.lineIndex

				# Move to the last matching line
				lineInfo = fdm.updateCaret(last_matching_line)
				speech.speakTextInfo(
					lineInfo,
					unit=textInfos.UNIT_LINE,
					reason=controlTypes.OutputReason.CARET,
				)
				return True

		except (RuntimeError, NotImplementedError, LookupError, COMError) as e:
			log.error(f"MarkdownNavigator: FastDocumentManager failed for boundary find: {e}")
			return False

	@script(gesture="kb:,")
	def script_endOfElement(self, gesture):
		if not self._find_block_boundary(1, _("start"), _("end")):
			gesture.send()

	@script(gesture="kb:shift+,")
	def script_startOfElement(self, gesture):
		if not self._find_block_boundary(-1, _("start"), _("end")):
			gesture.send()

	# Tables (Explicitly using _navigateBlock)
	@script(gesture="kb:t")
	def script_nextTable(self, gesture):
		self._navigateBlock(gesture, patterns.RE_TABLE, 1, _("table"), notFoundMessage=_("no next table"))

	@script(gesture="kb:shift+t")
	def script_prevTable(self, gesture):
		self._navigateBlock(
			gesture,
			patterns.RE_TABLE,
			-1,
			_("table"),
			notFoundMessage=_("no previous table"),
		)

	# Links & Images (Inline)
	@script(gesture="kb:k")
	def script_nextLink(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_LINK,
			1,
			_("link"),
			focus_element=True,
			notFoundMessage=_("no next link"),
		)

	@script(gesture="kb:shift+k")
	def script_prevLink(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_LINK,
			-1,
			_("link"),
			focus_element=True,
			notFoundMessage=_("no previous link"),
		)

	@script(gesture="kb:g")
	def script_nextImage(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_IMAGE,
			1,
			_("image"),
			focus_element=True,
			notFoundMessage=_("no next graphic"),
		)

	@script(gesture="kb:shift+g")
	def script_prevImage(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_IMAGE,
			-1,
			_("image"),
			focus_element=True,
			notFoundMessage=_("no previous graphic"),
		)

	@script(gesture="kb:m")
	def script_nextMathFormula(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_LATEX_MATH,
			1,
			# Translators: The element type announced when navigating to a math formula.
			_("math formula"),
			focus_element=True,
			# Translators: Message announced when there is no next math formula to navigate to.
			notFoundMessage=_("no next math formula"),
		)

	@script(gesture="kb:shift+m")
	def script_prevMathFormula(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_LATEX_MATH,
			-1,
			# Translators: The element type announced when navigating to a math formula.
			_("math formula"),
			focus_element=True,
			# Translators: Message announced when there is no previous math formula to navigate to.
			notFoundMessage=_("no previous math formula"),
		)

	# Block Elements
	@script(gesture="kb:h")
	def script_nextHeading(self, gesture):
		self._navigate(gesture, patterns.RE_HEADING, 1, _("heading"), notFoundMessage=_("no next heading"))

	@script(gesture="kb:shift+h")
	def script_prevHeading(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_HEADING,
			-1,
			_("heading"),
			notFoundMessage=_("no previous heading"),
		)

	@script(gesture="kb:i")
	def script_nextListItem(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_LIST_ITEM,
			1,
			_("list item"),
			notFoundMessage=_("no next list item"),
		)

	@script(gesture="kb:shift+i")
	def script_prevListItem(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_LIST_ITEM,
			-1,
			_("list item"),
			notFoundMessage=_("no previous list item"),
		)

	# Italics (E - Emphasis)
	@script(gesture="kb:e")
	def script_nextItalic(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_ITALIC,
			1,
			_("italic"),
			focus_element=True,
			notFoundMessage=_("no next italic"),
		)

	@script(gesture="kb:shift+e")
	def script_prevItalic(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_ITALIC,
			-1,
			_("italic"),
			focus_element=True,
			notFoundMessage=_("no previous italic"),
		)

	# Strikethrough (D - Delete)
	@script(gesture="kb:d")
	def script_nextStrikethrough(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_STRIKETHROUGH,
			1,
			_("strikethrough"),
			focus_element=True,
			notFoundMessage=_("no next strikethrough"),
		)

	@script(gesture="kb:shift+d")
	def script_prevStrikethrough(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_STRIKETHROUGH,
			-1,
			_("strikethrough"),
			focus_element=True,
			notFoundMessage=_("no previous strikethrough"),
		)

	# Bold (B)
	@script(gesture="kb:b")
	def script_nextBold(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_BOLD,
			1,
			_("bold"),
			focus_element=True,
			notFoundMessage=_("no next bold"),
		)

	@script(gesture="kb:shift+b")
	def script_prevBold(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_BOLD,
			-1,
			_("bold"),
			focus_element=True,
			notFoundMessage=_("no previous bold"),
		)

	# Footnotes (F)
	@script(gesture="kb:f")
	def script_nextFootnote(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_FOOTNOTE,
			1,
			_("footnote"),
			focus_element=True,
			notFoundMessage=_("no next footnote"),
		)

	@script(gesture="kb:shift+f")
	def script_prevFootnote(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_FOOTNOTE,
			-1,
			_("footnote"),
			focus_element=True,
			notFoundMessage=_("no previous footnote"),
		)

	@script(gesture="kb:l")
	def script_nextList(self, gesture):
		self._navigateBlock(gesture, patterns.RE_LIST_ITEM, 1, _("list"), notFoundMessage=_("no next list"))

	@script(gesture="kb:shift+l")
	def script_prevList(self, gesture):
		self._navigateBlock(
			gesture,
			patterns.RE_LIST_ITEM,
			-1,
			_("list"),
			notFoundMessage=_("no previous list"),
		)

	@script(gesture="kb:q")
	def script_nextBlockquote(self, gesture):
		self._navigateBlock(
			gesture,
			patterns.RE_BLOCKQUOTE,
			1,
			_("blockquote"),
			notFoundMessage=_("no next block quote"),
		)

	@script(gesture="kb:shift+q")
	def script_prevBlockquote(self, gesture):
		self._navigateBlock(
			gesture,
			patterns.RE_BLOCKQUOTE,
			-1,
			_("blockquote"),
			notFoundMessage=_("no previous block quote"),
		)

	@script(gesture="kb:c")
	def script_nextCodeBlock(self, gesture):
		self._navigateCode(gesture, 1, _("code"), notFoundMessage=_("no next code"))

	@script(gesture="kb:shift+c")
	def script_prevCodeBlock(self, gesture):
		self._navigateCode(gesture, -1, _("code"), notFoundMessage=_("no previous code"))

	@script(gesture="kb:s")
	def script_nextSeparator(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_SEPARATOR,
			1,
			_("separator"),
			notFoundMessage=_("no next separator"),
		)

	@script(gesture="kb:shift+s")
	def script_prevSeparator(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_SEPARATOR,
			-1,
			_("separator"),
			notFoundMessage=_("no previous separator"),
		)

	@script(gesture="kb:x")
	def script_nextCheckbox(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_CHECKBOX,
			1,
			_("checkbox"),
			notFoundMessage=_("no next check box"),
		)

	@script(gesture="kb:shift+x")
	def script_prevCheckbox(self, gesture):
		self._navigate(
			gesture,
			patterns.RE_CHECKBOX,
			-1,
			_("checkbox"),
			notFoundMessage=_("no previous check box"),
		)

	# Headings Levels
	@script(gesture="kb:1")
	def script_nextH1(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(1),
			1,
			_("level 1 heading"),
			notFoundMessage=_("No next heading at level {i}").format(i=1),
		)

	@script(gesture="kb:shift+1")
	def script_prevH1(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(1),
			-1,
			_("level 1 heading"),
			notFoundMessage=_("No previous heading at level {i}").format(i=1),
		)

	@script(gesture="kb:2")
	def script_nextH2(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(2),
			1,
			_("level 2 heading"),
			notFoundMessage=_("No next heading at level {i}").format(i=2),
		)

	@script(gesture="kb:shift+2")
	def script_prevH2(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(2),
			-1,
			_("level 2 heading"),
			notFoundMessage=_("No previous heading at level {i}").format(i=2),
		)

	@script(gesture="kb:3")
	def script_nextH3(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(3),
			1,
			_("level 3 heading"),
			notFoundMessage=_("No next heading at level {i}").format(i=3),
		)

	@script(gesture="kb:shift+3")
	def script_prevH3(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(3),
			-1,
			_("level 3 heading"),
			notFoundMessage=_("No previous heading at level {i}").format(i=3),
		)

	@script(gesture="kb:4")
	def script_nextH4(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(4),
			1,
			_("level 4 heading"),
			notFoundMessage=_("No next heading at level {i}").format(i=4),
		)

	@script(gesture="kb:shift+4")
	def script_prevH4(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(4),
			-1,
			_("level 4 heading"),
			notFoundMessage=_("No previous heading at level {i}").format(i=4),
		)

	@script(gesture="kb:5")
	def script_nextH5(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(5),
			1,
			_("level 5 heading"),
			notFoundMessage=_("No next heading at level {i}").format(i=5),
		)

	@script(gesture="kb:shift+5")
	def script_prevH5(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(5),
			-1,
			_("level 5 heading"),
			notFoundMessage=_("No previous heading at level {i}").format(i=5),
		)

	@script(gesture="kb:6")
	def script_nextH6(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(6),
			1,
			_("level 6 heading"),
			notFoundMessage=_("No next heading at level {i}").format(i=6),
		)

	@script(gesture="kb:shift+6")
	def script_prevH6(self, gesture):
		self._navigate(
			gesture,
			patterns.getHeadingRegex(6),
			-1,
			_("level 6 heading"),
			notFoundMessage=_("No previous heading at level {i}").format(i=6),
		)
