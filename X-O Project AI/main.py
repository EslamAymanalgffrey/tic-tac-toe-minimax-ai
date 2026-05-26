# =============================================================================
#  main.py  –  Application Entry Point
#
#  This is the ONLY file you need to run.
#  It creates the Tkinter root window and hands control to the GUI class.
#
#  Run command:
#      python main.py
# =============================================================================

import tkinter as tk
from Gui import TicTacToeApp    # Import our custom GUI application class


def main():
    """
    Bootstrap the application:
      1. Create the root Tk window (one per application).
      2. Pass it to TicTacToeApp which builds all widgets and game logic.
      3. Start the Tkinter event loop (blocks until the window is closed).
    """
    root = tk.Tk()             # Step 1: Create the main window object
    app  = TicTacToeApp(root)  # Step 2: Build the full game UI  (app stored to prevent GC)
    root.mainloop()            # Step 3: Enter the event loop – listens for clicks, keys, etc.


# Standard Python entry-point guard:
# This block only runs when the file is executed directly (not when imported).
if __name__ == "__main__":
    main()