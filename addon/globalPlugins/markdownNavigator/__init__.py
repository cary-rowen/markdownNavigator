# -*- coding: UTF-8 -*-
# Markdown Navigator for NVDA
# Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
# This file is covered by the GNU General Public License.

import controlTypes
import globalPluginHandler
import winUser
from logHandler import log

from .navigator import MarkdownEditorOverlay

_SUPPORTED_EDITOR_WINDOW_CLASSES = frozenset(
	{
		"Scintilla",
		"RichEditD2DPT",
		"AkelEditW",
	},
)


def _shouldApplyMarkdownOverlay(obj) -> bool:
	"""Return whether Markdown navigation should be added to the control."""
	windowClassName = getattr(obj, "windowClassName", "")
	if windowClassName in _SUPPORTED_EDITOR_WINDOW_CLASSES:
		try:
			states = obj.states
		except Exception:
			log.warning(
				f"MarkdownNavigator: could not get states while choosing overlay classes "
				f"for {obj.__class__.__name__} with window class {windowClassName!r}",
				exc_info=True,
			)
			return False
		if controlTypes.State.PROTECTED in states:
			return False
		try:
			return obj.role != controlTypes.Role.PASSWORDEDIT
		except Exception:
			log.warning(
				f"MarkdownNavigator: could not get role while choosing overlay classes "
				f"for {obj.__class__.__name__} with window class {windowClassName!r}",
				exc_info=True,
			)
			return False
	try:
		role = obj.role
	except Exception:
		log.warning(
			f"MarkdownNavigator: could not get role while choosing overlay classes "
			f"for {obj.__class__.__name__} with window class {windowClassName!r}",
			exc_info=True,
		)
		return False
	if role == controlTypes.Role.PASSWORDEDIT:
		return False
	if role != controlTypes.Role.EDITABLETEXT:
		return False
	try:
		states = obj.states
	except Exception:
		log.warning(
			f"MarkdownNavigator: could not get states while choosing overlay classes "
			f"for {obj.__class__.__name__} with window class {windowClassName!r}",
			exc_info=True,
		)
		return False
	if controlTypes.State.PROTECTED in states:
		return False
	if getattr(obj, "windowStyle", 0) & winUser.ES_MULTILINE:
		return True
	return controlTypes.State.MULTILINE in states


class GlobalPlugin(globalPluginHandler.GlobalPlugin):
	"""Inject Markdown navigation overlays into supported editor controls."""

	def chooseNVDAObjectOverlayClasses(self, obj, clsList):
		"""Add the Markdown overlay to controls that can contain Markdown documents."""
		if _shouldApplyMarkdownOverlay(obj):
			clsList.insert(0, MarkdownEditorOverlay)
