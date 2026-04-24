from __future__ import annotations

import copy
import heapq
import json
import time
from collections import Counter, OrderedDict, defaultdict
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple


DIR_RIGHT = "YATAY"
DIR_DOWN = "DIKEY"

TR_MAP = {
    "i": "İ",
    "ı": "I",
    "ş": "Ş",
    "ğ": "Ğ",
    "ü": "Ü",
    "ö": "Ö",
    "ç": "Ç",
}

LETTER_SCORES = {
    "A": 1, "B": 3, "C": 4, "Ç": 4, "D": 3, "E": 1, "F": 7, "G": 5, "Ğ": 8,
    "H": 5, "I": 2, "İ": 1, "J": 10, "K": 1, "L": 1, "M": 2, "N": 1, "O": 2,
    "Ö": 7, "P": 5, "R": 1, "S": 2, "Ş": 4, "T": 1, "U": 2, "Ü": 3, "V": 7,
    "Y": 3, "Z": 4, "?": 0,
}

LETTERS = tuple(ch for ch in LETTER_SCORES.keys() if ch != "?")
LETTER_INDEX = {ch: i for i, ch in enumerate(LETTERS)}
INDEX_LETTER = {i: ch for ch, i in LETTER_INDEX.items()}
ALL_LETTER_SET = frozenset(LETTERS)

SOLVE_CACHE_MAX = 64
SOLVE_CACHE: "OrderedDict[str, dict]" = OrderedDict()
CACHE_HITS = 0
CACHE_MISSES = 0


def cache_stats():
    return {
        "size": len(SOLVE_CACHE),
        "maxSize": SOLVE_CACHE_MAX,
        "hits": CACHE_HITS,
        "misses": CACHE_MISSES,
    }


def normalize_letter(ch: Any) -> str:
    if not ch:
        return ""
    ch = str(ch).strip()[:1]
    if ch in TR_MAP:
        return TR_MAP[ch]
    return ch.upper().replace("İ", "İ")


def normalize_word(word: Any) -> str:
    return "".join(normalize_letter(ch) for ch in str(word) if str(ch).strip())


def is_valid_word(word: str) -> bool:
    return len(word) >= 2 and all(ch in LETTER_SCORES and ch != "?" for ch in word)


def count_array_from_word(word: str) -> Tuple[int, ...]:
    arr = [0] * len(LETTERS)
    for ch in word:
        idx = LETTER_INDEX.get(ch)
        if idx is not None:
            arr[idx] += 1
    return tuple(arr)


@dataclass(frozen=True)
class WordEntry:
    word: str
    uniq: frozenset
    count_array: Tuple[int, ...]
    score: int
    length: int


@dataclass
class DictionaryIndex:
    word_set: Set[str]
    words: List[str]
    by_length: Dict[int, List[WordEntry]]
    by_pos_letter: Dict[Tuple[int, int, str], List[WordEntry]]
    pattern_cache: Dict[Tuple[int, Tuple[Tuple[int, str], ...]], List[WordEntry]] = field(default_factory=dict)
    sample_words: List[str] = field(default_factory=list)


def build_dictionary_index(words: Iterable[str]) -> DictionaryIndex:
    word_set: Set[str] = set()
    clean_words: List[str] = []
    by_length: Dict[int, List[WordEntry]] = defaultdict(list)
    by_pos_letter: Dict[Tuple[int, int, str], List[WordEntry]] = defaultdict(list)

    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word) or word in word_set:
            continue

        word_set.add(word)
        clean_words.append(word)

        entry = WordEntry(
            word=word,
            uniq=frozenset(word),
            count_array=count_array_from_word(word),
            score=sum(LETTER_SCORES.get(ch, 0) for ch in word),
            length=len(word),
        )

        by_length[len(word)].append(entry)

        for pos, ch in enumerate(word):
            by_pos_letter[(len(word), pos, ch)].append(entry)

    clean_words.sort()

    for length in by_length:
        by_length[length].sort(key=lambda e: (-e.score, -e.length, e.word))

    for key in by_pos_letter:
        by_pos_letter[key].sort(key=lambda e: (-e.score, -e.length, e.word))

    return DictionaryIndex(
        word_set=word_set,
        words=clean_words,
        by_length=dict(by_length),
        by_pos_letter=dict(by_pos_letter),
        sample_words=clean_words[:50],
    )


def board_size(board: List[List[Any]]) -> int:
    return len(board)


def in_bounds(ctx, r: int, c: int) -> bool:
    return 0 <= r < ctx["n"] and 0 <= c < ctx["n"]


def get_board_cell_letter(cell: Any) -> Optional[str]:
    if isinstance(cell, dict):
        ch = normalize_letter(cell.get("letter", ""))
    else:
        ch = normalize_letter(cell)
    return ch or None


def get_board_cell_bonus(cell: Any) -> Optional[str]:
    if isinstance(cell, dict):
        return cell.get("bonus")
    return None


def build_board_context(board: List[List[Any]], word_set: Set[str]):
    n = board_size(board)
    letters = [[None for _ in range(n)] for _ in range(n)]
    bonuses = [[None for _ in range(n)] for _ in range(n)]
    board_set = set()
    tiles = []

    for r in range(n):
        for c in range(n):
            cell = board[r][c]
            ch = get_board_cell_letter(cell)
            bonus = get_board_cell_bonus(cell)
            letters[r][c] = ch
            bonuses[r][c] = bonus

            if ch:
                board_set.add(ch)
                tiles.append((r, c, ch))

    empty = len(tiles) == 0
    center = (n // 2, n // 2)

    ctx = {
        "n": n,
        "letters": letters,
        "bonuses": bonuses,
        "board_set": board_set,
        "tiles": tiles,
        "empty": empty,
        "center": center,
        "word_set": word_set,
    }

    ctx["anchors"] = compute_anchors(ctx)
    ctx["neighbor_counts"] = compute_neighbor_counts(ctx)
    ctx["cross_checks"] = compute_cross_checks(ctx, word_set)
    return ctx


def ctx_letter(ctx, r: int, c: int) -> Optional[str]:
    if not in_bounds(ctx, r, c):
        return None
    return ctx["letters"][r][c]


def ctx_bonus(ctx, r: int, c: int) -> Optional[str]:
    if not in_bounds(ctx, r, c):
        return None
    return ctx["bonuses"][r][c]


def compute_anchors(ctx) -> Set[Tuple[int, int]]:
    n = ctx["n"]

    if ctx["empty"]:
        return {ctx["center"]}

    anchors = set()

    for r, c, _ in ctx["tiles"]:
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            rr, cc = r + dr, c + dc
            if in_bounds(ctx, rr, cc) and ctx_letter(ctx, rr, cc) is None:
                anchors.add((rr, cc))

    return anchors


def compute_neighbor_counts(ctx):
    n = ctx["n"]
    out = [[0 for _ in range(n)] for _ in range(n)]

    for r in range(n):
        for c in range(n):
            cnt = 0
            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                rr, cc = r + dr, c + dc
                if in_bounds(ctx, rr, cc) and ctx_letter(ctx, rr, cc):
                    cnt += 1
            out[r][c] = cnt

    return out


def neighbor_count(ctx, r: int, c: int) -> int:
    return ctx["neighbor_counts"][r][c]


def step(direction: str) -> Tuple[int, int]:
    return (0, 1) if direction == DIR_RIGHT else (1, 0)


def cell_at(direction: str, r: int, c: int, i: int) -> Tuple[int, int]:
    dr, dc = step(direction)
    return r + dr * i, c + dc * i


def line_in_bounds(ctx, r: int, c: int, direction: str, length: int) -> bool:
    er, ec = cell_at(direction, r, c, length - 1)
    return in_bounds(ctx, r, c) and in_bounds(ctx, er, ec)


def edge_ok(ctx, r: int, c: int, direction: str, length: int) -> bool:
    dr, dc = step(direction)
    br, bc = r - dr, c - dc
    ar, ac = r + dr * length, c + dc * length

    if in_bounds(ctx, br, bc) and ctx_letter(ctx, br, bc):
        return False
    if in_bounds(ctx, ar, ac) and ctx_letter(ctx, ar, ac):
        return False

    return True


def passes_center(ctx, r: int, c: int, direction: str, length: int) -> bool:
    return any(cell_at(direction, r, c, i) == ctx["center"] for i in range(length))


def perpendicular_fragments(ctx, r: int, c: int, direction: str) -> Tuple[str, str]:
    if direction == DIR_RIGHT:
        d1r, d1c, d2r, d2c = -1, 0, 1, 0
    else:
        d1r, d1c, d2r, d2c = 0, -1, 0, 1

    prefix = []
    rr, cc = r + d1r, c + d1c
    while in_bounds(ctx, rr, cc):
        ch = ctx_letter(ctx, rr, cc)
        if not ch:
            break
        prefix.append(ch)
        rr += d1r
        cc += d1c
    prefix.reverse()

    suffix = []
    rr, cc = r + d2r, c + d2c
    while in_bounds(ctx, rr, cc):
        ch = ctx_letter(ctx, rr, cc)
        if not ch:
            break
        suffix.append(ch)
        rr += d2r
        cc += d2c

    return "".join(prefix), "".join(suffix)


def compute_cross_checks(ctx, word_set: Set[str]):
    """Her boş hücre için ana yön bazında gelebilecek harfleri önceden hesaplar.
    Ana yön YATAY ise çapraz DIKEY kontrol edilir; ana yön DIKEY ise çapraz YATAY kontrol edilir.
    """
    n = ctx["n"]
    checks = {}

    for direction in (DIR_RIGHT, DIR_DOWN):
        for r in range(n):
            for c in range(n):
                if ctx_letter(ctx, r, c):
                    continue

                prefix, suffix = perpendicular_fragments(ctx, r, c, direction)

                if not prefix and not suffix:
                    allowed = ALL_LETTER_SET
                else:
                    allowed_set = set()
                    for ch in LETTERS:
                        if f"{prefix}{ch}{suffix}" in word_set:
                            allowed_set.add(ch)
                    allowed = frozenset(allowed_set)

                checks[(direction, r, c)] = allowed

    return checks


def candidate_start_positions(ctx, word_len: int, anchor_r: int, anchor_c: int, direction: str):
    n = ctx["n"]

    if direction == DIR_RIGHT:
        for off in range(word_len):
            row = anchor_r
            col = anchor_c - off
            if 0 <= col and col + word_len <= n:
                yield row, col
    else:
        for off in range(word_len):
            row = anchor_r - off
            col = anchor_c
            if 0 <= row and row + word_len <= n:
                yield row, col


def segment_has_connection_candidate(ctx, row: int, col: int, length: int, direction: str) -> bool:
    has_empty = False
    has_fixed = False
    adjacent = False

    for i in range(length):
        rr, cc = cell_at(direction, row, col, i)
        ch = ctx_letter(ctx, rr, cc)

        if ch:
            has_fixed = True
        else:
            has_empty = True
            if neighbor_count(ctx, rr, cc) > 0:
                adjacent = True

    return has_empty and (has_fixed or adjacent or ctx["empty"])


def all_legalish_start_positions(ctx, length: int, direction: str):
    n = ctx["n"]

    if direction == DIR_RIGHT:
        for row in range(n):
            for col in range(0, n - length + 1):
                if segment_has_connection_candidate(ctx, row, col, length, direction):
                    yield row, col
    else:
        for row in range(0, n - length + 1):
            for col in range(n):
                if segment_has_connection_candidate(ctx, row, col, length, direction):
                    yield row, col


def ranked_starts(ctx, starts: Set[Tuple[int, int]], length: int, direction: str):
    def rank(pos):
        row, col = pos
        fixed = 0
        adjacent = 0
        bonus_score = 0
        empty_count = 0

        for i in range(length):
            rr, cc = cell_at(direction, row, col, i)
            ch = ctx_letter(ctx, rr, cc)

            if ch:
                fixed += 1
            else:
                empty_count += 1
                bonus = ctx_bonus(ctx, rr, cc)
                if bonus in ("K3", "H3"):
                    bonus_score += 5
                elif bonus in ("K2", "H2", "START"):
                    bonus_score += 3
                adjacent += neighbor_count(ctx, rr, cc)

        return (-fixed, -adjacent, -bonus_score, empty_count, row, col)

    return sorted(starts, key=rank)


def build_pattern(ctx, row: int, col: int, length: int, direction: str):
    fixed_positions = {}
    empties = 0
    allowed_by_pos = {}
    pattern_letters = []

    for i in range(length):
        rr, cc = cell_at(direction, row, col, i)
        ch = ctx_letter(ctx, rr, cc)

        if ch:
            fixed_positions[i] = ch
            pattern_letters.append(ch)
        else:
            empties += 1
            allowed = ctx["cross_checks"].get((direction, rr, cc), ALL_LETTER_SET)
            if not allowed:
                return None, None, None, None
            allowed_by_pos[i] = allowed
            pattern_letters.append(".")

    return "".join(pattern_letters), fixed_positions, empties, allowed_by_pos


def word_matches_fixed(word: str, fixed_positions: Dict[int, str]) -> bool:
    for pos, ch in fixed_positions.items():
        if word[pos] != ch:
            return False
    return True


def word_matches_cross_allowed(word: str, allowed_by_pos: Dict[int, frozenset]) -> bool:
    for pos, allowed in allowed_by_pos.items():
        if word[pos] not in allowed:
            return False
    return True


def rack_array(rack: List[str]) -> Tuple[List[int], int, List[str]]:
    arr = [0] * len(LETTERS)
    jokers = 0
    cleaned = []

    for raw in rack:
        ch = normalize_letter(raw)
        if not ch:
            continue
        cleaned.append(ch)

        if ch == "?":
            jokers += 1
        else:
            idx = LETTER_INDEX.get(ch)
            if idx is not None:
                arr[idx] += 1

    return arr, jokers, cleaned


def can_make_needed_array(needed: List[str], rack_arr: List[int], joker_count: int):
    left = rack_arr[:]
    jokers = joker_count
    joker_used = []

    for ch in needed:
        idx = LETTER_INDEX.get(ch)
        if idx is not None and left[idx] > 0:
            left[idx] -= 1
        elif jokers > 0:
            jokers -= 1
            joker_used.append(ch)
        else:
            return None

    return joker_used


def word_count_possible_for_needed(entry: WordEntry, fixed_positions: Dict[int, str], rack_arr: List[int], joker_count: int) -> bool:
    """Counter yerine hızlı harf dizisiyle kaba ön filtre.
    Sabit tahta harflerini kelime ihtiyacından düşerek sadece rack'ten gerekli kısmı kontrol eder.
    """
    need = list(entry.count_array)

    for _, ch in fixed_positions.items():
        idx = LETTER_INDEX.get(ch)
        if idx is not None and need[idx] > 0:
            need[idx] -= 1

    missing = 0
    for i, cnt in enumerate(need):
        diff = cnt - rack_arr[i]
        if diff > 0:
            missing += diff
            if missing > joker_count:
                return False

    return True


def estimate_needed_letters(word: str, fixed_positions: Dict[int, str]) -> List[str]:
    return [ch for i, ch in enumerate(word) if i not in fixed_positions]


def get_pattern_candidates(
    index: DictionaryIndex,
    length: int,
    fixed_positions: Dict[int, str],
):
    key = (length, tuple(sorted(fixed_positions.items())))
    cached = index.pattern_cache.get(key)
    if cached is not None:
        return cached

    if not fixed_positions:
        candidates = index.by_length.get(length, [])
    else:
        pools = []
        for pos, ch in fixed_positions.items():
            pools.append(index.by_pos_letter.get((length, pos, ch), []))

        if not pools:
            candidates = []
        else:
            base_pool = min(pools, key=len)
            candidates = [entry for entry in base_pool if word_matches_fixed(entry.word, fixed_positions)]

    # Pattern cache fazla büyümesin.
    if len(index.pattern_cache) < 12000:
        index.pattern_cache[key] = candidates

    return candidates


def fits(ctx, word: str, row: int, col: int, direction: str):
    length = len(word)

    if not line_in_bounds(ctx, row, col, direction, length):
        return None

    placed = []
    needed = []
    touch_count = 0
    adjacent_contacts = 0
    touched_existing = set()

    for i, ch in enumerate(word):
        rr, cc = cell_at(direction, row, col, i)
        existing = ctx_letter(ctx, rr, cc)

        if existing:
            if existing != ch:
                return None
            touch_count += 1
            touched_existing.add((rr, cc))
        else:
            allowed = ctx["cross_checks"].get((direction, rr, cc), ALL_LETTER_SET)
            if ch not in allowed:
                return None

            placed.append((rr, cc, ch))
            needed.append(ch)
            adjacent_contacts += neighbor_count(ctx, rr, cc)

    if not placed:
        return None

    if not edge_ok(ctx, row, col, direction, length):
        return None

    if ctx["empty"]:
        if not passes_center(ctx, row, col, direction, length):
            return None
    elif touch_count == 0 and adjacent_contacts == 0:
        return None

    interaction_score = touch_count + adjacent_contacts
    return placed, needed, interaction_score, len(touched_existing)


def cross_word_for_new_tile(ctx, r: int, c: int, ch: str, direction: str):
    n = ctx["n"]

    if direction == DIR_RIGHT:
        start = r
        while start > 0 and ctx_letter(ctx, start - 1, c):
            start -= 1

        end = r
        while end < n - 1 and ctx_letter(ctx, end + 1, c):
            end += 1

        letters = []
        coords = []
        for rr in range(start, end + 1):
            letters.append(ch if rr == r else ctx_letter(ctx, rr, c))
            coords.append((rr, c))

        return "".join(letters), coords

    start = c
    while start > 0 and ctx_letter(ctx, r, start - 1):
        start -= 1

    end = c
    while end < n - 1 and ctx_letter(ctx, r, end + 1):
        end += 1

    letters = []
    coords = []
    for cc in range(start, end + 1):
        letters.append(ch if cc == c else ctx_letter(ctx, r, cc))
        coords.append((r, cc))

    return "".join(letters), coords


def all_words_valid_cached(ctx, word: str, direction: str, placed: List[Tuple[int, int, str]], cross_cache):
    word_set = ctx["word_set"]

    if word not in word_set:
        return False, []

    created = [word]

    for r, c, ch in placed:
        key = (r, c, direction, ch)
        cached = cross_cache.get(key)

        if cached is None:
            cw, _ = cross_word_for_new_tile(ctx, r, c, ch, direction)
            if len(cw) > 1 and cw not in word_set:
                cached = (False, tuple())
            elif len(cw) > 1:
                cached = (True, (cw,))
            else:
                cached = (True, tuple())
            cross_cache[key] = cached

        ok, words = cached
        if not ok:
            return False, []

        created.extend(words)

    return True, created


def build_joker_cells(placed: List[Tuple[int, int, str]], joker_used: List[str]):
    joker_pool = list(joker_used)
    joker_cells = set()

    for r, c, ch in placed:
        if ch in joker_pool:
            joker_cells.add((r, c))
            joker_pool.remove(ch)

    return joker_cells


def letter_score(ch: str, is_joker: bool) -> int:
    return 0 if is_joker else LETTER_SCORES.get(ch, 0)


def apply_bonus(base_value: int, bonus: Optional[str]):
    word_mult = 1
    letter_value = base_value

    if bonus == "H2":
        letter_value *= 2
    elif bonus == "H3":
        letter_value *= 3
    elif bonus in ("K2", "START"):
        word_mult = 2
    elif bonus == "K3":
        word_mult = 3

    return letter_value, word_mult


def score_word_with_coords(ctx, coords, placed_map, joker_cells):
    total = 0
    word_mult = 1
    bonus_notes = []

    for r, c in coords:
        if (r, c) in placed_map:
            ch = placed_map[(r, c)]
            base = letter_score(ch, (r, c) in joker_cells)
            bonus = ctx_bonus(ctx, r, c)
            letter_val, wm = apply_bonus(base, bonus)
            total += letter_val
            word_mult *= wm

            if bonus is not None:
                note_bonus = "K2" if bonus == "START" else bonus
                bonus_notes.append(f"{ch}@{r + 1},{c + 1}:{note_bonus}")
        else:
            ch = ctx_letter(ctx, r, c)
            total += LETTER_SCORES.get(ch, 0)

    return total * word_mult, bonus_notes


def score_move(ctx, word, row, col, direction, placed, joker_used):
    placed_map = {(r, c): ch for r, c, ch in placed}
    joker_cells = build_joker_cells(placed, joker_used)

    main_coords = [
        cell_at(direction, row, col, i)
        for i in range(len(word))
    ]

    main_score, notes = score_word_with_coords(ctx, main_coords, placed_map, joker_cells)

    cross_total = 0
    cross_details = []
    cross_count = 0

    for r, c, ch in placed:
        cw, coords = cross_word_for_new_tile(ctx, r, c, ch, direction)
        if len(cw) > 1:
            cw_score, cw_notes = score_word_with_coords(ctx, coords, placed_map, joker_cells)
            cross_total += cw_score
            cross_count += 1
            cross_details.append(f"{cw}={cw_score}")
            notes.extend(cw_notes)

    final = main_score + cross_total

    if len(placed) == 7:
        final += 50

    detail = f"ana_kelime={word}, ana_puan={main_score}, ek_puan={cross_total}, toplam={final}"

    if len(placed) == 7:
        detail += " | 7 taş bonusu=50"

    if cross_details:
        detail += " | yan=" + ", ".join(cross_details)

    if notes:
        seen = set()
        uniq_notes = []
        for note in notes:
            if note not in seen:
                seen.add(note)
                uniq_notes.append(note)
        detail += " | bonus=" + " ; ".join(uniq_notes)

    return final, detail, cross_count, joker_cells


class TopCollector:
    def __init__(self, limit: int):
        self.limit = limit
        self.heap = []
        self.seen = set()
        self.counter = 0

    def add(self, move: Dict[str, Any]):
        key = (move["word"], move["row"], move["col"], move["direction"], move["score"])
        if key in self.seen:
            return

        self.seen.add(key)

        rank = (
            int(move["score"]),
            int(move["effective_score"]),
            int(move["cross_count"]),
            int(move["interaction_score"]),
            len(move["word"]),
            -int(move["row"]) - int(move["col"]),
        )

        self.counter += 1
        item = (rank, self.counter, move)

        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, item)
        elif rank > self.heap[0][0]:
            heapq.heapreplace(self.heap, item)

    def results(self):
        out = [item[2] for item in self.heap]
        out.sort(key=lambda x: (-x["score"], -x["effective_score"], x["word"], x["row"], x["col"]))
        return out


def normalize_suggestion(move: Dict[str, Any]) -> Dict[str, Any]:
    joker_cells = move.get("joker_cells") or set()

    placed = [
        {
            "row": r,
            "col": c,
            "letter": ch,
            "is_joker": (r, c) in joker_cells,
        }
        for r, c, ch in move["placed"]
    ]

    return {
        "word": move["word"],
        "row": move["row"],
        "col": move["col"],
        "direction": move["direction"],
        "position": f'{move["direction"]} · {move["row"] + 1} / {move["col"] + 1}',
        "score": move["score"],
        "effective_score": move["effective_score"],
        "placed": placed,
        "covered": [{"row": r, "col": c} for r, c in move["covered"]],
        "detail": move["detail"],
        "createdWords": move["created_words"],
        "crossWords": [w for w in move["created_words"] if w != move["word"]],
        "interaction": move["interaction_score"],
        "crossCount": move["cross_count"],
    }


def make_cache_key(board, rack, limit, seconds, max_checks):
    compact_board = []
    for row in board:
        compact_row = []
        for cell in row:
            if isinstance(cell, dict):
                compact_row.append((normalize_letter(cell.get("letter", "")), cell.get("bonus")))
            else:
                compact_row.append((normalize_letter(cell), None))
        compact_board.append(compact_row)

    compact_rack = sorted(normalize_letter(x) for x in rack if normalize_letter(x))
    payload = {
        "board": compact_board,
        "rack": compact_rack,
        "limit": limit,
        "seconds": seconds,
        "max_checks": max_checks,
    }
    return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))


def get_cached(key: str):
    global CACHE_HITS, CACHE_MISSES

    if key in SOLVE_CACHE:
        CACHE_HITS += 1
        value = SOLVE_CACHE.pop(key)
        SOLVE_CACHE[key] = value
        cached = copy.deepcopy(value)
        cached["debug"]["cacheHit"] = True
        return cached

    CACHE_MISSES += 1
    return None


def set_cached(key: str, value: dict):
    SOLVE_CACHE[key] = copy.deepcopy(value)
    while len(SOLVE_CACHE) > SOLVE_CACHE_MAX:
        SOLVE_CACHE.popitem(last=False)


def find_best_moves(ctx, rack, index, limit=900, seconds=8.0, max_checks=5_000_000):
    start_time = time.time()
    deadline = start_time + seconds

    rack_arr, joker_count, cleaned_rack = rack_array(rack)
    rack_len = len(cleaned_rack)

    max_len = min(ctx["n"], rack_len + ctx["n"])
    anchors = ctx["anchors"]
    lengths = [length for length in range(2, max_len + 1) if length in index.by_length]

    collector = TopCollector(limit=max(20, limit))
    cross_cache = {}

    checks = 0
    pattern_hits = 0
    fit_hits = 0
    valid_hits = 0
    expanded_starts = 0
    cache_candidate_hits = 0
    skipped_cross = 0

    board_tile_count = len(ctx["tiles"])
    should_expand_base = (
        board_tile_count >= 18
        or len(anchors) >= 10
        or max_checks >= 4_000_000
    )

    for length in lengths:
        if time.time() > deadline or checks >= max_checks:
            break

        for direction in (DIR_RIGHT, DIR_DOWN):
            if time.time() > deadline or checks >= max_checks:
                break

            starts = set()

            if ctx["empty"]:
                cr, cc = ctx["center"]
                starts.update(candidate_start_positions(ctx, length, cr, cc, direction))
            else:
                for ar, ac in anchors:
                    for row, col in candidate_start_positions(ctx, length, ar, ac, direction):
                        starts.add((row, col))

                if should_expand_base:
                    before = len(starts)
                    starts.update(all_legalish_start_positions(ctx, length, direction))
                    expanded_starts += max(0, len(starts) - before)

            pattern_cache = {}

            for row, col in ranked_starts(ctx, starts, length, direction):
                if time.time() > deadline or checks >= max_checks:
                    break

                if not edge_ok(ctx, row, col, direction, length):
                    continue

                pattern, fixed_positions, empties, allowed_by_pos = build_pattern(ctx, row, col, length, direction)
                if pattern is None:
                    skipped_cross += 1
                    continue

                if empties == 0:
                    continue

                cache_key = (length, pattern)
                if cache_key not in pattern_cache:
                    candidates = get_pattern_candidates(index, length, fixed_positions)
                    pattern_cache[cache_key] = candidates
                else:
                    cache_candidate_hits += 1

                entries = pattern_cache[cache_key]
                if entries:
                    pattern_hits += 1

                for entry in entries:
                    if time.time() > deadline or checks >= max_checks:
                        break

                    word = entry.word

                    # Cross-check ön hesaplama ile erken eleme.
                    if allowed_by_pos and not word_matches_cross_allowed(word, allowed_by_pos):
                        skipped_cross += 1
                        continue

                    # Counter yerine hızlı harf dizisi ile ön eleme.
                    if not word_count_possible_for_needed(entry, fixed_positions, rack_arr, joker_count):
                        continue

                    checks += 1

                    needed_preview = estimate_needed_letters(word, fixed_positions)
                    joker_used_preview = can_make_needed_array(needed_preview, rack_arr, joker_count)
                    if joker_used_preview is None:
                        continue

                    fit = fits(ctx, word, row, col, direction)
                    if not fit:
                        continue

                    fit_hits += 1
                    placed, needed, interaction_score, overlap_count = fit

                    joker_used = can_make_needed_array(needed, rack_arr, joker_count)
                    if joker_used is None:
                        continue

                    ok, created_words = all_words_valid_cached(ctx, word, direction, placed, cross_cache)
                    if not ok:
                        continue

                    valid_hits += 1
                    score, detail, cross_count, joker_cells = score_move(ctx, word, row, col, direction, placed, joker_used)

                    covered = [
                        cell_at(direction, row, col, i)
                        for i in range(len(word))
                    ]

                    effective_score = score + (cross_count * 10) + (interaction_score * 4) + (overlap_count * 3)

                    collector.add({
                        "word": word,
                        "row": row,
                        "col": col,
                        "direction": direction,
                        "score": score,
                        "effective_score": effective_score,
                        "placed": placed,
                        "covered": covered,
                        "detail": detail + f" | desen={pattern}, etkileşim={interaction_score}, çapraz_sayısı={cross_count}",
                        "created_words": created_words,
                        "interaction_score": interaction_score,
                        "cross_count": cross_count,
                        "joker_cells": joker_cells,
                    })

                    # Çok iyi sayıda sonuç varsa hızlı modda gereksiz uzatma yapma.
                    if len(collector.heap) >= limit and time.time() - start_time > seconds * 0.55:
                        break

    uniq = [normalize_suggestion(move) for move in collector.results()[:limit]]

    return {
        "suggestions": uniq,
        "message": "" if uniq else "Bu taşlarla tahtaya kurallara uygun kelime yerleştirilemedi.",
        "debug": {
            "engine": "v8.2_pattern_ultra_fast",
            "wordCount": len(index.word_set),
            "rack": cleaned_rack,
            "boardSize": ctx["n"],
            "boardTiles": len(ctx["tiles"]),
            "anchors": len(anchors),
            "lengthBuckets": len(lengths),
            "checks": checks,
            "patternHits": pattern_hits,
            "fitHits": fit_hits,
            "validHits": valid_hits,
            "expandedStarts": expanded_starts,
            "crossCacheSize": len(cross_cache),
            "patternCacheSize": len(index.pattern_cache),
            "localPatternCacheHits": cache_candidate_hits,
            "skippedByCrossCheck": skipped_cross,
            "returned": len(uniq),
            "fallback": False,
            "timedOut": time.time() > deadline,
            "elapsedMs": int((time.time() - start_time) * 1000),
            "cacheHit": False,
        },
    }


def generate_moves(
    board: List[List[Any]],
    rack: List[str],
    index: DictionaryIndex,
    limit: int = 900,
    seconds: float = 8.0,
    max_checks: int = 5_000_000,
    **_kwargs,
):
    cleaned_rack = [normalize_letter(x) for x in rack if normalize_letter(x)]

    if not cleaned_rack:
        return {
            "suggestions": [],
            "message": "Harf alanına en az bir taş gir.",
            "debug": {
                "engine": "v8.2_pattern_ultra_fast",
                "reason": "empty_rack",
                "wordCount": len(index.word_set),
                "fallback": False,
                "cacheHit": False,
            },
        }

    if len(index.word_set) == 0:
        return {
            "suggestions": [],
            "message": "Sözlük yüklenmedi. backend/data klasörünü kontrol et.",
            "debug": {
                "engine": "v8.2_pattern_ultra_fast",
                "reason": "empty_dictionary",
                "wordCount": 0,
                "fallback": False,
                "cacheHit": False,
            },
        }

    key = make_cache_key(board, cleaned_rack, limit, seconds, max_checks)
    cached = get_cached(key)
    if cached is not None:
        return cached

    ctx = build_board_context(board, index.word_set)
    result = find_best_moves(
        ctx=ctx,
        rack=cleaned_rack,
        index=index,
        limit=limit,
        seconds=seconds,
        max_checks=max_checks,
    )

    set_cached(key, result)
    return result
