import { useState } from "react";
import Board from "./Board";
import "./App.css";
document.title="connect game";
const ROWS = 6;
const COLS = 7;

const createBoard = () =>
  Array.from({ length: ROWS }, () => Array(COLS).fill(null));

function App() {
  const [board, setBoard] = useState(createBoard());
  const [currentPlayer, setCurrentPlayer] = useState("p1");
  const [winner, setWinner] = useState(null);
  const [gameStarted, setGameStarted] = useState(false);

  const [players, setPlayers] = useState({
    p1: { name: "", color: "red", score: 0 },
    p2: { name: "", color: "yellow", score: 0 }
  });

  const startGame = () => {
    if (!players.p1.name || !players.p2.name) {
      alert("Please enter both player names");
      return;
    }

    alert(
      `✅ 2 players are entered\n\n` +
      `Player 1: ${players.p1.name}\n` +
      `Player 2: ${players.p2.name}`
    );

    setGameStarted(true);
  };

  const dropDisc = (col) => {
    if (!gameStarted || winner) return;

    const newBoard = board.map(row => [...row]);

    for (let row = ROWS - 1; row >= 0; row--) {
      if (!newBoard[row][col]) {
        newBoard[row][col] = currentPlayer;

        if (checkWin(newBoard, row, col, currentPlayer)) {
          setWinner(currentPlayer);
          setPlayers(prev => ({
            ...prev,
            [currentPlayer]: {
              ...prev[currentPlayer],
              score: prev[currentPlayer].score + 1
            }
          }));
        }

        setBoard(newBoard);
        setCurrentPlayer(currentPlayer === "p1" ? "p2" : "p1");
        return;
      }
    }
  };

  const nextRound = () => {
    setBoard(createBoard());
    setWinner(null);
    setCurrentPlayer("p1");
  };

  const resetGame = () => {
    setBoard(createBoard());
    setWinner(null);
    setGameStarted(false);
    setCurrentPlayer("p1");
    setPlayers({
      p1: { name: "", color: "red", score: 0 },
      p2: { name: "", color: "yellow", score: 0 }
    });
  };

  return (
    <div className="app">
      <h1>Connect Four</h1>

      {!gameStarted ? (
        <div className="setup">
          <input
            placeholder="Player 1 Name"
            value={players.p1.name}
            onChange={(e) =>
              setPlayers({
                ...players,
                p1: { ...players.p1, name: e.target.value }
              })
            }
          />

          <select
            value={players.p1.color}
            onChange={(e) =>
              setPlayers({
                ...players,
                p1: { ...players.p1, color: e.target.value }
              })
            }
          >
            <option value="red">Red</option>
            <option value="blue">Blue</option>
            <option value="green">Green</option>
          </select>

          <input
            placeholder="Player 2 Name"
            value={players.p2.name}
            onChange={(e) =>
              setPlayers({
                ...players,
                p2: { ...players.p2, name: e.target.value }
              })
            }
          />

          <select
            value={players.p2.color}
            onChange={(e) =>
              setPlayers({
                ...players,
                p2: { ...players.p2, color: e.target.value }
              })
            }
          >
            <option value="yellow">Yellow</option>
            <option value="purple">Purple</option>
            <option value="orange">Orange</option>
          </select>

          <button onClick={startGame}>Start Game</button>
        </div>
      ) : (
        <>
          <div className="scoreboard">
            <span>{players.p1.name}: {players.p1.score}</span>
            <span>{players.p2.name}: {players.p2.score}</span>
          </div>

          {winner ? (
            <h2>🎉 {players[winner].name} Wins!</h2>
          ) : (
            <h2>Turn: {players[currentPlayer].name}</h2>
          )}

          <Board
            board={board}
            dropDisc={dropDisc}
            players={players}
          />

          {winner && <button onClick={nextRound}>Next Round</button>}
          <button onClick={resetGame}>Reset Game</button>
        </>
      )}
    </div>
  );
}

export default App;


function checkWin(board, row, col, player) {
  const directions = [
    [0, 1],
    [1, 0],
    [1, 1],
    [1, -1]
  ];

  return directions.some(([dr, dc]) =>
    count(board, row, col, dr, dc, player) +
    count(board, row, col, -dr, -dc, player) >= 3
  );
}

function count(board, row, col, dr, dc, player) {
  let r = row + dr;
  let c = col + dc;
  let count = 0;

  while (
    r >= 0 && r < ROWS &&
    c >= 0 && c < COLS &&
    board[r][c] === player
  ) {
    count++;
    r += dr;
    c += dc;
  }
  return count;
}
