import bz2
import curses
from itertools import accumulate, groupby
from math import e, log
from random import choices, random
from statistics import median
from string import ascii_letters as letters
from time import perf_counter as t

WIDTH = 51
BACKSPACE = "KEY_BACKSPACE"
CTRL_BACKSPACE = "\x08"


def freq(rank):
    x = log(rank + 1)
    return 97763743070 * e ** (-0.66280297 * x - 0.04881087 * x**2)


with bz2.open("words.bz2", "rt") as fp:
    word_list = list(map(str.strip, fp.readlines()))
length_weights = list(accumulate(map(lambda L: 1.1 * L * 0.90**L, range(1, 31))))
word_weights = list(accumulate(map(freq, range(len(word_list)))))


def maketext(n):
    words = [
        x[0] + ("," if random() < 0.0884 else "")
        for x in groupby(choices(word_list, cum_weights=word_weights, k=int(n * 1.5)))
    ][:n]
    assert len(words) == n
    words[0] = words[0].capitalize()
    c = 0
    for sl in choices(range(1, 31), cum_weights=length_weights, k=n):
        c += sl
        if c >= n:
            break
        if words[c][-1] == ",":
            words[c] = words[c]
        words[c] = (words[c][:-1] if words[c][-1] == "," else words[c]) + "."
        if c + 1 < n:
            words[c + 1] = words[c + 1].capitalize()
    else:
        raise Exception
    return " ".join(words)


texts = [maketext(50) for _ in range(201)]
text = sorted(texts, key=len)[100]


def draw(window, start, typed, c, tot):
    elapsed = t() - start if start else 0
    wpm = 12 * (c - 1) / elapsed if start and c > 1 else 0
    acc = c / tot if tot != 0 else 1
    stats = f"wpm: {wpm:.2f}, acc: {100*acc:.2f}%".center(WIDTH - 2)
    window.addstr(0, 3, stats, curses.color_pair(5 if acc > 0.97 else 2))
    window.move(1, 1)
    window.clrtoeol()

    colors = [3 if c == u else 2 for c, u in zip(text, typed)] + [9] * WIDTH
    for i, (char, color) in enumerate(zip(text, colors)):
        pos = WIDTH // 2 + i + 1 - len(typed)
        if pos <= 0:
            continue
        if pos > WIDTH:
            break
        char = "_" if color == 2 and char == " " else char
        window.addstr(1, pos, char, curses.color_pair(color))
    window.move(1, WIDTH // 2 + 1)
    window.refresh()


def process_times(times):
    assert len(times) + 1 == len(text.split())
    word_stats = {}
    for word, time in zip(text.split()[1:], times):
        word = word.replace(",", "").replace(".", "")
        if word[0].isupper():
            continue
        word_stats[word] = word_stats[word] + [time] if word in word_stats else [time]

    averages = {k: len(k) * len(v) / sum(v) for k, v in word_stats.items()}
    med = median(averages.values())

    relocations = {}
    for word, cps in sorted(averages.items(), key=lambda x: x[1]):
        old = word_list.index(word) + 1
        new = old * cps / med
        rounded = max(1, round(new))
        print(f"{12 * cps:6.2f} {word:18} {old:6} -> {rounded:6}")
        if old != rounded:
            relocations[word] = new
    for word in relocations:
        word_list.remove(word)
    for word, index in sorted(relocations.items(), key=lambda x: x[1]):
        word_list.insert(max(0, round(index - 1)), word)

    with bz2.open("words.bz2", "wt", compresslevel=9) as f:
        f.write("\n".join(word_list))


def init(screen):
    screen.refresh()
    curses.use_default_colors()
    for i in range(curses.COLORS):
        curses.init_pair(i + 1, i, -1)
    maxy, maxx = screen.getmaxyx()
    window = curses.newwin(3, WIDTH + 2, maxy // 2 - 1, (maxx - WIDTH) // 2 - 1)
    window.box(1, 1)
    return window


def main(screen):
    correct = 0
    top = 0
    total = 0
    typed = ""
    start = None
    word_time = None
    word_times = []
    window = init(screen)

    while True:
        draw(window, start, typed, correct, total)
        char = screen.getkey()
        start = t() if start is None else start

        if char == BACKSPACE:
            typed = typed[:-1] if typed else ""
        elif char == CTRL_BACKSPACE:
            typed = typed[:-1] if typed and typed[-1] == " " else typed
            typed = typed[: len(typed) - typed[::-1].index(" ")] if " " in typed else ""
        elif len(char) == 1:
            typed += char
            total += 1
            correct += len(typed) <= len(text) and char == text[len(typed) - 1]
            if len(text) >= len(typed) > top and text[: len(typed)] == typed:
                top = len(typed)
                if word_time and (text == typed or text[len(typed)] not in letters):
                    # word ended
                    word_times.append(t() - word_time)
                    word_time = None
                elif typed[-1] == " " and text[len(typed)] in letters:
                    # word began
                    word_time = t()

        if typed == text:
            break
    return start, correct, total, word_times


start_time, correct_chars, total_chars, time_list = curses.wrapper(main)
final_time = t() - start_time
final_wpm = 12 * len(text[:-1]) / final_time
final_acc = 100 * correct_chars / total_chars
process_times(time_list)
print(f"time: {final_time:.2f}s, acc: {final_acc:.2f}%, wpm: {final_wpm:.2f}")
if final_acc < 97:
    print("please slow down on difficult words to improve your accuracy and speed")
