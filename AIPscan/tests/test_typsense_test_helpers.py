from AIPscan import typesense_test_helpers

FAKE_RESULTS = {"found": 1}


def test_fake_documents():
    fake_documents = typesense_test_helpers.FakeDocuments(FAKE_RESULTS)

    assert fake_documents.fake_results == FAKE_RESULTS
    assert fake_documents.search({}) == FAKE_RESULTS


def test_fake_collection():
    fake_collection = typesense_test_helpers.FakeCollection(FAKE_RESULTS)

    assert fake_collection.documents.fake_results == FAKE_RESULTS
    assert fake_collection.documents.search({}) == FAKE_RESULTS
