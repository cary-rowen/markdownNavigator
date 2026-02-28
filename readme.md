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
| **L** | List | Start of a list block |
| **I** | List Item | Specific list item (`-`, `*`, `1.`) |
| **Q** | Blockquote | Quote block (`>`) |
| **C** | Code | Code block (```` ``` ````) or inline code (`` ` ``) |
| **S** | Separator | Horizontal rule (`---`, `***`) |
| **X** | Checkbox | Task list item (`- [ ]`, `- [x]`) |
| **K** | Link | Markdown link `[text](url)` |
| **G** | Graphic | Image tag `![alt](url)` |
| **B** | Bold | Bold text (`**` or `__`) |
| **E** | Emphasis | Italic/Emphasis text (`*` or `_`) |
| **D** | Delete | Strikethrough text (`~~`) |
| **F** | Footnote | Footnote reference `[^1]` |
| **,** | End of Block | Jump to the end of the current block element |
| **Shift+,**| Start of Block | Jump to the start of the current block element |
| **M** | Math | LaTeX math expression (`$...$` or `$$...$$`) |

### Table Cell Navigation

When the cursor is inside a Markdown table and Browse Mode is enabled, you can use the following shortcuts to move between cells:

*   **Ctrl + Alt + Left Arrow**: Previous cell
*   **Ctrl + Alt + Right Arrow**: Next cell
*   **Ctrl + Alt + Up Arrow**: Cell above
*   **Ctrl + Alt + Down Arrow**: Cell below

## Notes

*   This add-on is specifically developed for Markdown editing scenarios. If you are reading an HTML page rendered by a browser, please use NVDA's built-in Browse Mode.
*   If pressing the keys above types characters instead of navigating, please check if you have enabled Browse Mode by pressing `NVDA + Shift + Space`.
*   In VS Code, due to the editor rendering content on demand (virtualization), this add-on's browse mode may not work as expected for content that is not currently visible/rendered.

Copyright (C) 2026 Cary-rowen <manchen_0528@outlook.com>
