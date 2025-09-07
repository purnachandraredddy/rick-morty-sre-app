# Rick and Morty SRE Application API Documentation

## Overview

The Rick and Morty SRE Application provides a RESTful API that filters and serves character data from the Rick and Morty universe. The API focuses on human characters that are alive and originate from any Earth variant.

## Base URL

```
https://rick-morty-api.example.com
```

## Authentication

Currently, the API does not require authentication. Rate limiting is applied to all endpoints.

## Rate Limiting

- **Default Rate Limit**: 100 requests per minute per IP address
- **Health Check**: 10 requests per minute per IP address
- **Sync Endpoint**: 1 request per minute per IP address

Rate limit headers are included in all responses:
- `X-RateLimit-Limit`: The rate limit ceiling for the given endpoint
- `X-RateLimit-Remaining`: The number of requests left for the time window
- `X-RateLimit-Reset`: The remaining window before the rate limit resets

## Endpoints

### GET /characters

Retrieve filtered Rick and Morty characters.

**Filters Applied:**
- Species: Human
- Status: Alive
- Origin: Earth (any variant, e.g., Earth (C-137), Earth (Replacement Dimension))

#### Query Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| `page` | integer | 1 | Page number (minimum: 1) |
| `per_page` | integer | 20 | Items per page (1-100) |
| `sort` | string | "id" | Sort field (`id`, `name`, `created_at`) |
| `order` | string | "asc" | Sort order (`asc`, `desc`) |

#### Example Request

```bash
curl "https://rick-morty-api.example.com/characters?page=1&per_page=10&sort=name&order=asc"
```

#### Example Response

```json
{
  "characters": [
    {
      "id": 1,
      "name": "Rick Sanchez",
      "status": "Alive",
      "species": "Human",
      "origin_name": "Earth (C-137)",
      "image_url": "https://rickandmortyapi.com/api/character/avatar/1.jpeg",
      "created_at": "2023-01-01T12:00:00.000Z"
    }
  ],
  "pagination": {
    "page": 1,
    "per_page": 10,
    "total": 150,
    "total_pages": 15,
    "has_next": true,
    "has_prev": false
  }
}
```

#### Response Status Codes

- `200 OK`: Success
- `400 Bad Request`: Invalid query parameters
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### GET /characters/{character_id}

Retrieve a specific character by ID.

#### Path Parameters

| Parameter | Type | Description |
|-----------|------|-------------|
| `character_id` | integer | Character ID (minimum: 1) |

#### Example Request

```bash
curl "https://rick-morty-api.example.com/characters/1"
```

#### Example Response

```json
{
  "id": 1,
  "name": "Rick Sanchez",
  "status": "Alive",
  "species": "Human",
  "origin_name": "Earth (C-137)",
  "image_url": "https://rickandmortyapi.com/api/character/avatar/1.jpeg",
  "created_at": "2023-01-01T12:00:00.000Z"
}
```

#### Response Status Codes

- `200 OK`: Success
- `400 Bad Request`: Invalid character ID
- `404 Not Found`: Character not found
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### GET /stats

Get character statistics and application metrics.

#### Example Request

```bash
curl "https://rick-morty-api.example.com/stats"
```

#### Example Response

```json
{
  "total_characters": 150,
  "species_breakdown": {
    "Human": 150
  },
  "status_breakdown": {
    "Alive": 150
  },
  "last_sync": "2023-01-01T12:00:00.000Z"
}
```

#### Response Status Codes

- `200 OK`: Success
- `429 Too Many Requests`: Rate limit exceeded
- `500 Internal Server Error`: Server error

---

### GET /healthcheck

Health check endpoint with deep health checks.

#### Example Request

```bash
curl "https://rick-morty-api.example.com/healthcheck"
```

#### Example Response (Healthy)

```json
{
  "status": "healthy",
  "timestamp": "2023-01-01T12:00:00.000Z",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "healthy",
      "message": "Database connection successful"
    },
    "cache": {
      "status": "healthy",
      "connected": true,
      "memory_usage": "1.2M",
      "connected_clients": 5,
      "uptime": 3600
    },
    "rick_morty_api": {
      "status": "healthy",
      "total_characters": 826,
      "pages": 42,
      "api_url": "https://rickandmortyapi.com/api"
    },
    "data": {
      "status": "healthy",
      "total_characters": 150,
      "last_sync": "2023-01-01T12:00:00.000Z"
    }
  }
}
```

#### Example Response (Unhealthy)

```json
{
  "status": "unhealthy",
  "timestamp": "2023-01-01T12:00:00.000Z",
  "version": "1.0.0",
  "checks": {
    "database": {
      "status": "unhealthy",
      "message": "Database connection failed: Connection timeout"
    },
    "cache": {
      "status": "unhealthy",
      "error": "Connection refused",
      "connected": false
    },
    "rick_morty_api": {
      "status": "healthy",
      "total_characters": 826,
      "pages": 42,
      "api_url": "https://rickandmortyapi.com/api"
    },
    "data": {
      "status": "unhealthy",
      "message": "Data check failed: No database connection"
    }
  }
}
```

#### Response Status Codes

- `200 OK`: Service is healthy or degraded
- `503 Service Unavailable`: Service is unhealthy
- `429 Too Many Requests`: Rate limit exceeded

---

### POST /sync

Manually trigger character synchronization from the Rick and Morty API.

#### Example Request

```bash
curl -X POST "https://rick-morty-api.example.com/sync"
```

#### Example Response

```json
{
  "message": "Synchronization started",
  "status": "in_progress"
}
```

#### Response Status Codes

- `200 OK`: Sync started successfully
- `429 Too Many Requests`: Rate limit exceeded (max 1 per minute)
- `500 Internal Server Error`: Server error

---

### GET /metrics

Prometheus metrics endpoint for monitoring and alerting.

#### Example Request

```bash
curl "https://rick-morty-api.example.com/metrics"
```

#### Example Response

```
# HELP http_requests_total Total number of HTTP requests
# TYPE http_requests_total counter
http_requests_total{method="GET",endpoint="/characters",status_code="200"} 1234

# HELP http_request_duration_seconds HTTP request duration in seconds
# TYPE http_request_duration_seconds histogram
http_request_duration_seconds_bucket{method="GET",endpoint="/characters",le="0.1"} 1000
http_request_duration_seconds_bucket{method="GET",endpoint="/characters",le="0.25"} 1100
...
```

#### Response Status Codes

- `200 OK`: Success

---

## Error Responses

All error responses follow a consistent format:

```json
{
  "error": "Error message",
  "detail": "Detailed error information (optional)",
  "timestamp": "2023-01-01T12:00:00.000Z"
}
```

## Common HTTP Status Codes

| Code | Meaning |
|------|---------|
| 200 | OK - Request successful |
| 400 | Bad Request - Invalid request parameters |
| 404 | Not Found - Resource not found |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Server error |
| 503 | Service Unavailable - Service is unhealthy |

## SDKs and Examples

### Python Example

```python
import requests

# Get characters
response = requests.get("https://rick-morty-api.example.com/characters")
data = response.json()

for character in data["characters"]:
    print(f"{character['name']} from {character['origin_name']}")

# Health check
health = requests.get("https://rick-morty-api.example.com/healthcheck")
print(f"Service status: {health.json()['status']}")
```

### JavaScript Example

```javascript
// Get characters
fetch('https://rick-morty-api.example.com/characters')
  .then(response => response.json())
  .then(data => {
    data.characters.forEach(character => {
      console.log(`${character.name} from ${character.origin_name}`);
    });
  });

// Health check
fetch('https://rick-morty-api.example.com/healthcheck')
  .then(response => response.json())
  .then(health => {
    console.log(`Service status: ${health.status}`);
  });
```

### cURL Examples

```bash
# Get first page of characters
curl "https://rick-morty-api.example.com/characters"

# Get characters sorted by name
curl "https://rick-morty-api.example.com/characters?sort=name&order=asc"

# Get specific character
curl "https://rick-morty-api.example.com/characters/1"

# Check health
curl "https://rick-morty-api.example.com/healthcheck"

# Get statistics
curl "https://rick-morty-api.example.com/stats"

# Trigger sync
curl -X POST "https://rick-morty-api.example.com/sync"
```

## Monitoring and Observability

The API exposes comprehensive metrics for monitoring:

- **Request Metrics**: Rate, latency, error rates by endpoint
- **Business Metrics**: Character counts, sync operations
- **Infrastructure Metrics**: Database connections, cache hit rates
- **External API Metrics**: Rick and Morty API response times and errors

Access the Grafana dashboard for visual monitoring and the Prometheus metrics endpoint for raw metrics.

## Support

For issues or questions about the API, please refer to the main repository documentation or contact the SRE team.
