FAKE_RESULTS_FORMAT_COUNTS = {
    "facet_counts": [
        {"field_name": "file_format", "counts": [{"value": "wav", "count": 10}]}
    ]
}


FAKE_MULTI_SEARCH_RESULTS_FORMAT_COUNTS = {
    "results": [
        {
            "hits": [{"document": {"file_format": "wav"}}],
            "facet_counts": [{"field_name": "size", "stats": {"sum": 999}}],
        }
    ]
}


def fake_collection_format_counts(mocker):
    fake_collection = FakeCollection(FAKE_RESULTS_FORMAT_COUNTS)

    query_collection = mocker.patch("typesense.collections.Collections.__getitem__")
    query_collection.return_value = fake_collection

    query_multi = mocker.patch("typesense.multi_search.MultiSearch.perform")
    query_multi.return_value = FAKE_MULTI_SEARCH_RESULTS_FORMAT_COUNTS

    return fake_collection


def fake_collection(mocker, fake_results):
    fake_collection = FakeCollection(fake_results)

    query = mocker.patch("typesense.collections.Collections.__getitem__")
    query.return_value = fake_collection


class FakeDocuments:
    def __init__(self, fake_results):
        self.fake_results = fake_results

    def search(self, search_parameters):
        return self.fake_results

    def _import(self, search_parameters):
        return {}


class FakeCollection:
    def __init__(self, fake_results=None):
        self.documents = FakeDocuments(fake_results)

    def delete(self):
        return
