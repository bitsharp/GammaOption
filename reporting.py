"""Reporting helpers (daily table outputs)."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd


def _extract_level(levels: Dict[str, Any], name: str) -> Optional[float]:
    value = levels.get(name)
    if isinstance(value, (int, float)):
        return float(value)
    return None


def _extract_converted_level(converted_levels: Dict[str, Any], name: str) -> tuple[Optional[float], Optional[float]]:
    item = converted_levels.get(name, {}) if isinstance(converted_levels, dict) else {}
    spx = item.get("spx") if isinstance(item, dict) else None
    es = item.get("es") if isinstance(item, dict) else None
    return (
        float(spx) if isinstance(spx, (int, float)) else None,
        float(es) if isinstance(es, (int, float)) else None,
    )


def write_daily_table(data_dir: Path, results: Dict[str, Any]) -> Path:
    """Write the daily summary table as CSV.

    The goal is a single, human-readable table per day with the key levels.
    """
    data_dir.mkdir(parents=True, exist_ok=True)

    timestamp = results.get("timestamp") or datetime.now().isoformat()
    date_str = (results.get("date") or timestamp[:10]).replace("-", "")

    spx_price = results.get("spx_price")
    es_price = results.get("es_price")
    spread = results.get("spread")
    regime = results.get("regime")

    levels = results.get("levels") or {}
    converted_levels = results.get("converted_levels") or {}

    put_wall_spx, put_wall_es = _extract_converted_level(converted_levels, "put_wall")
    call_wall_spx, call_wall_es = _extract_converted_level(converted_levels, "call_wall")
    gamma_flip_spx, gamma_flip_es = _extract_converted_level(converted_levels, "gamma_flip")

    row = {
        "date": results.get("date") or timestamp[:10],
        "timestamp": timestamp,
        "spx_price": float(spx_price) if isinstance(spx_price, (int, float)) else None,
        "es_price": float(es_price) if isinstance(es_price, (int, float)) else None,
        "spread": float(spread) if isinstance(spread, (int, float)) else None,
        "regime": regime,
        "put_wall_spx": put_wall_spx or _extract_level(levels, "put_wall"),
        "put_wall_es": put_wall_es,
        "call_wall_spx": call_wall_spx or _extract_level(levels, "call_wall"),
        "call_wall_es": call_wall_es,
        "gamma_flip_spx": gamma_flip_spx or _extract_level(levels, "gamma_flip"),
        "gamma_flip_es": gamma_flip_es,
    }

    out_path = data_dir / f"daily_table_{date_str}.csv"
    pd.DataFrame([row]).to_csv(out_path, index=False)
    return out_path
