from pathlib import Path
from typing import Any, List

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


@app.post("/api/solve")
def solve(payload: SolveRequest):
    try:
        requested_mode = payload.mode if payload.mode in ("fast", "max") else "fast"

        mode_settings = {
            "fast": {
                "limit": 500,
                "fast_seconds": 3.0,
                "deep_seconds": 30.0,
                "fast_nodes": 150000,
                "deep_nodes": 3000000,
                "backtrack_extra": 20,
                "full_sweep": True,
            },
            "max": {
                "limit": 1000,
                "fast_seconds": 5.0,
                "deep_seconds": 45.0,
                "fast_nodes": 300000,
                "deep_nodes": 6000000,
                "backtrack_extra": 35,
                "full_sweep": True,
            },
        }

        settings = mode_settings[requested_mode]

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
            full_sweep=settings["full_sweep"],
        )

        return {"suggestions": suggestions, "mode": requested_mode}

    except Exception as e:
        print("SOLVE ERROR:", e)
        return {"suggestions": [], "error": str(e)}
