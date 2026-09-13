from __future__ import annotations

# Modern 2025-era palette — inspired by Linear / Saleae Logic 2 / VSCode 2024
# Dark is default. Light is clean, high-contrast is accessible.

THEMES = {
    "dark": {
        # surfaces — layered depth (z0 → z4)
        "bg": "#0E0E10",          # window
        "bg2": "#1A1A1E",         # card / panel
        "bg3": "#232326",         # elevated (toolbar, inputs)
        "bg4": "#2C2C30",         # hover / active
        "bg5": "#34343A",         # pressed / border-light
        # text
        "fg": "#ECECEC",
        "fg2": "#9AA0A6",
        "fg3": "#6B7280",
        # accent — modern indigo/blue
        "accent": "#5B7FFF",
        "accent2": "#4A66E8",
        "accent_hover": "#6C8CFF",
        "accent_text": "#FFFFFF",
        # semantic
        "border": "#2A2A2E",
        "border_light": "#3A3A3E",
        "success": "#10B981",
        "warning": "#F59E0B",
        "error": "#EF4444",
        # specific
        "sidebar_bg": "#111113",
        "sidebar_hover": "#1E1E22",
        "sidebar_active": "#5B7FFF",
        "card_bg": "#1C1C1F",
        "card_border": "#2A2A2E",
        "input_bg": "#232326",
        "canvas_bg": "#0F0F12",
        "grid": "#1E1E22",
        "grid_strong": "#2A2A2E",
        "shadow": "#000000",
    },
    "light": {
        "bg": "#F8F9FA",
        "bg2": "#FFFFFF",
        "bg3": "#EFF2F5",
        "bg4": "#E6E8EB",
        "bg5": "#DDE1E6",
        "fg": "#0F172A",
        "fg2": "#64748B",
        "fg3": "#94A3B8",
        "accent": "#0A84FF",
        "accent2": "#0066CC",
        "accent_hover": "#1A90FF",
        "accent_text": "#FFFFFF",
        "border": "#E2E8F0",
        "border_light": "#CBD5E1",
        "success": "#059669",
        "warning": "#D97706",
        "error": "#DC2626",
        "sidebar_bg": "#FFFFFF",
        "sidebar_hover": "#F1F5F9",
        "sidebar_active": "#0A84FF",
        "card_bg": "#FFFFFF",
        "card_border": "#E2E8F0",
        "input_bg": "#FFFFFF",
        "canvas_bg": "#FFFFFF",
        "grid": "#F1F5F9",
        "grid_strong": "#E2E8F0",
        "shadow": "#000000",
    },
    "high_contrast": {
        "bg": "#000000",
        "bg2": "#0A0A0A",
        "bg3": "#1A1A1A",
        "bg4": "#2A2A2A",
        "bg5": "#3A3A3A",
        "fg": "#FFFFFF",
        "fg2": "#FFFF00",
        "fg3": "#AAAAAA",
        "accent": "#00FFFF",
        "accent2": "#00CCCC",
        "accent_hover": "#33FFFF",
        "accent_text": "#000000",
        "border": "#FFFFFF",
        "border_light": "#FFFFFF",
        "success": "#00FF00",
        "warning": "#FFFF00",
        "error": "#FF0000",
        "sidebar_bg": "#000000",
        "sidebar_hover": "#1A1A1A",
        "sidebar_active": "#00FFFF",
        "card_bg": "#0A0A0A",
        "card_border": "#FFFFFF",
        "input_bg": "#000000",
        "canvas_bg": "#000000",
        "grid": "#333333",
        "grid_strong": "#555555",
        "shadow": "#000000",
    },
}

# Preferred font stack — Windows 11 Variable first, then fallbacks
FONT_FAMILY = "Segoe UI Variable"
FALLBACK_FAMILY = "Segoe UI"


def _resolve_font_family(root) -> str:
    """Pick best available family."""
    try:
        import tkinter.font as tkfont
        families = set(tkfont.families(root))
        for name in (FONT_FAMILY, "Inter", "Segoe UI", "Helvetica", "Arial"):
            if name in families:
                return name
    except Exception:
        pass
    return FALLBACK_FAMILY


def apply_theme(root, name: str = "dark"):
    pal = THEMES.get(name, THEMES["dark"])
    try:
        import tkinter as tk
        import tkinter.font as tkfont
        import tkinter.ttk as ttk

        fam = _resolve_font_family(root)

        # --- Global font scaling (+2pt modern readability) ---
        # Bump built-ins so every widget without explicit font grows.
        try:
            for fname in ("TkDefaultFont", "TkTextFont", "TkHeadingFont", "TkMenuFont", "TkTooltipFont", "TkCaptionFont", "TkSmallCaptionFont", "TkIconFont"):
                try:
                    f = tkfont.nametofont(fname)
                except Exception:
                    continue
                # force modern family + size
                try:
                    cur = f.actual()
                    sz = cur.get("size", 9)
                    fam_cur = cur.get("family", fam)
                    if fam_cur in ("TkDefaultFont", "MS Shell Dlg 2"):
                        fam_cur = fam
                    # increase 1-2pt
                    if isinstance(sz, int):
                        new_sz = sz + 1 if sz > 0 else sz - 1
                        if sz < 0:
                            new_sz = sz - 1
                        else:
                            new_sz = sz + 1
                        # set to 10pt base for modern
                        if abs(new_sz) < 10:
                            new_sz = 10 if new_sz > 0 else -13
                    else:
                        new_sz = 10
                    f.configure(family=fam, size=new_sz)
                except Exception:
                    pass
        except Exception:
            pass

        style = ttk.Style(root)
        # clam is most customizable
        try:
            style.theme_use("clam")
        except Exception:
            pass

        # --- Base ---
        style.configure(".", background=pal["bg"], foreground=pal["fg"],
                        fieldbackground=pal["input_bg"], bordercolor=pal["border"],
                        lightcolor=pal["border"], darkcolor=pal["border"],
                        font=(fam, 10), focuscolor=pal["accent"])

        # --- Frames ---
        style.configure("TFrame", background=pal["bg"])
        style.configure("Card.TFrame", background=pal["card_bg"], relief="flat", borderwidth=1)
        style.configure("Sidebar.TFrame", background=pal["sidebar_bg"])
        style.configure("Toolbar.TFrame", background=pal["bg2"], relief="flat")
        style.configure("Header.TFrame", background=pal["bg2"])

        # --- Labels ---
        style.configure("TLabel", background=pal["bg"], foreground=pal["fg"], font=(fam, 10))
        style.configure("Header.TLabel", background=pal["bg2"], foreground=pal["fg"], font=(fam, 13, "bold"))
        style.configure("Subheader.TLabel", background=pal["bg"], foreground=pal["fg2"], font=(fam, 10))
        style.configure("Muted.TLabel", background=pal["bg"], foreground=pal["fg2"], font=(fam, 9))
        style.configure("Title.TLabel", background=pal["bg"], foreground=pal["fg"], font=(fam, 18, "bold"))
        style.configure("CardTitle.TLabel", background=pal["card_bg"], foreground=pal["fg"], font=(fam, 10, "bold"))
        style.configure("CardValue.TLabel", background=pal["card_bg"], foreground=pal["fg"], font=(fam, 13, "bold"))
        style.configure("Sidebar.TLabel", background=pal["sidebar_bg"], foreground=pal["fg2"], font=(fam, 9, "bold"))
        style.configure("Status.TLabel", background=pal["bg2"], foreground=pal["fg2"], font=(fam, 9))

        # --- Buttons ---
        # Normal
        style.configure("TButton",
                        background=pal["bg3"], foreground=pal["fg"],
                        borderwidth=0, focusthickness=0, focuscolor=pal["accent"],
                        relief="flat", padding=(14, 7), font=(fam, 10), anchor="center")
        style.map("TButton",
                  background=[("active", pal["bg4"]), ("pressed", pal["bg5"]), ("disabled", pal["bg2"])],
                  foreground=[("disabled", pal["fg3"])],
                  relief=[("pressed", "flat")])

        # Accent (primary)
        style.configure("Accent.TButton",
                        background=pal["accent"], foreground=pal["accent_text"],
                        borderwidth=0, padding=(16, 8), font=(fam, 10, "bold"))
        style.map("Accent.TButton",
                  background=[("active", pal["accent_hover"]), ("pressed", pal["accent2"]), ("disabled", pal["bg3"])],
                  foreground=[("disabled", pal["fg3"])])

        # Ghost / subtle
        style.configure("Ghost.TButton",
                        background=pal["bg"], foreground=pal["fg2"],
                        borderwidth=1, relief="flat", padding=(12, 6), font=(fam, 10))
        style.map("Ghost.TButton",
                  background=[("active", pal["bg3"])],
                  foreground=[("active", pal["fg"])],
                  bordercolor=[("active", pal["border_light"])])

        # Sidebar navigation buttons (flat, left-aligned, with left accent bar)
        style.configure("Sidebar.TButton",
                        background=pal["sidebar_bg"], foreground=pal["fg2"],
                        borderwidth=0, padding=(12, 9), font=(fam, 10), anchor="w", relief="flat")
        style.map("Sidebar.TButton",
                  background=[("active", pal["sidebar_hover"])],
                  foreground=[("active", pal["fg"])])

        style.configure("SidebarActive.TButton",
                        background=pal["bg3"], foreground=pal["fg"],
                        borderwidth=0, padding=(12, 9), font=(fam, 10, "bold"), anchor="w")
        # active state will be handled via manual bg change + left indicator

        # --- Entries / Combobox ---
        style.configure("TEntry",
                        fieldbackground=pal["input_bg"], background=pal["input_bg"],
                        foreground=pal["fg"], insertcolor=pal["fg"],
                        bordercolor=pal["border"], lightcolor=pal["border"], darkcolor=pal["border"],
                        borderwidth=1, relief="flat", padding=6, font=(fam, 10))
        style.map("TEntry",
                  fieldbackground=[("focus", pal["bg3"])],
                  bordercolor=[("focus", pal["accent"])],
                  lightcolor=[("focus", pal["accent"])])

        style.configure("TCombobox",
                        fieldbackground=pal["input_bg"], background=pal["input_bg"],
                        foreground=pal["fg"], arrowcolor=pal["fg2"],
                        selectbackground=pal["accent"], selectforeground="white",
                        bordercolor=pal["border"], lightcolor=pal["border"],
                        padding=6, font=(fam, 10))
        style.map("TCombobox",
                  fieldbackground=[("readonly", pal["input_bg"])],
                  background=[("readonly", pal["input_bg"])],
                  bordercolor=[("focus", pal["accent"])])

        # --- Checkbutton / Radio ---
        style.configure("TCheckbutton",
                        background=pal["bg"], foreground=pal["fg"],
                        indicatorbackground=pal["bg3"], indicatorforeground=pal["fg"],
                        font=(fam, 10), padding=4, focuscolor=pal["accent"])
        style.map("TCheckbutton",
                  background=[("active", pal["bg"])],
                  indicatorbackground=[("selected", pal["accent"])],
                  indicatorforeground=[("selected", "white")])

        # --- Notebook (top tabs) ---
        style.configure("TNotebook", background=pal["bg"], borderwidth=0, tabmargins=[0, 6, 0, 0])
        style.configure("TNotebook.Tab",
                        background=pal["bg"], foreground=pal["fg2"],
                        padding=[16, 8], font=(fam, 10), borderwidth=0, focuscolor=pal["bg"])
        style.map("TNotebook.Tab",
                  background=[("selected", pal["bg2"]), ("active", pal["bg3"])],
                  foreground=[("selected", pal["fg"]), ("active", pal["fg"])],
                  padding=[("selected", [16, 8])])
        style.layout("TNotebook.Tab", [
            ("Notebook.tab", {"sticky": "nswe", "children": [
                ("Notebook.padding", {"side": "top", "sticky": "nswe", "children": [
                    ("Notebook.label", {"side": "top", "sticky": ""})
                ]})
            ]})
        ])

        # --- Progressbar ---
        style.configure("TProgressbar",
                        background=pal["accent"], troughcolor=pal["bg3"],
                        bordercolor=pal["bg3"], lightcolor=pal["accent"], darkcolor=pal["accent"],
                        thickness=6, borderwidth=0, relief="flat")
        style.configure("Accent.Horizontal.TProgressbar", background=pal["accent"])

        # --- Scale ---
        style.configure("Horizontal.TScale", background=pal["bg"], troughcolor=pal["bg3"], sliderrelief="flat", sliderlength=18)

        # --- Separator ---
        style.configure("TSeparator", background=pal["border"])

        # --- Scrollbar (thin, modern) ---
        style.configure("Vertical.TScrollbar",
                        background=pal["bg"], troughcolor=pal["bg"],
                        bordercolor=pal["bg"], arrowcolor=pal["fg2"],
                        gripcount=0, relief="flat", width=10)
        style.configure("Horizontal.TScrollbar",
                        background=pal["bg"], troughcolor=pal["bg"],
                        bordercolor=pal["bg"], arrowcolor=pal["fg2"],
                        width=10)
        style.map("Vertical.TScrollbar", background=[("active", pal["bg4"])])
        style.map("Horizontal.TScrollbar", background=[("active", pal["bg4"])])

        # --- Treeview (modern table) ---
        style.configure("Treeview",
                        background=pal["card_bg"], foreground=pal["fg"],
                        fieldbackground=pal["card_bg"], bordercolor=pal["border"],
                        font=(fam, 10), rowheight=28, borderwidth=0, relief="flat")
        style.map("Treeview",
                  background=[("selected", pal["accent"])],
                  foreground=[("selected", "white")])
        style.configure("Treeview.Heading",
                        background=pal["bg3"], foreground=pal["fg2"],
                        font=(fam, 9, "bold"), relief="flat", borderwidth=0, padding=8)
        style.map("Treeview.Heading",
                  background=[("active", pal["bg4"])])
        style.layout("Treeview", [
            ("Treeview.treearea", {"sticky": "nswe"})
        ])

        # --- Labelframe (card-like) ---
        style.configure("TLabelframe",
                        background=pal["bg"], bordercolor=pal["border"],
                        relief="flat", borderwidth=1, padding=10)
        style.configure("TLabelframe.Label",
                        background=pal["bg"], foreground=pal["fg2"],
                        font=(fam, 9, "bold"))
        style.configure("Card.TLabelframe",
                        background=pal["card_bg"], bordercolor=pal["card_border"],
                        relief="flat", borderwidth=1, padding=12)
        style.configure("Card.TLabelframe.Label",
                        background=pal["card_bg"], foreground=pal["fg"],
                        font=(fam, 9, "bold"))

        # --- Panedwindow ---
        style.configure("TPanedwindow", background=pal["bg"])
        style.configure("Sash", background=pal["border"], sashthickness=1, handlepad=20, handlesize=40)

        # Root
        root.configure(bg=pal["bg"])
        # ttk::style theme_use can reset some; ensure bg again
        try:
            root.option_clear()
        except Exception:
            pass

    except Exception as e:
        # Never crash app due to theme — fallback
        try:
            import logging
            logging.getLogger("gui.theme").warning(f"Theme apply failed: {e}")
        except Exception:
            pass
    return pal
