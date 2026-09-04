import random
import time
import tkinter as tk
from tkinter import messagebox, ttk


DIFFICULTIES = {
    "Beginner": (9, 9, 10),
    "Intermediate": (16, 16, 40),
    "Expert": (16, 30, 99),
}

NUMBER_COLORS = {
    1: "#2563eb",
    2: "#15803d",
    3: "#dc2626",
    4: "#7c3aed",
    5: "#b45309",
    6: "#0891b2",
    7: "#111827",
    8: "#64748b",
}
CELL_SIZE = 32


class Minesweeper:
    def __init__(self, root):
        self.root = root
        self.root.title("Minesweeper")
        self.root.configure(bg="#0f172a")
        self.root.minsize(360, 420)

        self.difficulty = tk.StringVar(value="Beginner")
        self.status = tk.StringVar(value="Clear the board without hitting a mine.")
        self.mine_count = tk.StringVar()
        self.timer_text = tk.StringVar(value="000")
        self.buttons = {}
        self.reset_game()
        self.build_interface()
        self.root.bind_all("<Escape>", self.close_game)
        self.root.bind_all("<q>", self.close_game)
        self.root.bind_all("<Q>", self.close_game)
        self.root.bind_all("<Up>", self.choose_previous_mode)
        self.root.bind_all("<Down>", self.choose_next_mode)
        self.reset_game()

    def build_interface(self):
        header = tk.Frame(self.root, bg="#0f172a", padx=18, pady=16)
        header.pack(fill="x")

        tk.Label(
            header,
            text="MINESWEEPER",
            bg="#0f172a",
            fg="#f8fafc",
            font=("TkDefaultFont", 20, "bold"),
        ).pack(anchor="w")
        tk.Label(
            header,
            textvariable=self.status,
            bg="#0f172a",
            fg="#94a3b8",
            font=("TkDefaultFont", 10),
        ).pack(anchor="w", pady=(4, 12))

        controls = tk.Frame(header, bg="#0f172a")
        controls.pack(fill="x")
        self.counter_label = self.make_counter(controls, "MINES", self.mine_count)
        self.counter_label.pack(side="left")
        self.timer_label = self.make_counter(controls, "TIME", self.timer_text)
        self.timer_label.pack(side="right")
        tk.Button(
            controls,
            text="NEW GAME",
            command=self.reset_game,
            bg="#fbbf24",
            fg="#111827",
            activebackground="#f59e0b",
            relief="flat",
            padx=12,
            pady=6,
            font=("TkDefaultFont", 9, "bold"),
            cursor="hand2",
        ).pack(side="right", padx=12)

        options = tk.Frame(self.root, bg="#1e293b", padx=18, pady=9)
        options.pack(fill="x")
        tk.Label(
            options, text="DIFFICULTY", bg="#1e293b", fg="#cbd5e1",
            font=("TkDefaultFont", 9, "bold"),
        ).pack(side="left")
        self.selector = ttk.Combobox(
            options, textvariable=self.difficulty, values=list(DIFFICULTIES),
            state="readonly", width=16,
        )
        self.selector.pack(side="right")
        self.selector.bind("<<ComboboxSelected>>", lambda _event: self.reset_game())
        self.selector.bind("<Up>", self.choose_previous_mode)
        self.selector.bind("<Down>", self.choose_next_mode)

        self.board_frame = tk.Frame(self.root, bg="#334155", padx=3, pady=3)
        self.board_frame.pack(padx=18, pady=18)

        tk.Label(
            self.root,
            text="Left click: reveal     Right click: flag",
            bg="#0f172a",
            fg="#64748b",
            font=("TkDefaultFont", 9),
        ).pack(pady=(0, 14))

    def close_game(self, _event=None):
        self.root.destroy()
        return "break"

    def choose_mode(self, step):
        modes = list(DIFFICULTIES)
        current_index = modes.index(self.difficulty.get())
        next_index = (current_index + step) % len(modes)
        self.difficulty.set(modes[next_index])
        self.selector.current(next_index)
        self.reset_game()
        return "break"

    def choose_previous_mode(self, _event=None):
        return self.choose_mode(-1)

    def choose_next_mode(self, _event=None):
        return self.choose_mode(1)

    @staticmethod
    def make_counter(parent, title, value):
        frame = tk.Frame(parent, bg="#1e293b", padx=10, pady=5)
        tk.Label(
            frame, text=title, bg="#1e293b", fg="#94a3b8",
            font=("TkDefaultFont", 8, "bold"),
        ).pack()
        tk.Label(
            frame, textvariable=value, bg="#1e293b", fg="#f8fafc",
            font=("Courier New", 16, "bold"),
        ).pack()
        return frame

    def reset_game(self):
        timer_job = getattr(self, "timer_job", None)
        if timer_job:
            self.root.after_cancel(timer_job)
        previous_rows = getattr(self, "rows", 0)
        previous_columns = getattr(self, "columns", 0)
        if hasattr(self, "board_frame"):
            for row in range(previous_rows):
                self.board_frame.grid_rowconfigure(row, minsize=0, weight=0)
            for column in range(previous_columns):
                self.board_frame.grid_columnconfigure(column, minsize=0, weight=0)
        rows, columns, mines = DIFFICULTIES[self.difficulty.get()]
        self.rows = rows
        self.columns = columns
        self.mine_total = mines
        self.mines = set()
        self.revealed = set()
        self.flags = set()
        self.started_at = None
        self.game_over = False
        self.timer_job = None
        self.buttons.clear()

        if hasattr(self, "board_frame"):
            for child in self.board_frame.winfo_children():
                child.destroy()
            for row in range(rows):
                self.board_frame.grid_rowconfigure(row, minsize=CELL_SIZE, weight=0)
            for column in range(columns):
                self.board_frame.grid_columnconfigure(column, minsize=CELL_SIZE, weight=0)

            font_size = 14 if columns <= 16 else 10
            for row in range(rows):
                for column in range(columns):
                    button = tk.Button(
                        self.board_frame,
                        text="",
                        width=1,
                        height=1,
                        padx=0,
                        pady=0,
                        bg="#cbd5e1",
                        fg="#0f172a",
                        activebackground="#e2e8f0",
                        relief="raised",
                        bd=2,
                        highlightthickness=0,
                        font=("TkDefaultFont", font_size, "bold"),
                        command=lambda r=row, c=column: self.reveal(r, c),
                    )
                    button.grid(row=row, column=column, sticky="nsew")
                    button.bind(
                        "<Button-3>",
                        lambda event, r=row, c=column: self.toggle_flag(r, c),
                    )
                    self.buttons[(row, column)] = button

        self.mine_count.set(f"{self.mine_total:03d}")
        self.timer_text.set("000")
        self.status.set("Clear the board without hitting a mine.")

    def place_mines(self, first_cell):
        safe_cells = {first_cell}
        safe_cells.update(self.neighbors(*first_cell))
        candidates = [
            (row, column)
            for row in range(self.rows)
            for column in range(self.columns)
            if (row, column) not in safe_cells
        ]
        self.mines = set(random.sample(candidates, self.mine_total))

    def neighbors(self, row, column):
        return [
            (near_row, near_column)
            for near_row in range(max(0, row - 1), min(self.rows, row + 2))
            for near_column in range(max(0, column - 1), min(self.columns, column + 2))
            if (near_row, near_column) != (row, column)
        ]

    def adjacent_mines(self, cell):
        return sum(neighbor in self.mines for neighbor in self.neighbors(*cell))

    def reveal(self, row, column):
        if self.game_over or (row, column) in self.flags or (row, column) in self.revealed:
            return
        if self.started_at is None:
            self.started_at = time.monotonic()
            self.place_mines((row, column))
            self.update_timer()

        cell = (row, column)
        if cell in self.mines:
            self.end_game(False, cell)
            return

        self.reveal_area(cell)
        self.buttons[cell].configure(relief="sunken", state="disabled", bg="#e2e8f0")
        self.update_revealed_cells()
        if len(self.revealed) == self.rows * self.columns - self.mine_total:
            self.end_game(True)

    def reveal_area(self, start):
        pending = [start]
        while pending:
            cell = pending.pop()
            if cell in self.revealed or cell in self.flags or cell in self.mines:
                continue
            self.revealed.add(cell)
            if self.adjacent_mines(cell) == 0:
                pending.extend(
                    neighbor for neighbor in self.neighbors(*cell)
                    if neighbor not in self.revealed
                )

    def update_revealed_cells(self):
        for cell in self.revealed:
            button = self.buttons[cell]
            count = self.adjacent_mines(cell)
            button.configure(
                text=str(count) if count else "",
                fg=NUMBER_COLORS.get(count, "#111827"),
                relief="sunken",
                state="disabled",
                disabledforeground=NUMBER_COLORS.get(count, "#475569"),
                bg="#e2e8f0",
            )

    def toggle_flag(self, row, column):
        if self.game_over or (row, column) in self.revealed:
            return
        cell = (row, column)
        if cell in self.flags:
            self.flags.remove(cell)
            self.buttons[cell].configure(text="", fg="#0f172a")
        elif len(self.flags) < self.mine_total:
            self.flags.add(cell)
            self.buttons[cell].configure(text="!", fg="#dc2626")
        self.mine_count.set(f"{self.mine_total - len(self.flags):03d}")

    def update_timer(self):
        if self.game_over or self.started_at is None:
            return
        elapsed = min(999, int(time.monotonic() - self.started_at))
        self.timer_text.set(f"{elapsed:03d}")
        self.timer_job = self.root.after(250, self.update_timer)

    def end_game(self, won, exploded=None):
        self.game_over = True
        if self.timer_job:
            self.root.after_cancel(self.timer_job)
        if won:
            self.flags.update(self.mines)
            self.update_revealed_cells()
            for cell in self.mines:
                self.buttons[cell].configure(text="!", fg="#16a34a")
            self.mine_count.set("000")
            self.status.set("Board cleared. Excellent work!")
            return

        for cell in self.mines:
            self.buttons[cell].configure(text="*", fg="#991b1b", bg="#fecaca")
        for cell in self.flags & self.mines:
            self.buttons[cell].configure(text="!", fg="#16a34a", bg="#dcfce7")
        for cell in self.flags - self.mines:
            self.buttons[cell].configure(text="?", fg="#b45309", bg="#fef3c7")
        if exploded is not None:
            self.buttons[exploded].configure(text="*", fg="#ffffff", bg="#dc2626")
        self.status.set("Boom. Start a new game and try again.")


def main():
    root = tk.Tk()
    Minesweeper(root)
    root.mainloop()


if __name__ == "__main__":
    main()
