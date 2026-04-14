import React, { useEffect, useMemo, useRef, useState } from "react";
import BoardGrid from "./components/BoardGrid";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const MAX_TABS = 7;
const VALID_RACK_INPUT = /^[A-Za-zÇĞİIÖŞÜçğıiöşü? ]$/;

function normalizeLetter(value) {
  if (!value) return "";
  return value.toString().slice(0, 1).toLocaleUpperCase("tr-TR");
}

function createEmptyRack() {
  return ["", "", "", "", "", "", ""];
}

function getNextBoardNumber(tabs) {
  const nums = tabs
    .map((t) => {
      const m = String(t.name || "").match(/^Tahta\s+(\d+)$/i);
      return m ? Number(m[1]) : null;
    })
    .filter((x) => Number.isInteger(x));

  if (!nums.length) return 1;
  return Math.max(...nums) + 1;
}

function cloneBoard(board) {
  return board.map((row) => row.map((cell) => ({ ...cell })));
}

function createEmptyBoard(size) {
  return Array.from({ length: size }, () =>
    Array.from({ length: size }, () => ({
      letter: "",
      bonus: null,
    }))
  );
}

function normalizeBoardData(boardType, boardData) {
  const size = boardData?.size || boardData?.boardSize || (boardType === "9x9" ? 9 : 15);

  if (Array.isArray(boardData?.board) && boardData.board.length) {
    return boardData.board.map((row) =>
      row.map((cell) => ({
        letter: cell?.letter || "",
        bonus: cell?.bonus || null,
      }))
    );
  }

  if (Array.isArray(boardData?.cells) && boardData.cells.length) {
    return boardData.cells.map((row) =>
      row.map((cell) => ({
        letter: cell?.letter || "",
        bonus: cell?.bonus || null,
      }))
    );
  }

  if (Array.isArray(boardData?.bonusGrid) && boardData.bonusGrid.length) {
    return boardData.bonusGrid.map((row) =>
      row.map((bonus) => ({
        letter: "",
        bonus: bonus || null,
      }))
    );
  }

  return createEmptyBoard(size);
}

function createTabFromBoardData(boardType, boardData, name) {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name,
    boardType,
    board: normalizeBoardData(boardType, boardData),
    selectedCell: null,
    previewCells: [],
    rack: createEmptyRack(),
    suggestions: [],
    loading: false,
  };
}

function parseDirection(raw) {
  const value = String(raw || "").toLowerCase();

  if (
    value.includes("dikey") ||
    value.includes("dıkey") ||
    value === "v" ||
    value === "vertical" ||
    value === "down"
  ) {
    return "vertical";
  }

  if (
    value.includes("yatay") ||
    value === "h" ||
    value === "horizontal" ||
    value === "right"
  ) {
    return "horizontal";
  }

  return "";
}

function parsePositionString(position) {
  const value = String(position || "");
  const match = value.match(/(\d+)\s*\/\s*(\d+)/);

  if (!match) return { row: null, col: null, direction: "" };

  return {
    row: Number(match[1]) - 1,
    col: Number(match[2]) - 1,
    direction: parseDirection(value),
  };
}

function extractPlacements(suggestion, board = []) {
  if (!suggestion) return [];

  const directPlacements =
    suggestion.placements ||
    suggestion.newTiles ||
    suggestion.tiles ||
    suggestion.cells ||
    suggestion.placed ||
    [];

  if (Array.isArray(directPlacements) && directPlacements.length) {
    return directPlacements
      .map((p) => ({
        row:
          typeof p.row === "number"
            ? p.row
            : typeof p.r === "number"
            ? p.r
            : typeof p.y === "number"
            ? p.y
            : null,
        col:
          typeof p.col === "number"
            ? p.col
            : typeof p.c === "number"
            ? p.c
            : typeof p.x === "number"
            ? p.x
            : null,
        letter: normalizeLetter(p.letter || p.char || p.value || p.tile || ""),
      }))
      .filter((p) => typeof p.row === "number" && typeof p.col === "number" && p.letter);
  }

  const word = String(suggestion.word || suggestion.kelime || "").toLocaleUpperCase("tr-TR");

  let startRow = typeof suggestion.row === "number" ? suggestion.row : Number(suggestion.row);
  let startCol = typeof suggestion.col === "number" ? suggestion.col : Number(suggestion.col);
  let direction = parseDirection(suggestion.direction || suggestion.yon || "");

  if ((Number.isNaN(startRow) || Number.isNaN(startCol) || !direction) && suggestion.position) {
    const parsed = parsePositionString(suggestion.position);
    if (Number.isNaN(startRow)) startRow = parsed.row;
    if (Number.isNaN(startCol)) startCol = parsed.col;
    if (!direction) direction = parsed.direction;
  }

  if (!word || Number.isNaN(startRow) || Number.isNaN(startCol) || !direction) return [];

  const placements = [];
  for (let i = 0; i < word.length; i++) {
    const row = startRow + (direction === "vertical" ? i : 0);
    const col = startCol + (direction === "horizontal" ? i : 0);

    if (!board[row] || !board[row][col]) return [];

    const existing = normalizeLetter(board[row][col].letter || "");
    const nextLetter = normalizeLetter(word[i]);

    if (!existing) {
      placements.push({ row, col, letter: nextLetter });
    } else if (existing !== nextLetter) {
      return [];
    }
  }

  return placements;
}

function applySuggestionToBoard(board, suggestion) {
  const next = cloneBoard(board);
  const placements = extractPlacements(suggestion, board);

  for (const p of placements) {
    if (next[p.row] && next[p.row][p.col]) {
      next[p.row][p.col].letter = p.letter;
    }
  }

  return next;
}

export default function App() {
  const [tabs, setTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [newBoardType, setNewBoardType] = useState("15x15");
  const [loadingBoard, setLoadingBoard] = useState(false);
  const [activeSuggestionKey, setActiveSuggestionKey] = useState(null);

  const rackRefs = useRef([]);
  const lastSuggestionTapRef = useRef({ key: null, time: 0 });

  const activeTab = useMemo(
    () => tabs.find((t) => t.id === activeTabId) || null,
    [tabs, activeTabId]
  );

  useEffect(() => {
    if (!tabs.length) {
      handleCreateBoard("15x15");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function fetchBoard(boardType) {
    const res = await fetch(`${API_BASE}/api/board/${boardType}`);
    if (!res.ok) throw new Error("Tahta verisi alınamadı");
    return res.json();
  }

  async function handleCreateBoard(forcedType) {
    const boardType = forcedType || newBoardType;
    if (tabs.length >= MAX_TABS) {
      alert("En fazla 7 sekme açılabilir.");
      return;
    }

    try {
      setLoadingBoard(true);
      const boardData = await fetchBoard(boardType);
      const boardNumber = getNextBoardNumber(tabs);
      const newTab = createTabFromBoardData(boardType, boardData, `Tahta ${boardNumber}`);
      setTabs((prev) => [...prev, newTab]);
      setActiveTabId(newTab.id);
      setActiveSuggestionKey(null);
    } catch (err) {
      console.error(err);
      alert("Tahta oluşturulamadı.");
    } finally {
      setLoadingBoard(false);
    }
  }

  function updateActiveTab(patchFn) {
    setTabs((prev) => prev.map((tab) => (tab.id === activeTabId ? patchFn(tab) : tab)));
  }

  function handleSelectCell(row, col) {
    if (!activeTab) return;
    updateActiveTab((tab) => ({ ...tab, selectedCell: { row, col }, previewCells: [] }));
    setActiveSuggestionKey(null);
  }

  function focusBoardCell(row, col) {
    const nextInput = document.querySelector(`[data-cell="${row}-${col}"]`);
    nextInput?.focus();
  }

  function handleBoardCellInput(row, col, value) {
    if (!activeTab) return;

    const boardWidth = activeTab.board.length;

    updateActiveTab((tab) => {
      const nextBoard = cloneBoard(tab.board);
      nextBoard[row][col].letter = value || "";
      return {
        ...tab,
        board: nextBoard,
        selectedCell: { row, col: Math.min(col + 1, boardWidth - 1) },
      };
    });

    setTimeout(() => focusBoardCell(row, Math.min(col + 1, boardWidth - 1)), 0);
  }

  function handleBoardCellBackspace(row, col) {
    if (!activeTab) return;

    updateActiveTab((tab) => {
      const nextBoard = cloneBoard(tab.board);
      if (nextBoard[row][col].letter) {
        nextBoard[row][col].letter = "";
        return { ...tab, board: nextBoard, selectedCell: { row, col } };
      }

      const prevCol = Math.max(col - 1, 0);
      nextBoard[row][prevCol].letter = "";
      return { ...tab, board: nextBoard, selectedCell: { row, col: prevCol } };
    });

    setTimeout(() => focusBoardCell(row, Math.max(col - 1, 0)), 0);
  }

  function focusRack(index) {
    const el = rackRefs.current[index];
    if (el) {
      el.focus();
      el.select?.();
    }
  }

  function setRackValueFromIndex(startIndex, rawValue) {
    if (!activeTab) return;

    updateActiveTab((tab) => {
      const nextRack = [...tab.rack];
      let cursor = startIndex;

      for (const ch of rawValue) {
        if (cursor > 6) break;
        if (ch === " ") {
          nextRack[cursor] = "";
          cursor += 1;
          continue;
        }
        if (!VALID_RACK_INPUT.test(ch)) continue;
        nextRack[cursor] = normalizeLetter(ch);
        cursor += 1;
      }

      return { ...tab, rack: nextRack };
    });

    setTimeout(() => focusRack(Math.min(startIndex + Math.max(rawValue.length, 1), 6)), 0);
  }

  function handleRackChange(index, e) {
    setRackValueFromIndex(index, e.target.value || "");
  }

  function handleRackKeyDown(index, e) {
    if (!activeTab) return;

    if (e.key === "Backspace") {
      e.preventDefault();
      updateActiveTab((tab) => {
        const nextRack = [...tab.rack];
        if (nextRack[index]) {
          nextRack[index] = "";
          return { ...tab, rack: nextRack };
        }

        const prevIndex = Math.max(index - 1, 0);
        nextRack[prevIndex] = "";
        setTimeout(() => focusRack(prevIndex), 0);
        return { ...tab, rack: nextRack };
      });
      return;
    }

    if (e.key === "ArrowLeft") {
      e.preventDefault();
      focusRack(Math.max(index - 1, 0));
      return;
    }

    if (e.key === "ArrowRight") {
      e.preventDefault();
      focusRack(Math.min(index + 1, 6));
      return;
    }
  }

  async function handleSolve() {
    if (!activeTab) return;

    try {
      updateActiveTab((tab) => ({ ...tab, loading: true, previewCells: [] }));
      setActiveSuggestionKey(null);

      const payload = {
        boardType: activeTab.boardType,
        board: activeTab.board.map((row) =>
          row.map((cell) => ({ bonus: cell.bonus, letter: cell.letter || "" }))
        ),
        rack: activeTab.rack.filter(Boolean),
      };

      const res = await fetch(`${API_BASE}/api/solve`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Öneriler alınamadı");

      const data = await res.json();
      updateActiveTab((tab) => ({
        ...tab,
        loading: false,
        suggestions: Array.isArray(data?.suggestions) ? data.suggestions : [],
      }));
    } catch (err) {
      console.error(err);
      updateActiveTab((tab) => ({ ...tab, loading: false }));
      alert("Öneriler alınırken hata oluştu.");
    }
  }

  function previewSuggestion(suggestion, key = null) {
    if (!activeTab) return;
    const previewCells = extractPlacements(suggestion, activeTab.board);
    updateActiveTab((tab) => ({ ...tab, previewCells }));
    setActiveSuggestionKey(key);
  }

  function applySuggestion(suggestion) {
    if (!activeTab) return;
    updateActiveTab((tab) => ({
      ...tab,
      board: applySuggestionToBoard(tab.board, suggestion),
      previewCells: [],
    }));
    setActiveSuggestionKey(null);
  }

  function handleSuggestionTap(suggestion, key) {
    const now = Date.now();
    const last = lastSuggestionTapRef.current;

    if (last.key === key && now - last.time < 400) {
      applySuggestion(suggestion);
      lastSuggestionTapRef.current = { key: null, time: 0 };
      return;
    }

    previewSuggestion(suggestion, key);
    lastSuggestionTapRef.current = { key, time: now };
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div>
          <h1>Kelime Asistanı</h1>
          <p>Tahtaya tıkla, harf yaz. Dolu kare taş rengine döner; silince eski bonus rengi geri gelir.</p>
        </div>

        <div className="new-board-bar">
          <select value={newBoardType} onChange={(e) => setNewBoardType(e.target.value)}>
            <option value="15x15">15x15</option>
            <option value="9x9">9x9</option>
          </select>
          <button onClick={() => handleCreateBoard()} disabled={loadingBoard}>
            {loadingBoard ? "Açılıyor..." : "Yeni Tahta"}
          </button>
        </div>
      </header>

      <div className="tabs-bar">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={`tab-chip ${tab.id === activeTabId ? "active" : ""}`}
            onClick={() => setActiveTabId(tab.id)}
          >
            <span>{tab.name}</span>
          </div>
        ))}
      </div>

      {activeTab ? (
        <main className="layout">
          <section className="board-panel">
            <BoardGrid
              board={activeTab.board}
              selectedCell={activeTab.selectedCell}
              previewCells={activeTab.previewCells}
              onSelectCell={handleSelectCell}
              onCellInput={handleBoardCellInput}
              onCellBackspace={handleBoardCellBackspace}
            />
          </section>

          <aside className="side-panel">
            <section className="card">
              <div className="card-title-row">
                <h2>Harfler</h2>
                <span className="info-text">En fazla iki joker girilebilir. Joker:?</span>
              </div>

              <div className="rack-row">
                {activeTab.rack.map((value, i) => (
                  <input
                    key={i}
                    ref={(el) => (rackRefs.current[i] = el)}
                    className="rack-input"
                    value={value}
                    maxLength={7}
                    inputMode="text"
                    autoComplete="off"
                    autoCorrect="off"
                    autoCapitalize="characters"
                    spellCheck={false}
                    onChange={(e) => handleRackChange(i, e)}
                    onKeyDown={(e) => handleRackKeyDown(i, e)}
                  />
                ))}
              </div>
            </section>

            <section className="card">
              <div className="card-title-row">
                <h2>Öneriler</h2>
                <button onClick={handleSolve} disabled={activeTab.loading}>
                  {activeTab.loading ? "Hesaplanıyor..." : "En İyi Önerileri Hesapla"}
                </button>
              </div>

              <div className="suggestions-list">
                {activeTab.suggestions.length ? (
                  activeTab.suggestions.map((s, idx) => {
                    const suggestionKey = `${idx}-${s.word || s.kelime || "kelime"}`;
                    return (
                      <div
                        key={suggestionKey}
                        className={`suggestion-item ${
                          activeSuggestionKey === suggestionKey ? "active" : ""
                        }`}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSuggestionTap(s, suggestionKey);
                        }}
                        onDoubleClick={(e) => {
                          e.stopPropagation();
                          applySuggestion(s);
                        }}
                        onTouchEnd={(e) => {
                          e.preventDefault();
                          e.stopPropagation();
                          handleSuggestionTap(s, suggestionKey);
                        }}
                      >
                        <div className="suggestion-main">
                          <strong>{s.word || s.kelime || "Kelime"}</strong>
                          <span>{s.score ?? s.puan ?? 0} puan</span>
                        </div>
                        <div className="suggestion-sub">
                          <span>
                            {String(s.direction || s.yon || s.position || "-")}
                            {typeof s.row === "number" && typeof s.col === "number"
                              ? ` • ${s.row + 1} / ${s.col + 1}`
                              : ""}
                          </span>
                        </div>
                      </div>
                    );
                  })
                ) : (
                  <div className="empty-state">Henüz öneri yok.</div>
                )}
              </div>
            </section>
          </aside>
        </main>
      ) : (
        <div className="empty-page">Tahta yükleniyor...</div>
      )}
    </div>
  );
}
