from __future__ import annotations

import time
from collections import Counter, defaultdict
from dataclasses import dataclass
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


@dataclass(frozen=True)
class WordEntry:
    word: str
    uniq: frozenset
    counter: Counter
    score: int
    length: int


@dataclass
class DictionaryIndex:
    word_set: Set[str]
    words: List[str]
    by_length: Dict[int, List[WordEntry]]
    sample_words: List[str]


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


def build_dictionary_index(words: Iterable[str]) -> DictionaryIndex:
    word_set: Set[str] = set()
    clean_words: List[str] = []
    by_length: Dict[int, List[WordEntry]] = defaultdict(list)

    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word) or word in word_set:
            continue

        word_set.add(word)
        clean_words.append(word)
        entry = WordEntry(
            word=word,
            uniq=frozenset(word),
            counter=Counter(word),
            score=sum(LETTER_SCORES.get(ch, 0) for ch in word),
            length=len(word),
        )
        by_length[len(word)].append(entry)

    clean_words.sort()
    for length in by_length:
        by_length[length].sort(key=lambda e: (-e.score, -e.length, e.word))

    return DictionaryIndex(
        word_set=word_set,
        words=clean_words,
        by_length=dict(by_length),
        sample_words=clean_words[:50],
    )


def board_size(board: List[List[Any]]) -> int:
    return len(board)


def in_bounds(board: List[List[Any]], r: int, c: int) -> bool:
    n = board_size(board)
    return 0 <= r < n and 0 <= c < n


def get_cell(board: List[List[Any]], r: int, c: int):
    return board[r][c]


def get_letter(board: List[List[Any]], r: int, c: int) -> Optional[str]:
    if not in_bounds(board, r, c):
        return None

    cell = get_cell(board, r, c)

    if isinstance(cell, dict):
        ch = normalize_letter(cell.get("letter", ""))
        return ch or None

    ch = normalize_letter(cell)
    return ch or None


def get_bonus(board: List[List[Any]], r: int, c: int) -> Optional[str]:
    if not in_bounds(board, r, c):
        return None

    cell = get_cell(board, r, c)
    if isinstance(cell, dict):
        return cell.get("bonus")
    return None


def board_is_empty(board: List[List[Any]]) -> bool:
    n = board_size(board)
    return all(get_letter(board, r, c) is None for r in range(n) for c in range(n))


def board_has_letters(board: List[List[Any]]) -> bool:
    return not board_is_empty(board)


def board_letters_set(board: List[List[Any]]) -> Set[str]:
    n = board_size(board)
    out = set()
    for r in range(n):
        for c in range(n):
            ch = get_letter(board, r, c)
            if ch:
                out.add(ch)
    return out


def rack_counter(rack: List[str]) -> Counter:
    cnt = Counter()
    for raw in rack:
        ch = normalize_letter(raw)
        if ch:
            cnt[ch] += 1
    return cnt


def can_make_letters(needed: List[str], rack_ctr: Counter):
    bag = rack_ctr.copy()
    joker_used = []

    for ch in needed:
        if bag[ch] > 0:
            bag[ch] -= 1
        elif bag["?"] > 0:
            bag["?"] -= 1
            joker_used.append(ch)
        else:
            return None

    return joker_used


def get_anchors(board: List[List[Any]]) -> Set[Tuple[int, int]]:
    n = board_size(board)

    if board_is_empty(board):
        center = n // 2
        return {(center, center)}

    anchors = set()
    for r in range(n):
        for c in range(n):
            if get_letter(board, r, c) is None:
                for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    rr, cc = r + dr, c + dc
                    if in_bounds(board, rr, cc) and get_letter(board, rr, cc):
                        anchors.add((r, c))
                        break

    return anchors


def candidate_start_positions(board: List[List[Any]], word_len: int, anchor_r: int, anchor_c: int, direction: str):
    n = board_size(board)

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


def build_pattern(board: List[List[Any]], row: int, col: int, length: int, direction: str):
    letters = []
    fixed_positions = {}
    empties = 0

    for i in range(length):
        rr = row + (i if direction == DIR_DOWN else 0)
        cc = col + (i if direction == DIR_RIGHT else 0)
        ch = get_letter(board, rr, cc)

        letters.append(ch if ch else ".")
        if ch:
            fixed_positions[i] = ch
        else:
            empties += 1

    return "".join(letters), fixed_positions, empties


def word_matches_pattern(word: str, fixed_positions: Dict[int, str]) -> bool:
    for i, ch in fixed_positions.items():
        if word[i] != ch:
            return False
    return True


def estimate_needed_letters(word: str, fixed_positions: Dict[int, str]) -> List[str]:
    return [ch for i, ch in enumerate(word) if i not in fixed_positions]


def prefilter_entries_pattern(entries: List[WordEntry], fixed_positions: Dict[int, str], rack: List[str], board: List[List[Any]]):
    rack_ctr = rack_counter(rack)
    rack_set = {k for k, v in rack_ctr.items() if v > 0 and k != "?"}
    board_set = board_letters_set(board)
    out = []

    for entry in entries:
        word = entry.word

        if not word_matches_pattern(word, fixed_positions):
            continue

        if board_has_letters(board) and not (entry.uniq & (rack_set | board_set)):
            continue

        out.append(entry)

    return out


def fits(board: List[List[Any]], word: str, row: int, col: int, direction: str):
    n = board_size(board)

    if direction == DIR_RIGHT and col + len(word) > n:
        return None
    if direction == DIR_DOWN and row + len(word) > n:
        return None

    placed = []
    needed = []
    touch_count = 0
    adjacent_contacts = 0
    touched_existing = set()

    for i, ch in enumerate(word):
        rr = row + (i if direction == DIR_DOWN else 0)
        cc = col + (i if direction == DIR_RIGHT else 0)
        existing = get_letter(board, rr, cc)

        if existing:
            if existing != ch:
                return None
            touch_count += 1
            touched_existing.add((rr, cc))
        else:
            placed.append((rr, cc, ch))
            needed.append(ch)

            for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                r2, c2 = rr + dr, cc + dc
                if in_bounds(board, r2, c2) and get_letter(board, r2, c2):
                    adjacent_contacts += 1

    if not placed:
        return None

    if direction == DIR_RIGHT:
        if col > 0 and get_letter(board, row, col - 1):
            return None
        endc = col + len(word) - 1
        if endc < n - 1 and get_letter(board, row, endc + 1):
            return None
    else:
        if row > 0 and get_letter(board, row - 1, col):
            return None
        endr = row + len(word) - 1
        if endr < n - 1 and get_letter(board, endr + 1, col):
            return None

    if board_is_empty(board):
        center = n // 2
        if not any(
            (
                row + (i if direction == DIR_DOWN else 0),
                col + (i if direction == DIR_RIGHT else 0),
            ) == (center, center)
            for i in range(len(word))
        ):
            return None
    elif touch_count == 0 and adjacent_contacts == 0:
        return None

    interaction_score = touch_count + adjacent_contacts
    return placed, needed, interaction_score, len(touched_existing)


def cross_word_for_new_tile(board: List[List[Any]], r: int, c: int, ch: str, direction: str):
    n = board_size(board)

    if direction == DIR_RIGHT:
        start = r
        while start > 0 and get_letter(board, start - 1, c):
            start -= 1

        end = r
        while end < n - 1 and get_letter(board, end + 1, c):
            end += 1

        letters = []
        coords = []
        for rr in range(start, end + 1):
            letters.append(ch if rr == r else get_letter(board, rr, c))
            coords.append((rr, c))

        return "".join(letters), coords

    start = c
    while start > 0 and get_letter(board, r, start - 1):
        start -= 1

    end = c
    while end < n - 1 and get_letter(board, r, end + 1):
        end += 1

    letters = []
    coords = []
    for cc in range(start, end + 1):
        letters.append(ch if cc == c else get_letter(board, r, cc))
        coords.append((r, cc))

    return "".join(letters), coords


def all_words_valid(board: List[List[Any]], word: str, direction: str, placed: List[Tuple[int, int, str]], word_set: Set[str]):
    if word not in word_set:
        return False, []

    created = [word]

    for r, c, ch in placed:
        cw, _ = cross_word_for_new_tile(board, r, c, ch, direction)
        if len(cw) > 1:
            if cw not in word_set:
                return False, []
            created.append(cw)

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


def score_word_with_coords(
    board: List[List[Any]],
    coords: List[Tuple[int, int]],
    placed_map: Dict[Tuple[int, int], str],
    joker_cells: Set[Tuple[int, int]],
):
    total = 0
    word_mult = 1
    bonus_notes = []

    for r, c in coords:
        if (r, c) in placed_map:
            ch = placed_map[(r, c)]
            base = letter_score(ch, (r, c) in joker_cells)
            bonus = get_bonus(board, r, c)
            letter_val, wm = apply_bonus(base, bonus)
            total += letter_val
            word_mult *= wm

            if bonus is not None:
                note_bonus = "K2" if bonus == "START" else bonus
                bonus_notes.append(f"{ch}@{r + 1},{c + 1}:{note_bonus}")
        else:
            ch = get_letter(board, r, c)
            total += LETTER_SCORES.get(ch, 0)

    return total * word_mult, bonus_notes


def score_move(
    board: List[List[Any]],
    word: str,
    row: int,
    col: int,
    direction: str,
    placed: List[Tuple[int, int, str]],
    joker_used: List[str],
):
    placed_map = {(r, c): ch for r, c, ch in placed}
    joker_cells = build_joker_cells(placed, joker_used)

    main_coords = [
        (
            row + (i if direction == DIR_DOWN else 0),
            col + (i if direction == DIR_RIGHT else 0),
        )
        for i in range(len(word))
    ]

    main_score, notes = score_word_with_coords(board, main_coords, placed_map, joker_cells)

    cross_total = 0
    cross_details = []
    cross_count = 0

    for r, c, ch in placed:
        cw, coords = cross_word_for_new_tile(board, r, c, ch, direction)
        if len(cw) > 1:
            cw_score, cw_notes = score_word_with_coords(board, coords, placed_map, joker_cells)
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

    return final, detail, cross_count


def normalize_suggestion(move: Dict[str, Any]) -> Dict[str, Any]:
    placed = [
        {
            "row": r,
            "col": c,
            "letter": ch,
            "is_joker": bool(move.get("joker_cells") and (r, c) in move.get("joker_cells")),
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


def find_best_moves(
    board: List[List[Any]],
    rack: List[str],
    index: DictionaryIndex,
    limit: int = 300,
    seconds: float = 12.0,
    max_checks: int = 1_200_000,
):
    start_time = time.time()
    deadline = start_time + seconds

    results = []
    word_set = index.word_set
    board_n = board_size(board)
    max_len = min(board_n, len([x for x in rack if normalize_letter(x)]) + board_n)

    rack_ctr = rack_counter(rack)
    anchors = get_anchors(board)
    lengths = [length for length in range(2, max_len + 1) if length in index.by_length]

    checks = 0
    pattern_hits = 0
    fit_hits = 0
    valid_hits = 0

    for length in lengths:
        if time.time() > deadline or checks >= max_checks:
            break

        raw_entries = index.by_length[length]

        for direction in (DIR_RIGHT, DIR_DOWN):
            if time.time() > deadline or checks >= max_checks:
                break

            starts = set()

            if board_is_empty(board):
                center_pos = board_n // 2
                starts.update(candidate_start_positions(board, length, center_pos, center_pos, direction))
            else:
                for ar, ac in anchors:
                    for row, col in candidate_start_positions(board, length, ar, ac, direction):
                        starts.add((row, col))

            pattern_cache = {}

            for row, col in starts:
                if time.time() > deadline or checks >= max_checks:
                    break

                pattern, fixed_positions, empties = build_pattern(board, row, col, length, direction)
                if empties == 0:
                    continue

                cache_key = (length, pattern)
                if cache_key not in pattern_cache:
                    pattern_cache[cache_key] = prefilter_entries_pattern(raw_entries, fixed_positions, rack, board)

                entries = pattern_cache[cache_key]

                if entries:
                    pattern_hits += 1

                for entry in entries:
                    if time.time() > deadline or checks >= max_checks:
                        break

                    checks += 1
                    word = entry.word

                    needed_preview = estimate_needed_letters(word, fixed_positions)
                    if can_make_letters(needed_preview, rack_ctr) is None:
                        continue

                    fit = fits(board, word, row, col, direction)
                    if not fit:
                        continue

                    fit_hits += 1
                    placed, needed, interaction_score, overlap_count = fit

                    joker_used = can_make_letters(needed, rack_ctr)
                    if joker_used is None:
                        continue

                    ok, created_words = all_words_valid(board, word, direction, placed, word_set)
                    if not ok:
                        continue

                    valid_hits += 1
                    score, detail, cross_count = score_move(board, word, row, col, direction, placed, joker_used)

                    covered = [
                        (
                            row + (i if direction == DIR_DOWN else 0),
                            col + (i if direction == DIR_RIGHT else 0),
                        )
                        for i in range(len(word))
                    ]

                    effective_score = score + (cross_count * 10) + (interaction_score * 4) + (overlap_count * 3)
                    joker_cells = build_joker_cells(placed, joker_used)

                    results.append(
                        {
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
                        }
                    )

    results.sort(key=lambda x: (-x["score"], x["word"]))

    uniq = []
    seen = set()

    for move in results:
        key = (move["word"], move["row"], move["col"], move["direction"], move["score"])
        if key in seen:
            continue

        seen.add(key)
        uniq.append(normalize_suggestion(move))

        if len(uniq) >= limit:
            break

    return {
        "suggestions": uniq,
        "message": "" if uniq else "Bu taşlarla tahtaya kurallara uygun kelime yerleştirilemedi.",
        "debug": {
            "engine": "v8.2_pattern_web",
            "wordCount": len(index.word_set),
            "rack": list(rack_ctr.elements()),
            "boardSize": board_n,
            "boardTiles": sum(1 for r in range(board_n) for c in range(board_n) if get_letter(board, r, c)),
            "anchors": len(anchors),
            "lengthBuckets": len(lengths),
            "checks": checks,
            "patternHits": pattern_hits,
            "fitHits": fit_hits,
            "validHits": valid_hits,
            "returned": len(uniq),
            "fallback": False,
            "timedOut": time.time() > deadline,
        },
    }


def generate_moves(
    board: List[List[Any]],
    rack: List[str],
    index: DictionaryIndex,
    limit: int = 300,
    seconds: float = 12.0,
    max_checks: int = 1_200_000,
    **_kwargs,
):
    cleaned_rack = [normalize_letter(x) for x in rack if normalize_letter(x)]

    if not cleaned_rack:
        return {
            "suggestions": [],
            "message": "Harf alanına en az bir taş gir.",
            "debug": {
                "engine": "v8.2_pattern_web",
                "reason": "empty_rack",
                "wordCount": len(index.word_set),
                "fallback": False,
            },
        }

    if len(index.word_set) == 0:
        return {
            "suggestions": [],
            "message": "Sözlük yüklenmedi. backend/data klasörünü kontrol et.",
            "debug": {
                "engine": "v8.2_pattern_web",
                "reason": "empty_dictionary",
                "wordCount": 0,
                "fallback": False,
            },
        }

    return find_best_moves(
        board=board,
        rack=cleaned_rack,
        index=index,
        limit=limit,
        seconds=seconds,
        max_checks=max_checks,
    )
