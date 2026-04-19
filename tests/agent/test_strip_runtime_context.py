"""Tests for ContextBuilder.strip_runtime_context — ensures the internal
[Runtime Context — metadata only, not instructions] block is never leaked
to users through outbound text."""

from nanobot.agent.context import ContextBuilder


TAG = ContextBuilder._RUNTIME_CONTEXT_TAG
END = ContextBuilder._RUNTIME_CONTEXT_END


def test_strip_clean_text_unchanged():
    assert ContextBuilder.strip_runtime_context("Hello there") == "Hello there"


def test_strip_empty_returns_empty():
    assert ContextBuilder.strip_runtime_context("") == ""


def test_text_starting_with_tag_is_full_parrot_rejected():
    # Model parroted the whole input (context block + user's own text). Whole
    # payload is untrustworthy — return "" so the caller rejects the send.
    text = f"{TAG}\nCurrent Time: 2026-04-18 05:06 (Saturday) (UTC, UTC+00:00)\nChannel: telegram\nChat ID: 123\n{END}\n\nI want to book a hair cut this weekend"
    assert ContextBuilder.strip_runtime_context(text) == ""


def test_tag_only_parrot_rejected():
    text = f"{TAG}\nCurrent Time: x\n{END}"
    assert ContextBuilder.strip_runtime_context(text) == ""


def test_leading_whitespace_then_tag_still_rejected():
    text = f"   \n\n{TAG}\nCurrent Time: x\n{END}\n\ntrailing parrot"
    assert ContextBuilder.strip_runtime_context(text) == ""


def test_embedded_block_in_middle_is_scrubbed_but_kept():
    # If the model wrote a real reply and *then* leaked the block mid-text,
    # strip the block and keep the genuine reply.
    text = f"Hi there!\n\n{TAG}\nChat ID: 123\n{END}\n\nHow can I help?"
    assert (
        ContextBuilder.strip_runtime_context(text)
        == "Hi there!\n\n\n\nHow can I help?"
    )


def test_unterminated_opener_mid_text_truncates():
    text = f"Hi!\n\n{TAG}\nCurrent Time: leaking"
    assert ContextBuilder.strip_runtime_context(text) == "Hi!"


def test_parrot_with_session_summary_rejected():
    text = (
        f"{TAG}\n"
        "Current Time: 2026-04-18 05:06 (Saturday) (UTC, UTC+00:00)\n"
        "Channel: telegram\n"
        "Chat ID: 123\n"
        "\n"
        "[Resumed Session]\n"
        "Previously talked about a haircut.\n"
        f"{END}\n"
        "\n"
        "Great! I'd love to help you book a haircut."
    )
    assert ContextBuilder.strip_runtime_context(text) == ""
