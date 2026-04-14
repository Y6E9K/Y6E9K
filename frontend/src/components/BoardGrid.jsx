import React from "react";

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
      return "★2";
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

export default function BoardGrid({
  board,
  selectedCell,
  previewCells,
  onSelectCell,
  onCellInput,
  onCellBackspace,
}) {
  const previewMap = new Map((previewCells || []).map((p) => [`${p.row}-${p.col}`, p]));

  return (
    <div
      className="board-grid"
      style={{ gridTemplateColumns: `repeat(${board.length}, minmax(0, 1fr))` }}
    >
      {board.map((row, rowIndex) =>
        row.map((cell, colIndex) => {
          const isSelected =
            selectedCell?.row === rowIndex && selectedCell?.col === colIndex;
          const previewItem = previewMap.get(`${rowIndex}-${colIndex}`);
          const isPreview = !!previewItem && !cell.letter;

          return (
            <div
              key={`${rowIndex}-${colIndex}`}
              className={cellClassName(cell, isPreview, isSelected)}
              data-bonus={cell.bonus || ""}
            >
              {!cell.letter && !isPreview && cell.bonus && (
                <span className="board-cell-bonus">{bonusLabel(cell.bonus)}</span>
              )}

              {isPreview && !cell.letter && (
                <span className="board-cell-preview-letter">{previewItem.letter}</span>
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
                onFocus={() => onSelectCell(rowIndex, colIndex)}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectCell(rowIndex, colIndex);
                }}
                onChange={(e) => onCellInput(rowIndex, colIndex, e.target.value || "")}
                onKeyDown={(e) => {
                  if (e.key === "Backspace") {
                    e.preventDefault();
                    onCellBackspace(rowIndex, colIndex);
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
