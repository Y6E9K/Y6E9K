from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Iterable, List, Dict, Tuple, Set, Optional


TR_LETTERS = set("ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ")
DIR_RIGHT = "YATAY"
DIR_DOWN = "DIKEY"


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


def normalize_letter(ch: str) -> str:
    return ch[:1].upper().replace("İ", "İ")


def normalize_word(word: str) -> str:
    return "".join(normalize_letter(c) for c in word if c.strip())


def is_valid_word(word: str) -> bool:
    return len(word) >= 2 and all(c in TR_LETTERS for c in word)


def get_board_size(board: List[List[dict]]) -> int:
    return len(board)


def get_center(board: List[List[dict]]) -> Tuple[int, int]:
    size = get_board_size(board)
    return size // 2, size // 2


def in_bounds(board: List[List[dict]], row: int, col: int) -> bool:
    size = get_board_size(board)
    return 0 <= row < size and 0 <= col < size


def get_cell_letter(board: List[List[dict]], row: int, col: int) -> str:
    if not in_bounds(board, row, col):
        return ""
    cell = board[row][col]
    if isinstance(cell, dict):
        return normalize_letter(str(cell.get("letter", "") or ""))
    return normalize_letter(str(cell or ""))


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
    words = []
    seen = set()

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
    cleaned = [normalize_letter(x) for x in rack if str(x).strip()]
    return Counter(cleaned)


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
    need = Counter(word)
    return all(available[ch] >= count for ch, count in need.items())


def board_main_word(
    board: List[List[dict]],
    row: int,
    col: int,
    direction: str,
    placed_letters: Dict[Tuple[int, int], str],
) -> str:
    dr, dc = (0, 1) if direction == DIR_RIGHT else (1, 0)

    r, c = row, col
    while in_bounds(board, r - dr, c - dc):
        prev = placed_letters.get((r - dr, c - dc)) or get_cell_letter(board, r - dr, c - dc)
        if not prev:
            break
        r -= dr
        c -= dc

    chars: List[str] = []
    while in_bounds(board, r, c):
        ch = placed_letters.get((r, c)) or get_cell_letter(board, r, c)
        if not ch:
            break
        chars.append(ch)
        r += dr
        c += dc

    return "".join(chars)


def build_cross_word(
    board: List[List[dict]],
    row: int,
    col: int,
    letter: str,
    direction: str,
    placed_letters: Dict[Tuple[int, int], str],
) -> str:
    if direction == DIR_RIGHT:
        dr, dc = 1, 0
    else:
        dr, dc = 0, 1

    r, c = row, col
    while in_bounds(board, r - dr, c - dc):
        prev = placed_letters.get((r - dr, c - dc)) or get_cell_letter(board, r - dr, c - dc)
        if not prev:
            break
        r -= dr
        c -= dc

    chars: List[str] = []
    while in_bounds(board, r, c):
        if r == row and c == col:
            ch = letter
        else:
            ch = placed_letters.get((r, c)) or get_cell_letter(board, r, c)
        if not ch:
            break
        chars.append(ch)
        r += dr
        c += dc

    return "".join(chars)


def touches_existing_neighbors(
    board: List[List[dict]],
    row: int,
    col: int,
    direction: str,
) -> bool:
    if direction == DIR_RIGHT:
        neighbors = [(row - 1, col), (row + 1, col)]
    else:
        neighbors = [(row, col - 1), (row, col + 1)]

    return any(get_cell_letter(board, r, c) for r, c in neighbors if in_bounds(board, r, c))


def word_passes_center(word_len: int, row: int, col: int, direction: str, center: Tuple[int, int]) -> bool:
    cr, cc = center
    for i in range(word_len):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        if (r, c) == (cr, cc):
            return True
    return False


def can_build_with_rack(word: str, board_letters: List[str], rack: Counter) -> bool:
    needed = Counter()
    for ch, existing in zip(word, board_letters):
        if not existing:
            needed[ch] += 1
        elif existing != ch:
            return False
    return all(rack[ch] >= count for ch, count in needed.items())


def collect_line_letters(
    board: List[List[dict]],
    row: int,
    col: int,
    direction: str,
    word_len: int,
) -> Optional[List[str]]:
    letters: List[str] = []
    for i in range(word_len):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        if not in_bounds(board, r, c):
            return None
        letters.append(get_cell_letter(board, r, c))
    return letters


def has_blocking_prefix_suffix(
    board: List[List[dict]],
    row: int,
    col: int,
    direction: str,
    word_len: int,
) -> bool:
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


def possible_starts_for_anchor(
    word_len: int,
    anchor_row: int,
    anchor_col: int,
    direction: str,
) -> List[Tuple[int, int]]:
    starts = []
    for i in range(word_len):
        row = anchor_row - (i if direction == DIR_DOWN else 0)
        col = anchor_col - (i if direction == DIR_RIGHT else 0)
        starts.append((row, col))
    return starts


def validate_move(
    board: List[List[dict]],
    dictionary_set: Set[str],
    word: str,
    row: int,
    col: int,
    direction: str,
    rack: Counter,
) -> Optional[Move]:
    line_letters = collect_line_letters(board, row, col, direction, len(word))
    if line_letters is None:
        return None

    if has_blocking_prefix_suffix(board, row, col, direction, len(word)):
        return None

    if not can_build_with_rack(word, line_letters, rack):
        return None

    placed: List[Dict[str, object]] = []
    placed_map: Dict[Tuple[int, int], str] = {}

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
            placed.append({"row": r, "col": c, "letter": ch})
            placed_map[(r, c)] = ch
            if touches_existing_neighbors(board, r, c, direction):
                interaction += 1

    if not placed:
        return None

    board_has_tiles_now = has_any_tiles(board)
    if board_has_tiles_now:
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

    score = len(word) + sum(len(w) for w in cross_words)

    return Move(
        word=word,
        row=row,
        col=col,
        direction=direction,
        score=score,
        placed=placed,
        createdWords=created_words,
        crossWords=cross_words,
        interaction=interaction,
        overlap=overlap,
    )


def generate_moves(
    board: List[List[dict]],
    rack: List[str],
    dictionary: Iterable[str],
    limit: int = 120,
) -> List[Dict[str, object]]:
    dictionary_words = iter_dictionary_words(dictionary)
    dictionary_set = set(dictionary_words)
    rack_count = rack_counter(rack)
    board_counter = board_letters_counter(board)
    anchors = get_anchor_cells(board)

    moves: List[Move] = []
    seen_try = set()

    filtered_words = [
        word
        for word in dictionary_words
        if candidate_word_possible(word, rack_count, board_counter)
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
