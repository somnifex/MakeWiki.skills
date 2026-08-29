"""Tests for MultiLanguageSourceExtractor."""

from pathlib import Path

from makewiki_skills.toolkit.source_extractor import MultiLanguageSourceExtractor


def test_extract_go_flags_and_routes(tmp_path: Path):
    go_file = tmp_path / "main.go"
    go_file.write_text(
        """package main

import (
    "flag"
    "github.com/gin-gonic/gin"
)

// StartServer starts the main web server on the configured port.
func StartServer(port int) error {
    return nil
}

func main() {
    port := flag.Int("port", 3000, "Port to listen on")
    host := flag.String("host", "0.0.0.0", "Bind address")
    flag.Parse()

    r := gin.Default()
    r.GET("/api/status", nil)
    r.POST("/v1/chat/completions", nil)
}
""",
        encoding="utf-8",
    )

    extractor = MultiLanguageSourceExtractor()
    facts = extractor.extract_from_file(go_file)

    flag_names = {f.name for f in facts if f.symbol_type == "cli_flag"}
    assert "--port" in flag_names
    assert "--host" in flag_names

    routes = {f.name for f in facts if f.symbol_type == "api_route"}
    assert "GET /api/status" in routes
    assert "POST /v1/chat/completions" in routes

    funcs = {f.name for f in facts if f.symbol_type == "exported_func"}
    assert "StartServer" in funcs


def test_extract_rust_clap_and_routes(tmp_path: Path):
    rs_file = tmp_path / "main.rs"
    rs_file.write_text(
        """use clap::Parser;
use axum::{routing::get, Router};

/// Launch the gateway application service.
pub async fn run_app() {
}

#[derive(Parser)]
struct Args {
    #[arg(short, long, help = "Server listening address")]
    listen_addr: String,
}

fn router() -> Router {
    Router::new().route("/health", get(health_check))
}
""",
        encoding="utf-8",
    )

    extractor = MultiLanguageSourceExtractor()
    facts = extractor.extract_from_file(rs_file)

    flag_names = {f.name for f in facts if f.symbol_type == "cli_flag"}
    assert "--listen-addr" in flag_names

    routes = {f.name for f in facts if f.symbol_type == "api_route"}
    assert any("/health" in r for r in routes)

    funcs = {f.name for f in facts if f.symbol_type == "exported_func"}
    assert "run_app" in funcs
