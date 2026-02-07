# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

import globalPluginHandler
import controlTypes

from .navigator import MarkdownEditorOverlay


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Apply to all EditableText objects (Edit controls, RichEdit, etc.)
		# Also explicitly check for Scintilla to be safe, as sometimes Role might be unstable or specific
		# Windows 11 Notepad uses RichEditD2DPT class
		# Use getattr to safely access windowClassName, especially on Secure Desktops where it might be missing
		windowClassName = getattr(obj, "windowClassName", "")
		if (
			obj.role == controlTypes.Role.EDITABLETEXT
			or windowClassName == "Scintilla"
			or windowClassName == "RichEditD2DPT"
		):
			clsList.insert(0, MarkdownEditorOverlay)
