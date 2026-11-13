# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA - Document Manager Module
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

"""Fast document management for efficient text navigation.

This module provides the FastDocumentManager class and related utilities
for preloading document text and performing fast line-based navigation
without repeated IPC calls.
"""

from __future__ import annotations
from typing import TYPE_CHECKING

import bisect
import textInfos
from logHandler import log
from _ctypes import COMError
from textInfos.offsets import OffsetsTextInfo
from textUtils import getOffsetConverter
from appModules.devenv import VsWpfTextViewTextInfo
from NVDAObjects.IAccessible import IA2TextTextInfo

if TYPE_CHECKING:
	from NVDAObjects import NVDAObject

def getLogicalLineUnit(textInfo: textInfos.TextInfo) -> str:
	"""Return the appropriate paragraph unit based on the control type."""
	return textInfos.UNIT_LINE if isinstance(textInfo, VsWpfTextViewTextInfo) else textInfos.UNIT_PARAGRAPH


class FastDocumentManager:
	"""Document preload manager for fast line traversal.

	This class fetches the entire document text at once and supports
	fast line-by-line navigation without repeated IPC calls.

	The implementation strategy is inspired by the 'FastLineManagerV2' from
	the 'nvda-indent-nav' add-on by Tony Malykh:
	https://github.com/mltony/nvda-indent-nav
	"""

	def __init__(self, obj: NVDAObject) -> None:
		self.obj: NVDAObject = obj
		self.documentText: str | None = None
		self.pyOffsets: list[int] = []
		self.utf16Offsets: list[int] = []
		self.documentUtf16Length: int = 0
		self._offsetConverter = None
		self.lineIndex: int = 0
		self.originalLineIndex: int = 0
		self.nLines: int = 0
		self.document: textInfos.TextInfo | None = None
		self.originalCaret: textInfos.TextInfo | None = None
		self.initialCaretOffset: int = 0

	def __enter__(self) -> FastDocumentManager:
		"""Enter context manager and preload document text."""
		try:
			self.document = self.obj.makeTextInfo(textInfos.POSITION_ALL)
			self.originalCaret = self.obj.makeTextInfo(textInfos.POSITION_CARET)
		except (NotImplementedError, LookupError, COMError) as e:
			raise RuntimeError(f"Cannot obtain document TextInfo: {e}")

		self.originalCaret.collapse()
		pretext = self.originalCaret.copy()
		pretext.setEndPoint(self.document, "startToStart")
		self.documentText = self.document.text
		if isinstance(self.document, OffsetsTextInfo):
			self._offsetConverter = getOffsetConverter(self.document.encoding)(self.documentText)

		# Calculate offsets: maintain both Python indices (for regex/slicing)
		# and UTF-16 offsets (for TextInfo operations)
		self.pyOffsets = [0]
		self.utf16Offsets = [0]
		currentUtf16 = 0
		lastPy = 0

		for m in textInfos.RE_EOL.finditer(self.documentText):
			pyEnd = m.end()
			chunk = self.documentText[lastPy:pyEnd]
			# Calculate UTF-16 length
			chunkUtf16Len = len(chunk.encode("utf-16-le")) // 2
			currentUtf16 += chunkUtf16Len

			self.pyOffsets.append(pyEnd)
			self.utf16Offsets.append(currentUtf16)
			lastPy = pyEnd
		self.documentUtf16Length = currentUtf16 + len(self.documentText[lastPy:].encode("utf-16-le")) // 2

		# Determine caret line using Python offsets
		# Note: len(pretext.text) returns Python character count
		caretOffset = len(pretext.text)
		self.initialCaretOffset = caretOffset
		self.lineIndex = bisect.bisect_right(self.pyOffsets, caretOffset) - 1
		if self.lineIndex < 0:
			self.lineIndex = 0
		self.originalLineIndex = self.lineIndex
		self.nLines = len(self.pyOffsets)

		return self

	def __exit__(self, exc_type, exc_val, exc_tb) -> None:
		pass

	def move(self, increment: int) -> int:
		"""Move to the next or previous line.

		:return: Actual increment moved (0 if boundary reached).
		"""
		newIndex = self.lineIndex + increment
		if newIndex < 0 or newIndex >= self.nLines:
			return 0
		self.lineIndex = newIndex
		return increment

	def getText(self, lineIndex: int | None = None) -> str:
		"""Get the text content of the specified line (or current line)."""
		if lineIndex is None:
			lineIndex = self.lineIndex
		if lineIndex < 0 or lineIndex >= self.nLines:
			return ""
		startOffset = self.pyOffsets[lineIndex]
		try:
			endOffset = self.pyOffsets[lineIndex + 1]
		except IndexError:
			endOffset = len(self.documentText)
		return self.documentText[startOffset:endOffset]

	def getLineOffset(self, lineIndex: int | None = None) -> int:
		"""Get the Python start offset of the specified line (or current line)."""
		if lineIndex is None:
			lineIndex = self.lineIndex
		return self.pyOffsets[lineIndex] if lineIndex < self.nLines else len(self.documentText)

	def getTextInfo(self, lineIndex: int | None = None) -> textInfos.TextInfo:
		"""Get a TextInfo object for the specified line (or current line).

		Handles OffsetsTextInfo via textUtils and Web environments via flat injection.
		"""
		if lineIndex is None:
			lineIndex = self.lineIndex

		if isinstance(self.document, OffsetsTextInfo):
			# moveToCodepointOffset would refetch the full document for every cell.
			textInfo = self.document.copy()
			startOffset = self.pyOffsets[lineIndex]
			endOffset = self.pyOffsets[lineIndex + 1] if lineIndex + 1 < self.nLines else len(self.documentText)
			textInfo._startOffset, textInfo._endOffset = self._offsetConverter.strToEncodedOffsets(
				startOffset,
				endOffset,
			)
			return textInfo
		else:
			# Fallback for non-OffsetsTextInfo
			# Check if this is a web browser environment for optimized positioning
			appName = getattr(self.obj.appModule, "appName", "").lower()
			isWeb = appName in ("chrome", "msedge", "firefox", "opera", "brave", "browser")

			if isWeb:
				# Optimization V3: Use flattened IA2TextTextInfo with manual offset injection
				# This bypasses the Compound structure and maps directly to global UTF-16 offsets
				try:
					# Get precomputed UTF-16 offset
					targetUtf16 = (
						self.utf16Offsets[lineIndex]
						if lineIndex < len(self.utf16Offsets)
						else self.utf16Offsets[-1]
					)

					if (
						hasattr(self.obj, "IAccessibleTextObject")
						and self.obj.IAccessibleTextObject.nCharacters == self.documentUtf16Length
					):
						# Create a flat IA2TextTextInfo
						flatInfo = IA2TextTextInfo(self.obj, textInfos.POSITION_ALL)

						# Force set offsets
						flatInfo._startOffset = targetUtf16
						flatInfo._endOffset = targetUtf16

						# Expand to line for speech
						try:
							flatInfo.expand(getLogicalLineUnit(flatInfo))
						except Exception as e:
							log.debugWarning(f"FastDocumentManager: flatInfo.expand failed ({e})")

						return flatInfo
					else:
						log.debugWarning(
							"FastDocumentManager: Object does not expose one flat IA2 text buffer",
						)

				except Exception as e:
					log.debugWarning(f"FastDocumentManager: Flat IA2TextTextInfo failed ({e}), falling back")

				# Fall through to paragraph movement if optimization fails

			# Traditional line-by-line movement (Notepad, WordPad, etc.)
			unit = getLogicalLineUnit(self.document)
			delta = lineIndex - self.originalLineIndex
			textInfo = self.originalCaret.copy()
			textInfo.expand(unit)
			textInfo.collapse()
			textInfo.move(unit, delta)
			textInfo.expand(unit)
			return textInfo

	def updateCaret(self, lineIndex: int | None = None) -> textInfos.TextInfo:
		"""Update the caret to the specified line (or current line)."""
		lineInfo = self.getTextInfo(lineIndex)
		caret = lineInfo.copy()
		caret.collapse()
		caret.updateCaret()
		return lineInfo
