import React from "react";

const VALID_CELL_INPUT = /^[A-Za-zÇĞİIÖŞÜçğıiöşü?]$/;

function normalizeLetter(value) {
  if (!value) return "";
  return value.toString().slice(0, 1).toLocaleUpperCase("tr-TR");
}

function getBonusLabel(bonus) {
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

function getCellClassName(cell, isPreview) {
  const classes = ["board-cell"];

  if (cell.letter) {
    classes.push("filled");
  } else if (isPreview) {
    classes.push("preview");
  } else if (cell.bonus === "TW") {
    classes.push("bonus-tw");
  } else if (cell.bonus === "DW") {
    classes.push("bonus-dw");
  } else if (cell.bonus === "TL") {
    classes.push("bonus-tl");
  } else if (cell.bonus === "DL") {
    classes.push("bonus-dl");
  } else if (cell.bonus === "STAR") {
    classes.push("bonus-star");
  } else {
    classes.push("empty");
  }

  return classes.join(" ");
}

export default function BoardGrid({
  board,
  boardType,
  selectedCell,
  previewCells = [],
  onSelectCell,
  onCellInput,
  onCellBackspace,
}) {
  const size = boardType === "9x9" ? 9 : 15;
  const previewSet = new Set(previewCells.map((c) => `${c.row}-${c.col}`));

  return (
    <div
      className="board-grid"
      style={{ gridTemplateColumns: `repeat(${size}, minmax(0, 1fr))` }}
    >
      {board.map((row, rowIndex) =>
        row.map((cell, colIndex) => {
          const isSelected =
            selectedCell?.row === rowIndex && selectedCell?.col === colIndex;
          const isPreview = previewSet.has(`${rowIndex}-${colIndex}`);
          const className = `${getCellClassName(cell, isPreview)} ${
            isSelected ? "selected" : ""
          }`;

          return (
            <div key={`${rowIndex}-${colIndex}`} className={className}>
              {!cell.letter && !isPreview && (
                <span className="board-cell-bonus">{getBonusLabel(cell.bonus)}</span>
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
                onFocus={() => onSelectCell?.(rowIndex, colIndex)}
                onClick={() => onSelectCell?.(rowIndex, colIndex)}
                onChange={(e) => {
                  const raw = e.target.value || "";
                  if (!raw) {
                    onCellInput?.(rowIndex, colIndex, "");
                    return;
                  }

                  const ch = raw.slice(-1);
                  if (!VALID_CELL_INPUT.test(ch)) {
                    return;
                  }

                  onCellInput?.(rowIndex, colIndex, normalizeLetter(ch));
                }}
                onKeyDown={(e) => {
                  if (e.key === "Backspace" && !cell.letter) {
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
