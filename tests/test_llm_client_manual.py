import agents.llm_client as llm_client_module
from agents.llm_client import (
    GeminiClient,
    LLMResponseParseError,
    parse_json_response,
)


class FakeInteraction:
    def __init__(self, output_text):
        self.output_text = output_text


class FakeGeminiAPI:
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    class Interactions:
        def __init__(self, parent):
            self.parent = parent

        def create(self, **kwargs):
            self.parent.calls += 1

            response = self.parent.responses.pop(0)

            if isinstance(response, Exception):
                raise response

            return FakeInteraction(response)

    @property
    def interactions(self):
        return self.Interactions(self)


def make_client(fake_api):
    client = object.__new__(GeminiClient)
    client.client = fake_api
    client.model = "fake-model"
    return client


def test_transient_failure_retries_then_succeeds():
    fake_api = FakeGeminiAPI(
        [
            RuntimeError("503 service unavailable"),
            '{"status": "ok"}',
        ]
    )

    client = make_client(fake_api)

    original_sleep = llm_client_module.time.sleep
    llm_client_module.time.sleep = lambda _: None

    try:
        result = client.complete("system", "user")
    finally:
        llm_client_module.time.sleep = original_sleep

    assert result == '{"status": "ok"}'
    assert fake_api.calls == 2

    print("Transient failure retry test passed.")

def test_transient_failure_then_success_on_last_retry():
    fake_api = FakeGeminiAPI(
        [
            RuntimeError("503 service unavailable"),
            RuntimeError("503 service unavailable"),
            '{"status": "ok"}',
        ]
    )

    client = make_client(fake_api)

    original_sleep = llm_client_module.time.sleep
    llm_client_module.time.sleep = lambda _: None

    try:
        result = client.complete("system", "user")
    finally:
        llm_client_module.time.sleep = original_sleep

    assert result == '{"status": "ok"}'
    assert fake_api.calls == 3

    print("Last-attempt retry success test passed.")


def test_exhausted_transient_failures_raise_runtime_error():
    fake_api = FakeGeminiAPI(
        [
            RuntimeError("503 service unavailable"),
            RuntimeError("503 service unavailable"),
            RuntimeError("503 service unavailable"),
        ]
    )

    client = make_client(fake_api)

    original_sleep = llm_client_module.time.sleep
    llm_client_module.time.sleep = lambda _: None

    try:
        try:
            client.complete("system", "user")
        except RuntimeError as exc:
            message = str(exc)
        else:
            raise AssertionError(
                "Expected RuntimeError after all retry attempts."
            )
    finally:
        llm_client_module.time.sleep = original_sleep

    assert "failed after 3 attempts" in message
    assert fake_api.calls == 3

    print("Exhausted retry test passed.")


def test_non_retryable_failure_does_not_retry():
    fake_api = FakeGeminiAPI(
        [
            RuntimeError("400 invalid argument"),
            '{"status": "should not happen"}',
        ]
    )

    client = make_client(fake_api)

    try:
        client.complete("system", "user")
    except RuntimeError as exc:
        message = str(exc)
    else:
        raise AssertionError(
            "Expected RuntimeError for non-retryable failure."
        )

    assert "non-retryable error" in message
    assert fake_api.calls == 1

    print("Non-retryable failure test passed.")


def test_malformed_json_raises_custom_parse_error():
    try:
        parse_json_response('{"status": ')
    except LLMResponseParseError as exc:
        assert "not valid JSON" in str(exc)
    else:
        raise AssertionError(
            "Expected LLMResponseParseError for malformed JSON."
        )

    print("Malformed JSON parse test passed.")


def test_valid_json_still_parses():
    result = parse_json_response(
        '```json\n{"status": "supported"}\n```'
    )

    assert result == {"status": "supported"}

    print("Valid JSON parse test passed.")


if __name__ == "__main__":
    test_transient_failure_retries_then_succeeds()
    test_transient_failure_then_success_on_last_retry()
    test_exhausted_transient_failures_raise_runtime_error()
    test_non_retryable_failure_does_not_retry()
    test_malformed_json_raises_custom_parse_error()
    test_valid_json_still_parses()

    print("LLM client robustness test passed.")