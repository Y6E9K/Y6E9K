from __future__ import annotations
import heapq, time
from collections import Counter
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Set, Tuple

DIR_RIGHT='YATAY'; DIR_DOWN='DIKEY'
TR_MAP={'i':'İ','ı':'I','ş':'Ş','ğ':'Ğ','ü':'Ü','ö':'Ö','ç':'Ç'}
LETTER_SCORES={'A':1,'B':3,'C':4,'Ç':4,'D':3,'E':1,'F':7,'G':5,'Ğ':8,'H':5,'I':2,'İ':1,'J':10,'K':1,'L':1,'M':2,'N':1,'O':2,'Ö':7,'P':5,'R':1,'S':2,'Ş':4,'T':1,'U':2,'Ü':3,'V':7,'Y':3,'Z':4,'?':0}
WORD_MULTIPLIERS={'K2':2,'K3':3,'START':2}; LETTER_MULTIPLIERS={'H2':2,'H3':3}
TR_LETTERS=tuple(ch for ch in LETTER_SCORES if ch!='?')

def normalize_letter(ch:str)->str:
    if not ch: return ''
    ch=str(ch).strip()[:1]
    return TR_MAP.get(ch, ch.upper().replace('İ','İ'))
def normalize_word(w:str)->str: return ''.join(normalize_letter(c) for c in str(w) if str(c).strip())
def is_valid_word(w:str)->bool: return len(w)>=2 and all(c in LETTER_SCORES and c!='?' for c in w)
class TrieNode:
    __slots__=('children','terminal')
    def __init__(self): self.children={}; self.terminal=False
@dataclass
class DictionaryIndex:
    word_set:Set[str]; words_by_length:Dict[int,List[str]]; trie:TrieNode; words:List[str]; letters:Tuple[str,...]=field(default_factory=lambda:TR_LETTERS)
def build_dictionary_index(words:Iterable[str])->DictionaryIndex:
    ws=set(); by={}; clean=[]; trie=TrieNode()
    for raw in words:
        w=normalize_word(raw)
        if not is_valid_word(w) or w in ws: continue
        ws.add(w); clean.append(w); by.setdefault(len(w),[]).append(w)
        node=trie
        for c in w: node=node.children.setdefault(c,TrieNode())
        node.terminal=True
    clean.sort(key=lambda w:(-sum(LETTER_SCORES.get(c,0) for c in w),-len(w),w))
    return DictionaryIndex(ws,by,trie,clean)

def size(board): return len(board)
def inb(board,r,c): return 0<=r<size(board) and 0<=c<size(board)
def center(board): s=size(board); return s//2,s//2
def cell(board,r,c): return board[r][c]
def get_letter(board,r,c):
    if not inb(board,r,c): return ''
    x=cell(board,r,c)
    return normalize_letter(x.get('letter','') if isinstance(x,dict) else x)
def get_bonus(board,r,c):
    if not inb(board,r,c): return None
    x=cell(board,r,c); return x.get('bonus') if isinstance(x,dict) else None
def board_has_tiles(board):
    return any(get_letter(board,r,c) for r in range(size(board)) for c in range(size(board)))
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
            ch=get_letter(board,r,c)
            if ch: cnt[ch]+=1
    return cnt

def before(direction,r,c): return (r,c-1) if direction==DIR_RIGHT else (r-1,c)
def line_letters(board,r,c,direction,length):
    out=[]
    for i in range(length):
        rr=r+(i if direction==DIR_DOWN else 0); cc=c+(i if direction==DIR_RIGHT else 0)
        if not inb(board,rr,cc): return None
        out.append(get_letter(board,rr,cc))
    return out
def has_blocking(board,r,c,direction,length):
    br,bc=before(direction,r,c); ar=r+(length if direction==DIR_DOWN else 0); ac=c+(length if direction==DIR_RIGHT else 0)
    return (inb(board,br,bc) and get_letter(board,br,bc)) or (inb(board,ar,ac) and get_letter(board,ar,ac))
def passes_center(r,c,direction,length,ctr):
    return any((r+(i if direction==DIR_DOWN else 0), c+(i if direction==DIR_RIGHT else 0))==ctr for i in range(length))
def touches_neighbor(board,r,c,direction):
    ns=((r-1,c),(r+1,c)) if direction==DIR_RIGHT else ((r,c-1),(r,c+1))
    return any(inb(board,nr,nc) and get_letter(board,nr,nc) for nr,nc in ns)
def word_coords(board,r,c,direction,placed_map):
    dr,dc=(0,1) if direction==DIR_RIGHT else (1,0)
    rr,cc=r,c
    while inb(board,rr-dr,cc-dc):
        ch=placed_map.get((rr-dr,cc-dc)) or get_letter(board,rr-dr,cc-dc)
        if not ch: break
        rr-=dr; cc-=dc
    out=[]
    while inb(board,rr,cc):
        ch=placed_map.get((rr,cc)) or get_letter(board,rr,cc)
        if not ch: break
        out.append((rr,cc,ch)); rr+=dr; cc+=dc
    return out
def coords_word(coords): return ''.join(ch for _,_,ch in coords)
def score_coords(board,coords,new,jokers):
    total=0; mul=1
    for r,c,ch in coords:
        score=0 if jokers.get((r,c),False) else LETTER_SCORES.get(ch,0)
        if (r,c) in new:
            b=get_bonus(board,r,c)
            if b in LETTER_MULTIPLIERS: score*=LETTER_MULTIPLIERS[b]
            elif b in WORD_MULTIPLIERS: mul*=WORD_MULTIPLIERS[b]
        total+=score
    return total*mul

def perp_frag(board,r,c,direction):
    if direction==DIR_RIGHT: a=(-1,0); b=(1,0)
    else: a=(0,-1); b=(0,1)
    left=[]; rr=r+a[0]; cc=c+a[1]
    while inb(board,rr,cc) and get_letter(board,rr,cc): left.append(get_letter(board,rr,cc)); rr+=a[0]; cc+=a[1]
    left.reverse(); right=[]; rr=r+b[0]; cc=c+b[1]
    while inb(board,rr,cc) and get_letter(board,rr,cc): right.append(get_letter(board,rr,cc)); rr+=b[0]; cc+=b[1]
    return ''.join(left),''.join(right)
def cross_valid(board,r,c,direction,ch,word_set):
    p,s=perp_frag(board,r,c,direction)
    return True if not p and not s else (p+ch+s) in word_set

def anchors(board):
    if not board_has_tiles(board): return [center(board)]
    out=set()
    for r in range(size(board)):
        for c in range(size(board)):
            if get_letter(board,r,c):
                for nr,nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)):
                    if inb(board,nr,nc) and not get_letter(board,nr,nc): out.add((nr,nc))
    ctr=center(board)
    def rank(rc):
        r,c=rc; b=get_bonus(board,r,c); bonus=-10 if b in ('K3','H3') else (-5 if b in ('K2','H2','START') else 0)
        dens=-sum(1 for nr,nc in ((r-1,c),(r+1,c),(r,c-1),(r,c+1)) if inb(board,nr,nc) and get_letter(board,nr,nc))
        return bonus,dens,abs(r-ctr[0])+abs(c-ctr[1]),r,c
    return sorted(out,key=rank)

def consume(board,word,r,c,direction,rack):
    line=line_letters(board,r,c,direction,len(word))
    if line is None: return None
    left=rack.copy(); jok=set()
    for i,ch in enumerate(word):
        rr=r+(i if direction==DIR_DOWN else 0); cc=c+(i if direction==DIR_RIGHT else 0)
        ex=line[i]
        if ex:
            if ex!=ch: return None
            continue
        if left.get(ch,0)>0:
            left[ch]-=1
            if left[ch]==0: del left[ch]
        elif left.get('?',0)>0:
            left['?']-=1
            if left['?']==0: del left['?']
            jok.add((rr,cc))
        else: return None
    return jok

def compute(board,word_set,word,r,c,direction,joker_positions=None,require_connection=True):
    if joker_positions is None: joker_positions=set()
    line=line_letters(board,r,c,direction,len(word))
    if line is None or has_blocking(board,r,c,direction,len(word)): return None
    empty=not board_has_tiles(board)
    if empty and not passes_center(r,c,direction,len(word),center(board)): return None
    placed=[]; pmap={}; jmap={}; new=set(); inter=0; overlap=0
    for i,ch in enumerate(word):
        rr=r+(i if direction==DIR_DOWN else 0); cc=c+(i if direction==DIR_RIGHT else 0); ex=line[i]
        if ex:
            if ex!=ch: return None
            overlap+=1; inter+=1
        else:
            if not cross_valid(board,rr,cc,direction,ch,word_set): return None
            isj=(rr,cc) in joker_positions
            placed.append({'row':rr,'col':cc,'letter':ch,'is_joker':isj}); pmap[(rr,cc)]=ch; jmap[(rr,cc)]=isj; new.add((rr,cc))
            if touches_neighbor(board,rr,cc,direction): inter+=1
    if not placed: return None
    if not empty and require_connection and inter==0 and overlap==0: return None
    main=word_coords(board,r,c,direction,pmap); mainword=coords_word(main)
    if mainword!=word or mainword not in word_set: return None
    total=score_coords(board,main,new,jmap); cross=[]; created=[mainword]; crossdir=DIR_DOWN if direction==DIR_RIGHT else DIR_RIGHT
    for t in placed:
        cr=word_coords(board,t['row'],t['col'],crossdir,pmap); cw=coords_word(cr)
        if len(cw)>1:
            if cw not in word_set: return None
            cross.append(cw); created.append(cw); total+=score_coords(board,cr,{(t['row'],t['col'])},jmap)
    if len(placed)==7: total+=50
    return {'word':word,'row':r,'col':c,'direction':direction,'position':f'{direction} · {r+1} / {c+1}','score':total,'placed':placed,'createdWords':created,'crossWords':cross,'interaction':inter,'overlap':overlap,'connected':bool(inter or overlap or empty)}

class TopCollector:
    def __init__(self,limit): self.limit=limit; self.heap=[]; self.seen=set(); self.counter=0
    def rank(self,m): return (int(m['score']),int(m.get('connected',False)),len(m['placed']),int(m['interaction']),len(m['word']),-int(m['row']),-int(m['col']))
    def add(self,m):
        key=(m['word'],m['row'],m['col'],m['direction'])
        if key in self.seen: return
        self.seen.add(key); self.counter+=1; entry=(self.rank(m),self.counter,m)
        if len(self.heap)<self.limit: heapq.heappush(self.heap,entry)
        elif entry[0]>self.heap[0][0]: heapq.heapreplace(self.heap,entry)
    def results(self):
        items=[x[2] for x in self.heap]
        items.sort(key=lambda m:(-int(m['score']),-int(m.get('connected',False)),-len(m['placed']),-int(m['interaction']),-len(m['word']),m['word'],int(m['row']),int(m['col'])))
        return items

def starts(board,word_len,direction,anchor_list,backtrack_extra,allow_all):
    out=set(); s=size(board)
    for ar,ac in anchor_list:
        for i in range(word_len+backtrack_extra+2):
            r=ar-(i if direction==DIR_DOWN else 0); c=ac-(i if direction==DIR_RIGHT else 0)
            er=r+((word_len-1) if direction==DIR_DOWN else 0); ec=c+((word_len-1) if direction==DIR_RIGHT else 0)
            if inb(board,r,c) and inb(board,er,ec): out.add((r,c))
    if allow_all:
        for r in range(s):
            for c in range(s):
                er=r+((word_len-1) if direction==DIR_DOWN else 0); ec=c+((word_len-1) if direction==DIR_RIGHT else 0)
                if inb(board,er,ec): out.add((r,c))
    return list(out)

def possible(word,available,jokers):
    need=Counter(word); miss=0
    for ch,n in need.items():
        have=available.get(ch,0)
        if have<n:
            miss+=n-have
            if miss>jokers: return False
    return True

def generate_moves(board,rack,index,limit=500,seconds=30.0,max_checks=1800000,backtrack_extra=20,allow_disconnected=False):
    start=time.time(); deadline=start+seconds; rackcnt=rack_counter(rack)
    if sum(rackcnt.values())==0: return []
    empty=not board_has_tiles(board); max_len=min(size(board),max(2,sum(rackcnt.values())+(10 if empty else 14)))
    an=anchors(board); available=rackcnt+board_counter(board); jokers=rackcnt.get('?',0); coll=TopCollector(max(20,limit)); checks=0
    for word in index.words:
        if time.time()>deadline or checks>=max_checks: break
        if len(word)>max_len or not possible(word,available,jokers): continue
        for direction in (DIR_RIGHT,DIR_DOWN):
            for r,c in starts(board,len(word),direction,an,backtrack_extra,allow_all=(empty or backtrack_extra>=20)):
                if time.time()>deadline or checks>=max_checks: break
                checks+=1
                if has_blocking(board,r,c,direction,len(word)): continue
                jp=consume(board,word,r,c,direction,rackcnt)
                if jp is None: continue
                m=compute(board,index.word_set,word,r,c,direction,jp,require_connection=True)
                if m: coll.add(m)
    if allow_disconnected and time.time()<deadline and len(coll.heap)<max(50,limit//5):
        for word in index.words:
            if time.time()>deadline or checks>=max_checks: break
            if len(word)>min(size(board),sum(rackcnt.values())) or not possible(word,rackcnt,jokers): continue
            for direction in (DIR_RIGHT,DIR_DOWN):
                for r,c in starts(board,len(word),direction,an or [center(board)],backtrack_extra,allow_all=True):
                    if time.time()>deadline or checks>=max_checks: break
                    checks+=1
                    if has_blocking(board,r,c,direction,len(word)): continue
                    jp=consume(board,word,r,c,direction,rackcnt)
                    if jp is None: continue
                    m=compute(board,index.word_set,word,r,c,direction,jp,require_connection=False)
                    if m: coll.add(m)
    return coll.results()[:limit]
