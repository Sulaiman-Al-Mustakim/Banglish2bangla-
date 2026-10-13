# banglish-hotkey

**Type Banglish anywhere. Press a hotkey. Get Bangla.**

A tiny, offline Banglish → Bangla converter for your desktop. No floating toolbar, no always-on keyboard layout, no AI model, no API key, no internet.

```text
ami tomake bhalobasi.      →  আমি তোমাকে ভালোবাসি।
ajke kaj kori              →  আজকে কাজ করি
bishesh kore tomar jonno   →  বিশেষ করে তোমার জন্য
ami {Chokro AI} niye kaj   →  আমি Chokro AI নিয়ে কাজ
```

## Why

Phonetic keyboards sit on top of your screen, switch your whole system into "Bangla mode", and still guess wrong on ন/ণ, স/শ/ষ and ই/ঈ. This tool does one thing instead: you write normally, then convert a word, a selection or a line **only when you ask**.

## Features

- **Works in any app** (browser, Word, VS Code, chat apps). It copies the selection, converts it and pastes the result back.
- **Nothing selected? It converts the current line.**
- **Your clipboard is restored** afterwards.
- **Spelling by frequency, not by guessing.** It tries sound-alike spellings (ন/ণ, স/শ/ষ, ই/ঈ, উ/ঊ, ো) and keeps the one that is a real, common Bangla word.
- **Your own dictionary** (`words.txt`) always wins, and reloads instantly.
- **Full control with capitals.** Anything you type in CAPITAL letters is never changed.
- **Leave English alone** with `{curly braces}`.
- Windows first. The code also runs on macOS and Linux (X11).

## Install

Requires Python 3.9+.

```bash
git clone <https://github.com/Sulaiman-Al-Mustakim/Banglish2bangla-l>
cd banglish-hotkey
pip install -r requirements.txt
python banglish_hotkey.py
```

On Windows you can also double-click `start_banglish.bat` to run it silently in the background.

## Use

1. Type Banglish anywhere.
2. Press **Ctrl+Alt+B**.
3. The selection (or current line) becomes Bangla.

Test without hotkeys:

```bash
python banglish_hotkey.py --text "ami tomake bhalobasi"
```

## Typing guide

| You type | You get | | You type | You get |
|---|---|---|---|---|
| `n` / `N` | ন / ণ | | `t` / `T` | ত / ট |
| `s` / `sh` / `Sh` | স / শ / ষ | | `d` / `D` | দ / ড |
| `z` | য | | `j` | জ |
| `ng` | ং | | `^` | ঁ |
| `O` | ো | | `A` | অ্যা |
| `{text}` | text (as typed) | | `aj,ke` | আজকে (comma blocks a conjunct) |

Conjuncts (যুক্তাক্ষর) form only for real Bangla pairs. For example `bondhu` → বন্ধু, but `ajke` → আজকে and `bolchi` → বলছি.

## How a word is converted

1. **`words.txt`** (your dictionary) wins.
2. **Built-in starter dictionary** covers tricky common words (`kono`, `tomar`, `jodi` ...).
3. **Phonetic rules** produce the base spelling.
4. **Frequency ranking** (needs `wordfreq`, installed by `requirements.txt`) tests sound-alike variants and keeps the most frequent real word. A typed capital letter or a typed final `o` is never varied.

A wrong word? Teach it once:

```bash
python banglish_hotkey.py --add "kono=কোনো"
```

or edit `words.txt` by hand (`banglish = বাংলা`, one per line, no restart needed).

## Configuration

| Environment variable | Default | Meaning |
|---|---|---|
| `BANGLISH_HOTKEY` | `<ctrl>+<alt>+b` | Hotkey in `pynput` format |
| `BANGLISH_DICT` | `words.txt` next to the script | Path of your dictionary |
| `BANGLISH_RANK` | `1` | Set `0` to turn frequency ranking off |

## Known limits

- Without understanding meaning, some words stay ambiguous (`kono` কোন/কোনো, `bolo` বল/বলো). Add them to `words.txt` once and they stay fixed.
- Names are often not in any word list. Use capitals (`Dhaka` → ঢাকা, `dhaka` → ধাকা).
- Programs running as Administrator ignore simulated keys from a normal process. Run the tool as Administrator too.
- macOS: allow your terminal under *System Settings → Privacy & Security → Accessibility*.
- Linux: X11 only. Wayland usually blocks global hotkeys.

## Status

The conversion engine is tested. The hotkey, copy and paste layer is simple but has not yet been tested on every OS, so please open an issue if it misbehaves on your machine.

## Roadmap

- Press the hotkey again to cycle through alternative spellings
- Auto-learn corrections into `words.txt`
- Bigger built-in dictionary
- Optional pluggable local language model

## Credits and licenses

- Word frequencies come from [`wordfreq`](https://pypi.org/project/wordfreq/), installed separately from PyPI and **not bundled** here. See its own license.
- Typing scheme inspired by Avro Phonetic.
- Add a `LICENSE` file of your choice before publishing.

---

## বাংলায় সংক্ষেপে

1. Python ইনস্টল করুন (ইনস্টলের সময় **Add python.exe to PATH**-এ টিক দিন)।
2. ফোল্ডারে `cmd` খুলে লিখুন: `pip install -r requirements.txt`
3. চালান: `python banglish_hotkey.py`
4. যেকোনো জায়গায় Banglish লিখে **Ctrl+Alt+B** চাপুন।
5. ভুল শব্দ শেখাতে: `python banglish_hotkey.py --add "kono=কোনো"`
