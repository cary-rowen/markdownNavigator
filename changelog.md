### 1.0.0

- Added extended Markdown table navigation for the first and last rows and columns.
- Added row and column reading commands, including reading from the current cell to the end of an axis.
- Reused NVDA text navigation APIs so native table and editor behavior remains available.
- Added a public integration hook for Easy Table Navigator in Markdown tables. (Once Easy Table Navigator PR #23 is merged, its arrow-key and edge-navigation commands will work with Markdown Navigator tables.)
- Fixed list navigation across continuation paragraphs, nested lists, list boundaries, and documents without a trailing newline.
- Added Markdown link activation with Space, Enter, and Numpad Enter, including internal anchor jumps and external URL opening.
- Added NVDA+K support for reporting the destination of the Markdown link at the caret.
- Added support for opening existing absolute local Markdown link targets.
