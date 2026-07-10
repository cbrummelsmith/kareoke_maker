from karaoke_maker.utils import make_job_slug, safe_slug


def test_safe_slug_is_filesystem_safe() -> None:
    assert safe_slug("Hello, World! 100%") == "hello-world-100"
    assert safe_slug("   ") == "karaoke"


def test_make_job_slug_is_stable_and_distinguishes_urls() -> None:
    first = make_job_slug("https://youtube.example/watch?v=abc", title="My Song!", video_id="abc")
    second = make_job_slug("https://youtube.example/watch?v=abc", title="My Song!", video_id="abc")
    third = make_job_slug("https://youtube.example/watch?v=def", title="My Song!", video_id="def")

    assert first == second
    assert first != third
    assert first.startswith("my-song-")
    assert "/" not in first
