#!/usr/bin/env python3
"""
Core Backend API Testing Script for CRM Kanban System
Tests the existing core features to ensure they still work
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os

# Get backend URL from frontend .env file
BACKEND_URL = "https://89863155-7754-4917-8455-8b0133abbbcd.preview.emergentagent.com/api"

class CoreBackendTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_id = None
        self.test_lead_id = None
    
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
    
    def test_authentication(self):
        """Test authentication endpoints"""
        print("\n🔐 Testing Authentication...")
        
        # Test registration
        user_data = {
            "email": "jane.doe@example.com",
            "name": "Jane Doe",
            "password": "TestPass123!",
            "role": "user"
        }
        
        response = self.make_request("POST", "/auth/register", user_data)
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            print("✅ Registration working")
        elif response and response.status_code == 400:
            # Try login instead
            login_data = {"email": user_data["email"], "password": user_data["password"]}
            response = self.make_request("POST", "/auth/login", login_data)
            if response and response.status_code == 200:
                data = response.json()
                self.auth_token = data.get("access_token")
                self.user_id = data.get("user", {}).get("id")
                print("✅ Login working")
            else:
                print("❌ Authentication failed")
                return False
        else:
            print("❌ Registration failed")
            return False
        
        # Test /auth/me endpoint
        response = self.make_request("GET", "/auth/me")
        if response and response.status_code == 200:
            print("✅ User profile endpoint working")
        else:
            print("❌ User profile endpoint failed")
            return False
        
        return True
    
    def test_lead_crud(self):
        """Test Lead CRUD operations"""
        print("\n📋 Testing Lead CRUD Operations...")
        
        # Create lead
        lead_data = {
            "title": "Test Lead for CRUD",
            "company": "CRUD Test Corp",
            "contact_name": "John Smith",
            "email": "john@crudtest.com",
            "phone": "+1-555-9999",
            "status": "novo",
            "tags": ["test", "crud"],
            "notes": "This is a test lead for CRUD operations",
            "value": 25000.0,
            "priority": "medium",
            "source": "api_test"
        }
        
        response = self.make_request("POST", "/leads", lead_data)
        if response and response.status_code == 200:
            self.test_lead_id = response.json().get("id")
            print("✅ Lead creation working")
        else:
            print("❌ Lead creation failed")
            return False
        
        # Read lead
        response = self.make_request("GET", f"/leads/{self.test_lead_id}")
        if response and response.status_code == 200:
            lead = response.json()
            if lead.get("title") == lead_data["title"]:
                print("✅ Lead retrieval working")
            else:
                print("❌ Lead retrieval data mismatch")
                return False
        else:
            print("❌ Lead retrieval failed")
            return False
        
        # Update lead
        update_data = {
            "title": "Updated Test Lead",
            "value": 30000.0,
            "status": "qualificado"
        }
        
        response = self.make_request("PUT", f"/leads/{self.test_lead_id}", update_data)
        if response and response.status_code == 200:
            updated_lead = response.json()
            if updated_lead.get("title") == "Updated Test Lead":
                print("✅ Lead update working")
            else:
                print("❌ Lead update data mismatch")
                return False
        else:
            print("❌ Lead update failed")
            return False
        
        # List leads
        response = self.make_request("GET", "/leads")
        if response and response.status_code == 200:
            leads = response.json()
            if len(leads) > 0:
                print(f"✅ Lead listing working - Found {len(leads)} leads")
            else:
                print("❌ Lead listing returned no leads")
                return False
        else:
            print("❌ Lead listing failed")
            return False
        
        return True
    
    def test_kanban_board(self):
        """Test Kanban Board API"""
        print("\n📊 Testing Kanban Board API...")
        
        # Get kanban board
        response = self.make_request("GET", "/kanban")
        if response and response.status_code == 200:
            columns = response.json()
            if len(columns) == 6:  # Should have 6 columns
                column_statuses = [col.get("status") for col in columns]
                expected_statuses = ["novo", "qualificado", "proposta", "negociacao", "fechado_ganho", "fechado_perdido"]
                if all(status in column_statuses for status in expected_statuses):
                    print("✅ Kanban board structure correct - 6 columns with proper statuses")
                else:
                    print("❌ Kanban board missing expected statuses")
                    return False
            else:
                print(f"❌ Kanban board has {len(columns)} columns, expected 6")
                return False
        else:
            print("❌ Kanban board retrieval failed")
            return False
        
        # Test move lead
        if self.test_lead_id:
            move_data = {
                "lead_id": self.test_lead_id,
                "new_status": "proposta",
                "new_position": 0
            }
            
            response = self.make_request("POST", "/kanban/move", move_data)
            if response and response.status_code == 200:
                print("✅ Lead move functionality working")
            else:
                print("❌ Lead move functionality failed")
                return False
        
        return True
    
    def run_core_tests(self):
        """Run all core backend tests"""
        print("🚀 Starting Core Backend API Tests...")
        print(f"Backend URL: {self.base_url}")
        
        success = True
        
        if not self.test_authentication():
            success = False
        
        if not self.test_lead_crud():
            success = False
        
        if not self.test_kanban_board():
            success = False
        
        print("\n" + "="*60)
        print("📋 CORE TESTS SUMMARY")
        print("="*60)
        
        if success:
            print("🎉 ALL CORE TESTS PASSED!")
        else:
            print("⚠️  SOME CORE TESTS FAILED")
        
        return success

if __name__ == "__main__":
    tester = CoreBackendTester()
    success = tester.run_core_tests()
    sys.exit(0 if success else 1)