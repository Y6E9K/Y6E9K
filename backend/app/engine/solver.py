from __future__ import annotations

import heapq
import time
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Set, Tuple

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
    "A": 1,
    "B": 3,
    "C": 4,
    "Ç": 4,
    "D": 3,
    "E": 1,
    "F": 7,
    "G": 5,
    "Ğ": 8,
    "H": 5,
    "I": 2,
    "İ": 1,
    "J": 10,
    "K": 1,
    "L": 1,
    "M": 2,
    "N": 1,
    "O": 2,
    "Ö": 7,
    "P": 5,
    "R": 1,
    "S": 2,
    "Ş": 4,
    "T": 1,
    "U": 2,
    "Ü": 3,
    "V": 7,
    "Y": 3,
    "Z": 4,
    "?": 0,
}

WORD_MULTIPLIERS = {"K2": 2, "K3": 3, "START": 2}
LETTER_MULTIPLIERS = {"H2": 2, "H3": 3}
TR_LETTERS = tuple(ch for ch in LETTER_SCORES.keys() if ch != "?")


def normalize_letter(ch: str) -> str:
    if not ch:
        return ""
    ch = str(ch).strip()[:1]
    if ch in TR_MAP:
        return TR_MAP[ch]
    return ch.upper().replace("İ", "İ")


def normalize_word(word: str) -> str:
    return "".join(normalize_letter(ch) for ch in str(word) if str(ch).strip())


def is_valid_word(word: str) -> bool:
    return len(word) >= 2 and all(ch in LETTER_SCORES and ch != "?" for ch in word)


class TrieNode:
    __slots__ = ("children", "terminal")

    def __init__(self) -> None:
        self.children: Dict[str, "TrieNode"] = {}
        self.terminal = False


@dataclass
class DictionaryIndex:
    word_set: Set[str]
    words_by_length: Dict[int, List[str]]
    trie: TrieNode
    letters: Tuple[str, ...] = field(default_factory=lambda: TR_LETTERS)


def build_dictionary_index(words: Iterable[str]) -> DictionaryIndex:
    word_set: Set[str] = set()
    words_by_length: Dict[int, List[str]] = {}
    trie = TrieNode()

    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word):
            continue
        if word in word_set:
            continue

        word_set.add(word)
        words_by_length.setdefault(len(word), []).append(word)

        node = trie
        for ch in word:
            node = node.children.setdefault(ch, TrieNode())
        node.terminal = True

    return DictionaryIndex(
        word_set=word_set,
        words_by_length=words_by_length,
        trie=trie,
    )


def get_board_size(board: List[List[dict]]) -> int:
    return len(board)


def in_bounds(board: List[List[dict]], row: int, col: int) -> bool:
    size = get_board_size(board)
    return 0 <= row < size and 0 <= col < size


def get_center(board: List[List[dict]]) -> Tuple[int, int]:
    size = get_board_size(board)
    return size // 2, size // 2


def get_cell(board: List[List[dict]], row: int, col: int):
    return board[row][col]


def get_letter(board: List[List[dict]], row: int, col: int) -> str:
    if not in_bounds(board, row, col):
        return ""
    cell = get_cell(board, row, col)
    if isinstance(cell, dict):
        return normalize_letter(cell.get("letter", ""))
    return normalize_letter(cell)


def get_bonus(board: List[List[dict]], row: int, col: int) -> Optional[str]:
    if not in_bounds(board, row, col):
        return None
    cell = get_cell(board, row, col)
    if isinstance(cell, dict):
        return cell.get("bonus")
    return None


def board_has_tiles(board: List[List[dict]]) -> bool:
    for row in range(len(board)):
        for col in range(len(board[row])):
            if get_letter(board, row, col):
                return True
    return False


def rack_counter(rack: List[str]) -> Counter:
    cnt = Counter()
    for ch in rack:
        n = normalize_letter(ch)
        if n:
            cnt[n] += 1
    return cnt


def get_anchor_cells(board: List[List[dict]]) -> List[Tuple[int, int]]:
    if not board_has_tiles(board):
        return [get_center(board)]

    anchors: Set[Tuple[int, int]] = set()
    for row in range(len(board)):
        for col in range(len(board[row])):
            if get_letter(board, row, col):
                for nr, nc in (
                    (row - 1, col),
                    (row + 1, col),
                    (row, col - 1),
                    (row, col + 1),
                ):
                    if in_bounds(board, nr, nc) and not get_letter(board, nr, nc):
                        anchors.add((nr, nc))

    center = get_center(board)
    return sorted(anchors, key=lambda rc: abs(rc[0] - center[0]) + abs(rc[1] - center[1]))


def before_cell(direction: str, row: int, col: int) -> Tuple[int, int]:
    return (row, col - 1) if direction == DIR_RIGHT else (row - 1, col)


def line_letters(
    board: List[List[dict]], row: int, col: int, direction: str, length: int
) -> Optional[List[str]]:
    out = []
    for i in range(length):
        rr = row + (i if direction == DIR_DOWN else 0)
        cc = col + (i if direction == DIR_RIGHT else 0)
        if not in_bounds(board, rr, cc):
            return None
        out.append(get_letter(board, rr, cc))
    return out


def has_blocking_before_after(
    board: List[List[dict]], row: int, col: int, direction: str, length: int
) -> bool:
    br, bc = before_cell(direction, row, col)
    ar = row + (length if direction == DIR_DOWN else 0)
    ac = col + (length if direction == DIR_RIGHT else 0)

    if in_bounds(board, br, bc) and get_letter(board, br, bc):
        return True
    if in_bounds(board, ar, ac) and get_letter(board, ar, ac):
        return True
    return False


def passes_center(
    row: int, col: int, direction: str, length: int, center: Tuple[int, int]
) -> bool:
    for i in range(length):
        rr = row + (i if direction == DIR_DOWN else 0)
        cc = col + (i if direction == DIR_RIGHT else 0)
        if (rr, cc) == center:
            return True
    return False


def touches_neighbor(board: List[List[dict]], row: int, col: int, direction: str) -> bool:
    neighbors = (
        ((row - 1, col), (row + 1, col))
        if direction == DIR_RIGHT
        else ((row, col - 1), (row, col + 1))
    )
    return any(in_bounds(board, nr, nc) and get_letter(board, nr, nc) for nr, nc in neighbors)


def build_word_coords(
    board: List[List[dict]],
    row: int,
    col: int,
    direction: str,
    placed_map: Dict[Tuple[int, int], str],
) -> List[Tuple[int, int, str]]:
    if direction == DIR_RIGHT:
        dr, dc = 0, 1
    else:
        dr, dc = 1, 0

    rr, cc = row, col
    while in_bounds(board, rr - dr, cc - dc):
        ch = placed_map.get((rr - dr, cc - dc)) or get_letter(board, rr - dr, cc - dc)
        if not ch:
            break
        rr -= dr
        cc -= dc

    coords: List[Tuple[int, int, str]] = []
    while in_bounds(board, rr, cc):
        ch = placed_map.get((rr, cc)) or get_letter(board, rr, cc)
        if not ch:
            break
        coords.append((rr, cc, ch))
        rr += dr
        cc += dc

    return coords


def coords_to_word(coords: List[Tuple[int, int, str]]) -> str:
    return "".join(ch for _, _, ch in coords)


def score_word_coords(
    board: List[List[dict]],
    coords: List[Tuple[int, int, str]],
    newly_placed: Set[Tuple[int, int]],
    joker_map: Dict[Tuple[int, int], bool],
) -> int:
    total = 0
    word_mul = 1

    for row, col, ch in coords:
        is_joker = joker_map.get((row, col), False)

        if is_joker:
            score = 0
        else:
            score = LETTER_SCORES.get(ch, 0)

        if (row, col) in newly_placed:
            bonus = get_bonus(board, row, col)
            if bonus in LETTER_MULTIPLIERS:
                score *= LETTER_MULTIPLIERS[bonus]
            elif bonus in WORD_MULTIPLIERS:
                word_mul *= WORD_MULTIPLIERS[bonus]

        total += score

    return total * word_mul


def perpendicular_fragments(
    board: List[List[dict]], row: int, col: int, direction: str
) -> Tuple[str, str]:
    if direction == DIR_RIGHT:
        dr1, dc1 = -1, 0
        dr2, dc2 = 1, 0
    else:
        dr1, dc1 = 0, -1
        dr2, dc2 = 0, 1

    left = []
    rr, cc = row + dr1, col + dc1
    while in_bounds(board, rr, cc):
        ch = get_letter(board, rr, cc)
        if not ch:
            break
        left.append(ch)
        rr += dr1
        cc += dc1
    left.reverse()

    right = []
    rr, cc = row + dr2, col + dc2
    while in_bounds(board, rr, cc):
        ch = get_letter(board, rr, cc)
        if not ch:
            break
        right.append(ch)
        rr += dr2
        cc += dc2

    return ("".join(left), "".join(right))


def is_cross_valid(
    board: List[List[dict]],
    row: int,
    col: int,
    direction: str,
    ch: str,
    word_set: Set[str],
) -> bool:
    prefix, suffix = perpendicular_fragments(board, row, col, direction)
    if not prefix and not suffix:
        return True
    return f"{prefix}{ch}{suffix}" in word_set


def compute_move_payload(
    board: List[List[dict]],
    word_set: Set[str],
    word: str,
    row: int,
    col: int,
    direction: str,
    joker_positions: Optional[Set[Tuple[int, int]]] = None,
) -> Optional[Dict[str, object]]:
    if joker_positions is None:
        joker_positions = set()

    line = line_letters(board, row, col, direction, len(word))
    if line is None:
        return None
    if has_blocking_before_after(board, row, col, direction, len(word)):
        return None
    if not board_has_tiles(board):
        if not passes_center(row, col, direction, len(word), get_center(board)):
            return None

    placed = []
    placed_map: Dict[Tuple[int, int], str] = {}
    joker_map: Dict[Tuple[int, int], bool] = {}
    newly_placed: Set[Tuple[int, int]] = set()
    interaction = 0
    overlap = 0

    for i, ch in enumerate(word):
        rr = row + (i if direction == DIR_DOWN else 0)
        cc = col + (i if direction == DIR_RIGHT else 0)
        existing = line[i]

        if existing:
            if existing != ch:
                return None
            overlap += 1
            interaction += 1
        else:
            if not is_cross_valid(board, rr, cc, direction, ch, word_set):
                return None

            is_joker = (rr, cc) in joker_positions

            placed.append({
                "row": rr,
                "col": cc,
                "letter": ch,
                "is_joker": is_joker,
            })
            placed_map[(rr, cc)] = ch
            joker_map[(rr, cc)] = is_joker
            newly_placed.add((rr, cc))

            if touches_neighbor(board, rr, cc, direction):
                interaction += 1

    if not placed:
        return None

    if board_has_tiles(board) and interaction == 0 and overlap == 0:
        return None

    main_coords = build_word_coords(board, row, col, direction, placed_map)
    main_word = coords_to_word(main_coords)
    if main_word != word or main_word not in word_set:
        return None

    total_score = score_word_coords(board, main_coords, newly_placed, joker_map)
    cross_words: List[str] = []
    created_words: List[str] = [main_word]
    cross_direction = DIR_DOWN if direction == DIR_RIGHT else DIR_RIGHT

    for tile in placed:
        rr = int(tile["row"])
        cc = int(tile["col"])
        cross_coords = build_word_coords(board, rr, cc, cross_direction, placed_map)
        cross_word = coords_to_word(cross_coords)
        if len(cross_word) > 1:
            if cross_word not in word_set:
                return None
            cross_words.append(cross_word)
            created_words.append(cross_word)
            total_score += score_word_coords(board, cross_coords, {(rr, cc)}, joker_map)

    return {
        "word": word,
        "row": row,
        "col": col,
        "direction": direction,
        "position": f"{direction} · {row + 1} / {col + 1}",
        "score": total_score,
        "placed": placed,
        "createdWords": created_words,
        "crossWords": cross_words,
        "interaction": interaction,
        "overlap": overlap,
    }


class TopCollector:
    def __init__(self, limit: int) -> None:
        self.limit = limit
        self.heap: List[Tuple[Tuple, int, Dict[str, object]]] = []
        self.seen: Set[Tuple[str, int, int, str]] = set()
        self.counter = 0

    def _rank(self, move: Dict[str, object]) -> Tuple:
        return (
            int(move["score"]),
            len(move["placed"]),
            int(move["interaction"]),
            len(move["word"]),
            -int(move["row"]),
            -int(move["col"]),
        )

    def add(self, move: Dict[str, object]) -> None:
        key = (move["word"], move["row"], move["col"], move["direction"])
        if key in self.seen:
            return
        self.seen.add(key)

        rank = self._rank(move)
        self.counter += 1
        entry = (rank, self.counter, move)

        if len(self.heap) < self.limit:
            heapq.heappush(self.heap, entry)
        else:
            if rank > self.heap[0][0]:
                heapq.heapreplace(self.heap, entry)

    def results(self) -> List[Dict[str, object]]:
        items = [item[2] for item in self.heap]
        items.sort(
            key=lambda m: (
                -int(m["score"]),
                -len(m["placed"]),
                -int(m["interaction"]),
                -len(m["word"]),
                m["word"],
                int(m["row"]),
                int(m["col"]),
            )
        )
        return items


def generate_moves(
    board: List[List[dict]],
    rack: List[str],
    index: DictionaryIndex,
    limit: int = 60,
    fast_seconds: float = 1.2,
    deep_seconds: float = 4.5,
) -> List[Dict[str, object]]:
    start_time = time.time()
    rack_cnt = rack_counter(rack)
    anchors = get_anchor_cells(board)
    size = get_board_size(board)
    board_empty = not board_has_tiles(board)

    letters_by_score = tuple(sorted(index.letters, key=lambda ch: (-LETTER_SCORES[ch], ch)))
    max_len = min(size, max(2, len(rack) + (6 if board_empty else 8)))
    max_rack_letters = len(rack)

    def try_emit(
        word: str,
        row: int,
        col: int,
        direction: str,
        collector: TopCollector,
        joker_positions: Set[Tuple[int, int]],
    ) -> None:
        if len(word) < 2 or len(word) > max_len:
            return
        move = compute_move_payload(
            board,
            index.word_set,
            word,
            row,
            col,
            direction,
            joker_positions=joker_positions,
        )
        if move:
            collector.add(move)

    def extend_from_start(
        row: int,
        col: int,
        direction: str,
        anchor: Tuple[int, int],
        collector: TopCollector,
        time_deadline: float,
        max_nodes: int,
    ) -> int:
        nodes = 0

        if direction == DIR_RIGHT:
            step_r, step_c = 0, 1
        else:
            step_r, step_c = 1, 0

        initial_before = before_cell(direction, row, col)
        if in_bounds(board, *initial_before) and get_letter(board, *initial_before):
            return 0

        def dfs(
            rr: int,
            cc: int,
            node: TrieNode,
            rack_now: Counter,
            built: List[str],
            used_tiles: int,
            touched_anchor: bool,
            joker_positions: Set[Tuple[int, int]],
        ) -> bool:
            nonlocal nodes

            if time.time() > time_deadline:
                return True

            nodes += 1
            if nodes > max_nodes:
                return True

            if not in_bounds(board, rr, cc):
                if node.terminal and touched_anchor and used_tiles > 0:
                    try_emit("".join(built), row, col, direction, collector, set(joker_positions))
                return False

            existing = get_letter(board, rr, cc)

            if existing:
                child = node.children.get(existing)
                if child is None:
                    return False

                built.append(existing)
                nr, nc = rr + step_r, cc + step_c

                if child.terminal and touched_anchor and used_tiles > 0:
                    after_has = in_bounds(board, nr, nc) and bool(get_letter(board, nr, nc))
                    if not after_has:
                        try_emit("".join(built), row, col, direction, collector, set(joker_positions))

                stop = dfs(
                    nr,
                    nc,
                    child,
                    rack_now,
                    built,
                    used_tiles,
                    touched_anchor or (rr, cc) == anchor,
                    joker_positions,
                )
                built.pop()
                return stop

            if len(built) + 1 > max_len:
                return False

            for ch in letters_by_score:
                child = node.children.get(ch)
                if child is None:
                    continue

                used_joker = False
                added_joker_pos = False

                if rack_now.get(ch, 0) > 0:
                    rack_now[ch] -= 1
                    if rack_now[ch] == 0:
                        del rack_now[ch]
                elif rack_now.get("?", 0) > 0:
                    rack_now["?"] -= 1
                    if rack_now["?"] == 0:
                        del rack_now["?"]
                    used_joker = True
                    joker_positions.add((rr, cc))
                    added_joker_pos = True
                else:
                    continue

                built.append(ch)
                nr, nc = rr + step_r, cc + step_c

                next_used_tiles = used_tiles + 1
                next_touched_anchor = touched_anchor or (rr, cc) == anchor

                if child.terminal and next_touched_anchor and next_used_tiles > 0:
                    after_has = in_bounds(board, nr, nc) and bool(get_letter(board, nr, nc))
                    if not after_has:
                        try_emit("".join(built), row, col, direction, collector, set(joker_positions))

                stop = dfs(
                    nr,
                    nc,
                    child,
                    rack_now,
                    built,
                    next_used_tiles,
                    next_touched_anchor,
                    joker_positions,
                )
                built.pop()

                if added_joker_pos:
                    joker_positions.remove((rr, cc))

                if used_joker:
                    rack_now["?"] += 1
                else:
                    rack_now[ch] += 1

                if stop:
                    return True

            return False

        dfs(row, col, index.trie, rack_cnt.copy(), [], 0, False, set())
        return nodes

    def run_pass(time_budget: float, max_nodes: int, collector: TopCollector) -> None:
        deadline = time.time() + time_budget
        visited_starts: Set[Tuple[int, int, str]] = set()

        for anchor in anchors:
            if time.time() > deadline:
                break

            for direction in (DIR_RIGHT, DIR_DOWN):
                if time.time() > deadline:
                    break

                if direction == DIR_RIGHT:
                    back_step_r, back_step_c = 0, -1
                else:
                    back_step_r, back_step_c = -1, 0

                start_candidates = []

                rr, cc = anchor
                start_candidates.append((rr, cc))

                temp_r, temp_c = rr, cc
                for _ in range(max_rack_letters):
                    pr, pc = temp_r + back_step_r, temp_c + back_step_c
                    if not in_bounds(board, pr, pc):
                        break
                    if get_letter(board, pr, pc):
                        break
                    start_candidates.append((pr, pc))
                    temp_r, temp_c = pr, pc

                start_candidates.sort(
                    key=lambda rc: abs(rc[0] - anchor[0]) + abs(rc[1] - anchor[1])
                )

                for start in start_candidates:
                    if time.time() > deadline:
                        break

                    key = (start[0], start[1], direction)
                    if key in visited_starts:
                        continue
                    visited_starts.add(key)

                    extend_from_start(
                        start[0],
                        start[1],
                        direction,
                        anchor,
                        collector,
                        deadline,
                        max_nodes=max_nodes,
                    )

    collector = TopCollector(limit=max(20, limit))

    run_pass(time_budget=fast_seconds, max_nodes=18000, collector=collector)

    remaining = deep_seconds - (time.time() - start_time)
    if remaining > 0:
        run_pass(time_budget=remaining, max_nodes=120000, collector=collector)

    return collector.results()[:limit]
