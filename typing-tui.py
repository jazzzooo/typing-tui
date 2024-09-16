import bz2
import curses
import operator
from datetime import datetime
from itertools import accumulate, groupby
from math import e, log
from random import choices, random
from statistics import median
from string import ascii_letters as letters
from time import perf_counter as t
from time import sleep, time

TEST_LENGTH = 270
WIDTH = 51
BACKSPACE = "KEY_BACKSPACE"
CTRL_BACKSPACE = "\x08"
VERBOSE = False


def freq(rank):
    x = log(rank + 1)
    return 97763743070 * e ** (-0.66280297 * x - 0.04881087 * x**2)


with bz2.open("words.bz2", "rt") as fp:
    word_list = list(map(str.strip, fp.readlines()))
length_weights = list(accumulate(1.1 * L * 0.90**L for L in range(1, 31)))
word_weights = list(accumulate(map(freq, range(len(word_list)))))


def maketext(n):
    words = [
        word + ("," if random() < 0.0884 else "")
        for word, _ in groupby(choices(word_list, cum_weights=word_weights, k=int(n * 1.5)))
    ][:n]
    assert len(words) == n
    words[0] = words[0].capitalize()
    c = 0
    for sl in choices(range(1, 31), cum_weights=length_weights, k=n):
        c += sl
        if c >= n:
            break
        words[c] = words[c].rstrip(",") + "."
        if c + 1 < n:
            words[c + 1] = words[c + 1].capitalize()
    else:
        msg = "word generation failed, unlucky, try again"
        raise RuntimeError(msg)
    return " ".join(words)


text = maketext(100)
assert len(text) >= TEST_LENGTH


def score(acc, wpm):
    return round(acc**2.5 * wpm * 1000)


def draw(window, start, typed, c, tot):
    elapsed = t() - start if start else 0
    wpm = 12 * (c - 1) / elapsed if start and c > 1 else 0
    acc = c / tot if tot != 0 else 1
    stats = f"{score(acc, wpm)}".center(WIDTH - 2)
    acc_color = 5 if acc > 0.98 else (4 if acc > 0.97 else 2)
    window.addstr(0, 3, stats, curses.color_pair(acc_color))
    window.move(1, 1)
    window.clrtoeol()

    colors = [3 if c == u else 2 for c, u in zip(text, typed)] + [9] * WIDTH
    for i, (char, color) in enumerate(zip(text, colors)):
        pos = WIDTH // 2 + i + 1 - len(typed)
        if pos <= 0:
            continue
        if pos > WIDTH:
            break
        ch = "_" if color == 2 and char == " " else char
        window.addstr(1, pos, ch, curses.color_pair(color))
    window.move(1, WIDTH // 2 + 1)
    window.refresh()


def process_times(times):
    word_stats = {}
    for punctuated_word, duration in zip(text.split()[1:], times):
        word = punctuated_word.replace(",", "").replace(".", "")
        if word[0].islower():
            word_stats.setdefault(word, []).append(duration)

    averages = {k: len(k) * len(v) / sum(v) for k, v in word_stats.items()}
    test_median = median(averages.values())

    relocations = {}
    for word, cps in sorted(averages.items(), key=operator.itemgetter(1)):
        old = word_list.index(word) + 1
        new = old * cps / test_median
        rounded = max(1, round(new))
        if VERBOSE or rounded < 100:
            print(f"{12 * cps:6.2f} {word:18} {old:6} -> {rounded:6}")
        if old != rounded:
            relocations[word] = new
    for word in relocations:
        word_list.remove(word)
    for word, index in sorted(relocations.items(), key=operator.itemgetter(1)):
        word_list.insert(max(0, round(index - 1)), word)

    with bz2.open("words.bz2", "wt", compresslevel=9) as f:
        f.write("\n".join(word_list))


def leaderboard(timestamp):
    with open("log") as logfile:
        log = [list(map(float, line.split(","))) for line in logfile]
    top = sorted(log, key=lambda line: score(line[1] / 100, line[2]), reverse=True)[:20]
    for line in top:
        current = int(line[3]) == timestamp
        points = score(line[1] / 100, line[2])
        print(f"{points:6} {datetime.fromtimestamp(line[3])}{'<-' * current}")


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
            correct += len(typed) <= TEST_LENGTH and typed == text[: len(typed)]
            if TEST_LENGTH >= len(typed) > top and text[: len(typed)] == typed:
                top = len(typed)
                if word_time and (text == typed or text[len(typed)] not in letters):
                    # word ended
                    word_times.append(t() - word_time)
                    word_time = None
                elif typed[-1] == " " and text[len(typed)] in letters:
                    # word began
                    word_time = t()

        if typed == text[:TEST_LENGTH]:
            break
    return start, correct, total, word_times


start_time, correct_chars, total_chars, time_list = curses.wrapper(main)
sleep(0.6)
print("   wpm word             old rank  new rank")
process_times(time_list)
print("-" * 42)

final_time = t() - start_time
final_wpm = 12 * (TEST_LENGTH - 1) / final_time
final_acc = correct_chars / total_chars
print(f"score: {score(final_acc, final_wpm)}")
print(f"time: {final_time:.2f}s, acc: {final_acc:.2%}, wpm: {final_wpm:.2f}")
print("-" * 42)

timestamp = int(time())
with open("log", "a") as f:
    f.write(f"{final_time},{final_acc * 100},{final_wpm},{timestamp}\n")
leaderboard(timestamp)
