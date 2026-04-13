from pathlib import Path
from typing import List, Any

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine.solver import generate_moves


BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"


def load_dictionary_words() -> List[str]:
    words: List[str] = []

    if not DATA_DIR.exists():
        return words

    for file_path in DATA_DIR.glob("*"):
      if file_path.is_file():
            try:
                content = file_path.read_text(encoding="utf-8", errors="ignore")
                for line in content.splitlines():
                    line = line.strip()
                    if line:
                        words.append(line)
            except Exception:
                continue

    return words


class SolveRequest(BaseModel):
    boardType: str
    board: List[List[Any]]
    rack: List[str]


app = FastAPI(title="Kelime Asistanı API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    words = load_dictionary_words()
    return {
        "ok": True,
        "name": "Kelime Asistanı API",
        "docs": "/docs",
        "wordCount": len(words),
        "files": len(list(DATA_DIR.glob("*"))) if DATA_DIR.exists() else 0,
    }


@app.get("/api/health")
def health():
    words = load_dictionary_words()
    return {
        "ok": True,
        "wordCount": len(words),
        "files": len(list(DATA_DIR.glob("*"))) if DATA_DIR.exists() else 0,
    }


@app.get("/api/board/{board_type}")
def get_board(board_type: str):
    size = 9 if board_type == "9x9" else 15

    if size == 15:
        bonus_grid = [
            [None, None, "K3", None, None, "H2", None, None, None, "H2", None, None, "K3", None, None],
            [None, "H3", None, None, None, None, "H2", None, "H2", None, None, None, None, "H3", None],
            ["K3", None, None, None, None, None, None, "K2", None, None, None, None, None, None, "K3"],
            [None, None, None, "K2", None, None, None, None, None, None, None, "K2", None, None, None],
            [None, None, None, None, "H3", None, None, None, None, None, "H3", None, None, None, None],
            ["H2", None, None, None, None, "H2", None, None, None, "H2", None, None, None, None, "H2"],
            [None, "H2", None, None, None, None, "H2", None, "H2", None, None, None, None, "H2", None],
            [None, None, "K2", None, None, None, None, "START", None, None, None, None, "K2", None, None],
            [None, "H2", None, None, None, None, "H2", None, "H2", None, None, None, None, "H2", None],
            ["H2", None, None, None, None, "H2", None, None, None, "H2", None, None, None, None, "H2"],
            [None, None, None, None, "H3", None, None, None, None, None, "H3", None, None, None, None],
            [None, None, None, "K2", None, None, None, None, None, None, None, "K2", None, None, None],
            ["K3", None, None, None, None, None, None, "K2", None, None, None, None, None, None, "K3"],
            [None, "H3", None, None, None, None, "H2", None, "H2", None, None, None, None, "H3", None],
            [None, None, "K3", None, None, "H2", None, None, None, "H2", None, None, "K3", None, None],
        ]
    else:
        bonus_grid = [[None for _ in range(size)] for _ in range(size)]
        bonus_grid[size // 2][size // 2] = "START"

    return {
        "boardType": board_type,
        "size": size,
        "bonusGrid": bonus_grid,
        "center": [size // 2, size // 2],
    }


@app.post("/api/solve")
def solve(payload: SolveRequest):
    words = load_dictionary_words()
    suggestions = generate_moves(payload.board, payload.rack, words)
    return {"suggestions": suggestions}
