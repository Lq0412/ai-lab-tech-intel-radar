from __future__ import annotations

import argparse
from datetime import date, datetime
from pathlib import Path

from dotenv import load_dotenv

from radar.collectors.github import GithubCollector
from radar.collectors.huggingface import HuggingFaceCollector
from radar.collectors.rss import RssCollector
from radar.config import (RuntimeConfig, Settings, load_runtime, load_settings,
                          load_sources)
from radar.llm.client import LLMClient
from radar.llm.prescreen import prescreen
from radar.llm.scoring import score_item
from radar.models import Analysis
from radar.pipeline.cluster import cluster_items
from radar.pipeline.filter import apply_filters
from radar.ranking import compute_quality, recommend
from radar.report import ReportRow, render_report
from radar.storage import Repository

CONFIG_DIR = Path("config")


def run_collect(repo: Repository, settings: Settings, runtime: RuntimeConfig,
                now: str) -> int:
    sources = load_sources(CONFIG_DIR / "sources.yaml")
    collectors = {
        "github": GithubCollector(token=runtime.github_token),
        "huggingface": HuggingFaceCollector(),
        "rss": RssCollector(),
    }
    count = 0
    for source in sources:
        collector = collectors.get(source.kind)
        if collector is None:
            continue
        for item in collector.collect(source, now=now):
            repo.upsert_item(item)
            count += 1
    return count


def run_process(repo: Repository, settings: Settings) -> int:
    items = repo.list_items()
    kept, dropped = apply_filters(items, settings)
    for it in dropped:
        item_id = repo.item_id_by_raw(it.raw_id)
        if item_id:
            repo.set_cluster(item_id, cluster_id=-1, is_duplicate=True)
    clusters = cluster_items(kept, threshold=settings.title_similarity_threshold)
    kept_count = 0
    for cid, cluster in enumerate(clusters):
        for member in cluster.members:
            item_id = repo.item_id_by_raw(member.raw_id)
            if item_id is None:
                continue
            is_dup = member.raw_id != cluster.primary.raw_id
            repo.set_cluster(item_id, cluster_id=cid, is_duplicate=is_dup)
        kept_count += 1
    return kept_count


def run_analyze(repo: Repository, settings: Settings, client: LLMClient,
                today: str) -> int:
    primaries = repo.list_items(only_unique=True)
    analyzed = 0
    for item in primaries:
        item_id = repo.item_id_by_raw(item.raw_id)
        if item_id is None:
            continue
        if not prescreen(item, client):
            repo.save_analysis(Analysis(item_id=item_id, is_relevant=False),
                               quality_score=0.0, recommendation="暂不投入",
                               created_at=today)
            continue
        analysis = score_item(item_id, item, client)
        quality = compute_quality(analysis, item.source_tier, item.published_at,
                                  settings, today)
        rec = recommend(quality, analysis.category, settings)
        repo.save_analysis(analysis, quality_score=quality, recommendation=rec,
                           created_at=today)
        analyzed += 1
    return analyzed


def run_report(repo: Repository, week: str) -> str:
    rows: list[ReportRow] = []
    for item in repo.list_items(only_unique=True):
        item_id = repo.item_id_by_raw(item.raw_id)
        a = repo.get_analysis_row(item_id) if item_id else None
        if not a or not a["is_relevant"]:
            continue
        rows.append(ReportRow(
            title=item.title, recommendation=a["recommendation"],
            quality_score=a["quality_score"], category=a["category"],
            source_tier=item.source_tier, summary=a["summary"],
            good_for=a["good_for"], not_good_for=a["not_good_for"],
            risks=a["risks"], url=item.url, related_urls=[]))
    return render_report(rows, week=week)


def run_review(repo: Repository, item_id: int, verdict: str, note: str,
               reviewed_at: str) -> None:
    repo.save_review(item_id, verdict=verdict, note=note, reviewed_at=reviewed_at)


def _iso_week(today: str) -> str:
    d = date.fromisoformat(today)
    y, w, _ = d.isocalendar()
    return f"{y}-W{w:02d}"


def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    parser = argparse.ArgumentParser(prog="radar")
    parser.add_argument("command",
                        choices=["collect", "process", "analyze", "report",
                                 "review", "all"])
    parser.add_argument("--out", default="report.md")
    parser.add_argument("--item-id", type=int)
    parser.add_argument("--verdict", default="")
    parser.add_argument("--note", default="")
    args = parser.parse_args(argv)

    runtime = load_runtime()
    settings = load_settings(CONFIG_DIR / "settings.yaml")
    repo = Repository(runtime.db_path)
    repo.init_schema()
    now = datetime.now().isoformat(timespec="seconds")
    today = date.today().isoformat()

    if args.command in ("collect", "all"):
        print("collected:", run_collect(repo, settings, runtime, now))
    if args.command in ("process", "all"):
        print("clusters:", run_process(repo, settings))
    if args.command in ("analyze", "all"):
        client = LLMClient(model=runtime.model, api_key=runtime.openai_api_key,
                           base_url=runtime.openai_base_url)
        print("analyzed:", run_analyze(repo, settings, client, today))
    if args.command in ("report", "all"):
        md = run_report(repo, week=_iso_week(today))
        Path(args.out).write_text(md, encoding="utf-8")
        print("report written:", args.out)
    if args.command == "review":
        if args.item_id is None:
            parser.error("--item-id is required for review")
        run_review(repo, item_id=args.item_id, verdict=args.verdict,
                   note=args.note, reviewed_at=today)
        print("review saved for item", args.item_id)
    repo.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
