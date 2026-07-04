#!/usr/bin/env python
"""Query the ucscxenatoolspy TCGA Analysis API."""
from __future__ import annotations

import argparse
import json
import os
import sys
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

DEFAULT_BASE_URL = os.getenv("UCSCXENA_API_BASE_URL", "https://ucscxenatoolspy.onrender.com")
DEFAULT_API_KEY = os.getenv("UCSCXENA_API_KEY")


def _request(base_url: str, path: str, params: dict[str, str], api_key: str | None, timeout: int) -> Any:
    url = base_url.rstrip("/") + path
    if params:
        url += "?" + urllib.parse.urlencode(params)
    headers = {"Accept": "application/json"}
    if api_key:
        headers["X-API-Key"] = api_key
    req = urllib.request.Request(url, headers=headers, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            text = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise SystemExit(f"HTTP {exc.code} from {url}: {body}") from exc
    except urllib.error.URLError as exc:
        raise SystemExit(f"Could not reach {url}: {exc.reason}") from exc
    return json.loads(text)


def _p(value: Any, digits: int = 4) -> str:
    if value is None:
        return "NA"
    if isinstance(value, float):
        if value != 0 and abs(value) < 0.001:
            return f"{value:.2e}"
        return f"{value:.{digits}g}"
    return str(value)


def summarize(task: str, data: Any) -> str:
    if task == "cancers":
        cancers = data.get("cancers", [])
        with_normals = sum(1 for item in cancers if item.get("has_normal"))
        examples = ", ".join(item.get("cancer", "?") for item in cancers[:8])
        return f"Available cancer entries: {data.get('count', len(cancers))}; with >=3 normals: {with_normals}. Examples: {examples}."

    if task == "diff-expr":
        gene = data.get("gene")
        if data.get("gene_input"):
            gene = f"{data['gene_input']} -> {gene}"
        tumor = data.get("tumor", {})
        normal = data.get("normal", {})
        return (
            f"{gene} in {data.get('cancer')} ({data.get('cancer_full_name')}): "
            f"tumor n={tumor.get('n')}, normal n={normal.get('n')}, "
            f"log2-scale difference={_p(data.get('log2_fold_change'))}, "
            f"Mann-Whitney p={_p(data.get('p_value'))}."
        )

    if task == "corr":
        g1 = data.get("gene1")
        g2 = data.get("gene2")
        if data.get("gene1_input"):
            g1 = f"{data['gene1_input']} -> {g1}"
        if data.get("gene2_input"):
            g2 = f"{data['gene2_input']} -> {g2}"
        return (
            f"{g1} vs {g2} in {data.get('cancer')} primary tumors: "
            f"n={data.get('n')}, Spearman r={_p(data.get('spearman_r'))}, "
            f"p={_p(data.get('p_value'))}."
        )

    if task == "survival":
        lines = [
            f"{data.get('gene')} in {data.get('cancer')} ({data.get('cancer_full_name')}), log-rank survival associations:"
        ]
        for endpoint, result in data.get("survival", {}).items():
            if "error" in result:
                lines.append(f"- {endpoint}: {result['error']}")
                continue
            median = result.get("median_cutoff", {})
            optimal = result.get("optimal_cutoff", {})
            lines.append(
                f"- {endpoint}: n={result.get('n_total')}, events={result.get('n_events')}; "
                f"median p={_p(median.get('p_value'))}; exploratory optimal p={_p(optimal.get('p_value'))}."
            )
        lines.append("Optimal-cutoff results are exploratory and not adjusted for multiple cutoff testing.")
        return "\n".join(lines)

    return json.dumps(data, indent=2, ensure_ascii=False)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default=DEFAULT_BASE_URL)
    parser.add_argument("--api-key", default=DEFAULT_API_KEY)
    parser.add_argument("--timeout", type=int, default=120)
    parser.add_argument("--json", action="store_true", help="Print raw JSON only")

    sub = parser.add_subparsers(dest="task", required=True)
    sub.add_parser("cancers")

    diff = sub.add_parser("diff-expr")
    diff.add_argument("--gene", required=True)
    diff.add_argument("--cancer", required=True)

    corr = sub.add_parser("corr")
    corr.add_argument("--gene", required=True, help="First gene")
    corr.add_argument("--gene2", required=True, help="Second gene")
    corr.add_argument("--cancer", required=True)

    surv = sub.add_parser("survival")
    surv.add_argument("--gene", required=True)
    surv.add_argument("--cancer", required=True)
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    paths = {
        "cancers": "/api/v1/cancers",
        "diff-expr": "/api/v1/diff-expr",
        "corr": "/api/v1/corr",
        "survival": "/api/v1/survival",
    }
    params: dict[str, str] = {}
    if args.task == "diff-expr":
        params = {"gene": args.gene, "cancer": args.cancer}
    elif args.task == "corr":
        params = {"gene1": args.gene, "gene2": args.gene2, "cancer": args.cancer}
    elif args.task == "survival":
        params = {"gene": args.gene, "cancer": args.cancer}

    data = _request(args.base_url, paths[args.task], params, args.api_key, args.timeout)
    if args.json:
        print(json.dumps(data, indent=2, ensure_ascii=False))
    else:
        print(summarize(args.task, data))
        print("\nRaw JSON:")
        print(json.dumps(data, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
