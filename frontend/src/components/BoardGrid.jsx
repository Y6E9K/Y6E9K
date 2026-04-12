export default function BoardGrid({
  board,
  bonusGrid,
  activeCell,
  previewCells = [],
  onCellClick,
  onBoardPointerDown,
}) {
  const size = board.length
  const previewSet = new Set(previewCells.map((item) => `${item.row}-${item.col}`))

  return (
    <div
      className="board"
      style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}
      onMouseDown={onBoardPointerDown}
      onTouchStart={onBoardPointerDown}
    >
      {board.map((row, r) =>
        row.map((cell, c) => {
          const bonus = bonusGrid[r]?.[c]
          const hasLetter = Boolean(cell)
          const classes = ['cell']
          if (bonus) classes.push(`bonus-${bonus.toLowerCase()}`)
          if (hasLetter) classes.push('filled')
          if (activeCell?.row === r && activeCell?.col === c) classes.push('active')
          if (previewSet.has(`${r}-${c}`)) classes.push('preview')
          return (
            <button
              key={`${r}-${c}`}
              className={classes.join(' ')}
              onClick={() => onCellClick(r, c)}
              type="button"
              title={hasLetter ? `Harf: ${cell}` : `Bonus: ${bonus || 'normal'}`}
            >
              {hasLetter ? <span className="tile-letter">{cell}</span> : bonusLabel(bonus)}
            </button>
          )
        }),
      )}
    </div>
  )
}

function bonusLabel(bonus) {
  if (!bonus) return ''
  if (bonus === 'START') return '★'
  return bonus
}
