Feature: Register
  As a new user
  I want to create an account in the MatchMyCV system
  So that I can log in and use the CV analysis feature

  # Rules:
  #   - Username must be unique
  #   - Email must be valid and unique
  #   - Password must match confirmation
  #   - Password must be at least 8 characters

  Scenario: Register Success
    Given I am on the "/register" page
    And I fill in "Username" with "registeruser"
    And I fill in "Email" with "cobaregist@gmail.com"
    And I fill in "Password" with "ayamjago123"
    And I fill in "Confirm Password" with "ayamjago123"
    When I press "Register"
    Then I should be redirected to "/"
    And I should see the message "Berhasil membuat akun!"

  Scenario: Failed Register (missing fields)
    Given I am on the "/register" page
    And I fill in "Username" with ""
    And I fill in "Email" with ""
    And I fill in "Password" with ""
    And I fill in "Confirm Password" with ""
    When I press "Register"
    Then I should see an error message "Registrasi gagal. Periksa kembali data yang Anda masukkan."
    And I should remain on the "/register" page

  Scenario: Failed Register (passwords do not match)
    Given I am on the "/register" page
    And I fill in "Username" with "adeliauser"
    And I fill in "Email" with "adelia@fst.unair.ac.id"
    And I fill in "Password" with "ayamjago123"
    And I fill in "Confirm Password" with "ayamjago456"
    When I press "Register"
    Then I should see the message "Kedua kolom password tidak sama."
    And I should remain on the "/register" page

  Scenario: Failed Register (email already registered)
    Given I am on the "/register" page
    And I fill in "Username" with "anotheruser"
    And I fill in "Email" with "adeleimup@gmail.com"
    And I fill in "Password" with "ayamjago123"
    And I fill in "Confirm Password" with "ayamjago123"
    When I press "Register"
    Then I should see the message "Email sudah terdaftar. Silakan gunakan email lain."
    And I should remain on the "/register" page

  Scenario: Failed Register (weak password)
    Given I am on the "/register" page
    And I fill in "Username" with "adeliaweak"
    And I fill in "Email" with "adeliaweak@fst.unair.ac.id"
    And I fill in "Password" with "123"
    And I fill in "Confirm Password" with "123"
    When I press "Register"
    Then I should see the message "Password terlalu pendek. Gunakan minimal 8 karakter."
    And I should remain on the "/register" page
