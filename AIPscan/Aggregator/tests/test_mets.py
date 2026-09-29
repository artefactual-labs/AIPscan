"""Tests for METS helper functions."""

import os

import metsrw
import pytest

from AIPscan.Aggregator import mets_parse_helpers

FIXTURES_DIR = "fixtures"


@pytest.mark.parametrize(
    "fixture_path, transfer_name, package_uuid, directory_name",
    [
        (
            os.path.join("features_mets", "features-mets.xml"),
            "myTransfer",
            "ab793f82-27b0-4c2e-ac3e-621bab5af8f1",
            "0A-74220a00-b06d-4a60-ab96-90573d1ef2de",
        ),
        (
            os.path.join("iso_mets", "iso_mets.xml"),
            "iso",
            "4e625930-08c8-4cb7-8a5f-d3957cb7cf71",
            "iso",
        ),
        (
            os.path.join("original_name_mets", "document-empty-dirs.xml"),
            "empty-dirs",
            "97f78cc1-e6fd-483d-a139-18f633bc865c",
            "empty-dirs",
        ),
        # METSRW cannot disambiguate dmdSec_1, but the root label is usable.
        (
            os.path.join("original_name_mets", "dataverse_example.xml"),
            "dataverse",
            "e10369a1-a485-4001-8967-33c18e1ab142",
            "dataverse",
        ),
        (
            os.path.join("legacy_mets", "production-aip-mets-file.xml"),
            "easy_1488911181",
            "80f077d8-2a6f-49e2-9327-903c36d6d92d",
            "easy_1488911181",
        ),
    ],
)
def test_get_aip_original_name(
    fixture_path, transfer_name, package_uuid, directory_name
):
    """Make sure that we can reliably get original name from the METS
    file given we haven't any mets-reader-writer helpers.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    mets_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)
    mets = metsrw.METSDocument.fromfile(mets_file)
    assert mets_parse_helpers.get_aip_original_name(mets, package_uuid) == transfer_name
    # Test the same works with a string.
    with open(mets_file, "rb") as mets_stream:
        mets = metsrw.METSDocument.fromstring(mets_stream.read())
    assert mets_parse_helpers.get_aip_original_name(mets, package_uuid) == transfer_name
    # Use that string to manipulate the text so that the element cannot
    # be found.
    with open(mets_file, "rb") as mets_stream:
        # With no PREMIS name, the physical structure map supplies the name.
        new_mets = mets_stream.read()
        new_mets = new_mets.replace(b"originalName", b"originalNameIsNotHere")
        mets = metsrw.METSDocument.fromstring(new_mets)
        assert (
            mets_parse_helpers.get_aip_original_name(mets, package_uuid)
            == directory_name
        )


LEGACY_UUID = "80f077d8-2a6f-49e2-9327-903c36d6d92d"


@pytest.mark.parametrize(
    "label, expected",
    [
        (f"easy_1488911181-{LEGACY_UUID}", "easy_1488911181"),
        ("a-name-without-a-uuid", "a-name-without-a-uuid"),
        (
            "another-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
            "another-aaaaaaaa-aaaa-4aaa-8aaa-aaaaaaaaaaaa",
        ),
    ],
)
def test_legacy_aip_name(label, expected):
    path = os.path.join(
        os.path.dirname(__file__),
        FIXTURES_DIR,
        "legacy_mets",
        "production-aip-mets-file.xml",
    )
    with open(path, "rb") as stream:
        xml = stream.read().replace(
            f"easy_1488911181-{LEGACY_UUID}".encode(), label.encode()
        )
    mets = metsrw.METSDocument.fromstring(xml)
    assert mets_parse_helpers.get_aip_original_name(mets, LEGACY_UUID) == expected


def test_legacy_name_requires_one_package_directory():
    mets = metsrw.METSDocument()
    mets.append(metsrw.FSEntry(label="one", type="Directory"))
    mets.append(metsrw.FSEntry(label="two", type="Directory"))
    with pytest.raises(mets_parse_helpers.METSError):
        mets_parse_helpers.get_aip_original_name(mets, LEGACY_UUID)


@pytest.mark.parametrize("label", [None, "", f"-{LEGACY_UUID}"])
def test_legacy_name_without_usable_label(label):
    mets = metsrw.METSDocument()
    mets.append(metsrw.FSEntry(label=label, type="Directory"))
    with pytest.raises(mets_parse_helpers.METSError):
        mets_parse_helpers.get_aip_original_name(mets, LEGACY_UUID)
