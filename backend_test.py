#!/usr/bin/env python3
"""
Backend API Testing Script for CRM Kanban System
Tests the newly implemented features: Google Calendar Integration, Advanced Automation Rules, Advanced Dashboard Stats
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os

# Get backend URL from frontend .env file
BACKEND_URL = "https://6cf823be-380e-4c01-a422-12532e03979b.preview.emergentagent.com/api"

class CRMBackendTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_id = None
        self.test_lead_id = None
        self.test_results = {
            "google_calendar_integration": {"status": "PENDING", "details": []},
            "advanced_automation_rules": {"status": "PENDING", "details": []},
            "advanced_dashboard_stats": {"status": "PENDING", "details": []},
            "activity_tracking": {"status": "PENDING", "details": []}
        }
    
    def log_result(self, category, message, success=True):
        """Log test result"""
        status = "✅" if success else "❌"
        print(f"{status} {category}: {message}")
        self.test_results[category]["details"].append(f"{status} {message}")
        if not success and self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "FAILED"
    
    def make_request(self, method, endpoint, data=None, headers=None):
        """Make HTTP request with error handling"""
        url = f"{self.base_url}{endpoint}"
        default_headers = {"Content-Type": "application/json"}
        
        if self.auth_token:
            default_headers["Authorization"] = f"Bearer {self.auth_token}"
        
        if headers:
            default_headers.update(headers)
        
        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=default_headers, timeout=30)
            elif method.upper() == "POST":
                response = requests.post(url, json=data, headers=default_headers, timeout=30)
            elif method.upper() == "PUT":
                response = requests.put(url, json=data, headers=default_headers, timeout=30)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=default_headers, timeout=30)
            
            return response
        except requests.exceptions.RequestException as e:
            print(f"❌ Request failed: {e}")
            return None
    
    def setup_authentication(self):
        """Setup authentication for testing"""
        print("\n🔐 Setting up authentication...")
        
        # Register a test user
        user_data = {
            "email": "sarah.johnson@techcorp.com",
            "name": "Sarah Johnson",
            "password": "SecurePass123!",
            "role": "manager"
        }
        
        response = self.make_request("POST", "/auth/register", user_data)
        
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            print(f"✅ Authentication setup successful - User ID: {self.user_id}")
            return True
        elif response and response.status_code == 400:
            # User might already exist, try login
            login_data = {
                "email": user_data["email"],
                "password": user_data["password"]
            }
            response = self.make_request("POST", "/auth/login", login_data)
            if response and response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                print(f"✅ Authentication via login successful - User ID: {self.user_id}")
                return True
        
        print("❌ Authentication setup failed")
        return False
    
    def create_test_lead(self):
        """Create a test lead for testing"""
        lead_data = {
            "title": "Enterprise Software Solution",
            "company": "TechCorp Industries",
            "contact_name": "Michael Chen",
            "email": "michael.chen@techcorp.com",
            "phone": "+1-555-0123",
            "status": "novo",
            "tags": ["enterprise", "software", "high-priority"],
            "notes": "Potential $50K deal for enterprise software solution",
            "value": 50000.0,
            "priority": "high",
            "source": "website"
        }
        
        response = self.make_request("POST", "/leads", lead_data)
        if response and response.status_code == 200:
            self.test_lead_id = response.json().get("id")
            print(f"✅ Test lead created - ID: {self.test_lead_id}")
            return True
        
        print("❌ Failed to create test lead")
        return False
    
    def test_google_calendar_integration(self):
        """Test Google Calendar Integration endpoints"""
        print("\n📅 Testing Google Calendar Integration...")
        category = "google_calendar_integration"
        
        # Test Google Calendar OAuth connect endpoint
        response = self.make_request("GET", "/auth/google/connect")
        if response and response.status_code == 200:
            data = response.json()
            if "authorization_url" in data:
                self.log_result(category, "Google OAuth connect endpoint working - returns authorization URL")
            else:
                self.log_result(category, "Google OAuth connect endpoint missing authorization_url", False)
        else:
            self.log_result(category, f"Google OAuth connect endpoint failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test calendar events creation (will fail without Google tokens, but endpoint should exist)
        if self.test_lead_id:
            event_data = {
                "lead_id": self.test_lead_id,
                "title": "Follow-up Call with TechCorp",
                "description": "Discuss enterprise software requirements",
                "start_time": (datetime.utcnow() + timedelta(days=1)).isoformat(),
                "end_time": (datetime.utcnow() + timedelta(days=1, hours=1)).isoformat(),
                "event_type": "call"
            }
            
            response = self.make_request("POST", "/calendar/events", event_data)
            if response and response.status_code == 200:
                self.log_result(category, "Calendar event creation endpoint working")
            else:
                self.log_result(category, f"Calendar event creation failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test get calendar events
        response = self.make_request("GET", "/calendar/events")
        if response and response.status_code == 200:
            events = response.json()
            self.log_result(category, f"Calendar events retrieval working - Found {len(events)} events")
        else:
            self.log_result(category, f"Calendar events retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Mark as passed if basic endpoints work (Google tokens not required for testing)
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_advanced_automation_rules(self):
        """Test Advanced Automation Rules endpoints"""
        print("\n🤖 Testing Advanced Automation Rules...")
        category = "advanced_automation_rules"
        
        # Test creating automation rule
        rule_data = {
            "name": "Auto Follow-up for Qualified Leads",
            "trigger_status": "qualificado",
            "action": "schedule_follow_up",
            "action_params": {"days": 3}
        }
        
        response = self.make_request("POST", "/automation/rules", rule_data)
        rule_id = None
        if response and response.status_code == 200:
            rule_id = response.json().get("id")
            self.log_result(category, f"Automation rule creation working - Rule ID: {rule_id}")
        else:
            self.log_result(category, f"Automation rule creation failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test getting automation rules
        response = self.make_request("GET", "/automation/rules")
        if response and response.status_code == 200:
            rules = response.json()
            self.log_result(category, f"Automation rules retrieval working - Found {len(rules)} rules")
        else:
            self.log_result(category, f"Automation rules retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test automation processing by moving lead to trigger status
        if self.test_lead_id and rule_id:
            move_data = {
                "lead_id": self.test_lead_id,
                "new_status": "qualificado",
                "new_position": 0
            }
            
            response = self.make_request("POST", "/kanban/move", move_data)
            if response and response.status_code == 200:
                self.log_result(category, "Lead status change triggers automation processing")
                
                # Check if follow-up was scheduled (check lead details)
                response = self.make_request("GET", f"/leads/{self.test_lead_id}")
                if response and response.status_code == 200:
                    lead = response.json()
                    if lead.get("next_follow_up"):
                        self.log_result(category, "Automation rule executed - follow-up scheduled")
                    else:
                        self.log_result(category, "Automation rule may not have executed - no follow-up scheduled", False)
            else:
                self.log_result(category, f"Lead status change failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_advanced_dashboard_stats(self):
        """Test Advanced Dashboard Stats endpoint"""
        print("\n📊 Testing Advanced Dashboard Stats...")
        category = "advanced_dashboard_stats"
        
        response = self.make_request("GET", "/dashboard/stats")
        if response and response.status_code == 200:
            stats = response.json()
            
            # Check for required fields
            required_fields = [
                "status_stats", "total_leads", "conversion_rate", 
                "avg_deal_size", "recent_activities", "monthly_trends", "top_sources"
            ]
            
            missing_fields = []
            for field in required_fields:
                if field not in stats:
                    missing_fields.append(field)
            
            if not missing_fields:
                self.log_result(category, "Dashboard stats endpoint returns all required fields")
                
                # Validate data types and content
                if isinstance(stats["status_stats"], dict):
                    self.log_result(category, f"Status stats working - {len(stats['status_stats'])} statuses")
                else:
                    self.log_result(category, "Status stats format incorrect", False)
                
                if isinstance(stats["total_leads"], int):
                    self.log_result(category, f"Total leads count working - {stats['total_leads']} leads")
                else:
                    self.log_result(category, "Total leads count format incorrect", False)
                
                if isinstance(stats["conversion_rate"], (int, float)):
                    self.log_result(category, f"Conversion rate calculation working - {stats['conversion_rate']}%")
                else:
                    self.log_result(category, "Conversion rate format incorrect", False)
                
                if isinstance(stats["recent_activities"], list):
                    self.log_result(category, f"Recent activities working - {len(stats['recent_activities'])} activities")
                else:
                    self.log_result(category, "Recent activities format incorrect", False)
                
                if isinstance(stats["monthly_trends"], list):
                    self.log_result(category, f"Monthly trends working - {len(stats['monthly_trends'])} months")
                else:
                    self.log_result(category, "Monthly trends format incorrect", False)
                
                if isinstance(stats["top_sources"], list):
                    self.log_result(category, f"Top sources working - {len(stats['top_sources'])} sources")
                else:
                    self.log_result(category, "Top sources format incorrect", False)
                    
            else:
                self.log_result(category, f"Dashboard stats missing fields: {missing_fields}", False)
        else:
            self.log_result(category, f"Dashboard stats endpoint failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_activity_tracking(self):
        """Test Activity Tracking functionality"""
        print("\n📝 Testing Activity Tracking...")
        category = "activity_tracking"
        
        if not self.test_lead_id:
            self.log_result(category, "No test lead available for activity tracking", False)
            return
        
        # Get activities for the test lead
        response = self.make_request("GET", f"/leads/{self.test_lead_id}/activities")
        if response and response.status_code == 200:
            activities = response.json()
            self.log_result(category, f"Activity retrieval working - Found {len(activities)} activities")
            
            # Check if lead creation was logged
            creation_activities = [a for a in activities if a.get("action") == "created"]
            if creation_activities:
                self.log_result(category, "Lead creation activity logged correctly")
            else:
                self.log_result(category, "Lead creation activity not found", False)
            
            # Check if lead move was logged (from automation test)
            move_activities = [a for a in activities if a.get("action") == "moved"]
            if move_activities:
                self.log_result(category, "Lead move activity logged correctly")
            else:
                self.log_result(category, "Lead move activity not found (may not have been triggered)")
            
        else:
            self.log_result(category, f"Activity retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def run_all_tests(self):
        """Run all backend tests"""
        print("🚀 Starting CRM Backend API Tests...")
        print(f"Backend URL: {self.base_url}")
        
        # Setup
        if not self.setup_authentication():
            print("❌ Cannot proceed without authentication")
            return False
        
        if not self.create_test_lead():
            print("❌ Cannot proceed without test lead")
            return False
        
        # Run tests for new features
        self.test_google_calendar_integration()
        self.test_advanced_automation_rules()
        self.test_advanced_dashboard_stats()
        self.test_activity_tracking()
        
        # Print summary
        print("\n" + "="*60)
        print("📋 TEST SUMMARY")
        print("="*60)
        
        all_passed = True
        for category, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "⏳"
            print(f"{status_icon} {category.replace('_', ' ').title()}: {result['status']}")
            if result["status"] == "FAILED":
                all_passed = False
        
        print("\n" + "="*60)
        if all_passed:
            print("🎉 ALL TESTS PASSED!")
        else:
            print("⚠️  SOME TESTS FAILED - Check details above")
        
        return all_passed

if __name__ == "__main__":
    tester = CRMBackendTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)