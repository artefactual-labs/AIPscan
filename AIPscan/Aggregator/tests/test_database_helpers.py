# -*- coding: utf-8 -*-

import os

import metsrw
import pytest

from AIPscan.Aggregator import database_helpers

FIXTURES_DIR = "fixtures"


@pytest.mark.parametrize(
    "fixture_path, event_count",
    [
        (os.path.join("features_mets", "features-mets.xml"), 0),
        (os.path.join("iso_mets", "iso_mets.xml"), 17),
        (os.path.join("images_mets", "images.xml"), 76),
    ],
)
def test_event_creation(fixture_path, event_count, mocker):
    """Make sure that we're seeing all of the events associated with
    an AIP and that they are potentially written to the database okay.
    """
    script_dir = os.path.dirname(os.path.realpath(__file__))
    mets_file = os.path.join(script_dir, FIXTURES_DIR, fixture_path)
    mets = metsrw.METSDocument.fromfile(mets_file)
    mocker.patch("AIPscan.models.events")
    mocked_events = mocker.patch("AIPscan.db.session.add")
    mocker.patch("AIPscan.db.session.commit")
    for fsentry in mets.all_files():
        database_helpers._create_event_objs(fsentry, "some_id")
    assert mocked_events.call_count == event_count
