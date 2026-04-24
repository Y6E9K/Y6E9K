from __future__ import annotations

import heapq
import time
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Set, Tuple

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
TR_LETTERS = tuple(ch for ch in LETTER_SCORES if ch != "?")


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


@dataclass
class DictionaryIndex:
    word_set: Set[str]
    words: List[str]


def build_dictionary_index(words: Iterable[str]) -> DictionaryIndex:
    word_set: Set[str] = set()
    clean_words: List[str] = []
    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word) or word in word_set:
            continue
        word_set.add(word)
        clean_words.append(word)
    clean_words.sort(key=lambda w: (-sum(LETTER_SCORES.get(c, 0) for c in w), -len(w), w))
    return DictionaryIndex(word_set=word_set, words=clean_words)


def size(board):
    return len(board)


def in_bounds(board, r, c):
    return 0 <= r < size(board) and 0 <= c < size(board)


def center(board):
    n = size(board)
    return n // 2, n // 2


def get_letter(board, r, c):
    if not in_bounds(board, r, c):
        return ""
    cell = board[r][c]
    if isinstance(cell, dict):
        return normalize_letter(cell.get("letter", ""))
    return normalize_letter(cell)


def get_bonus(board, r, c):
    if not in_bounds(board, r, c):
        return None
    cell = board[r][c]
    return cell.get("bonus") if isinstance(cell, dict) else None


def has_tiles(board):
    return any(get_letter(board, r, c) for r in range(size(board)) for c in range(size(board)))


def rack_counter(rack: List[str]) -> Counter:
    cnt = Counter()
    for ch in rack:
        n = normalize_letter(ch)
        if n:
            cnt[n] += 1
    return cnt


def board_counter(board) -> Counter:
    cnt = Counter()
    for r in range(size(board)):
        for c in range(size(board)):
            ch = get_letter(board, r, c)
            if ch:
                cnt[ch] += 1
    return cnt


def anchors(board):
    if not has_tiles(board):
        return [center(board)]
    out = set()
    for r in range(size(board)):
        for c in range(size(board)):
            if get_letter(board, r, c):
                for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                    if in_bounds(board, nr, nc) and not get_letter(board, nr, nc):
                        out.add((nr, nc))
    cr, cc = center(board)
    def rank(rc):
        r, c = rc
        bonus = 0
        for nr, nc in ((r,c),(r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if in_bounds(board, nr, nc):
                b = get_bonus(board, nr, nc)
                if b in ("K3", "H3"):
                    bonus -= 5
                elif b in ("K2", "H2", "START"):
                    bonus -= 3
        density = -sum(1 for nr,nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if in_bounds(board,nr,nc) and get_letter(board,nr,nc))
        return (bonus, density, abs(r-cr)+abs(c-cc))
    return sorted(out, key=rank)


def line_letters(board, row, col, direction, length):
    out = []
    for i in range(length):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        if not in_bounds(board, r, c):
            return None
        out.append(get_letter(board, r, c))
    return out


def before_after_blocked(board, row, col, direction, length):
    br, bc = (row, col-1) if direction == DIR_RIGHT else (row-1, col)
    ar, ac = row + (length if direction == DIR_DOWN else 0), col + (length if direction == DIR_RIGHT else 0)
    return (in_bounds(board, br, bc) and get_letter(board, br, bc)) or (in_bounds(board, ar, ac) and get_letter(board, ar, ac))


def passes_center(board, row, col, direction, length):
    cr, cc = center(board)
    return any((row + (i if direction == DIR_DOWN else 0), col + (i if direction == DIR_RIGHT else 0)) == (cr, cc) for i in range(length))


def perpendicular_fragments(board, row, col, direction):
    if direction == DIR_RIGHT:
        a, b = (-1,0), (1,0)
    else:
        a, b = (0,-1), (0,1)
    left=[]; r=row+a[0]; c=col+a[1]
    while in_bounds(board,r,c) and get_letter(board,r,c):
        left.append(get_letter(board,r,c)); r+=a[0]; c+=a[1]
    left.reverse()
    right=[]; r=row+b[0]; c=col+b[1]
    while in_bounds(board,r,c) and get_letter(board,r,c):
        right.append(get_letter(board,r,c)); r+=b[0]; c+=b[1]
    return "".join(left), "".join(right)


def cross_valid(board, row, col, direction, ch, word_set):
    pre, suf = perpendicular_fragments(board, row, col, direction)
    return True if not pre and not suf else f"{pre}{ch}{suf}" in word_set


def consume_rack(board, word, row, col, direction, rack):
    line = line_letters(board, row, col, direction, len(word))
    if line is None:
        return None
    left = rack.copy()
    jokers = set()
    used_new = 0
    for i, ch in enumerate(word):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        existing = line[i]
        if existing:
            if existing != ch:
                return None
            continue
        if left.get(ch, 0) > 0:
            left[ch] -= 1
            if left[ch] == 0: del left[ch]
        elif left.get("?", 0) > 0:
            left["?"] -= 1
            if left["?"] == 0: del left["?"]
            jokers.add((r, c))
        else:
            return None
        used_new += 1
    return jokers if used_new else None


def build_word_coords(board, row, col, direction, placed):
    dr, dc = (0,1) if direction == DIR_RIGHT else (1,0)
    r, c = row, col
    while in_bounds(board, r-dr, c-dc) and (placed.get((r-dr,c-dc)) or get_letter(board,r-dr,c-dc)):
        r -= dr; c -= dc
    coords=[]
    while in_bounds(board,r,c):
        ch = placed.get((r,c)) or get_letter(board,r,c)
        if not ch: break
        coords.append((r,c,ch)); r += dr; c += dc
    return coords


def score_coords(board, coords, new_cells, joker_map):
    total = 0; word_mul = 1
    for r,c,ch in coords:
        val = 0 if joker_map.get((r,c), False) else LETTER_SCORES.get(ch, 0)
        if (r,c) in new_cells:
            b = get_bonus(board,r,c)
            if b in LETTER_MULTIPLIERS:
                val *= LETTER_MULTIPLIERS[b]
            elif b in WORD_MULTIPLIERS:
                word_mul *= WORD_MULTIPLIERS[b]
        total += val
    return total * word_mul


def make_move(board, word_set, word, row, col, direction, jokers):
    if line_letters(board,row,col,direction,len(word)) is None:
        return None
    if before_after_blocked(board,row,col,direction,len(word)):
        return None
    if not has_tiles(board) and not passes_center(board,row,col,direction,len(word)):
        return None
    line = line_letters(board,row,col,direction,len(word))
    placed = {}; joker_map = {}; new_cells=set(); placed_list=[]; interaction=0; overlap=0
    for i,ch in enumerate(word):
        r = row + (i if direction == DIR_DOWN else 0)
        c = col + (i if direction == DIR_RIGHT else 0)
        existing = line[i]
        if existing:
            if existing != ch: return None
            interaction += 1; overlap += 1
        else:
            if not cross_valid(board,r,c,direction,ch,word_set): return None
            is_joker = (r,c) in jokers
            placed[(r,c)] = ch; joker_map[(r,c)] = is_joker; new_cells.add((r,c))
            placed_list.append({"row":r,"col":c,"letter":ch,"is_joker":is_joker})
            if any(in_bounds(board,nr,nc) and get_letter(board,nr,nc) for nr,nc in (((r-1,c),(r+1,c)) if direction==DIR_RIGHT else ((r,c-1),(r,c+1)))):
                interaction += 1
    if not placed_list: return None
    if has_tiles(board) and interaction == 0 and overlap == 0: return None
    main_coords = build_word_coords(board,row,col,direction,placed)
    main_word = "".join(ch for _,_,ch in main_coords)
    if main_word != word or main_word not in word_set: return None
    score = score_coords(board, main_coords, new_cells, joker_map)
    cross_words=[]; created=[main_word]
    cross_dir = DIR_DOWN if direction == DIR_RIGHT else DIR_RIGHT
    for p in placed_list:
        coords = build_word_coords(board, p["row"], p["col"], cross_dir, placed)
        cw = "".join(ch for _,_,ch in coords)
        if len(cw) > 1:
            if cw not in word_set: return None
            cross_words.append(cw); created.append(cw)
            score += score_coords(board, coords, {(p["row"],p["col"])}, joker_map)
    if len(placed_list) == 7: score += 50
    return {"word":word,"row":row,"col":col,"direction":direction,"position":f"{direction} · {row+1} / {col+1}","score":score,"placed":placed_list,"createdWords":created,"crossWords":cross_words,"interaction":interaction,"overlap":overlap}


class TopCollector:
    def __init__(self, limit):
        self.limit=limit; self.heap=[]; self.seen=set(); self.counter=0
    def add(self, move):
        key=(move["word"],move["row"],move["col"],move["direction"])
        if key in self.seen: return
        self.seen.add(key); self.counter += 1
        rank=(int(move["score"]), len(move["placed"]), int(move["interaction"]), len(move["word"]), -int(move["row"]), -int(move["col"]))
        entry=(rank,self.counter,move)
        if len(self.heap)<self.limit: heapq.heappush(self.heap,entry)
        elif rank > self.heap[0][0]: heapq.heapreplace(self.heap,entry)
    def results(self):
        out=[x[2] for x in self.heap]
        out.sort(key=lambda m:(-m["score"],-len(m["placed"]),-m["interaction"],-len(m["word"]),m["word"],m["row"],m["col"]))
        return out


def start_positions(board, word_len, direction, anchor_list, backtrack_extra):
    starts=set(); n=size(board)
    for ar,ac in anchor_list:
        for i in range(word_len + backtrack_extra + 2):
            r = ar - (i if direction == DIR_DOWN else 0)
            c = ac - (i if direction == DIR_RIGHT else 0)
            er = r + (word_len-1 if direction == DIR_DOWN else 0)
            ec = c + (word_len-1 if direction == DIR_RIGHT else 0)
            if in_bounds(board,r,c) and in_bounds(board,er,ec): starts.add((r,c))
    if backtrack_extra >= 20:
        for r in range(n):
            for c in range(n):
                er = r + (word_len-1 if direction == DIR_DOWN else 0)
                ec = c + (word_len-1 if direction == DIR_RIGHT else 0)
                if in_bounds(board,r,c) and in_bounds(board,er,ec): starts.add((r,c))
    return list(starts)


def generate_moves(board, rack, index, limit=500, seconds=30.0, max_checks=1800000, backtrack_extra=20):
    deadline = time.time() + seconds
    rack_cnt = rack_counter(rack)
    available = rack_cnt + board_counter(board)
    anchor_list = anchors(board)
    collector = TopCollector(max(20, limit))
    n = size(board)
    empty = not has_tiles(board)
    max_len = min(n, max(2, sum(rack_cnt.values()) + (10 if empty else 14)))
    checks = 0
    for word in index.words:
        if time.time() > deadline or checks >= max_checks: break
        if len(word) > max_len: continue
        need = Counter(word); missing = 0
        for ch,cnt in need.items():
            have=available.get(ch,0)
            if have<cnt: missing += cnt-have
        if missing > rack_cnt.get("?",0): continue
        for direction in (DIR_RIGHT, DIR_DOWN):
            for row,col in start_positions(board,len(word),direction,anchor_list,backtrack_extra):
                if time.time() > deadline or checks >= max_checks: break
                checks += 1
                if before_after_blocked(board,row,col,direction,len(word)): continue
                jokers = consume_rack(board,word,row,col,direction,rack_cnt)
                if jokers is None: continue
                move = make_move(board,index.word_set,word,row,col,direction,jokers)
                if move: collector.add(move)
    return collector.results()[:limit]
