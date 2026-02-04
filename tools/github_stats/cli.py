"""CLI interface for GitHub Stats Fetcher."""

import json
import sys
from typing import List, Optional

import click
from rich.console import Console
from rich.panel import Panel
from rich.progress import BarColumn, Progress, SpinnerColumn, TextColumn
from rich.table import Table

from shared.cli import create_table, error, handle_errors, info, print_table, success, warning
from shared.logger import setup_logger

from .fetcher import GitHubStats, RepoStats

console = Console()


def display_repo_stats(stats: RepoStats, detailed: bool = False) -> None:
    """
    Display repository statistics.

    Args:
        stats: RepoStats object
        detailed: Show detailed information
    """
    if stats.error:
        error(f"Failed to fetch {stats.full_name}")
        error(f"Error: {stats.error}")
        return

    # Header
    title = f"[bold cyan]{stats.full_name}[/bold cyan]"
    if stats.description:
        title += f"\n[dim]{stats.description}[/dim]"

    console.print(Panel(title, title="Repository Stats"))

    # Main metrics
    console.print("\n[bold yellow]📊 Metrics:[/bold yellow]")
    console.print(f"  ⭐ Stars:        [bold]{stats.stars:,}[/bold]")
    console.print(f"  🍴 Forks:        {stats.forks:,}")
    console.print(f"  👀 Watchers:     {stats.watchers:,}")
    console.print(f"  🐛 Open Issues:  {stats.open_issues:,}")

    if stats.stars_per_day:
        console.print(f"  📈 Stars/day:    {stats.stars_per_day:.2f}")

    # Info
    console.print("\n[bold yellow]ℹ️  Information:[/bold yellow]")
    console.print(f"  Language:      {stats.language or 'N/A'}")
    console.print(f"  License:       {stats.license or 'None'}")
    console.print(f"  Default Branch: {stats.default_branch}")
    console.print(f"  Size:          {stats.size:,} KB")

    if stats.topics:
        console.print(f"  Topics:        {', '.join(stats.topics)}")

    # Dates
    console.print("\n[bold yellow]📅 Timeline:[/bold yellow]")
    console.print(f"  Created:       {stats.created_at.strftime('%Y-%m-%d')} ({stats.days_since_creation} days ago)")
    console.print(f"  Last Updated:  {stats.updated_at.strftime('%Y-%m-%d')} ({stats.days_since_update} days ago)")
    console.print(f"  Last Push:     {stats.pushed_at.strftime('%Y-%m-%d')}")

    # Flags
    if stats.is_fork:
        warning("  ⚠️  This is a fork")
    if stats.is_archived:
        warning("  🗃️  This repository is archived")

    console.print()


def display_comparison(repos: List[RepoStats]) -> None:
    """
    Display side-by-side comparison of repositories.

    Args:
        repos: List of RepoStats
    """
    console.print(Panel("[bold cyan]Repository Comparison[/bold cyan]"))

    # Filter out errors
    valid_repos = [r for r in repos if not r.error]

    if not valid_repos:
        error("No valid repositories to compare")
        return

    # Create comparison table
    table = create_table(title=None)
    table.add_column("Metric", style="bold yellow")
    
    for repo in valid_repos:
        table.add_column(repo.name, style="cyan")

    # Add rows
    metrics = [
        ("Stars ⭐", lambda r: f"{r.stars:,}"),
        ("Forks 🍴", lambda r: f"{r.forks:,}"),
        ("Watchers 👀", lambda r: f"{r.watchers:,}"),
        ("Issues 🐛", lambda r: f"{r.open_issues:,}"),
        ("Language", lambda r: r.language or "N/A"),
        ("License", lambda r: r.license or "None"),
        ("Size (KB)", lambda r: f"{r.size:,}"),
        ("Created", lambda r: r.created_at.strftime("%Y-%m-%d")),
        ("Updated", lambda r: r.updated_at.strftime("%Y-%m-%d")),
        ("Age (days)", lambda r: str(r.days_since_creation)),
        ("Stars/day", lambda r: f"{r.stars_per_day:.2f}" if r.stars_per_day else "N/A"),
    ]

    for label, getter in metrics:
        row = [label]
        for repo in valid_repos:
            row.append(getter(repo))
        table.add_row(*row)

    print_table(table)

    # Winner analysis
    console.print("\n[bold yellow]🏆 Analysis:[/bold yellow]")
    
    most_stars = max(valid_repos, key=lambda r: r.stars)
    console.print(f"  Most stars: [bold]{most_stars.name}[/bold] ({most_stars.stars:,} ⭐)")
    
    most_active = max(valid_repos, key=lambda r: r.pushed_at)
    console.print(f"  Most active: [bold]{most_active.name}[/bold] (last push: {most_active.pushed_at.strftime('%Y-%m-%d')})")
    
    best_ratio = max(valid_repos, key=lambda r: r.stars_per_day if r.stars_per_day else 0)
    if best_ratio.stars_per_day:
        console.print(f"  Best growth: [bold]{best_ratio.name}[/bold] ({best_ratio.stars_per_day:.2f} stars/day)")

    console.print()


def display_contributors(contributors, repo_name: str) -> None:
    """Display top contributors."""
    if not contributors:
        info("No contributors found")
        return

    console.print(f"\n[bold yellow]👥 Top Contributors for {repo_name}:[/bold yellow]")
    
    table = create_table(title=None)
    table.add_column("#", justify="right", style="cyan", width=4)
    table.add_column("Username", style="bold")
    table.add_column("Contributions", justify="right", style="yellow")
    table.add_column("% of total", justify="right", style="dim")

    total_contributions = sum(c.contributions for c in contributors)

    for idx, contrib in enumerate(contributors, 1):
        percentage = (contrib.contributions / total_contributions * 100) if total_contributions > 0 else 0
        table.add_row(
            str(idx),
            contrib.username,
            str(contrib.contributions),
            f"{percentage:.1f}%",
        )

    print_table(table)


def display_languages(languages: dict, repo_name: str) -> None:
    """Display language breakdown."""
    if not languages:
        info("No language data found")
        return

    console.print(f"\n[bold yellow]💻 Languages in {repo_name}:[/bold yellow]")

    total_bytes = sum(languages.values())
    
    table = create_table(title=None)
    table.add_column("Language", style="bold cyan")
    table.add_column("Bytes", justify="right", style="yellow")
    table.add_column("Percentage", justify="right")
    table.add_column("Visual", width=30)

    # Sort by bytes descending
    sorted_langs = sorted(languages.items(), key=lambda x: x[1], reverse=True)

    for lang, bytes_count in sorted_langs:
        percentage = (bytes_count / total_bytes * 100) if total_bytes > 0 else 0
        bar_length = int((percentage / 100) * 25)
        bar = "█" * bar_length + "░" * (25 - bar_length)
        
        table.add_row(
            lang,
            f"{bytes_count:,}",
            f"{percentage:.1f}%",
            bar,
        )

    print_table(table)


@click.command()
@click.option("--repo", "-r", help="Repository in format 'owner/repo'", multiple=True)
@click.option("--compare", "-c", is_flag=True, help="Compare multiple repositories")
@click.option("--contributors", is_flag=True, help="Show top contributors")
@click.option("--languages", "-l", is_flag=True, help="Show language breakdown")
@click.option("--search", "-s", help="Search repositories")
@click.option(
    "--sort",
    type=click.Choice(["stars", "forks", "updated"], case_sensitive=False),
    default="stars",
    help="Sort search results by",
)
@click.option("--limit", type=int, default=10, help="Limit for search/contributors")
@click.option(
    "--output",
    "-o",
    type=click.Choice(["rich", "json"], case_sensitive=False),
    default="rich",
    help="Output format",
)
@click.option("--token", help="GitHub personal access token (or set GITHUB_TOKEN env var)")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
@handle_errors
def main(
    repo: tuple,
    compare: bool,
    contributors: bool,
    languages: bool,
    search: Optional[str],
    sort: str,
    limit: int,
    output: str,
    token: Optional[str],
    verbose: bool,
):
    """
    GitHub Stats Fetcher - Analyze GitHub repositories.

    Examples:

        \b
        # Get repo stats
        gh-stats --repo facebook/react

        \b
        # Compare repos
        gh-stats --repo facebook/react --repo vuejs/vue --compare

        \b
        # Show contributors
        gh-stats --repo torvalds/linux --contributors

        \b
        # Language breakdown
        gh-stats --repo python/cpython --languages

        \b
        # Search repos
        gh-stats --search "machine learning" --sort stars --limit 5

        \b
        # JSON output
        gh-stats --repo nodejs/node --output json
    """
    # Setup logging
    log_level = "DEBUG" if verbose else "INFO"
    setup_logger(__name__, level=log_level)

    # Initialize fetcher
    fetcher = GitHubStats(token=token)

    # Search mode
    if search:
        info(f"Searching for: {search}")
        
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
        ) as progress:
            task = progress.add_task("Searching...", total=None)
            results = fetcher.search_repos(search, sort=sort, limit=limit)
            progress.update(task, completed=True)

        if not results:
            warning("No results found")
            sys.exit(0)

        if output == "rich":
            console.print(f"\n[bold cyan]Search Results ({len(results)}):[/bold cyan]\n")
            
            table = create_table(title=None)
            table.add_column("#", justify="right", style="cyan", width=4)
            table.add_column("Repository", style="bold")
            table.add_column("Stars", justify="right", style="yellow")
            table.add_column("Language", style="dim")
            table.add_column("Description", style="dim", no_wrap=False)

            for idx, r in enumerate(results, 1):
                table.add_row(
                    str(idx),
                    r.full_name,
                    f"{r.stars:,}",
                    r.language or "N/A",
                    (r.description or "")[:60],
                )

            print_table(table)
        else:
            data = [
                {
                    "name": r.full_name,
                    "stars": r.stars,
                    "forks": r.forks,
                    "language": r.language,
                    "description": r.description,
                }
                for r in results
            ]
            print(json.dumps({"results": data, "count": len(data)}, indent=2))

        sys.exit(0)

    # Repo mode
    if not repo:
        error("Please specify at least one --repo or use --search")
        sys.exit(1)

    repos_list = list(repo)

    # Fetch stats
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        BarColumn(),
        TextColumn("[progress.percentage]{task.percentage:>3.0f}%"),
    ) as progress:
        task = progress.add_task(f"Fetching stats...", total=len(repos_list))
        
        stats_list = []
        for r in repos_list:
            stats = fetcher.get_repo_stats(r)
            stats_list.append(stats)
            progress.advance(task)

    # Check for errors
    errors = [s for s in stats_list if s.error]
    if errors:
        for s in errors:
            error(f"{s.full_name}: {s.error}")

    valid_stats = [s for s in stats_list if not s.error]

    if not valid_stats:
        error("No valid repositories found")
        sys.exit(1)

    # Output
    if output == "json":
        data = []
        for s in valid_stats:
            data.append({
                "name": s.full_name,
                "stars": s.stars,
                "forks": s.forks,
                "watchers": s.watchers,
                "open_issues": s.open_issues,
                "language": s.language,
                "license": s.license,
                "size": s.size,
                "created_at": s.created_at.isoformat(),
                "updated_at": s.updated_at.isoformat(),
                "topics": s.topics,
            })
        print(json.dumps({"repositories": data}, indent=2))
        sys.exit(0)

    # Rich output
    if compare and len(valid_stats) > 1:
        display_comparison(valid_stats)
    else:
        for stats in valid_stats:
            display_repo_stats(stats, detailed=True)

    # Additional info
    if contributors:
        for r in repos_list:
            contribs = fetcher.get_contributors(r, limit=limit)
            if contribs:
                display_contributors(contribs, r)

    if languages:
        for r in repos_list:
            langs = fetcher.get_languages(r)
            if langs:
                display_languages(langs, r)

    success("Fetch completed!")
    sys.exit(0)


if __name__ == "__main__":
    main()
