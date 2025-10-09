from keep_mcp.cli import parse_args


def test_parse_args_serve_defaults() -> None:
    args = parse_args(["serve"])
    assert args.command == "serve"
    assert args.transport == "stdio"
    assert args.host == "127.0.0.1"
    assert args.port == 8000
    assert args.mount_path is None


def test_parse_args_serve_sse_options() -> None:
    args = parse_args(
        [
            "serve",
            "--transport",
            "sse",
            "--host",
            "0.0.0.0",
            "--port",
            "9000",
            "--mount-path",
            "/mcp",
        ]
    )
    assert args.command == "serve"
    assert args.transport == "sse"
    assert args.host == "0.0.0.0"
    assert args.port == 9000
    assert args.mount_path == "/mcp"
