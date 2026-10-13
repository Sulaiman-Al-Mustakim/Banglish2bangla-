#!/usr/bin/env python3
"""
banglish_hotkey.py  --  Banglish -> Bangla by hotkey, in ANY app. 100% offline.
No AI, no internet, no tokens, no floating bar.

Use:
  1. Type Banglish anywhere.
  2. Press the hotkey (default Ctrl+Alt+B).
  3. Selected text -- or the current line if nothing is selected -- becomes Bangla.

How spelling is decided:
  1. words.txt  -- YOUR dictionary. Always wins. Edited any time, no restart.
  2. built-in starter dictionary (common tricky words: kono, tomar, jodi ...).
  3. phonetic rules (Avro-like) make the base spelling.
  4. Frequency ranking (optional but recommended: pip install wordfreq):
     the tool tries sound-alike spellings (ন/ণ, স/শ/ষ, ই/ঈ, উ/ঊ, ো ...) and
     keeps the one that is a real, frequent Bangla word. No AI, fully offline.
     Turn off with  BANGLISH_RANK=0
  Letters you type in CAPITALS are never changed, so you stay in control:  n=ন N=ণ | s=স sh=শ Sh=ষ | t=ত T=ট | d=দ D=ড
     | z=য j=জ | o at word end = ো , O = ো anywhere | A = অ্যা | ^ = ঁ | ng = ং
  Wrong word? Teach it once:
       python banglish_hotkey.py --add "kono=কোনো"
  and it is right forever.

Other tips:
  {English}   text in curly braces stays as typed (braces removed)
  aj,ke       a comma between letters blocks a conjunct (আজকে, not আজ্কে)

Settings (environment variables):
  BANGLISH_HOTKEY   pynput style, default <ctrl>+<alt>+b
  BANGLISH_DICT     path of your dictionary file (default: words.txt next to this file)

Test without hotkeys:  python banglish_hotkey.py --text "ami tomake bhalobasi"
"""

import argparse
import functools
import itertools
import os
import platform
import re
import sys
import threading
import time

HOTKEY = os.environ.get("BANGLISH_HOTKEY", "<ctrl>+<alt>+b")
IS_MAC = platform.system() == "Darwin"
HERE = os.path.dirname(os.path.abspath(__file__))
DICT_PATH = os.environ.get("BANGLISH_DICT", os.path.join(HERE, "words.txt"))

# ----------------------------------------------------------------------------
# Phonetic rules
# ----------------------------------------------------------------------------
HAS = "\u09cd"  # hasanta (্)

CONSONANTS = {
    "kkh": "ক্ষ", "jn": "জ্ঞ", "GG": "জ্ঞ", "ngg": "ঙ্গ", "ngk": "ঙ্ক",
    "kh": "খ", "gh": "ঘ", "Ng": "ঙ", "NG": "ঞ", "chh": "ছ", "ch": "ছ", "jh": "ঝ",
    "Th": "ঠ", "Dh": "ঢ", "th": "থ", "dh": "ধ", "ph": "ফ", "bh": "ভ",
    "sh": "শ", "Sh": "ষ", "Rh": "ঢ়",
    "k": "ক", "g": "গ", "c": "চ", "j": "জ", "T": "ট", "D": "ড", "N": "ণ",
    "t": "ত", "d": "দ", "n": "ন", "p": "প", "f": "ফ", "b": "ব", "v": "ভ",
    "m": "ম", "z": "য", "r": "র", "l": "ল", "S": "শ", "s": "স", "h": "হ",
    "R": "ড়", "q": "ক", "x": "ক্স",
}
# vowel: (independent form, kar form)
VOWELS = {
    "rri": ("ঋ", "ৃ"), "oi": ("ঐ", "ৈ"), "ou": ("ঔ", "ৌ"),
    "ee": ("ঈ", "ী"), "oo": ("ঊ", "ূ"), "aa": ("আ", "া"),
    "a": ("আ", "া"), "i": ("ই", "ি"), "I": ("ঈ", "ী"),
    "u": ("উ", "ু"), "U": ("ঊ", "ূ"), "e": ("এ", "ে"),
    "A": ("অ্যা", "্যা"),
}

TOKENS = {}
for k, v in CONSONANTS.items():
    TOKENS[k] = ("C", v)
for k in VOWELS:
    TOKENS[k] = ("V", k)
TOKENS.update({
    "t`": ("T", "ৎ"), "ng": ("ng", ""), "y": ("y", ""), "Y": ("Y", "য়"),
    "w": ("w", ""), "o": ("o", ""), "O": ("O", ""),
})
TOKEN_KEYS = sorted(TOKENS, key=len, reverse=True)
KEEP_UPPER = set("TDNSRGAIUO")

# Consonant pairs that really form a conjunct (juktakkhor) in Bangla.
# Pairs not listed stay separate, so "ajke" -> আজকে, "bolchi" -> বলছি.
# (র + anything is a reph, and anything + র is a ra-fola; handled separately.)
PAIRS = set("""
কক কত কট কম কষ কল কস কব গগ গধ গন গম গল গব ঘন ঙক ঙখ ঙগ ঙঘ চচ চছ চঞ চব
জজ জঞ জব জঝ ঞচ ঞছ ঞজ ঞঝ টট টব ডড ণট ণঠ ণড ণণ ণম ণব ণঢ তত তথ তন তম তব
থব দদ দধ দব দভ দম দগ দঘ ধন ধম ধব নট নঠ নড নত নথ নদ নধ নন নপ নফ নব নম নস
পট পত পন পপ পল পস ফল বজ বদ বধ বব বল বভ ভল মন মপ মফ মব মভ মম মল লক লগ লট
লড লপ লফ লব লম লল শচ শছ শন শব শম শল ষক ষট ষঠ ষণ ষপ ষফ ষম ষব সক সখ সট সত
সথ সন সপ সফ সম সল সব হন হম হল হব হণ
""".split())


def _can_join(a: str, b: str) -> bool:
    if a == "র":
        return b != "ছ"
    if b == "র":
        return True
    return (a + b) in PAIRS


def _tokenize(w: str):
    toks, i, n = [], 0, len(w)
    while i < n:
        ch = w[i]
        if ch == ",":
            toks.append(("sep", "", ""))
            i += 1
            continue
        if ch == "^":
            toks.append(("chandra", "ঁ", ""))
            i += 1
            continue
        for key in TOKEN_KEYS:
            if w.startswith(key, i):
                kind, val = TOKENS[key]
                tkey = key
                if kind == "ng":  # ng + vowel -> ঙ ; otherwise anusvara ং
                    nxt = w[i + 2] if i + 2 < n else ""
                    kind, val = ("C", "ঙ") if nxt and nxt in "aeiouAIUOE" else ("anu", "ং")
                toks.append((kind, val, tkey))
                i += len(key)
                break
        else:
            toks.append(("other", ch, ""))
            i += 1
    return toks


def _normalize(w: str) -> str:
    # Capital letters that are not special in the scheme become lowercase.
    w = "".join(c if (not c.isupper() or c in KEEP_UPPER) else c.lower() for c in w)
    # "Ami", "Amar" (capital only because it starts a sentence) -> lowercase vowel
    if len(w) > 1 and w[0] in "AIUO" and w[1:] == w[1:].lower():
        w = w[0].lower() + w[1:]
    return w


def _render(toks) -> str:
    n = len(toks)
    out = []
    bare = False       # previous token is a consonant that can still take a kar
    joinable = False   # a following consonant may form a conjunct with it
    conj = False       # current consonant is already inside a conjunct
    last_c = ""        # last consonant letter (for conjunct check)
    fresh = True       # at the start of the word / after a separator
    for i, (kind, val, _key) in enumerate(toks):
        last = i == n - 1
        if kind == "sep":
            bare = joinable = conj = False
            fresh = True
            continue
        if kind == "chandra":
            out.append(val)
            continue
        if kind == "C":
            if joinable and _can_join(last_c, val[0]):
                out.append(HAS)
                conj = True
            else:
                conj = False
            out.append(val)
            bare, joinable, last_c = True, True, val[-1]
        elif kind == "T":
            out.append(val)
            bare = joinable = conj = False
        elif kind == "anu":
            out.append(val)
            bare = joinable = conj = False
        elif kind == "Y":
            out.append(val)
            bare, joinable, conj = True, False, False
        elif kind == "y":
            if joinable:  # ya-fola: shotyo -> সত্য
                out.append(HAS + "য")
                bare, joinable, conj, last_c = True, True, True, "য"
            else:
                out.append("য়")
                bare, joinable, conj = True, False, False
        elif kind == "w":
            if joinable:  # ba-fola: swasthyo -> স্বাস্থ্য
                out.append(HAS + "ব")
                bare, joinable, conj, last_c = True, True, True, "ব"
            else:  # after a vowel / at start: newa -> নেওয়া
                out.append("ওয়")
                bare, joinable, conj = True, False, False
        elif kind == "V":
            ind, kar = VOWELS[val]
            out.append(kar if bare else ind)
            bare = joinable = conj = False
        elif kind == "o":
            if bare:
                if last and not conj:
                    out.append("ো")  # bhalo, koro, dekho
                # otherwise: inherent vowel, nothing to write
            elif fresh:
                out.append("ও" if n == 1 else "অ")
            else:
                out.append("ও")  # after a vowel: kothao, jao
            bare = joinable = conj = False
        elif kind == "O":
            out.append("ো" if bare else "ও")
            bare = joinable = conj = False
        elif kind == "o_inh":  # forced: no ো mark (used by ranking only)
            if not bare:
                out.append("ও" if (n == 1 and fresh) else ("অ" if fresh else "ও"))
            bare = joinable = conj = False
        else:
            out.append(val)
            bare = joinable = conj = False
        fresh = False
    return "".join(out)


# ----------------------------------------------------------------------------
# Frequency ranking (optional, needs: pip install wordfreq)
# ----------------------------------------------------------------------------
RANK = os.environ.get("BANGLISH_RANK", "1") != "0"
# typed key -> sound-alike alternatives
ALTS = {
    "n": [("C", "ণ", "n")],
    "s": [("C", "শ", "s"), ("C", "ষ", "s")],
    "sh": [("C", "স", "sh"), ("C", "ষ", "sh")],
    "ch": [("C", "চ", "ch")],
    "j": [("C", "য", "j")],
    "i": [("V", "I", "i")],
    "u": [("V", "U", "u")],
    "o": [("O", "", "o")],  # a typed final "o" is deliberate, so it is never varied
}
MAX_SLOTS = 6
_zf = None


def _zipf(w: str):
    """Bangla word frequency on a log scale (0 = unknown). None if wordfreq is missing."""
    global _zf
    if _zf is None:
        try:
            from wordfreq import zipf_frequency
            _zf = zipf_frequency
        except ImportError:
            _zf = False
            log("Tip: pip install wordfreq  -> much better spelling (ন/ণ, স/শ/ষ ...)")
    return _zf(w, "bn") if _zf else None


@functools.lru_cache(maxsize=20000)
def rules_word(word: str) -> str:
    toks = _tokenize(_normalize(word))
    base = _render(toks)
    if not RANK:
        return base
    base_z = _zipf(base)
    if base_z is None:
        return base
    slots = [(i, ALTS[t[2]]) for i, t in enumerate(toks)
             if t[2] in ALTS and not (t[2] == "o" and i == len(toks) - 1)][:MAX_SLOTS]
    if not slots:
        return base
    best, best_score = base, base_z
    options = [[None] + alts for _, alts in slots]
    for combo in itertools.product(*options):
        changes = sum(1 for c in combo if c is not None)
        if not changes:
            continue
        t2 = list(toks)
        for (idx, _), c in zip(slots, combo):
            if c is not None:
                t2[idx] = c
        cand = _render(t2)
        z = _zipf(cand) or 0.0
        if z < 1.5:  # unknown / noise word: ignore
            continue
        score = z - 0.2 * changes
        if score > best_score:
            best, best_score = cand, score
    return best


# ----------------------------------------------------------------------------
# Dictionaries
# ----------------------------------------------------------------------------
STARTER = """
kono=কোনো|keno=কেন|chai=চাই|amra=আমরা|chhoto=ছোট|boro=বড়|jawa=যাওয়া|jaoa=যাওয়া|eto=এত|ora=ওরা|oke=ওকে|tomar=তোমার|tomake=তোমাকে|tomader=তোমাদের
tomra=তোমরা|kothay=কোথায়|kothao=কোথাও|jodi=যদি|je=যে|ja=যা|jai=যাই|jabo=যাব|jabe=যাবে
jete=যেতে|jokhon=যখন|jemon=যেমন|jar=যার|jake=যাকে|joto=যত|jekhane=যেখানে|jonno=জন্য
onno=অন্য|dhonnobad=ধন্যবাদ|korte=করতে|korbo=করব|korbe=করবে|korle=করলে|korlam=করলাম
kortam=করতাম|korben=করবেন|bolbo=বলব|bolbe=বলবে|bolte=বলতে|bolle=বললে|bollam=বললাম
hoyto=হয়তো|bhalobasi=ভালোবাসি|bhalobasha=ভালোবাসা|bhasha=ভাষা|shob=সব|shobar=সবার
shokal=সকাল|shundor=সুন্দর|shomoy=সময়|shotti=সত্যি|shomosya=সমস্যা|shathe=সাথে|shei=সেই
shey=সে|she=সে|taka=টাকা|kaj=কাজ|aj=আজ|ajke=আজকে|kal=কাল|bondhu=বন্ধু
""".replace("\n", "|").split("|")

_user_cache = {"mtime": None, "data": {}}


def _load_user_dict() -> dict:
    try:
        mt = os.path.getmtime(DICT_PATH)
    except OSError:
        return {}
    if _user_cache["mtime"] != mt:
        data = {}
        with open(DICT_PATH, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                if k.strip() and v.strip():
                    data[k.strip()] = v.strip()
        _user_cache.update(mtime=mt, data=data)
    return _user_cache["data"]


_starter_dict = {}
for _pair in STARTER:
    if "=" in _pair:
        _k, _v = _pair.split("=", 1)
        _starter_dict[_k.strip()] = _v.strip()


def lookup(word: str):
    for d in (_load_user_dict(), _starter_dict):
        if word in d:
            return d[word]
        if word.lower() in d:
            return d[word.lower()]
    return None


def add_word(spec: str) -> None:
    if "=" not in spec:
        sys.exit('Use: --add "banglish=বাংলা"')
    k, v = (s.strip() for s in spec.split("=", 1))
    new_file = not os.path.exists(DICT_PATH)
    with open(DICT_PATH, "a", encoding="utf-8") as f:
        if new_file:
            f.write("# Your words. Format:  banglish = বাংলা   (one per line)\n")
        f.write(f"{k} = {v}\n")
    print(f"Saved: {k} -> {v}   ({DICT_PATH})")


# ----------------------------------------------------------------------------
# Whole-text conversion
# ----------------------------------------------------------------------------
WORD_RE = re.compile(r"[A-Za-z`^]+(?:,[A-Za-z`^]+)*")


def convert_word(w: str) -> str:
    return lookup(w) or rules_word(w)


def convert(text: str) -> str:
    out = []
    for part in re.split(r"(\{[^{}]*\})", text):
        if len(part) >= 2 and part[0] == "{" and part[-1] == "}":
            out.append(part[1:-1])  # keep as typed
        else:
            out.append(WORD_RE.sub(lambda m: convert_word(m.group(0)), part))
    s = "".join(out)
    return re.sub(r"(?<=[\u0980-\u09FF])\.(?=\s|$)", "।", s)  # sentence-end dot


def log(msg: str) -> None:
    print(time.strftime("[%H:%M:%S] ") + msg, flush=True)


# ----------------------------------------------------------------------------
# Hotkey app
# ----------------------------------------------------------------------------
MOD_NAMES = {
    "ctrl", "ctrl_l", "ctrl_r", "alt", "alt_l", "alt_r", "alt_gr",
    "shift", "shift_l", "shift_r", "cmd", "cmd_l", "cmd_r",
}


class HotkeyApp:
    def __init__(self):
        from pynput import keyboard  # imported late so --text works without it
        import pyperclip

        self.kb = keyboard
        self.clip = pyperclip
        self.ctl = keyboard.Controller()
        self.pressed = set()
        self.lock = threading.Lock()
        self.mod = keyboard.Key.cmd if IS_MAC else keyboard.Key.ctrl

    def _on_press(self, key):
        self.pressed.add(key)

    def _on_release(self, key):
        self.pressed.discard(key)

    def _modifiers_held(self) -> bool:
        return any(getattr(k, "name", None) in MOD_NAMES for k in list(self.pressed))

    def _wait_release(self, timeout=2.0):
        end = time.time() + timeout
        while self._modifiers_held() and time.time() < end:
            time.sleep(0.02)

    def _chord(self, *keys):
        for k in keys:
            self.ctl.press(k)
        for k in reversed(keys):
            self.ctl.release(k)

    def _get_clip(self):
        try:
            return self.clip.paste()
        except Exception:  # noqa: BLE001
            return None

    def _set_clip(self, value):
        try:
            self.clip.copy(value if value is not None else "")
        except Exception:  # noqa: BLE001
            pass

    def _copy_selection(self, sentinel: str):
        self._set_clip(sentinel)
        self._chord(self.mod, "c")
        time.sleep(0.15)
        return self._get_clip()

    def _select_line(self):
        K = self.kb.Key
        if IS_MAC:
            self._chord(K.cmd, K.shift, K.left)
        else:
            self._chord(K.shift, K.home)
        time.sleep(0.05)

    def on_hotkey(self):
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        if not self.lock.acquire(blocking=False):
            return
        try:
            self._wait_release()
            old = self._get_clip()
            sentinel = "\u200b__banglish_wait__\u200b"

            text = self._copy_selection(sentinel)
            if text == sentinel:  # nothing selected -> take the current line
                self._select_line()
                text = self._copy_selection(sentinel)
            if text == sentinel or not (text or "").strip():
                log("Nothing to convert")
                self._set_clip(old)
                return

            result = convert(text)
            self._set_clip(result)
            time.sleep(0.05)
            self._chord(self.mod, "v")
            time.sleep(0.3)
            self._set_clip(old)  # give the user's old clipboard back
            log(f"{text.strip()[:40]!r} -> {result.strip()[:40]!r}")
        except Exception as e:  # noqa: BLE001
            log(f"Error: {e}")
        finally:
            self.lock.release()

    def run(self):
        log(f"Ready (offline). Hotkey: {HOTKEY}   Dictionary: {DICT_PATH}")
        log("Type Banglish, then press the hotkey. Press Ctrl+C in this window to quit.")
        if RANK:
            threading.Thread(target=lambda: _zipf("আমি"), daemon=True).start()  # warm up
        tracker = self.kb.Listener(on_press=self._on_press, on_release=self._on_release)
        tracker.start()
        with self.kb.GlobalHotKeys({HOTKEY: self.on_hotkey}) as hk:
            try:
                hk.join()
            except KeyboardInterrupt:
                pass
        tracker.stop()


def main():
    ap = argparse.ArgumentParser(description="Banglish -> Bangla by hotkey (offline)")
    ap.add_argument("--text", help="convert this text once and exit")
    ap.add_argument("--add", help='teach a word: --add "kono=কোনো"')
    args = ap.parse_args()

    if args.add is not None:
        return add_word(args.add)
    if args.text is not None:
        print(convert(args.text))
        return
    try:
        HotkeyApp().run()
    except ImportError as e:
        sys.exit(f"Missing package: {e}. Run: pip install -r requirements.txt")


if __name__ == "__main__":
    main()
