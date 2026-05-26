# =============================================================================
#  game_logic.py  –  Tic-Tac-Toe Core Logic
#  Handles board state, win detection, and game rules.
#  Completely independent of the GUI so it can be tested or reused easily.
# =============================================================================

# ---------------------------------------------------------------------------
# Constants  (use names, not magic numbers/strings, throughout the project)
# ---------------------------------------------------------------------------
EMPTY = ""          # An empty cell on the board
HUMAN = "X"         # Human player marker
AI    = "O"         # AI player marker

# The three board positions that form each possible winning line
WINNING_COMBOS = [
    (0, 1, 2),   # Top    row
    (3, 4, 5),   # Middle row
    (6, 7, 8),   # Bottom row
    (0, 3, 6),   # Left   column
    (1, 4, 7),   # Centre column
    (2, 5, 8),   # Right  column
    (0, 4, 8),   # Main   diagonal  (\)
    (2, 4, 6),   # Anti   diagonal  (/)
]


# =============================================================================
# Class: GameLogic
# Encapsulates everything the game needs to know about board state and rules.
# The GUI calls these methods; it never touches the board list directly.
# =============================================================================
class GameLogic:

    def __init__(self):
        """Create a fresh game with an empty 3×3 board."""
        self.board = [EMPTY] * 9   # Flat list: index 0-8 maps to cells left→right, top→bottom
        self.current_turn = HUMAN  # Track whose turn it is

    # ------------------------------------------------------------------
    # Board helpers
    # ------------------------------------------------------------------

    def reset_board(self):
        """Wipe the board and reset the turn to HUMAN (caller can override)."""
        self.board = [EMPTY] * 9

    def make_move(self, index, player):
        """
        Place *player*'s marker at *index* if the cell is empty.
        Returns True on success, False if the cell is already taken.
        """
        if self.board[index] == EMPTY:  # Only allow moves on empty cells
            self.board[index] = player
            return True
        return False

    def get_available_moves(self):
        """Return a list of indices that still have no marker (EMPTY cells)."""
        return [i for i, cell in enumerate(self.board) if cell == EMPTY]

    def is_board_full(self):
        """True when every cell has been claimed – used to detect draws."""
        return all(cell != EMPTY for cell in self.board)

    # ------------------------------------------------------------------
    # Win / draw detection
    # ------------------------------------------------------------------

    def check_winner(self):
        """
        Scan every winning combination.
        Return the winning player constant (HUMAN or AI) if found,
        "Draw" if the board is full with no winner,
        or None if the game is still in progress.
        """
        for a, b, c in WINNING_COMBOS:
            # All three cells must be the same non-empty marker
            if self.board[a] == self.board[b] == self.board[c] != EMPTY:
                return self.board[a]          # "X" or "O"

        if self.is_board_full():
            return "Draw"                     # Board full, no winner

        return None                           # Game still ongoing

    def get_winning_combo(self):
        """
        After a winner is detected, return the exact (a, b, c) triple
        so the GUI can highlight those three cells.
        Returns None if there is no winner yet.
        """
        for a, b, c in WINNING_COMBOS:
            if self.board[a] == self.board[b] == self.board[c] != EMPTY:
                return (a, b, c)
        return None