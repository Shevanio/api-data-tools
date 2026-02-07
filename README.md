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
CURL on steroids with beautiful output and comprehensive features.

**Features:**
- HTTP methods (GET, POST, PUT, PATCH, DELETE, HEAD, OPTIONS)
- Multiple authentication methods (Bearer, Basic, API Key)
- Custom headers support
- Request body (JSON or raw text)
- Query parameters
- Response formatting with syntax highlighting
- Status code visualization (color-coded)
- Response time measurement
- Follow redirects option
- SSL verification control
- Timeout configuration
- Verbose mode for debugging

**Usage:**
```bash
# Simple GET request
api-test GET https://api.github.com/users/octocat

# POST with JSON body
api-test POST https://api.example.com/users \
  --data '{"name": "John", "email": "john@example.com"}' \
  --header "Content-Type: application/json"

# With Bearer auth
api-test GET https://api.example.com/protected \
  --auth bearer --token YOUR_TOKEN

# With query parameters
api-test GET https://api.example.com/search \
  --param "q=python" --param "limit=10"

# Verbose output
api-test GET https://api.example.com/data --verbose
```

**Status:** ✅ Complete

---

### 2. **JSON/YAML/TOML Converter** (`data-convert`)
Transform, validate, and query JSON/YAML/TOML files.

**Features:**
- Bidirectional format conversion (JSON ↔ YAML ↔ TOML)
- Auto-format detection from file extension
- JMESPath querying for JSON data
- Pretty printing with syntax highlighting
- Minification (JSON only)
- File or stdin input
- File or stdout output
- Error handling with user-friendly messages

**Usage:**
```bash
# Convert JSON to YAML
data-convert config.json --to yaml

# Convert YAML to JSON
data-convert config.yaml --to json --output config.json

# Query JSON with JMESPath
data-convert data.json --query 'users[0].name'

# Minify JSON
data-convert large.json --minify

# Pretty print
data-convert minified.json --pretty

# Convert from stdin
cat config.json | data-convert --from json --to yaml
```

**Status:** ✅ Complete

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
- Automatic schema inference from CSV data
- Intelligent type detection (INTEGER, TEXT, REAL, BOOLEAN)
- Custom table names
- Multiple database dialects (PostgreSQL, MySQL, SQLite)
- Batch inserts for performance (configurable batch size)
- Handle NULL values and empty strings
- Schema-only mode
- Data-only mode (skip CREATE TABLE)
- Syntax highlighting for SQL output
- File or stdout output

**Usage:**
```bash
# Generate CREATE TABLE + INSERTs
csv2sql users.csv --table users --output users.sql

# PostgreSQL dialect
csv2sql data.csv --dialect postgresql --output data.sql

# Schema only
csv2sql large-file.csv --schema-only

# Data only (skip CREATE TABLE)
csv2sql data.csv --table users --data-only

# Batch inserts (500 rows per statement)
csv2sql data.csv --batch-size 500 --output inserts.sql

# SQLite dialect
csv2sql contacts.csv --dialect sqlite --table contacts
```

**Status:** ✅ Complete

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

- [x] Project setup and structure ✅
- [x] Webhook Receiver MVP ✅
- [x] Data Converter MVP ✅
- [x] GitHub Stats MVP ✅
- [x] API Tester MVP ✅
- [x] CSV to SQL MVP ✅
- [ ] Integration testing suite
- [ ] Published pip package
- [ ] Web dashboard for Webhook Receiver

**🎉 All 5 core tools complete! (100%)**

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
