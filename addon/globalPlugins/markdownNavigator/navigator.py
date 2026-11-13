# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

from __future__ import annotations
import builtins
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
from speech import sayAll
from logHandler import log
from baseObject import ScriptableObject
from textInfos.offsets import Offsets, OffsetsTextInfo
from textUtils import getOffsetConverter
from . import patterns
from _ctypes import COMError
from NVDAObjects.IAccessible import IA2TextTextInfo

from .document import FastDocumentManager

addonHandler.initTranslation()


class MarkdownEditorOverlay(ScriptableObject):
	"""Overlay class to add Markdown navigation capabilities to EditableText objects."""

	markdownBrowseMode: bool = False

	@script(
		# Translators: Description for the toggle script.
		description=_("Toggles Markdown Browse Mode. When enabled, keys like H, I, T navigate content."),
		gesture="kb:NVDA+shift+space",
	)
	def script_toggleMarkdownBrowseMode(self, gesture) -> None:
		if self._hasActiveTreeInterceptor():
			return
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
		if self._hasActiveTreeInterceptor():
			scriptFunction = getattr(script, "__func__", script)
			if MarkdownEditorOverlay.__dict__.get(getattr(scriptFunction, "__name__", "")) is scriptFunction:
				return None
			return script
		if not self._isMarkdownBrowseActive():
			return script

		if script:
			return script

		# Trap non-command gestures if configured
		if config.conf["virtualBuffers"]["trapNonCommandGestures"] and gesture.isCharacter:
			return self.script_trapNonCommandGesture

		return None

	def _hasActiveTreeInterceptor(self) -> bool:
		"""Return whether a ready tree interceptor currently owns input."""
		treeInterceptor = getattr(self, "treeInterceptor", None)
		return bool(
			treeInterceptor and getattr(treeInterceptor, "isReady", False) and not treeInterceptor.passThrough
		)

	def _isMarkdownBrowseActive(self) -> bool:
		"""Return whether Markdown browse commands should handle input."""
		return bool(getattr(self, "markdownBrowseMode", False) and not self._hasActiveTreeInterceptor())

	def makeTextInfo(self, position):
		"""Create TextInfo instances, including bookmarks from flat IA2 ranges."""
		if (
			isinstance(position, Offsets)
			and not issubclass(self.TextInfo, OffsetsTextInfo)
			and hasattr(self, "IAccessibleTextObject")
		):
			return IA2TextTextInfo(self, position)
		return super().makeTextInfo(position)

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

		:param gesture: The gesture that triggered navigation.
		:param regex: Compiled regex pattern to match.
		:param direction: Direction (1=forward, -1=backward).
		:param name: Human-readable name of the element type.
		:param focus_element: Whether to position caret at match (True for inline elements).
		:param notFoundMessage: Custom message when element not found.
		"""
		if not self._isMarkdownBrowseActive():
			if not self._hasActiveTreeInterceptor():
				gesture.send()
			return
		with FastDocumentManager(self) as fdm:
			self._navigateFast(fdm, regex, direction, name, focus_element, notFoundMessage)

	def _moveToCharacterRange(
		self,
		textInfo: textInfos.TextInfo,
		text: str,
		charOffset: int,
		isWeb: bool,
		charLength: int = 0,
	) -> None:
		"""Move the caret to a Python character offset, using IA2 UTF-16 offsets for web editors."""
		textInfo = self._getCharacterRangeTextInfo(
			textInfo,
			text,
			charOffset,
			charLength if isWeb else 0,
		)
		textInfo.updateCaret()

	def _getCharacterRangeTextInfo(
		self,
		textInfo: textInfos.TextInfo,
		text: str,
		charOffset: int,
		charLength: int = 0,
	) -> textInfos.TextInfo:
		"""Return a TextInfo for a Python character range."""
		if isinstance(textInfo, OffsetsTextInfo):
			converter = getOffsetConverter(textInfo.encoding)(text)
			startOffset, endOffset = converter.strToEncodedOffsets(
				charOffset,
				charOffset + charLength,
			)
			textInfo = textInfo.copy()
			lineStartOffset = textInfo._startOffset
			textInfo._startOffset = lineStartOffset + startOffset
			textInfo._endOffset = lineStartOffset + endOffset
			return textInfo

		startInfo = textInfo.moveToCodepointOffset(charOffset)
		if charLength:
			endInfo = textInfo.moveToCodepointOffset(charOffset + charLength)
			startInfo.setEndPoint(endInfo, "endToStart")
		return startInfo

	def _navigateFast(
		self,
		fdm: FastDocumentManager,
		regex: re.Pattern,
		direction: int,
		name: str,
		focus_element: bool,
		notFoundMessage: str | None,
	) -> None:
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
				self._moveToCharacterRange(
					lineInfo,
					currentLineText,
					target_match.start(),
					isWeb,
					len(target_match.group()),
				)
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
					self._moveToCharacterRange(lineInfo, text, m.start(), isWeb, len(m.group()))
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
		if not self._isMarkdownBrowseActive():
			if not self._hasActiveTreeInterceptor():
				gesture.send()
			return
		with FastDocumentManager(self) as fdm:
			self._navigateBlockFast(fdm, regex, direction, name, notFoundMessage)

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
		if not self._isMarkdownBrowseActive():
			if not self._hasActiveTreeInterceptor():
				gesture.send()
			return
		with FastDocumentManager(self) as fdm:
			self._navigateCodeFast(fdm, direction, name, notFoundMessage)

	def _navigateCodeFast(self, fdm, direction, name, notFoundMessage):
		"""Implementing Code Block Navigation with FastDocumentManager"""
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
				self._moveToCharacterRange(
					lineInfo,
					currentLineText,
					target_match.start(),
					isWeb,
					len(target_match.group()),
				)
				speech.speak([target_match.group()])
				return

		found = False

		# If skipping block, consume lines until we hit another boundary
		if should_skip_block:
			log.debug("MarkdownNavigator: Skipping logic active.")
			# Simple skip logic: Keep searching until the next RE_CODE_BLOCK is found.
			# Note: This assumes it's paired.

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
								fdm.lineIndex = scanLine
								found = True
								break
						# If not found start, maybe just stop at this end tag?
						if not found:
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
					self._moveToCharacterRange(lineInfo, text, m.start(), isWeb, len(m.group()))
					speech.speak([m.group()])
					break

		if not found:
			msg = (
				notFoundMessage
				if notFoundMessage
				else (_("no next %s found") % name if direction == 1 else _("no previous %s found") % name)
			)
			ui.message(msg)

	def isTableNavigationAvailable(self) -> bool:
		"""Return whether Markdown table navigation is available at the caret."""
		if not self._isMarkdownBrowseActive() or self._inNativeTable():
			return False
		try:
			lineInfo = self.makeTextInfo(textInfos.POSITION_CARET)
			lineInfo.expand(textInfos.UNIT_LINE)
			return bool(patterns.RE_TABLE.match(lineInfo.text) and patterns.parseTableRow(lineInfo.text))
		except (RuntimeError, NotImplementedError, LookupError, COMError, OSError, ValueError):
			return False

	def _getTableContext(self, fdm):
		"""Return the table rows and current cell coordinates for a document manager."""
		caretOffset = max(0, fdm.initialCaretOffset - fdm.getLineOffset())
		return patterns.getTableContext(fdm.getText, fdm.nLines, fdm.lineIndex, caretOffset)

	def _inNativeTable(self) -> bool:
		"""Return whether NVDA reports the caret inside a native table."""
		inTable = getattr(super(), "_inTable", None)
		if inTable is None:
			return False
		try:
			return inTable(self.makeTextInfo(textInfos.POSITION_CARET))
		except (RuntimeError, NotImplementedError, LookupError, COMError, OSError, ValueError):
			return False

	def _fallbackTableScript(self, scriptName, gesture, sendGesture):
		"""Run an underlying NVDA table script or optionally pass the gesture through."""
		nativeTableScript = getattr(super(), f"script_{scriptName}", None)
		if nativeTableScript is not None and self._inNativeTable():
			nativeTableScript(gesture)
		elif sendGesture:
			try:
				gesture.send()
			except NotImplementedError:
				pass

	def _navigateTable(self, gesture, scriptName, rowOffset=0, columnOffset=0, toEdge=False):
		"""Move to a Markdown table cell, or pass the gesture through outside browse mode."""
		if self._hasActiveTreeInterceptor():
			return
		if not self._isMarkdownBrowseActive() or self._inNativeTable():
			self._fallbackTableScript(scriptName, gesture, sendGesture=True)
			return
		with FastDocumentManager(self) as fdm:
			self._navigateTableFast(fdm, rowOffset, columnOffset, toEdge)

	def _navigateTableFast(self, fdm, rowOffset=0, columnOffset=0, toEdge=False):
		"""Move to a Markdown table cell using a preloaded document."""
		context = self._getTableContext(fdm)
		if context is None:
			# Translators: Message shown when a Markdown table command is used outside a table.
			ui.message(_("Not inside a table"))
			return
		target = patterns.getTableCellForMovement(context, rowOffset, columnOffset, toEdge)
		if target is None:
			# Translators: Message shown when table navigation reaches the table boundary.
			ui.message(_("Edge of table"))
			return
		lineIndex, cell = target
		self._moveToTableCell(fdm, lineIndex, cell)

	def _getTableCellTextInfo(self, fdm, lineIndex, cell):
		"""Return a TextInfo restricted to one Markdown table cell."""
		return self._getCharacterRangeTextInfo(
			fdm.getTextInfo(lineIndex),
			fdm.getText(lineIndex),
			cell["content_start"],
			len(cell["text"]),
		)

	def _moveToTableCell(self, fdm, lineIndex, targetCell):
		"""Move the caret to a Markdown table cell and speak its text."""
		textInfo = self._getTableCellTextInfo(fdm, lineIndex, targetCell)
		textInfo.collapse()
		textInfo.updateCaret()
		speech.speakMessage(targetCell["text"])

	def _markdownTableSayAll(self, gesture, scriptName, axis, startAtFirst, updateCaret):
		"""Read Markdown table cells along one axis using NVDA's table say-all."""
		if self._hasActiveTreeInterceptor():
			return
		if not self._isMarkdownBrowseActive() or self._inNativeTable():
			self._fallbackTableScript(scriptName, gesture, sendGesture=False)
			return
		with FastDocumentManager(self) as fdm:
			context = self._getTableContext(fdm)
			if context is None:
				# Translators: Message shown when a Markdown table command is used outside a table.
				ui.message(_("Not inside a table"))
				return
			rows, currentRow, currentColumn = context
			if axis == "row":
				lineIndex, cells = rows[currentRow]
				startColumn = 0 if startAtFirst else currentColumn
				selectedCells = [(lineIndex, cell) for cell in cells[startColumn:]]
			elif axis == "column":
				startRow = 0 if startAtFirst else currentRow
				selectedCells = [
					(lineIndex, cells[min(currentColumn, len(cells) - 1)])
					for lineIndex, cells in rows[startRow:]
				]
			else:
				raise ValueError(f"Unknown table axis {axis!r}")

			def getBlankTextWithFields(_formatConfig=None):
				"""Return NVDA's localized speech text for an empty table cell."""
				# Translators: Spoken for an empty Markdown table cell.
				return [builtins._("blank")]

			cellTextInfos = []
			for lineIndex, cell in selectedCells:
				cellTextInfo = self._getTableCellTextInfo(fdm, lineIndex, cell)
				if not cell["text"]:
					cellTextInfo.getTextWithFields = getBlankTextWithFields
				cellTextInfos.append(cellTextInfo)

		remainingTextInfos = iter(cellTextInfos[1:])

		def nextCell(_textInfo):
			"""Return the next cell to NVDA's table say-all reader."""
			return next(remainingTextInfos)

		sayAll.SayAllHandler.readText(
			sayAll.CURSOR.TABLE,
			cellTextInfos[0],
			nextCell,
			updateCaret,
			startedFromScript=True,
		)

	@script(
		# Translators: Description for moving to the previous Markdown table column.
		description=_("Moves to the previous table column"),
		gesture="kb:control+alt+leftArrow",
	)
	def script_previousColumn(self, gesture):
		"""Move to the previous Markdown table column."""
		self._navigateTable(gesture, "previousColumn", columnOffset=-1)

	@script(
		# Translators: Description for moving to the next Markdown table column.
		description=_("Moves to the next table column"),
		gesture="kb:control+alt+rightArrow",
	)
	def script_nextColumn(self, gesture):
		"""Move to the next Markdown table column."""
		self._navigateTable(gesture, "nextColumn", columnOffset=1)

	@script(
		# Translators: Description for moving to the previous Markdown table row.
		description=_("Moves to the previous table row"),
		gesture="kb:control+alt+upArrow",
	)
	def script_previousRow(self, gesture):
		"""Move to the previous Markdown table row."""
		self._navigateTable(gesture, "previousRow", rowOffset=-1)

	@script(
		# Translators: Description for moving to the next Markdown table row.
		description=_("Moves to the next table row"),
		gesture="kb:control+alt+downArrow",
	)
	def script_nextRow(self, gesture):
		"""Move to the next Markdown table row."""
		self._navigateTable(gesture, "nextRow", rowOffset=1)

	@script(
		# Translators: Description for moving to the first Markdown table row.
		description=_("Moves to the first table row"),
		gesture="kb:control+alt+pageUp",
	)
	def script_firstRow(self, gesture):
		"""Move to the first Markdown table row."""
		self._navigateTable(gesture, "firstRow", rowOffset=-1, toEdge=True)

	@script(
		# Translators: Description for moving to the last Markdown table row.
		description=_("Moves to the last table row"),
		gesture="kb:control+alt+pageDown",
	)
	def script_lastRow(self, gesture):
		"""Move to the last Markdown table row."""
		self._navigateTable(gesture, "lastRow", rowOffset=1, toEdge=True)

	@script(
		# Translators: Description for moving to the first Markdown table column.
		description=_("Moves to the first table column"),
		gesture="kb:control+alt+home",
	)
	def script_firstColumn(self, gesture):
		"""Move to the first Markdown table column."""
		self._navigateTable(gesture, "firstColumn", columnOffset=-1, toEdge=True)

	@script(
		# Translators: Description for moving to the last Markdown table column.
		description=_("Moves to the last table column"),
		gesture="kb:control+alt+end",
	)
	def script_lastColumn(self, gesture):
		"""Move to the last Markdown table column."""
		self._navigateTable(gesture, "lastColumn", columnOffset=1, toEdge=True)

	@script(
		# Translators: Description for reading the current Markdown table row.
		description=_("Reads the current row from left to right without moving the caret"),
		gesture="kb:NVDA+control+alt+leftArrow",
		speakOnDemand=True,
	)
	def script_speakRow(self, gesture):
		"""Read the current Markdown table row without moving the caret."""
		self._markdownTableSayAll(gesture, "speakRow", "row", startAtFirst=True, updateCaret=False)

	@script(
		# Translators: Description for reading the current Markdown table column.
		description=_("Reads the current column from top to bottom without moving the caret"),
		gesture="kb:NVDA+control+alt+upArrow",
		speakOnDemand=True,
	)
	def script_speakColumn(self, gesture):
		"""Read the current Markdown table column without moving the caret."""
		self._markdownTableSayAll(gesture, "speakColumn", "column", startAtFirst=True, updateCaret=False)

	@script(
		# Translators: Description for reading rightwards from the current Markdown table cell.
		description=_("Reads from the current cell to the end of the row"),
		gesture="kb:NVDA+control+alt+rightArrow",
		speakOnDemand=True,
	)
	def script_sayAllRow(self, gesture):
		"""Read from the current Markdown table cell to the end of its row."""
		self._markdownTableSayAll(gesture, "sayAllRow", "row", startAtFirst=False, updateCaret=True)

	@script(
		# Translators: Description for reading downwards from the current Markdown table cell.
		description=_("Reads from the current cell to the end of the column"),
		gesture="kb:NVDA+control+alt+downArrow",
		speakOnDemand=True,
	)
	def script_sayAllColumn(self, gesture):
		"""Read from the current Markdown table cell to the end of its column."""
		self._markdownTableSayAll(gesture, "sayAllColumn", "column", startAtFirst=False, updateCaret=True)

	def _find_block_boundary(self, direction):
		if not self._isMarkdownBrowseActive():
			return self._hasActiveTreeInterceptor()

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
		if not self._find_block_boundary(1):
			gesture.send()

	@script(gesture="kb:shift+,")
	def script_startOfElement(self, gesture):
		if not self._find_block_boundary(-1):
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
