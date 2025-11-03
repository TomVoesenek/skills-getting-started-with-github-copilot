"""
Test cases for the Mergington High School API endpoints.
"""

import pytest
from fastapi.testclient import TestClient


class TestRootEndpoint:
    """Test cases for the root endpoint."""

    def test_root_redirects_to_static(self, client):
        """Test that root endpoint redirects to static/index.html."""
        response = client.get("/", follow_redirects=False)
        assert response.status_code == 307
        assert response.headers["location"] == "/static/index.html"


class TestActivitiesEndpoint:
    """Test cases for the activities endpoint."""

    def test_get_activities_success(self, client, reset_activities):
        """Test successful retrieval of all activities."""
        response = client.get("/activities")
        assert response.status_code == 200
        
        data = response.json()
        assert isinstance(data, dict)
        assert len(data) > 0
        
        # Check that required fields are present
        for activity_name, activity_data in data.items():
            assert "description" in activity_data
            assert "schedule" in activity_data
            assert "max_participants" in activity_data
            assert "participants" in activity_data
            assert isinstance(activity_data["participants"], list)

    def test_get_activities_structure(self, client, reset_activities):
        """Test the structure of activities data."""
        response = client.get("/activities")
        data = response.json()
        
        # Test a specific activity
        assert "Chess Club" in data
        chess_club = data["Chess Club"]
        assert chess_club["description"] == "Learn strategies and compete in chess tournaments"
        assert chess_club["schedule"] == "Fridays, 3:30 PM - 5:00 PM"
        assert chess_club["max_participants"] == 12
        assert isinstance(chess_club["participants"], list)


class TestSignupEndpoint:
    """Test cases for the signup endpoint."""

    def test_signup_success(self, client, reset_activities):
        """Test successful signup for an activity."""
        email = "newstudent@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == f"Signed up {email} for {activity}"
        
        # Verify the participant was added
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email in activities_data[activity]["participants"]

    def test_signup_nonexistent_activity(self, client, reset_activities):
        """Test signup for a non-existent activity."""
        email = "student@mergington.edu"
        activity = "Nonexistent Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_signup_already_registered(self, client, reset_activities):
        """Test signup when student is already registered."""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"] == "Student already signed up for this activity"

    def test_signup_special_characters_in_activity_name(self, client, reset_activities):
        """Test signup with URL-encoded activity names."""
        email = "student@mergington.edu"
        activity = "Art Workshop"  # Has space in name
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == f"Signed up {email} for {activity}"

    def test_signup_special_characters_in_email(self, client, reset_activities):
        """Test signup with special characters in email."""
        email = "test+tag@mergington.edu"
        activity = "Chess Club"
        
        response = client.post(f"/activities/{activity}/signup?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        # Note: URL encoding converts + to space in query parameters
        expected_email = email.replace("+", " ")
        assert data["message"] == f"Signed up {expected_email} for {activity}"


class TestUnregisterEndpoint:
    """Test cases for the unregister endpoint."""

    def test_unregister_success(self, client, reset_activities):
        """Test successful unregistration from an activity."""
        email = "michael@mergington.edu"  # Already in Chess Club
        activity = "Chess Club"
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        assert data["message"] == f"Unregistered {email} from {activity}"
        
        # Verify the participant was removed
        activities_response = client.get("/activities")
        activities_data = activities_response.json()
        assert email not in activities_data[activity]["participants"]

    def test_unregister_nonexistent_activity(self, client, reset_activities):
        """Test unregistration from a non-existent activity."""
        email = "student@mergington.edu"
        activity = "Nonexistent Club"
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 404
        
        data = response.json()
        assert data["detail"] == "Activity not found"

    def test_unregister_not_registered(self, client, reset_activities):
        """Test unregistration when student is not registered."""
        email = "notregistered@mergington.edu"
        activity = "Chess Club"
        
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 400
        
        data = response.json()
        assert data["detail"] == "Student is not registered for this activity"

    def test_unregister_special_characters(self, client, reset_activities):
        """Test unregistration with special characters in names."""
        # First register a student with special characters
        email = "test+tag@mergington.edu"
        activity = "Art Workshop"
        
        # Register first
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Then unregister (note: + gets URL decoded to space)
        response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert response.status_code == 200
        
        data = response.json()
        # Note: URL encoding converts + to space in query parameters
        expected_email = email.replace("+", " ")
        assert data["message"] == f"Unregistered {expected_email} from {activity}"


class TestIntegrationScenarios:
    """Integration test scenarios."""

    def test_full_signup_unregister_cycle(self, client, reset_activities):
        """Test complete signup and unregister cycle."""
        email = "integration@mergington.edu"
        activity = "Programming Class"
        
        # Check initial state
        initial_response = client.get("/activities")
        initial_data = initial_response.json()
        initial_participants = initial_data[activity]["participants"]
        assert email not in initial_participants
        
        # Sign up
        signup_response = client.post(f"/activities/{activity}/signup?email={email}")
        assert signup_response.status_code == 200
        
        # Verify signup
        after_signup_response = client.get("/activities")
        after_signup_data = after_signup_response.json()
        assert email in after_signup_data[activity]["participants"]
        assert len(after_signup_data[activity]["participants"]) == len(initial_participants) + 1
        
        # Unregister
        unregister_response = client.delete(f"/activities/{activity}/unregister?email={email}")
        assert unregister_response.status_code == 200
        
        # Verify unregistration
        final_response = client.get("/activities")
        final_data = final_response.json()
        assert email not in final_data[activity]["participants"]
        assert len(final_data[activity]["participants"]) == len(initial_participants)

    def test_multiple_students_same_activity(self, client, reset_activities):
        """Test multiple students signing up for the same activity."""
        activity = "Science Club"
        emails = ["student1@mergington.edu", "student2@mergington.edu", "student3@mergington.edu"]
        
        # Sign up all students
        for email in emails:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify all are registered
        response = client.get("/activities")
        data = response.json()
        activity_participants = data[activity]["participants"]
        
        for email in emails:
            assert email in activity_participants

    def test_student_multiple_activities(self, client, reset_activities):
        """Test one student signing up for multiple activities."""
        email = "multisport@mergington.edu"
        activities = ["Basketball Club", "Soccer Team", "Chess Club"]
        
        # Sign up for all activities
        for activity in activities:
            response = client.post(f"/activities/{activity}/signup?email={email}")
            assert response.status_code == 200
        
        # Verify registration in all activities
        response = client.get("/activities")
        data = response.json()
        
        for activity in activities:
            assert email in data[activity]["participants"]