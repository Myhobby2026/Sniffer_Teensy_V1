import tkinter as tk
import tkinter.ttk as ttk

class StatusBar(ttk.Frame):
    def __init__(self, parent):
        super().__init__(parent)
        self.state_var = tk.StringVar(value="IDLE")
        self.msg_var = tk.StringVar(value="Ready")
        self.rate_var = tk.StringVar(value="—")
        self.errors_var = tk.StringVar(value="")
        self._build()

    def _build(self):
        inner = ttk.Frame(self)
        inner.pack(fill=tk.X, padx=6, pady=2)
        ttk.Label(inner, textvariable=self.state_var, width=14, anchor="w").pack(side=tk.LEFT)
        ttk.Separator(inner, orient=tk.VERTICAL).pack(side=tk.LEFT, fill=tk.Y, padx=6)
        ttk.Label(inner, textvariable=self.msg_var, anchor="w").pack(side=tk.LEFT, fill=tk.X, expand=True)
        ttk.Label(inner, textvariable=self.rate_var, width=18, anchor="e").pack(side=tk.LEFT, padx=8)
        ttk.Label(inner, textvariable=self.errors_var, width=22, anchor="e", foreground="#F44747").pack(side=tk.LEFT)

    def set_state(self, s: str):
        self.state_var.set(s)

    def set_message(self, m: str):
        self.msg_var.set(m)

    def set_rate(self, r: str):
        self.rate_var.set(r)

    def set_errors(self, e: str):
        self.errors_var.set(e)
