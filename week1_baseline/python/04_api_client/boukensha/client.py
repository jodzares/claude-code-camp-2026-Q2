import json
import socket
import ssl
import time
import urllib.error
import urllib.request

from .errors import ApiError


class Client:
    RETRYABLE_STATUS_CODES = {408, 409, 429, 500, 502, 503, 504}
    TRANSIENT_ERRORS = (
        urllib.error.URLError,
        TimeoutError,
        ConnectionError,
        ssl.SSLError,
        EOFError,
        socket.gaierror,
    )
    MAX_RETRIES = 3
    BASE_RETRY_DELAY = 0.5
    TIMEOUT = 30

    def __init__(self, builder):
        self._builder = builder

    def call(self, max_output_tokens=1024):
        body = json.dumps(self._builder.to_api_payload(max_output_tokens)).encode("utf-8")
        request = urllib.request.Request(
            self._builder.url(),
            data=body,
            headers=self._builder.headers(),
            method="POST",
        )

        attempts = 0
        status = None
        response_body = None

        while True:
            attempts += 1

            try:
                # HTTPError MUST be caught before TRANSIENT_ERRORS. HTTPError is a
                # subclass of URLError, which is itself one of the transient errors
                # below — if URLError were checked first, it would also match every
                # HTTPError, so every non-2xx response would be misclassified as a
                # transient network failure instead of reaching the status-code
                # check below.
                with urllib.request.urlopen(request, timeout=self.TIMEOUT) as resp:
                    status = resp.status
                    response_body = resp.read().decode("utf-8")
            except urllib.error.HTTPError as e:
                # Records status and body only — does not retry here. Whether this
                # status is retryable is decided once, below, after both the
                # success path and this path have converged.
                status = e.code
                response_body = e.read().decode("utf-8")
            except self.TRANSIENT_ERRORS as e:
                if attempts > self.MAX_RETRIES:
                    raise ApiError(
                        f"API request failed after {attempts} attempts: {type(e).__name__}: {e}"
                    ) from e
                time.sleep(self._retry_delay(attempts))
                continue

            if status in self.RETRYABLE_STATUS_CODES and attempts <= self.MAX_RETRIES:
                time.sleep(self._retry_delay(attempts))
                continue

            break

        if not (200 <= status < 300):
            plural = "" if attempts == 1 else "s"
            raise ApiError(f"API request failed after {attempts} attempt{plural} ({status}): {response_body}")

        return json.loads(response_body)

    def _retry_delay(self, attempt):
        return self.BASE_RETRY_DELAY * (2 ** (attempt - 1))
