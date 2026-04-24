import React, { useEffect, useMemo, useRef, useState } from "react";
import BoardGrid from "./components/BoardGrid";

const API_BASE = import.meta.env.VITE_API_URL || "http://localhost:8000";
const MAX_TABS = 7;
const VALID_TR_CELL = /^[ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ?]$/;
const VALID_TR_RACK = /^[ABCÇDEFGĞHIİJKLMNOÖPRSŞTUÜVYZ? ]$/;
const STORAGE_KEY = "kelime_asistani_state_v3";

function normalizeTR(value) {
  if (!value) return "";
  const raw = String(value).trim().slice(0, 1);
  const map = { i: "İ", ı: "I", ş: "Ş", ğ: "Ğ", ü: "Ü", ö: "Ö", ç: "Ç" };
  if (map[raw]) return map[raw];
  return raw.toLocaleUpperCase("tr-TR");
}
function createEmptyRack() { return ["", "", "", "", "", "", ""]; }
function cloneBoard(board) { return board.map((row) => row.map((cell) => ({ ...cell }))); }
function createEmptyBoard(size) { return Array.from({ length: size }, () => Array.from({ length: size }, () => ({ letter: "", bonus: null }))); }
function getNextBoardNumber(tabs) { const nums = tabs.map(t => String(t.name || "").match(/^Tahta\s+(\d+)$/i)?.[1]).filter(Boolean).map(Number); return nums.length ? Math.max(...nums) + 1 : 1; }
function normalizeBoardData(boardType, data) { if (Array.isArray(data?.bonusGrid)) return data.bonusGrid.map(row => row.map(bonus => ({ letter: "", bonus: bonus || null }))); return createEmptyBoard(boardType === "9x9" ? 9 : 15); }
function createTab(boardType, data, name) { return { id: `${Date.now()}-${Math.random().toString(36).slice(2)}`, name, boardType, board: normalizeBoardData(boardType, data), selectedCell: null, previewCells: [], rack: createEmptyRack(), suggestions: [], loading: false, renameMode: false }; }
function parseDirection(raw) { const v = String(raw || "").toLowerCase(); if (v.includes("dikey") || v === "vertical" || v === "down") return "vertical"; if (v.includes("yatay") || v === "horizontal" || v === "right") return "horizontal"; return ""; }
function extractPlacements(s, board = []) {
  if (!s) return [];
  const direct = s.placed || s.placements || s.tiles || [];
  if (Array.isArray(direct) && direct.length) return direct.map(p => ({ row: p.row, col: p.col, letter: normalizeTR(p.letter || "") })).filter(p => Number.isInteger(p.row) && Number.isInteger(p.col) && p.letter);
  const word = String(s.word || "").split("").map(normalizeTR).join(""); const dir = parseDirection(s.direction || ""); const row = Number(s.row), col = Number(s.col); if (!word || Number.isNaN(row) || Number.isNaN(col) || !dir) return [];
  const out = [];
  for (let i = 0; i < word.length; i++) { const r = row + (dir === "vertical" ? i : 0); const c = col + (dir === "horizontal" ? i : 0); if (!board[r]?.[c]) return []; const existing = normalizeTR(board[r][c].letter || ""); if (!existing) out.push({ row: r, col: c, letter: normalizeTR(word[i]) }); else if (existing !== normalizeTR(word[i])) return []; }
  return out;
}
function applySuggestionToBoard(board, suggestion) { const next = cloneBoard(board); for (const p of extractPlacements(suggestion, board)) next[p.row][p.col].letter = p.letter; return next; }

export default function App() {
  const [tabs, setTabs] = useState([]);
  const [activeTabId, setActiveTabId] = useState(null);
  const [newBoardType, setNewBoardType] = useState("15x15");
  const [solveMode, setSolveMode] = useState("fast");
  const [solveProgress, setSolveProgress] = useState(0);
  const [loadingBoard, setLoadingBoard] = useState(false);
  const [activeSuggestionKey, setActiveSuggestionKey] = useState(null);
  const rackRefs = useRef([]); const cellRefs = useRef({}); const lastTapRef = useRef({ key: null, time: 0 });
  const activeTab = useMemo(() => tabs.find(t => t.id === activeTabId) || null, [tabs, activeTabId]);

  useEffect(() => { try { const saved = JSON.parse(localStorage.getItem(STORAGE_KEY) || "null"); if (saved?.tabs?.length) { const restored = saved.tabs.map(t => ({ ...t, previewCells: [], selectedCell: null, loading: false, renameMode: false })); setTabs(restored); setActiveTabId(saved.activeTabId || restored[0].id); setNewBoardType(saved.newBoardType || "15x15"); setSolveMode(saved.solveMode === "max" ? "max" : "fast"); return; } } catch {} handleCreateBoard("15x15"); }, []);
  useEffect(() => { localStorage.setItem(STORAGE_KEY, JSON.stringify({ tabs: tabs.map(t => ({ ...t, previewCells: [], selectedCell: null, loading: false, renameMode: false })), activeTabId, newBoardType, solveMode })); }, [tabs, activeTabId, newBoardType, solveMode]);

  async function fetchBoard(type) { const r = await fetch(`${API_BASE}/api/board/${type}`); if (!r.ok) throw new Error("Tahta verisi alınamadı"); return r.json(); }
  async function handleCreateBoard(forced) { const type = forced || newBoardType; if (tabs.length >= MAX_TABS) return alert("En fazla 7 sekme açılabilir."); try { setLoadingBoard(true); const data = await fetchBoard(type); const newTab = createTab(type, data, `Tahta ${getNextBoardNumber(tabs)}`); setTabs(prev => [...prev, newTab]); setActiveTabId(newTab.id); } catch (e) { console.error(e); alert("Tahta oluşturulamadı."); } finally { setLoadingBoard(false); } }
  function updateActive(fn) { setTabs(prev => prev.map(t => t.id === activeTabId ? fn(t) : t)); }
  function closeTab(id) { setTabs(prev => { const next = prev.filter(t => t.id !== id); if (id === activeTabId) setActiveTabId(next.at(-1)?.id || null); return next; }); }
  function selectCell(row, col) { updateActive(t => ({ ...t, selectedCell: { row, col }, previewCells: [] })); setActiveSuggestionKey(null); }
  function focusCell(row, col) { cellRefs.current[`${row}-${col}`]?.focus(); }
  function cellInput(row, col, value) { const ch = normalizeTR(value); if (!VALID_TR_CELL.test(ch) || !activeTab) return; const width = activeTab.boardType === "9x9" ? 9 : 15; updateActive(t => { const b = cloneBoard(t.board); b[row][col].letter = ch; return { ...t, board: b, selectedCell: { row, col: Math.min(col + 1, width - 1) } }; }); setTimeout(() => focusCell(row, Math.min(col + 1, width - 1)), 0); }
  function cellBackspace(row, col) { updateActive(t => { const b = cloneBoard(t.board); if (b[row][col].letter) { b[row][col].letter = ""; return { ...t, board: b, selectedCell: { row, col } }; } const pc = Math.max(col - 1, 0); b[row][pc].letter = ""; setTimeout(() => focusCell(row, pc), 0); return { ...t, board: b, selectedCell: { row, col: pc } }; }); }
  function focusRack(i) { rackRefs.current[i]?.focus(); rackRefs.current[i]?.select?.(); }
  function setRackFrom(index, raw) { updateActive(t => { const rack = [...t.rack]; let cur = index; for (const rc of String(raw || "")) { if (cur > 6) break; if (rc === " ") { rack[cur++] = ""; continue; } const ch = normalizeTR(rc); if (!VALID_TR_RACK.test(ch)) continue; if (ch === "?" && rack.filter(x => x === "?").length >= 2 && rack[cur] !== "?") continue; rack[cur++] = ch; } return { ...t, rack }; }); setTimeout(() => focusRack(Math.min(index + Math.max(String(raw || "").length, 1), 6)), 0); }
  function rackKey(i, e) { if (e.key === "Backspace") { e.preventDefault(); updateActive(t => { const rack = [...t.rack]; if (rack[i]) rack[i] = ""; else { const p = Math.max(i - 1, 0); rack[p] = ""; setTimeout(() => focusRack(p), 0); } return { ...t, rack }; }); } if (e.key === "ArrowLeft") { e.preventDefault(); focusRack(Math.max(i - 1, 0)); } if (e.key === "ArrowRight") { e.preventDefault(); focusRack(Math.min(i + 1, 6)); } if (e.key === " ") { e.preventDefault(); setRackFrom(i, " "); } }
  async function handleSolve() { if (!activeTab) return; let timer = null; try { setSolveProgress(0); const totalMs = solveMode === "max" ? 45000 : 30000; const start = Date.now(); timer = setInterval(() => setSolveProgress(Math.min(95, Math.round(((Date.now() - start) / totalMs) * 100))), 300); updateActive(t => ({ ...t, loading: true, previewCells: [] })); const payload = { boardType: activeTab.boardType, board: activeTab.board.map(row => row.map(cell => ({ bonus: cell.bonus, letter: cell.letter || "" }))), rack: activeTab.rack.filter(Boolean), mode: solveMode }; const res = await fetch(`${API_BASE}/api/solve`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload) }); const data = await res.json(); updateActive(t => ({ ...t, loading: false, suggestions: Array.isArray(data.suggestions) ? data.suggestions : [] })); } catch (e) { console.error(e); updateActive(t => ({ ...t, loading: false })); alert("Öneriler alınırken hata oluştu."); } finally { if (timer) clearInterval(timer); setSolveProgress(100); setTimeout(() => setSolveProgress(0), 800); } }
  function preview(s, key) { updateActive(t => ({ ...t, previewCells: extractPlacements(s, t.board) })); setActiveSuggestionKey(key); }
  function apply(s) { updateActive(t => ({ ...t, board: applySuggestionToBoard(t.board, s), previewCells: [] })); setActiveSuggestionKey(null); }
  function suggestionTap(s, key) { const now = Date.now(); if (lastTapRef.current.key === key && now - lastTapRef.current.time < 400) { apply(s); lastTapRef.current = { key: null, time: 0 }; } else { preview(s, key); lastTapRef.current = { key, time: now }; } }

  return <div className="app-shell"><header className="topbar"><div><h1>Kelime Asistanı</h1><p>Tahtaya tıkla, harf yaz. Dolu kare taş rengine döner; silince eski bonus rengi geri gelir.</p></div><div className="new-board-bar"><select value={newBoardType} onChange={e => setNewBoardType(e.target.value)}><option value="15x15">15x15</option><option value="9x9">9x9</option></select><select value={solveMode} onChange={e => setSolveMode(e.target.value)}><option value="fast">Hızlı Mod</option><option value="max">Çok Derin Mod</option></select><button onClick={() => handleCreateBoard()} disabled={loadingBoard}>{loadingBoard ? "Açılıyor..." : "Yeni Tahta"}</button></div></header><div className="tabs-bar">{tabs.map(t => <div key={t.id} className={`tab-chip ${t.id === activeTabId ? "active" : ""}`} onClick={() => setActiveTabId(t.id)}><span>{t.name}</span><button className="tab-close" onClick={e => { e.stopPropagation(); closeTab(t.id); }}>×</button></div>)}</div>{activeTab ? <main className="layout"><section className="board-panel"><BoardGrid board={activeTab.board} boardType={activeTab.boardType} selectedCell={activeTab.selectedCell} previewCells={activeTab.previewCells} cellRefs={cellRefs} onSelectCell={selectCell} onCellChange={cellInput} onCellBackspace={cellBackspace} /></section><aside className="side-panel"><section className="card"><div className="card-title-row"><h2>Harfler</h2><span className="info-text">En fazla iki joker girilebilir. Joker:?</span></div><div className="rack-row">{activeTab.rack.map((v, i) => <input key={i} ref={el => rackRefs.current[i] = el} className="rack-input" value={v} maxLength={7} inputMode="text" autoComplete="off" autoCorrect="off" autoCapitalize="characters" spellCheck={false} onPaste={e => e.preventDefault()} onChange={e => setRackFrom(i, e.target.value)} onKeyDown={e => rackKey(i, e)} />)}</div></section><section className="card"><div className="card-title-row"><h2>Öneriler</h2><button onClick={handleSolve} disabled={activeTab.loading}>{activeTab.loading ? "Hesaplanıyor..." : "En İyi Önerileri Hesapla"}</button></div><div className="suggestion-sub" style={{ marginBottom: 10 }}>Aktif mod: {solveMode === "max" ? "Çok Derin" : "Hızlı"}</div>{activeTab.loading && <div className="progress-wrap"><div className="progress-label">{solveMode === "max" ? "Çok Derin Mod taranıyor..." : "Hızlı Mod taranıyor..."} %{solveProgress}</div><div className="progress-bar"><div className="progress-fill" style={{ width: `${solveProgress}%` }} /></div></div>}<div className="suggestions-list">{activeTab.suggestions.length ? activeTab.suggestions.map((s, idx) => { const key = `${idx}-${s.word}`; return <div key={key} className={`suggestion-item ${activeSuggestionKey === key ? "active" : ""}`} onClick={e => { e.stopPropagation(); suggestionTap(s, key); }} onDoubleClick={e => { e.stopPropagation(); apply(s); }} onTouchEnd={e => { e.preventDefault(); e.stopPropagation(); suggestionTap(s, key); }}><div className="suggestion-main"><strong>{s.word || "Kelime"}</strong><span>{s.score ?? 0} puan</span></div><div className="suggestion-sub">{String(s.direction || "-")} • {Number.isInteger(s.row) ? s.row + 1 : ""} / {Number.isInteger(s.col) ? s.col + 1 : ""}</div></div>; }) : <div className="empty-state">Henüz öneri yok.</div>}</div></section></aside></main> : <div className="empty-page">Tahta yükleniyor...</div>}</div>;
}
