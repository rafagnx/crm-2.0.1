#!/usr/bin/env python3
"""
Comprehensive Backend API Testing Script for CRM Kanban System
Tests all core backend functionality as requested in the review:
1. Core Authentication & User Management
2. Lead Management APIs  
3. Kanban Board APIs
4. Dashboard Statistics APIs
5. Activity Tracking
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os

# Get backend URL from frontend .env file
BACKEND_URL = "https://89863155-7754-4917-8455-8b0133abbbcd.preview.emergentagent.com/api"

class ComprehensiveCRMTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_id = None
        self.test_lead_ids = []
        self.test_results = {
            "authentication": {"status": "PENDING", "details": []},
            "user_management": {"status": "PENDING", "details": []},
            "lead_crud": {"status": "PENDING", "details": []},
            "kanban_board": {"status": "PENDING", "details": []},
            "dashboard_stats": {"status": "PENDING", "details": []},
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
    
    def test_authentication(self):
        """Test Core Authentication & User Management"""
        print("\n🔐 Testing Core Authentication & User Management...")
        category = "authentication"
        
        # Test 1: User Registration with JWT token
        print("\n--- Testing User Registration ---")
        user_data = {
            "email": "maria.silva@empresa.com.br",
            "name": "Maria Silva",
            "password": "MinhaSenh@123",
            "role": "manager"
        }
        
        response = self.make_request("POST", "/auth/register", user_data)
        if response and response.status_code == 200:
            data = response.json()
            if "access_token" in data and "user" in data:
                self.auth_token = data["access_token"]
                self.user_id = data["user"]["id"]
                self.log_result(category, f"User registration successful - JWT token received, User ID: {self.user_id}")
                
                # Verify user data
                user = data["user"]
                if user["role"] == "manager" and user["email"] == user_data["email"]:
                    self.log_result(category, "User role assignment working correctly")
                else:
                    self.log_result(category, "User role assignment failed", False)
            else:
                self.log_result(category, "Registration response missing required fields", False)
        elif response and response.status_code == 400:
            # User exists, try login instead
            self.log_result(category, "User already exists, testing login instead")
            self.test_existing_user_login()
        else:
            self.log_result(category, f"User registration failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 2: JWT Token Validation
        if self.auth_token:
            print("\n--- Testing JWT Token Validation ---")
            response = self.make_request("GET", "/auth/me")
            if response and response.status_code == 200:
                user_data = response.json()
                if user_data.get("id") == self.user_id:
                    self.log_result(category, "JWT token validation working correctly")
                else:
                    self.log_result(category, "JWT token validation returned wrong user", False)
            else:
                self.log_result(category, f"JWT token validation failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 3: Demo Users Login
        print("\n--- Testing Demo Users Login ---")
        demo_users = [
            {"email": "admin", "password": "Rafa040388?", "expected_role": "admin"},
            {"email": "suporte", "password": "25261020", "expected_role": "manager"}
        ]
        
        for demo_user in demo_users:
            response = self.make_request("POST", "/auth/login", {
                "email": demo_user["email"],
                "password": demo_user["password"]
            })
            
            if response and response.status_code == 200:
                data = response.json()
                if data.get("user", {}).get("role") == demo_user["expected_role"]:
                    self.log_result(category, f"Demo user {demo_user['email']} login successful with correct role")
                else:
                    self.log_result(category, f"Demo user {demo_user['email']} has incorrect role", False)
            else:
                self.log_result(category, f"Demo user {demo_user['email']} login failed", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_existing_user_login(self):
        """Test login for existing user"""
        login_data = {
            "email": "maria.silva@empresa.com.br",
            "password": "MinhaSenh@123"
        }
        
        response = self.make_request("POST", "/auth/login", login_data)
        if response and response.status_code == 200:
            data = response.json()
            self.auth_token = data.get("access_token")
            self.user_id = data.get("user", {}).get("id")
            self.log_result("authentication", "Existing user login successful")
        else:
            self.log_result("authentication", "Existing user login failed", False)
    
    def test_user_management(self):
        """Test User Management APIs"""
        print("\n👥 Testing User Management...")
        category = "user_management"
        
        if not self.auth_token:
            self.log_result(category, "No authentication token available", False)
            return
        
        # Test getting users list (role-based access)
        response = self.make_request("GET", "/users")
        if response and response.status_code == 200:
            users = response.json()
            self.log_result(category, f"Users list retrieval working - Found {len(users)} users")
            
            # Verify user data structure
            if users and isinstance(users[0], dict):
                required_fields = ["id", "email", "name", "role", "created_at", "is_active"]
                user = users[0]
                missing_fields = [field for field in required_fields if field not in user]
                
                if not missing_fields:
                    self.log_result(category, "User data structure correct")
                else:
                    self.log_result(category, f"User data missing fields: {missing_fields}", False)
        else:
            self.log_result(category, f"Users list retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_lead_crud_operations(self):
        """Test Lead Management APIs - CRUD Operations"""
        print("\n📋 Testing Lead CRUD Operations...")
        category = "lead_crud"
        
        if not self.auth_token:
            self.log_result(category, "No authentication token available", False)
            return
        
        # Test 1: CREATE Lead
        print("\n--- Testing Lead Creation ---")
        lead_data = {
            "title": "Implementação Sistema ERP",
            "company": "Indústrias ABC Ltda",
            "contact_name": "João Santos",
            "email": "joao.santos@industriasabc.com.br",
            "phone": "+55 11 99999-8888",
            "status": "novo",
            "tags": ["erp", "industria", "alta-prioridade"],
            "notes": "Cliente interessado em sistema ERP completo para gestão industrial",
            "value": 75000.0,
            "priority": "high",
            "source": "website"
        }
        
        response = self.make_request("POST", "/leads", lead_data)
        if response and response.status_code == 200:
            lead = response.json()
            lead_id = lead.get("id")
            if lead_id:
                self.test_lead_ids.append(lead_id)
                self.log_result(category, f"Lead creation successful - ID: {lead_id}")
                
                # Verify all fields were saved correctly
                for key, value in lead_data.items():
                    if lead.get(key) == value:
                        continue
                    else:
                        self.log_result(category, f"Lead field {key} not saved correctly", False)
                        break
                else:
                    self.log_result(category, "All lead fields saved correctly")
            else:
                self.log_result(category, "Lead creation response missing ID", False)
        else:
            self.log_result(category, f"Lead creation failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 2: READ Lead (Individual and List)
        print("\n--- Testing Lead Retrieval ---")
        if self.test_lead_ids:
            # Individual lead retrieval
            response = self.make_request("GET", f"/leads/{self.test_lead_ids[0]}")
            if response and response.status_code == 200:
                lead = response.json()
                self.log_result(category, "Individual lead retrieval working")
            else:
                self.log_result(category, f"Individual lead retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # List all leads
        response = self.make_request("GET", "/leads")
        if response and response.status_code == 200:
            leads = response.json()
            self.log_result(category, f"Lead list retrieval working - Found {len(leads)} leads")
        else:
            self.log_result(category, f"Lead list retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 3: UPDATE Lead
        print("\n--- Testing Lead Updates ---")
        if self.test_lead_ids:
            update_data = {
                "status": "qualificado",
                "value": 85000.0,
                "notes": "Cliente confirmou interesse - proposta em preparação",
                "priority": "high"
            }
            
            response = self.make_request("PUT", f"/leads/{self.test_lead_ids[0]}", update_data)
            if response and response.status_code == 200:
                updated_lead = response.json()
                self.log_result(category, "Lead update successful")
                
                # Verify updates were applied
                for key, value in update_data.items():
                    if updated_lead.get(key) == value:
                        continue
                    else:
                        self.log_result(category, f"Lead update field {key} not updated correctly", False)
                        break
                else:
                    self.log_result(category, "All lead update fields applied correctly")
            else:
                self.log_result(category, f"Lead update failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Create additional test leads for better testing
        additional_leads = [
            {
                "title": "Consultoria em TI",
                "company": "TechSolutions Ltda",
                "contact_name": "Ana Costa",
                "email": "ana.costa@techsolutions.com.br",
                "status": "proposta",
                "value": 25000.0,
                "source": "referral"
            },
            {
                "title": "Sistema de Vendas Online",
                "company": "E-commerce Brasil",
                "contact_name": "Carlos Oliveira",
                "email": "carlos@ecommercebrasil.com.br",
                "status": "negociacao",
                "value": 45000.0,
                "source": "cold_call"
            }
        ]
        
        for lead_data in additional_leads:
            response = self.make_request("POST", "/leads", lead_data)
            if response and response.status_code == 200:
                lead_id = response.json().get("id")
                if lead_id:
                    self.test_lead_ids.append(lead_id)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_kanban_board_apis(self):
        """Test Kanban Board APIs"""
        print("\n📊 Testing Kanban Board APIs...")
        category = "kanban_board"
        
        if not self.auth_token:
            self.log_result(category, "No authentication token available", False)
            return
        
        # Test 1: Retrieve Kanban Board
        print("\n--- Testing Kanban Board Retrieval ---")
        response = self.make_request("GET", "/kanban")
        if response and response.status_code == 200:
            columns = response.json()
            self.log_result(category, f"Kanban board retrieval working - Found {len(columns)} columns")
            
            # Verify 6 columns structure
            expected_statuses = ["novo", "qualificado", "proposta", "negociacao", "fechado_ganho", "fechado_perdido"]
            if len(columns) == 6:
                self.log_result(category, "Correct number of kanban columns (6)")
                
                # Verify column structure
                for i, column in enumerate(columns):
                    required_fields = ["status", "title", "color", "leads"]
                    missing_fields = [field for field in required_fields if field not in column]
                    
                    if not missing_fields:
                        if column["status"] in expected_statuses:
                            self.log_result(category, f"Column {i+1} structure correct - Status: {column['status']}")
                        else:
                            self.log_result(category, f"Column {i+1} has unexpected status: {column['status']}", False)
                    else:
                        self.log_result(category, f"Column {i+1} missing fields: {missing_fields}", False)
                
                # Check if leads are positioned correctly
                total_leads_in_columns = sum(len(col["leads"]) for col in columns)
                self.log_result(category, f"Total leads positioned in columns: {total_leads_in_columns}")
                
            else:
                self.log_result(category, f"Incorrect number of columns - Expected 6, got {len(columns)}", False)
        else:
            self.log_result(category, f"Kanban board retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 2: Move Leads Between Columns
        print("\n--- Testing Lead Movement ---")
        if self.test_lead_ids:
            # Move first lead to different status
            move_data = {
                "lead_id": self.test_lead_ids[0],
                "new_status": "proposta",
                "new_position": 0
            }
            
            response = self.make_request("POST", "/kanban/move", move_data)
            if response and response.status_code == 200:
                self.log_result(category, "Lead movement working")
                
                # Verify lead appears in correct column
                response = self.make_request("GET", "/kanban")
                if response and response.status_code == 200:
                    columns = response.json()
                    proposta_column = next((col for col in columns if col["status"] == "proposta"), None)
                    
                    if proposta_column:
                        lead_in_column = next((lead for lead in proposta_column["leads"] if lead["id"] == self.test_lead_ids[0]), None)
                        if lead_in_column:
                            self.log_result(category, "Lead correctly positioned in new column after move")
                        else:
                            self.log_result(category, "Lead not found in target column after move", False)
                    else:
                        self.log_result(category, "Target column not found", False)
            else:
                self.log_result(category, f"Lead movement failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_dashboard_statistics(self):
        """Test Dashboard Statistics APIs"""
        print("\n📈 Testing Dashboard Statistics APIs...")
        category = "dashboard_stats"
        
        if not self.auth_token:
            self.log_result(category, "No authentication token available", False)
            return
        
        # Test Dashboard Stats Endpoint
        response = self.make_request("GET", "/dashboard/stats")
        if response and response.status_code == 200:
            stats = response.json()
            self.log_result(category, "Dashboard stats endpoint accessible")
            
            # Check for all required metrics
            required_fields = [
                "status_stats", "total_leads", "conversion_rate", 
                "avg_deal_size", "recent_activities", "monthly_trends", "top_sources"
            ]
            
            missing_fields = [field for field in required_fields if field not in stats]
            if not missing_fields:
                self.log_result(category, "All required dashboard fields present")
                
                # Validate data types and content
                if isinstance(stats["status_stats"], dict):
                    self.log_result(category, f"Status distribution working - {len(stats['status_stats'])} statuses tracked")
                else:
                    self.log_result(category, "Status statistics format incorrect", False)
                
                if isinstance(stats["total_leads"], int) and stats["total_leads"] >= 0:
                    self.log_result(category, f"Total leads count working - {stats['total_leads']} leads")
                else:
                    self.log_result(category, "Total leads count format incorrect", False)
                
                if isinstance(stats["conversion_rate"], (int, float)) and 0 <= stats["conversion_rate"] <= 100:
                    self.log_result(category, f"Conversion rate calculation working - {stats['conversion_rate']}%")
                else:
                    self.log_result(category, "Conversion rate calculation incorrect", False)
                
                if isinstance(stats["avg_deal_size"], (int, float)) and stats["avg_deal_size"] >= 0:
                    self.log_result(category, f"Average deal size calculation working - R$ {stats['avg_deal_size']:.2f}")
                else:
                    self.log_result(category, "Average deal size calculation incorrect", False)
                
                if isinstance(stats["recent_activities"], list):
                    self.log_result(category, f"Recent activities working - {len(stats['recent_activities'])} activities")
                    
                    # Validate activity structure
                    if stats["recent_activities"]:
                        activity = stats["recent_activities"][0]
                        activity_fields = ["id", "lead_id", "user_id", "action", "timestamp"]
                        missing_activity_fields = [field for field in activity_fields if field not in activity]
                        
                        if not missing_activity_fields:
                            self.log_result(category, "Activity structure validation passed")
                        else:
                            self.log_result(category, f"Activity structure missing fields: {missing_activity_fields}", False)
                else:
                    self.log_result(category, "Recent activities format incorrect", False)
                
                if isinstance(stats["monthly_trends"], list):
                    self.log_result(category, f"Monthly trends working - {len(stats['monthly_trends'])} months of data")
                else:
                    self.log_result(category, "Monthly trends format incorrect", False)
                
                if isinstance(stats["top_sources"], list):
                    self.log_result(category, f"Top sources working - {len(stats['top_sources'])} sources tracked")
                else:
                    self.log_result(category, "Top sources format incorrect", False)
                    
            else:
                self.log_result(category, f"Dashboard stats missing required fields: {missing_fields}", False)
        else:
            self.log_result(category, f"Dashboard stats endpoint failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_activity_tracking(self):
        """Test Activity Tracking"""
        print("\n📝 Testing Activity Tracking...")
        category = "activity_tracking"
        
        if not self.auth_token:
            self.log_result(category, "No authentication token available", False)
            return
        
        if not self.test_lead_ids:
            self.log_result(category, "No test leads available for activity tracking", False)
            return
        
        # Test activity retrieval for leads
        for i, lead_id in enumerate(self.test_lead_ids[:2]):  # Test first 2 leads
            response = self.make_request("GET", f"/leads/{lead_id}/activities")
            if response and response.status_code == 200:
                activities = response.json()
                self.log_result(category, f"Lead {i+1} activities retrieval working - {len(activities)} activities")
                
                if activities:
                    # Check activity structure
                    activity = activities[0]
                    required_fields = ["id", "lead_id", "user_id", "action", "details", "timestamp"]
                    missing_fields = [field for field in required_fields if field not in activity]
                    
                    if not missing_fields:
                        self.log_result(category, f"Lead {i+1} activity structure correct")
                        
                        # Check if creation activity exists
                        creation_activities = [a for a in activities if a.get("action") == "created"]
                        if creation_activities:
                            self.log_result(category, f"Lead {i+1} creation activity logged correctly")
                        
                        # Check if update activities exist
                        update_activities = [a for a in activities if a.get("action") in ["updated", "moved"]]
                        if update_activities:
                            self.log_result(category, f"Lead {i+1} update/move activities logged correctly")
                        
                    else:
                        self.log_result(category, f"Lead {i+1} activity structure missing fields: {missing_fields}", False)
                else:
                    self.log_result(category, f"Lead {i+1} has no activities (unexpected)", False)
            else:
                self.log_result(category, f"Lead {i+1} activities retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def cleanup_test_data(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test leads
        for lead_id in self.test_lead_ids:
            response = self.make_request("DELETE", f"/leads/{lead_id}")
            if response and response.status_code == 200:
                print(f"✅ Deleted test lead: {lead_id}")
            else:
                print(f"❌ Failed to delete test lead: {lead_id}")
    
    def run_comprehensive_tests(self):
        """Run all comprehensive backend tests"""
        print("🚀 Starting Comprehensive CRM Backend API Tests...")
        print(f"Backend URL: {self.base_url}")
        print("="*80)
        
        # Run all test categories
        self.test_authentication()
        self.test_user_management()
        self.test_lead_crud_operations()
        self.test_kanban_board_apis()
        self.test_dashboard_statistics()
        self.test_activity_tracking()
        
        # Clean up
        self.cleanup_test_data()
        
        # Print comprehensive summary
        print("\n" + "="*80)
        print("📋 COMPREHENSIVE TEST SUMMARY")
        print("="*80)
        
        all_passed = True
        for category, result in self.test_results.items():
            status_icon = "✅" if result["status"] == "PASSED" else "❌" if result["status"] == "FAILED" else "⏳"
            category_name = category.replace('_', ' ').title()
            print(f"{status_icon} {category_name}: {result['status']}")
            
            if result["status"] == "FAILED":
                all_passed = False
                print(f"   Failed tests in {category_name}:")
                for detail in result["details"]:
                    if "❌" in detail:
                        print(f"     {detail}")
        
        print("\n" + "="*80)
        if all_passed:
            print("🎉 ALL COMPREHENSIVE TESTS PASSED!")
            print("✅ Core CRM backend functionality is working correctly")
            print("✅ Authentication system fully functional")
            print("✅ Lead management CRUD operations working")
            print("✅ Kanban board APIs operational")
            print("✅ Dashboard statistics accurate")
            print("✅ Activity tracking functioning properly")
        else:
            print("⚠️  SOME TESTS FAILED - Check details above")
            print("❌ Backend has issues that need attention")
        
        return all_passed

if __name__ == "__main__":
    tester = ComprehensiveCRMTester()
    success = tester.run_comprehensive_tests()
    sys.exit(0 if success else 1)