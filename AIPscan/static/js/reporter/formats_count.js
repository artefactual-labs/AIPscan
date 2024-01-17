const FormatCountData = class {
  constructor(storageServiceId, storageLocationId, startDate, endDate) {
    this.client = this.typesenseClient();

    this.storageServiceId = storageServiceId;
    this.storageLocationId = storageLocationId;
    this.startDate = startDate;
    this.endDate = endDate;

    this.filter = TypesenseHelpers.assembleFilterBy(this.generateFilters());
  }

  typesenseClient() {
    return new Typesense.SearchClient({
      nodes: [
        {
          host: "localhost",
          port: "8108",
          protocol: "http",
        },
      ],
      apiKey: $("body").data("search-api-key"),
      numRetries: 3, // A total of 4 tries (1 original try + 3 retries)
      connectionTimeoutSeconds: 10,
    });
  }

  generateFilters() {
    let startTimestamp = TypesenseHelpers.dateStringToTimestampInt(
      this.startDate,
    );
    let endTimestamp = TypesenseHelpers.dateStringToTimestampInt(this.endDate);

    let filters = [
      ["date_created", ">", startTimestamp],
      ["date_created", "<", endTimestamp],
      ["storage_service_id", "=", this.storageServiceId],
      ["file_type", "=", "'original'"],
    ];

    if (this.storageLocationId) {
      filters.push(["storage_location_id", "=", this.storageLocationId]);
    }

    return filters;
  }

  getFormatCountsData() {
    const client = this.typesenseClient();

    let searchParameters = {
      q: "*",
      filter_by: this.filter,
      facet_by: TypesenseHelpers.FACET_FIELDS["file"].join(","),
      max_facet_values: 10000,
    };

    // Perform search
    let self = this;

    return client
      .collections("aipscan_file")
      .documents()
      .search(searchParameters)
      .then(function (results) {
        self.formatCounts = TypesenseHelpers.facetValueCounts(
          results,
          "file_format",
        );
      });
  }

  getFormatSizeData(results) {
    const client = this.typesenseClient();

    // Request total size of files for each file format
    let searchRequests = { searches: [] };
    let formatFilters;
    let formatFilterBy;

    for (let fileFormat in this.formatCounts) {
      formatFilters = this.generateFilters();
      formatFilters.push(["file_format", "=", "'${fileFormat}'"]);

      formatFilterBy = TypesenseHelpers.assembleFilterBy(formatFilters);

      searchRequests["searches"].push({
        collection: "aipscan_file",
        q: "*",
        filter_by: formatFilterBy,
        facet_by: TypesenseHelpers.FACET_FIELDS["file"].join(","),
        max_facet_values: 10000,
      });
    }

    return client.multiSearch.perform(searchRequests, {});
  }

  summarizeFileFormatSizes(searches) {
    // Summarize file format sizes
    let formatSizeSums = {};
    let fileFormat;
    let results;
    let count;

    for (let i in searches["results"]) {
      results = searches["results"][i];

      if (results["hits"].length) {
        fileFormat = results["hits"][0]["document"]["file_format"];

        for (let j in results["facet_counts"]) {
          count = results["facet_counts"][j];

          if (count["field_name"] == "file_format") {
            formatSizeSums[fileFormat] = count["counts"][0]["count"];
          }
        }
      }
    }

    return formatSizeSums;
  }
};
