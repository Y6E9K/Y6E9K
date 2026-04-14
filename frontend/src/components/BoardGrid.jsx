import React from "react";

function bonusLabel(bonus) {
  switch (bonus) {
    case "K3":
      return "K3";
    case "K2":
      return "K2";
    case "H3":
      return "H3";
    case "H2":
      return "H2";
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
  else if (cell.bonus === "K3") cls += " bonus-tw";
  else if (cell.bonus === "K2") cls += " bonus-dw";
  else if (cell.bonus === "H3") cls += " bonus-tl";
  else if (cell.bonus === "H2") cls += " bonus-dl";
  else if (cell.bonus === "START") cls += " bonus-star";
  else cls += " empty";

  if (isSelected) cls += " selected";
  return cls;
}

export default function BoardGrid({
  board,
  boardType,
  selectedCell,
  previewCells = [],
  cellRefs,
  onSelectCell,
  onCellChange,
  onCellBackspace,
}) {
  const previewMap = new Map(
    (previewCells || []).map((p) => [`${p.row}-${p.col}`, p])
  );

  return (
    <div
      className="board-grid"
      style={{
        gridTemplateColumns: `repeat(${boardType === "9x9" ? 9 : 15}, minmax(0, 1fr))`,
      }}
    >
      {board.map((row, rowIndex) =>
        row.map((cell, colIndex) => {
          const key = `${rowIndex}-${colIndex}`;
          const previewItem = previewMap.get(key);
          const isPreview = !!previewItem && !cell.letter;
          const isSelected =
            selectedCell?.row === rowIndex && selectedCell?.col === colIndex;

          return (
            <div
              key={key}
              className={cellClassName(cell, isPreview, isSelected)}
              data-bonus={cell.bonus || ""}
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
                ref={(el) => {
                  if (cellRefs?.current) {
                    cellRefs.current[key] = el;
                  }
                }}
                data-cell={key}
                className="board-cell-input"
                value={cell.letter || ""}
                maxLength={1}
                inputMode="text"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="characters"
                spellCheck={false}
                onPaste={(e) => e.preventDefault()}
                onFocus={() => onSelectCell?.(rowIndex, colIndex)}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectCell?.(rowIndex, colIndex);
                }}
                onChange={(e) => {
                  const raw = e.target.value || "";
                  if (!raw) return;
                  onCellChange?.(rowIndex, colIndex, raw);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Backspace") {
                    e.preventDefault();
                    onCellBackspace?.(rowIndex, colIndex);
                  }
                }}
                aria-label={`Hücre ${rowIndex + 1}-${colIndex + 1}`}
              />
            </div>
          );
        })
      )}
    </div>
  );
}
