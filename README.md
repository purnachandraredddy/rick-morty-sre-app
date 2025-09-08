# Rick and Morty SRE Application

Hey there! This is a production-ready REST API that pulls character data from the Rick and Morty API. I built this to showcase some solid SRE and DevOps practices while having a bit of fun with interdimensional data.

## What Does This Thing Do?

Pretty simple - it filters Rick and Morty characters to only show you the humans who are still alive and from some version of Earth. Because let's face it, keeping track of dead aliens from dimension C-500A gets confusing real quick.

The filtering criteria:
- Must be human (sorry, Mr. Poopybutthole)
- Must be alive (RIP Bird Person)
- Must be from Earth (any variant works - C-137, Replacement Dimension, whatever)

## The Tech Stack

I went with a pretty standard but battle-tested setup:

- **FastAPI** for the backend (because who has time for slow APIs?)
- **PostgreSQL** for persistent storage
- **Redis** for caching (the Rick and Morty API has rate limits, and we respect that)
- **Kubernetes** for orchestration
- **Prometheus + Grafana** for monitoring (gotta know when things break)
- **GitHub Actions** for CI/CD

## Getting Started

### Running Locally (The Easy Way)

If you just want to see this thing in action:

```bash
# Clone the repo
git clone <repository-url>
cd rick-morty-sre-app

# Fire up Docker Compose
docker-compose up -d

# Check if it's alive
curl http://localhost:8000/healthcheck

# Get some characters
curl http://localhost:8000/characters
```

That's it. Docker Compose will spin up the app, Postgres, and Redis for you.

### For Python Developers

Want to hack on the code directly? Here's how:

```bash
# Set up your virtual environment (you ARE using venvs, right?)
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Set up your environment
cp env.example .env
# Edit .env with your settings

# Run it
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Deploying to Kubernetes

Got a cluster? Cool, let's deploy:

```bash
# The quick and dirty way
helm install rick-morty-app ./helm/rick-morty-app \
  --namespace rick-morty-app --create-namespace

# Port forward to test it
kubectl port-forward service/rick-morty-app 8080:80 -n rick-morty-app
curl http://localhost:8080/healthcheck
```

For production, you'll want to use external databases and set up proper ingress:

```bash
helm install rick-morty-prod ./helm/rick-morty-app \
  --namespace rick-morty-prod --create-namespace \
  --set postgresql.enabled=false \
  --set redis.enabled=false \
  --set secrets.databaseUrl="$DATABASE_URL" \
  --set secrets.redisUrl="$REDIS_URL" \
  --set ingress.hosts[0].host="rick-morty-api.yourdomain.com"
```

## API Endpoints

Here's what you can hit:

- `GET /characters` - Get all the filtered characters (paginated, because we're not barbarians)
- `GET /characters/{id}` - Get a specific character
- `GET /stats` - Some fun statistics about the data
- `GET /healthcheck` - Is this thing on?
- `GET /metrics` - Prometheus metrics
- `POST /sync` - Force a data refresh (rate limited because we're nice to the upstream API)

### Example Requests

```bash
# Get page 2 with 20 results per page
curl "http://localhost:8000/characters?page=2&per_page=20"

# Sort by name (because alphabetical order matters)
curl "http://localhost:8000/characters?sort=name&order=asc"

# Get Rick's details
curl "http://localhost:8000/characters/1"
```

## Architecture Overview

Nothing too fancy here. We've got:

1. **FastAPI app** that handles requests
2. **PostgreSQL** stores the character data
3. **Redis** caches responses (because hitting the Rick and Morty API repeatedly is rude)
4. **Kubernetes** keeps everything running with auto-scaling
5. **Prometheus/Grafana** tells us when things go wrong
6. **GitHub Actions** deploys our code

The app periodically syncs with the Rick and Morty API to keep data fresh. If the external API is down, we gracefully degrade to serving cached/stored data.

## Development

### Running Tests

We've got decent test coverage:

```bash
# Run everything
pytest

# Just unit tests (fast)
pytest tests/unit/

# Integration tests (slower, needs database)
pytest tests/integration/

# Generate a coverage report
pytest --cov=app --cov-report=html
# Then open htmlcov/index.html in your browser
```

### Code Quality

I'm a bit obsessive about clean code:

```bash
# Format with black (non-negotiable)
black app/ tests/

# Sort imports
isort app/ tests/

# Lint
flake8 app/ tests/

# Type checking
mypy app/

# Or just run everything at once
./scripts/quality-check.sh
```

### Load Testing

Want to see how much traffic this can handle?

```bash
# Install locust if you haven't
pip install locust

# Run load tests
locust -f tests/load/locustfile.py --host=http://localhost:8000
# Then open http://localhost:8089 in your browser
```

## Monitoring

### What We Track

- **Golden signals**: Latency, traffic, errors, saturation (the classics)
- **Business metrics**: How many characters we're serving, sync success rates
- **Infrastructure**: CPU, memory, the usual suspects

### Alerts That Actually Matter

We alert on stuff that needs immediate attention:

- Error rate > 5% for 5 minutes (something's broken)
- P95 latency > 500ms (users are suffering)
- Pods crash looping (deployment probably failed)
- Can't reach the database (this is bad)

Everything else just goes to Slack for someone to look at during business hours.

### Our SLOs

We aim for:
- 99.9% uptime (about 9 hours downtime per year)
- P95 latency under 500ms
- Less than 1% error rate
- Support for 1000 requests per second

So far, so good!

## Project Structure

Here's how everything is organized:

```
rick-morty-sre-app/
├── app/                   # The actual application code
├── tests/                 # All the tests
├── helm/                  # Helm charts for K8s deployment
├── k8s/                   # Raw Kubernetes manifests (if you're into that)
├── monitoring/            # Grafana dashboards and alert rules
├── scripts/               # Helpful scripts for deployment and such
├── docs/                  # More documentation
├── .github/workflows/     # CI/CD pipeline
├── docker-compose.yml     # Local dev environment
├── Dockerfile            # How we build the container
└── requirements.txt      # Python dependencies
```

## CI/CD Pipeline

Every push triggers our pipeline:

1. Linting and tests run first
2. If tests pass, we build a Docker image
3. Security scanning on the image
4. Deploy to the appropriate environment:
   - `main` branch → production
   - `develop` branch → staging
   - Pull requests → review apps
5. Smoke tests run after deployment

It's all in `.github/workflows/ci-cd.yml` if you want to peek under the hood.

## Contributing

Found a bug? Want to add a feature? Awesome! Here's how:

1. Fork the repo
2. Create a feature branch (`git checkout -b feature/cool-new-thing`)
3. Write your code (and tests!)
4. Push and open a PR

Just make sure:
- Your code passes the linter (run `black` and `flake8`)
- Tests are green
- You've updated docs if you changed the API

## A Few Notes

This started as a weekend project to practice some SRE concepts, but it's grown into something I'm actually pretty proud of. The Rick and Morty API is fantastic for this kind of thing - it's reliable, well-documented, and who doesn't love Rick and Morty?

If you're using this to learn, here are the interesting bits:
- Check out `app/rick_morty_client.py` for retry logic and circuit breakers
- The caching strategy in `app/cache.py` is pretty neat
- The Helm chart has some good examples of production K8s patterns

## Questions? Issues?

Hit me up! Open an issue on GitHub or find me on the company Slack (#rick-morty-sre-app). 

If something's broken and you need help ASAP, check the runbooks in `docs/runbooks/` first - they might have your answer.

## Thanks

Big shout-out to the folks who maintain the [Rick and Morty API](https://rickandmortyapi.com/). You're doing the Lord's work.

Also thanks to my team for the code reviews and for putting up with my Rick and Morty references in every standup.

---

*"Sometimes science is more art than science, Morty. A lot of people don't get that."* - Rick Sanchez

Built with coffee and too many late nights by the SRE Team.