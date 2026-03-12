# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

import globalPluginHandler
import controlTypes
from NVDAObjects.IAccessible import ia2Web

from .navigator import MarkdownEditorOverlay


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		# Apply to desktop EditableText objects (Edit controls, RichEdit, etc.)
		# Also explicitly check for Scintilla to be safe, as sometimes Role might be unstable or specific
		# Windows 11 Notepad uses RichEditD2DPT class
		# Use getattr to safely access windowClassName, especially on Secure Desktops where it might be missing
		# Exclude IA2 web objects (Chromium/Electron editors) as their text
		# interface is not compatible with this add-on's plain-text navigation.
		if any(issubclass(cls, ia2Web.Ia2Web) for cls in clsList):
			return
		windowClassName = getattr(obj, "windowClassName", "")
		if (
			obj.role == controlTypes.Role.EDITABLETEXT
			or windowClassName == "Scintilla"
			or windowClassName == "RichEditD2DPT"
			or windowClassName == "AkelEditW"
		):
			clsList.insert(0, MarkdownEditorOverlay)
