from __future__ import annotations
import time, heapq
from collections import Counter
from dataclasses import dataclass
from typing import Dict, Iterable, List, Set

DIR_RIGHT="YATAY"; DIR_DOWN="DIKEY"
TR_MAP={"i":"İ","ı":"I","ş":"Ş","ğ":"Ğ","ü":"Ü","ö":"Ö","ç":"Ç"}
LETTER_SCORES={"A":1,"B":3,"C":4,"Ç":4,"D":3,"E":1,"F":7,"G":5,"Ğ":8,"H":5,"I":2,"İ":1,"J":10,"K":1,"L":1,"M":2,"N":1,"O":2,"Ö":7,"P":5,"R":1,"S":2,"Ş":4,"T":1,"U":2,"Ü":3,"V":7,"Y":3,"Z":4,"?":0}
WORD_MULTIPLIERS={"K2":2,"K3":3,"START":2}; LETTER_MULTIPLIERS={"H2":2,"H3":3}

def normalize_letter(ch:str)->str:
    if not ch: return ""
    ch=str(ch).strip()[:1]
    return TR_MAP.get(ch, ch.upper().replace("İ","İ"))

def normalize_word(w:str)->str:
    return "".join(normalize_letter(c) for c in str(w) if str(c).strip())

def is_valid_word(w:str)->bool:
    return len(w)>=2 and all(c in LETTER_SCORES and c!="?" for c in w)

@dataclass
class DictionaryIndex:
    word_set:Set[str]
    words_by_length:Dict[int,List[str]]
    words:List[str]

def build_dictionary_index(words:Iterable[str])->DictionaryIndex:
    word_set=set(); by_len={}; clean=[]
    for raw in words:
        w=normalize_word(raw)
        if not is_valid_word(w) or w in word_set: continue
        word_set.add(w); clean.append(w); by_len.setdefault(len(w),[]).append(w)
    clean.sort(key=lambda w:(-sum(LETTER_SCORES.get(c,0) for c in w), -len(w), w))
    return DictionaryIndex(word_set=word_set, words_by_length=by_len, words=clean)

def size(board): return len(board)
def inb(board,r,c): return 0<=r<size(board) and 0<=c<size(board)
def center(board): s=size(board); return (s//2,s//2)
def letter(board,r,c):
    if not inb(board,r,c): return ""
    x=board[r][c]
    return normalize_letter(x.get("letter","") if isinstance(x,dict) else x)
def bonus(board,r,c):
    if not inb(board,r,c): return None
    x=board[r][c]
    return x.get("bonus") if isinstance(x,dict) else None
def has_tiles(board): return any(letter(board,r,c) for r in range(size(board)) for c in range(size(board)))
def rack_counter(rack):
    cnt=Counter()
    for ch in rack:
        n=normalize_letter(ch)
        if n: cnt[n]+=1
    return cnt
def board_counter(board):
    cnt=Counter()
    for r in range(size(board)):
        for c in range(size(board)):
            ch=letter(board,r,c)
            if ch: cnt[ch]+=1
    return cnt

def anchors(board):
    if not has_tiles(board): return [center(board)]
    a=set(); cen=center(board)
    for r in range(size(board)):
        for c in range(size(board)):
            if letter(board,r,c):
                for nr,nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                    if inb(board,nr,nc) and not letter(board,nr,nc): a.add((nr,nc))
    def rank(rc):
        r,c=rc; bs=0; den=0
        for nr,nc in ((r,c),(r-1,c),(r+1,c),(r,c-1),(r,c+1)):
            if inb(board,nr,nc):
                b=bonus(board,nr,nc)
                if b in ("K3","H3"): bs-=5
                elif b in ("K2","H2","START"): bs-=3
                if letter(board,nr,nc): den-=1
        return (bs,den,abs(r-cen[0])+abs(c-cen[1]))
    return sorted(a,key=rank)

def before(direction,r,c): return (r,c-1) if direction==DIR_RIGHT else (r-1,c)
def line_letters(board,r,c,d,l):
    out=[]
    for i in range(l):
        rr=r+(i if d==DIR_DOWN else 0); cc=c+(i if d==DIR_RIGHT else 0)
        if not inb(board,rr,cc): return None
        out.append(letter(board,rr,cc))
    return out

def blocked(board,r,c,d,l):
    br,bc=before(d,r,c); ar=r+(l if d==DIR_DOWN else 0); ac=c+(l if d==DIR_RIGHT else 0)
    return (inb(board,br,bc) and letter(board,br,bc)) or (inb(board,ar,ac) and letter(board,ar,ac))

def passes_center(board,r,c,d,l):
    cen=center(board)
    return any((r+(i if d==DIR_DOWN else 0), c+(i if d==DIR_RIGHT else 0))==cen for i in range(l))

def touches(board,r,c,d):
    ns=((r-1,c),(r+1,c)) if d==DIR_RIGHT else ((r,c-1),(r,c+1))
    return any(inb(board,nr,nc) and letter(board,nr,nc) for nr,nc in ns)

def word_coords(board,r,c,d,placed):
    dr,dc=(0,1) if d==DIR_RIGHT else (1,0)
    rr,cc=r,c
    while inb(board,rr-dr,cc-dc) and (placed.get((rr-dr,cc-dc)) or letter(board,rr-dr,cc-dc)):
        rr-=dr; cc-=dc
    out=[]
    while inb(board,rr,cc):
        ch=placed.get((rr,cc)) or letter(board,rr,cc)
        if not ch: break
        out.append((rr,cc,ch)); rr+=dr; cc+=dc
    return out

def coords_word(coords): return "".join(ch for _,_,ch in coords)

def score_coords(board,coords,new,jokers):
    total=0; wm=1
    for r,c,ch in coords:
        sc=0 if jokers.get((r,c),False) else LETTER_SCORES.get(ch,0)
        if (r,c) in new:
            b=bonus(board,r,c)
            if b in LETTER_MULTIPLIERS: sc*=LETTER_MULTIPLIERS[b]
            elif b in WORD_MULTIPLIERS: wm*=WORD_MULTIPLIERS[b]
        total+=sc
    return total*wm

def perp_frag(board,r,c,d):
    if d==DIR_RIGHT: a=(-1,0); b=(1,0)
    else: a=(0,-1); b=(0,1)
    left=[]; rr=r+a[0]; cc=c+a[1]
    while inb(board,rr,cc) and letter(board,rr,cc): left.append(letter(board,rr,cc)); rr+=a[0]; cc+=a[1]
    left.reverse(); right=[]; rr=r+b[0]; cc=c+b[1]
    while inb(board,rr,cc) and letter(board,rr,cc): right.append(letter(board,rr,cc)); rr+=b[0]; cc+=b[1]
    return "".join(left),"".join(right)

def cross_ok(board,r,c,d,ch,word_set):
    p,s=perp_frag(board,r,c,d)
    return True if not p and not s else (p+ch+s) in word_set

def consume(board,word,r,c,d,rack):
    line=line_letters(board,r,c,d,len(word))
    if line is None: return None
    left=rack.copy(); jok=set()
    for i,ch in enumerate(word):
        rr=r+(i if d==DIR_DOWN else 0); cc=c+(i if d==DIR_RIGHT else 0); ex=line[i]
        if ex:
            if ex!=ch: return None
        elif left.get(ch,0)>0:
            left[ch]-=1
            if left[ch]==0: del left[ch]
        elif left.get("?",0)>0:
            left["?"]-=1
            if left["?"]==0: del left["?"]
            jok.add((rr,cc))
        else: return None
    return jok

def validate(board,word_set,word,r,c,d,rack):
    if not inb(board,r,c) or blocked(board,r,c,d,len(word)): return None
    if not has_tiles(board) and not passes_center(board,r,c,d,len(word)): return None
    jokpos=consume(board,word,r,c,d,rack)
    if jokpos is None: return None
    line=line_letters(board,r,c,d,len(word)); placed=[]; pmap={}; jmap={}; new=set(); inter=0; overlap=0
    for i,ch in enumerate(word):
        rr=r+(i if d==DIR_DOWN else 0); cc=c+(i if d==DIR_RIGHT else 0); ex=line[i]
        if ex: overlap+=1; inter+=1
        else:
            if not cross_ok(board,rr,cc,d,ch,word_set): return None
            isj=(rr,cc) in jokpos
            placed.append({"row":rr,"col":cc,"letter":ch,"is_joker":isj})
            pmap[(rr,cc)]=ch; jmap[(rr,cc)]=isj; new.add((rr,cc))
            if touches(board,rr,cc,d): inter+=1
    if not placed or (has_tiles(board) and inter==0 and overlap==0): return None
    main=word_coords(board,r,c,d,pmap); mw=coords_word(main)
    if mw!=word or mw not in word_set: return None
    total=score_coords(board,main,new,jmap); cross_words=[]; created=[mw]; cd=DIR_DOWN if d==DIR_RIGHT else DIR_RIGHT
    for t in placed:
        cr=word_coords(board,int(t["row"]),int(t["col"]),cd,pmap); cw=coords_word(cr)
        if len(cw)>1:
            if cw not in word_set: return None
            cross_words.append(cw); created.append(cw); total+=score_coords(board,cr,{(int(t["row"]),int(t["col"]))},jmap)
    if len(placed)==7: total+=50
    return {"word":word,"row":r,"col":c,"direction":d,"position":f"{d} · {r+1} / {c+1}","score":total,"placed":placed,"createdWords":created,"crossWords":cross_words,"interaction":inter,"overlap":overlap}

class Top:
    def __init__(self,limit): self.limit=limit; self.heap=[]; self.seen=set(); self.i=0
    def rank(self,m): return (int(m["score"]),len(m["placed"]),int(m["interaction"]),len(m["word"]),-int(m["row"]),-int(m["col"]))
    def add(self,m):
        k=(m["word"],m["row"],m["col"],m["direction"])
        if k in self.seen: return
        self.seen.add(k); self.i+=1; e=(self.rank(m),self.i,m)
        if len(self.heap)<self.limit: heapq.heappush(self.heap,e)
        elif e[0]>self.heap[0][0]: heapq.heapreplace(self.heap,e)
    def results(self):
        out=[e[2] for e in self.heap]
        out.sort(key=lambda m:(-int(m["score"]),-len(m["placed"]),-int(m["interaction"]),-len(m["word"]),m["word"],int(m["row"]),int(m["col"])))
        return out

def starts_for(board,word_len,d,anch,all_starts,extra):
    st=set(); n=size(board)
    if all_starts:
        for r in range(n):
            for c in range(n):
                er=r+(word_len-1 if d==DIR_DOWN else 0); ec=c+(word_len-1 if d==DIR_RIGHT else 0)
                if inb(board,er,ec): st.add((r,c))
        return list(st)
    for ar,ac in anch:
        for i in range(word_len+extra+2):
            r=ar-(i if d==DIR_DOWN else 0); c=ac-(i if d==DIR_RIGHT else 0)
            er=r+(word_len-1 if d==DIR_DOWN else 0); ec=c+(word_len-1 if d==DIR_RIGHT else 0)
            if inb(board,r,c) and inb(board,er,ec): st.add((r,c))
    return list(st)

def generate_moves(board,rack,index,limit=180,seconds=8.0,checks=500000,all_starts=False,extra=8):
    deadline=time.time()+seconds; rackcnt=rack_counter(rack); avail=rackcnt+board_counter(board); top=Top(limit); anch=anchors(board); n=size(board); empty=not has_tiles(board)
    max_len=min(n, max(2, len(rack)+(10 if empty else 14)))
    count=0
    for word in index.words:
        if time.time()>deadline or count>=checks: break
        if len(word)>max_len: continue
        need=Counter(word); missing=sum(max(0,cnt-avail.get(ch,0)) for ch,cnt in need.items())
        if missing>rackcnt.get("?",0): continue
        for d in (DIR_RIGHT,DIR_DOWN):
            for r,c in starts_for(board,len(word),d,anch,all_starts,extra):
                if time.time()>deadline or count>=checks: break
                count+=1
                m=validate(board,index.word_set,word,r,c,d,rackcnt)
                if m: top.add(m)
    return top.results()[:limit]
