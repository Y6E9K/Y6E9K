import os
from collections import Counter, defaultdict
from .tr_utils import tr_upper

ALLOWED_EXTS = {".list", ".txt"}


def load_dictionary_folder(folder_path: str):
    words = set()
    file_count = 0
    for name in sorted(os.listdir(folder_path)):
        ext = os.path.splitext(name)[1].lower()
        if ext not in ALLOWED_EXTS:
            continue
        full = os.path.join(folder_path, name)
        if not os.path.isfile(full):
            continue
        file_count += 1
        with open(full, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                w = tr_upper(line.strip())
                if len(w) >= 2:
                    words.add(w)

    words = sorted(words)
    by_length = defaultdict(list)
    for w in words:
        by_length[len(w)].append({"word": w, "len": len(w), "count": Counter(w), "uniq": set(w)})
    return words, by_length, {"file_count": file_count, "word_count": len(words)}
