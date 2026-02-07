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


def getHeadingRegex(level):
	return re.compile(r"^\s*#{%d}\s" % level)
