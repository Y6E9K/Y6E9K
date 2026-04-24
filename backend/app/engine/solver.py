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
    sample_words: List[str]


def build_dictionary_index(words: Iterable[str]) -> DictionaryIndex:
    word_set: Set[str] = set()
    infos: List[WordInfo] = []
    by_letter: Dict[str, List[WordInfo]] = defaultdict(list)
    for raw in words:
        word = normalize_word(raw)
        if not is_valid_word(word) or word in word_set:
            continue
        word_set.add(word)
        info = WordInfo(word=word, counter=Counter(word), score=sum(LETTER_SCORES.get(ch, 0) for ch in word), length=len(word))
        infos.append(info)
        for ch in set(word):
            by_letter[ch].append(info)
    infos.sort(key=lambda x: (-x.score, -x.length, x.word))
    for ch in by_letter:
        by_letter[ch].sort(key=lambda x: (-x.score, -x.length, x.word))
    return DictionaryIndex(word_set=word_set, words=infos, words_by_letter=dict(by_letter), sample_words=[x.word for x in infos[:50]])


def size(board): return len(board)
def in_bounds(board, r, c):
    n = size(board)
    return 0 <= r < n and 0 <= c < n

def center(board):
    n = size(board)
    return n // 2, n // 2

def get_letter(board, r, c):
    if not in_bounds(board, r, c): return ""
    cell = board[r][c]
    if isinstance(cell, dict): return normalize_letter(cell.get("letter", ""))
    return normalize_letter(cell)

def get_bonus(board, r, c):
    if not in_bounds(board, r, c): return None
    cell = board[r][c]
    if isinstance(cell, dict): return cell.get("bonus")
    return None

def board_tiles(board):
    out = []
    for r in range(size(board)):
        for c in range(size(board)):
            ch = get_letter(board, r, c)
            if ch: out.append((r, c, ch))
    return out

def board_has_tiles(board): return bool(board_tiles(board))

def rack_counter(rack):
    cnt = Counter()
    for raw in rack:
        ch = normalize_letter(raw)
        if ch: cnt[ch] += 1
    return cnt

def board_counter(board):
    cnt = Counter()
    for _, _, ch in board_tiles(board): cnt[ch] += 1
    return cnt

def step(direction): return (0, 1) if direction == DIR_RIGHT else (1, 0)
def cell_at(direction, r, c, i):
    dr, dc = step(direction)
    return r + dr * i, c + dc * i

def line_in_bounds(board, r, c, direction, length):
    er, ec = cell_at(direction, r, c, length - 1)
    return in_bounds(board, r, c) and in_bounds(board, er, ec)

def before_after_clear(board, r, c, direction, length):
    dr, dc = step(direction)
    br, bc = r - dr, c - dc
    ar, ac = r + dr * length, c + dc * length
    if in_bounds(board, br, bc) and get_letter(board, br, bc): return False
    if in_bounds(board, ar, ac) and get_letter(board, ar, ac): return False
    return True

def neighbor_count(board, r, c):
    total = 0
    for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
        if in_bounds(board, nr, nc) and get_letter(board, nr, nc): total += 1
    return total

def passes_center(board, r, c, direction, length):
    cen = center(board)
    return any(cell_at(direction, r, c, i) == cen for i in range(length))

def perpendicular_fragments(board, r, c, direction):
    if direction == DIR_RIGHT: a1,b1,a2,b2 = -1,0,1,0
    else: a1,b1,a2,b2 = 0,-1,0,1
    prefix = []
    rr, cc = r + a1, c + b1
    while in_bounds(board, rr, cc):
        ch = get_letter(board, rr, cc)
        if not ch: break
        prefix.append(ch); rr += a1; cc += b1
    prefix.reverse()
    suffix = []
    rr, cc = r + a2, c + b2
    while in_bounds(board, rr, cc):
        ch = get_letter(board, rr, cc)
        if not ch: break
        suffix.append(ch); rr += a2; cc += b2
    return "".join(prefix), "".join(suffix)

def cross_ok(board, r, c, direction, ch, word_set, strict):
    prefix, suffix = perpendicular_fragments(board, r, c, direction)
    if not prefix and not suffix: return True
    if not strict: return True
    return f"{prefix}{ch}{suffix}" in word_set

def anchors(board):
    if not board_has_tiles(board): return [center(board)]
    pts = set()
    for r, c, _ in board_tiles(board):
        for nr, nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if in_bounds(board, nr, nc) and not get_letter(board, nr, nc): pts.add((nr,nc))
    cen = center(board)
    def rank(p):
        r,c = p; b = get_bonus(board,r,c)
        br = -10 if b in ("K3","H3") else -5 if b in ("K2","H2","START") else 0
        return (br, -neighbor_count(board,r,c), abs(r-cen[0])+abs(c-cen[1]), r, c)
    return sorted(pts, key=rank)

def word_available(info, available, jokers):
    missing = 0
    for ch, need in info.counter.items():
        have = available.get(ch, 0)
        if have < need:
            missing += need - have
            if missing > jokers: return False
    return True

def consume_word(board, word, r, c, direction, rack):
    left = rack.copy(); placed = []; jokers = set(); overlap = 0
    for i, ch in enumerate(word):
        rr, cc = cell_at(direction, r, c, i)
        existing = get_letter(board, rr, cc)
        if existing:
            if existing != ch: return None
            overlap += 1; continue
        if left.get(ch,0) > 0:
            left[ch] -= 1
            if left[ch] == 0: del left[ch]
        elif left.get("?",0) > 0:
            left["?"] -= 1
            if left["?"] == 0: del left["?"]
            jokers.add((rr,cc))
        else: return None
        placed.append((rr,cc,ch))
    return placed, jokers, overlap

def build_coords(board, r, c, direction, placed_map):
    dr, dc = step(direction)
    rr, cc = r, c
    while in_bounds(board, rr-dr, cc-dc):
        ch = placed_map.get((rr-dr, cc-dc)) or get_letter(board, rr-dr, cc-dc)
        if not ch: break
        rr -= dr; cc -= dc
    coords = []
    while in_bounds(board, rr, cc):
        ch = placed_map.get((rr,cc)) or get_letter(board, rr, cc)
        if not ch: break
        coords.append((rr,cc,ch)); rr += dr; cc += dc
    return coords

def score_coords(board, coords, newly, joker_map):
    total = 0; word_mul = 1
    for r,c,ch in coords:
        val = 0 if joker_map.get((r,c), False) else LETTER_SCORES.get(ch,0)
        if (r,c) in newly:
            b = get_bonus(board,r,c)
            if b in LETTER_MULTIPLIERS: val *= LETTER_MULTIPLIERS[b]
            elif b in WORD_MULTIPLIERS: word_mul *= WORD_MULTIPLIERS[b]
        total += val
    return total * word_mul

def make_move(board, word_set, word, r, c, direction, rack, require_connection, strict_cross, fallback=False):
    length = len(word)
    if not line_in_bounds(board, r, c, direction, length): return None
    if strict_cross and not before_after_clear(board, r, c, direction, length): return None
    empty = not board_has_tiles(board)
    if empty and not passes_center(board, r, c, direction, length): return None
    consumed = consume_word(board, word, r, c, direction, rack)
    if consumed is None: return None
    placed_raw, jokers, overlap = consumed
    if not placed_raw: return None
    placed_map = {}; joker_map = {}; newly = set(); placed = []; interaction = overlap
    for rr,cc,ch in placed_raw:
        if not cross_ok(board, rr, cc, direction, ch, word_set, strict_cross): return None
        is_joker = (rr,cc) in jokers
        placed_map[(rr,cc)] = ch; joker_map[(rr,cc)] = is_joker; newly.add((rr,cc))
        placed.append({"row": rr, "col": cc, "letter": ch, "is_joker": is_joker})
        if neighbor_count(board, rr, cc) > 0: interaction += 1
    if require_connection and not empty and interaction == 0: return None
    main_coords = build_coords(board, r, c, direction, placed_map)
    main_word = "".join(ch for _,_,ch in main_coords)
    if strict_cross and main_word not in word_set: return None
    total = score_coords(board, main_coords, newly, joker_map)
    cross_words = []; created_words = [main_word]
    cross_dir = DIR_DOWN if direction == DIR_RIGHT else DIR_RIGHT
    if strict_cross:
        for tile in placed:
            rr,cc = int(tile["row"]), int(tile["col"])
            coords = build_coords(board, rr, cc, cross_dir, placed_map)
            cw = "".join(ch for _,_,ch in coords)
            if len(cw) > 1:
                if cw not in word_set: return None
                cross_words.append(cw); created_words.append(cw)
                total += score_coords(board, coords, {(rr,cc)}, joker_map)
    if len(placed) == 7: total += 50
    return {"word": word, "row": r, "col": c, "direction": direction, "position": f"{direction} · {r+1} / {c+1}", "score": total, "placed": placed, "createdWords": created_words, "crossWords": cross_words, "interaction": interaction, "overlap": overlap, "connected": bool(empty or interaction > 0), "fallback": fallback}

class Collector:
    def __init__(self, limit):
        self.limit=limit; self.seen=set(); self.heap=[]; self.counter=0
    def add(self, move):
        key=(move["word"],move["row"],move["col"],move["direction"])
        if key in self.seen: return
        self.seen.add(key)
        rank=(int(move["score"]), 1 if move.get("connected") else 0, 0 if move.get("fallback") else 1, len(move["placed"]), len(move["word"]), -int(move["row"])-int(move["col"]))
        self.counter += 1; item=(rank,self.counter,move)
        if len(self.heap) < self.limit: heapq.heappush(self.heap,item)
        elif rank > self.heap[0][0]: heapq.heapreplace(self.heap,item)
    def results(self):
        out=[x[2] for x in self.heap]
        out.sort(key=lambda m:(-int(m["score"]), -int(bool(m.get("connected"))), int(bool(m.get("fallback"))), -len(m["placed"]), -len(m["word"]), m["word"]))
        return out

def candidate_starts(board, word, direction, anchor_list, tile_list, empty):
    n=len(word); starts=set()
    if empty:
        cr,cc=center(board)
        for i in range(n):
            r = cr - (i if direction == DIR_DOWN else 0)
            c = cc - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board,r,c,direction,n): starts.add((r,c))
        return list(starts)
    for ar,ac in anchor_list:
        for i in range(n):
            r = ar - (i if direction == DIR_DOWN else 0)
            c = ac - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board,r,c,direction,n): starts.add((r,c))
    positions=defaultdict(list)
    for i,ch in enumerate(word): positions[ch].append(i)
    for tr,tc,tch in tile_list:
        for i in positions.get(tch,[]):
            r = tr - (i if direction == DIR_DOWN else 0)
            c = tc - (i if direction == DIR_RIGHT else 0)
            if line_in_bounds(board,r,c,direction,n): starts.add((r,c))
    return list(starts)

def empty_starts_for_fallback(board, word_len, direction):
    n=size(board); starts=[]
    for r in range(n):
        for c in range(n):
            if not line_in_bounds(board,r,c,direction,word_len): continue
            ok=True
            for i in range(word_len):
                rr,cc=cell_at(direction,r,c,i)
                if get_letter(board,rr,cc): ok=False; break
            if ok: starts.append((r,c))
    return starts

def fallback_search(board,index,rack_cnt,collector,deadline,max_checks):
    checks=0; rack_total=sum(rack_cnt.values()); jokers=rack_cnt.get("?",0); n=size(board)
    for info in index.words:
        if time.time() > deadline or checks >= max_checks: break
        if info.length > min(n,rack_total): continue
        if not word_available(info,rack_cnt,jokers): continue
        for direction in (DIR_RIGHT,DIR_DOWN):
            for r,c in empty_starts_for_fallback(board,info.length,direction):
                if time.time() > deadline or checks >= max_checks: return
                checks += 1
                move=make_move(board,index.word_set,info.word,r,c,direction,rack_cnt,False,False,True)
                if move:
                    collector.add(move)
                    if len(collector.heap) >= 80: return

def generate_moves(board, rack, index, limit=500, seconds=8.0, max_checks=500_000, **_kwargs):
    start=time.time(); deadline=start+seconds
    rack_cnt=rack_counter(rack); rack_total=sum(rack_cnt.values())
    if rack_total == 0: return {"suggestions": [], "debug": {"reason":"empty_rack", "wordCount":len(index.word_set)}}
    if len(index.word_set) == 0: return {"suggestions": [], "debug": {"reason":"empty_dictionary", "wordCount":0}}
    empty=not board_has_tiles(board); n=size(board); max_len=min(n, rack_total if empty else rack_total+10)
    available=rack_cnt+board_counter(board); jokers=rack_cnt.get("?",0); anchor_list=anchors(board); tile_list=board_tiles(board)
    collector=Collector(max(20,limit)); checks=0; strict_found=0; loose_found=0
    for info in index.words:
        if time.time() > deadline or checks >= max_checks: break
        if info.length > max_len: continue
        if not word_available(info,available,jokers): continue
        for direction in (DIR_RIGHT,DIR_DOWN):
            for r,c in candidate_starts(board,info.word,direction,anchor_list,tile_list,empty):
                if time.time() > deadline or checks >= max_checks: break
                checks += 1
                move=make_move(board,index.word_set,info.word,r,c,direction,rack_cnt,True,True,False)
                if move: collector.add(move); strict_found += 1
        if len(collector.heap) >= limit and time.time()-start > seconds*0.30: break
    if len(collector.heap) < 10 and time.time() < deadline:
        loose_limit=max_checks//3; loose_checks=0
        for info in index.words:
            if time.time() > deadline or loose_checks >= loose_limit: break
            if info.length > max_len: continue
            if not word_available(info,available,jokers): continue
            for direction in (DIR_RIGHT,DIR_DOWN):
                for r,c in candidate_starts(board,info.word,direction,anchor_list,tile_list,empty):
                    if time.time() > deadline or loose_checks >= loose_limit: break
                    loose_checks += 1
                    move=make_move(board,index.word_set,info.word,r,c,direction,rack_cnt,True,False,False)
                    if move:
                        collector.add(move); loose_found += 1
                        if len(collector.heap) >= 80: break
    if len(collector.heap) == 0 and time.time() < deadline:
        fallback_search(board,index,rack_cnt,collector,deadline,max(50_000,max_checks//4))
    results=collector.results()[:limit]
    return {"suggestions": results, "debug": {"wordCount":len(index.word_set), "rack":list(rack_cnt.elements()), "boardTiles":len(tile_list), "checks":checks, "strictFound":strict_found, "looseFound":loose_found, "returned":len(results), "usedFallback": bool(results and results[0].get("fallback"))}}
