import tkinter as tk

class StatusBar(tk.Frame):
    def __init__(self, parent):
        # modern status bar — bg2 with top border
        super().__init__(parent, bg="#1A1A1E", highlightthickness=0)
        self.state_var = tk.StringVar(value="IDLE")
        self.msg_var = tk.StringVar(value="Ready")
        self.rate_var = tk.StringVar(value="—")
        self.errors_var = tk.StringVar(value="")
        self._build()

    def _build(self):
        # top hairline
        self._line = tk.Frame(self, height=1, bg="#2A2A2E")
        self._line.pack(fill=tk.X, side=tk.TOP)

        inner = tk.Frame(self, bg="#1A1A1E")
        inner.pack(fill=tk.X, padx=12, pady=6)

        # left: state pill
        self._state_frame = tk.Frame(inner, bg="#232326", highlightthickness=1, highlightbackground="#3A3A3E")
        self._state_frame.pack(side=tk.LEFT)
        self._dot = tk.Canvas(self._state_frame, width=8, height=8, bg="#232326", highlightthickness=0)
        self._dot.pack(side=tk.LEFT, padx=(8, 4), pady=4)
        self._dot.create_oval(0, 0, 8, 8, fill="#9AA0A6", outline="", tags="dot")
        tk.Label(self._state_frame, textvariable=self.state_var, bg="#232326", fg="#ECECEC",
                 font=("Segoe UI", 8, "bold")).pack(side=tk.LEFT, padx=(0, 8))

        # center: message
        tk.Label(inner, textvariable=self.msg_var, bg="#1A1A1E", fg="#9AA0A6",
                 font=("Segoe UI", 9), anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True, padx=12)

        # right: rate pill + errors
        self._rate_lbl = tk.Label(inner, textvariable=self.rate_var, bg="#1A1A1E", fg="#9AA0A6",
                                  font=("Segoe UI", 8), anchor="e")
        self._rate_lbl.pack(side=tk.LEFT, padx=8)

        self._err_lbl = tk.Label(inner, textvariable=self.errors_var, bg="#1A1A1E", fg="#EF4444",
                                 font=("Segoe UI", 8, "bold"), anchor="e")
        self._err_lbl.pack(side=tk.LEFT, padx=(8, 0))

    def set_state(self, s: str):
        self.state_var.set(s.upper())
        # color dot by state
        try:
            col = "#10B981" if s.upper() in ("CAPTURING", "CONNECTED") else "#9AA0A6"
            if s.upper() in ("OVERFLOW", "ERROR"):
                col = "#EF4444"
            self._dot.itemconfig("dot", fill=col)
        except Exception:
            pass
        # also update background based on theme — keep dark for now

    def set_message(self, m: str):
        self.msg_var.set(m)

    def set_rate(self, r: str):
        self.rate_var.set(r)

    def set_errors(self, e: str):
        self.errors_var.set(e)
        if e:
            self._err_lbl.configure(fg="#EF4444")
