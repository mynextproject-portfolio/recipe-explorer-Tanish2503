"""
Prometheus metrics instrumentation for Recipe Explorer.

Tracks cache performance, API usage patterns, and recipe popularity.
All metrics are thread-safe and use prometheus_client's built-in locking.
"""

from prometheus_client import Counter, Histogram, Gauge

# Cache performance metrics
cache_hits = Counter(
    "cache_hits_total",
    "Total cache hits by operation",
    ["operation"],  # "search" or "lookup"
)

cache_misses = Counter(
    "cache_misses_total",
    "Total cache misses by operation",
    ["operation"],  # "search" or "lookup"
)

cache_hit_rate = Gauge(
    "cache_hit_rate",
    "Cache hit rate (0-1) by operation",
    ["operation"],
)

# Query performance metrics
query_duration_ms = Histogram(
    "query_duration_ms",
    "Query duration in milliseconds",
    ["source"],  # "internal" or "external"
    buckets=(5, 10, 25, 50, 100, 250, 500, 1000),
)

# Recipe popularity: how often each recipe is searched for
recipe_search_frequency = Counter(
    "recipe_searches_total",
    "Total searches by recipe (internal database)",
    ["recipe_id"],
)

# Search volume tracking
search_queries_total = Counter(
    "search_queries_total",
    "Total search queries",
    ["source"],  # "internal", "external", or "combined"
)

# External API metrics
external_api_calls = Counter(
    "external_api_calls_total",
    "Total external API calls by operation and status",
    ["operation", "status"],  # operation: "search" or "lookup", status: "success" or "error"
)

external_api_errors = Counter(
    "external_api_errors_total",
    "Total external API errors by operation",
    ["operation", "error_type"],  # error_type: "timeout", "http_error", "unreachable", etc.
)

# Database metrics
db_operations = Counter(
    "db_operations_total",
    "Total database operations by type",
    ["operation"],  # "get", "search", "create", "update", "delete", "import"
)

db_operation_duration_ms = Histogram(
    "db_operation_duration_ms",
    "Database operation duration in milliseconds",
    ["operation"],
    buckets=(1, 5, 10, 25, 50, 100, 250),
)

# HTTP metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests by method, endpoint, and status",
    ["method", "endpoint", "status"],
)

http_request_duration_ms = Histogram(
    "http_request_duration_ms",
    "HTTP request duration in milliseconds",
    ["method", "endpoint"],
    buckets=(10, 25, 50, 100, 250, 500, 1000),
)
