# =============================================================================
#  Gui.py  –  Graphical User Interface (Tkinter)
#
#  Responsibilities:
#    • Build and manage the 3-panel window (left settings, centre board, right info)
#    • Translate user clicks into game-logic calls
#    • Run the AI on a background thread and apply results safely on the main thread
#    • Maintain session scores across multiple games
#
#  Fixed bugs (see README for full details):
#    [FIX-1] Race condition: pressing "New Game" while the AI thread was still
#            running caused the stale thread to apply a move to the new game.
#            Solved with a `_game_id` counter — each new game gets a unique ID
#            and the AI callback is silently dropped if the ID no longer matches.
#    [FIX-2] _hover_leave() did not check ai_thinking, so hovering over a cell
#            during AI thinking would reset its background even if it was about
#            to be played, causing a brief visual glitch.
#    [FIX-3] Right-panel "Complexity" label showed O(b^d) (plain Minimax).
#            Because the code uses Alpha-Beta pruning the correct value is
#            O(b^(d/2)) in the best case.
# =============================================================================

import tkinter as tk
from tkinter import font as tkfont
import threading

from game_logic import GameLogic, HUMAN, AI, EMPTY
from Minimax import get_ai_move


# =============================================================================
# Colour palette
# All colours are defined once here so a theme change only touches this section.
# =============================================================================
C_BG          = "#1a1f2e"   # Window background (very dark blue-grey)
C_PANEL       = "#242938"   # Side-panel background
C_CARD        = "#2e3348"   # Default board-cell colour
C_CARD_HOVER  = "#3a4060"   # Board-cell colour when the mouse is over it
C_ACCENT      = "#7c9fff"   # Human player (X) – soft blue
C_ACCENT2     = "#ff8c69"   # AI player (O) – soft orange
C_WIN_HL      = "#ffd700"   # Winning cells – gold
C_TEXT_PRI    = "#e8eaf6"   # Primary text (near-white)
C_TEXT_SEC    = "#8892b0"   # Secondary text (muted blue-grey)
C_TEXT_DARK   = "#1a1f2e"   # Dark text used on light-coloured buttons
C_BTN         = "#3a4060"   # Standard button background
C_BTN_HOVER   = "#4a5278"   # Button hover background
C_DIVIDER     = "#3a4060"   # Thin horizontal divider lines

# Map player constants → their accent colour for convenient lookups
PLAYER_COLORS = {
    HUMAN: C_ACCENT,
    AI:    C_ACCENT2,
}

SYMBOL_FONT_SIZE = 38   # pt size for the X / O symbols on the board


# =============================================================================
# TicTacToeApp
# The single top-level class; one instance lives for the whole application.
# =============================================================================
class TicTacToeApp:

    # -------------------------------------------------------------------------
    # Construction
    # -------------------------------------------------------------------------
    def __init__(self, root):

        self.root = root
        self.root.title("Tic-Tac-Toe · Minimax AI")
        self.root.resizable(False, False)
        self.root.configure(bg=C_BG)

        # ── Game state ────────────────────────────────────────────────────────
        self.logic = GameLogic()        # Holds the board and win-detection logic

        self.scores = {                 # Persistent across new_game() calls
            HUMAN:  0,
            AI:     0,
            "Draw": 0,
        }

        self.difficulty   = tk.StringVar(value="Hard")  # "Easy" | "Medium" | "Hard"
        self.first_player = tk.StringVar(value=HUMAN)   # HUMAN | AI

        self.ai_thinking = False   # True while the AI background thread is active

        # [FIX-1] Each call to new_game() increments this counter.
        # The AI thread captures the value at launch time and compares it when
        # it is about to apply its move; a mismatch means a newer game started
        # in the meantime and the result is silently discarded.
        self._game_id = 0

        # ── Build UI ─────────────────────────────────────────────────────────
        self._load_fonts()
        self._build_layout()
        self._centre_window(900, 620)

        # ── First game ───────────────────────────────────────────────────────
        self.new_game()

    # =========================================================================
    # Fonts
    # All Font objects are created once and reused by every widget.
    # =========================================================================
    def _load_fonts(self):

        self.font_title     = tkfont.Font(family="Georgia",   size=20, weight="bold")
        self.font_subtitle  = tkfont.Font(family="Georgia",   size=11, slant="italic")
        self.font_symbol    = tkfont.Font(family="Georgia",   size=SYMBOL_FONT_SIZE, weight="bold")
        self.font_label     = tkfont.Font(family="Helvetica", size=11)
        self.font_label_b   = tkfont.Font(family="Helvetica", size=11, weight="bold")
        self.font_status    = tkfont.Font(family="Helvetica", size=13, weight="bold")
        self.font_score     = tkfont.Font(family="Georgia",   size=22, weight="bold")
        self.font_score_lbl = tkfont.Font(family="Helvetica", size=9)
        self.font_btn       = tkfont.Font(family="Helvetica", size=10, weight="bold")
        self.font_option    = tkfont.Font(family="Helvetica", size=10)

    # =========================================================================
    # Layout – three columns: left panel | board | right panel
    # =========================================================================
    def _build_layout(self):

        container = tk.Frame(self.root, bg=C_BG)
        container.pack(padx=20, pady=20)

        # ── Left ──────────────────────────────────────────────────────────────
        left = tk.Frame(
            container,
            bg=C_PANEL,
            width=200,
            highlightthickness=1,
            highlightbackground=C_DIVIDER,
        )
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 16))
        left.pack_propagate(False)
        self._build_left_panel(left)

        # ── Centre ────────────────────────────────────────────────────────────
        center = tk.Frame(container, bg=C_BG)
        center.pack(side=tk.LEFT)
        self._build_board(center)

        # ── Right ─────────────────────────────────────────────────────────────
        right = tk.Frame(
            container,
            bg=C_PANEL,
            width=200,
            highlightthickness=1,
            highlightbackground=C_DIVIDER,
        )
        right.pack(side=tk.LEFT, fill=tk.Y, padx=(16, 0))
        right.pack_propagate(False)
        self._build_right_panel(right)

    # =========================================================================
    # Left panel – title, scoreboard, settings, new-game button
    # =========================================================================
    def _build_left_panel(self, parent):

        pad = dict(padx=16, pady=6)

        # ── Title ─────────────────────────────────────────────────────────────
        tk.Label(parent, text="TIC-TAC-TOE",    font=self.font_title,    bg=C_PANEL, fg=C_ACCENT   ).pack(pady=(20, 2))
        tk.Label(parent, text="Minimax AI Engine", font=self.font_subtitle, bg=C_PANEL, fg=C_TEXT_SEC).pack(pady=(0, 16))

        self._divider(parent)

        # ── Scoreboard ────────────────────────────────────────────────────────
        tk.Label(parent, text="S C O R E B O A R D", font=self.font_score_lbl, bg=C_PANEL, fg=C_TEXT_SEC).pack(pady=(14, 4))

        score_frame = tk.Frame(parent, bg=C_PANEL)
        score_frame.pack()

        self._score_block(score_frame, "YOU (X)", C_ACCENT,   "score_human").pack(side=tk.LEFT, padx=6)
        self._score_block(score_frame, "DRAW",    C_TEXT_SEC,  "score_draw" ).pack(side=tk.LEFT, padx=6)
        self._score_block(score_frame, "AI (O)",  C_ACCENT2,   "score_ai"   ).pack(side=tk.LEFT, padx=6)

        self._divider(parent)

        # ── Settings ─────────────────────────────────────────────────────────
        tk.Label(parent, text="S E T T I N G S", font=self.font_score_lbl, bg=C_PANEL, fg=C_TEXT_SEC).pack(pady=(14, 8))

        # Difficulty radio buttons
        tk.Label(parent, text="Difficulty", font=self.font_label_b, bg=C_PANEL, fg=C_TEXT_PRI).pack(**pad)

        diff_frame = tk.Frame(parent, bg=C_PANEL)
        diff_frame.pack(pady=(0, 6))

        for level in ("Easy", "Medium", "Hard"):
            self._radio_btn(diff_frame, level, self.difficulty).pack(side=tk.LEFT, padx=3)

        # First-player radio buttons
        tk.Label(parent, text="First Player", font=self.font_label_b, bg=C_PANEL, fg=C_TEXT_PRI).pack(**pad)

        first_frame = tk.Frame(parent, bg=C_PANEL)
        first_frame.pack(pady=(0, 6))

        self._radio_btn(first_frame, "You", self.first_player, HUMAN).pack(side=tk.LEFT, padx=3)
        self._radio_btn(first_frame, "AI",  self.first_player, AI   ).pack(side=tk.LEFT, padx=3)

        self._divider(parent)

        # ── New-game button ───────────────────────────────────────────────────
        self.btn_restart = self._styled_btn(parent, "⟳ NEW GAME", self.new_game, C_ACCENT)
        self.btn_restart.pack(pady=20, padx=16, fill=tk.X)

        # ── Footer ────────────────────────────────────────────────────────────
        tk.Label(parent, text="Minimax · Alpha-Beta", font=self.font_score_lbl, bg=C_PANEL, fg=C_TEXT_SEC).pack(side=tk.BOTTOM, pady=10)

    # =========================================================================
    # Centre – status bar + 3×3 board
    # =========================================================================
    def _build_board(self, parent):

        # Status label (changes dynamically during play)
        self.status_var = tk.StringVar(value="")
        self.status_lbl = tk.Label(
            parent,
            textvariable=self.status_var,
            font=self.font_status,
            bg=C_BG,
            fg=C_TEXT_PRI,
            width=24,
            height=2,
        )
        self.status_lbl.pack(pady=(0, 12))

        # Board frame – thin C_DIVIDER gaps between cells act as grid lines
        board_frame = tk.Frame(parent, bg=C_DIVIDER)
        board_frame.pack()

        self.buttons = []

        for i in range(9):
            btn = tk.Button(
                board_frame,
                text="",
                font=self.font_symbol,
                width=3,
                height=1,
                bg=C_CARD,
                fg=C_TEXT_PRI,
                activebackground=C_CARD_HOVER,
                activeforeground=C_TEXT_PRI,
                bd=0,
                relief=tk.FLAT,
                cursor="hand2",
                command=lambda idx=i: self.on_cell_click(idx),
            )

            row, col = divmod(i, 3)   # Map flat index → (row, column)
            btn.grid(row=row, column=col, padx=2, pady=2, ipadx=14, ipady=14)

            btn.bind("<Enter>", lambda e, b=btn: self._hover_enter(b))
            btn.bind("<Leave>", lambda e, b=btn: self._hover_leave(b))

            self.buttons.append(btn)

    # =========================================================================
    # Right panel – algorithm info + legend
    # =========================================================================
    def _build_right_panel(self, parent):

        tk.Label(parent, text="G A M E   I N F O", font=self.font_score_lbl, bg=C_PANEL, fg=C_TEXT_SEC).pack(pady=(20, 8))

        self._divider(parent)

        # [FIX-3] Complexity corrected from O(b^d) → O(b^(d/2))
        # Plain Minimax is O(b^d).  With Alpha-Beta pruning (as implemented here)
        # the best-case complexity is O(b^(d/2)), roughly halving the search depth.
        info_lines = [
            ("Algorithm",  "Minimax + α-β"),
            ("Complexity", "O(b^(d/2))"),   # ← corrected: Alpha-Beta best case
            ("Strategy",   "Zero-sum"),
        ]

        for lbl, val in info_lines:
            row = tk.Frame(parent, bg=C_PANEL)
            row.pack(fill=tk.X, padx=16, pady=5)
            tk.Label(row, text=lbl, font=self.font_score_lbl, bg=C_PANEL, fg=C_TEXT_SEC).pack(anchor="w")
            tk.Label(row, text=val, font=self.font_label_b,   bg=C_PANEL, fg=C_TEXT_PRI).pack(anchor="w")

        self._divider(parent)

        # Legend
        tk.Label(parent, text="L E G E N D", font=self.font_score_lbl, bg=C_PANEL, fg=C_TEXT_SEC).pack(pady=(14, 8))

        for symbol, name, color in [("X", "Human", C_ACCENT), ("O", "AI", C_ACCENT2)]:
            row = tk.Frame(parent, bg=C_PANEL)
            row.pack(fill=tk.X, padx=16, pady=3)
            tk.Label(row, text=symbol,   font=self.font_label_b, bg=C_PANEL, fg=color,     width=2).pack(side=tk.LEFT)
            tk.Label(row, text=f"= {name}", font=self.font_label, bg=C_PANEL, fg=C_TEXT_PRI       ).pack(side=tk.LEFT)

    # =========================================================================
    # Widget factory helpers
    # =========================================================================
    def _divider(self, parent):
        """One-pixel horizontal rule."""
        tk.Frame(parent, bg=C_DIVIDER, height=1).pack(fill=tk.X, padx=12, pady=4)

    def _score_block(self, parent, label_text, color, attr_name):
        """
        Create a small score widget (big number + small label).
        Stores the StringVar as self.<attr_name> for later updates.
        """
        frame = tk.Frame(parent, bg=C_PANEL)
        var   = tk.StringVar(value="0")
        setattr(self, attr_name, var)

        tk.Label(frame, textvariable=var,   font=self.font_score,     bg=C_PANEL, fg=color    ).pack()
        tk.Label(frame, text=label_text,    font=self.font_score_lbl, bg=C_PANEL, fg=C_TEXT_SEC).pack()
        return frame

    def _radio_btn(self, parent, text, variable, value=None):
        """Styled radio button – value defaults to text when not specified."""
        if value is None:
            value = text
        return tk.Radiobutton(
            parent,
            text=text,
            variable=variable,
            value=value,
            font=self.font_option,
            bg=C_PANEL,
            fg=C_TEXT_PRI,
            selectcolor=C_ACCENT,
            activebackground=C_PANEL,
            activeforeground=C_ACCENT,
            bd=0,
        )

    def _styled_btn(self, parent, text, command, color):
        """Flat-style button with hover colour change."""
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            font=self.font_btn,
            bg=color,
            fg=C_TEXT_DARK,
            activebackground=C_BTN_HOVER,
            bd=0,
            cursor="hand2",
            padx=10,
            pady=8,
        )
        btn.bind("<Enter>", lambda e: btn.config(bg=C_BTN_HOVER))
        btn.bind("<Leave>", lambda e: btn.config(bg=color))
        return btn

    # =========================================================================
    # Hover effects
    # =========================================================================
    def _hover_enter(self, btn):
        """Highlight an empty cell when the cursor enters — only during human's turn."""
        if btn["text"] == EMPTY and not self.ai_thinking:
            btn.config(bg=C_CARD_HOVER)

    def _hover_leave(self, btn):
        """
        Restore an empty cell's background when the cursor leaves.

        [FIX-2] Added ai_thinking guard (matching _hover_enter).
        Without it, leaving a hovered cell during AI thinking could briefly
        re-colour a cell that was just disabled, causing a visual glitch.
        """
        if btn["text"] == EMPTY and not self.ai_thinking:
            btn.config(bg=C_CARD)

    # =========================================================================
    # Window centering
    # =========================================================================
    def _centre_window(self, width, height):
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x  = (sw - width)  // 2
        y  = (sh - height) // 2
        self.root.geometry(f"{width}x{height}+{x}+{y}")

    # =========================================================================
    # New Game
    # =========================================================================
    def new_game(self):
        """
        Reset board, scores display, and button states for a fresh game.

        [FIX-1] Increment _game_id first.  Any AI thread that was launched for
        the previous game will see a mismatched ID in _apply_ai_move() and will
        discard its result, preventing it from corrupting the new game's board.
        """
        self._game_id += 1          # Invalidate any in-flight AI thread

        self.logic.reset_board()
        self.ai_thinking = False
        self.logic.current_turn = self.first_player.get()

        for btn in self.buttons:
            btn.config(text="", bg=C_CARD, fg=C_TEXT_PRI, state=tk.NORMAL)

        self._update_status()

        if self.logic.current_turn == AI:
            self._schedule_ai_move()

    # =========================================================================
    # Human move
    # =========================================================================
    def on_cell_click(self, index):
        """
        Handle a player clicking a board cell.

        Guards:
          • Ignore click while the AI is computing.
          • Ignore click if it is not the human's turn.
          • Ignore click on an already-occupied cell.
        """
        if self.ai_thinking:
            return
        if self.logic.current_turn != HUMAN:
            return
        if self.buttons[index]["text"] != EMPTY:
            return

        # Apply the human move
        self.logic.make_move(index, HUMAN)
        self.buttons[index].config(
            text=HUMAN,
            fg=PLAYER_COLORS[HUMAN],
            state=tk.DISABLED,
            disabledforeground=PLAYER_COLORS[HUMAN],
        )

        if self._check_end_of_game():
            return

        self.logic.current_turn = AI
        self._update_status()
        self._schedule_ai_move()

    # =========================================================================
    # AI move – scheduling and application
    # =========================================================================
    def _schedule_ai_move(self):
        """
        Launch the AI computation on a background daemon thread.

        Why a background thread?
        Tkinter runs on a single thread.  If we called get_ai_move() directly
        on the main thread the entire window would freeze until the AI returned.
        Running it on a daemon thread keeps the UI responsive.  The result is
        safely handed back to the main thread via root.after(0, …).

        [FIX-1] We capture `current_game_id = self._game_id` now (before the
        thread starts) and pass it through to _apply_ai_move() via the lambda.
        """
        self.ai_thinking = True

        self.status_var.set("🤖 AI is thinking...")
        self.status_lbl.config(fg=C_ACCENT2)

        # Disable all empty cells so the human cannot click during AI's turn
        for btn in self.buttons:
            if btn["text"] == EMPTY:
                btn.config(state=tk.DISABLED)

        current_game_id = self._game_id   # [FIX-1] snapshot current game

        def ai_turn():
            import time
            time.sleep(0.7)                         # Brief pause – feels more natural

            board_copy = self.logic.board[:]        # Work on a copy; never touch the live board from a thread
            move = get_ai_move(board_copy, self.difficulty.get())

            # Schedule the UI update on the main (Tkinter) thread
            self.root.after(
                0,
                lambda: self._apply_ai_move(move, current_game_id),   # [FIX-1] pass id
            )

        threading.Thread(target=ai_turn, daemon=True).start()

    def _apply_ai_move(self, move, game_id):
        """
        Apply the AI's chosen move to the board and update the UI.

        Called from the main thread via root.after().

        [FIX-1] If game_id no longer matches self._game_id the player pressed
        "New Game" while the AI was thinking.  We reset ai_thinking and return
        immediately so the stale move is never applied to the new game.
        """
        # ── [FIX-1] Stale-move guard ─────────────────────────────────────────
        if game_id != self._game_id:
            self.ai_thinking = False    # Safety reset in case new_game() missed it
            return                      # Silently discard result from old game

        self.ai_thinking = False

        if move is None:                # Board was already full (shouldn't happen normally)
            return

        # Apply move to logic and visual button
        self.logic.make_move(move, AI)
        self.buttons[move].config(
            text=AI,
            fg=PLAYER_COLORS[AI],
            state=tk.DISABLED,
            disabledforeground=PLAYER_COLORS[AI],
        )

        # Re-enable remaining empty cells for the human's next turn
        for btn in self.buttons:
            if btn["text"] == EMPTY:
                btn.config(state=tk.NORMAL)

        if self._check_end_of_game():
            return

        self.logic.current_turn = HUMAN
        self._update_status()

    # =========================================================================
    # End-of-game detection
    # =========================================================================
    def _check_end_of_game(self):
        """
        Ask GameLogic whether the game has ended.
        If so: disable all buttons, highlight winning cells (if any),
        update the scoreboard, and show a result message.
        Returns True if the game is over, False otherwise.
        """
        result = self.logic.check_winner()

        if result is None:
            return False    # Game still in progress

        # Disable every cell – the game is over
        for btn in self.buttons:
            btn.config(state=tk.DISABLED)

        # Highlight the three winning cells in gold
        combo = self.logic.get_winning_combo()
        if combo:
            for idx in combo:
                self.buttons[idx].config(bg=C_WIN_HL, disabledforeground=C_TEXT_DARK)

        # Update persistent score counters
        self.scores[result] += 1
        self._refresh_scoreboard()

        # Show result in status bar
        if result == HUMAN:
            self.status_var.set("🎉 You Win!")
            self.status_lbl.config(fg=C_ACCENT)
        elif result == AI:
            self.status_var.set("🤖 AI Wins!")
            self.status_lbl.config(fg=C_ACCENT2)
        else:
            self.status_var.set("🤝 Draw!")
            self.status_lbl.config(fg=C_TEXT_SEC)

        return True

    # =========================================================================
    # Status bar helpers
    # =========================================================================
    def _update_status(self):
        """Reflect whose turn it currently is in the status bar."""
        if self.logic.current_turn == HUMAN:
            self.status_var.set("Your Turn — Play X")
            self.status_lbl.config(fg=C_ACCENT)
        else:
            self.status_var.set("AI Turn — Play O")
            self.status_lbl.config(fg=C_ACCENT2)

    def _refresh_scoreboard(self):
        """Push the latest session scores into the score StringVars."""
        self.score_human.set(str(self.scores[HUMAN]))
        self.score_ai.set(str(self.scores[AI]))
        self.score_draw.set(str(self.scores["Draw"]))