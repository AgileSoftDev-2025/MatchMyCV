Feature: CV Analysis (MatchMyCV - Analyze CV)
  As a user of MatchMyCV
  I want to upload my CV in PDF format and receive analysis and job recommendations
  So that I can see job vacancies that match my CV

  # Rules:
  #  - File must be in PDF format
  #  - Maximum file size is 10MB

  Scenario: Successful CV Analysis with All Locations
    Given I am on the "/analisis-cv/" page
    And I select "All Locations" from the "location" dropdown
    When I press "Upload CV" button
    Then I should see the modal "uploadCvModal"
    When I upload the file "CV_Mahasiswa.pdf"
    And the file format should be "pdf"
    And the file size should be below 10MB
    When I press "Analyze" button
    Then I should see the loading screen
    And I should be redirected to "/hasil-rekomendasi/"
    And I should see "CV-Summary" element
    And I should see "JobsThatMatchedYourCV" element
    And I should see text "Hasil analisis CV ditampilkan"
    And I should see text "Rekomendasi pekerjaan berdasarkan CV ditampilkan"

  Scenario: Invalid File Format - DOCX Upload
    Given I am on the "/analisis-cv/" page
    And I select "All Locations" from the "location" dropdown
    When I press "Upload CV" button
    Then I should see the modal "uploadCvModal"
    When I upload the file "srs_template-ieee.doc"
    Then I should see error message "Format file tidak valid, silakan unggah file PDF!"
    And the displayed filename should be "No file chosen"
    And I should remain on "/analisis-cv/" page

  Scenario: File Size Exceeds 10MB Limit
    Given I am on the "/analisis-cv/" page
    And I select "All Locations" from the "location" dropdown
    When I press "Upload CV" button
    Then I should see the modal "uploadCvModal"
    When I upload the file "Pengenalan_PHP.pdf"
    And the file size should be larger than 10MB
    Then I should see error message "Ukuran file melebihi batas maksimum (10MB)!"
    And the displayed filename should be "No file chosen"
    And I should remain on "/analisis-cv/" page

  Scenario: Cancel Upload Modal
    Given I am on the "/analisis-cv/" page
    When I press "Upload CV" button
    Then I should see the modal "uploadCvModal"
    When I press "Cancel" button
    Then the modal "uploadCvModal" should be hidden
    And I should remain on "/analisis-cv/" page

  Scenario: Attempt to Analyze Without File
    Given I am on the "/analisis-cv/" page
    When I press "Upload CV" button
    Then I should see the modal "uploadCvModal"
    When I press "Analyze" button
    Then I should see error message "Silakan pilih file PDF terlebih dahulu."
    And I should remain on "/analisis-cv/" page
