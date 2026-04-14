# sample-cli

A sample Python CLI tool for testing MakeWiki documentation generation.

## Installation

```bash
pip install -e .
```

## Usage

```bash
sample-cli greet World
sample-cli serve --port 9090
```

## Configuration

Create a `config.yaml` file:

```yaml
server:
  host: 127.0.0.1
  port: 8080
debug: false
```