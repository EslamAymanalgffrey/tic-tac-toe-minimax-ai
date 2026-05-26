# =============================================================================
#  minimax.py  –  AI Decision Engine
#
#  Contains the Minimax algorithm and the public get_ai_move() function.
#  The GUI calls only get_ai_move(); everything else is internal.
#
#  Minimax Summary
#  ───────────────
#  Minimax is a recursive algorithm used in two-player zero-sum games.
#  It explores every possible future game state and picks the move that:
#    • MAXIMISES the AI's score  (AI  is the "maximising" player)
#    • MINIMISES the human's score (Human is the "minimising" player)
#  Because Tic-Tac-Toe has a tiny search space (at most 9! = 362 880 nodes),
#  the algorithm can evaluate the full game tree – making Hard mode unbeatable.
# =============================================================================

import random                          # Used for Easy / Medium random choices
from game_logic import HUMAN, AI, EMPTY  # Import shared constants


# =============================================================================
# Scoring function
# Maps game outcomes to numeric values that Minimax optimises.
# =============================================================================
def _score(winner, depth):
    """
    Convert a game outcome into a Minimax score.

    Parameters
    ----------
    winner : str   – "O" (AI), "X" (HUMAN), or "Draw"
    depth  : int   – how many moves deep we are in the tree

    The depth term rewards faster wins (higher score) and punishes slower
    losses (lower negative score), making the AI aggressive when winning
    and defensive when losing.
    """
    if winner == AI:
        return 10 - depth    # AI wins: positive, prefer quicker wins
    if winner == HUMAN:
        return depth - 10    # Human wins: negative, prefer slower losses
    return 0                 # Draw: neutral


# =============================================================================
# Core Minimax algorithm  (with optional Alpha-Beta pruning)
# =============================================================================
def minimax(board, depth, is_maximising, alpha, beta):
    """
    Recursively evaluate every possible board state and return the best score.

    Parameters
    ----------
    board          : list[str]  – current board state (9-element list)
    depth          : int        – recursion depth (number of moves made so far)
    is_maximising  : bool       – True → AI's turn (maximise), False → Human's turn (minimise)
    alpha          : float      – best score the maximiser can guarantee so far
    beta           : float      – best score the minimiser can guarantee so far

    Returns
    -------
    int  – the best achievable score from this board position
    """

    # ------- Base Cases: check if the game has ended -------
    winner = _get_winner(board)      # Check the current board for a result

    if winner is not None:           # Terminal state reached
        return _score(winner, depth)

    # ------- Recursive Case -------
    available = [i for i, cell in enumerate(board) if cell == EMPTY]

    if is_maximising:
        # AI's turn → try every move and pick the one with the highest score
        best_score = float('-inf')   # Start with the worst possible score for maximiser

        for index in available:
            board[index] = AI            # Simulate AI placing its marker
            score = minimax(board, depth + 1, False, alpha, beta)  # Recurse (human's turn next)
            board[index] = EMPTY         # Undo the move (backtrack)

            best_score = max(best_score, score)   # Keep the highest score found

            # Alpha-Beta pruning: if this branch can't improve alpha, stop exploring
            alpha = max(alpha, best_score)
            if beta <= alpha:            # β cut-off: minimiser won't allow this path
                break

        return best_score

    else:
        # Human's turn → try every move and pick the one with the lowest score
        best_score = float('inf')    # Start with the worst possible score for minimiser

        for index in available:
            board[index] = HUMAN         # Simulate human placing their marker
            score = minimax(board, depth + 1, True, alpha, beta)   # Recurse (AI's turn next)
            board[index] = EMPTY         # Undo the move (backtrack)

            best_score = min(best_score, score)   # Keep the lowest score found

            # Alpha-Beta pruning: if this branch can't improve beta, stop exploring
            beta = min(beta, best_score)
            if beta <= alpha:            # α cut-off: maximiser won't allow this path
                break

        return best_score


# =============================================================================
# Internal helper: winner detection on a raw board list
# (Avoids importing the full GameLogic class inside recursive calls)
# =============================================================================
_WINNING_COMBOS = [
    (0, 1, 2), (3, 4, 5), (6, 7, 8),   # Rows
    (0, 3, 6), (1, 4, 7), (2, 5, 8),   # Columns
    (0, 4, 8), (2, 4, 6),              # Diagonals
]

def _get_winner(board):
    """
    Check *board* for a winner or draw.
    Returns AI, HUMAN, "Draw", or None (game still in progress).
    """
    for a, b, c in _WINNING_COMBOS:
        if board[a] == board[b] == board[c] != EMPTY:
            return board[a]                # A player has three in a row

    if all(cell != EMPTY for cell in board):
        return "Draw"                      # Board full, no winner

    return None                            # Still playing


# =============================================================================
# Public API: get_ai_move()
# The only function the GUI / game controller needs to call.
# =============================================================================
def get_ai_move(board, difficulty):
    """
    Choose and return the best cell index for the AI to play.

    Parameters
    ----------
    board      : list[str]   – current 9-element board
    difficulty : str         – "Easy", "Medium", or "Hard"

    Difficulty logic
    ─────────────────
    Easy   →  Fully random. The AI picks any available cell at random.
              Good for beginners; the AI makes no intelligent decisions.

    Medium →  50 % chance of a random move, 50 % chance of the optimal
              Minimax move. Provides a balanced challenge.

    Hard   →  Full Minimax on every turn. The AI is mathematically
              unbeatable; the best a human can achieve is a draw.
    """
    available = [i for i, cell in enumerate(board) if cell == EMPTY]

    if not available:
        return None     # Board is full – should not happen in normal play

    # ── Easy: always random ──────────────────────────────────────────────
    if difficulty == "Easy":
        return random.choice(available)

    # ── Medium: coin-flip between random and optimal ─────────────────────
    if difficulty == "Medium":
        if random.random() < 0.5:          # 50 % chance → random move
            return random.choice(available)
        # Otherwise fall through to Minimax below

    # ── Hard (and Medium 50 %): full Minimax ─────────────────────────────
    best_score = float('-inf')
    best_move  = None

    for index in available:
        board[index] = AI                          # Try placing AI marker
        # Evaluate this move; next turn belongs to the minimiser (human)
        score = minimax(board, 0, False, float('-inf'), float('inf'))
        board[index] = EMPTY                       # Undo the simulated move

        if score > best_score:                     # Found a better move
            best_score = score
            best_move  = index

    return best_move