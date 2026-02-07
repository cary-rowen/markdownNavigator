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

import re
import bisect
import textInfos
from logHandler import log
from _ctypes import COMError
from textInfos.offsets import OffsetsTextInfo
from appModules.devenv import VsWpfTextViewTextInfo
from NVDAObjects.IAccessible import IA2TextTextInfo

if TYPE_CHECKING:
	from NVDAObjects import NVDAObject

#: Regex pattern for splitting text into lines.
NEWLINE_REGEX = re.compile(r"\r?\n|\r")


def _splitLines(text: str) -> list[int]:
	"""Split text into lines using regex and return a list of start offsets for each line."""
	offsets = [0]
	for m in NEWLINE_REGEX.finditer(text):
		offsets.append(m.end())
	return offsets


def _getParagraphUnit(textInfo: textInfos.TextInfo) -> str:
	"""Return the appropriate paragraph unit based on the control type."""
	try:
		if isinstance(textInfo, VsWpfTextViewTextInfo):
			return textInfos.UNIT_LINE
	except NameError:
		pass
	return textInfos.UNIT_PARAGRAPH


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

		# Calculate offsets: maintain both Python indices (for regex/slicing)
		# and UTF-16 offsets (for TextInfo operations)
		self.pyOffsets = [0]
		self.utf16Offsets = [0]
		currentUtf16 = 0
		lastPy = 0

		for m in NEWLINE_REGEX.finditer(self.documentText):
			pyEnd = m.end()
			chunk = self.documentText[lastPy:pyEnd]
			# Calculate UTF-16 length
			chunkUtf16Len = len(chunk.encode("utf-16-le")) // 2
			currentUtf16 += chunkUtf16Len

			self.pyOffsets.append(pyEnd)
			self.utf16Offsets.append(currentUtf16)
			lastPy = pyEnd

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
			textInfo = self.document.copy()
			offset = 0

			# Try using textUtils to handle different encodings (e.g., Scintilla's UTF-8)
			encoding = getattr(textInfo, "encoding", None)
			if encoding:
				from textUtils import getOffsetConverter

				pyOffset = self.pyOffsets[lineIndex]
				try:
					converter = getOffsetConverter(encoding)(self.documentText)
					# Note: strToEncodedOffsets returns tuple (start, end), we need start
					offset = converter.strToEncodedOffsets(pyOffset)
					if isinstance(offset, tuple):
						offset = offset[0]
				except Exception as e:
					log.debugWarning(
						f"FastDocumentManager: textUtils conversion failed ({e}), falling back to UTF-16",
					)
					# Fall back to precomputed UTF-16 offsets
					if lineIndex < len(self.utf16Offsets):
						offset = self.utf16Offsets[lineIndex]
					else:
						# Handle end-of-document case
						lastKnownPy = self.pyOffsets[-1]
						lastKnownUtf16 = self.utf16Offsets[-1]
						remainingText = self.documentText[lastKnownPy:]
						offset = lastKnownUtf16 + (len(remainingText.encode("utf-16-le")) // 2)
			else:
				# No specific encoding, default to Windows UTF-16
				if lineIndex < len(self.utf16Offsets):
					offset = self.utf16Offsets[lineIndex]
				else:
					# Handle end-of-document case
					lastKnownPy = self.pyOffsets[-1]
					lastKnownUtf16 = self.utf16Offsets[-1]
					remainingText = self.documentText[lastKnownPy:]
					offset = lastKnownUtf16 + (len(remainingText.encode("utf-16-le")) // 2)

			textInfo._startOffset = textInfo._endOffset = offset
			textInfo.expand(textInfos.UNIT_LINE)
			return textInfo
		else:
			# Fallback for non-OffsetsTextInfo
			# Check if this is a web browser environment for optimized positioning
			appName = getattr(self.obj.appModule, "appName", "").lower()
			isWeb = appName in ("chrome", "msedge", "firefox", "opera", "brave", "browser")

			if isWeb:
				self.pyOffsets[lineIndex] if lineIndex < self.nLines else len(self.documentText)

				# Optimization V3: Use flattened IA2TextTextInfo with manual offset injection
				# This bypasses the Compound structure and maps directly to global UTF-16 offsets
				try:
					# Get precomputed UTF-16 offset
					targetUtf16 = (
						self.utf16Offsets[lineIndex]
						if lineIndex < len(self.utf16Offsets)
						else self.utf16Offsets[-1]
					)

					if hasattr(self.obj, "IAccessibleTextObject"):
						# Create a flat IA2TextTextInfo
						flatInfo = IA2TextTextInfo(self.obj, textInfos.POSITION_ALL)

						# Force set offsets
						flatInfo._startOffset = targetUtf16
						flatInfo._endOffset = targetUtf16

						# Expand to line for speech
						try:
							flatInfo.expand(textInfos.UNIT_LINE)
						except Exception as e:
							log.debugWarning(f"FastDocumentManager: flatInfo.expand failed ({e})")

						return flatInfo
					else:
						log.debugWarning(
							"FastDocumentManager: Object missing IAccessibleTextObject, cannot use flat info",
						)

				except Exception as e:
					log.debugWarning(f"FastDocumentManager: Flat IA2TextTextInfo failed ({e}), falling back")

				# Fall through to paragraph movement if optimization fails

			# Traditional line-by-line movement (Notepad, WordPad, etc.)
			unit = _getParagraphUnit(self.document)
			delta = lineIndex - self.originalLineIndex
			textInfo = self.originalCaret.copy()
			textInfo.expand(unit)
			textInfo.collapse()
			textInfo.move(unit, delta)
			textInfo.expand(textInfos.UNIT_LINE)
			return textInfo

	def updateCaret(self, lineIndex: int | None = None) -> textInfos.TextInfo:
		"""Update the caret to the specified line (or current line)."""
		lineInfo = self.getTextInfo(lineIndex)
		caret = lineInfo.copy()
		caret.collapse()
		caret.updateCaret()
		return lineInfo
