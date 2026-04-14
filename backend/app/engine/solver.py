from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

DIR_RIGHT = "YATAY"
DIR_DOWN = "DIKEY"

TR_UPPER_MAP = str.maketrans(
    {
        "a": "A",
        "b": "B",
        "c": "C",
        "ç": "Ç",
        "d": "D",
        "e": "E",
        "f": "F",
        "g": "G",
        "ğ": "Ğ",
        "h": "H",
        "ı": "I",
        "i": "İ",
        "j": "J",
        "k": "K",
        "l": "L",
        "m": "M",
        "n": "N",
        "o": "O",
        "ö": "Ö",
        "p": "P",
        "r": "R",
        "s": "S",
        "ş": "Ş",
        "t": "T",
        "u": "U",
        "ü": "Ü",
        "v": "V",
        "y": "Y",
        "z": "Z",
        "q": "Q",
        "w": "W",
        "x": "X",
    }
)

TR_LOWER_MAP = str.maketrans(
    {
        "A": "a",
        "B": "b",
        "C": "c",
        "Ç": "ç",
        "D": "d",
        "E": "e",
        "F": "f",
        "G": "g",
        "Ğ": "ğ",
        "H": "h",
        "I": "ı",
        "İ": "i",
        "J": "j",
        "K": "k",
        "L": "l",
        "M": "m",
        "N": "n",
        "O": "o",
        "Ö": "ö",
        "P": "p",
        "R": "r",
        "S": "s",
        "Ş": "ş",
        "T": "t",
        "U": "u",
        "Ü": "ü",
        "V": "v",
        "Y": "y",
        "Z": "z",
    }
)

TR_LETTERS = set("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ?")

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

LETTER_MULTIPLIERS = {"H2": 2, "H3": 3}
WORD_MULTIPLIERS = {"K2": 2, "K3": 3, "START": 2}


@dataclass
class Move:
    word: str
    row: int
    col: int
    direction: str
    score: int
    placed: List[Dict[str, object]]
    createdWords: List[str]
    crossWords: List[str]
    interaction: int
    overlap: int


def tr_upper(text: str) -> str:
    return str(text).translate(TR_UPPER_MAP).upper()


def tr_lower(text: str) -> str:
    return str(text).translate(TR_LOWER_MAP).lower()


def normalize_letter(ch: str) -> str:
    if not ch:
        return ""
    return tr_upper(str(ch)[0])


def normalize_word(word: str) -> str:
    return "".join(normalize_letter(c) for c in str(word) if str(c).strip())


def is_valid_word(word: str) -> bool:
    return len(word) >= 2 and all(c in TR_LETTERS and c != "?" for c in word)


def get_board_size(board: List[List[dict]]) -> int:
    return len(board)


def get_center(board: List[List[dict]]) -> Tuple[int, int]:
    size = get_board_size(board)
    return size // 2, size // 2


def in_bounds(board: List[List[dict]], row: int, col: int) -> bool:
    size = get_board_size(board)
    return 0 <= row < size and 0 <= col < size


def get_cell(board: List[List[dict]], row: int, col: int) -> dict:
    if not in_bounds(board, row, col):
        return {"letter": "", "bonus": None}
    cell = board[row][col]
    if isinstance(cell, dict):
        return {"letter": normalize_letter(cell.get("letter", "") or ""), "bonus": cell.get("bonus")}
    return {"letter": normalize_letter(cell or ""), "bonus": None}


def get_cell_letter(board: List[List[dict]], row: int, col: int) -> str:
    return get_cell(board, row, col)["letter"]


def get_cell_bonus(board: List[List[dict]], row: int, col: int) -> Optional[str]:
    return get_cell(board, row, col).get("bonus")


def has_any_tiles(board: List[List[dict]]) -> bool:
    for row in board:
        for cell in row:
            if isinstance(cell, dict):
                if str(cell.get("letter", "") or "").strip():
                    return True
            elif str(cell or "").strip():
                return True
    return False


def iter_dictionary_words(dictionary: Iterable[str]) -> List[str]:
    words: List[str] = []
    seen: Set[str] = set()
    for raw in dictionary:
        word = normalize_word(str(raw))
        if word in seen:
            continue
        if not is_valid_word(word):
            continue
        seen.add(word)
        words.append(word)
    return words


def rack_counter(rack: List[str]) -> Counter:
    return Counter(normalize_letter(x) for x in rack if str(x).strip())


def board_letters_counter(board: List[List[dict]]) -> Counter:
    result = Counter()
    for r in range(len(board)):
        for c in range(len(board[r])):
            ch = get_cell_letter(board, r, c)
            if ch:
                result[ch] += 1
    return result


def candidate_word_possible(word: str, rack: Counter, board_letters: Counter) -> bool:
    available = rack + board_letters
    joker_count = available.get("?", 0)
    deficit = 0
    for ch, count in Counter(word).items():
        have = available.get(ch, 0)
        if have < count:
            deficit += count - have
    return deficit <= joker_count


def board_main_word(board, row, col, direction, placed_letters):
    dr, dc = (0, 1) if direction == DIR_RIGHT else (1, 0)

    r, c = row, col
    while in_bounds(board, r - dr, c - dc):
        prev = placed_letters.get((r - dr, c - dc), {}).get("letter") or get_cell_letter(board, r - dr, c - dc)
        if not prev:
            break
        r -= dr
        c -= dc

    chars = []
    while in_bounds(board, r, c):
        ch = placed_letters.get((r, c), {}).get("letter") or get_cell_letter(board, r, c)
        if not ch:
            break
        chars.append(ch)
        r += dr
        c += dc
    return "".join(chars)


def build_cross_word(board, row, col, letter, direction, placed_letters):
    if direction == DIR_RIGHT:
        dr, dc = 1, 0
    else:
        dr, dc = 0, 1

    r, c = row, col
    while in_bounds(board, r - dr, c - dc):
        prev = placed_letters.get((r - dr, c - dc), {}).get("letter") or get_cell_letter(board, r - dr, c - dc)
        if not prev:
            break
        r -= dr
        c -= dc

    chars = []
    while in_bounds(board, r, c):
        if r == row and c == col:
            ch = letter
        else:
            ch = placed_letters.get((r, c), {}).get("letter") or get_cell_letter(board, r, c)
        if not ch:
            break
        chars.append(ch)
        r += dr
        c += dc

    return "".join(chars)


def touches_existing_neighbors(board, row, col, direction):
    if direction == DIR_RIGHT:
        neighbors = [(row - 1, col), (row + 1, col)]
    else:
        neighbors = [(row, col - 1), (row, col + 1)]

    return any(get_cell_letter(board, r, c) for r, c in neighbors if in_bounds(board, r, c))


def word_passes_center(word_len, row, col, direction, center):
    cr, cc = center
    for i in range(word_len):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        if (r, c) == (cr, cc):
            return True
    return False


def collect_line_letters(board, row, col, direction, word_len):
    letters = []
    for i in range(word_len):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        if not in_bounds(board, r, c):
            return None
        letters.append(get_cell_letter(board, r, c))
    return letters


def has_blocking_prefix_suffix(board, row, col, direction, word_len):
    dr, dc = (0, 1) if direction == DIR_RIGHT else (1, 0)

    before_r, before_c = row - dr, col - dc
    after_r, after_c = row + dr * word_len, col + dc * word_len

    if in_bounds(board, before_r, before_c) and get_cell_letter(board, before_r, before_c):
        return True
    if in_bounds(board, after_r, after_c) and get_cell_letter(board, after_r, after_c):
        return True
    return False


def get_anchor_cells(board: List[List[dict]]) -> Set[Tuple[int, int]]:
    anchors: Set[Tuple[int, int]] = set()

    if not has_any_tiles(board):
        anchors.add(get_center(board))
        return anchors

    size = get_board_size(board)
    for r in range(size):
        for c in range(size):
            if get_cell_letter(board, r, c):
                for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
                    if in_bounds(board, nr, nc) and not get_cell_letter(board, nr, nc):
                        anchors.add((nr, nc))
    return anchors


def possible_starts_for_anchor(word_len: int, anchor_row: int, anchor_col: int, direction: str) -> List[Tuple[int, int]]:
    starts = []
    for i in range(word_len):
        row = anchor_row - (i if direction == DIR_DOWN else 0)
        col = anchor_col - (i if direction == DIR_RIGHT else 0)
        starts.append((row, col))
    return starts


def assign_rack_usage(word: str, line_letters: List[str], rack: Counter) -> Optional[Dict[int, bool]]:
    remaining = rack.copy()
    joker_positions: Dict[int, bool] = {}

    for i, ch in enumerate(word):
        existing = line_letters[i]
        if existing:
            if existing != ch:
                return None
            continue

        if remaining.get(ch, 0) > 0:
            remaining[ch] -= 1
            joker_positions[i] = False
        elif remaining.get("?", 0) > 0:
            remaining["?"] -= 1
            joker_positions[i] = True
        else:
            return None

    return joker_positions


def letter_score(letter: str, is_joker: bool = False) -> int:
    if is_joker:
        return 0
    return LETTER_SCORES.get(letter, 0)


def score_word_with_placements(
    board: List[List[dict]],
    coords: List[Tuple[int, int]],
    placed_info: Dict[Tuple[int, int], Dict[str, object]],
) -> int:
    word_multiplier = 1
    total = 0

    for row, col in coords:
        existing_letter = get_cell_letter(board, row, col)
        placed = placed_info.get((row, col))

        if placed:
            ch = str(placed["letter"])
            is_joker = bool(placed.get("joker", False))
            bonus = get_cell_bonus(board, row, col)
            l_mult = LETTER_MULTIPLIERS.get(str(bonus), 1)
            w_mult = WORD_MULTIPLIERS.get(str(bonus), 1)
            total += letter_score(ch, is_joker) * l_mult
            word_multiplier *= w_mult
        else:
            total += letter_score(existing_letter, False)

    return total * word_multiplier


def collect_word_coords(board, row, col, direction, placed_letters):
    dr, dc = (0, 1) if direction == DIR_RIGHT else (1, 0)

    r, c = row, col
    while in_bounds(board, r - dr, c - dc):
        prev = placed_letters.get((r - dr, c - dc), {}).get("letter") or get_cell_letter(board, r - dr, c - dc)
        if not prev:
            break
        r -= dr
        c -= dc

    coords = []
    while in_bounds(board, r, c):
        ch = placed_letters.get((r, c), {}).get("letter") or get_cell_letter(board, r, c)
        if not ch:
            break
        coords.append((r, c))
        r += dr
        c += dc
    return coords


def validate_move(board, dictionary_set, word, row, col, direction, rack):
    line_letters = collect_line_letters(board, row, col, direction, len(word))
    if line_letters is None:
        return None

    if has_blocking_prefix_suffix(board, row, col, direction, len(word)):
        return None

    joker_positions = assign_rack_usage(word, line_letters, rack)
    if joker_positions is None:
        return None

    placed: List[Dict[str, object]] = []
    placed_map: Dict[Tuple[int, int], Dict[str, object]] = {}

    interaction = 0
    overlap = 0

    for i, ch in enumerate(word):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        existing = line_letters[i]

        if existing:
            if existing != ch:
                return None
            overlap += 1
            interaction += 1
        else:
            info = {"row": r, "col": c, "letter": ch, "joker": bool(joker_positions.get(i, False))}
            placed.append(info)
            placed_map[(r, c)] = info
            if touches_existing_neighbors(board, r, c, direction):
                interaction += 1

    if not placed:
        return None

    if has_any_tiles(board):
        if interaction == 0 and overlap == 0:
            return None
    else:
        if not word_passes_center(len(word), row, col, direction, get_center(board)):
            return None

    main_word = board_main_word(board, row, col, direction, placed_map)
    if main_word != word:
        return None
    if main_word not in dictionary_set:
        return None

    cross_words: List[str] = []
    created_words: List[str] = [main_word]

    main_coords = collect_word_coords(board, row, col, direction, placed_map)
    total_score = score_word_with_placements(board, main_coords, placed_map)

    for tile in placed:
        cross = build_cross_word(
            board,
            int(tile["row"]),
            int(tile["col"]),
            str(tile["letter"]),
            direction,
            placed_map,
        )
        if len(cross) > 1:
            if cross not in dictionary_set:
                return None
            cross_words.append(cross)
            created_words.append(cross)

            cross_direction = DIR_DOWN if direction == DIR_RIGHT else DIR_RIGHT
            cross_coords = collect_word_coords(board, int(tile["row"]), int(tile["col"]), cross_direction, placed_map)
            total_score += score_word_with_placements(board, cross_coords, placed_map)

    clean_placed = [
        {"row": int(item["row"]), "col": int(item["col"]), "letter": str(item["letter"]), "joker": bool(item["joker"])}
        for item in placed
    ]

    return Move(
        word=word,
        row=row,
        col=col,
        direction=direction,
        score=total_score,
        placed=clean_placed,
        createdWords=created_words,
        crossWords=cross_words,
        interaction=interaction,
        overlap=overlap,
    )


def generate_moves(board: List[List[dict]], rack: List[str], dictionary: Iterable[str], limit: int = 120) -> List[Dict[str, object]]:
    dictionary_words = iter_dictionary_words(dictionary)
    dictionary_set = set(dictionary_words)
    rack_count = rack_counter(rack)
    board_counter = board_letters_counter(board)
    anchors = get_anchor_cells(board)

    moves: List[Move] = []
    seen_try = set()

    filtered_words = [
        word for word in dictionary_words if candidate_word_possible(word, rack_count, board_counter)
    ]

    for word in filtered_words:
        for direction in (DIR_RIGHT, DIR_DOWN):
            for anchor_row, anchor_col in anchors:
                for row, col in possible_starts_for_anchor(len(word), anchor_row, anchor_col, direction):
                    key = (word, row, col, direction)
                    if key in seen_try:
                        continue
                    seen_try.add(key)

                    move = validate_move(
                        board=board,
                        dictionary_set=dictionary_set,
                        word=word,
                        row=row,
                        col=col,
                        direction=direction,
                        rack=rack_count,
                    )
                    if move:
                        moves.append(move)

    moves.sort(
        key=lambda m: (
            -m.score,
            -len(m.placed),
            -m.interaction,
            -len(m.word),
            m.word,
            m.row,
            m.col,
        )
    )

    unique = []
    seen = set()
    for move in moves:
        key = (move.word, move.row, move.col, move.direction)
        if key in seen:
            continue
        seen.add(key)
        unique.append(
            {
                "word": move.word,
                "row": move.row,
                "col": move.col,
                "direction": move.direction,
                "position": f"{move.direction} · {move.row + 1} / {move.col + 1}",
                "score": move.score,
                "placed": move.placed,
                "createdWords": move.createdWords,
                "crossWords": move.crossWords,
                "interaction": move.interaction,
                "overlap": move.overlap,
            }
        )
        if len(unique) >= limit:
            break

    return unique
