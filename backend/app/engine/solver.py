from __future__ import annotations

import heapq
import time
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Any, Dict, Iterable, List, Optional, Set, Tuple

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
    if ch in TR_MAP:
        return TR_MAP[ch]
    return ch.upper().replace("İ", "İ")


def normalize_word(word: Any) -> str:
    return "".join(normalize_letter(ch) for ch in str(word) if str(ch).strip())


def is_valid_word(word: str) -> bool:
    return len(word) >= 2 and all(ch in LETTER_SCORES and ch != "?" for ch in word)


@dataclass(frozen=True)
class WordInfo:
    word: str
    counter: Counter
    score: int
    length: int


@dataclass
class DictionaryIndex:
    word_set: Set[str]
    words: List[WordInfo]
    words_by_letter: Dict[str, List[WordInfo]]


def build_dictionary_index(words: Iterable[str]) -> DictionaryIndex:
    seen: Set[str] = set()
    infos: List[WordInfo] = []
    by_letter: Dict[str, List[WordInfo]] = defaultdict(list)
    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word) or word in seen:
            continue
        seen.add(word)
        info = WordInfo(word=word, counter=Counter(word), score=sum(LETTER_SCORES.get(c, 0) for c in word), length=len(word))
        infos.append(info)
        for ch in set(word):
            by_letter[ch].append(info)
    infos.sort(key=lambda x: (-x.score, -x.length, x.word))
    for ch in list(by_letter):
        by_letter[ch].sort(key=lambda x: (-x.score, -x.length, x.word))
    return DictionaryIndex(word_set=seen, words=infos, words_by_letter=dict(by_letter))


def board_size(board: List[List[dict]]) -> int:
    return len(board)


def in_bounds(board: List[List[dict]], r: int, c: int) -> bool:
    n = board_size(board)
    return 0 <= r < n and 0 <= c < n


def get_center(board: List[List[dict]]) -> Tuple[int, int]:
    n = board_size(board)
    return n // 2, n // 2


def get_letter(board: List[List[dict]], r: int, c: int) -> str:
    if not in_bounds(board, r, c):
        return ""
    cell = board[r][c]
    if isinstance(cell, dict):
        return normalize_letter(cell.get("letter", ""))
    return normalize_letter(cell)


def get_bonus(board: List[List[dict]], r: int, c: int) -> Optional[str]:
    if not in_bounds(board, r, c):
        return None
    cell = board[r][c]
    if isinstance(cell, dict):
        return cell.get("bonus")
    return None


def board_has_tiles(board: List[List[dict]]) -> bool:
    for r in range(len(board)):
        for c in range(len(board[r])):
            if get_letter(board, r, c):
                return True
    return False


def rack_counter(rack: List[str]) -> Counter:
    cnt = Counter()
    for x in rack:
        ch = normalize_letter(x)
        if ch:
            cnt[ch] += 1
    return cnt


def board_counter(board: List[List[dict]]) -> Counter:
    cnt = Counter()
    for r in range(len(board)):
        for c in range(len(board[r])):
            ch = get_letter(board, r, c)
            if ch:
                cnt[ch] += 1
    return cnt


def existing_tiles(board: List[List[dict]]) -> List[Tuple[int, int, str]]:
    out = []
    for r in range(len(board)):
        for c in range(len(board[r])):
            ch = get_letter(board, r, c)
            if ch:
                out.append((r, c, ch))
    return out


def neighbor_count(board: List[List[dict]], r: int, c: int) -> int:
    return sum(1 for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if in_bounds(board, nr, nc) and get_letter(board, nr, nc))


def anchor_cells(board: List[List[dict]]) -> List[Tuple[int, int]]:
    if not board_has_tiles(board):
        return [get_center(board)]
    anchors = set()
    for r, c, _ in existing_tiles(board):
        for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if in_bounds(board, nr, nc) and not get_letter(board, nr, nc):
                anchors.add((nr, nc))
    center = get_center(board)
    def rank(pos):
        r, c = pos
        bonus = get_bonus(board, r, c)
        bonus_rank = -8 if bonus in ("K3", "H3") else (-4 if bonus in ("K2", "H2", "START") else 0)
        return (bonus_rank, -neighbor_count(board, r, c), abs(r-center[0]) + abs(c-center[1]), r, c)
    return sorted(anchors, key=rank)


def cell_at(direction: str, row: int, col: int, i: int) -> Tuple[int, int]:
    return (row, col + i) if direction == DIR_RIGHT else (row + i, col)


def line_in_bounds(board: List[List[dict]], row: int, col: int, direction: str, length: int) -> bool:
    end_r, end_c = cell_at(direction, row, col, length - 1)
    return in_bounds(board, row, col) and in_bounds(board, end_r, end_c)


def before_after_blocked(board: List[List[dict]], row: int, col: int, direction: str, length: int) -> bool:
    if direction == DIR_RIGHT:
        before, after = (row, col - 1), (row, col + length)
    else:
        before, after = (row - 1, col), (row + length, col)
    return (in_bounds(board, *before) and get_letter(board, *before)) or (in_bounds(board, *after) and get_letter(board, *after))


def passes_center(board: List[List[dict]], row: int, col: int, direction: str, length: int) -> bool:
    center = get_center(board)
    return any(cell_at(direction, row, col, i) == center for i in range(length))


def perpendicular_fragments(board: List[List[dict]], r: int, c: int, direction: str) -> Tuple[str, str]:
    if direction == DIR_RIGHT:
        deltas = ((-1, 0), (1, 0))
    else:
        deltas = ((0, -1), (0, 1))
    prefix = []
    dr, dc = deltas[0]
    nr, nc = r + dr, c + dc
    while in_bounds(board, nr, nc):
        ch = get_letter(board, nr, nc)
        if not ch:
            break
        prefix.append(ch)
        nr += dr
        nc += dc
    prefix.reverse()
    suffix = []
    dr, dc = deltas[1]
    nr, nc = r + dr, c + dc
    while in_bounds(board, nr, nc):
        ch = get_letter(board, nr, nc)
        if not ch:
            break
        suffix.append(ch)
        nr += dr
        nc += dc
    return "".join(prefix), "".join(suffix)


def cross_valid(board: List[List[dict]], r: int, c: int, direction: str, ch: str, word_set: Set[str]) -> bool:
    pre, suf = perpendicular_fragments(board, r, c, direction)
    if not pre and not suf:
        return True
    return f"{pre}{ch}{suf}" in word_set


def score_word(board: List[List[dict]], word: str, row: int, col: int, direction: str, newly: Set[Tuple[int, int]], jokers: Set[Tuple[int, int]]) -> int:
    total = 0
    word_mul = 1
    for i, ch in enumerate(word):
        r, c = cell_at(direction, row, col, i)
        value = 0 if (r, c) in jokers else LETTER_SCORES.get(ch, 0)
        if (r, c) in newly:
            bonus = get_bonus(board, r, c)
            if bonus in LETTER_MULTIPLIERS:
                value *= LETTER_MULTIPLIERS[bonus]
            elif bonus in WORD_MULTIPLIERS:
                word_mul *= WORD_MULTIPLIERS[bonus]
        total += value
    return total * word_mul


def can_make_word(info: WordInfo, available: Counter, joker_count: int) -> bool:
    missing = 0
    for ch, need in info.counter.items():
        have = available.get(ch, 0)
        if have < need:
            missing += need - have
            if missing > joker_count:
                return False
    return True


def consume_position(board: List[List[dict]], word: str, row: int, col: int, direction: str, rack: Counter):
    left = rack.copy()
    jokers = set()
    newly = set()
    overlap = 0
    for i, ch in enumerate(word):
        r, c = cell_at(direction, row, col, i)
        existing = get_letter(board, r, c)
        if existing:
            if existing != ch:
                return None
            overlap += 1
            continue
        newly.add((r, c))
        if left.get(ch, 0) > 0:
            left[ch] -= 1
            if left[ch] <= 0:
                del left[ch]
        elif left.get("?", 0) > 0:
            left["?"] -= 1
            if left["?"] <= 0:
                del left["?"]
            jokers.add((r, c))
        else:
            return None
    return newly, jokers, overlap


def compute_move(board: List[List[dict]], index: DictionaryIndex, word: str, row: int, col: int, direction: str, rack: Counter, strict: bool = True, check_cross: bool = True):
    if not line_in_bounds(board, row, col, direction, len(word)):
        return None
    if strict and before_after_blocked(board, row, col, direction, len(word)):
        return None
    empty_board = not board_has_tiles(board)
    if empty_board and not passes_center(board, row, col, direction, len(word)):
        return None
    consumed = consume_position(board, word, row, col, direction, rack)
    if consumed is None:
        return None
    newly, jokers, overlap = consumed
    if not newly:
        return None
    interaction = overlap
    placed = []
    for i, ch in enumerate(word):
        r, c = cell_at(direction, row, col, i)
        if (r, c) not in newly:
            continue
        if check_cross and not cross_valid(board, r, c, direction, ch, index.word_set):
            return None
        if neighbor_count(board, r, c):
            interaction += 1
        placed.append({"row": r, "col": c, "letter": ch, "is_joker": (r, c) in jokers})
    if strict and not empty_board and interaction == 0:
        return None
    total_score = score_word(board, word, row, col, direction, newly, jokers)
    created = [word]
    cross_words = []
    if check_cross:
        for p in placed:
            r, c = int(p["row"]), int(p["col"])
            pre, suf = perpendicular_fragments(board, r, c, direction)
            if pre or suf:
                cw = f"{pre}{p['letter']}{suf}"
                cross_words.append(cw)
                created.append(cw)
                total_score += sum(LETTER_SCORES.get(x, 0) for x in cw)
    if len(placed) == 7:
        total_score += 50
    return {
        "word": word,
        "row": row,
        "col": col,
        "direction": direction,
        "position": f"{direction} · {row + 1} / {col + 1}",
        "score": total_score,
        "placed": placed,
        "createdWords": created,
        "crossWords": cross_words,
        "interaction": interaction,
        "overlap": overlap,
        "connected": bool(empty_board or interaction > 0),
        "relaxed": not strict,
    }


class TopCollector:
    def __init__(self, limit: int):
        self.limit = limit
        self.heap = []
        self.seen = set()
        self.counter = 0
    def add(self, move: Dict[str, Any]):
        key = (move["word"], move["row"], move["col"], move["direction"], bool(move.get("relaxed")))
        if key in self.seen:
            return
        self.seen.add(key)
        rank = (int(move["score"]), int(bool(move.get("connected"))), -int(bool(move.get("relaxed"))), len(move["placed"]), int(move["interaction"]), len(move["word"]))
        self.counter += 1
        entry = (rank, self.counter, move)
        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, entry)
        elif rank > self.heap[0][0]:
            heapq.heapreplace(self.heap, entry)
    def results(self):
        out = [x[2] for x in self.heap]
        out.sort(key=lambda m: (-int(m["score"]), int(bool(m.get("relaxed"))), -int(bool(m.get("connected"))), -len(m["placed"]), m["word"]))
        return out


def candidate_starts(board: List[List[dict]], word: str, anchors: List[Tuple[int, int]], tiles: List[Tuple[int, int, str]], direction: str, empty_board: bool):
    starts = set()
    L = len(word)
    if empty_board:
        cr, cc = get_center(board)
        for i in range(L):
            row = cr - (i if direction == DIR_DOWN else 0)
            col = cc - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board, row, col, direction, L):
                starts.add((row, col))
        return list(starts)
    for ar, ac in anchors:
        for i in range(L):
            row = ar - (i if direction == DIR_DOWN else 0)
            col = ac - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board, row, col, direction, L):
                starts.add((row, col))
    positions = defaultdict(list)
    for i, ch in enumerate(word):
        positions[ch].append(i)
    for tr, tc, tch in tiles:
        for i in positions.get(tch, []):
            row = tr - (i if direction == DIR_DOWN else 0)
            col = tc - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board, row, col, direction, L):
                starts.add((row, col))
    return list(starts)


def empty_line_starts(board: List[List[dict]], length: int, direction: str):
    starts = []
    n = board_size(board)
    for r in range(n):
        for c in range(n):
            if not line_in_bounds(board, r, c, direction, length):
                continue
            ok = True
            for i in range(length):
                rr, cc = cell_at(direction, r, c, i)
                if get_letter(board, rr, cc):
                    ok = False
                    break
            if ok:
                starts.append((r, c))
    return starts


def fallback_rack_words(board: List[List[dict]], rack_cnt: Counter, index: DictionaryIndex, collector: TopCollector, deadline: float, max_count: int):
    joker = rack_cnt.get("?", 0)
    count = 0
    for info in index.words:
        if time.time() > deadline or count >= max_count:
            return
        if info.length > sum(rack_cnt.values()):
            continue
        if not can_make_word(info, rack_cnt, joker):
            continue
        for direction in (DIR_RIGHT, DIR_DOWN):
            for row, col in empty_line_starts(board, info.length, direction)[:40]:
                move = compute_move(board, index, info.word, row, col, direction, rack_cnt, strict=False, check_cross=False)
                if move:
                    move["fallback"] = True
                    collector.add(move)
                    count += 1
                    break
            if count >= max_count:
                return


def generate_moves(board: List[List[dict]], rack: List[str], index: DictionaryIndex, limit: int = 500, seconds: float = 8.0, max_checks: int = 450000, fallback_min: int = 25, **kwargs) -> List[Dict[str, Any]]:
    start_time = time.time()
    deadline = start_time + seconds
    rack_cnt = rack_counter(rack)
    rack_len = sum(rack_cnt.values())
    if rack_len == 0:
        return []
    empty = not board_has_tiles(board)
    n = board_size(board)
    max_len = min(n, rack_len if empty else rack_len + 10)
    anchors = anchor_cells(board)
    tiles = existing_tiles(board)
    available = rack_cnt + board_counter(board)
    joker = rack_cnt.get("?", 0)
    collector = TopCollector(limit=max(20, limit))
    checks = 0
    for info in index.words:
        if time.time() > deadline or checks >= max_checks:
            break
        if info.length > max_len:
            continue
        if not can_make_word(info, available, joker):
            continue
        for direction in (DIR_RIGHT, DIR_DOWN):
            starts = candidate_starts(board, info.word, anchors, tiles, direction, empty)
            for row, col in starts:
                if time.time() > deadline or checks >= max_checks:
                    break
                checks += 1
                move = compute_move(board, index, info.word, row, col, direction, rack_cnt, strict=True, check_cross=True)
                if move:
                    collector.add(move)
        if len(collector.heap) >= limit and time.time() - start_time > seconds * 0.45:
            break
    if len(collector.heap) < fallback_min and time.time() < deadline:
        for info in index.words:
            if time.time() > deadline or checks >= max_checks:
                break
            if info.length > max_len:
                continue
            if not can_make_word(info, available, joker):
                continue
            for direction in (DIR_RIGHT, DIR_DOWN):
                starts = candidate_starts(board, info.word, anchors, tiles, direction, empty)
                for row, col in starts:
                    if time.time() > deadline or checks >= max_checks:
                        break
                    checks += 1
                    move = compute_move(board, index, info.word, row, col, direction, rack_cnt, strict=True, check_cross=False)
                    if move:
                        move["relaxed"] = True
                        collector.add(move)
            if len(collector.heap) >= fallback_min:
                break
    if len(collector.heap) < fallback_min and time.time() < deadline:
        fallback_rack_words(board, rack_cnt, index, collector, deadline, fallback_min)
    return collector.results()[:limit]
