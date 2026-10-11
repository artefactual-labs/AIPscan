Feature: Handle Storage Service changes and failures
  Controlled HTTP responses exercise the real worker, database, and browser.
  These cases use a separate Storage Service from the real ingest corpus.

  Background:
    Given a boundary package has been fetched

  Scenario: Replace changed METS without keeping stale records
    When Storage Service changes the package name to boundary-updated
    And I fetch the boundary repository
    Then the boundary report has one package named boundary-updated
    When I fetch the boundary repository
    Then the boundary report has one package named boundary-updated

  Scenario: Remove deleted packages from reports
    When Storage Service marks the boundary package deleted
    And I fetch the boundary repository
    Then the boundary report has no packages
    And the real ingest report still contains three packages

  Scenario Outline: Show download and parse failures before replacing metadata
    When Storage Service returns <response> for METS
    And I start a boundary fetch in the browser
    Then the browser shows the import error "<message>"
    And the browser reports one failed import and allows another fetch
    And the boundary report has one package named boundary-original

    Examples:
      | response     | message              |
      | invalid-mets | Cannot parse METS    |
      | missing-mets | Cannot download METS |

  Scenario: Report a persistence failure and recover on a later fetch
    When Storage Service returns missing-event-agent for METS
    And I start a boundary fetch in the browser
    Then the browser shows the import error "Cannot import METS"
    And the browser reports one failed import and allows another fetch
    When Storage Service recovers
    And I start a boundary fetch in the browser
    Then the browser reports successful METS completion
    And the boundary report has one package named boundary-original

  Scenario: Recover after package listing fails
    When Storage Service fails after the connection probe
    And I start a boundary fetch in the browser
    Then the browser shows a package listing failure and allows another fetch
    When Storage Service recovers
    And I start a boundary fetch in the browser
    Then the browser reports successful METS completion

  Scenario: Report original and preservation image files separately
    When Storage Service returns images for METS
    And I fetch the boundary repository
    Then the image format report counts ten original files
    And the image file report contains six preservation files

  Scenario: Report files whose METS does not record sizes
    When Storage Service returns missing-sizes for METS
    And I fetch the boundary repository
    Then the format reports count the file with zero known bytes

  Scenario: Keep exact totals across index batches and varied sizes
    When Storage Service returns many-files for METS
    And I fetch the boundary repository
    Then the format reports count 1200 files with 4794 bytes
