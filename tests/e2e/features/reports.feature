Feature: Report on imported AIPs
  Reports show the files that AIPscan fetched from Archivematica Storage Service.

  Background:
    Given modern and legacy AIPs have been fetched

  Scenario Outline: Keep package names and original file metadata
    When I export AIP contents for the <package> package
    Then its name is "<name>"
    And its original files total <size> bytes
    And its formats are "<formats>"

    Examples:
      | package | name                  | size | formats                          |
      | modern  | aipscan-e2e           | 25   | x-fmt/111 (Plain Text): 1 file     |
      | legacy  | easy_1488911181        | 4    | x-fmt/111 (Plain Text): 1 file     |
      | unknown | unidentified-transfer | 4    | Unknown (Unknown): 1 file         |

  Scenario: Include unidentified originals in format totals
    When I export the format count report
    Then plain text originals total 2 files and 29 bytes
    And unidentified originals total 1 file and 4 bytes
    And there are no other formats

  Scenario Outline: Render interactive charts from imported files
    Then the <chart> chart shows the imported data without browser errors

    Examples:
      | chart       |
      | pie         |
      | scatter     |
      | timeline    |
      | time series |
