# Copyright (c) 2026, Prime Tech BD and Contributors
# See license.txt

import frappe
from frappe.tests.utils import FrappeTestCase


class TestPunchRequest(FrappeTestCase):
	def test_create_punch_request(self):
		"""Test creating a punch request"""
		# Create test ZK Person if not exists
		if not frappe.db.exists("ZK Person", {"pin": "TEST001"}):
			person = frappe.get_doc({
				"doctype": "ZK Person",
				"pin": "TEST001",
				"full_name": "Test Employee",
				"is_active": 1
			})
			person.insert()
		
		# Create test device if not exists
		if not frappe.db.exists("ZK Device", "TESTDEV"):
			device = frappe.get_doc({
				"doctype": "ZK Device",
				"name": "TESTDEV",
				"serial_number": "TESTDEV",
				"device_name": "Test Device",
				"status": "Active"
			})
			device.insert()
		
		# Create punch request
		request = frappe.get_doc({
			"doctype": "Punch Request",
			"employee": frappe.db.get_value("ZK Person", {"pin": "TEST001"}, "name"),
			"device": "TESTDEV",
			"punch_date": frappe.utils.today(),
			"punch_time": "09:00:00",
			"request_type": "Manual Punch",
			"reason": "Test request"
		})
		request.insert()
		
		self.assertEqual(request.workflow_state, "Draft")
		self.assertIsNotNone(request.name)
