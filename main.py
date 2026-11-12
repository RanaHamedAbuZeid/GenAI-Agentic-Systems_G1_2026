"""
Name: Rana Hamed Abuzeid
Group :1

Calls the U.S. Department of Education's College Scorecard REST API,
parses the JSON response into University objects, and prints a bold,
colourful comparison of universities: acceptance rate, tuition,
graduation rate and graduate salaries.

Usage:
    python main.py                 # top selective universities
    python main.py "Texas"         # search universities by name
"""

import os
import sys
from dataclasses import dataclass
from typing import Optional

import requests
from dotenv import load_dotenv
from rich import box
from rich.align import Align
from rich.columns import Columns
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.text import Text

API_URL = "https://api.data.gov/ed/collegescorecard/v1/schools"
FIELDS = [
    "school.name", "school.city", "school.state", "school.school_url",
    "latest.student.size",
    "latest.admissions.admission_rate.overall",
    "latest.cost.tuition.out_of_state",
    "latest.completion.rate_suppressed.overall",
    "latest.earnings.10_yrs_after_entry.median",
]
console = Console()

PINK, CYAN, LIME, YELLOW, ORANGE, PURPLE, RED = (
    "#ff2e88", "#00f0ff", "#b6ff00", "#ffe600", "#ff8a00", "#a259ff", "#ff3b3b",
)


# ─────────────────────────────── Data model ───────────────────────────────
@dataclass
class University:
    name: str
    city: str
    state: str
    website: str
    students: Optional[int]
    acceptance: Optional[float]   # 0.0 – 1.0
    tuition: Optional[int]        # USD / year
    grad_rate: Optional[float]    # 0.0 – 1.0
    salary: Optional[int]         # median salary 10 years after entry

    @classmethod
    def from_json(cls, d: dict) -> "University":
        """Build a University from one item of the API's JSON response."""
        return cls(
            name=d.get("school.name", "Unknown"),
            city=d.get("school.city") or "",
            state=d.get("school.state") or "",
            website=d.get("school.school_url") or "",
            students=d.get("latest.student.size"),
            acceptance=d.get("latest.admissions.admission_rate.overall"),
            tuition=d.get("latest.cost.tuition.out_of_state"),
            grad_rate=d.get("latest.completion.rate_suppressed.overall"),
            salary=d.get("latest.earnings.10_yrs_after_entry.median"),
        )

    @property
    def vibe(self) -> Text:
        """A badge describing how hard it is to get in."""
        a = self.acceptance
        if a is None:
            return Text(" ? ", style="dim")
        if a < 0.10:
            return Text(" 🔥 ELITE ", style=f"bold white on {RED}")
        if a < 0.30:
            return Text(" ⭐ TOUGH ", style=f"bold black on {ORANGE}")
        if a < 0.60:
            return Text(" 👍 SOLID ", style=f"bold black on {YELLOW}")
        return Text(" 🚪 OPEN ", style=f"bold black on {LIME}")

    @property
    def value_score(self) -> float:
        """Salary earned per dollar of yearly tuition (higher = better deal)."""
        if self.salary and self.tuition:
            return self.salary / self.tuition
        return 0.0


# ─────────────────────────────── API call ─────────────────────────────────
def fetch_universities(api_key: str, search: Optional[str]) -> tuple[list[University], int]:
    params = {
        "api_key": api_key,
        "fields": ",".join(FIELDS),
        "per_page": 10,
        "latest.school.degrees_awarded.highest": 4,          # grants graduate degrees
        "latest.admissions.admission_rate.overall__range": "0.01..",
    }
    if search:
        params["school.name"] = search
        params["sort"] = "latest.student.size:desc"
    else:
        params["latest.student.size__range"] = "5000.."
        params["sort"] = "latest.admissions.admission_rate.overall:asc"

    with console.status(f"[bold {CYAN}]🎓 Scouting campuses…", spinner="dots12"):
        response = requests.get(API_URL, params=params, timeout=20)
        response.raise_for_status()
        payload = response.json()

    universities = [University.from_json(item) for item in payload["results"]]
    return universities, payload["metadata"]["total"]


# ─────────────────────────────── Helpers ──────────────────────────────────
def money(v: Optional[int]) -> str:
    return f"${v:,.0f}" if v else "—"


def pct(v: Optional[float]) -> str:
    return f"{v * 100:.0f}%" if v is not None else "—"


def bar(v: Optional[float], color: str, width: int = 10) -> Text:
    if v is None:
        return Text("—", style="dim")
    fill = max(1, round(v * width))
    return Text("█" * fill, style=color) + Text("░" * (width - fill), style="grey30") + Text(f" {pct(v)}", style=f"bold {color}")


# ─────────────────────────────── Rendering ────────────────────────────────
def banner(search: Optional[str]) -> Panel:
    title = Text.assemble(("🎓 UNI ", f"bold {PINK}"), ("SCOUT", f"bold {CYAN}"), (" 🚀", ""))
    mode = f'Search: "{search}"' if search else "Most selective universities (5,000+ students)"
    sub = Text(f"{mode}  •  Data: U.S. College Scorecard", style=f"italic {LIME}")
    return Panel(Align.center(Text.assemble(title, "\n", sub)), box=box.DOUBLE, border_style=PURPLE, padding=(1, 4))


def stat_card(label: str, value: str, note: str, color: str) -> Panel:
    body = Text.assemble((value, f"bold {color}"), "\n", (note, "dim"))
    return Panel(Align.center(body), title=f"[bold]{label}", border_style=color, box=box.HEAVY, width=28)


def render(unis: list[University], total: int, search: Optional[str]) -> None:
    console.print(banner(search))

    if not unis:
        console.print(Panel("🔍 No universities matched. Try another name!", border_style=CYAN))
        return

    with_tuition = [u for u in unis if u.tuition]
    with_salary = [u for u in unis if u.salary]
    rates = [u.acceptance for u in unis if u.acceptance is not None]

    cards = [
        stat_card("🏛️  MATCHES", f"{total:,}", f"showing top {len(unis)}", CYAN),
        stat_card("🎯 AVG ACCEPTANCE", pct(sum(rates) / len(rates)) if rates else "—", "of applicants get in", PINK),
    ]
    if with_tuition:
        cheap = min(with_tuition, key=lambda u: u.tuition)
        cards.append(stat_card("💸 CHEAPEST", money(cheap.tuition), cheap.name, LIME))
    if with_salary:
        rich_ = max(with_salary, key=lambda u: u.salary)
        cards.append(stat_card("💰 TOP SALARY", money(rich_.salary), rich_.name, YELLOW))
    console.print(Columns(cards, align="center"), justify="center")

    table = Table(
        title=f"[bold {PINK}]🏆 UNIVERSITY LEADERBOARD",
        box=box.ROUNDED, border_style=PINK, header_style=f"bold black on {CYAN}",
        row_styles=["", "on grey11"],
    )
    table.add_column("#", justify="right", style=f"bold {PURPLE}")
    table.add_column("University", style="bold white", max_width=34)
    table.add_column("Location", style=CYAN)
    table.add_column("Students", justify="right", style=PURPLE)
    table.add_column("Acceptance")
    table.add_column("Tuition/yr", justify="right", style=ORANGE)
    table.add_column("Graduation")
    table.add_column("Salary (10y)", justify="right", style=f"bold {YELLOW}")
    table.add_column("Vibe", justify="center")

    for i, u in enumerate(unis, 1):
        table.add_row(
            str(i), u.name, f"{u.city}, {u.state}",
            f"{u.students:,}" if u.students else "—",
            bar(u.acceptance, PINK),
            money(u.tuition),
            bar(u.grad_rate, LIME),
            money(u.salary),
            u.vibe,
        )
    console.print(table, justify="center")

    best = max(unis, key=lambda u: u.value_score)
    if best.value_score:
        spotlight = Text.assemble(
            ("💎 ", ""), (best.name, f"bold {PINK}"), (" is the best deal on this list!\n", ""),
            ("Tuition ", ""), (money(best.tuition), f"bold {ORANGE}"),
            (" → graduates earn ", ""), (money(best.salary), f"bold {YELLOW}"),
            (" a year — that's ", ""), (f"{best.value_score:.1f}×", f"bold {LIME}"),
            (" the yearly tuition 📈\n", ""),
            (f"🌐 {best.website}", f"underline {PURPLE}"),
        )
        console.print(Panel(spotlight, title="[bold]✨ BEST VALUE PICK", border_style=YELLOW, box=box.DOUBLE, padding=(1, 2)))
    console.print(Align.center(Text("Tuition = out-of-state  •  Salary = median, 10 years after enrolling", style="dim italic")))


def fail(message: str) -> None:
    console.print(Panel(message, title="[bold]💥 ERROR", border_style=RED, box=box.HEAVY))
    sys.exit(1)


# ─────────────────────────────── Entry point ──────────────────────────────
def main() -> None:
    load_dotenv()  # reads .env in the project folder
    api_key = os.getenv("SCORECARD_API_KEY")
    if not api_key:
        fail("SCORECARD_API_KEY is missing.\nCopy [bold].env.example[/] to [bold].env[/] and paste your free key from https://api.data.gov/signup")

    search = " ".join(sys.argv[1:]).strip() or None

    try:
        unis, total = fetch_universities(api_key, search)
    except requests.HTTPError as e:
        fail(f"API returned {e.response.status_code}. Check that your API key is valid.")
    except requests.RequestException as e:
        fail(f"Couldn't reach the API: {e}")
    except (KeyError, ValueError) as e:
        fail(f"Unexpected response format: {e}")

    render(unis, total, search)


if __name__ == "__main__":
    main()
