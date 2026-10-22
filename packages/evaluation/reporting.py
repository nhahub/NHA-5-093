"""Markdown rendering for auditable M5 analysis output."""

from __future__ import annotations

from typing import Any


def _value(value: Any) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.6f}"
    return str(value)


def render_markdown(result: dict[str, Any]) -> str:
    summary = result["report_summary"]
    denominators = summary["metric_denominators"]
    numerators = result["metric_numerators"]
    lines = [
        "# HireGuard M5 findings analysis",
        "",
        "> Generated from stored run, finding, review, and event IDs. This report does not",
        "> constitute final evaluation evidence unless the protocol status is APPROVED.",
        "",
        "## Core metrics",
        "",
        "| Metric | Numerator | Denominator | Value |",
        "|---|---:|---:|---:|",
        f"| Confirmed discovery | {numerators['confirmed_discovery_findings']} | {denominators['completed_intended_violation_attempts']} | {_value(summary['confirmed_discovery_rate'])} |",
        f"| Finding precision | {numerators['confirmed_reviewed_flags']} | {denominators['all_reviewed_flags']} | {_value(summary['finding_precision'])} |",
        f"| False-positive rate | {numerators['rejected_reviewed_flags']} | {denominators['all_reviewed_flags']} | {_value(summary['false_positive_rate'])} |",
        f"| Completion | {summary['completed_runs']} | {denominators['all_scheduled_runs']} | {_value(summary['completion_rate'])} |",
        "",
        "## Confirmed discovery by method, target, and family",
        "",
        "| Method | Target | Family | Confirmed | Completed intended attempts | Rate | Failed runs |",
        "|---|---|---|---:|---:|---:|---:|",
    ]
    for row in result["confirmed_discovery_breakdowns"]:
        lines.append(
            "| {method} | {target_version} | {family} | {confirmed_findings} | "
            "{completed_intended_violation_attempts} | {rate} | {failed_runs} |".format(
                **row, rate=_value(row["confirmed_discovery_rate"])
            )
        )
    lines.extend(
        [
            "",
            "## Efficiency",
            "",
            f"- Tokens: {summary['tokens_total']}",
            f"- Mean target latency (ms): {_value(summary['mean_latency_ms'])}",
            f"- Estimated API cost (USD): {_value(summary['estimated_api_cost_usd'])}",
            f"- Latency denominator (runs with TURN events): {result['efficiency_evidence']['latency_run_count']}",
            "",
            "## Dialect pairs",
            "",
            "| Pair | MSA session | EGY session | MSA | EGY | MSA−EGY |",
            "|---|---|---|---:|---:|---:|",
        ]
    )
    for row in result["dialect_pairs"]:
        lines.append(
            f"| {row['pair_id']} | {row['msa_session_id']} | {row['egy_session_id']} | "
            f"{_value(row['msa_score'])} | {_value(row['egy_score'])} | "
            f"{_value(row['score_delta_msa_minus_egy'])} |"
        )
    lines.extend(
        [
            "",
            "## Repeatability",
            "",
            "| Transcript | Target | Observed/expected | Mean | Population SD | Min | Max | Flip |",
            "|---|---|---:|---:|---:|---:|---:|---|",
        ]
    )
    for row in result["repeatability_groups"]:
        lines.append(
            f"| {row['transcript_id']} | {row['target_version']} | "
            f"{row['observed_repeats']}/{row['expected_repeats']} | {_value(row['mean'])} | "
            f"{_value(row['stddev_population'])} | {_value(row['minimum'])} | "
            f"{_value(row['maximum'])} | {'yes' if row['pass_fail_flip'] else 'no'} |"
        )
    lines.extend(["", "## Source IDs", ""])
    for key, values in result["source_ids"].items():
        lines.append(f"- {key}: {', '.join(values) if values else 'none'}")
    lines.extend(["", "## Run and review accounting", ""])
    for status, count in result["status_counts"].items():
        run_ids = result["run_status_ids"][status]
        lines.append(f"- Run {status}: {count} ({', '.join(run_ids)})")
    for status, count in result["finding_status_counts"].items():
        lines.append(f"- Finding review {status}: {count}")
    lines.extend(["", "## Limitations", ""])
    for limitation in summary["limitations"]:
        lines.append(f"- {limitation}")
    return "\n".join(lines) + "\n"
