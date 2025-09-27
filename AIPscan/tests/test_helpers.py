import hashlib

import pytest

from AIPscan.helpers import filesizeformat
from AIPscan.helpers import stream_write_and_hash


@pytest.mark.parametrize(
    "byte_size,binary,expected_result",
    [
        # Test non-binary results.
        (100, False, "100 Bytes"),
        (1000, False, "1.0 kB"),
        (1000000, False, "1.0 MB"),
        (1000000000, False, "1.0 GB"),
        (1000000000000, False, "1.0 TB"),
        # Test binary results.
        (100, True, "100 Bytes"),
        (1000, True, "1000 Bytes"),
        (1000000, True, "976.6 KiB"),
        (1000000000, True, "953.7 MiB"),
        (1000000000000, True, "931.3 GiB"),
        # Test real-life values.
        (396245, False, "396.2 kB"),
        (396245, True, "387.0 KiB"),
        (125121042160, False, "125.1 GB"),
        (125121042160, True, "116.5 GiB"),
    ],
)
def test_filesizeformat(byte_size, binary, expected_result):
    assert filesizeformat(byte_size, binary=binary) == expected_result


class _FakeStreamingResponse:
    def __init__(self, chunks):
        self._chunks = chunks

    def iter_content(self, chunk_size=None):
        yield from self._chunks


def test_stream_write_and_hash(tmp_path):
    payload = b"test payload for mets file"
    chunks = [payload[:5], payload[5:-1], payload[-1:], b""]
    response = _FakeStreamingResponse(chunks)

    destination = tmp_path / "mets.xml"

    digest = stream_write_and_hash(response, destination)

    assert destination.read_bytes() == payload
    assert digest == hashlib.sha256(payload).hexdigest()


def test_stream_write_and_hash_with_iterable(tmp_path):
    payload = b"chunked bytes"
    chunks = [payload[:6], payload[6:]]

    destination = tmp_path / "payload.bin"

    digest = stream_write_and_hash(chunks, destination)

    assert destination.read_bytes() == payload
    assert digest == hashlib.sha256(payload).hexdigest()
