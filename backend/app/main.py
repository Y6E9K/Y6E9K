from functools import lru_cache
from pathlib import Path
from typing import List, Literal, Optional, Union

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .engine.board_layout import get_board_config
from .engine.dictionary_loader import load_dictionary_folder
from .engine.solver import generate_moves
from .engine.tr_utils import tr_upper

BASE_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = BASE_DIR / "data"

app = FastAPI(title="Kelime Asistanı API", version="1.2.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class SolveRequest(BaseModel):
    boardType: Literal["9x9", "15x15"] = "15x15"
    boardLetters: List[List[Optional[str]]] = Field(default_factory=list)
    rack: Union[str, List[str]] = Field(default_factory=list)
    limit: int = 1000


@lru_cache(maxsize=1)
def get_dictionary():
    words, by_length, meta = load_dictionary_folder(str(DATA_DIR))
    return words, by_length, meta


@app.get("/")
def root():
    return {"ok": True, "name": "Kelime Asistanı API", "docs": "/docs"}


@app.get("/api/health")
def health():
    words, _, meta = get_dictionary()
    return {"ok": True, "wordCount": len(words), "files": meta["file_count"]}


@app.get("/api/board/{board_type}")
def board_meta(board_type: str):
    config = get_board_config(board_type)
    return {"boardType": board_type, "size": config["size"], "bonusGrid": config["bonus_grid"], "center": config["center"]}


@app.post("/api/solve")
def solve(req: SolveRequest):
    words, by_length, _ = get_dictionary()
    config = get_board_config(req.boardType)
    size = config["size"]

    raw_rack = req.rack if isinstance(req.rack, list) else list(req.rack)
    rack = [tr_upper(ch) for ch in raw_rack if str(ch).strip()]

    joker_count = sum(1 for ch in rack if ch == "?")
    if joker_count > 2:
        raise HTTPException(status_code=400, detail="En fazla 2 joker kullanılabilir.")

    suggestions = generate_moves(payload.board, payload.rack, words)
        board,
        config["bonus_grid"],
        rack,
        words,
        by_length,
        size,
        tuple(config["center"]),
        limit=max(1, min(req.limit, 1000)),
    )
    return {
        "boardType": req.boardType,
        "size": size,
        "rack": rack,
        "suggestions": results,
    }
