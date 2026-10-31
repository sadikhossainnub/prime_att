"""
Unit tests for iClock protocol implementation
"""

import unittest
import frappe
from prime_att.zkteco.parser import parse_attlog, parse_userinfo, parse_fingertmp, parse_operlog
from datetime import datetime


class TestProtocolParser(unittest.TestCase):
	"""Test protocol data parsing"""
	
	def test_parse_attlog_basic(self):
		"""Test basic ATTLOG parsing"""
		payload = "101\t2024-10-31 09:00:00\t0\t1\t\t\t\n102\t2024-10-31 09:05:00\t1\t1\t\t\t"
		
		records = parse_attlog(payload)
		
		self.assertEqual(len(records), 2)
		self.assertEqual(records[0]['pin'], '101')
		self.assertEqual(records[0]['status'], '0')
		self.assertEqual(records[1]['pin'], '102')
		self.assertEqual(records[1]['status'], '1')
	
	def test_parse_attlog_varying_fields(self):
		"""Test ATTLOG with varying field counts (firmware tolerance)"""
		# Minimal fields
		payload = "101\t2024-10-31 09:00:00"
		records = parse_attlog(payload)
		
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0]['pin'], '101')
		self.assertEqual(records[0]['status'], '0')  # Default
	
	def test_parse_userinfo(self):
		"""Test USERINFO parsing"""
		payload = "101\tJohn Doe\t0\t\t1001\t\t\t\n102\tJane Smith\t0\t\t1002"
		
		records = parse_userinfo(payload)
		
		self.assertEqual(len(records), 2)
		self.assertEqual(records[0]['pin'], '101')
		self.assertEqual(records[0]['name'], 'John Doe')
		self.assertEqual(records[0]['card_no'], '1001')
	
	def test_parse_fingertmp(self):
		"""Test FINGERTMP parsing"""
		payload = "101\t0\t1024\t1\tSAMPLE_TEMPLATE_DATA"
		
		records = parse_fingertmp(payload)
		
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0]['pin'], '101')
		self.assertEqual(records[0]['fid'], '0')
		self.assertEqual(records[0]['template'], 'SAMPLE_TEMPLATE_DATA')
	
	def test_parse_operlog(self):
		"""Test OPERLOG parsing"""
		payload = "100\t2024-10-31 09:00:00\t1\t101\textra_info"
		
		records = parse_operlog(payload)
		
		self.assertEqual(len(records), 1)
		self.assertEqual(records[0]['admin_pin'], '100')
		self.assertEqual(records[0]['op_object'], '101')


class TestDeviceWorkflow(unittest.TestCase):
	"""Test complete device workflow"""
	
	def setUp(self):
		"""Setup test environment"""
		frappe.set_user("Administrator")
	
	def test_device_registration(self):
		"""Test auto-registration of unknown device"""
		from prime_att.zkteco.device_manager import register_device
		
		sn = "TEST_DEVICE_001"
		
		# Clean up if exists
		if frappe.db.exists("ZK Device", sn):
			frappe.delete_doc("ZK Device", sn, force=True)
		
		device = register_device(sn)
		
		self.assertIsNotNone(device)
		self.assertEqual(device.serial_number, sn)
		self.assertEqual(device.status, "Pending")
	
	def test_command_queue(self):
		"""Test command queueing"""
		from prime_att.zkteco.device_manager import send_command
		
		sn = "TEST_DEVICE_001"
		
		# Ensure device exists
		if not frappe.db.exists("ZK Device", sn):
			from prime_att.zkteco.device_manager import register_device
			register_device(sn)
		
		# Send command
		cmd_id = send_command(sn, "DATA QUERY USERINFO", "Administrator")
		
		self.assertIsNotNone(cmd_id)
		
		# Verify command
		cmd = frappe.get_doc("ZK Device Command", cmd_id)
		self.assertEqual(cmd.device, sn)
		self.assertEqual(cmd.status, "Pending")


def run_tests():
	"""Run all tests"""
	suite = unittest.TestLoader().loadTestsFromModule(__name__)
	unittest.TextTestRunner(verbosity=2).run(suite)


if __name__ == "__main__":
	run_tests()
