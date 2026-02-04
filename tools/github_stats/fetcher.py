"""Core GitHub statistics fetching logic."""

import os
from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional

import httpx

from shared.logger import get_logger

logger = get_logger(__name__)


@dataclass
class RepoStats:
    """Statistics for a GitHub repository."""

    name: str
    full_name: str
    owner: str
    description: Optional[str]
    stars: int
    forks: int
    watchers: int
    open_issues: int
    language: Optional[str]
    created_at: datetime
    updated_at: datetime
    pushed_at: datetime
    size: int  # KB
    license: Optional[str]
    topics: List[str]
    is_fork: bool
    is_archived: bool
    default_branch: str
    
    # Calculated metrics
    days_since_creation: Optional[int] = None
    days_since_update: Optional[int] = None
    stars_per_day: Optional[float] = None
    
    error: Optional[str] = None

    def calculate_metrics(self) -> None:
        """Calculate derived metrics."""
        now = datetime.utcnow()
        
        if self.created_at:
            delta = now - self.created_at
            self.days_since_creation = delta.days
            
            if self.days_since_creation > 0:
                self.stars_per_day = self.stars / self.days_since_creation
        
        if self.updated_at:
            delta = now - self.updated_at
            self.days_since_update = delta.days


@dataclass
class ContributorStats:
    """Statistics for a contributor."""

    username: str
    contributions: int
    avatar_url: str


class GitHubStats:
    """
    Fetch GitHub repository statistics.

    Uses GitHub API v3 (REST).
    """

    def __init__(self, token: Optional[str] = None):
        """
        Initialize GitHub stats fetcher.

        Args:
            token: GitHub personal access token (optional but recommended)
        """
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.base_url = "https://api.github.com"
        
        self.headers = {
            "Accept": "application/vnd.github.v3+json",
            "User-Agent": "github-stats-fetcher",
        }
        
        if self.token:
            self.headers["Authorization"] = f"token {self.token}"
            logger.debug("Using authenticated GitHub API")
        else:
            logger.warning("No GitHub token found. Rate limits: 60 req/hour (vs 5000 with token)")

    def get_repo_stats(self, repo: str) -> RepoStats:
        """
        Get statistics for a repository.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            RepoStats object
        """
        logger.info(f"Fetching stats for {repo}")

        try:
            # Validate format
            if "/" not in repo:
                raise ValueError(f"Invalid repo format. Use 'owner/repo', got: {repo}")

            owner, repo_name = repo.split("/", 1)

            # Fetch repo data
            url = f"{self.base_url}/repos/{repo}"
            
            with httpx.Client(headers=self.headers, timeout=10.0) as client:
                response = client.get(url)
                
                if response.status_code == 404:
                    return self._create_error_stats(repo, "Repository not found")
                elif response.status_code == 403:
                    return self._create_error_stats(repo, "Rate limit exceeded or access forbidden")
                elif response.status_code != 200:
                    return self._create_error_stats(repo, f"API error: {response.status_code}")

                data = response.json()

            # Parse response
            stats = RepoStats(
                name=data["name"],
                full_name=data["full_name"],
                owner=data["owner"]["login"],
                description=data.get("description"),
                stars=data["stargazers_count"],
                forks=data["forks_count"],
                watchers=data["watchers_count"],
                open_issues=data["open_issues_count"],
                language=data.get("language"),
                created_at=datetime.fromisoformat(data["created_at"].replace("Z", "+00:00")),
                updated_at=datetime.fromisoformat(data["updated_at"].replace("Z", "+00:00")),
                pushed_at=datetime.fromisoformat(data["pushed_at"].replace("Z", "+00:00")),
                size=data["size"],
                license=data["license"]["name"] if data.get("license") else None,
                topics=data.get("topics", []),
                is_fork=data["fork"],
                is_archived=data["archived"],
                default_branch=data["default_branch"],
            )

            stats.calculate_metrics()
            return stats

        except ValueError as e:
            return self._create_error_stats(repo, str(e))
        
        except httpx.RequestError as e:
            logger.error(f"Network error: {e}")
            return self._create_error_stats(repo, f"Network error: {e}")
        
        except Exception as e:
            logger.error(f"Unexpected error: {e}")
            return self._create_error_stats(repo, f"Error: {e}")

    def get_contributors(self, repo: str, limit: int = 10) -> List[ContributorStats]:
        """
        Get top contributors for a repository.

        Args:
            repo: Repository in format "owner/repo"
            limit: Maximum number of contributors to return

        Returns:
            List of ContributorStats
        """
        logger.info(f"Fetching contributors for {repo}")

        try:
            url = f"{self.base_url}/repos/{repo}/contributors"
            params = {"per_page": limit}

            with httpx.Client(headers=self.headers, timeout=10.0) as client:
                response = client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch contributors: {response.status_code}")
                    return []

                data = response.json()

            contributors = []
            for contrib in data:
                contributors.append(
                    ContributorStats(
                        username=contrib["login"],
                        contributions=contrib["contributions"],
                        avatar_url=contrib["avatar_url"],
                    )
                )

            return contributors

        except Exception as e:
            logger.error(f"Failed to fetch contributors: {e}")
            return []

    def get_languages(self, repo: str) -> Dict[str, int]:
        """
        Get language breakdown for a repository.

        Args:
            repo: Repository in format "owner/repo"

        Returns:
            Dict of language -> bytes of code
        """
        logger.info(f"Fetching languages for {repo}")

        try:
            url = f"{self.base_url}/repos/{repo}/languages"

            with httpx.Client(headers=self.headers, timeout=10.0) as client:
                response = client.get(url)
                
                if response.status_code != 200:
                    logger.error(f"Failed to fetch languages: {response.status_code}")
                    return {}

                return response.json()

        except Exception as e:
            logger.error(f"Failed to fetch languages: {e}")
            return {}

    def compare_repos(self, repos: List[str]) -> List[RepoStats]:
        """
        Compare multiple repositories.

        Args:
            repos: List of repositories in format "owner/repo"

        Returns:
            List of RepoStats
        """
        results = []
        for repo in repos:
            stats = self.get_repo_stats(repo)
            results.append(stats)
        return results

    def search_repos(
        self, 
        query: str, 
        sort: str = "stars", 
        limit: int = 10
    ) -> List[RepoStats]:
        """
        Search GitHub repositories.

        Args:
            query: Search query
            sort: Sort by (stars, forks, updated)
            limit: Maximum number of results

        Returns:
            List of RepoStats
        """
        logger.info(f"Searching repos: {query}")

        try:
            url = f"{self.base_url}/search/repositories"
            params = {
                "q": query,
                "sort": sort,
                "per_page": limit,
            }

            with httpx.Client(headers=self.headers, timeout=10.0) as client:
                response = client.get(url, params=params)
                
                if response.status_code != 200:
                    logger.error(f"Search failed: {response.status_code}")
                    return []

                data = response.json()

            results = []
            for item in data.get("items", []):
                stats = RepoStats(
                    name=item["name"],
                    full_name=item["full_name"],
                    owner=item["owner"]["login"],
                    description=item.get("description"),
                    stars=item["stargazers_count"],
                    forks=item["forks_count"],
                    watchers=item["watchers_count"],
                    open_issues=item["open_issues_count"],
                    language=item.get("language"),
                    created_at=datetime.fromisoformat(item["created_at"].replace("Z", "+00:00")),
                    updated_at=datetime.fromisoformat(item["updated_at"].replace("Z", "+00:00")),
                    pushed_at=datetime.fromisoformat(item["pushed_at"].replace("Z", "+00:00")),
                    size=item["size"],
                    license=item["license"]["name"] if item.get("license") else None,
                    topics=item.get("topics", []),
                    is_fork=item["fork"],
                    is_archived=item["archived"],
                    default_branch=item["default_branch"],
                )
                stats.calculate_metrics()
                results.append(stats)

            return results

        except Exception as e:
            logger.error(f"Search failed: {e}")
            return []

    def _create_error_stats(self, repo: str, error: str) -> RepoStats:
        """Create RepoStats for error cases."""
        owner = repo.split("/")[0] if "/" in repo else "unknown"
        name = repo.split("/")[1] if "/" in repo else repo
        
        now = datetime.utcnow()
        
        return RepoStats(
            name=name,
            full_name=repo,
            owner=owner,
            description=None,
            stars=0,
            forks=0,
            watchers=0,
            open_issues=0,
            language=None,
            created_at=now,
            updated_at=now,
            pushed_at=now,
            size=0,
            license=None,
            topics=[],
            is_fork=False,
            is_archived=False,
            default_branch="main",
            error=error,
        )
