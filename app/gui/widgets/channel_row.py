import tkinter as tk
import tkinter.ttk as ttk

class ChannelRow(ttk.Frame):
    def __init__(self, parent, ch_id: int, label: str = "", enabled: bool = True, color: str = "#00BFFF", trigger: str = "none", on_change=None):
        super().__init__(parent)
        self.ch_id = ch_id
        self.on_change = on_change
        self.enabled_var = tk.BooleanVar(value=enabled)
        self.label_var = tk.StringVar(value=label or f"CH{ch_id}")
        self.color_var = tk.StringVar(value=color)
        self.trigger_var = tk.StringVar(value=trigger)
        self._build()

    def _build(self):
        ttk.Label(self, text=f"{self.ch_id:02d}", width=3).pack(side=tk.LEFT, padx=2)
        ttk.Checkbutton(self, variable=self.enabled_var, command=self._notify).pack(side=tk.LEFT)
        e = ttk.Entry(self, textvariable=self.label_var, width=14)
        e.pack(side=tk.LEFT, padx=4)
        e.bind("<FocusOut>", lambda _e: self._notify())
        ttk.Label(self, text="●", foreground=self.color_var.get()).pack(side=tk.LEFT, padx=2)
        cb = ttk.Combobox(self, textvariable=self.trigger_var, values=["none","rising","falling","both"], width=8, state="readonly")
        cb.pack(side=tk.LEFT, padx=4)
        cb.bind("<<ComboboxSelected>>", lambda _e: self._notify())
        # color button
        btn = tk.Button(self, bg=self.color_var.get(), width=2, height=1, relief=tk.FLAT, command=self._pick_color)
        btn.pack(side=tk.LEFT, padx=4)

    def _pick_color(self):
        from tkinter import colorchooser
        c = colorchooser.askcolor(color=self.color_var.get())[1]
        if c:
            self.color_var.set(c)
            for child in self.winfo_children():
                if isinstance(child, tk.Button):
                    child.configure(bg=c)
            self._notify()

    def _notify(self):
        if self.on_change:
            self.on_change(self)

    def get_config(self):
        return {
            "id": self.ch_id,
            "label": self.label_var.get(),
            "enabled": bool(self.enabled_var.get()),
            "color": self.color_var.get(),
            "trigger": self.trigger_var.get(),
        }
