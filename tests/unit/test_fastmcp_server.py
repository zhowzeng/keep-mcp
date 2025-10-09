from keep_mcp.fastmcp_server import create_fastmcp


def test_create_fastmcp_uses_host_and_port() -> None:
    server = create_fastmcp(host="0.0.0.0", port=9001)
    assert server.settings.host == "0.0.0.0"
    assert server.settings.port == 9001
