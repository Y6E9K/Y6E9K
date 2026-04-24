from pathlib import Path
from typing import Any, List

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from .engine.solver import build_dictionary_index, generate_moves, cache_stats


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
    boardType: str = "15x15"
    board: List[List[Any]]
    rack: List[str]
    mode: str = "fast"


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
        "engine": "v8.2 pattern ultra fast",
        "docs": "/docs",
        "wordCount": len(DICT_INDEX.word_set),
        "files": len(list(DATA_DIR.glob("*"))) if DATA_DIR.exists() else 0,
        "cache": cache_stats(),
    }


@app.head("/")
def head_root():
    return {}


@app.get("/api/health")
def health():
    return {
        "ok": True,
        "engine": "v8.2 pattern ultra fast",
        "wordCount": len(DICT_INDEX.word_set),
        "files": len(list(DATA_DIR.glob("*"))) if DATA_DIR.exists() else 0,
        "dataDir": str(DATA_DIR),
        "cache": cache_stats(),
    }


@app.get("/api/debug")
def debug():
    return {
        "ok": True,
        "engine": "v8.2 pattern ultra fast",
        "wordCount": len(DICT_INDEX.word_set),
        "files": [p.name for p in DATA_DIR.glob("*")] if DATA_DIR.exists() else [],
        "sampleWords": DICT_INDEX.sample_words[:30],
        "cache": cache_stats(),
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
        requested_mode = payload.mode if payload.mode in ("fast", "max") else "fast"

        settings = {
            "fast": {
                "limit": 900,
                "seconds": 8.0,
                "max_checks": 5_000_000,
            },
            "max": {
                "limit": 1800,
                "seconds": 28.0,
                "max_checks": 18_000_000,
            },
        }[requested_mode]

        result = generate_moves(
            board=payload.board,
            rack=payload.rack,
            index=DICT_INDEX,
            limit=settings["limit"],
            seconds=settings["seconds"],
            max_checks=settings["max_checks"],
        )

        return {
            "suggestions": result["suggestions"],
            "mode": requested_mode,
            "message": result["message"],
            "debug": result["debug"],
        }

    except Exception as e:
        print("SOLVE ERROR:", e)
        return {
            "suggestions": [],
            "message": "Öneriler alınırken hata oluştu.",
            "error": str(e),
        }
