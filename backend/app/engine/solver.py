from __future__ import annotations

import heapq
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

WORD_MULTIPLIERS = {"K2": 2, "K3": 3, "START": 2}
LETTER_MULTIPLIERS = {"H2": 2, "H3": 3}


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
    words_by_length: Dict[int, List[WordInfo]]
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
    infos: List[WordInfo] = []
    by_length: Dict[int, List[WordInfo]] = defaultdict(list)

    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word) or word in word_set:
            continue

        word_set.add(word)
        info = WordInfo(
            word=word,
            counter=Counter(word),
            score=sum(LETTER_SCORES.get(ch, 0) for ch in word),
            length=len(word),
        )
        infos.append(info)
        by_length[len(word)].append(info)

    infos.sort(key=lambda x: (-x.score, -x.length, x.word))
    for ln in by_length:
        by_length[ln].sort(key=lambda x: (-x.score, -x.length, x.word))

    return DictionaryIndex(
        word_set=word_set,
        words=infos,
        words_by_length=dict(by_length),
        sample_words=[x.word for x in infos[:50]],
    )


def board_size(board: List[List[dict]]) -> int:
    return len(board)


def in_bounds(board: List[List[dict]], r: int, c: int) -> bool:
    n = board_size(board)
    return 0 <= r < n and 0 <= c < n


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


def center(board: List[List[dict]]) -> Tuple[int, int]:
    n = board_size(board)
    return n // 2, n // 2


def step(direction: str) -> Tuple[int, int]:
    return (0, 1) if direction == DIR_RIGHT else (1, 0)


def cell_at(direction: str, r: int, c: int, i: int) -> Tuple[int, int]:
    dr, dc = step(direction)
    return r + dr * i, c + dc * i


def line_in_bounds(board: List[List[dict]], r: int, c: int, direction: str, length: int) -> bool:
    er, ec = cell_at(direction, r, c, length - 1)
    return in_bounds(board, r, c) and in_bounds(board, er, ec)


def edge_ok(board: List[List[dict]], r: int, c: int, direction: str, length: int) -> bool:
    dr, dc = step(direction)
    br, bc = r - dr, c - dc
    ar, ac = r + dr * length, c + dc * length

    if in_bounds(board, br, bc) and get_letter(board, br, bc):
        return False
    if in_bounds(board, ar, ac) and get_letter(board, ar, ac):
        return False
    return True


def board_tiles(board: List[List[dict]]) -> List[Tuple[int, int, str]]:
    out = []
    n = board_size(board)
    for r in range(n):
        for c in range(n):
            ch = get_letter(board, r, c)
            if ch:
                out.append((r, c, ch))
    return out


def board_has_tiles(board: List[List[dict]]) -> bool:
    return bool(board_tiles(board))


def board_counter(board: List[List[dict]]) -> Counter:
    cnt = Counter()
    for _, _, ch in board_tiles(board):
        cnt[ch] += 1
    return cnt


def rack_counter(rack: List[str]) -> Counter:
    cnt = Counter()
    for raw in rack:
        ch = normalize_letter(raw)
        if ch:
            cnt[ch] += 1
    return cnt


def neighbor_count(board: List[List[dict]], r: int, c: int) -> int:
    total = 0
    for nr, nc in ((r - 1, c), (r + 1, c), (r, c - 1), (r, c + 1)):
        if in_bounds(board, nr, nc) and get_letter(board, nr, nc):
            total += 1
    return total


def passes_center(board: List[List[dict]], r: int, c: int, direction: str, length: int) -> bool:
    cen = center(board)
    return any(cell_at(direction, r, c, i) == cen for i in range(length))


def perpendicular_fragments(board: List[List[dict]], r: int, c: int, direction: str) -> Tuple[str, str]:
    if direction == DIR_RIGHT:
        d1r, d1c, d2r, d2c = -1, 0, 1, 0
    else:
        d1r, d1c, d2r, d2c = 0, -1, 0, 1

    prefix = []
    rr, cc = r + d1r, c + d1c
    while in_bounds(board, rr, cc):
        ch = get_letter(board, rr, cc)
        if not ch:
            break
        prefix.append(ch)
        rr += d1r
        cc += d1c
    prefix.reverse()

    suffix = []
    rr, cc = r + d2r, c + d2c
    while in_bounds(board, rr, cc):
        ch = get_letter(board, rr, cc)
        if not ch:
            break
        suffix.append(ch)
        rr += d2r
        cc += d2c

    return "".join(prefix), "".join(suffix)


def cross_valid(board: List[List[dict]], r: int, c: int, direction: str, ch: str, word_set: Set[str], strict: bool) -> bool:
    prefix, suffix = perpendicular_fragments(board, r, c, direction)
    if not prefix and not suffix:
        return True
    if not strict:
        return True
    return f"{prefix}{ch}{suffix}" in word_set


def build_coords(board: List[List[dict]], r: int, c: int, direction: str, placed_map: Dict[Tuple[int, int], str]):
    dr, dc = step(direction)

    rr, cc = r, c
    while in_bounds(board, rr - dr, cc - dc):
        ch = placed_map.get((rr - dr, cc - dc)) or get_letter(board, rr - dr, cc - dc)
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


def score_coords(board: List[List[dict]], coords: List[Tuple[int, int, str]], newly: Set[Tuple[int, int]], joker_map: Dict[Tuple[int, int], bool]) -> int:
    total = 0
    word_mul = 1

    for r, c, ch in coords:
        value = 0 if joker_map.get((r, c), False) else LETTER_SCORES.get(ch, 0)

        if (r, c) in newly:
            bonus = get_bonus(board, r, c)
            if bonus in LETTER_MULTIPLIERS:
                value *= LETTER_MULTIPLIERS[bonus]
            elif bonus in WORD_MULTIPLIERS:
                word_mul *= WORD_MULTIPLIERS[bonus]

        total += value

    return total * word_mul


def word_available(info: WordInfo, available: Counter, jokers: int) -> bool:
    missing = 0
    for ch, need in info.counter.items():
        have = available.get(ch, 0)
        if have < need:
            missing += need - have
            if missing > jokers:
                return False
    return True


def consume_word(board: List[List[dict]], word: str, r: int, c: int, direction: str, rack: Counter):
    left = rack.copy()
    placed = []
    jokers = set()
    overlap = 0

    for i, ch in enumerate(word):
        rr, cc = cell_at(direction, r, c, i)
        existing = get_letter(board, rr, cc)

        if existing:
            if existing != ch:
                return None
            overlap += 1
            continue

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

        placed.append((rr, cc, ch))

    return placed, jokers, overlap


def make_move(
    board: List[List[dict]],
    word: str,
    r: int,
    c: int,
    direction: str,
    rack: Counter,
    word_set: Set[str],
    require_connection: bool,
    strict_cross: bool,
    fallback: bool = False,
):
    length = len(word)

    if not line_in_bounds(board, r, c, direction, length):
        return None

    # Gerçek hamlede kenarların boş olması gerekir. Fallback'te gevşek çalışabilir.
    if not fallback and not edge_ok(board, r, c, direction, length):
        return None

    empty_board = not board_has_tiles(board)
    if empty_board and not passes_center(board, r, c, direction, length):
        return None

    consumed = consume_word(board, word, r, c, direction, rack)
    if consumed is None:
        return None

    placed_raw, jokers, overlap = consumed
    if not placed_raw:
        return None

    placed_map = {}
    joker_map = {}
    newly = set()
    placed = []
    interaction = overlap

    for rr, cc, ch in placed_raw:
        if not cross_valid(board, rr, cc, direction, ch, word_set, strict_cross):
            return None

        is_joker = (rr, cc) in jokers
        placed_map[(rr, cc)] = ch
        joker_map[(rr, cc)] = is_joker
        newly.add((rr, cc))
        placed.append({"row": rr, "col": cc, "letter": ch, "is_joker": is_joker})

        if neighbor_count(board, rr, cc) > 0:
            interaction += 1

    if require_connection and not empty_board and interaction == 0:
        return None

    main_coords = build_coords(board, r, c, direction, placed_map)
    main_word = "".join(ch for _, _, ch in main_coords)

    if strict_cross and main_word not in word_set:
        return None

    total = score_coords(board, main_coords, newly, joker_map)
    created_words = [main_word]
    cross_words = []
    cross_dir = DIR_DOWN if direction == DIR_RIGHT else DIR_RIGHT

    if strict_cross:
        for tile in placed:
            rr = int(tile["row"])
            cc = int(tile["col"])
            coords = build_coords(board, rr, cc, cross_dir, placed_map)
            cw = "".join(ch for _, _, ch in coords)
            if len(cw) > 1:
                if cw not in word_set:
                    return None
                cross_words.append(cw)
                created_words.append(cw)
                total += score_coords(board, coords, {(rr, cc)}, joker_map)

    if len(placed) == 7:
        total += 50

    return {
        "word": word,
        "row": r,
        "col": c,
        "direction": direction,
        "position": f"{direction} · {r + 1} / {c + 1}",
        "score": total,
        "placed": placed,
        "createdWords": created_words,
        "crossWords": cross_words,
        "interaction": interaction,
        "overlap": overlap,
        "connected": bool(empty_board or interaction > 0),
        "fallback": fallback,
    }


class Collector:
    def __init__(self, limit: int):
        self.limit = limit
        self.seen = set()
        self.heap = []
        self.counter = 0

    def add(self, move):
        key = (move["word"], move["row"], move["col"], move["direction"])
        if key in self.seen:
            return
        self.seen.add(key)

        rank = (
            int(move["score"]),
            1 if move.get("connected") else 0,
            0 if move.get("fallback") else 1,
            len(move["placed"]),
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
        out = [x[2] for x in self.heap]
        out.sort(
            key=lambda m: (
                -int(m["score"]),
                -int(bool(m.get("connected"))),
                int(bool(m.get("fallback"))),
                -len(m["placed"]),
                -len(m["word"]),
                m["word"],
            )
        )
        return out


def collect_slots(board: List[List[dict]], max_len: int, allow_edge_blocked: bool = False):
    n = board_size(board)
    empty_board = not board_has_tiles(board)
    slots = []

    for direction in (DIR_RIGHT, DIR_DOWN):
        for r in range(n):
            for c in range(n):
                for length in range(2, max_len + 1):
                    if not line_in_bounds(board, r, c, direction, length):
                        break

                    if not allow_edge_blocked and not edge_ok(board, r, c, direction, length):
                        continue

                    letters = []
                    empty_count = 0
                    overlap = 0
                    connection = 0

                    for i in range(length):
                        rr, cc = cell_at(direction, r, c, i)
                        ch = get_letter(board, rr, cc)
                        letters.append(ch)

                        if ch:
                            overlap += 1
                        else:
                            empty_count += 1
                            if neighbor_count(board, rr, cc) > 0:
                                connection += 1

                    if empty_count == 0:
                        continue

                    if empty_board:
                        if not passes_center(board, r, c, direction, length):
                            continue
                    else:
                        if overlap == 0 and connection == 0:
                            continue

                    # Yoğun tahtalarda kısa/bağlantılı slotları önce dene.
                    bonus_rank = 0
                    for i in range(length):
                        rr, cc = cell_at(direction, r, c, i)
                        b = get_bonus(board, rr, cc)
                        if b in ("K3", "H3"):
                            bonus_rank += 5
                        elif b in ("K2", "H2", "START"):
                            bonus_rank += 3

                    slots.append({
                        "row": r,
                        "col": c,
                        "direction": direction,
                        "length": length,
                        "letters": letters,
                        "empty": empty_count,
                        "overlap": overlap,
                        "connection": connection,
                        "bonusRank": bonus_rank,
                    })

    slots.sort(
        key=lambda s: (
            -s["overlap"],
            -s["connection"],
            -s["bonusRank"],
            s["empty"],
            s["length"],
            s["row"],
            s["col"],
        )
    )
    return slots


def pattern_matches(info: WordInfo, slot) -> bool:
    word = info.word
    if len(word) != slot["length"]:
        return False

    for i, fixed in enumerate(slot["letters"]):
        if fixed and word[i] != fixed:
            return False

    return True


def slot_search(board, index, rack_cnt, collector, deadline, max_checks, strict_cross: bool, allow_edge_blocked: bool):
    n = board_size(board)
    rack_total = sum(rack_cnt.values())
    if rack_total == 0:
        return 0, 0

    board_cnt = board_counter(board)
    available = rack_cnt + board_cnt
    joker_count = rack_cnt.get("?", 0)
    max_len = min(n, rack_total + (0 if not board_has_tiles(board) else 10))

    slots = collect_slots(board, max_len=max_len, allow_edge_blocked=allow_edge_blocked)
    checks = 0
    found = 0

    for slot in slots:
        if time.time() > deadline or checks >= max_checks:
            break

        words = index.words_by_length.get(slot["length"], [])
        if not words:
            continue

        for info in words:
            if time.time() > deadline or checks >= max_checks:
                break

            # Hızlı desen filtresi
            if not pattern_matches(info, slot):
                continue

            # Harf mevcudiyeti filtresi
            if not word_available(info, available, joker_count):
                continue

            checks += 1

            move = make_move(
                board=board,
                word=info.word,
                r=slot["row"],
                c=slot["col"],
                direction=slot["direction"],
                rack=rack_cnt,
                word_set=index.word_set,
                require_connection=True,
                strict_cross=strict_cross,
                fallback=False,
            )

            if move:
                collector.add(move)
                found += 1

                if found >= collector.limit and time.time() > deadline - 1:
                    return checks, found

    return checks, found


def fallback_search(board, index, rack_cnt, collector, deadline, max_checks):
    # Son çare: eldeki taşlardan oluşan kelimeleri en uygun boş yere yerleştir.
    # Bağlantı şartı ve kenar şartı gevşek; kullanıcı boş liste görmesin diye fallback=true döner.
    n = board_size(board)
    rack_total = sum(rack_cnt.values())
    joker_count = rack_cnt.get("?", 0)
    checks = 0

    # Boş hücreleri önce bonus/komşuluk değerine göre sırala.
    empty_cells = []
    for r in range(n):
        for c in range(n):
            if not get_letter(board, r, c):
                bonus = get_bonus(board, r, c)
                bonus_rank = 5 if bonus in ("K3", "H3") else 3 if bonus in ("K2", "H2", "START") else 0
                empty_cells.append((-(bonus_rank + neighbor_count(board, r, c)), r, c))
    empty_cells.sort()

    for info in index.words:
        if time.time() > deadline or checks >= max_checks:
            break

        if info.length > min(n, rack_total):
            continue

        if not word_available(info, rack_cnt, joker_count):
            continue

        for _, sr, sc in empty_cells:
            for direction in (DIR_RIGHT, DIR_DOWN):
                if time.time() > deadline or checks >= max_checks:
                    return checks

                # Kelimeyi seçilen boş hücreye farklı indekslerle denk getir.
                for i in range(info.length):
                    r = sr - (i if direction == DIR_DOWN else 0)
                    c = sc - (i if direction == DIR_RIGHT else 0)

                    if not line_in_bounds(board, r, c, direction, info.length):
                        continue

                    checks += 1
                    move = make_move(
                        board=board,
                        word=info.word,
                        r=r,
                        c=c,
                        direction=direction,
                        rack=rack_cnt,
                        word_set=index.word_set,
                        require_connection=False,
                        strict_cross=False,
                        fallback=True,
                    )

                    if move:
                        move["connected"] = bool(move.get("interaction", 0) > 0)
                        collector.add(move)
                        if len(collector.heap) >= 60:
                            return checks

    return checks


def generate_moves(
    board: List[List[dict]],
    rack: List[str],
    index: DictionaryIndex,
    limit: int = 500,
    seconds: float = 8.0,
    max_checks: int = 700_000,
    **_kwargs,
):
    start = time.time()
    deadline = start + seconds

    rack_cnt = rack_counter(rack)
    rack_total = sum(rack_cnt.values())

    if rack_total == 0:
        return {
            "suggestions": [],
            "debug": {"reason": "empty_rack", "wordCount": len(index.word_set)},
        }

    if len(index.word_set) == 0:
        return {
            "suggestions": [],
            "debug": {"reason": "empty_dictionary", "wordCount": 0},
        }

    collector = Collector(limit=max(20, limit))

    # 1) Yoğun tahta için slot tabanlı gerçek arama
    strict_checks, strict_found = slot_search(
        board=board,
        index=index,
        rack_cnt=rack_cnt,
        collector=collector,
        deadline=deadline,
        max_checks=max_checks // 2,
        strict_cross=True,
        allow_edge_blocked=False,
    )

    # 2) Az sonuç varsa çapraz kelime kontrolünü gevşet
    loose_checks = 0
    loose_found = 0
    if len(collector.heap) < 10 and time.time() < deadline:
        loose_checks, loose_found = slot_search(
            board=board,
            index=index,
            rack_cnt=rack_cnt,
            collector=collector,
            deadline=deadline,
            max_checks=max_checks // 3,
            strict_cross=False,
            allow_edge_blocked=False,
        )

    # 3) Hâlâ boşsa kenar şartını da gevşeterek slot ara
    edge_loose_checks = 0
    edge_loose_found = 0
    if len(collector.heap) == 0 and time.time() < deadline:
        edge_loose_checks, edge_loose_found = slot_search(
            board=board,
            index=index,
            rack_cnt=rack_cnt,
            collector=collector,
            deadline=deadline,
            max_checks=max_checks // 4,
            strict_cross=False,
            allow_edge_blocked=True,
        )

    # 4) Son çare fallback. Bu artık süre bitmeden çalışsın diye ayrı ve kısa tutuldu.
    fallback_checks = 0
    if len(collector.heap) == 0:
        # Süre bitmiş olsa bile 1.5 sn ek emniyet ver.
        fallback_deadline = max(deadline, time.time() + 1.5)
        fallback_checks = fallback_search(
            board=board,
            index=index,
            rack_cnt=rack_cnt,
            collector=collector,
            deadline=fallback_deadline,
            max_checks=80_000,
        )

    results = collector.results()[:limit]

    return {
        "suggestions": results,
        "debug": {
            "wordCount": len(index.word_set),
            "rack": list(rack_cnt.elements()),
            "boardTiles": len(board_tiles(board)),
            "strictChecks": strict_checks,
            "strictFound": strict_found,
            "looseChecks": loose_checks,
            "looseFound": loose_found,
            "edgeLooseChecks": edge_loose_checks,
            "edgeLooseFound": edge_loose_found,
            "fallbackChecks": fallback_checks,
            "returned": len(results),
            "usedFallback": bool(results and results[0].get("fallback")),
        },
    }
