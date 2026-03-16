function Board({ board, dropDisc, players }) {
  return (
    <div className="board">
      {board.map((row, r) =>
        row.map((cell, c) => (
          <div
            key={`${r}-${c}`}
            className="cell"
            style={{
              backgroundColor: cell
                ? players[cell].color
                : "#111"
            }}
            onClick={() => dropDisc(c)}
          />
        ))
      )}
    </div>
  );
}

export default Board;
