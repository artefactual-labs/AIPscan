Feature: Fetch AIPs from Storage Service
  Fetch jobs finish after imports, including when package lists are paginated.

  Background:
    Given modern and legacy AIPs have been fetched

  Scenario: Fetch the same packages again without duplicate files
    When I fetch the repository again
    Then all three imports finish successfully
    And the report still contains exactly the three packages
    And the fetch job has a recorded duration

  Scenario: Start and finish a fetch from the browser
    When I start a fetch using the New fetch job button
    Then the browser reports that METS downloads completed
    And the new job shows a duration and no new AIPs
    And the report still contains exactly the three packages

  Scenario: Filter imported AIPs by creation date
    When I export AIPs created between 2017-01-01 and 2017-12-31
    Then only the legacy and unidentified packages are included
    When I export AIPs created between 2100-01-01 and 2100-12-31
    Then no packages are included
