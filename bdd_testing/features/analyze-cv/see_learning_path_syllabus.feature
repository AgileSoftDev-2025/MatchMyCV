Feature: See Learning Path Syllabus
  As a user
  I want to be able to see the detailed syllabus of a learning path
  So that I can understand the learning structure

  Scenario: See Learning Path Syllabus Success
    Given I am on "/"
    When I press "Alur Belajar" 
    Then I should see an "listAlurBelajarDropdown" element 
    When I follow "Full-Stack Website Developer" 
    Then I should be on "career-path/full-stack-website-developer-2025-tingkat-pemula"
    And I should see an "syllabusSection" element 