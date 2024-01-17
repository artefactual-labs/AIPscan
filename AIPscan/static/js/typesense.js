var TypesenseHelpers = {};

TypesenseHelpers["FACET_FIELDS"] = {
  file: [
    "file_format",
    "file_type",
    "puid",
    "aip_id",
    "size",
    "aip_create_date",
  ],
};

TypesenseHelpers["assembleFilterBy"] = function (filters) {
  var filterBy = "";
  var clause;

  for (var i in filters) {
    if (filterBy != "") {
      filterBy += " && ";
    }

    clause = filters[i];
    filterBy += clause[0] + ":" + clause[1] + clause[2];
  }

  return filterBy;
};

TypesenseHelpers["dateStringToTimestampInt"] = function (dateString) {
  var dateData = dateString.split("-");
  var newDate = new Date(dateData[0], dateData[1] - 1, dateData[2]);

  return newDate.getTime() / 1000;
};

TypesenseHelpers["facetValueCounts"] = function (result, fieldName) {
  var facetValueCounts = {};
  var facetCount;
  var facetCountItem;

  for (var i in result["facet_counts"]) {
    facetCount = result["facet_counts"][i];
    facetValueCounts[facetCount["field_name"]] = {};

    for (var i in facetCount["counts"]) {
      facetCountItem = facetCount["counts"][i];
      facetValueCounts[facetCount["field_name"]][facetCountItem["value"]] =
        facetCountItem["count"];
    }
  }

  if (fieldName) {
    return facetValueCounts[fieldName];
  }

  return facetValueCounts;
};

export default TypesenseHelpers;
