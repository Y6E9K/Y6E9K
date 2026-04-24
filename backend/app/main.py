from pathlib import Path
from typing import Any, List
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from .engine.solver import build_dictionary_index, generate_moves

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / 'data'

def load_dictionary_words() -> List[str]:
    words=[]
    if DATA_DIR.exists():
        for p in DATA_DIR.glob('*'):
            if p.is_file():
                try:
                    words += [x.strip() for x in p.read_text(encoding='utf-8', errors='ignore').splitlines() if x.strip()]
                except Exception:
                    pass
    return words

WORDS=load_dictionary_words()
DICT_INDEX=build_dictionary_index(WORDS)

class SolveRequest(BaseModel):
    boardType: str
    board: List[List[Any]]
    rack: List[str]
    mode: str = 'fast'

app=FastAPI(title='Kelime Asistanı API')
app.add_middleware(CORSMiddleware, allow_origins=['*'], allow_credentials=True, allow_methods=['*'], allow_headers=['*'])

@app.get('/')
def root():
    return {'ok': True, 'name':'Kelime Asistanı API', 'docs':'/docs', 'wordCount':len(DICT_INDEX.word_set), 'files':len(list(DATA_DIR.glob('*'))) if DATA_DIR.exists() else 0}

@app.get('/api/health')
def health():
    return {'ok': True, 'wordCount':len(DICT_INDEX.word_set), 'files':len(list(DATA_DIR.glob('*'))) if DATA_DIR.exists() else 0}

@app.get('/api/board/{board_type}')
def get_board(board_type: str):
    if board_type == '9x9':
        size=9
        bonus_grid=[
            ['K3',None,None,None,'H3',None,None,None,'K3'],
            [None,'K2',None,'H2',None,'H2',None,'K2',None],
            [None,None,'H3',None,None,None,'H3',None,None],
            [None,'H2',None,None,None,None,None,'H2',None],
            ['H3',None,None,None,'START',None,None,None,'H3'],
            [None,'H2',None,None,None,None,None,'H2',None],
            [None,None,'H3',None,None,None,'H3',None,None],
            [None,'K2',None,'H2',None,'H2',None,'K2',None],
            ['K3',None,None,None,'H3',None,None,None,'K3'],
        ]
    else:
        size=15
        bonus_grid=[
            [None,None,'K3',None,None,'H2',None,None,None,'H2',None,None,'K3',None,None],
            [None,'H3',None,None,None,None,'H2',None,'H2',None,None,None,None,'H3',None],
            ['K3',None,None,None,None,None,None,'K2',None,None,None,None,None,None,'K3'],
            [None,None,None,'K2',None,None,None,None,None,None,None,'K2',None,None,None],
            [None,None,None,None,'H3',None,None,None,None,None,'H3',None,None,None,None],
            ['H2',None,None,None,None,'H2',None,None,None,'H2',None,None,None,None,'H2'],
            [None,'H2',None,None,None,None,'H2',None,'H2',None,None,None,None,'H2',None],
            [None,None,'K2',None,None,None,None,'START',None,None,None,None,'K2',None,None],
            [None,'H2',None,None,None,None,'H2',None,'H2',None,None,None,None,'H2',None],
            ['H2',None,None,None,None,'H2',None,None,None,'H2',None,None,None,None,'H2'],
            [None,None,None,None,'H3',None,None,None,None,None,'H3',None,None,None,None],
            [None,None,None,'K2',None,None,None,None,None,None,None,'K2',None,None,None],
            ['K3',None,None,None,None,None,None,'K2',None,None,None,None,None,None,'K3'],
            [None,'H3',None,None,None,None,'H2',None,'H2',None,None,None,None,'H3',None],
            [None,None,'K3',None,None,'H2',None,None,None,'H2',None,None,'K3',None,None],
        ]
    return {'boardType':board_type, 'size':size, 'bonusGrid':bonus_grid, 'center':[size//2,size//2]}

@app.post('/api/solve')
def solve(payload: SolveRequest):
    try:
        mode = payload.mode if payload.mode in ('fast','max') else 'fast'
        cfg = {
            'fast': dict(limit=500, seconds=30.0, max_checks=1800000, backtrack_extra=20, allow_disconnected=False),
            'max': dict(limit=1200, seconds=45.0, max_checks=4000000, backtrack_extra=40, allow_disconnected=True),
        }[mode]
        suggestions=generate_moves(board=payload.board, rack=payload.rack, index=DICT_INDEX, **cfg)
        return {'suggestions': suggestions, 'mode': mode}
    except Exception as e:
        print('SOLVE ERROR:', e)
        return {'suggestions': [], 'error': str(e)}
