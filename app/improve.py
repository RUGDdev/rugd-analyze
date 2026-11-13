"""Feasibility improvement scenarios for the startup cost build.

Scenarios call the existing `project_startup` calculation with changed inputs. They
never run Analyze, never write a result, and never touch a flag, a score, human
review, or investor readiness. A projection that looks better is a projection from
the customer's assumptions. It is not an approval.

Every changed input is listed as needing the customer's verification.
"""

from __future__ import annotations

import math
from typing import Any

from app import display
from app.inputs import field_state
from engine.startup_projection import (
    DEFAULT_AMORTIZATION_YEARS,
    DEFAULT_ANNUAL_INTEREST_RATE,
    DEFAULT_CONTINGENCY_PCT,
    DEFAULT_DEBT_SHARE,
    DEFAULT_DOWNSIDE_MULTIPLIER,
    project_startup,
)
from scoring.rules import DEFAULT_DOWNSIDE_DSCR_MINIMUM, LENDER_DOWNSIDE_DSCR_MINIMUM

NOT_APPROVED = (
    "A scenario is a what-if projection from your own assumptions. It is not approved, it does not change the official "
    "result, scoring, or human review, and it does not supply the evidence a serious concern asks for."
)

REQUIRED = (
    "construction_cost",
    "seats",
    "average_ticket",
    "weekday_occupancy",
    "weekend_occupancy",
    "operating_days",
    "contribution_margin",
)
OPTIONAL_DEFAULTS: dict[str, float] = {
    "equipment": 0.0,
    "soft_costs": 0.0,
    "preopening_working_capital": 0.0,
    "contingency_pct": DEFAULT_CONTINGENCY_PCT,
    "debt_share": DEFAULT_DEBT_SHARE,
    "annual_interest_rate": DEFAULT_ANNUAL_INTEREST_RATE,
    "amortization_years": float(DEFAULT_AMORTIZATION_YEARS),
    "annual_fixed_costs": 0.0,
    "downside_multiplier": DEFAULT_DOWNSIDE_MULTIPLIER,
}
FIELDS = REQUIRED + tuple(OPTIONAL_DEFAULTS)
APPLICABLE = FIELDS + ("available_cash",)
LABELS = {
    "construction_cost": "Construction cost",
    "equipment": "Equipment",
    "soft_costs": "Soft costs",
    "preopening_working_capital": "Pre-opening working capital",
    "contingency_pct": "Contingency",
    "debt_share": "Debt share",
    "annual_interest_rate": "Interest rate",
    "amortization_years": "Amortization years",
    "seats": "Seats",
    "average_ticket": "Average ticket",
    "weekday_occupancy": "Weekday occupancy",
    "weekend_occupancy": "Weekend occupancy",
    "operating_days": "Operating days",
    "annual_fixed_costs": "Annual fixed costs",
    "contribution_margin": "Contribution margin",
    "downside_multiplier": "Downside multiplier",
    "available_cash": "Cash you can put in",
}
VERIFY = {
    "construction_cost": "A written contractor bid for the changed scope.",
    "equipment": "Written vendor quotes for the changed equipment list.",
    "soft_costs": "Fee proposals from the designer, permit office, and attorney.",
    "preopening_working_capital": "A cash plan for the weeks before opening.",
    "contingency_pct": "What the contractor's bid already carries.",
    "debt_share": "A lender's written terms.",
    "annual_interest_rate": "A lender's term sheet.",
    "amortization_years": "A lender's term sheet.",
    "seats": "A floor plan that meets code for the changed seat count.",
    "average_ticket": "Your menu prices and what nearby competitors charge.",
    "weekday_occupancy": "Sales or reservations from a comparable place, or a documented plan.",
    "weekend_occupancy": "Sales or reservations from a comparable place, or a documented plan.",
    "operating_days": "Your lease, staffing plan, and hours.",
    "annual_fixed_costs": "Quotes for rent, insurance, utilities, and salaried staff.",
    "contribution_margin": "Recipe costing, labor schedule, and fee statements.",
    "downside_multiplier": "Your own downside view of demand.",
    "available_cash": "Bank statements or documented commitments for the cash.",
}
_WHOLE = {"seats", "amortization_years"}
_SHARES = {
    "contingency_pct",
    "debt_share",
    "annual_interest_rate",
    "weekday_occupancy",
    "weekend_occupancy",
    "contribution_margin",
}


def _num(value: Any) -> float | None:
    text = str(value if value is not None else "").strip().replace(",", "").replace("$", "")
    if not text:
        return None
    try:
        number = float(text)
    except ValueError:
        return None
    return number if math.isfinite(number) else None


def entered(profile: dict[str, Any], key: str) -> float | None:
    if field_state(profile.get(key)) not in {"entered", "zero"}:
        return None
    return _num(profile.get(key))


def is_placeholder(profile: dict[str, Any], key: str) -> bool:
    """True when an optional line is blank or still equals the engine's coded placeholder. New drafts start there."""
    number = entered(profile, key)
    return key in OPTIONAL_DEFAULTS and (number is None or abs(number - OPTIONAL_DEFAULTS[key]) < 1e-12)


def base_inputs(profile: dict[str, Any]) -> dict[str, Any]:
    """The working inputs for the startup build. A blank optional line uses the engine's coded default and says so."""
    values: dict[str, float] = {}
    absent: list[str] = []
    placeholders: list[str] = []
    for key in REQUIRED:
        number = entered(profile, key)
        if number is None:
            absent.append(key)
        else:
            values[key] = number
    for key, default in OPTIONAL_DEFAULTS.items():
        number = entered(profile, key)
        values[key] = default if number is None else number
        if is_placeholder(profile, key):
            placeholders.append(key)
    return {
        "inputs": values,
        "missing": absent,
        "placeholders": placeholders,
        "cash": entered(profile, "available_cash"),
    }


def evaluate(inputs: dict[str, float]) -> tuple[dict[str, Any] | None, str]:
    """Run the existing projection. Returns (metrics, "") or (None, reason)."""
    try:
        record = project_startup(
            inputs["construction_cost"],
            inputs["seats"],
            inputs["average_ticket"],
            inputs["weekday_occupancy"],
            inputs["weekend_occupancy"],
            inputs["operating_days"],
            inputs["contribution_margin"],
            equipment=inputs["equipment"],
            soft_costs=inputs["soft_costs"],
            preopening_working_capital=inputs["preopening_working_capital"],
            contingency_pct=inputs["contingency_pct"],
            debt_share=inputs["debt_share"],
            annual_interest_rate=inputs["annual_interest_rate"],
            amortization_years=int(inputs["amortization_years"]),
            annual_fixed_costs=inputs["annual_fixed_costs"],
            downside_multiplier=inputs["downside_multiplier"],
        ).to_dict()
    except (ValueError, KeyError) as exc:
        return None, str(exc)
    uses = record["sources_and_uses"]["uses"]
    sources = record["sources_and_uses"]["sources"]
    base = record["views"]["base"]
    down = record["views"]["downside"]
    revenue = base["revenue"]
    break_even = record["views"]["break_even"]["revenue"]
    return (
        {
            "total_project_cost": uses["total_project_cost"]["amount"],
            "contingency": uses["contingency"]["amount"],
            "debt": sources["debt"]["amount"],
            "equity": sources["equity"]["amount"],
            "annual_debt_service": sources["annual_debt_service"],
            "monthly_debt_service": sources["monthly_debt_service"],
            "base_revenue": revenue,
            "base_cash_flow": base["cash_flow_before_debt_service"],
            "base_dscr": base["dscr"],
            "downside_revenue": down["revenue"],
            "downside_cash_flow": down["cash_flow_before_debt_service"],
            "downside_dscr": down["dscr"],
            "break_even_revenue": break_even,
            "revenue_to_break_even": None if not break_even else round(revenue / break_even, 3),
        },
        "",
    )


def debt_capacity(cash_flow: float, inputs: dict[str, float], target_dscr: float) -> float:
    """The most debt a cash flow can carry at a target coverage, using the same level-payment method."""
    if cash_flow <= 0 or target_dscr <= 0:
        return 0.0
    monthly = math.floor(cash_flow / target_dscr / 12 * 100) / 100
    months = int(inputs["amortization_years"]) * 12
    rate = inputs["annual_interest_rate"] / 12
    if rate == 0:
        return round(monthly * months, 2)
    return round(monthly * (1 - (1 + rate) ** (-months)) / rate, 2)


def gap(inputs: dict[str, float], metrics: dict[str, Any], cash: float | None, target: float) -> dict[str, Any]:
    """Funding and cash-flow gaps. Each line names what it is based on."""
    total = metrics["total_project_cost"]
    result: dict[str, Any] = {"target": target}
    for case in ("base", "downside"):
        flow = metrics[f"{case}_cash_flow"]
        service = metrics["annual_debt_service"]
        capacity = debt_capacity(flow, inputs, target)
        needed = round(max(0.0, total - capacity), 2)
        result[case] = {
            "cash_flow": flow,
            "annual_shortfall": round(max(0.0, service * target - flow), 2),
            "debt_capacity": capacity,
            "owner_funding_needed": needed,
            "gap_vs_cash": None if cash is None else round(max(0.0, needed - cash), 2),
        }
    revenue = metrics["base_revenue"]
    break_even = metrics["break_even_revenue"]
    result["revenue_gap"] = None if break_even is None else round(max(0.0, break_even - revenue), 2)
    result["meets_target"] = {
        case: (metrics[f"{case}_dscr"] is not None and metrics[f"{case}_dscr"] >= target - 1e-9)
        or metrics["annual_debt_service"] == 0
        for case in ("base", "downside")
    }
    return result


def apply_overrides(
    base: dict[str, float],
    overrides: dict[str, float],
    *,
    cash: float | None,
    scale_with_size: bool,
    derive_debt_from_cash: bool,
) -> tuple[dict[str, float], list[str], list[dict[str, Any]]]:
    """Scenario inputs plus the dependent inputs that follow from supported relationships."""
    inputs = dict(base)
    changed: list[str] = []
    dependent: list[dict[str, Any]] = []
    for key, value in overrides.items():
        if key in inputs and inputs[key] != value:
            inputs[key] = value
            changed.append(key)
    if scale_with_size and "seats" in changed and base["seats"] > 0:
        ratio = inputs["seats"] / base["seats"]
        for key in ("construction_cost", "equipment", "soft_costs"):
            if key in overrides or base[key] <= 0:
                continue
            scaled = round(base[key] * ratio, 2)
            inputs[key] = scaled
            dependent.append(
                {
                    "field": key,
                    "from": base[key],
                    "to": scaled,
                    "relationship": f"scaled with seats ({ratio:.2f}×). Assumes the same cost per seat.",
                }
            )
    if derive_debt_from_cash and cash is not None and "debt_share" not in overrides:
        subtotal = (
            inputs["construction_cost"]
            + inputs["equipment"]
            + inputs["soft_costs"]
            + inputs["preopening_working_capital"]
        )
        total = subtotal * (1 + inputs["contingency_pct"])
        if total > 0:
            share = round(min(1.0, max(0.0, 1 - cash / total)), 4)
            if share != inputs["debt_share"]:
                dependent.append(
                    {
                        "field": "debt_share",
                        "from": inputs["debt_share"],
                        "to": share,
                        "relationship": "your cash covers part of the total project cost. The rest is borrowed.",
                    }
                )
                inputs["debt_share"] = share
    return inputs, changed, dependent


def _solve(
    base: dict[str, float],
    key: str,
    low: float,
    high: float,
    target: float,
    *,
    increasing: bool,
) -> float | None:
    """Smallest (or largest) value of one input that reaches the downside coverage target."""

    def meets(value: float) -> bool:
        trial = dict(base)
        trial[key] = value
        metrics, _error = evaluate(trial)
        if metrics is None:
            return False
        dscr = metrics["downside_dscr"]
        return metrics["annual_debt_service"] == 0 or (dscr is not None and dscr >= target - 1e-9)

    if increasing:
        if meets(low):
            return low
        if not meets(high):
            return None
        lo, hi = low, high
        for _ in range(60):
            mid = (lo + hi) / 2
            if meets(mid):
                hi = mid
            else:
                lo = mid
        return hi
    if meets(high):
        return high
    if not meets(low):
        return None
    lo, hi = low, high
    for _ in range(60):
        mid = (lo + hi) / 2
        if meets(mid):
            lo = mid
        else:
            hi = mid
    return lo


def presets(
    base: dict[str, float],
    metrics: dict[str, Any],
    cash: float | None,
    target: float,
    step: float,
) -> list[dict[str, Any]]:
    """Starting points the customer can edit. Solved ones show the arithmetic. What-ifs use the customer's step."""
    items: list[dict[str, Any]] = []
    placeholder = {"overrides": {}, "scale": False, "derive": False, "cash": None}

    # 1. Owner funding
    downside_gap = gap(base, metrics, cash, target)["downside"]
    needed = downside_gap["owner_funding_needed"]
    items.append(
        {
            **placeholder,
            "id": "owner_cash",
            "title": "Put in the cash the project needs",
            "solved": True,
            "cash": math.ceil(needed / 100) * 100 if needed else None,
            "derive": True,
            "basis": (
                f"At a downside coverage of {target:g}×, your downside cash flow supports about "
                f"{_money(downside_gap['debt_capacity'])} of debt. The project costs {_money(metrics['total_project_cost'])}, "
                f"so about {_money(needed)} would have to come from you. This is your cash, not a lender's decision."
            ),
        }
    )
    # 2. Lower build cost, solved
    solved_cost = _solve(base, "construction_cost", base["construction_cost"] * 0.2, base["construction_cost"], target, increasing=False)
    if solved_cost is not None and solved_cost < base["construction_cost"]:
        value = math.floor(solved_cost / 100) * 100 if solved_cost >= 100 else round(solved_cost, 2)
        items.append(
            {
                **placeholder,
                "id": "lower_build",
                "title": "Lower the build cost",
                "solved": True,
                "overrides": {"construction_cost": float(value)},
                "basis": (
                    f"Holding every other input, the highest construction cost that reaches {target:g}× downside coverage is about "
                    f"{_money(value)}, which is {(1 - value / base['construction_cost']) * 100:.0f}% below your entry."
                ),
            }
        )
    else:
        items.append(
            {
                **placeholder,
                "id": "lower_build",
                "title": "Lower the build cost",
                "solved": False,
                "overrides": {"construction_cost": round(base["construction_cost"] * (1 - step), 2)},
                "basis": (
                    f"A lower build cost alone does not reach {target:g}× in the range tested. "
                    f"This what-if cuts construction cost by your step of {step * 100:g}%."
                ),
            }
        )
    # 3. Revenue needed (ticket)
    revenue = metrics["downside_revenue"]
    service = metrics["annual_debt_service"]
    fixed = base["annual_fixed_costs"]
    margin = base["contribution_margin"]
    if revenue > 0 and margin > 0 and service > 0:
        needed_revenue = (service * target + fixed) / margin
        factor = needed_revenue / revenue
        if factor > 1:
            ticket = math.ceil(base["average_ticket"] * factor * 100) / 100
            items.append(
                {
                    **placeholder,
                    "id": "higher_ticket",
                    "title": "Raise the average ticket",
                    "solved": True,
                    "overrides": {"average_ticket": ticket},
                    "basis": (
                        f"Downside revenue would need to be {_money(needed_revenue)} for {target:g}× coverage, "
                        f"{factor:.2f}× today's downside revenue. Through the ticket alone, that is {display.money(ticket, cents=True)} per cover{' (a very large change, so look at seat turns in the revenue worksheet before trusting it)' if factor > 1.5 else ''}. "
                        "Through occupancy alone it would take "
                        f"weekday {base['weekday_occupancy'] * factor:.2f} and weekend {base['weekend_occupancy'] * factor:.2f}"
                        f"{' (above 1.00, so it cannot be done with occupancy alone)' if max(base['weekday_occupancy'], base['weekend_occupancy']) * factor > 1 else ''}."
                    ),
                }
            )
    # 4. Operating costs, solved
    if margin > 0 and revenue > 0:
        allowed_fixed = revenue * margin - service * target
        if allowed_fixed < fixed:
            if allowed_fixed >= 0:
                items.append(
                    {
                        **placeholder,
                        "id": "lower_fixed",
                        "title": "Lower annual fixed costs",
                        "solved": True,
                        "overrides": {"annual_fixed_costs": math.floor(allowed_fixed * 100) / 100},
                        "basis": (
                            f"The most annual fixed cost that keeps {target:g}× downside coverage is about {_money(allowed_fixed)}, "
                            f"{_money(fixed - allowed_fixed)} below your entry."
                        ),
                    }
                )
            else:
                items.append(
                    {
                        **placeholder,
                        "id": "lower_fixed",
                        "title": "Lower annual fixed costs",
                        "solved": False,
                        "overrides": {"annual_fixed_costs": 0.0},
                        "basis": (
                            f"Even with no fixed costs, downside contribution of {_money(revenue * margin)} does not reach "
                            f"{target:g}× of {_money(service)} in debt service. Cost cuts alone are not enough."
                        ),
                    }
                )
    # 5. Smaller venue, what-if
    seats = max(1, int(round(base["seats"] * (1 - step))))
    if seats < base["seats"]:
        items.append(
            {
                **placeholder,
                "id": "smaller_venue",
                "title": "Build a smaller venue",
                "solved": False,
                "overrides": {"seats": float(seats)},
                "scale": True,
                "basis": (
                    f"What-if: seats cut by your step of {step * 100:g}%. Construction, equipment, and soft costs scale with seats. "
                    "Annual fixed costs do not shrink on their own, so a smaller venue can look worse until you enter lower fixed costs you can support."
                ),
            }
        )
    # 6. Financing, what-if
    years = min(100, int(base["amortization_years"]) + 5)
    if years > int(base["amortization_years"]):
        items.append(
            {
                **placeholder,
                "id": "longer_term",
                "title": "Ask for a longer repayment term",
                "solved": False,
                "overrides": {"amortization_years": float(years)},
                "basis": (
                    f"What-if: amortization of {years} years instead of {int(base['amortization_years'])}. "
                    "A lender sets the term. A longer term lowers each yearly payment and raises total interest."
                ),
            }
        )
    return items


def customer_needs(changed: list[str], dependent: list[dict[str, Any]], placeholders: list[str]) -> list[dict[str, str]]:
    """Every assumption that needs the customer's verification."""
    rows = []
    seen = set()
    for key in changed + [item["field"] for item in dependent]:
        if key in seen:
            continue
        seen.add(key)
        rows.append({"field": LABELS.get(key, key), "verify": VERIFY.get(key, "Evidence you can show a lender.")})
    open_placeholders = [key for key in placeholders if key not in changed and key not in {row["field"] for row in dependent}]
    if open_placeholders:
        rows.append(
            {
                "field": "Placeholders (" + ", ".join(LABELS.get(key, key) for key in open_placeholders) + ")",
                "verify": "Blank or still at a starting number from RUGD. A starting number is not a market figure. Confirm each or replace it.",
            }
        )
    return rows


def parse_scenario(form: dict[str, str], base: dict[str, Any]) -> tuple[dict[str, Any], list[str]]:
    """Read posted overrides. A blank override means no change. A bad number is reported, not guessed."""
    errors: list[str] = []
    overrides: dict[str, float] = {}
    for key in FIELDS:
        raw = str(form.get(f"ov_{key}") or "").strip()
        if not raw:
            continue
        number = _num(raw)
        if number is None:
            errors.append(f"{LABELS[key]} must be a number.")
            continue
        if key in _SHARES and not 0 <= number <= 1:
            errors.append(f"{LABELS[key]} must be from 0 to 1. Enter 0.40 for 40%.")
            continue
        if key in _WHOLE and (number < 0 or int(number) != number):
            errors.append(f"{LABELS[key]} must be a whole number.")
            continue
        if key in {"seats", "amortization_years", "operating_days"} and number <= 0:
            errors.append(f"{LABELS[key]} must be above zero.")
            continue
        if number < 0:
            errors.append(f"{LABELS[key]} cannot be negative.")
            continue
        overrides[key] = number
    cash_raw = str(form.get("cash_contribution") or "").strip()
    cash = base["cash"]
    if cash_raw:
        parsed = _num(cash_raw)
        if parsed is None or parsed < 0:
            errors.append("Cash you can put in must be a number of zero or more.")
        else:
            cash = parsed
    return (
        {
            "overrides": overrides,
            "cash": cash,
            "cash_changed": bool(cash_raw) and cash != base["cash"],
            "scale_with_size": str(form.get("scale_with_size") or "") == "on",
            "derive_debt_from_cash": str(form.get("derive_debt_from_cash") or "") == "on",
        },
        errors,
    )


def build_scenario(base: dict[str, Any], spec: dict[str, Any], *, name: str = "") -> dict[str, Any]:
    """Full scenario record: inputs, what changed, what followed from it, and the projection."""
    inputs, changed, dependent = apply_overrides(
        base["inputs"],
        spec["overrides"],
        cash=spec["cash"],
        scale_with_size=spec["scale_with_size"],
        derive_debt_from_cash=spec["derive_debt_from_cash"],
    )
    metrics, error = evaluate(inputs)
    if spec.get("cash_changed"):
        changed = changed + ["available_cash"]
    return {
        "name": name,
        "inputs": inputs,
        "cash": spec["cash"],
        "changed": changed,
        "dependent": dependent,
        "metrics": metrics,
        "error": error,
        "spec": spec,
        "needs": customer_needs(changed, dependent, base["placeholders"]),
    }


def scenario_from_form(
    profile: dict[str, Any], form: dict[str, str]
) -> tuple[dict[str, Any], dict[str, Any] | None, list[str]]:
    """Base, draft scenario, and errors for a posted form. The draft is None when the base is incomplete or the form is invalid."""
    base = base_inputs(profile)
    if base["missing"]:
        return base, None, []
    spec, errors = parse_scenario(form, base)
    if errors:
        return base, None, errors
    scenario = build_scenario(base, spec, name=" ".join(str(form.get("name") or "").split())[:80])
    if scenario["error"]:
        return base, None, [scenario["error"]]
    return base, scenario, []


def recompute(stored: dict[str, Any]) -> dict[str, Any]:
    """Rebuild a saved scenario's projection from its saved inputs. The inputs are never re-derived."""
    data = stored.get("payload") or {}
    inputs = {key: float(value) for key, value in (data.get("inputs") or {}).items() if key in FIELDS}
    metrics, error = (None, "Saved inputs are incomplete.") if set(inputs) != set(FIELDS) else evaluate(inputs)
    return {
        "id": stored.get("id"),
        "name": str(data.get("name") or stored.get("title") or "Scenario"),
        "inputs": inputs,
        "cash": data.get("cash"),
        "changed": list(data.get("changed") or []),
        "dependent": list(data.get("dependent") or []),
        "metrics": metrics,
        "error": error,
        "needs": list(data.get("needs") or []),
        "applied": list(data.get("applied") or []),
        "saved_at": stored.get("created_at"),
        "note": str(data.get("note") or ""),
    }


def payload_for_save(scenario: dict[str, Any], name: str, note: str) -> dict[str, Any]:
    return {
        "name": name,
        "note": note,
        "inputs": scenario["inputs"],
        "cash": scenario["cash"],
        "changed": scenario["changed"],
        "dependent": scenario["dependent"],
        "needs": scenario["needs"],
        "applied": [],
    }


def applicable_values(scenario: dict[str, Any]) -> dict[str, str]:
    """The fields that would change in the draft if the customer approves this scenario."""
    values: dict[str, str] = {}
    fields = list(scenario["changed"]) + [item["field"] for item in scenario["dependent"]]
    for key in fields:
        if key == "available_cash":
            if scenario.get("cash") is not None:
                values[key] = _plain(scenario["cash"])
        elif key in scenario["inputs"]:
            values[key] = _plain(scenario["inputs"][key])
    return {key: value for key, value in values.items() if key in APPLICABLE}


def apply_to_profile(profile: dict[str, Any], scenario: dict[str, Any]) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Copy of the profile with a scenario's changed fields set, plus the from and to of each. Nothing else is touched."""
    updated = dict(profile)
    changes = []
    for key, value in applicable_values(scenario).items():
        previous = str(profile.get(key) or "")
        if previous.strip() == value:
            continue
        updated[key] = value
        changes.append({"field": key, "from": previous, "to": value})
    return updated, changes


def _plain(value: float) -> str:
    return str(int(value)) if float(value).is_integer() else f"{value:.4f}".rstrip("0").rstrip(".")


def _money(value: float | None) -> str:
    return display.money(value, missing="n/a")


def explain_official(record: dict[str, Any]) -> dict[str, Any]:
    """What the stored official result says, split into evidence issues and financial issues. Read only."""
    from scoring import rules

    result = record.get("result") if isinstance(record.get("result"), dict) else None
    if not result or not result.get("engine_ran"):
        return {"ran": False, "recommendation": "", "flags": [], "gaps": [], "evidence": [], "financial": [], "readiness": ""}
    flags = list(result.get("blocking_flags") or [])
    gaps = list(result.get("gap_flags") or [])
    evidence_flags = {rules.FLAG_DEMAND, rules.FLAG_DEMAND_UNVERIFIED, rules.FLAG_FINANCIALS_UNMEASURED}
    evidence, financial = [], []
    for flag in flags + gaps:
        action = rules.NEXT_ACTIONS.get(flag, "")
        row = {"flag": flag, "action": action, "blocking": flag in flags}
        (evidence if flag in evidence_flags or "UNEVALUATED" in flag else financial).append(row)
    return {
        "ran": True,
        "recommendation": str(result.get("recommendation") or ""),
        "flags": flags,
        "gaps": gaps,
        "evidence": evidence,
        "financial": financial,
        "readiness": str(result.get("readiness_status") or ""),
        "review": str(result.get("human_review_status") or "pending"),
    }


def financial_findings(metrics: dict[str, Any] | None, target: float) -> list[str]:
    """Plain statements about the working numbers. They are not official flags."""
    if not metrics:
        return []
    lines = []
    if metrics["base_cash_flow"] <= 0:
        lines.append("Base cash flow before debt service is zero or negative under your assumptions.")
    if metrics["annual_debt_service"] and metrics["base_cash_flow"] > 0 and metrics["base_dscr"] is not None and metrics["base_dscr"] < 1:
        lines.append(f"Base cash flow covers {metrics['base_dscr']:.2f}× of yearly debt service, below 1.00×.")
    if metrics["annual_debt_service"] and metrics["downside_dscr"] is not None and metrics["downside_dscr"] < target:
        if metrics["downside_cash_flow"] <= 0:
            lines.append(f"Downside cash flow is zero or negative, so it covers none of the yearly debt service (target {target:g}×).")
        else:
            lines.append(f"Downside cash flow covers {metrics['downside_dscr']:.2f}× of yearly debt service, below the {target:g}× used here.")
    if metrics["break_even_revenue"] and metrics["base_revenue"] < metrics["break_even_revenue"]:
        lines.append(
            f"Base revenue of {_money(metrics['base_revenue'])} is below break-even revenue of {_money(metrics['break_even_revenue'])}."
        )
    return lines


TARGETS = (DEFAULT_DOWNSIDE_DSCR_MINIMUM, LENDER_DOWNSIDE_DSCR_MINIMUM)
