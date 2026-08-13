"""
ANVIQO COMMAND CENTER
Product UI V1.0
V5 Intelligence Core - Frozen

READ ONLY
PLC WRITE BLOCKED
SCADA CONTROL BLOCKED
HUMAN DECISION REQUIRED
"""

import tkinter as tk
from tkinter import ttk
from datetime import datetime


# ============================================================
# PRODUCT CORE
# ============================================================

try:
    from anviqo_product import AnviqoProduct
except Exception:
    AnviqoProduct = None


# ============================================================
# COLORS
# ============================================================

BG = "#08111F"
PANEL = "#0F1B2D"
PANEL2 = "#13243A"
BORDER = "#243B55"
TEXT = "#EAF2F8"
MUTED = "#8EA4BA"
GREEN = "#28D17C"
YELLOW = "#F5C542"
RED = "#FF5C5C"
BLUE = "#4DA3FF"
CYAN = "#37D6E8"


# ============================================================
# COMMAND CENTER
# ============================================================

class AnviqoCommandCenter:

    def __init__(self, root):

        self.root = root

        self.root.title(
            "ANVIQO | Industrial Intelligence Command Center"
        )

        self.root.geometry("1400x850")
        self.root.minsize(1100, 700)

        self.product = (
            AnviqoProduct()
            if AnviqoProduct
            else None
        )

        self.current_page = "Command Center"

        self.setup_style()
        self.build_layout()
        self.show_command_center()
        self.update_clock()

    # ========================================================
    # STYLE
    # ========================================================

    def setup_style(self):

        style = ttk.Style()

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "Treeview",
            background=PANEL,
            foreground=TEXT,
            fieldbackground=PANEL,
            rowheight=30,
            borderwidth=0
        )

        style.configure(
            "Treeview.Heading",
            background=PANEL2,
            foreground=TEXT,
            font=("Arial", 10, "bold")
        )

        style.configure(
            "TButton",
            font=("Arial", 10, "bold"),
            padding=8
        )

    # ========================================================
    # MAIN LAYOUT
    # ========================================================

    def build_layout(self):

        # HEADER
        self.header = tk.Frame(
            self.root,
            bg=BG,
            height=75
        )

        self.header.pack(
            fill="x"
        )

        self.build_header()

        # BODY
        body = tk.Frame(
            self.root,
            bg=BG
        )

        body.pack(
            fill="both",
            expand=True
        )

        # SIDEBAR
        self.sidebar = tk.Frame(
            body,
            bg=PANEL,
            width=230
        )

        self.sidebar.pack(
            side="left",
            fill="y"
        )

        self.sidebar.pack_propagate(False)

        self.build_sidebar()

        # CONTENT
        self.content = tk.Frame(
            body,
            bg=BG
        )

        self.content.pack(
            side="right",
            fill="both",
            expand=True
        )

    # ========================================================
    # HEADER
    # ========================================================

    def build_header(self):

        logo = tk.Label(
            self.header,
            text="ANVIQO",
            bg=BG,
            fg=CYAN,
            font=("Arial", 24, "bold")
        )

        logo.pack(
            side="left",
            padx=25,
            pady=18
        )

        tagline = tk.Label(
            self.header,
            text="THINK  •  PREDICT  •  PROTECT",
            bg=BG,
            fg=MUTED,
            font=("Arial", 10)
        )

        tagline.pack(
            side="left",
            padx=5
        )

        self.clock = tk.Label(
            self.header,
            bg=BG,
            fg=TEXT,
            font=("Arial", 10)
        )

        self.clock.pack(
            side="right",
            padx=25
        )

    # ========================================================
    # SIDEBAR
    # ========================================================

    def build_sidebar(self):

        title = tk.Label(
            self.sidebar,
            text="COMMAND CENTER",
            bg=PANEL,
            fg=MUTED,
            font=("Arial", 9, "bold")
        )

        title.pack(
            anchor="w",
            padx=20,
            pady=(25, 10)
        )

        items = [
            ("⌂", "Command Center"),
            ("◉", "Plant Health"),
            ("⚙", "Equipment"),
            ("⚠", "Events & Correlation"),
            ("↗", "What Changed"),
            ("◆", "Maintenance"),
            ("⇄", "Shift Intelligence"),
            ("▣", "Management"),
            ("★", "Executive / HOD"),
            ("✓", "Evidence & Learning"),
        ]

        for icon, name in items:

            button = tk.Button(
                self.sidebar,
                text=f"  {icon}   {name}",
                anchor="w",
                bg=PANEL,
                fg=TEXT,
                activebackground=PANEL2,
                activeforeground=CYAN,
                relief="flat",
                bd=0,
                font=("Arial", 10),
                padx=15,
                pady=10,
                command=lambda n=name:
                self.navigate(n)
            )

            button.pack(
                fill="x",
                padx=8
            )

        tk.Frame(
            self.sidebar,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            padx=15,
            pady=20
        )

        safety = tk.Label(
            self.sidebar,
            text=(
                "● SYSTEM SAFE\n\n"
                "READ-ONLY\n"
                "PLC WRITE  BLOCKED\n"
                "SCADA       BLOCKED\n\n"
                "HUMAN DECISION\n"
                "REQUIRED"
            ),
            justify="left",
            bg=PANEL,
            fg=GREEN,
            font=("Arial", 9, "bold"),
            padx=20
        )

        safety.pack(
            anchor="w"
        )

    # ========================================================
    # NAVIGATION
    # ========================================================

    def navigate(self, page):

        self.current_page = page

        if page == "Command Center":
            self.show_command_center()
        else:
            self.show_module_page(page)

    # ========================================================
    # CLEAR CONTENT
    # ========================================================

    def clear_content(self):

        for widget in self.content.winfo_children():
            widget.destroy()

    # ========================================================
    # COMMAND CENTER
    # ========================================================

    def show_command_center(self):

        self.clear_content()

        self.page_title(
            "Plant Intelligence Command Center",
            "Unified V5 intelligence overview"
        )

        # KPI ROW
        kpi = tk.Frame(
            self.content,
            bg=BG
        )

        kpi.pack(
            fill="x",
            padx=25,
            pady=15
        )

        self.kpi_card(
            kpi,
            "PLANT HEALTH",
            "ATTENTION",
            YELLOW
        )

        self.kpi_card(
            kpi,
            "MANAGEMENT PRIORITY",
            "P1 — URGENT",
            RED
        )

        self.kpi_card(
            kpi,
            "ACTIVE EQUIPMENT",
            "03",
            BLUE
        )

        self.kpi_card(
            kpi,
            "EVENT CHAINS",
            "02",
            CYAN
        )

        self.kpi_card(
            kpi,
            "SYSTEM CONFIDENCE",
            "88%",
            GREEN
        )

        # MAIN GRID
        grid = tk.Frame(
            self.content,
            bg=BG
        )

        grid.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=5
        )

        left = tk.Frame(
            grid,
            bg=BG
        )

        left.pack(
            side="left",
            fill="both",
            expand=True,
            padx=(0, 8)
        )

        right = tk.Frame(
            grid,
            bg=BG
        )

        right.pack(
            side="right",
            fill="both",
            expand=True,
            padx=(8, 0)
        )

        # TOP RISKS
        self.panel(
            left,
            "TOP EQUIPMENT RISKS",
            [
                "CV-101    P1 — URGENT      84.7/100",
                "CV-102    HIGH PRIORITY    71.4/100",
                "PT-201    EARLY WARNING    63.2/100",
            ],
            RED
        )

        # WHAT CHANGED
        self.panel(
            left,
            "WHAT CHANGED",
            [
                "✓ CV-101 valve position increased",
                "✓ CV-102 valve position increased",
                "✓ PT-201 pressure requires attention",
                "✓ Multiple abnormal signals detected",
            ],
            YELLOW
        )

        # EVENT CORRELATION
        self.panel(
            right,
            "EVENT / CORRELATION",
            [
                "CV-101 ↔ CV-102",
                "PROCESS_RELATED",
                "Developing event chain",
                "",
                "CV-102 ↔ PT-201",
                "PROCESS_RELATED",
                "Developing event chain",
            ],
            CYAN
        )

        # DECISION
        self.panel(
            right,
            "MANAGEMENT DECISION",
            [
                "CV-101",
                "MAINTENANCE REVIEW REQUIRED",
                "",
                "Controlled maintenance review",
                "Process condition verification",
                "",
                "Human authorization required",
            ],
            GREEN
        )

        self.bottom_safety()

    # ========================================================
    # KPI CARD
    # ========================================================

    def kpi_card(
        self,
        parent,
        title,
        value,
        accent
    ):

        card = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        card.pack(
            side="left",
            fill="both",
            expand=True,
            padx=5
        )

        tk.Label(
            card,
            text=title,
            bg=PANEL,
            fg=MUTED,
            font=("Arial", 9, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 4)
        )

        tk.Label(
            card,
            text=value,
            bg=PANEL,
            fg=accent,
            font=("Arial", 17, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(0, 12)
        )

    # ========================================================
    # PANEL
    # ========================================================

    def panel(
        self,
        parent,
        title,
        lines,
        accent
    ):

        frame = tk.Frame(
            parent,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        frame.pack(
            fill="both",
            expand=True,
            pady=6
        )

        tk.Label(
            frame,
            text=title,
            bg=PANEL,
            fg=accent,
            font=("Arial", 10, "bold")
        ).pack(
            anchor="w",
            padx=15,
            pady=(12, 8)
        )

        for line in lines:

            tk.Label(
                frame,
                text=line,
                bg=PANEL,
                fg=TEXT,
                font=("Arial", 10),
                anchor="w"
            ).pack(
                fill="x",
                padx=20,
                pady=3
            )

    # ========================================================
    # MODULE PAGE
    # ========================================================

    def show_module_page(
        self,
        page
    ):

        self.clear_content()

        descriptions = {

            "Plant Health":
                (
                    "Plant Health Intelligence",
                    "Area health, equipment health and operational condition"
                ),

            "Equipment":
                (
                    "Equipment Intelligence",
                    "Digital equipment identity, health, risk and relationships"
                ),

            "Events & Correlation":
                (
                    "Event & Correlation Intelligence",
                    "Chronological events and cross-equipment relationships"
                ),

            "What Changed":
                (
                    "What Changed?",
                    "Operational changes requiring attention"
                ),

            "Maintenance":
                (
                    "Maintenance Intelligence",
                    "Evidence-backed maintenance recommendations"
                ),

            "Shift Intelligence":
                (
                    "Shift Intelligence",
                    "Operational handover and developing conditions"
                ),

            "Management":
                (
                    "Management Intelligence",
                    "Prioritized decisions and management review"
                ),

            "Executive / HOD":
                (
                    "Executive / HOD Intelligence",
                    "Plant-level decision summary"
                ),

            "Evidence & Learning":
                (
                    "Evidence & Learning",
                    "Evidence quality, verification and confidence"
                )
        }

        title, subtitle = descriptions.get(
            page,
            (page, "ANVIQO intelligence module")
        )

        self.page_title(
            title,
            subtitle
        )

        # MAIN MODULE CARD
        frame = tk.Frame(
            self.content,
            bg=PANEL,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        frame.pack(
            fill="both",
            expand=True,
            padx=25,
            pady=20
        )

        tk.Label(
            frame,
            text=page.upper(),
            bg=PANEL,
            fg=CYAN,
            font=("Arial", 18, "bold")
        ).pack(
            anchor="w",
            padx=25,
            pady=(25, 10)
        )

        tk.Label(
            frame,
            text=subtitle,
            bg=PANEL,
            fg=MUTED,
            font=("Arial", 10)
        ).pack(
            anchor="w",
            padx=25
        )

        tk.Frame(
            frame,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            padx=25,
            pady=20
        )

        data = self.module_content(page)

        for item in data:

            row = tk.Frame(
                frame,
                bg=PANEL
            )

            row.pack(
                fill="x",
                padx=30,
                pady=6
            )

            tk.Label(
                row,
                text="✓",
                bg=PANEL,
                fg=GREEN,
                font=("Arial", 11, "bold")
            ).pack(
                side="left"
            )

            tk.Label(
                row,
                text=item,
                bg=PANEL,
                fg=TEXT,
                font=("Arial", 10),
                anchor="w"
            ).pack(
                side="left",
                padx=10
            )

        self.bottom_safety()

    # ========================================================
    # MODULE CONTENT
    # ========================================================

    def module_content(
        self,
        page
    ):

        content = {

            "Plant Health": [
                "MBF — operational attention detected",
                "Equipment risk contributes to plant condition",
                "Health evidence available",
                "Read-only plant intelligence",
            ],

            "Equipment": [
                "CV-101 — Control Valve",
                "CV-102 — Control Valve",
                "PT-201 — Pressure Transmitter",
                "Digital identity and relationship intelligence available",
            ],

            "Events & Correlation": [
                "CV-101 ↔ CV-102 — PROCESS_RELATED",
                "CV-102 ↔ PT-201 — PROCESS_RELATED",
                "Developing event chains detected",
                "Causation is NOT established",
            ],

            "What Changed": [
                "CV-101 valve position increased",
                "CV-102 valve position increased",
                "PT-201 pressure condition changed",
                "Multiple abnormal signals require review",
            ],

            "Maintenance": [
                "CV-101 — Maintenance Review Required",
                "Priority: 84.7/100",
                "Previous verified outcome: IMPROVED",
                "Human maintenance authorization required",
            ],

            "Shift Intelligence": [
                "Developing conditions available for handover",
                "Priority equipment identified",
                "Evidence-backed shift information",
                "Human review required",
            ],

            "Management": [
                "P1 — URGENT management priority",
                "CV-101 is primary contributor",
                "Controlled maintenance review recommended",
                "No automatic authorization",
            ],

            "Executive / HOD": [
                "Plant condition: ATTENTION",
                "Primary contributor: CV-101",
                "Multiple related equipment signals detected",
                "Decision support available",
            ],

            "Evidence & Learning": [
                "Evidence integration: PASS",
                "Verified maintenance experience available",
                "Historical confidence: HIGH",
                "Confidence does not authorize automatic action",
            ]
        }

        return content.get(
            page,
            ["Module ready."]
        )

    # ========================================================
    # PAGE TITLE
    # ========================================================

    def page_title(
        self,
        title,
        subtitle
    ):

        frame = tk.Frame(
            self.content,
            bg=BG
        )

        frame.pack(
            fill="x",
            padx=25,
            pady=(20, 5)
        )

        tk.Label(
            frame,
            text=title,
            bg=BG,
            fg=TEXT,
            font=("Arial", 20, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            frame,
            text=subtitle,
            bg=BG,
            fg=MUTED,
            font=("Arial", 10)
        ).pack(
            anchor="w",
            pady=(4, 0)
        )

    # ========================================================
    # SAFETY BAR
    # ========================================================

    def bottom_safety(self):

        frame = tk.Frame(
            self.content,
            bg=PANEL2,
            height=42
        )

        frame.pack(
            fill="x",
            padx=25,
            pady=(5, 15)
        )

        frame.pack_propagate(False)

        text = (
            "● READ-ONLY     "
            "● PLC WRITE BLOCKED     "
            "● SCADA CONTROL BLOCKED     "
            "● HUMAN DECISION REQUIRED"
        )

        tk.Label(
            frame,
            text=text,
            bg=PANEL2,
            fg=GREEN,
            font=("Arial", 9, "bold")
        ).pack(
            expand=True
        )

    # ========================================================
    # CLOCK
    # ========================================================

    def update_clock(self):

        self.clock.config(
            text=datetime.now().strftime(
                "%d %b %Y   %H:%M:%S"
            )
        )

        self.root.after(
            1000,
            self.update_clock
        )


# ============================================================
# MAIN
# ============================================================

def main():

    root = tk.Tk()

    AnviqoCommandCenter(
        root
    )

    root.mainloop()


if __name__ == "__main__":
    main()
