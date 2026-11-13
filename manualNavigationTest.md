# Markdown Navigator Manual Test Document

Use this file in an editable Markdown control. Start near the top, enable Markdown Browse Mode with NVDA+shift+space, then test each shortcut forward and backward.

## Quick Coverage Map

| Shortcut | Element | First test marker |
| --- | --- | --- |
| H / shift+H | Any heading | H1-A |
| 1-6 / shift+1-6 | Heading levels | H1-A through H6-A |
| T / shift+T | Table block | TABLE-A |
| L / shift+L | List block | LIST-A |
| I / shift+I | List item | ITEM-A1 |
| Q / shift+Q | Blockquote block | QUOTE-A |
| C / shift+C | Code block or inline code | CODE-A and INLINE-CODE-A |
| S / shift+S | Separator | SEPARATOR-A |
| X / shift+X | Checkbox | CHECKBOX-A |
| K / shift+K | Link | LINK-A |
| G / shift+G | Image | IMAGE-A |
| B / shift+B | Bold | BOLD-A |
| E / shift+E | Italic | ITALIC-A |
| D / shift+D | Strikethrough | STRIKE-A |
| F / shift+F | Footnote | FOOTNOTE-A |
| M / shift+M | Math formula | MATH-A |
| Comma / shift+comma | End/start of block | LIST-A, TABLE-A, QUOTE-A |
| Ctrl+alt+arrows | Adjacent table cell navigation | CELL-A1 |
| Ctrl+alt+Home/End/PageUp/PageDown | Table edge navigation | CELL-B2 |
| NVDA+ctrl+alt+arrows | Read table row or column | CELL-B2 |

# H1-A Top Level Heading

Plain paragraph before the first structured elements. It contains LINK-A [Open NVDA](https://www.nvaccess.org/) and IMAGE-A ![NVDA logo placeholder](https://example.com/nvda.png).

This sentence contains BOLD-A **bold text alpha**, ITALIC-A *italic text alpha*, STRIKE-A ~~deleted text alpha~~, INLINE-CODE-A `inline_code_alpha()`, FOOTNOTE-A [^alpha], and MATH-A $a^2 + b^2 = c^2$.

## H2-A Lists And Checkboxes

LIST-A unordered list starts below.

- ITEM-A1 first unordered item
- ITEM-A2 second unordered item with nested formatting: **bold inside item** and `code_inside_item`
- ITEM-A3 third unordered item

LIST-B ordered list starts below.

1. ITEM-B1 first ordered item
2. ITEM-B2 second ordered item
3. ITEM-B3 third ordered item

CHECKBOX-A task list starts below.

- [ ] CHECKBOX-A unchecked task
- [x] CHECKBOX-B checked task lowercase
1. [X] CHECKBOX-C checked task uppercase in ordered list

### H3-A Blockquotes

QUOTE-A blockquote starts below.

> QUOTE-A line 1 of first quote block
> QUOTE-A line 2 of first quote block with [quoted link](https://example.com/quote)
> QUOTE-A line 3 of first quote block

Plain paragraph between quote blocks.

> QUOTE-B line 1 of second quote block
> QUOTE-B line 2 of second quote block

#### H4-A Tables

TABLE-A begins below. Use Ctrl+alt+left/right/up/down inside this table.

From CELL-B2:

- Ctrl+alt+Home moves to CELL-B1; Ctrl+alt+End moves to CELL-B4.
- Ctrl+alt+PageUp moves to Column 2; Ctrl+alt+PageDown moves to CELL-C2 with escaped pipe content.
- NVDA+ctrl+alt+Left reads CELL-B1 through CELL-B4 without moving the caret.
- NVDA+ctrl+alt+Up reads Column 2, the separator cell, CELL-A2, CELL-B2, and CELL-C2 without moving the caret.
- NVDA+ctrl+alt+Right reads CELL-B2 through CELL-B4 and leaves the caret at CELL-B4.
- NVDA+ctrl+alt+Down reads CELL-B2 and CELL-C2 and leaves the caret at CELL-C2.

With Easy Table Navigator installed, assign its toggle command, enable its table layer on CELL-B2, and verify that plain arrows perform the same adjacent-cell movements. Home, End, PageUp, and PageDown should perform the same edge movements.

While the Easy Table Navigator layer is still enabled, turn Markdown Browse Mode off. Plain arrows, Ctrl+arrows, Home, End, PageUp, and PageDown should return to the editor's normal caret commands and continue reporting caret movement.

In a browser, switch NVDA's native Browse Mode on while focus remains associated with the editable control. Markdown shortcuts and `NVDA+shift+space` must not override the virtual document. Switch NVDA back to Focus Mode and verify that the Markdown shortcuts work again when Markdown Browse Mode is enabled.

In an editable HTML or Word document containing a real native table, enable Markdown Browse Mode and place the caret in a native table cell. The table commands must use NVDA's native table navigation and must not announce "Not inside a table". After turning Markdown Browse Mode off outside the native table, the same Ctrl+alt gestures must retain the editor's normal behavior.

| Marker | Column 2 | Column 3 | Column 4 |
| --- | --- | --- | --- |
| CELL-A1 | CELL-A2 | CELL-A3 | CELL-A4 |
| CELL-B1 | CELL-B2 with `inline` | CELL-B3 with **bold** | CELL-B4 |
| CELL-C1 | CELL-C2 with escaped pipe a \| b | CELL-C3 | CELL-C4 |

Text between tables.

TABLE-B begins below.

| Marker | Status | Notes |
| --- | --- | --- |
| CELL-D1 | ready | second table first data row |
| CELL-E1 | done | second table second data row |

TABLE-C covers empty cells, Unicode offsets, and a caret placed after the closing pipe.

| Marker | Empty | Unicode |
| --- | --- | --- |
| CELL-H1 |  | 🧑‍💻 CELL-H3 |
| CELL-I1 | CELL-I2 | CELL-I3 |

From CELL-H1, Ctrl+alt+Right should announce "blank" and another Ctrl+alt+Right should announce the complete Unicode cell. Reading the row should include "blank" between CELL-H1 and the Unicode cell. Press End on this row and then Ctrl+alt+Left; the caret should move to the empty middle cell rather than CELL-H1.

##### H5-A Code

CODE-A fenced code block with language starts below.

```python
def code_block_alpha(value):
	return value + 1

print(code_block_alpha(41))
```

Paragraph after CODE-A. It contains INLINE-CODE-B `inline_code_beta` for inline code navigation.

CODE-B fenced code block without language starts below.

```
plain fenced code block beta
second line in beta block
```

###### H6-A Separators And Math

SEPARATOR-A follows this paragraph.

---

Paragraph after SEPARATOR-A.

SEPARATOR-B follows this paragraph.

***

MATH-B inline math appears here: $x = \frac{-b \pm \sqrt{b^2 - 4ac}}{2a}$.

MATH-C display math on one line follows.

$$E = mc^2$$

# H1-B Second Top Level Heading

This section gives previous-navigation targets near the bottom. LINK-B [Example link](https://example.com/link-b), IMAGE-B ![Example image](https://example.com/image-b.png), BOLD-B __bold text beta__, ITALIC-B _italic text beta_, STRIKE-B ~~deleted text beta~~, FOOTNOTE-B [^beta], and INLINE-CODE-C `inline_code_gamma`.

## H2-B More Lists

LIST-C mixed content starts below.

- ITEM-C1 list item before table and quote tests
- ITEM-C2 list item with CHECKBOX-D marker text but no checkbox syntax
- ITEM-C3 final list item in this block

### H3-B More Blockquotes

> QUOTE-C line 1 final quote block
> QUOTE-C line 2 final quote block

#### H4-B More Tables

| Marker | Left | Right |
| --- | --- | --- |
| CELL-F1 | CELL-F2 | CELL-F3 |
| CELL-G1 | CELL-G2 | CELL-G3 |

##### H5-B More Code

Another inline code marker appears before the final fence: INLINE-CODE-D `inline_code_delta`.

```js
function codeBlockGamma(value) {
	return value * 2;
}
```

###### H6-B Final Heading

Final paragraph for backward navigation. It contains CHECKBOX-E below, final math MATH-D $n(n+1)/2$, and final separator after the checkbox.

- [ ] CHECKBOX-E final unchecked task

___

[^alpha]: Footnote definition alpha.
[^beta]: Footnote definition beta.
