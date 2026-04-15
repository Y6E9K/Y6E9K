from __future__ import annotations

import time
from collections import Counter
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
    "A": 1, "B": 3, "C": 4, "Ç": 4, "D": 3, "E": 1, "F": 7, "G": 5, "Ğ": 8,
    "H": 5, "I": 2, "İ": 1, "J": 10, "K": 1, "L": 1, "M": 2, "N": 1, "O": 2,
    "Ö": 7, "P": 5, "R": 1, "S": 2, "Ş": 4, "T": 1, "U": 2, "Ü": 3, "V": 7,
    "Y": 3, "Z": 4, "?": 0,
}

WORD_MULTIPLIERS = {"K2": 2, "K3": 3, "START": 2}
LETTER_MULTIPLIERS = {"H2": 2, "H3": 3}


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
    return len(word) >= 2 and all(ch in LETTER_SCORES for ch in word)


def get_board_size(board: List[List[dict]]) -> int:
    return len(board)


def in_bounds(board: List[List[dict]], row: int, col: int) -> bool:
    size = get_board_size(board)
    return 0 <= row < size and 0 <= col < size


def get_center(board: List[List[dict]]) -> Tuple[int, int]:
    s = get_board_size(board)
    return s // 2, s // 2


def get_cell(board: List[List[dict]], row: int, col: int) -> dict:
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
    for r in range(len(board)):
        for c in range(len(board[r])):
            if get_letter(board, r, c):
                return True
    return False


def rack_counter(rack: List[str]) -> Counter:
    result = Counter()
    for ch in rack:
        n = normalize_letter(ch)
        if n:
            result[n] += 1
    return result


def board_counter(board: List[List[dict]]) -> Counter:
    result = Counter()
    for r in range(len(board)):
        for c in range(len(board[r])):
            ch = get_letter(board, r, c)
            if ch:
                result[ch] += 1
    return result


def dictionary_index(dictionary: Iterable[str]) -> Tuple[List[str], Set[str], Dict[int, List[str]]]:
    words: List[str] = []
    word_set: Set[str] = set()
    words_by_length: Dict[int, List[str]] = {}

    for raw in dictionary:
        word = normalize_word(raw)
        if not is_valid_word(word):
            continue
        if word in word_set:
            continue
        word_set.add(word)
        words.append(word)
        words_by_length.setdefault(len(word), []).append(word)

    return words, word_set, words_by_length


def candidate_possible(word: str, rack: Counter, board_letters: Counter) -> bool:
    available = rack + board_letters
    need = Counter(word)
    return all(available[ch] >= cnt for ch, cnt in need.items())


def get_anchor_cells(board: List[List[dict]]) -> Set[Tuple[int, int]]:
    anchors: Set[Tuple[int, int]] = set()

    if not board_has_tiles(board):
        anchors.add(get_center(board))
        return anchors

    for r in range(len(board)):
        for c in range(len(board[r])):
            if get_letter(board, r, c):
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if in_bounds(board, nr, nc) and not get_letter(board, nr, nc):
                        anchors.add((nr, nc))
    return anchors


def starts_for_anchor(anchor_row: int, anchor_col: int, word_len: int, direction: str) -> List[Tuple[int, int]]:
    starts = []
    for i in range(word_len):
        row = anchor_row - (i if direction == DIR_DOWN else 0)
        col = anchor_col - (i if direction == DIR_RIGHT else 0)
        starts.append((row, col))
    return starts


def line_letters(board: List[List[dict]], row: int, col: int, direction: str, length: int) -> Optional[List[str]]:
    out = []
    for i in range(length):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        if not in_bounds(board, r, c):
            return None
        out.append(get_letter(board, r, c))
    return out


def has_blocking_before_after(board: List[List[dict]], row: int, col: int, direction: str, length: int) -> bool:
    dr, dc = (0, 1) if direction == DIR_RIGHT else (1, 0)

    br, bc = row - dr, col - dc
    ar, ac = row + dr * length, col + dc * length

    if in_bounds(board, br, bc) and get_letter(board, br, bc):
        return True
    if in_bounds(board, ar, ac) and get_letter(board, ar, ac):
        return True
    return False


def passes_center(row: int, col: int, direction: str, length: int, center: Tuple[int, int]) -> bool:
    cr, cc = center
    for i in range(length):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        if (r, c) == (cr, cc):
            return True
    return False


def touches_neighbor(board: List[List[dict]], row: int, col: int, direction: str) -> bool:
    neighbors = (
        ((row - 1, col), (row + 1, col))
        if direction == DIR_RIGHT
        else ((row, col - 1), (row, col + 1))
    )
    for nr, nc in neighbors:
        if in_bounds(board, nr, nc) and get_letter(board, nr, nc):
            return True
    return False


def build_word_coords(
    board: List[List[dict]],
    row: int,
    col: int,
    direction: str,
    placed_map: Dict[Tuple[int, int], str],
) -> List[Tuple[int, int, str]]:
    dr, dc = (0, 1) if direction == DIR_RIGHT else (1, 0)

    r, c = row, col
    while in_bounds(board, r - dr, c - dc):
        ch = placed_map.get((r - dr, c - dc)) or get_letter(board, r - dr, c - dc)
        if not ch:
            break
        r -= dr
        c -= dc

    coords: List[Tuple[int, int, str]] = []
    while in_bounds(board, r, c):
        ch = placed_map.get((r, c)) or get_letter(board, r, c)
        if not ch:
            break
        coords.append((r, c, ch))
        r += dr
        c += dc

    return coords


def coords_to_word(coords: List[Tuple[int, int, str]]) -> str:
    return "".join(ch for _, _, ch in coords)


def score_word_coords(
    board: List[List[dict]],
    coords: List[Tuple[int, int, str]],
    newly_placed: Set[Tuple[int, int]],
) -> int:
    total = 0
    word_mul = 1

    for r, c, ch in coords:
        score = LETTER_SCORES.get(ch, 0)
        if (r, c) in newly_placed:
            bonus = get_bonus(board, r, c)
            if bonus in LETTER_MULTIPLIERS:
                score *= LETTER_MULTIPLIERS[bonus]
            elif bonus in WORD_MULTIPLIERS:
                word_mul *= WORD_MULTIPLIERS[bonus]
        total += score

    return total * word_mul


def can_consume_from_rack(word: str, line: List[str], rack: Counter) -> bool:
    need = Counter()
    jokers = rack.get("?", 0)

    for ch, existing in zip(word, line):
        if existing:
            if existing != ch:
                return False
        else:
            need[ch] += 1

    missing = 0
    for ch, cnt in need.items():
        have = rack.get(ch, 0)
        if have < cnt:
            missing += cnt - have

    return missing <= jokers


def validate_move(
    board: List[List[dict]],
    word_set: Set[str],
    word: str,
    row: int,
    col: int,
    direction: str,
    rack: Counter,
) -> Optional[Dict[str, object]]:
    line = line_letters(board, row, col, direction, len(word))
    if line is None:
        return None

    if has_blocking_before_after(board, row, col, direction, len(word)):
        return None

    if not can_consume_from_rack(word, line, rack):
        return None

    placed = []
    placed_map: Dict[Tuple[int, int], str] = {}
    newly_placed: Set[Tuple[int, int]] = set()
    interaction = 0
    overlap = 0

    for i, ch in enumerate(word):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        existing = line[i]

        if existing:
            if existing != ch:
                return None
            overlap += 1
            interaction += 1
        else:
            placed.append({"row": r, "col": c, "letter": ch})
            placed_map[(r, c)] = ch
            newly_placed.add((r, c))
            if touches_neighbor(board, r, c, direction):
                interaction += 1

    if not placed:
        return None

    if board_has_tiles(board):
        if interaction == 0 and overlap == 0:
            return None
    else:
        if not passes_center(row, col, direction, len(word), get_center(board)):
            return None

    main_coords = build_word_coords(board, row, col, direction, placed_map)
    main_word = coords_to_word(main_coords)
    if main_word != word or main_word not in word_set:
        return None

    total_score = score_word_coords(board, main_coords, newly_placed)
    cross_words: List[str] = []
    created_words: List[str] = [main_word]

    cross_dir = DIR_DOWN if direction == DIR_RIGHT else DIR_RIGHT

    for tile in placed:
        r = int(tile["row"])
        c = int(tile["col"])
        cross_coords = build_word_coords(board, r, c, cross_dir, placed_map)
        cross_word = coords_to_word(cross_coords)
        if len(cross_word) > 1:
            if cross_word not in word_set:
                return None
            cross_words.append(cross_word)
            created_words.append(cross_word)
            total_score += score_word_coords(board, cross_coords, {(r, c)})

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


def generate_moves(
    board: List[List[dict]],
    rack: List[str],
    dictionary: Iterable[str],
    limit: int = 20,
) -> List[Dict[str, object]]:
    start_time = time.time()
    time_limit = 6.0
    max_checks = 30000
    checks = 0

    _, word_set, words_by_length = dictionary_index(dictionary)

    rack_cnt = rack_counter(rack)
    board_cnt = board_counter(board)
    anchors = get_anchor_cells(board)

    max_word_len = min(get_board_size(board), len(rack) + 8)
    candidate_lengths = sorted(k for k in words_by_length.keys() if 2 <= k <= max_word_len)

    candidate_words: List[str] = []
    for ln in candidate_lengths:
        for word in words_by_length.get(ln, []):
            if candidate_possible(word, rack_cnt, board_cnt):
                candidate_words.append(word)

    moves: List[Dict[str, object]] = []
    tried = set()

    stop = False
    for word in candidate_words:
        if stop:
            break
        for direction in (DIR_RIGHT, DIR_DOWN):
            if stop:
                break
            for ar, ac in anchors:
                if stop:
                    break
                for row, col in starts_for_anchor(ar, ac, len(word), direction):
                    checks += 1
                    if checks >= max_checks or (time.time() - start_time) > time_limit:
                        stop = True
                        break

                    key = (word, row, col, direction)
                    if key in tried:
                        continue
                    tried.add(key)

                    move = validate_move(
                        board=board,
                        word_set=word_set,
                        word=word,
                        row=row,
                        col=col,
                        direction=direction,
                        rack=rack_cnt,
                    )
                    if move:
                        moves.append(move)

    moves.sort(
        key=lambda m: (
            -m["score"],
            -len(m["placed"]),
            -m["interaction"],
            -len(m["word"]),
            m["word"],
            m["row"],
            m["col"],
        )
    )

    unique: List[Dict[str, object]] = []
    seen = set()
    for move in moves:
        key = (move["word"], move["row"], move["col"], move["direction"])
        if key in seen:
            continue
        seen.add(key)
        unique.append(move)
        if len(unique) >= limit:
            break

    return unique
