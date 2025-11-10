Feature: Login
  As a user
  I want to log in to the MatchMyCV system
  So that I can access the CV analysis feature

  # Rules:
  #   - Email must be "adeleimup@gmail.com"
  #   - Password must be "ayamjago123"
  
  Scenario: Login Success
    Given I am on the "/login" page
    And I fill in "Email" with "adeleimup@gmail.com"
    And I fill in "Password" with "ayamjago123"
    When I press "Login"
    Then I should be redirected to "/"
    And I should see the message "Login Berhasil!"

  Scenario: Failed Login (missing fields)
    Given I am on the "/login" page
    And I fill in "Email" with ""
    And I fill in "Password" with ""
    When I press "Login"
    Then I should see the message "Login gagal. Semua field harus diisi!"
    And I should remain on the "/login" page

  Scenario: Failed Login (email not registered)
    Given I am on the "/login" page
    And I fill in "Email" with "unknownuser@fst.unair.ac.id"
    And I fill in "Password" with "ayamjago123"
    When I press "Login"
    Then I should see the message "Login gagal. Email tidak terdaftar."
    And I should remain on the "/login" page

  Scenario: Failed Login (wrong password)
    Given I am on the "/login" page
    And I fill in "Email" with "adeleimup@gmail.com"
    And I fill in "Password" with "password123"
    When I press "Login"
    Then I should see the message "Login gagal. Email atau password Anda salah."
    And I should remain on the "/login" page