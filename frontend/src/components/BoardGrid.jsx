import React from "react";

function bonusClass(bonus) {
  if (bonus === "K3") return "bonus-tw";
  if (bonus === "K2") return "bonus-dw";
  if (bonus === "H3") return "bonus-tl";
  if (bonus === "H2") return "bonus-dl";
  if (bonus === "START") return "bonus-star";
  return "";
}

function bonusText(bonus) {
  if (bonus === "START") return "★";
  return bonus || "";
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
  const size = boardType === "9x9" ? 9 : 15;
  const previewMap = new Map(previewCells.map((p) => [`${p.row}-${p.col}`, p.letter]));

  return (
    <div className={`board-grid board-${size}`} style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}>
      {board.map((row, r) =>
        row.map((cell, c) => {
          const key = `${r}-${c}`;
          const isSelected = selectedCell?.row === r && selectedCell?.col === c;
          const previewLetter = previewMap.get(key);
          const isPreview = Boolean(previewLetter);
          const isFilled = Boolean(cell.letter);

          return (
            <div
              key={key}
              className={[
                "board-cell",
                isFilled ? "filled" : "empty",
                cell.bonus && !isFilled && !isPreview ? bonusClass(cell.bonus) : "",
                isSelected ? "selected" : "",
                isPreview ? "preview" : "",
              ].join(" ")}
              onClick={() => onSelectCell(r, c)}
            >
              {!isFilled && !isPreview && cell.bonus && <span className="board-cell-bonus">{bonusText(cell.bonus)}</span>}
              {isPreview && !isFilled && <span className="board-cell-preview-letter">{previewLetter}</span>}
              <input
                ref={(el) => {
                  if (cellRefs?.current) cellRefs.current[key] = el;
                }}
                className="board-cell-input"
                value={cell.letter || ""}
                inputMode="text"
                autoComplete="off"
                autoCorrect="off"
                autoCapitalize="characters"
                spellCheck={false}
                maxLength={1}
                onFocus={() => onSelectCell(r, c)}
                onClick={(e) => {
                  e.stopPropagation();
                  onSelectCell(r, c);
                }}
                onChange={(e) => {
                  const value = e.target.value;
                  if (value) onCellChange(r, c, value);
                }}
                onKeyDown={(e) => {
                  if (e.key === "Backspace") {
                    e.preventDefault();
                    onCellBackspace(r, c);
                  }
                }}
              />
            </div>
          );
        })
      )}
    </div>
  );
}
