# -*- coding: utf-8 -*-

"""Tests for METS helper functions."""

import os

import metsrw
import pytest

from AIPscan.Aggregator import mets_parse_helpers

FIXTURES_DIR = "fixtures"


@pytest.mark.parametrize(
    "fixture_path, transfer_name, mets_error",
    [
        (os.path.join("features_mets", "features-mets.xml"), "myTransfer", False),
        (os.path.join("iso_mets", "iso_mets.xml"), "iso", False),
        (
            os.path.join("original_name_mets", "document-empty-dirs.xml"),
            "empty-dirs",
            False,
        ),
        # Exception: Cannot disambiguate dmdSec_1 in the METS using
        # mets-reader-writer and so we cannot retrieve the originalName.
        (os.path.join("original_name_mets", "dataverse_example.xml"), "", True),
    ],
)
def test_get_aip_original_name(fixture_path, transfer_name, mets_error):
    """Make sure that we can reliably get original name from the METS
    file given we haven't any mets-reader-writer helpers.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    mets_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)
    mets = metsrw.METSDocument.fromfile(mets_file)
    if mets_error:
        # Function should raise an error to work with.
        with pytest.raises(mets_parse_helpers.METSError):
            _ = mets_parse_helpers.get_aip_original_name(mets)
        return
    assert mets_parse_helpers.get_aip_original_name(mets) == transfer_name
    # Test the same works with a string.
    with open(mets_file, "rb") as mets_stream:
        mets = metsrw.METSDocument.fromstring(mets_stream.read())
        assert mets_parse_helpers.get_aip_original_name(mets) == transfer_name
    # Use that string to manipulate the text so that the element cannot
    # be found.
    with open(mets_file, "rb") as mets_stream:
        # Remove originalName and test for an appropriate side-effect.
        new_mets = mets_stream.read()
        new_mets = new_mets.replace(b"originalName", b"originalNameIsNotHere")
        mets = metsrw.METSDocument.fromstring(new_mets)
        # Function should raise an error to work with.
        with pytest.raises(mets_parse_helpers.METSError):
            _ = mets_parse_helpers.get_aip_original_name(mets) == transfer_name


# MOBBING STUB: We're gonna flesh out these tests!
@pytest.mark.parametrize(
    "fixture_path, transfer_name, mets_error",
    [
        (os.path.join("original_name_mets", "dataverse_example.xml"), "", True),
    ],
)
def test_corrupt_mets_file(fixture_path, transfer_name, mets_error):
    """We need a docstring to describe this test."""
    # Where are we?
    script_dir = os.path.dirname(os.path.realpath(__file__))

    # Create an absolute path from our relative location.
    mets_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)

    # Read the mets in from the file.
    mets = metsrw.METSDocument.fromfile(mets_file)

    try:
        myvar = mets_parse_helpers.get_aip_original_name(mets)
    except mets_parse_helpers.METSError:
        return True
