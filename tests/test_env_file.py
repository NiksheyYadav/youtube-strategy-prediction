from src.env_file import load_env_file, parse_env_text


def test_parse_handles_comments_quotes_export_and_junk_lines():
    text = """
# a comment
LLM_MODEL=qwen2.5:7b
export GOOGLE_CLIENT_ID="abc 123"
GOOGLE_REDIRECT_URI='http://localhost:8501/'
LLM_TIMEOUT_S=120   # raise on slow CPUs
EMPTY=
not a setting
1BAD=x
"""
    values = parse_env_text(text)
    assert values == {
        "LLM_MODEL": "qwen2.5:7b",
        "GOOGLE_CLIENT_ID": "abc 123",
        "GOOGLE_REDIRECT_URI": "http://localhost:8501/",
        "LLM_TIMEOUT_S": "120",
        "EMPTY": "",
    }


def test_real_environment_wins_and_empty_values_are_skipped(tmp_path):
    path = tmp_path / ".env"
    path.write_text("LLM_MODEL=from_file\nLLM_TIMEOUT_S=99\nEMPTY=\n", encoding="utf-8")
    environ = {"LLM_MODEL": "from_environment"}
    applied = load_env_file(path, environ)
    assert environ == {"LLM_MODEL": "from_environment", "LLM_TIMEOUT_S": "99"}
    assert applied == ["LLM_TIMEOUT_S"]


def test_missing_file_is_not_an_error(tmp_path):
    environ: dict[str, str] = {}
    assert load_env_file(tmp_path / "nope.env", environ) == []
    assert environ == {}


def test_bom_from_windows_editors_is_ignored(tmp_path):
    path = tmp_path / ".env"
    path.write_bytes(b"\xef\xbb\xbfLLM_MODEL=qwen2.5:3b\n")
    environ: dict[str, str] = {}
    load_env_file(path, environ)
    assert environ == {"LLM_MODEL": "qwen2.5:3b"}
