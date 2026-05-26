"""
Analytics Tracker
==================
Tracks and stores analytics data:
- Query counts and patterns
- Evaluation metric trends
- Agent performance metrics
- Latency tracking
- Token usage monitoring
- Error tracking
"""

import json
from collections import defaultdict
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

from app.utils.logger import get_logger

logger = get_logger("analytics.tracker")

ANALYTICS_FILE = Path("./logs/analytics.jsonl")


class AnalyticsTracker:
    """
    In-memory analytics tracker with file persistence.
    Stores request/response analytics for the dashboard.
    """

    def __init__(self):
        self._events: List[Dict[str, Any]] = []
        self._agent_stats: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            "total_calls": 0,
            "total_latency_ms": 0.0,
            "errors": 0,
        })
        # Load existing analytics
        self._load_events()

    def record_query(
        self,
        session_id: str,
        query: str,
        mode: str,
        response_length: int,
        confidence_score: float,
        evaluation_metrics: Dict[str, float],
        latency_ms: float,
        reflection_iterations: int,
        num_sources: int,
        tokens_used: int = 0,
        error: Optional[str] = None,
    ) -> None:
        """Record a complete query-response event."""
        event = {
            "timestamp": datetime.utcnow().isoformat(),
            "session_id": session_id,
            "query_preview": query[:80],
            "mode": mode,
            "response_length": response_length,
            "confidence_score": confidence_score,
            "evaluation_metrics": evaluation_metrics,
            "latency_ms": latency_ms,
            "reflection_iterations": reflection_iterations,
            "num_sources": num_sources,
            "tokens_used": tokens_used,
            "error": error,
            "success": error is None,
        }

        self._events.append(event)

        # Persist to file
        try:
            ANALYTICS_FILE.parent.mkdir(parents=True, exist_ok=True)
            with open(ANALYTICS_FILE, "a") as f:
                f.write(json.dumps(event) + "\n")
        except Exception as e:
            logger.warning(f"Failed to persist analytics event: {e}")

    def record_agent_call(
        self,
        agent_name: str,
        latency_ms: float,
        success: bool,
    ) -> None:
        """Record individual agent performance."""
        stats = self._agent_stats[agent_name]
        stats["total_calls"] += 1
        stats["total_latency_ms"] += latency_ms
        if not success:
            stats["errors"] += 1

    def get_dashboard_data(self, days: int = 7) -> Dict[str, Any]:
        """
        Compile analytics dashboard data.

        Args:
            days: Number of days to include in trends

        Returns:
            Dashboard data dict
        """
        cutoff = datetime.utcnow() - timedelta(days=days)
        recent_events = [
            e for e in self._events
            if self._parse_ts(e["timestamp"]) > cutoff
        ]

        # Basic stats
        total_queries = len(recent_events)
        successful = [e for e in recent_events if e.get("success")]

        avg_confidence = (
            sum(e["confidence_score"] for e in successful) / len(successful)
            if successful else 0.0
        )
        avg_latency = (
            sum(e["latency_ms"] for e in successful) / len(successful)
            if successful else 0.0
        )
        eval_pass_count = sum(
            1 for e in recent_events
            if e.get("evaluation_metrics", {}).get("overall_score", 0) >= 0.7
        )
        eval_pass_rate = eval_pass_count / total_queries if total_queries > 0 else 0.0

        # Daily counts
        daily_counts = defaultdict(int)
        for e in recent_events:
            date = e["timestamp"][:10]
            daily_counts[date] += 1

        daily_query_counts = [
            {"date": d, "count": c}
            for d, c in sorted(daily_counts.items())
        ]

        # Evaluation trends (daily averages)
        daily_metrics: Dict[str, List[Dict]] = defaultdict(list)
        for e in recent_events:
            if e.get("evaluation_metrics"):
                date = e["timestamp"][:10]
                daily_metrics[date].append(e["evaluation_metrics"])

        evaluation_trends = []
        for date in sorted(daily_metrics.keys()):
            day_metrics = daily_metrics[date]
            n = len(day_metrics)
            evaluation_trends.append({
                "date": date,
                "faithfulness": sum(m.get("faithfulness", 0) for m in day_metrics) / n,
                "relevance": sum(m.get("relevance", 0) for m in day_metrics) / n,
                "precision": sum(m.get("precision", 0) for m in day_metrics) / n,
                "overall": sum(m.get("overall_score", 0) for m in day_metrics) / n,
            })

        # Agent performance
        agent_performance = []
        for agent_name, stats in self._agent_stats.items():
            total = stats["total_calls"]
            if total > 0:
                agent_performance.append({
                    "agent_name": agent_name,
                    "total_calls": total,
                    "avg_latency_ms": stats["total_latency_ms"] / total,
                    "error_rate": stats["errors"] / total,
                    "success_rate": 1.0 - (stats["errors"] / total),
                })

        # Top modes/topics
        mode_counts = defaultdict(int)
        for e in recent_events:
            mode_counts[e.get("mode", "chat")] += 1

        top_topics = [
            {"mode": m, "count": c}
            for m, c in sorted(mode_counts.items(), key=lambda x: x[1], reverse=True)
        ]

        return {
            "total_queries": total_queries,
            "avg_confidence_score": round(avg_confidence, 4),
            "avg_latency_ms": round(avg_latency, 1),
            "evaluation_pass_rate": round(eval_pass_rate, 4),
            "evaluation_trends": evaluation_trends[-7:],  # Last 7 days
            "agent_performance": agent_performance,
            "top_topics": top_topics,
            "daily_query_counts": daily_query_counts[-7:],
        }

    def _parse_ts(self, ts_str: str) -> datetime:
        """Parse ISO timestamp string."""
        try:
            return datetime.fromisoformat(ts_str.replace("Z", ""))
        except Exception:
            return datetime.min

    def _load_events(self) -> None:
        """Load persisted analytics events from file."""
        if not ANALYTICS_FILE.exists():
            return
        try:
            with open(ANALYTICS_FILE, "r") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            self._events.append(json.loads(line))
                        except json.JSONDecodeError:
                            continue
            # Keep only last 10,000 events
            self._events = self._events[-10000:]
            logger.info(f"Loaded {len(self._events)} analytics events")
        except Exception as e:
            logger.warning(f"Could not load analytics: {e}")
