from nse_agentic_trader.config import Settings
from nse_agentic_trader.config_tools import init_env_file, settings_lines


def test_settings_lines_masks_secrets():
    settings = Settings(angel_api_key="secret", angel_password="pw")

    lines = settings_lines(settings)
    rendered = "\n".join(lines)

    assert "angel_api_key: secret" not in rendered
    assert "angel_password: pw" not in rendered
    assert "angel_api_key: ***set***" in rendered
    assert "live_orders_enabled: False" in rendered


def test_init_env_file_copies_example_without_overwriting(tmp_path):
    example = tmp_path / ".env.example"
    env = tmp_path / ".env"
    example.write_text("TRADING_MODE=paper\n", encoding="utf-8")

    message = init_env_file(example, env)
    second = init_env_file(example, env)

    assert "Created" in message
    assert env.read_text(encoding="utf-8") == "TRADING_MODE=paper\n"
    assert "already exists" in second
