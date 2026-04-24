from pathlib import Path
from typing import Any, List, Literal

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine.solver import build_dictionary_index, generate_moves

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

def load_dictionary_words() -> List[str]:
    words: List[str] = []
    if not DATA_DIR.exists():
        return words
    for file_path in DATA_DIR.glob("*"):
        if not file_path.is_file():
            continue
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            continue
        for line in content.splitlines():
            line = line.strip()
            if line:
                words.append(line)
    return words

WORDS = load_dictionary_words()
DICT_INDEX = build_dictionary_index(WORDS)

class SolveRequest(BaseModel):
    boardType: str
    board: List[List[Any]]
    rack: List[str]
    mode: Literal["fast", "deep", "max"] = "deep"

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/solve")
def solve(payload: SolveRequest):
    mode_settings = {
        "max": {
            "limit": 500,
            "fast_seconds": 3.0,
            "deep_seconds": 30.0,
            "fast_nodes": 150000,
            "deep_nodes": 3000000,
            "backtrack_extra": 20,
        }
    }

    settings = mode_settings["max"]

    suggestions = generate_moves(
        board=payload.board,
        rack=payload.rack,
        index=DICT_INDEX,
        limit=settings["limit"],
        fast_seconds=settings["fast_seconds"],
        deep_seconds=settings["deep_seconds"],
        fast_nodes=settings["fast_nodes"],
        deep_nodes=settings["deep_nodes"],
        backtrack_extra=settings["backtrack_extra"],
    )

    return {"suggestions": suggestions}
