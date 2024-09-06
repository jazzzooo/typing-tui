# typing-tui
A terminal based typing test and trainer.
Inspired by [Problem Words](https://problemwords.com/) and [fasttyper](https://github.com/ickyicky/fasttyper).
The text you type starts out with the normal english distribution of words.
Over time words you type slowly get reranked to be more common, whereas words you type quickly become less common.
To see your highest ranked words, run `bzip2 -kdc words.bz2 | head`.

![Recording](./demo.gif)

## Goals
- Stay under 250 lines of code
- Be easy to modify and extend
- Have no external dependencies

## Non-Goals
- Support MacOS, Windows and other non-standard terminals
- Themes, other languages, maintaining a proper english wordlist
- GUI

If you add a feature that some might find useful, send me a patch and I might add it to the README.

This runs on st and alacritty, if your terminal is weird you'll need to modify the code to work with it.
