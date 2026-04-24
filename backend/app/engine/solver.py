from __future__ import annotations

import heapq
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Set

DIR_RIGHT = "YATAY"
DIR_DOWN = "DIKEY"
TR_MAP = {"i": "İ", "ı": "I", "ş": "Ş", "ğ": "Ğ", "ü": "Ü", "ö": "Ö", "ç": "Ç"}
LETTER_SCORES = {
    "A": 1, "B": 3, "C": 4, "Ç": 4, "D": 3, "E": 1, "F": 7, "G": 5, "Ğ": 8,
    "H": 5, "I": 2, "İ": 1, "J": 10, "K": 1, "L": 1, "M": 2, "N": 1, "O": 2,
    "Ö": 7, "P": 5, "R": 1, "S": 2, "Ş": 4, "T": 1, "U": 2, "Ü": 3, "V": 7,
    "Y": 3, "Z": 4, "?": 0,
}
WORD_MULTIPLIERS = {"K2": 2, "K3": 3, "START": 2}
LETTER_MULTIPLIERS = {"H2": 2, "H3": 3}


def normalize_letter(ch: Any) -> str:
    if not ch:
        return ""
    ch = str(ch).strip()[:1]
    return TR_MAP.get(ch, ch.upper().replace("İ", "İ"))


def normalize_word(word: Any) -> str:
    return "".join(normalize_letter(ch) for ch in str(word) if str(ch).strip())


def is_valid_word(word: str) -> bool:
    return len(word) >= 2 and all(ch in LETTER_SCORES and ch != "?" for ch in word)


@dataclass(frozen=True)
class WordInfo:
    word: str
    counter: Counter
    base_score: int
    length: int


@dataclass
class DictionaryIndex:
    word_set: Set[str]
    words: List[WordInfo]
    words_by_length: Dict[int, List[WordInfo]]
    words_by_letter: Dict[str, List[WordInfo]]


def build_dictionary_index(words: Iterable[str]) -> DictionaryIndex:
    word_set: Set[str] = set()
    infos: List[WordInfo] = []
    by_length: Dict[int, List[WordInfo]] = defaultdict(list)
    by_letter: Dict[str, List[WordInfo]] = defaultdict(list)
    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word) or word in word_set:
            continue
        word_set.add(word)
        info = WordInfo(word, Counter(word), sum(LETTER_SCORES.get(ch, 0) for ch in word), len(word))
        infos.append(info)
        by_length[len(word)].append(info)
        for ch in set(word):
            by_letter[ch].append(info)
    infos.sort(key=lambda x: (-x.base_score, -x.length, x.word))
    for group in by_length.values():
        group.sort(key=lambda x: (-x.base_score, -x.length, x.word))
    for group in by_letter.values():
        group.sort(key=lambda x: (-x.base_score, -x.length, x.word))
    return DictionaryIndex(word_set, infos, dict(by_length), dict(by_letter))


def size(board): return len(board)
def in_bounds(board, r, c): return 0 <= r < size(board) and 0 <= c < size(board)
def center(board): return (size(board) // 2, size(board) // 2)


def get_letter(board, r, c):
    if not in_bounds(board, r, c):
        return ""
    cell = board[r][c]
    return normalize_letter(cell.get("letter", "")) if isinstance(cell, dict) else normalize_letter(cell)


def get_bonus(board, r, c):
    if not in_bounds(board, r, c):
        return None
    cell = board[r][c]
    return cell.get("bonus") if isinstance(cell, dict) else None


def board_tiles(board):
    out = []
    for r in range(size(board)):
        for c in range(size(board)):
            ch = get_letter(board, r, c)
            if ch:
                out.append((r, c, ch))
    return out


def has_tiles(board): return bool(board_tiles(board))


def rack_counter(rack):
    cnt = Counter()
    for raw in rack:
        ch = normalize_letter(raw)
        if ch:
            cnt[ch] += 1
    return cnt


def board_counter(board):
    cnt = Counter()
    for _, _, ch in board_tiles(board):
        cnt[ch] += 1
    return cnt


def neighbor_count(board, r, c):
    return sum(1 for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if in_bounds(board, nr, nc) and get_letter(board, nr, nc))


def anchors(board):
    if not has_tiles(board):
        return [center(board)]
    a = set()
    for r, c, _ in board_tiles(board):
        for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if in_bounds(board, nr, nc) and not get_letter(board, nr, nc):
                a.add((nr, nc))
    cr, cc = center(board)
    def rank(pos):
        r, c = pos
        b = get_bonus(board, r, c)
        br = -8 if b in ("K3", "H3") else -4 if b in ("K2", "H2", "START") else 0
        return (br, -neighbor_count(board, r, c), abs(r-cr)+abs(c-cc), r, c)
    return sorted(a, key=rank)


def step_cell(direction, r, c, i): return (r, c+i) if direction == DIR_RIGHT else (r+i, c)
def before_cell(direction, r, c): return (r, c-1) if direction == DIR_RIGHT else (r-1, c)
def after_cell(direction, r, c, length): return (r, c+length) if direction == DIR_RIGHT else (r+length, c)


def line_in_bounds(board, r, c, direction, length):
    er, ec = step_cell(direction, r, c, length-1)
    return in_bounds(board, r, c) and in_bounds(board, er, ec)


def edge_blocked(board, r, c, direction, length):
    br, bc = before_cell(direction, r, c)
    ar, ac = after_cell(direction, r, c, length)
    return (in_bounds(board, br, bc) and get_letter(board, br, bc)) or (in_bounds(board, ar, ac) and get_letter(board, ar, ac))


def passes_center(board, r, c, direction, length):
    cen = center(board)
    return any(step_cell(direction, r, c, i) == cen for i in range(length))


def perp_fragments(board, r, c, direction):
    vectors = [(-1,0),(1,0)] if direction == DIR_RIGHT else [(0,-1),(0,1)]
    parts = []
    for dr, dc in vectors:
        arr = []
        nr, nc = r + dr, c + dc
        while in_bounds(board, nr, nc) and get_letter(board, nr, nc):
            arr.append(get_letter(board, nr, nc))
            nr += dr
            nc += dc
        parts.append(arr)
    parts[0].reverse()
    return "".join(parts[0]), "".join(parts[1])


def cross_valid(board, r, c, direction, ch, word_set):
    pre, suf = perp_fragments(board, r, c, direction)
    return True if not pre and not suf else (pre + ch + suf) in word_set


def build_coords(board, r, c, direction, placed_map):
    dr, dc = (0, 1) if direction == DIR_RIGHT else (1, 0)
    rr, cc = r, c
    while in_bounds(board, rr-dr, cc-dc):
        ch = placed_map.get((rr-dr, cc-dc)) or get_letter(board, rr-dr, cc-dc)
        if not ch:
            break
        rr -= dr
        cc -= dc
    coords = []
    while in_bounds(board, rr, cc):
        ch = placed_map.get((rr, cc)) or get_letter(board, rr, cc)
        if not ch:
            break
        coords.append((rr, cc, ch))
        rr += dr
        cc += dc
    return coords


def score_coords(board, coords, new_cells, jokers):
    total = 0
    word_mul = 1
    for r, c, ch in coords:
        val = 0 if jokers.get((r, c), False) else LETTER_SCORES.get(ch, 0)
        if (r, c) in new_cells:
            b = get_bonus(board, r, c)
            if b in LETTER_MULTIPLIERS:
                val *= LETTER_MULTIPLIERS[b]
            elif b in WORD_MULTIPLIERS:
                word_mul *= WORD_MULTIPLIERS[b]
        total += val
    return total * word_mul


def quick_filter(info, available, joker_count):
    missing = 0
    for ch, need in info.counter.items():
        have = available.get(ch, 0)
        if have < need:
            missing += need - have
            if missing > joker_count:
                return False
    return True


def candidate_starts(board, word, a_cells, tiles, direction, empty):
    length = len(word)
    starts = set()
    if empty:
        cr, cc = center(board)
        for i in range(length):
            r = cr - (i if direction == DIR_DOWN else 0)
            c = cc - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board, r, c, direction, length):
                starts.add((r, c))
        return list(starts)
    for ar, ac in a_cells:
        for i in range(length):
            r = ar - (i if direction == DIR_DOWN else 0)
            c = ac - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board, r, c, direction, length):
                starts.add((r, c))
    pos_by_letter = defaultdict(list)
    for i, ch in enumerate(word):
        pos_by_letter[ch].append(i)
    for tr, tc, tch in tiles:
        for i in pos_by_letter.get(tch, []):
            r = tr - (i if direction == DIR_DOWN else 0)
            c = tc - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board, r, c, direction, length):
                starts.add((r, c))
    return list(starts)


def consume(board, word, r, c, direction, rack):
    left = rack.copy()
    jokers = set()
    placed = 0
    overlap = 0
    for i, ch in enumerate(word):
        rr, cc = step_cell(direction, r, c, i)
        ex = get_letter(board, rr, cc)
        if ex:
            if ex != ch:
                return None
            overlap += 1
            continue
        placed += 1
        if left.get(ch, 0) > 0:
            left[ch] -= 1
            if left[ch] == 0:
                del left[ch]
        elif left.get("?", 0) > 0:
            left["?"] -= 1
            if left["?"] == 0:
                del left["?"]
            jokers.add((rr, cc))
        else:
            return None
    return jokers, placed, overlap


def compute_move(board, word_set, word, r, c, direction, rack, require_connection=True):
    length = len(word)
    if not line_in_bounds(board, r, c, direction, length):
        return None
    if edge_blocked(board, r, c, direction, length):
        return None
    empty = not has_tiles(board)
    if empty and not passes_center(board, r, c, direction, length):
        return None
    consumed = consume(board, word, r, c, direction, rack)
    if consumed is None:
        return None
    joker_positions, placed_count, overlap = consumed
    if placed_count == 0:
        return None
    placed = []
    placed_map = {}
    joker_map = {}
    new_cells = set()
    interaction = overlap
    for i, ch in enumerate(word):
        rr, cc = step_cell(direction, r, c, i)
        if get_letter(board, rr, cc):
            continue
        if not cross_valid(board, rr, cc, direction, ch, word_set):
            return None
        is_joker = (rr, cc) in joker_positions
        placed.append({"row": rr, "col": cc, "letter": ch, "is_joker": is_joker})
        placed_map[(rr, cc)] = ch
        joker_map[(rr, cc)] = is_joker
        new_cells.add((rr, cc))
        if neighbor_count(board, rr, cc) > 0:
            interaction += 1
    if not empty and require_connection and interaction == 0:
        return None
    main_coords = build_coords(board, r, c, direction, placed_map)
    main_word = "".join(ch for _, _, ch in main_coords)
    if main_word != word or main_word not in word_set:
        return None
    total = score_coords(board, main_coords, new_cells, joker_map)
    cross_words = []
    created = [main_word]
    cross_dir = DIR_DOWN if direction == DIR_RIGHT else DIR_RIGHT
    for tile in placed:
        rr, cc = tile["row"], tile["col"]
        coords = build_coords(board, rr, cc, cross_dir, placed_map)
        cw = "".join(ch for _, _, ch in coords)
        if len(cw) > 1:
            if cw not in word_set:
                return None
            cross_words.append(cw)
            created.append(cw)
            total += score_coords(board, coords, {(rr, cc)}, joker_map)
    if len(placed) == 7:
        total += 50
    return {"word": word, "row": r, "col": c, "direction": direction, "position": f"{direction} · {r+1} / {c+1}", "score": total, "placed": placed, "createdWords": created, "crossWords": cross_words, "interaction": interaction, "overlap": overlap, "connected": bool(empty or interaction)}


class TopCollector:
    def __init__(self, limit):
        self.limit = limit
        self.heap = []
        self.seen = set()
        self.counter = 0
    def add(self, move):
        key = (move["word"], move["row"], move["col"], move["direction"])
        if key in self.seen:
            return
        self.seen.add(key)
        self.counter += 1
        rank = (int(move["score"]), int(bool(move.get("connected", False))), len(move["placed"]), int(move["interaction"]), len(move["word"]), -int(move["row"]) - int(move["col"]))
        entry = (rank, self.counter, move)
        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, entry)
        elif rank > self.heap[0][0]:
            heapq.heapreplace(self.heap, entry)
    def results(self):
        out = [x[2] for x in self.heap]
        out.sort(key=lambda m: (-int(m["score"]), -int(bool(m.get("connected", False))), -len(m["placed"]), -int(m["interaction"]), -len(m["word"]), m["word"], int(m["row"]), int(m["col"])))
        return out


def rack_fallback(board, index, rack, collector, deadline, max_checks):
    checks = 0
    bsize = size(board)
    joker_count = rack.get("?", 0)
    for info in index.words:
        if time.time() > deadline or checks >= max_checks:
            return
        if info.length > min(bsize, sum(rack.values())):
            continue
        if not quick_filter(info, rack, joker_count):
            continue
        for direction in (DIR_RIGHT, DIR_DOWN):
            for r in range(bsize):
                for c in range(bsize):
                    if time.time() > deadline or checks >= max_checks:
                        return
                    checks += 1
                    if not line_in_bounds(board, r, c, direction, info.length):
                        continue
                    if edge_blocked(board, r, c, direction, info.length):
                        continue
                    if any(get_letter(board, *step_cell(direction, r, c, i)) for i in range(info.length)):
                        continue
                    move = compute_move(board, index.word_set, info.word, r, c, direction, rack, require_connection=False)
                    if move:
                        move["connected"] = False
                        move["fallback"] = True
                        collector.add(move)
                        if len(collector.heap) >= 30:
                            return


def generate_moves(board, rack, index, limit=500, seconds=10.0, max_checks=650000, allow_fallback=True, **_kwargs):
    start = time.time()
    deadline = start + seconds
    rack_cnt = rack_counter(rack)
    rack_len = sum(rack_cnt.values())
    if rack_len == 0:
        return []
    empty = not has_tiles(board)
    bsize = size(board)
    max_len = min(bsize, rack_len if empty else rack_len + 10)
    a_cells = anchors(board)
    tiles = board_tiles(board)
    available = rack_cnt + board_counter(board)
    joker_count = rack_cnt.get("?", 0)
    collector = TopCollector(max(20, limit))
    checks = 0
    for info in index.words:
        if time.time() > deadline or checks >= max_checks:
            break
        if info.length > max_len:
            continue
        if not quick_filter(info, available, joker_count):
            continue
        for direction in (DIR_RIGHT, DIR_DOWN):
            starts = candidate_starts(board, info.word, a_cells, tiles, direction, empty)
            for r, c in starts:
                if time.time() > deadline or checks >= max_checks:
                    break
                checks += 1
                if edge_blocked(board, r, c, direction, info.length):
                    continue
                move = compute_move(board, index.word_set, info.word, r, c, direction, rack_cnt, require_connection=True)
                if move:
                    collector.add(move)
        if len(collector.heap) >= limit and time.time() - start > seconds * 0.35:
            break
    if allow_fallback and len(collector.heap) < 5 and time.time() < deadline:
        rack_fallback(board, index, rack_cnt, collector, deadline, max(20000, max_checks // 8))
    return collector.results()[:limit]
