import pytest

from AIPscan.helpers import filesizeformat


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
