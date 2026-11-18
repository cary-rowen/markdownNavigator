# NVDA Markdown Navigator

Markdown Navigator is an NVDA add-on designed to enhance the experience of editing and reading Markdown content. It allows you to use single-key navigation features, similar to NVDA's Browse Mode, within editable text areas (such as Notepad, VS Code, web-based editors, etc.).

It enables you to quickly jump to headings, lists, tables, code blocks, and various inline formatting without frequently pressing the arrow keys.

## Key Features

*   **Efficient Navigation**: Implements fast algorithms that allow for instant jumping even in large documents with tens of thousands of lines.
*   **Structured Browsing**: Supports navigation by headings, lists, tables, blockquotes, code blocks, and more.
*   **Inline Elements**: Supports jumping to bold, italic, links, images, and inline code.
*   **Table Cell Navigation**: Provides shortcuts consistent with NVDA for moving between cells in Markdown tables.

## Usage

### Toggle Browse Mode
By default, single-key navigation is disabled. You need to manually enable Markdown Browse Mode.

*   **Shortcut**: `NVDA + Shift + Space` (Spacebar)
*   **Effect**: Turns the add-on's functionality on or off. NVDA will announce "Markdown Browse Mode On/Off". This feature also follows NVDA's "Audio indications for focus and browse modes" setting in the Browse Mode settings.

### Shortcut List (When Browse Mode is Enabled)

Once the mode is enabled, you can use the following single-letter keys.
*   Press the **Letter Key** to jump to the next element.
*   Press **Shift + Letter Key** to jump to the previous element.

| Key | Element Type | Description |
| :--- | :--- | :--- |
| **H** | Heading | Any level heading (`#` to `######`) |
| **1-6** | Heading 1-6 | Specific heading level |
| **T** | Table | Start of a table |
| **L** | List | Start of a list block, including nested lists |
| **I** | List Item | Specific list item (`-`, `*`, `1.`) |
| **Q** | Blockquote | Quote block (`>`) |
| **C** | Code | Code block (```` ``` ````) or inline code (`` ` ``) |
| **S** | Separator | Horizontal rule (`---`, `***`) |
| **X** | Checkbox | Task list item (`- [ ]`, `- [x]`) |
| **K** | Link | Markdown link `[text](url)` |
| **Space / Enter / Numpad Enter** | Activate link | Follow an internal anchor or open an external URL |
| **NVDA+K** | Link destination | Report the destination URL of the Markdown link at the caret. Press twice to show the URL in a reviewable window |
| **G** | Graphic | Image tag `![alt](url)` |
| **B** | Bold | Bold text (`**` or `__`) |
| **E** | Emphasis | Italic/Emphasis text (`*` or `_`) |
| **D** | Delete | Strikethrough text (`~~`) |
| **F** | Footnote | Footnote reference `[^1]` |
| **,** | After Block | Jump to the first line after the current list, table, or blockquote |
| **Shift+,**| Start of Block | Jump to the start of the current block element |
| **M** | Math | LaTeX math expression (`$...$` or `$$...$$`) |

For nested lists, **,** and **Shift+,** use the current item's indentation to find the end or start of its list. Exiting a sublist lands on the next parent-level item (or the first line after the list). If the block reaches the end of the document, **,** moves to the end of the text. Both commands also work on plain text that continues a list item's paragraph, even without indentation. A blank line ends the recognized list block.

### Table Cell Navigation

When the cursor is inside a Markdown table and Browse Mode is enabled, you can use the following shortcuts to move between cells:

*   **Ctrl + Alt + Left Arrow**: Previous cell
*   **Ctrl + Alt + Right Arrow**: Next cell
*   **Ctrl + Alt + Up Arrow**: Cell above
*   **Ctrl + Alt + Down Arrow**: Cell below
*   **Ctrl + Alt + Home**: First cell in the row
*   **Ctrl + Alt + End**: Last cell in the row
*   **Ctrl + Alt + Page Up**: First cell in the column
*   **Ctrl + Alt + Page Down**: Last cell in the column
*   **NVDA + Ctrl + Alt + Left Arrow**: Read the current row without moving the caret
*   **NVDA + Ctrl + Alt + Up Arrow**: Read the current column without moving the caret
*   **NVDA + Ctrl + Alt + Right Arrow**: Read from the current cell to the end of the row
*   **NVDA + Ctrl + Alt + Down Arrow**: Read from the current cell to the end of the column

## Notes

*   This add-on is specifically developed for Markdown editing scenarios. If you are reading an HTML page rendered by a browser, please use NVDA's built-in Browse Mode.
*   NVDA's active Browse Mode and native HTML or Word table navigation take priority over Markdown navigation.
*   If pressing the keys above types characters instead of navigating, please check if you have enabled Browse Mode by pressing `NVDA + Shift + Space`.
*   In VS Code, due to the editor rendering content on demand (virtualization), this add-on's browse mode may not work as expected for content that is not currently visible/rendered.

## Development

Run `uv sync` to install the build, translation, and lint tools. Python package discovery is limited to `addon` so template documentation does not interfere with dependency setup. Run `uv run prek run --all-files` for local checks and `uv run scons` to build (gettext is required). Build CI skips strict Pyright checking until the add-on is ready for it.

For pushes to `main` or `master`, CI automatically commits fixes made by the existing checks after rerunning the checks and unit tests successfully, then builds the corrected files. The bot commit does not trigger another CI run. Pull requests and tag builds remain check-only; errors that cannot be fixed automatically still fail CI. Pull the latest changes before continuing local work if CI adds a formatting commit.

Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
