# Performance Guide

Comprehensive guide to understanding and optimizing performance in Beginnings applications.

## Performance Overview

Beginnings is built on FastAPI, inheriting its high-performance characteristics while adding configuration-driven enhancements and extension capabilities. This guide covers performance characteristics, optimization strategies, and monitoring techniques.

## Performance Characteristics

### Framework Overhead

Beginnings adds minimal overhead to FastAPI:

- **Configuration loading**: ~10-50ms at startup (depending on complexity)
- **Extension loading**: ~5-20ms per extension at startup  
- **Route registration**: ~1-5ms per route with middleware chains
- **Request processing**: ~0.1-1ms additional per request for middleware

### Baseline Performance

On modern hardware (4-core CPU, 8GB RAM):

```
Metric                    | Development | Production
--------------------------|-------------|------------
Startup time             | 100-500ms   | 50-200ms
Memory usage (base)      | 50-100MB    | 30-80MB
Requests/second (simple) | 8,000-15,000| 12,000-25,000
Requests/second (complex)| 2,000-5,000 | 4,000-10,000
Response time (P95)      | <10ms       | <5ms
```

*Performance varies based on application complexity, extensions, and hardware.*

## Optimization Strategies

### Configuration Optimization

#### Minimize Configuration Complexity

```yaml
# Efficient configuration
routes:
  global_defaults:
    timeout: 30
  patterns:
    "/api/*": 
      cors_enabled: true
    "/admin/*":
      auth_required: true

# Avoid excessive patterns
routes:
  patterns:
    "/api/v1/users/*": {}
    "/api/v1/posts/*": {}
    "/api/v1/comments/*": {}
    # Better: use "/api/v1/*" for common settings
```

#### Use Specific Patterns

```yaml
# Efficient: specific patterns
routes:
  patterns:
    "/api/public/*":     # Specific scope
      rate_limit: 1000
    "/api/admin/*":      # Specific scope  
      auth_required: true

# Inefficient: overly broad patterns
routes:
  patterns:
    "/*":               # Matches everything
      some_setting: true
```

#### Optimize Include Files

```yaml
# Efficient: logical grouping
include:
  - "core.yaml"        # Essential settings
  - "extensions.yaml"  # Extension config

# Inefficient: many small files
include:
  - "auth.yaml"
  - "cors.yaml"
  - "logging.yaml"
  - "rate_limit.yaml"
  # Better: combine related settings
```

### Extension Optimization

#### Lightweight Extensions

```python
class EfficientExtension(BaseExtension):
    def __init__(self, config):
        super().__init__(config)
        # Pre-compute expensive operations
        self.compiled_patterns = [re.compile(p) for p in config.get("patterns", [])]
        self.enabled = config.get("enabled", True)
    
    def get_middleware_factory(self):
        # Return early if disabled
        if not self.enabled:
            return lambda route_config: lambda endpoint: endpoint
            
        def middleware_factory(route_config):
            # Pre-check applicability
            if not self._applies_to_route(route_config):
                return lambda endpoint: endpoint
                
            def middleware(endpoint):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    # Minimal processing
                    return await endpoint(*args, **kwargs)
                return wrapper
            return middleware
        return middleware_factory
    
    def should_apply_to_route(self, path, methods, route_config):
        # Fast path for disabled extension
        if not self.enabled:
            return False
        return self._applies_to_route(route_config)
    
    def _applies_to_route(self, route_config):
        # Cache-friendly applicability check
        return route_config.get("feature_enabled", False)
```

#### Extension Caching

```python
class CachedExtension(BaseExtension):
    def __init__(self, config):
        super().__init__(config)
        self._middleware_cache = {}
        self._applicability_cache = {}
    
    def get_middleware_factory(self):
        def middleware_factory(route_config):
            # Cache middleware instances
            config_key = self._get_config_key(route_config)
            if config_key not in self._middleware_cache:
                self._middleware_cache[config_key] = self._create_middleware(route_config)
            return self._middleware_cache[config_key]
        return middleware_factory
    
    def should_apply_to_route(self, path, methods, route_config):
        # Cache applicability decisions
        cache_key = (path, tuple(methods), self._get_config_key(route_config))
        if cache_key not in self._applicability_cache:
            self._applicability_cache[cache_key] = self._check_applicability(path, methods, route_config)
        return self._applicability_cache[cache_key]
```

### Routing Optimization

#### Efficient Route Organization

```python
# Efficient: group related routes
api_router = app.create_api_router(prefix="/api/v1")

@api_router.get("/users")
async def list_users(): pass

@api_router.get("/users/{user_id}")
async def get_user(user_id: int): pass

@api_router.post("/users")
async def create_user(user: UserCreate): pass

app.include_router(api_router)

# Less efficient: scattered individual routes
@app.get("/api/v1/users")
async def list_users(): pass

@app.get("/api/v1/posts")  
async def list_posts(): pass
```

#### Route Configuration Caching

```python
from functools import lru_cache

class OptimizedRouteResolver:
    def __init__(self, config):
        self.config = config
        self._compiled_patterns = self._compile_patterns()
    
    @lru_cache(maxsize=1000)
    def resolve_route_config(self, path: str, method: str):
        """Cached route configuration resolution"""
        return self._resolve_config_internal(path, method)
    
    def _compile_patterns(self):
        """Pre-compile regex patterns for performance"""
        patterns = {}
        for pattern, config in self.config.get("routes", {}).get("patterns", {}).items():
            patterns[re.compile(pattern)] = config
        return patterns
```

### Database Optimization

#### Connection Pooling

```python
class DatabaseExtension(BaseExtension):
    def __init__(self, config):
        super().__init__(config)
        self.engine = create_engine(
            config["url"],
            pool_size=config.get("pool_size", 20),      # Adequate pool
            max_overflow=config.get("max_overflow", 10), # Handle spikes
            pool_pre_ping=True,                          # Connection health
            pool_recycle=3600,                          # Recycle connections
            echo=config.get("echo", False)              # Disable in production
        )
```

#### Query Optimization

```python
# Efficient: eager loading
users = session.query(User).options(
    joinedload(User.profile),
    joinedload(User.permissions)
).all()

# Efficient: specific fields
users = session.query(User.id, User.name, User.email).all()

# Inefficient: N+1 queries
for user in users:
    print(user.profile.bio)  # Triggers individual query
```

### Memory Optimization

#### Configuration Memory Management

```python
class MemoryEfficientApp(App):
    def get_config(self):
        """Return view instead of deep copy for read-only access"""
        if self._read_only_config is None:
            import copy
            self._read_only_config = copy.deepcopy(self._config)
        return self._read_only_config
    
    def _clear_config_cache(self):
        """Clear cached configuration when reloading"""
        self._read_only_config = None
```

#### Extension Memory Management

```python
class MemoryEfficientExtension(BaseExtension):
    def __init__(self, config):
        super().__init__(config)
        # Use __slots__ to reduce memory overhead
        __slots__ = ['name', 'enabled', '_compiled_patterns']
        
        # Store only necessary data
        self.name = config.get("name", self.__class__.__name__)
        self.enabled = config.get("enabled", True)
        
        # Avoid storing full config
        patterns = config.get("patterns", [])
        self._compiled_patterns = [re.compile(p) for p in patterns]
```

## Monitoring and Profiling

### Performance Monitoring Extension

```python
import time
from collections import defaultdict
from typing import Any, Callable
from beginnings.extensions.base import BaseExtension

class PerformanceMonitorExtension(BaseExtension):
    def __init__(self, config: dict[str, Any]):
        super().__init__(config)
        self.name = config.get("name", "PerformanceMonitor")
        self.enabled = config.get("enabled", True)
        self.sample_rate = config.get("sample_rate", 0.1)  # 10% sampling
        
        # Metrics storage
        self.request_times = defaultdict(list)
        self.request_counts = defaultdict(int)
        self.error_counts = defaultdict(int)
    
    def get_middleware_factory(self):
        def middleware_factory(route_config: dict[str, Any]):
            def performance_middleware(endpoint: Callable):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    if not self.enabled or random.random() > self.sample_rate:
                        return await endpoint(*args, **kwargs)
                    
                    endpoint_name = endpoint.__name__
                    start_time = time.time()
                    
                    try:
                        result = await endpoint(*args, **kwargs)
                        
                        # Record successful request
                        duration = time.time() - start_time
                        self.request_times[endpoint_name].append(duration)
                        self.request_counts[endpoint_name] += 1
                        
                        return result
                        
                    except Exception as e:
                        # Record error
                        self.error_counts[endpoint_name] += 1
                        raise
                        
                return wrapper
            return performance_middleware
        return middleware_factory
    
    def should_apply_to_route(self, path: str, methods: list[str], route_config: dict[str, Any]) -> bool:
        return self.enabled and route_config.get("monitoring_enabled", True)
    
    def get_metrics(self):
        """Get performance metrics"""
        metrics = {}
        
        for endpoint, times in self.request_times.items():
            if times:
                metrics[endpoint] = {
                    "count": len(times),
                    "avg_time": sum(times) / len(times),
                    "min_time": min(times),
                    "max_time": max(times),
                    "p95_time": sorted(times)[int(len(times) * 0.95)] if len(times) > 0 else 0,
                    "errors": self.error_counts.get(endpoint, 0)
                }
        
        return metrics
```

### Application Metrics Endpoint

```python
@app.get("/metrics")
async def get_metrics():
    """Performance metrics endpoint"""
    perf_monitor = app.get_extension("PerformanceMonitorExtension")
    if not perf_monitor:
        return {"error": "Performance monitoring not enabled"}
    
    metrics = perf_monitor.get_metrics()
    return {
        "timestamp": time.time(),
        "endpoints": metrics,
        "summary": {
            "total_requests": sum(m.get("count", 0) for m in metrics.values()),
            "total_errors": sum(m.get("errors", 0) for m in metrics.values()),
            "avg_response_time": sum(m.get("avg_time", 0) for m in metrics.values()) / len(metrics) if metrics else 0
        }
    }
```

### Profiling Tools

#### Memory Profiling

```python
import tracemalloc
from beginnings.extensions.base import BaseExtension

class MemoryProfilerExtension(BaseExtension):
    def get_startup_handler(self):
        async def startup():
            if self.config.get("enabled", False):
                tracemalloc.start()
                print("Memory profiling started")
        return startup
    
    def get_shutdown_handler(self):
        async def shutdown():
            if tracemalloc.is_tracing():
                current, peak = tracemalloc.get_traced_memory()
                print(f"Memory usage: {current / 1024 / 1024:.1f} MB current, {peak / 1024 / 1024:.1f} MB peak")
                tracemalloc.stop()
        return shutdown
```

#### Request Profiling

```python
import cProfile
import pstats
from io import StringIO

class RequestProfilerExtension(BaseExtension):
    def get_middleware_factory(self):
        def middleware_factory(route_config):
            def profiling_middleware(endpoint):
                @functools.wraps(endpoint)
                async def wrapper(*args, **kwargs):
                    if not route_config.get("profile_enabled", False):
                        return await endpoint(*args, **kwargs)
                    
                    # Profile the request
                    profiler = cProfile.Profile()
                    profiler.enable()
                    
                    try:
                        result = await endpoint(*args, **kwargs)
                        return result
                    finally:
                        profiler.disable()
                        
                        # Print profiling results
                        s = StringIO()
                        ps = pstats.Stats(profiler, stream=s)
                        ps.sort_stats('cumulative').print_stats(20)
                        print(f"Profile for {endpoint.__name__}:")
                        print(s.getvalue())
                        
                return wrapper
            return profiling_middleware
        return middleware_factory
```

## Performance Testing

### Load Testing Setup

```python
# test_performance.py
import asyncio
import aiohttp
import time
from statistics import mean, median

async def load_test(url: str, concurrent_requests: int = 100, total_requests: int = 1000):
    """Simple load test"""
    semaphore = asyncio.Semaphore(concurrent_requests)
    response_times = []
    
    async def make_request(session):
        async with semaphore:
            start = time.time()
            try:
                async with session.get(url) as response:
                    await response.read()
                    response_times.append(time.time() - start)
                    return response.status
            except Exception as e:
                print(f"Request failed: {e}")
                return 0
    
    async with aiohttp.ClientSession() as session:
        tasks = [make_request(session) for _ in range(total_requests)]
        results = await asyncio.gather(*tasks)
    
    successful = len([r for r in results if r == 200])
    failed = total_requests - successful
    
    if response_times:
        print(f"Results:")
        print(f"  Successful requests: {successful}")
        print(f"  Failed requests: {failed}")
        print(f"  Average response time: {mean(response_times):.3f}s")
        print(f"  Median response time: {median(response_times):.3f}s")
        print(f"  Min response time: {min(response_times):.3f}s")
        print(f"  Max response time: {max(response_times):.3f}s")
        print(f"  Requests per second: {total_requests / sum(response_times):.1f}")

# Run load test
if __name__ == "__main__":
    asyncio.run(load_test("http://localhost:8000/health"))
```

### Benchmark Configuration

```yaml
# config/benchmark.yaml
app:
  debug: false
  
routes:
  global_defaults:
    timeout: 30
    
extensions:
  # Minimal extensions for benchmarking
  "performance.monitor:PerformanceMonitorExtension":
    enabled: true
    sample_rate: 0.01  # 1% sampling for minimal overhead
```

## Production Optimization

### Deployment Configuration

```yaml
# config/app.yaml (production)
app:
  debug: false
  workers: 4                    # Match CPU cores
  
templates:
  auto_reload: false           # Disable template reloading
  
static:
  directories:
    - url_path: "/static"
      directory: "static"
      cache_control: "public, max-age=86400"  # Aggressive caching
      gzip: true               # Enable compression

extensions:
  # Production-optimized extensions only
  "auth:AuthExtension":
    enabled: true
    cache_tokens: true         # Enable token caching
    
  "cors:CORSExtension":
    enabled: true
    cache_preflight: true      # Cache preflight responses
```

### Server Configuration

```bash
# Use production ASGI server
gunicorn main:app \
  --worker-class uvicorn.workers.UvicornWorker \
  --workers 4 \
  --max-requests 1000 \
  --max-requests-jitter 100 \
  --timeout 30 \
  --bind 0.0.0.0:8000

# Or use uvicorn with multiple workers
uvicorn main:app \
  --workers 4 \
  --host 0.0.0.0 \
  --port 8000 \
  --no-access-log \
  --loop uvloop
```

### Operating System Tuning

```bash
# Increase file descriptor limits
ulimit -n 65536

# Optimize TCP settings
echo 'net.core.somaxconn = 65536' >> /etc/sysctl.conf
echo 'net.ipv4.tcp_max_syn_backlog = 65536' >> /etc/sysctl.conf
echo 'net.core.netdev_max_backlog = 5000' >> /etc/sysctl.conf

# Apply settings
sysctl -p
```

## Performance Best Practices

### Configuration
1. **Minimize pattern complexity** - Use specific patterns over broad wildcards
2. **Combine related settings** - Reduce number of include files
3. **Cache compiled patterns** - Pre-compile regex patterns at startup
4. **Use environment-specific configs** - Optimize for each deployment environment

### Extensions
1. **Fast path for disabled extensions** - Return early when disabled
2. **Cache middleware instances** - Avoid recreating middleware repeatedly  
3. **Minimize memory allocations** - Use object pools and caching
4. **Profile extension overhead** - Measure impact on request processing

### Database
1. **Use connection pooling** - Configure appropriate pool sizes
2. **Optimize queries** - Use eager loading and specific field selection
3. **Cache frequently accessed data** - Implement application-level caching
4. **Monitor query performance** - Track slow queries and optimize

### Monitoring
1. **Use sampling** - Monitor subset of requests to reduce overhead
2. **Aggregate metrics** - Collect metrics efficiently without blocking requests
3. **Set up alerts** - Monitor key performance indicators
4. **Regular performance testing** - Establish performance baselines

This performance guide provides comprehensive coverage of optimization strategies, monitoring techniques, and best practices for maintaining high-performance Beginnings applications.