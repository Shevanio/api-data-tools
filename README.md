# 📊 API & Data Tools

> Professional CLI utilities for API testing, data transformation, and developer workflows.

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

## 🎯 Why This Exists

Modern development involves constant interaction with APIs and data formats. These tools eliminate friction in common workflows:
- Testing APIs without Postman
- Converting data between formats
- Debugging webhooks locally
- Analyzing GitHub repositories
- Generating SQL from CSVs

**Fast. Reliable. CLI-first.**

---

## 🛠️ Available Tools

### 1. **API Tester CLI** (`api-test`)
CURL on steroids with collections, variables, and history.

**Features:**
- HTTP methods (GET, POST, PUT, PATCH, DELETE)
- Headers and authentication (Bearer, Basic, API Key)
- Request body templates
- Environment variables
- Request history
- Response formatting (JSON, XML, HTML)
- Collection support (like Postman)

**Usage:**
```bash
# Simple GET request
api-test GET https://api.github.com/users/octocat

# POST with JSON body
api-test POST https://api.example.com/users \
  --data '{"name": "John", "email": "john@example.com"}' \
  --header "Authorization: Bearer TOKEN"

# Load from collection
api-test run --collection my-api.json --env production

# View history
api-test history --last 10
```

**Status:** 📋 Planned

---

### 2. **JSON/YAML Converter** (`data-convert`)
Transform, validate, and query JSON/YAML/TOML files.

**Features:**
- Format conversion (JSON ↔ YAML ↔ TOML)
- JSON Schema validation
- JQ-style querying
- Pretty printing
- Minification
- Batch processing

**Usage:**
```bash
# Convert JSON to YAML
data-convert config.json --to yaml

# Query JSON
data-convert data.json --query '.users[0].name'

# Validate against schema
data-convert api-response.json --validate schema.json

# Pretty print
data-convert minified.json --pretty
```

**Status:** 📋 Planned

---

### 3. **Webhook Receiver** (`webhook-recv`)
Local server to receive, inspect, and debug webhooks.

**Features:**
- HTTP server on configurable port
- Real-time webhook display
- Request logging (headers, body, query params)
- Parser presets (GitHub, Stripe, Slack, etc.)
- Event filtering
- Mock response configuration
- ngrok integration for public URLs
- Web dashboard

**Usage:**
```bash
# Start receiver on port 3000
webhook-recv --port 3000

# With GitHub parser
webhook-recv --port 3000 --parser github

# Public URL via ngrok
webhook-recv --port 3000 --public

# Mock responses
webhook-recv --port 3000 --mock-response '{"status": "ok"}'
```

**Status:** 🚧 In Development (MVP)

---

### 4. **CSV to SQL Converter** (`csv2sql`)
Generate SQL schemas and INSERT statements from CSV files.

**Features:**
- Automatic schema inference
- Type detection (INT, VARCHAR, DATE, etc.)
- Custom table names
- Multiple database dialects (PostgreSQL, MySQL, SQLite)
- Batch inserts for performance
- Handle NULL values
- Primary key detection

**Usage:**
```bash
# Generate CREATE TABLE + INSERTs
csv2sql users.csv --table users --output users.sql

# PostgreSQL dialect
csv2sql data.csv --dialect postgresql --output data.sql

# Schema only
csv2sql large-file.csv --schema-only

# Batch inserts (1000 rows per statement)
csv2sql data.csv --batch-size 1000
```

**Status:** 📋 Planned

---

### 5. **GitHub Stats Fetcher** (`gh-stats`)
Analyze GitHub repositories and extract metrics using GitHub API.

**Features:**
- Repository statistics (stars, forks, watchers, issues)
- Growth metrics (stars per day)
- Top contributors with contributions
- Language breakdown with visual bars
- Repository comparison (side-by-side)
- Search repositories with filters
- Multiple output formats (rich tables, JSON)
- Authenticated API support (rate limit: 5000/hour)

**Usage:**
```bash
# Get repo stats
gh-stats --repo facebook/react

# Compare repos
gh-stats --repo facebook/react --repo vuejs/vue --compare

# Show contributors
gh-stats --repo torvalds/linux --contributors --limit 20

# Language breakdown
gh-stats --repo python/cpython --languages

# Search repos
gh-stats --search "machine learning" --sort stars --limit 10

# JSON output
gh-stats --repo nodejs/node --output json
```

**Status:** 🚧 Complete (MVP)

---

## 🚀 Installation

### Prerequisites
- Python 3.9 or higher
- pip
- (Optional) GitHub CLI for gh-stats

### Install from source

```bash
# Clone the repository
git clone https://github.com/Shevanio/api-data-tools.git
cd api-data-tools

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install in development mode
pip install -e .
```

### Install via pip (future)

```bash
pip install api-data-tools
```

---

## 📖 Documentation

Detailed documentation for each tool is available in the [`docs/`](docs/) directory:

- [API Tester Guide](docs/api-tester.md)
- [Data Converter Guide](docs/json-converter.md)
- [Webhook Receiver Guide](docs/webhook-receiver.md)
- [CSV to SQL Guide](docs/csv-to-sql.md)
- [GitHub Stats Guide](docs/github-stats.md)

---

## 🧪 Development

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=tools --cov-report=html

# Run specific tool tests
pytest tests/test_webhook_receiver.py -v
```

### Code Quality

```bash
# Format code
black .

# Lint
ruff check .

# Type checking
mypy tools/
```

---

## 🤝 Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) for details.

### Quick Start for Contributors

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/api-enhancement`)
3. Make your changes
4. Add tests (coverage must be >70%)
5. Run quality checks (`black .`, `pytest`, `ruff check .`)
6. Commit (`git commit -m 'Add API enhancement'`)
7. Push (`git push origin feature/api-enhancement`)
8. Open a Pull Request

---

## 💡 Integration Ideas

These tools are designed to work well together:

```bash
# Receive webhook -> Parse JSON -> Convert to SQL
webhook-recv --port 3000 | data-convert --to json | csv2sql --output webhook-data.sql

# Fetch GitHub stats -> Export CSV -> Analyze
gh-stats --repo popular/project --export data.csv
```

---

## 📊 Project Roadmap

- [x] Project setup and structure
- [x] Webhook Receiver MVP (Phase 1) ✅
- [x] Data Converter MVP (Phase 1) ✅
- [x] GitHub Stats MVP (Phase 1) ✅
- [ ] API Tester MVP (Phase 2)
- [ ] CSV to SQL MVP (Phase 2)
- [ ] Integration testing suite
- [ ] Published pip package
- [ ] Web dashboard for Webhook Receiver

---

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 🙏 Acknowledgments

- Inspired by tools like jq, curl, Postman, and httpie
- Built for API-first development workflows
- Community feedback drives features

---

## 📧 Contact

For questions, issues, or suggestions:
- Open an issue on GitHub
- Join the discussions

**Build better APIs.** 🚀
