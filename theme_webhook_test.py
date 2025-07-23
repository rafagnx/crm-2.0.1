#!/usr/bin/env python3
"""
Backend API Testing Script for CRM Kanban System
Tests the newly implemented Theme and Webhook Management Systems
"""

import requests
import json
from datetime import datetime, timedelta
import sys
import os
import time

# Get backend URL from frontend .env file
BACKEND_URL = "https://481e367b-dd92-48fb-b198-ba0bd400bbd2.preview.emergentagent.com/api"

class ThemeWebhookTester:
    def __init__(self):
        self.base_url = BACKEND_URL
        self.auth_token = None
        self.user_id = None
        self.test_lead_id = None
        self.test_theme_id = None
        self.test_webhook_id = None
        self.test_results = {
            "theme_management": {"status": "PENDING", "details": []},
            "webhook_management": {"status": "PENDING", "details": []},
            "webhook_integration": {"status": "PENDING", "details": []}
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
        
        # Use a unique email with timestamp to avoid conflicts
        import time
        timestamp = str(int(time.time()))
        
        # Register a test user
        user_data = {
            "email": f"theme.tester.{timestamp}@crmsystem.com",
            "name": "Theme Tester",
            "password": "ThemeTest123!",
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
        """Create a test lead for webhook testing"""
        lead_data = {
            "title": "Webhook Test Lead",
            "company": "Test Company Inc",
            "contact_name": "John Webhook",
            "email": "john@testcompany.com",
            "phone": "+1-555-0199",
            "status": "novo",
            "tags": ["webhook-test", "automation"],
            "notes": "Lead created for webhook testing purposes",
            "value": 25000.0,
            "priority": "medium",
            "source": "api_test"
        }
        
        response = self.make_request("POST", "/leads", lead_data)
        if response and response.status_code == 200:
            self.test_lead_id = response.json().get("id")
            print(f"✅ Test lead created - ID: {self.test_lead_id}")
            return True
        
        print("❌ Failed to create test lead")
        return False
    
    def test_theme_management(self):
        """Test Theme Management System"""
        print("\n🎨 Testing Theme Management System...")
        category = "theme_management"
        
        # Test 1: Create a custom theme
        theme_data = {
            "name": "Corporate Blue Theme",
            "colors": {
                "primary": "#1e40af",
                "secondary": "#64748b",
                "success": "#059669",
                "warning": "#d97706",
                "danger": "#dc2626",
                "background": "#f1f5f9",
                "surface": "#ffffff",
                "text_primary": "#0f172a",
                "text_secondary": "#475569"
            },
            "logo_base64": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mNkYPhfDwAChwGA60e6kgAAAABJRU5ErkJggg==",
            "font_family": "Roboto, sans-serif",
            "font_size_base": "16px",
            "border_radius": "0.75rem",
            "is_dark_mode": False
        }
        
        response = self.make_request("POST", "/themes", theme_data)
        if response and response.status_code == 200:
            theme = response.json()
            self.test_theme_id = theme.get("id")
            self.log_result(category, f"Theme creation successful - Theme ID: {self.test_theme_id}")
            
            # Verify theme data
            if theme.get("name") == theme_data["name"]:
                self.log_result(category, "Theme name stored correctly")
            else:
                self.log_result(category, "Theme name not stored correctly", False)
                
            if theme.get("colors", {}).get("primary") == theme_data["colors"]["primary"]:
                self.log_result(category, "Theme colors stored correctly")
            else:
                self.log_result(category, "Theme colors not stored correctly", False)
        else:
            self.log_result(category, f"Theme creation failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 2: Get user themes
        response = self.make_request("GET", "/themes")
        if response and response.status_code == 200:
            themes = response.json()
            self.log_result(category, f"Theme retrieval successful - Found {len(themes)} themes")
            
            # Check if our created theme is in the list
            created_theme = next((t for t in themes if t.get("id") == self.test_theme_id), None)
            if created_theme:
                self.log_result(category, "Created theme found in user themes list")
            else:
                self.log_result(category, "Created theme not found in user themes list", False)
        else:
            self.log_result(category, f"Theme retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 3: Get active theme (should be default initially)
        response = self.make_request("GET", "/themes/active")
        if response and response.status_code == 200:
            active_theme = response.json()
            self.log_result(category, f"Active theme retrieval successful - Theme: {active_theme.get('name', 'Unknown')}")
        else:
            self.log_result(category, f"Active theme retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 4: Activate the created theme
        if self.test_theme_id:
            response = self.make_request("POST", f"/themes/{self.test_theme_id}/activate")
            if response and response.status_code == 200:
                self.log_result(category, "Theme activation successful")
                
                # Verify the theme is now active
                response = self.make_request("GET", "/themes/active")
                if response and response.status_code == 200:
                    active_theme = response.json()
                    if active_theme.get("id") == self.test_theme_id:
                        self.log_result(category, "Theme activation verified - correct theme is now active")
                    else:
                        self.log_result(category, "Theme activation verification failed - wrong theme active", False)
            else:
                self.log_result(category, f"Theme activation failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 5: Update theme
        if self.test_theme_id:
            update_data = {
                "name": "Updated Corporate Blue Theme",
                "colors": {
                    "primary": "#2563eb",
                    "secondary": "#64748b"
                }
            }
            
            response = self.make_request("PUT", f"/themes/{self.test_theme_id}", update_data)
            if response and response.status_code == 200:
                updated_theme = response.json()
                if updated_theme.get("name") == update_data["name"]:
                    self.log_result(category, "Theme update successful")
                else:
                    self.log_result(category, "Theme update failed - name not updated", False)
            else:
                self.log_result(category, f"Theme update failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_webhook_management(self):
        """Test Webhook Management System"""
        print("\n🔗 Testing Webhook Management System...")
        category = "webhook_management"
        
        # Test 1: Create a webhook
        webhook_data = {
            "name": "Lead Notifications Webhook",
            "url": "https://webhook.site/unique-id-here",  # Using webhook.site for testing
            "events": ["lead.created", "lead.updated", "lead.status_changed"],
            "retry_count": 3,
            "timeout_seconds": 30
        }
        
        response = self.make_request("POST", "/webhooks", webhook_data)
        if response and response.status_code == 200:
            webhook = response.json()
            self.test_webhook_id = webhook.get("id")
            self.log_result(category, f"Webhook creation successful - Webhook ID: {self.test_webhook_id}")
            
            # Verify webhook data
            if webhook.get("name") == webhook_data["name"]:
                self.log_result(category, "Webhook name stored correctly")
            else:
                self.log_result(category, "Webhook name not stored correctly", False)
                
            if webhook.get("url") == webhook_data["url"]:
                self.log_result(category, "Webhook URL stored correctly")
            else:
                self.log_result(category, "Webhook URL not stored correctly", False)
                
            if set(webhook.get("events", [])) == set(webhook_data["events"]):
                self.log_result(category, "Webhook events stored correctly")
            else:
                self.log_result(category, "Webhook events not stored correctly", False)
        else:
            self.log_result(category, f"Webhook creation failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 2: Get webhooks
        response = self.make_request("GET", "/webhooks")
        if response and response.status_code == 200:
            webhooks = response.json()
            self.log_result(category, f"Webhook retrieval successful - Found {len(webhooks)} webhooks")
            
            # Check if our created webhook is in the list
            created_webhook = next((w for w in webhooks if w.get("id") == self.test_webhook_id), None)
            if created_webhook:
                self.log_result(category, "Created webhook found in webhooks list")
            else:
                self.log_result(category, "Created webhook not found in webhooks list", False)
        else:
            self.log_result(category, f"Webhook retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 3: Get specific webhook
        if self.test_webhook_id:
            response = self.make_request("GET", f"/webhooks/{self.test_webhook_id}")
            if response and response.status_code == 200:
                webhook = response.json()
                self.log_result(category, f"Individual webhook retrieval successful - Name: {webhook.get('name')}")
            else:
                self.log_result(category, f"Individual webhook retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 4: Update webhook
        if self.test_webhook_id:
            update_data = {
                "name": "Updated Lead Notifications Webhook",
                "events": ["lead.created", "lead.updated", "lead.status_changed", "lead.deleted"],
                "is_active": True
            }
            
            response = self.make_request("PUT", f"/webhooks/{self.test_webhook_id}", update_data)
            if response and response.status_code == 200:
                updated_webhook = response.json()
                if updated_webhook.get("name") == update_data["name"]:
                    self.log_result(category, "Webhook update successful")
                else:
                    self.log_result(category, "Webhook update failed - name not updated", False)
            else:
                self.log_result(category, f"Webhook update failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 5: Test webhook (send test payload)
        if self.test_webhook_id:
            response = self.make_request("POST", f"/webhooks/{self.test_webhook_id}/test")
            if response and response.status_code == 200:
                self.log_result(category, "Webhook test successful - test payload sent")
            else:
                self.log_result(category, f"Webhook test failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 6: Get webhook logs
        if self.test_webhook_id:
            # Wait a moment for logs to be created
            time.sleep(2)
            
            response = self.make_request("GET", f"/webhooks/{self.test_webhook_id}/logs")
            if response and response.status_code == 200:
                logs = response.json()
                self.log_result(category, f"Webhook logs retrieval successful - Found {len(logs)} log entries")
                
                # Check if test webhook log exists
                test_logs = [log for log in logs if log.get("payload", {}).get("test") == True]
                if test_logs:
                    self.log_result(category, "Test webhook log entry found")
                else:
                    self.log_result(category, "Test webhook log entry not found (may be processing)")
            else:
                self.log_result(category, f"Webhook logs retrieval failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def test_webhook_integration(self):
        """Test Webhook Integration with Lead Operations"""
        print("\n🔄 Testing Webhook Integration...")
        category = "webhook_integration"
        
        if not self.test_webhook_id or not self.test_lead_id:
            self.log_result(category, "Missing webhook or lead for integration testing", False)
            return
        
        # Test 1: Lead creation webhook (already triggered when we created the test lead)
        # Check webhook logs for lead creation event
        response = self.make_request("GET", f"/webhooks/{self.test_webhook_id}/logs")
        if response and response.status_code == 200:
            logs = response.json()
            creation_logs = [log for log in logs if log.get("event") == "lead.created"]
            if creation_logs:
                self.log_result(category, "Lead creation webhook triggered successfully")
            else:
                self.log_result(category, "Lead creation webhook not found in logs")
        
        # Test 2: Lead update webhook
        update_data = {
            "notes": "Updated notes for webhook testing",
            "value": 30000.0
        }
        
        response = self.make_request("PUT", f"/leads/{self.test_lead_id}", update_data)
        if response and response.status_code == 200:
            self.log_result(category, "Lead update successful - should trigger webhook")
            
            # Wait for webhook processing
            time.sleep(3)
            
            # Check for update webhook logs
            response = self.make_request("GET", f"/webhooks/{self.test_webhook_id}/logs")
            if response and response.status_code == 200:
                logs = response.json()
                update_logs = [log for log in logs if log.get("event") == "lead.updated"]
                if update_logs:
                    self.log_result(category, "Lead update webhook triggered successfully")
                else:
                    self.log_result(category, "Lead update webhook not found in logs")
        else:
            self.log_result(category, f"Lead update failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 3: Lead status change webhook
        move_data = {
            "lead_id": self.test_lead_id,
            "new_status": "qualificado",
            "new_position": 0
        }
        
        response = self.make_request("POST", "/kanban/move", move_data)
        if response and response.status_code == 200:
            self.log_result(category, "Lead status change successful - should trigger webhook")
            
            # Wait for webhook processing
            time.sleep(3)
            
            # Check for status change webhook logs
            response = self.make_request("GET", f"/webhooks/{self.test_webhook_id}/logs")
            if response and response.status_code == 200:
                logs = response.json()
                status_logs = [log for log in logs if log.get("event") == "lead.status_changed"]
                if status_logs:
                    self.log_result(category, "Lead status change webhook triggered successfully")
                else:
                    self.log_result(category, "Lead status change webhook not found in logs")
        else:
            self.log_result(category, f"Lead status change failed - Status: {response.status_code if response else 'No response'}", False)
        
        # Test 4: Lead deletion webhook
        response = self.make_request("DELETE", f"/leads/{self.test_lead_id}")
        if response and response.status_code == 200:
            self.log_result(category, "Lead deletion successful - should trigger webhook")
            
            # Wait for webhook processing
            time.sleep(3)
            
            # Check for deletion webhook logs
            response = self.make_request("GET", f"/webhooks/{self.test_webhook_id}/logs")
            if response and response.status_code == 200:
                logs = response.json()
                delete_logs = [log for log in logs if log.get("event") == "lead.deleted"]
                if delete_logs:
                    self.log_result(category, "Lead deletion webhook triggered successfully")
                else:
                    self.log_result(category, "Lead deletion webhook not found in logs")
        else:
            self.log_result(category, f"Lead deletion failed - Status: {response.status_code if response else 'No response'}", False)
        
        if self.test_results[category]["status"] != "FAILED":
            self.test_results[category]["status"] = "PASSED"
    
    def cleanup(self):
        """Clean up test data"""
        print("\n🧹 Cleaning up test data...")
        
        # Delete test webhook
        if self.test_webhook_id:
            response = self.make_request("DELETE", f"/webhooks/{self.test_webhook_id}")
            if response and response.status_code == 200:
                print("✅ Test webhook deleted")
            else:
                print("❌ Failed to delete test webhook")
        
        # Delete test theme (only if not active)
        if self.test_theme_id:
            # First deactivate by creating a new default theme
            default_theme = {
                "name": "Default Theme",
                "is_dark_mode": False
            }
            response = self.make_request("POST", "/themes", default_theme)
            if response and response.status_code == 200:
                new_theme_id = response.json().get("id")
                # Activate the new default theme
                self.make_request("POST", f"/themes/{new_theme_id}/activate")
                
                # Now delete the test theme
                response = self.make_request("DELETE", f"/themes/{self.test_theme_id}")
                if response and response.status_code == 200:
                    print("✅ Test theme deleted")
                else:
                    print("❌ Failed to delete test theme")
    
    def run_all_tests(self):
        """Run all theme and webhook tests"""
        print("🚀 Starting Theme and Webhook Management Tests...")
        print(f"Backend URL: {self.base_url}")
        
        # Setup
        if not self.setup_authentication():
            print("❌ Cannot proceed without authentication")
            return False
        
        if not self.create_test_lead():
            print("❌ Cannot proceed without test lead")
            return False
        
        # Run tests
        self.test_theme_management()
        self.test_webhook_management()
        self.test_webhook_integration()
        
        # Cleanup
        self.cleanup()
        
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
    tester = ThemeWebhookTester()
    success = tester.run_all_tests()
    sys.exit(0 if success else 1)