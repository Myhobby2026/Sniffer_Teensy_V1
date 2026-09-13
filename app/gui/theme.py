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
        import tkinter.ttk as ttk
        style = ttk.Style(root)
        # Use clam as base for customizability
        style.theme_use("clam")
        style.configure(".", background=pal["bg"], foreground=pal["fg"], fieldbackground=pal["bg2"])
        style.configure("TFrame", background=pal["bg"])
        style.configure("TLabel", background=pal["bg"], foreground=pal["fg"])
        style.configure("TButton", background=pal["bg3"], foreground=pal["fg"], bordercolor=pal["border"])
        style.map("TButton", background=[("active", pal["accent2"])])
        style.configure("TNotebook", background=pal["bg"], borderwidth=0)
        style.configure("TNotebook.Tab", background=pal["bg3"], foreground=pal["fg"], padding=[12,6])
        style.map("TNotebook.Tab", background=[("selected", pal["accent"])], foreground=[("selected","white")])
        style.configure("Treeview", background=pal["bg2"], foreground=pal["fg"], fieldbackground=pal["bg2"], bordercolor=pal["border"])
        style.configure("Treeview.Heading", background=pal["bg3"], foreground=pal["fg"])
        style.configure("TEntry", fieldbackground=pal["bg2"], foreground=pal["fg"])
        style.configure("TCombobox", fieldbackground=pal["bg2"], background=pal["bg2"], foreground=pal["fg"])
        style.configure("Horizontal.TScale", background=pal["bg"])
        root.configure(bg=pal["bg"])
    except Exception:
        pass
    return pal
