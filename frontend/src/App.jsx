import { useEffect, useMemo, useRef, useState } from 'react'
import BoardGrid from './components/BoardGrid'

const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'
const RACK_SIZE = 7
const TAB_LIMIT = 7
const VALID_LETTER = /^[A-Za-zÇĞİIÖŞÜçğıiöşü?]$/

function createEmptyBoard(size) {
  return Array.from({ length: size }, () => Array.from({ length: size }, () => ''))
}

function createRack() {
  return Array.from({ length: RACK_SIZE }, () => '')
}

function normalizeLetter(value) {
  return (value || '')
    .toString()
    .trim()
    .slice(0, 1)
    .toLocaleUpperCase('tr-TR')
}

function sanitizeRackInput(rawValue) {
  const value = (rawValue || '').toString()
  if (!value) return ''
  const char = value.at(-1)
  if (char === ' ') return ' '
  if (!VALID_LETTER.test(char)) return null
  return normalizeLetter(char)
}

function getNextDefaultTabNumber(tabs) {
  const nums = tabs
    .map((tab) => {
      const match = /^Tahta\s+(\d+)$/i.exec((tab.name || '').trim())
      return match ? Number(match[1]) : null
    })
    .filter((v) => Number.isInteger(v))
  return nums.length ? Math.max(...nums) + 1 : 1
}

function makeTab(id, boardType, size, bonusGrid, center, name) {
  return {
    id,
    name: name || `Tahta ${id}`,
    boardType,
    board: createEmptyBoard(size),
    bonusGrid,
    activeCell: { row: center[0], col: center[1] },
    rack: createRack(),
    rackCursor: 0,
    suggestions: [],
    preview: [],
  }
}

export default function App() {
  const [tabs, setTabs] = useState([])
  const [activeTabId, setActiveTabId] = useState(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showBoardPicker, setShowBoardPicker] = useState(false)
  const [renameTabId, setRenameTabId] = useState(null)
  const [renameValue, setRenameValue] = useState('')
  const rackRefs = useRef([])
  const renameRef = useRef(null)
  const nextInternalIdRef = useRef(1)
  const initializedRef = useRef(false)

  const activeTab = useMemo(
    () => tabs.find((tab) => tab.id === activeTabId) || tabs[0] || null,
    [tabs, activeTabId],
  )

  useEffect(() => {
    if (!initializedRef.current) {
      initializedRef.current = true
      createTab('15x15')
    }
  }, [])

  useEffect(() => {
    if (renameTabId && renameRef.current) {
      renameRef.current.focus()
      renameRef.current.select()
    }
  }, [renameTabId])

  useEffect(() => {
    if (!activeTab) return
    const index = Math.max(0, Math.min(RACK_SIZE - 1, activeTab.rackCursor ?? 0))
    const timer = setTimeout(() => {
      const el = rackRefs.current[index]
      if (!el) return
      if (document.activeElement !== el) el.focus()
      if (typeof el.select === 'function') el.select()
    }, 0)
    return () => clearTimeout(timer)
  }, [activeTabId, activeTab?.rackCursor])

  useEffect(() => {
    const handler = (event) => {
      const target = event.target
      const targetTag = target?.tagName?.toLowerCase()
      if (targetTag === 'input' || targetTag === 'textarea') return
      if (!activeTab?.activeCell) return

      const key = event.key
      if (key === 'Backspace' || key === 'Delete') {
        event.preventDefault()
        updateCell(activeTab.id, activeTab.activeCell.row, activeTab.activeCell.col, '')
        return
      }
      if (key === 'ArrowUp') { event.preventDefault(); return moveActive(activeTab.id, -1, 0) }
      if (key === 'ArrowDown') { event.preventDefault(); return moveActive(activeTab.id, 1, 0) }
      if (key === 'ArrowLeft') { event.preventDefault(); return moveActive(activeTab.id, 0, -1) }
      if (key === 'ArrowRight') { event.preventDefault(); return moveActive(activeTab.id, 0, 1) }
      if (key === ' ') return
      if (key.length === 1 && VALID_LETTER.test(key)) {
        event.preventDefault()
        updateCell(activeTab.id, activeTab.activeCell.row, activeTab.activeCell.col, normalizeLetter(key))
        moveActive(activeTab.id, 0, 1)
      }
    }

    window.addEventListener('keydown', handler)
    return () => window.removeEventListener('keydown', handler)
  }, [activeTab])

  async function fetchBoardMeta(boardType) {
    const res = await fetch(`${API_BASE}/api/board/${boardType}`)
    if (!res.ok) throw new Error('Tahta bilgisi alınamadı')
    return res.json()
  }

  async function createTab(boardType) {
    try {
      const data = await fetchBoardMeta(boardType)
      let createdId = null
      setTabs((current) => {
        if (current.length >= TAB_LIMIT) return current
        const defaultNumber = getNextDefaultTabNumber(current)
        createdId = nextInternalIdRef.current++
        return [...current, makeTab(createdId, boardType, data.size, data.bonusGrid, data.center, `Tahta ${defaultNumber}`)]
      })
      if (createdId !== null) setActiveTabId(createdId)
      setError('')
    } catch (err) {
      setError(err.message || 'Tahta oluşturulamadı')
    }
  }

  useEffect(() => {
    if (tabs.length > 0 && !tabs.some((t) => t.id === activeTabId)) {
      setActiveTabId(tabs[0].id)
    }
  }, [tabs, activeTabId])

  function updateTab(tabId, updater) {
    setTabs((current) => current.map((tab) => (tab.id === tabId ? updater(tab) : tab)))
  }

  function moveActive(tabId, dr, dc) {
    updateTab(tabId, (tab) => {
      const size = tab.board.length
      const prev = tab.activeCell
      if (!prev) return tab
      const row = Math.max(0, Math.min(size - 1, prev.row + dr))
      const col = Math.max(0, Math.min(size - 1, prev.col + dc))
      return { ...tab, activeCell: { row, col } }
    })
  }

  function updateCell(tabId, row, col, value) {
    updateTab(tabId, (tab) => {
      const nextBoard = tab.board.map((line) => [...line])
      nextBoard[row][col] = normalizeLetter(value)
      return { ...tab, board: nextBoard }
    })
  }

  function clearPreview() {
    if (!activeTab) return
    updateTab(activeTab.id, (tab) => ({ ...tab, preview: [] }))
  }

  function handleGlobalPointerDown(event) {
    if (event.target.closest('.suggestion')) return
    if (activeTab?.preview?.length) clearPreview()
  }

  function handleBoardCellClick(row, col) {
    updateTab(activeTab.id, (tab) => ({ ...tab, activeCell: { row, col }, preview: [] }))
  }

  function setRackCursor(tabId, index) {
    updateTab(tabId, (tab) => ({ ...tab, rackCursor: Math.max(0, Math.min(RACK_SIZE - 1, index)) }))
  }

  function focusRackIndex(index) {
    setTimeout(() => {
      const el = rackRefs.current[index]
      if (!el) return
      el.focus()
      if (typeof el.select === 'function') el.select()
    }, 0)
  }

  function updateRack(index, rawValue) {
    if (!activeTab) return
    const sanitized = sanitizeRackInput(rawValue)
    if (sanitized === null) return

    let accepted = false
    let nextIndex = index

    updateTab(activeTab.id, (tab) => {
      const currentRack = tab.rack || createRack()
      const nextRack = [...currentRack]
      const nextValue = sanitized === ' ' ? '' : sanitized
      const jokerCount = currentRack.filter((v, i) => i !== index && v === '?').length

      if (nextValue === '?' && jokerCount >= 2) {
        setError('En fazla iki joker girilebilir. Joker:?')
        return tab
      }

      nextRack[index] = nextValue
      accepted = true
      nextIndex = Math.min(index + 1, RACK_SIZE - 1)
      return { ...tab, rack: nextRack, rackCursor: nextIndex }
    })

    if (!accepted) return
    setError('')
    if (index < RACK_SIZE - 1) focusRackIndex(nextIndex)
  }

  function handleRackKeyDown(index, event) {
    if (!activeTab) return

    if (event.key === ' ') {
      event.preventDefault()
      updateRack(index, ' ')
      return
    }

    if (event.key === 'Backspace') {
      event.preventDefault()
      const value = activeTab.rack?.[index] || ''
      if (value) {
        updateTab(activeTab.id, (tab) => {
          const nextRack = [...(tab.rack || createRack())]
          nextRack[index] = ''
          return { ...tab, rack: nextRack, rackCursor: index }
        })
        focusRackIndex(index)
      } else if (index > 0) {
        updateTab(activeTab.id, (tab) => ({ ...tab, rackCursor: index - 1 }))
        focusRackIndex(index - 1)
      }
      return
    }

    if (event.key === 'Delete') {
      event.preventDefault()
      updateTab(activeTab.id, (tab) => {
        const nextRack = [...(tab.rack || createRack())]
        nextRack[index] = ''
        return { ...tab, rack: nextRack, rackCursor: index }
      })
      return
    }

    if (event.key === 'Enter' && index < RACK_SIZE - 1) {
      event.preventDefault()
      setRackCursor(activeTab.id, index + 1)
      focusRackIndex(index + 1)
      return
    }
    if (event.key === 'ArrowLeft' && index > 0) {
      event.preventDefault()
      setRackCursor(activeTab.id, index - 1)
      focusRackIndex(index - 1)
      return
    }
    if (event.key === 'ArrowRight' && index < RACK_SIZE - 1) {
      event.preventDefault()
      setRackCursor(activeTab.id, index + 1)
      focusRackIndex(index + 1)
    }
  }

  async function solve() {
    if (!activeTab) return
    try {
      setLoading(true)
      setError('')
      const res = await fetch(`${API_BASE}/api/solve`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          boardType: activeTab.boardType,
          boardLetters: activeTab.board,
          rack: activeTab.rack || createRack(),
          limit: 1000,
        }),
      })
      const data = await res.json()
      if (!res.ok) throw new Error(data.detail || 'Öneriler alınamadı')
      updateTab(activeTab.id, (tab) => ({ ...tab, suggestions: data.suggestions, preview: [] }))
    } catch (err) {
      setError(err.message || 'Bir hata oluştu')
    } finally {
      setLoading(false)
    }
  }

  function previewSuggestion(item) {
    if (!activeTab) return
    updateTab(activeTab.id, (tab) => ({ ...tab, preview: item.placed || [] }))
  }

  function applySuggestion(item) {
    if (!activeTab) return
    updateTab(activeTab.id, (tab) => {
      const nextBoard = tab.board.map((line) => [...line])
      ;(item.placed || []).forEach(({ row, col, letter }) => {
        nextBoard[row][col] = letter
      })
      return { ...tab, board: nextBoard, preview: [] }
    })
  }

  function startRename(tab) {
    setRenameTabId(tab.id)
    setRenameValue(tab.name)
  }

  function commitRename() {
    const value = renameValue.trim()
    if (renameTabId === null) return
    updateTab(renameTabId, (tab) => ({ ...tab, name: value || tab.name }))
    setRenameTabId(null)
    setRenameValue('')
  }

  function closeTab(tabId) {
    setTabs((current) => {
      if (current.length === 1) return current
      const idx = current.findIndex((t) => t.id === tabId)
      const next = current.filter((tab) => tab.id !== tabId)
      if (activeTabId === tabId) {
        const fallback = next[Math.max(0, idx - 1)] || next[0]
        if (fallback) setActiveTabId(fallback.id)
      }
      return next
    })
  }

  const canCreateTab = tabs.length < TAB_LIMIT

  return (
    <div className="page" onMouseDownCapture={handleGlobalPointerDown} onTouchStartCapture={handleGlobalPointerDown}>
      <header className="hero compact">
        <div className="brand-row">
          <h1>Kelime Asistanı</h1>
          <div className="controls">
            <button type="button" className="primary" onClick={() => setShowBoardPicker((v) => !v)} disabled={!canCreateTab}>
              Yeni Tahta
            </button>
            {showBoardPicker && canCreateTab && (
              <div className="picker-popover">
                <button type="button" onClick={() => { setShowBoardPicker(false); createTab('15x15') }}>15x15</button>
                <button type="button" onClick={() => { setShowBoardPicker(false); createTab('9x9') }}>9x9</button>
              </div>
            )}
          </div>
        </div>

        <div className="tabs-strip">
          {tabs.map((tab) => (
            <div key={tab.id} className={`tab-chip ${tab.id === activeTabId ? 'active' : ''}`} onClick={() => { setActiveTabId(tab.id); setShowBoardPicker(false) }}>
              {renameTabId === tab.id ? (
                <input
                  ref={renameRef}
                  className="tab-rename"
                  value={renameValue}
                  onChange={(e) => setRenameValue(e.target.value)}
                  onBlur={commitRename}
                  onKeyDown={(e) => { if (e.key === 'Enter') commitRename() }}
                />
              ) : (
                <button type="button" className="tab-name" onDoubleClick={(e) => { e.stopPropagation(); startRename(tab) }}>
                  {tab.name}
                </button>
              )}
              <button
                type="button"
                className="tab-close"
                onClick={(e) => { e.stopPropagation(); closeTab(tab.id) }}
                aria-label={`${tab.name} kapat`}
                disabled={tabs.length === 1}
              >
                ×
              </button>
            </div>
          ))}
        </div>
      </header>

      <main className="layout">
        <section className="panel board-panel">
          {activeTab && (
            <BoardGrid
              board={activeTab.board}
              bonusGrid={activeTab.bonusGrid}
              activeCell={activeTab.activeCell}
              previewCells={activeTab.preview}
              onCellClick={handleBoardCellClick}
              onBoardPointerDown={clearPreview}
            />
          )}
        </section>

        <aside className="panel side-panel">
          <div className="rack-card">
            <div className="rack-head">
              <label>Harfler</label>
              <span className="muted">En fazla iki joker girilebilir. Joker:?</span>
            </div>
            <div className="rack-grid">
              {(activeTab?.rack || createRack()).map((letter, index) => (
                <input
                  key={index}
                  ref={(el) => (rackRefs.current[index] = el)}
                  className="rack-slot"
                  value={letter}
                  onChange={(e) => updateRack(index, e.target.value)}
                  onKeyDown={(e) => handleRackKeyDown(index, e)}
                  onFocus={() => activeTab && setRackCursor(activeTab.id, index)}
                  onClick={() => activeTab && setRackCursor(activeTab.id, index)}
                  maxLength={1}
                  inputMode="text"
                  enterKeyHint="next"
                  autoComplete="off"
                />
              ))}
            </div>
          </div>

          <div className="actions">
            <button className="primary" onClick={solve} disabled={loading || !activeTab}>
              {loading ? 'Hesaplanıyor...' : 'En İyi Önerileri Hesapla'}
            </button>
          </div>

          {error && <p className="error">{error}</p>}

          <div className="suggestions">
            <h3>Öneriler</h3>
            <div className="suggestions-list">
              {activeTab?.suggestions?.length ? (
                activeTab.suggestions.map((item, index) => {
                  const isHighlighted = JSON.stringify(activeTab.preview || []) === JSON.stringify(item.placed || [])
                  return (
                    <button
                      key={`${item.word}-${index}`}
                      className={`suggestion ${isHighlighted ? 'highlighted' : ''}`}
                      onClick={() => previewSuggestion(item)}
                      onDoubleClick={() => applySuggestion(item)}
                      type="button"
                    >
                      <div>
                        <strong>{item.word}</strong>
                        <span>{item.direction} · {item.row + 1},{item.col + 1}</span>
                      </div>
                      <b>{item.score}</b>
                    </button>
                  )
                })
              ) : (
                <p className="muted">Henüz öneri yok.</p>
              )}
            </div>
          </div>
        </aside>
      </main>
    </div>
  )
}
