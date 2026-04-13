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
      return "K3";
    case "DW":
      return "K2";
    case "TL":
      return "H3";
    case "DL":
      return "H2";
    case "STAR":
      return "★";
    default:
      return "";
  }
}

function cellClassName(cell, isPreview, isSelected) {
  let cls = "board-cell";

  if (cell.letter) cls += " filled";
  else if (isPreview) cls += " preview";
  else if (cell.bonus === "TW") cls += " bonus-tw";
  else if (cell.bonus === "DW") cls += " bonus-dw";
  else if (cell.bonus === "TL") cls += " bonus-tl";
  else if (cell.bonus === "DL") cls += " bonus-dl";
  else if (cell.bonus === "STAR") cls += " bonus-star";
  else cls += " empty";

  if (isSelected) cls += " selected";
  return cls;
}

function buildPreviewCells(suggestion) {
  if (!suggestion) return [];
  const placements = suggestion.placements || suggestion.newTiles || [];
  return placements.map((p) => ({
    row: p.row,
    col: p.col,
    letter: p.letter || "",
  }));
}

function cloneBoard(board) {
  return board.map((row) => row.map((cell) => ({ ...cell })));
}

function applySuggestionToBoard(board, suggestion) {
  const next = cloneBoard(board);
  const placements = suggestion?.placements || suggestion?.newTiles || [];
  for (const p of placements) {
    if (
      typeof p.row === "number" &&
      typeof p.col === "number" &&
      next[p.row] &&
      next[p.row][p.col]
    ) {
      next[p.row][p.col].letter = normalizeLetter(p.letter || "");
    }
  }
  return next;
}

function createTabFromBoardData(boardType, boardData, name) {
  return {
    id: `${Date.now()}-${Math.random().toString(36).slice(2, 8)}`,
    name,
    boardType,
    board: boardData.board || [],
    selectedCell: null,
    previewCells: [],
    rack: createEmptyRack(),
    suggestions: [],
    loading: false,
    renameMode: false,
  };
}

export default function App() {
  const [tabs, setTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [newBoardType, setNewBoardType] = useState("15x15");
  const [loadingBoard, setLoadingBoard] = useState(false);
  const rackRefs = useRef([]);
  const renameRefs = useRef({});

  const activeTab = useMemo(
    () => tabs.find((t) => t.id === activeTabId) || null,
    [tabs, activeTabId]
  );

  useEffect(() => {
    ensureStyles();
  }, []);

  useEffect(() => {
    if (!tabs.length) {
      handleCreateBoard("15x15");
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  useEffect(() => {
    const clickAway = () => {
      if (!activeTab) return;
      setTabs((prev) =>
        prev.map((tab) =>
          tab.id === activeTab.id ? { ...tab, previewCells: [] } : tab
        )
      );
    };

    window.addEventListener("click", clickAway);
    return () => window.removeEventListener("click", clickAway);
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
  }

  function handleBoardCellInput(row, col, value) {
    if (!activeTab) return;

    updateActiveTab((tab) => {
      const nextBoard = cloneBoard(tab.board);
      nextBoard[row][col].letter = value || "";
      return {
        ...tab,
        board: nextBoard,
        selectedCell: { row, col },
      };
    });
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

      const prevCol = col > 0 ? col - 1 : 0;
      nextBoard[row][prevCol].letter = "";
      return {
        ...tab,
        board: nextBoard,
        selectedCell: { row, col: prevCol },
      };
    });
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

  function previewSuggestion(suggestion) {
    if (!activeTab) return;
    const previewCells = buildPreviewCells(suggestion);
    updateActiveTab((tab) => ({
      ...tab,
      previewCells,
    }));
  }

  function applySuggestion(suggestion) {
    if (!activeTab) return;

    updateActiveTab((tab) => ({
      ...tab,
      board: applySuggestionToBoard(tab.board, suggestion),
      previewCells: [],
    }));
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
                          if (e.key === "Backspace" && !cell.letter) {
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
                  activeTab.suggestions.map((s, idx) => (
                    <div
                      key={idx}
                      className="suggestion-item"
                      onClick={(e) => {
                        e.stopPropagation();
                        previewSuggestion(s);
                      }}
                      onDoubleClick={(e) => {
                        e.stopPropagation();
                        applySuggestion(s);
                      }}
                    >
                      <div className="suggestion-main">
                        <strong>{s.word || s.kelime || "Kelime"}</strong>
                        <span>{s.score ?? s.puan ?? 0} puan</span>
                      </div>
                      <div className="suggestion-sub">
                        <span>
                          {s.direction || s.yon || "-"} •{" "}
                          {typeof s.row === "number" ? s.row + 1 : "-"} /{" "}
                          {typeof s.col === "number" ? s.col + 1 : "-"}
                        </span>
                      </div>
                    </div>
                  ))
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

function ensureStyles() {
  if (document.getElementById("kelime-asistani-app-styles")) return;

  const style = document.createElement("style");
  style.id = "kelime-asistani-app-styles";
  style.innerHTML = `
    * { box-sizing: border-box; }

    body {
      margin: 0;
      background: #0f1727;
      color: #eef3ff;
      font-family: Inter, Arial, sans-serif;
    }

    .app-shell {
      min-height: 100vh;
      padding: 18px;
      background:
        radial-gradient(circle at top left, rgba(80,120,255,.18), transparent 30%),
        #0f1727;
    }

    .topbar {
      display: flex;
      justify-content: space-between;
      gap: 16px;
      align-items: flex-start;
      margin-bottom: 14px;
    }

    .topbar h1 {
      margin: 0 0 6px;
      font-size: 28px;
    }

    .topbar p {
      margin: 0;
      color: #aeb9d7;
      max-width: 700px;
      line-height: 1.45;
    }

    .new-board-bar {
      display: flex;
      gap: 10px;
      align-items: center;
      flex-wrap: wrap;
    }

    .new-board-bar select,
    .new-board-bar button,
    .card button,
    .tab-close,
    .tab-rename-input,
    .rack-input {
      border: 0;
      outline: 0;
      font: inherit;
    }

    .new-board-bar select,
    .new-board-bar button,
    .card button {
      padding: 10px 14px;
      border-radius: 12px;
      background: #1b2740;
      color: #eef3ff;
      border: 1px solid rgba(255,255,255,.08);
    }

    .new-board-bar button,
    .card button {
      cursor: pointer;
    }

    .tabs-bar {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-bottom: 16px;
    }

    .tab-chip {
      display: inline-flex;
      align-items: center;
      gap: 8px;
      background: #182236;
      border: 1px solid rgba(255,255,255,.08);
      padding: 10px 12px;
      border-radius: 14px;
      cursor: pointer;
      min-height: 44px;
    }

    .tab-chip.active {
      background: #24324f;
      box-shadow: 0 0 0 2px rgba(93,162,255,.28) inset;
    }

    .tab-close {
      width: 24px;
      height: 24px;
      border-radius: 999px;
      background: rgba(255,255,255,.08);
      color: #fff;
      cursor: pointer;
    }

    .tab-rename-input {
      width: 110px;
      padding: 4px 6px;
      border-radius: 8px;
      background: rgba(255,255,255,.08);
      color: #fff;
    }

    .layout {
      display: grid;
      grid-template-columns: minmax(0, 1fr) 390px;
      gap: 18px;
      align-items: start;
    }

    .board-panel,
    .card {
      background: rgba(18, 27, 45, .9);
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 22px;
      padding: 16px;
      box-shadow: 0 10px 35px rgba(0,0,0,.24);
    }

    .side-panel {
      display: grid;
      gap: 16px;
      position: sticky;
      top: 18px;
    }

    .card-title-row {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 12px;
      margin-bottom: 12px;
      flex-wrap: wrap;
    }

    .card-title-row h2 {
      margin: 0;
      font-size: 18px;
    }

    .info-text {
      color: #aeb9d7;
      font-size: 13px;
    }

    .board-grid {
      display: grid;
      gap: 8px;
      width: 100%;
    }

    .board-cell {
      position: relative;
      aspect-ratio: 1 / 1;
      border-radius: 14px;
      border: 1px solid rgba(255,255,255,.08);
      overflow: hidden;
      display: flex;
      align-items: center;
      justify-content: center;
    }

    .board-cell.empty {
      background: #1b2740;
    }

    .board-cell.filled {
      background: #e1c67a;
    }

    .board-cell.preview {
      background: #79cf82;
    }

    .board-cell.bonus-tw {
      background: #c8a06f;
    }

    .board-cell.bonus-dw {
      background: #9cc586;
    }

    .board-cell.bonus-tl {
      background: #bca2cc;
    }

    .board-cell.bonus-dl {
      background: #88c2d1;
    }

    .board-cell.bonus-star {
      background: #d9c768;
    }

    .board-cell.selected {
      box-shadow: 0 0 0 2px #5da2ff inset;
    }

    .board-cell-bonus,
    .board-cell-preview-letter {
      position: absolute;
      inset: 0;
      display: flex;
      align-items: center;
      justify-content: center;
      font-weight: 800;
      pointer-events: none;
      user-select: none;
    }

    .board-cell-bonus {
      color: rgba(255,255,255,.96);
    }

    .board-cell-preview-letter {
      color: #1e3a1f;
      font-size: clamp(16px, 2.1vw, 28px);
    }

    .board-cell-input {
      position: absolute;
      inset: 0;
      width: 100%;
      height: 100%;
      border: 0;
      outline: 0;
      background: transparent;
      text-align: center;
      font-size: clamp(16px, 2.1vw, 28px);
      font-weight: 800;
      color: #243047;
      caret-color: transparent;
    }

    .board-cell.empty .board-cell-input,
    .board-cell.preview .board-cell-input,
    .board-cell.bonus-tw .board-cell-input,
    .board-cell.bonus-dw .board-cell-input,
    .board-cell.bonus-tl .board-cell-input,
    .board-cell.bonus-dl .board-cell-input,
    .board-cell.bonus-star .board-cell-input {
      color: transparent;
    }

    .board-cell.filled .board-cell-input {
      color: #243047;
    }

    .rack-row {
      display: grid;
      grid-template-columns: repeat(7, minmax(0, 1fr));
      gap: 8px;
    }

    .rack-input {
      width: 100%;
      min-height: 48px;
      border-radius: 12px;
      background: #e1c67a;
      color: #243047;
      text-align: center;
      font-size: 22px;
      font-weight: 800;
      border: 1px solid rgba(0,0,0,.08);
    }

    .suggestions-list {
      max-height: 460px;
      overflow: auto;
      padding-right: 4px;
      display: grid;
      gap: 8px;
    }

    .suggestion-item {
      background: #182236;
      border: 1px solid rgba(255,255,255,.08);
      border-radius: 14px;
      padding: 12px;
      cursor: pointer;
    }

    .suggestion-item:hover {
      background: #1d2940;
    }

    .suggestion-main {
      display: flex;
      justify-content: space-between;
      gap: 12px;
      align-items: center;
      margin-bottom: 4px;
    }

    .suggestion-sub {
      color: #aeb9d7;
      font-size: 13px;
    }

    .empty-state,
    .empty-page {
      color: #aeb9d7;
    }

    @media (max-width: 980px) {
      .layout {
        grid-template-columns: 1fr;
      }

      .side-panel {
        position: static;
      }
    }

    @media (max-width: 768px) {
      .app-shell {
        padding: 12px;
      }

      .topbar {
        flex-direction: column;
        align-items: stretch;
      }

      .board-grid {
        gap: 6px;
      }

      .board-cell {
        border-radius: 10px;
      }

      .board-cell-input,
      .board-cell-preview-letter {
        font-size: 18px;
      }

      .rack-input {
        min-height: 44px;
        font-size: 20px;
      }
    }
  `;
  document.head.appendChild(style);
}
