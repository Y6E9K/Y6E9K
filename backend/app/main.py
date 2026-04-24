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
    return {
        "ok": True,
        "name": "Kelime Asistanı API",
        "docs": "/docs",
        "wordCount": len(DICT_INDEX.word_set),
        "files": len(list(DATA_DIR.glob("*"))) if DATA_DIR.exists() else 0,
    }


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "wordCount": len(DICT_INDEX.word_set),
        "files": len(list(DATA_DIR.glob("*"))) if DATA_DIR.exists() else 0,
    }


@app.get("/api/board/{board_type}")
def get_board(board_type: str):
    if board_type == "9x9":
        size = 9
        bonus_grid = [
            ["K3", None, None, None, "H3", None, None, None, "K3"],
            [None, "K2", None, "H2", None, "H2", None, "K2", None],
            [None, None, "H3", None, None, None, "H3", None, None],
            [None, "H2", None, None, None, None, None, "H2", None],
            ["H3", None, None, None, "START", None, None, None, "H3"],
            [None, "H2", None, None, None, None, None, "H2", None],
            [None, None, "H3", None, None, None, "H3", None, None],
            [None, "K2", None, "H2", None, "H2", None, "K2", None],
            ["K3", None, None, None, "H3", None, None, None, "K3"],
        ]
    else:
        size = 15
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

    return {
        "boardType": board_type,
        "size": size,
        "bonusGrid": bonus_grid,
        "center": [size // 2, size // 2],
    }


@app.post("/api/solve")
def solve(payload: SolveRequest):
    try:
        mode_settings = {
            "fast": {
                "limit": 40,
                "fast_seconds": 0.8,
                "deep_seconds": 1.8,
                "fast_nodes": 12000,
                "deep_nodes": 50000,
                "backtrack_extra": 1,
            },
            "deep": {
                "limit": 80,
                "fast_seconds": 1.4,
                "deep_seconds": 5.5,
                "fast_nodes": 30000,
                "deep_nodes": 180000,
                "backtrack_extra": 3,
            },
            "max": {
                "limit": 150,
                "fast_seconds": 2.0,
                "deep_seconds": 10.0,
                "fast_nodes": 70000,
                "deep_nodes": 500000,
                "backtrack_extra": 5,
            },
        }

        settings = mode_settings[payload.mode]

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
        return {"suggestions": suggestions, "mode": payload.mode}
    except Exception as e:
        print("SOLVE ERROR:", e)
        return {"suggestions": [], "error": str(e)}
