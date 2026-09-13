from __future__ import annotations

THEMES = {
    "dark": {
        "bg": "#1E1E1E",
        "bg2": "#252526",
        "bg3": "#2D2D30",
        "fg": "#D4D4D4",
        "fg2": "#9E9E9E",
        "accent": "#007ACC",
        "accent2": "#0E639C",
        "border": "#3C3C3C",
        "success": "#89D185",
        "warning": "#CCA700",
        "error": "#F44747",
        "canvas_bg": "#1E1E1E",
        "grid": "#2A2A2A",
    },
    "light": {
        "bg": "#F3F3F3",
        "bg2": "#FFFFFF",
        "bg3": "#EAEAEA",
        "fg": "#1E1E1E",
        "fg2": "#5A5A5A",
        "accent": "#007ACC",
        "accent2": "#0066AA",
        "border": "#CCCCCC",
        "success": "#2E7D32",
        "warning": "#E67E22",
        "error": "#C62828",
        "canvas_bg": "#FFFFFF",
        "grid": "#E0E0E0",
    },
    "high_contrast": {
        "bg": "#000000",
        "bg2": "#000000",
        "bg3": "#1A1A1A",
        "fg": "#FFFFFF",
        "fg2": "#FFFF00",
        "accent": "#00FFFF",
        "accent2": "#FF00FF",
        "border": "#FFFFFF",
        "success": "#00FF00",
        "warning": "#FFFF00",
        "error": "#FF0000",
        "canvas_bg": "#000000",
        "grid": "#333333",
    },
}

def apply_theme(root, name: str = "dark"):
    pal = THEMES.get(name, THEMES["dark"])
    try:
        import tkinter as tk
        import tkinter.font as tkfont
        import tkinter.ttk as ttk
        # --- Global font scaling (+2 pt for readability) ---
        # Bump the built-in Tk fonts so every widget without an explicit font grows a little.
        try:
            for fname in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkTooltipFont"):
                f = tkfont.nametofont(fname)
                sz = f.cget("size")
                # Tk reports size negative for pixel size; handle both
                if isinstance(sz, int):
                    if sz < 0:
                        f.configure(size=sz - 2)  # more negative = larger
                    else:
                        f.configure(size=sz + 2)
                # gently increase family weight for clarity
            # ttk widgets often fall back to TkDefaultFont, so this covers most of the UI
        except Exception:
            pass
        style = ttk.Style(root)
        # Use clam as base for customizability
        style.theme_use("clam")
        style.configure(".", background=pal["bg"], foreground=pal["fg"], fieldbackground=pal["bg2"], font=("Segoe UI", 10))
        style.configure("TFrame", background=pal["bg"])
        style.configure("TLabel", background=pal["bg"], foreground=pal["fg"], font=("Segoe UI", 10))
        style.configure("TButton", background=pal["bg3"], foreground=pal["fg"], bordercolor=pal["border"], font=("Segoe UI", 10))
        style.map("TButton", background=[("active", pal["accent2"])])
        style.configure("TNotebook", background=pal["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=pal["bg3"], foreground=pal["fg"], padding=[12, 7], font=("Segoe UI", 10, "bold"))
        style.map("TNotebook.Tab", background=[("selected", pal["accent"])], foreground=[("selected","white")])
        style.configure("Treeview", background=pal["bg2"], foreground=pal["fg"], fieldbackground=pal["bg2"], bordercolor=pal["border"], font=("Segoe UI", 10), rowheight=24)
        style.configure("Treeview.Heading", background=pal["bg3"], foreground=pal["fg"], font=("Segoe UI", 10, "bold"))
        style.configure("TEntry", fieldbackground=pal["bg2"], foreground=pal["fg"], font=("Segoe UI", 10))
        style.configure("TCombobox", fieldbackground=pal["bg2"], background=pal["bg2"], foreground=pal["fg"], font=("Segoe UI", 10))
        style.configure("Horizontal.TScale", background=pal["bg"])
        root.configure(bg=pal["bg"])
        # Menus already enlarged via TkMenuFont above — no extra option needed
        # (previous root.option_add("*Menu*Font", "Segoe UI 10") broke on Windows:
        #  Tcl parses "Segoe UI" as two tokens and expects integer for size)
    except Exception:
        pass
    return pal
