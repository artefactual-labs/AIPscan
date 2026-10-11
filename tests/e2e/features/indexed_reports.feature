@indexed
Feature: Return the same reports with Typesense enabled
  The SQL and indexed app instances read the same imported repository.

  Background:
    Given modern and legacy AIPs have been fetched

  Scenario Outline: Keep indexed report values equal to SQL
    When I export <report> from SQL and Typesense
    Then both reports have the same rows and values

    Examples:
      | report               |
      | report_formats_count |
      | largest_aips         |
      | largest_files        |
      | report_format_versions_count |

  Scenario Outline: Keep indexed filters equal to SQL
    When I filter formats in <scope> using SQL and Typesense
    Then both reports have the same rows and values

    Examples:
      | scope            |
      | legacy dates     |
      | current location |

  Scenario Outline: Keep reports available with an index from before the upgrade
    When the existing index uses the previous format schema
    And I export <report> from SQL and Typesense
    Then both reports have the same rows and values

    Examples:
      | report                       |
      | report_formats_count         |
      | report_format_versions_count |
