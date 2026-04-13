import React, { useEffect, useMemo, useRef, useState } from "react";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";

const MAX_TABS = 7;
const VALID_RACK_INPUT = /^[A-Za-zÇĞİIÖŞÜçğıiöşü? ]$/;
const VALID_CELL_INPUT = /^[A-Za-zÇĞİIÖŞÜçğıiöşü?]$/;

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

function bonusLabel(bonus) {
  switch (bonus) {
    case "TW":
    case "K3":
      return "K3";
    case "DW":
    case "K2":
      return "K2";
    case "TL":
    case "H3":
      return "H3";
    case "DL":
    case "H2":
      return "H2";
    case "STAR":
    case "START":
      return "★";
    default:
      return "";
  }
}

function cellClassName(cell, isPreview, isSelected) {
  let cls = "board-cell";

  if (cell.letter) cls += " filled";
  else if (isPreview) cls += " preview";
  else if (cell.bonus === "TW" || cell.bonus === "K3") cls += " bonus-tw";
  else if (cell.bonus === "DW" || cell.bonus === "K2") cls += " bonus-dw";
  else if (cell.bonus === "TL" || cell.bonus === "H3") cls += " bonus-tl";
  else if (cell.bonus === "DL" || cell.bonus === "H2") cls += " bonus-dl";
  else if (cell.bonus === "STAR" || cell.bonus === "START") cls += " bonus-star";
  else cls += " empty";

  if (isSelected) cls += " selected";
  return cls;
}

function cloneBoard(board) {
  return board.map((row) => row.map((cell) => ({ ...cell })));
}

function createEmptyBoard(size) {
  return Array.from({ length: size }, () =>
    Array.from({ length: size }, () => ({
      letter: "",
      bonus: "NORMAL",
    }))
  );
}

function normalizeBoardData(boardType, boardData) {
  if (Array.isArray(boardData?.board) && boardData.board.length) {
    return boardData.board.map((row) =>
      row.map((cell) => ({
        letter: cell?.letter || "",
        bonus: cell?.bonus || "NORMAL",
      }))
    );
  }

  if (Array.isArray(boardData?.cells) && boardData.cells.length) {
    return boardData.cells.map((row) =>
      row.map((cell) => ({
        letter: cell?.letter || "",
        bonus: cell?.bonus || "NORMAL",
      }))
    );
  }

  if (Array.isArray(boardData?.bonusGrid) && boardData.bonusGrid.length) {
    return boardData.bonusGrid.map((row) =>
      row.map((bonus) => ({
        letter: "",
        bonus: bonus || "NORMAL",
      }))
    );
  }

  const size =
    boardData?.size ||
    boardData?.boardSize ||
    (boardType === "9x9" ? 9 : 15);

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
    renameMode: false,
  };
}

function parseDirection(raw) {
  const value = String(raw || "").toLocaleLowerCase("tr-TR");

  if (
    value.includes("dikey") ||
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

  if (!match) {
    return { row: null, col: null, direction: "" };
  }

  const row = Number(match[1]) - 1;
  const col = Number(match[2]) - 1;
  const direction = parseDirection(value);

  return { row, col, direction };
}

function extractPlacements(suggestion, board = []) {
  if (!suggestion) return [];

  const directPlacements =
    suggestion.placements ||
    suggestion.newTiles ||
    suggestion.tiles ||
    suggestion.cells ||
    [];

  if (Array.isArray(directPlacements) && directPlacements.length) {
    return directPlacements
      .filter(
        (p) =>
          p &&
          typeof p.row === "number" &&
          typeof p.col === "number"
      )
      .map((p) => ({
        row: p.row,
        col: p.col,
        letter: normalizeLetter(p.letter || p.char || p.value || ""),
      }));
  }

  const word = String(
    suggestion.word || suggestion.kelime || ""
  ).toLocaleUpperCase("tr-TR");

  let startRow =
    typeof suggestion.row === "number" ? suggestion.row : Number(suggestion.row);
  let startCol =
    typeof suggestion.col === "number" ? suggestion.col : Number(suggestion.col);
  let direction = parseDirection(suggestion.direction || suggestion.yon || "");

  if ((Number.isNaN(startRow) || Number.isNaN(startCol) || !direction) && suggestion.position) {
    const parsed = parsePositionString(suggestion.position);
    if (Number.isNaN(startRow)) startRow = parsed.row;
    if (Number.isNaN(startCol)) startCol = parsed.col;
    if (!direction) direction = parsed.direction;
  }

  if (!word || Number.isNaN(startRow) || Number.isNaN(startCol) || !direction) {
    return [];
  }

  const placements = [];

  for (let i = 0; i < word.length; i++) {
    const row = startRow + (direction === "vertical" ? i : 0);
    const col = startCol + (direction === "horizontal" ? i : 0);

    if (!board[row] || !board[row][col]) {
      return [];
    }

    const existingLetter = normalizeLetter(board[row][col].letter || "");
    const nextLetter = normalizeLetter(word[i]);

    if (!existingLetter) {
      placements.push({ row, col, letter: nextLetter });
    } else if (existingLetter !== nextLetter) {
      return [];
    }
  }

  return placements;
}

function buildPreviewCells(suggestion, board = []) {
  return extractPlacements(suggestion, board);
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
  const renameRefs = useRef({});
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

  useEffect(() => {
    const handleOutsidePreview = (event) => {
      if (!activeTab) return;

      const target = event.target;
      if (
        target.closest(".suggestion-item") ||
        target.closest(".board-cell") ||
        target.closest(".rack-input") ||
        target.closest(".card button")
      ) {
        return;
      }

      setTabs((prev) =>
        prev.map((tab) =>
          tab.id === activeTab.id ? { ...tab, previewCells: [] } : tab
        )
      );
      setActiveSuggestionKey(null);
    };

    document.addEventListener("pointerdown", handleOutsidePreview);
    return () => {
      document.removeEventListener("pointerdown", handleOutsidePreview);
    };
  }, [activeTab]);

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
      const newTab = createTabFromBoardData(
        boardType,
        boardData,
        `Tahta ${boardNumber}`
      );
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

  function closeTab(tabId) {
    setTabs((prev) => {
      const next = prev.filter((t) => t.id !== tabId);
      if (activeTabId === tabId) {
        const fallback = next[next.length - 1] || null;
        setActiveTabId(fallback ? fallback.id : null);
      }
      return next;
    });
  }

  function startRename(tabId) {
    setTabs((prev) =>
      prev.map((t) => (t.id === tabId ? { ...t, renameMode: true } : t))
    );
    setTimeout(() => {
      const el = renameRefs.current[tabId];
      if (el) {
        el.focus();
        el.select();
      }
    }, 0);
  }

  function finishRename(tabId, value) {
    const clean = String(value || "").trim() || "Tahta";
    setTabs((prev) =>
      prev.map((t) =>
        t.id === tabId ? { ...t, name: clean, renameMode: false } : t
      )
    );
  }

  function updateActiveTab(patchFn) {
    setTabs((prev) =>
      prev.map((tab) => (tab.id === activeTabId ? patchFn(tab) : tab))
    );
  }

  function handleSelectCell(row, col) {
    if (!activeTab) return;
    updateActiveTab((tab) => ({
      ...tab,
      selectedCell: { row, col },
      previewCells: [],
    }));
    setActiveSuggestionKey(null);
  }

  function focusBoardCell(row, col) {
    const nextInput = document.querySelector(`[data-cell="${row}-${col}"]`);
    nextInput?.focus();
  }

  function handleBoardCellInput(row, col, value) {
    if (!activeTab) return;

    const boardWidth = activeTab.boardType === "9x9" ? 9 : 15;

    updateActiveTab((tab) => {
      const nextBoard = cloneBoard(tab.board);
      nextBoard[row][col].letter = value || "";

      const nextCol = Math.min(col + 1, boardWidth - 1);

      return {
        ...tab,
        board: nextBoard,
        selectedCell: { row, col: nextCol },
      };
    });

    setTimeout(() => {
      const nextCol = Math.min(col + 1, boardWidth - 1);
      focusBoardCell(row, nextCol);
    }, 0);
  }

  function handleBoardCellBackspace(row, col) {
    if (!activeTab) return;

    updateActiveTab((tab) => {
      const nextBoard = cloneBoard(tab.board);

      if (nextBoard[row][col].letter) {
        nextBoard[row][col].letter = "";
        return {
          ...tab,
          board: nextBoard,
          selectedCell: { row, col },
        };
      }

      const prevCol = Math.max(col - 1, 0);
      nextBoard[row][prevCol].letter = "";

      return {
        ...tab,
        board: nextBoard,
        selectedCell: { row, col: prevCol },
      };
    });

    setTimeout(() => {
      const prevCol = Math.max(col - 1, 0);
      focusBoardCell(row, prevCol);
    }, 0);
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

        const normalized = normalizeLetter(ch);
        if (normalized === "?") {
          const jokerCount = nextRack.filter((x) => x === "?").length;
          if (jokerCount >= 2 && nextRack[cursor] !== "?") continue;
        }

        if (!normalized) continue;

        nextRack[cursor] = normalized;
        cursor += 1;
      }

      return {
        ...tab,
        rack: nextRack,
      };
    });

    const nextIndex = Math.min(startIndex + Math.max(rawValue.length, 1), 6);
    setTimeout(() => focusRack(nextIndex), 0);
  }

  function handleRackChange(index, e) {
    const raw = e.target.value || "";
    setRackValueFromIndex(index, raw);
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

    if (e.key === " ") {
      e.preventDefault();
      setRackValueFromIndex(index, " ");
    }
  }

  async function handleSolve() {
    if (!activeTab) return;

    try {
      updateActiveTab((tab) => ({
        ...tab,
        loading: true,
        previewCells: [],
      }));
      setActiveSuggestionKey(null);

      const payload = {
        boardType: activeTab.boardType,
        board: activeTab.board.map((row) =>
          row.map((cell) => ({
            bonus: cell.bonus,
            letter: cell.letter || "",
          }))
        ),
        rack: activeTab.rack.filter(Boolean),
      };

      const res = await fetch(`${API_BASE}/api/solve`, {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });

      if (!res.ok) {
        throw new Error("Öneriler alınamadı.");
      }

      const data = await res.json();
      const suggestions = Array.isArray(data?.suggestions)
        ? data.suggestions
        : [];

      updateActiveTab((tab) => ({
        ...tab,
        loading: false,
        suggestions,
      }));
    } catch (err) {
      console.error(err);
      updateActiveTab((tab) => ({
        ...tab,
        loading: false,
      }));
      alert("Öneriler alınırken hata oluştu.");
    }
  }

  function previewSuggestion(suggestion, key = null) {
    if (!activeTab) return;

    const previewCells = buildPreviewCells(suggestion, activeTab.board);

    updateActiveTab((tab) => ({
      ...tab,
      previewCells,
    }));

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
          <p>
            Tahtaya tıkla, harf yaz. Dolu kare taş rengine döner; silince eski
            bonus rengi geri gelir.
          </p>
        </div>

        <div className="new-board-bar">
          <select
            value={newBoardType}
            onChange={(e) => setNewBoardType(e.target.value)}
          >
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
            onDoubleClick={() => startRename(tab.id)}
          >
            {tab.renameMode ? (
              <input
                ref={(el) => (renameRefs.current[tab.id] = el)}
                className="tab-rename-input"
                defaultValue={tab.name}
                onClick={(e) => e.stopPropagation()}
                onBlur={(e) => finishRename(tab.id, e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter") {
                    finishRename(tab.id, e.currentTarget.value);
                  }
                }}
              />
            ) : (
              <span>{tab.name}</span>
            )}

            <button
              className="tab-close"
              onClick={(e) => {
                e.stopPropagation();
                closeTab(tab.id);
              }}
              title="Sekmeyi kapat"
            >
              ×
            </button>
          </div>
        ))}
      </div>

      {activeTab ? (
        <main className="layout">
          <section className="board-panel">
            <div
              className="board-grid"
              style={{
                gridTemplateColumns: `repeat(${
                  activeTab.boardType === "9x9" ? 9 : 15
                }, minmax(0, 1fr))`,
              }}
            >
              {activeTab.board.map((row, rowIndex) =>
                row.map((cell, colIndex) => {
                  const isSelected =
                    activeTab.selectedCell?.row === rowIndex &&
                    activeTab.selectedCell?.col === colIndex;

                  const previewMap = new Map(
                    (activeTab.previewCells || []).map((p) => [
                      `${p.row}-${p.col}`,
                      p,
                    ])
                  );
                  const previewItem = previewMap.get(`${rowIndex}-${colIndex}`);
                  const isPreview = !!previewItem && !cell.letter;

                  return (
                    <div
                      key={`${rowIndex}-${colIndex}`}
                      className={cellClassName(cell, isPreview, isSelected)}
                    >
                      {!cell.letter && !isPreview && (
                        <span className="board-cell-bonus">
                          {bonusLabel(cell.bonus)}
                        </span>
                      )}

                      {isPreview && !cell.letter && (
                        <span className="board-cell-preview-letter">
                          {previewItem.letter}
                        </span>
                      )}

                      <input
                        data-cell={`${rowIndex}-${colIndex}`}
                        className="board-cell-input"
                        value={cell.letter || ""}
                        maxLength={1}
                        inputMode="text"
                        autoComplete="off"
                        autoCorrect="off"
                        autoCapitalize="characters"
                        spellCheck={false}
                        onFocus={() => handleSelectCell(rowIndex, colIndex)}
                        onClick={(e) => {
                          e.stopPropagation();
                          handleSelectCell(rowIndex, colIndex);
                        }}
                        onChange={(e) => {
                          const raw = e.target.value || "";
                          if (!raw) {
                            handleBoardCellInput(rowIndex, colIndex, "");
                            return;
                          }

                          const ch = raw.slice(-1);
                          if (!VALID_CELL_INPUT.test(ch)) return;

                          handleBoardCellInput(
                            rowIndex,
                            colIndex,
                            normalizeLetter(ch)
                          );
                        }}
                        onKeyDown={(e) => {
                          if (e.key === "Backspace") {
                            e.preventDefault();
                            handleBoardCellBackspace(rowIndex, colIndex);
                          }
                        }}
                        aria-label={`Hücre ${rowIndex + 1}-${colIndex + 1}`}
                      />
                    </div>
                  );
                })
              )}
            </div>
          </section>

          <aside className="side-panel">
            <section className="card">
              <div className="card-title-row">
                <h2>Harfler</h2>
                <span className="info-text">
                  En fazla iki joker girilebilir. Joker:?
                </span>
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
