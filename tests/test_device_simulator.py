#!/usr/bin/env python3
"""
ZKTeco Device Simulator for Testing
Simulates a ZKTeco device communicating via iClock protocol
"""

import requests
import time
from datetime import datetime
import sys


class ZKDeviceSimulator:
	def __init__(self, server_url, serial_number, comm_key=None):
		self.server_url = server_url.rstrip('/')
		self.serial_number = serial_number
		self.comm_key = comm_key
		self.session = requests.Session()
	
	def handshake(self):
		"""Perform initial handshake"""
		print(f"\n[{self.serial_number}] Performing handshake...")
		
		params = {
			'SN': self.serial_number,
			'options': 'all',
			'pushver': '3.0.0',
			'language': 'en'
		}
		
		if self.comm_key:
			params['key'] = self.comm_key
		
		url = f"{self.server_url}/iclock/cdata"
		response = self.session.get(url, params=params)
		
		print(f"Status: {response.status_code}")
		print(f"Response:\n{response.text}")
		
		return response.status_code == 200
	
	def send_attlog(self, records):
		"""
		Send attendance log records
		records: list of dicts with pin, timestamp, status, verify, workcode
		"""
		print(f"\n[{self.serial_number}] Sending ATTLOG...")
		
		# Build payload
		lines = []
		for record in records:
			line = "{pin}\t{timestamp}\t{status}\t{verify}\t{workcode}".format(
				pin=record.get('pin', '1'),
				timestamp=record.get('timestamp', datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
				status=record.get('status', '0'),
				verify=record.get('verify', '1'),
				workcode=record.get('workcode', '')
			)
			lines.append(line)
		
		payload = '\n'.join(lines)
		
		params = {
			'SN': self.serial_number,
			'table': 'ATTLOG'
		}
		
		if self.comm_key:
			params['key'] = self.comm_key
		
		url = f"{self.server_url}/iclock/cdata"
		response = self.session.post(url, params=params, data=payload.encode('utf-8'))
		
		print(f"Status: {response.status_code}")
		print(f"Response: {response.text}")
		print(f"Sent {len(records)} records")
		
		return response.text == "OK"
	
	def send_userinfo(self, users):
		"""
		Send user info
		users: list of dicts with pin, name, privilege, password, card_no
		"""
		print(f"\n[{self.serial_number}] Sending USERINFO...")
		
		lines = []
		for user in users:
			line = "{pin}\t{name}\t{privilege}\t\t{card_no}".format(
				pin=user.get('pin', '1'),
				name=user.get('name', 'User'),
				privilege=user.get('privilege', '0'),
				card_no=user.get('card_no', '')
			)
			lines.append(line)
		
		payload = '\n'.join(lines)
		
		params = {
			'SN': self.serial_number,
			'table': 'USERINFO'
		}
		
		if self.comm_key:
			params['key'] = self.comm_key
		
		url = f"{self.server_url}/iclock/cdata"
		response = self.session.post(url, params=params, data=payload.encode('utf-8'))
		
		print(f"Status: {response.status_code}")
		print(f"Response: {response.text}")
		
		return response.text == "OK"
	
	def send_fingertmp(self, templates):
		"""
		Send fingerprint templates
		templates: list of dicts with pin, fid, size, valid, template
		"""
		print(f"\n[{self.serial_number}] Sending FINGERTMP...")
		
		lines = []
		for tpl in templates:
			line = "{pin}\t{fid}\t{size}\t{valid}\t{template}".format(
				pin=tpl.get('pin', '1'),
				fid=tpl.get('fid', '0'),
				size=tpl.get('size', '1024'),
				valid=tpl.get('valid', '1'),
				template=tpl.get('template', 'DUMMY_TEMPLATE_DATA')
			)
			lines.append(line)
		
		payload = '\n'.join(lines)
		
		params = {
			'SN': self.serial_number,
			'table': 'FINGERTMP'
		}
		
		if self.comm_key:
			params['key'] = self.comm_key
		
		url = f"{self.server_url}/iclock/cdata"
		response = self.session.post(url, params=params, data=payload.encode('utf-8'))
		
		print(f"Status: {response.status_code}")
		print(f"Response: {response.text}")
		
		return response.text == "OK"
	
	def poll_commands(self):
		"""Poll for pending commands"""
		print(f"\n[{self.serial_number}] Polling for commands...")
		
		params = {
			'SN': self.serial_number
		}
		
		if self.comm_key:
			params['key'] = self.comm_key
		
		url = f"{self.server_url}/iclock/getrequest"
		response = self.session.get(url, params=params)
		
		print(f"Status: {response.status_code}")
		print(f"Response: {response.text}")
		
		# Parse command
		if response.text and response.text != "OK":
			parts = response.text.split(':', 2)
			if len(parts) == 3 and parts[0] == 'C':
				cmd_id = parts[1]
				command = parts[2]
				return cmd_id, command
		
		return None, None
	
	def send_command_result(self, cmd_id, result="OK"):
		"""Send command execution result"""
		print(f"\n[{self.serial_number}] Sending command result for {cmd_id}...")
		
		params = {
			'SN': self.serial_number,
			'ID': cmd_id
		}
		
		if self.comm_key:
			params['key'] = self.comm_key
		
		url = f"{self.server_url}/iclock/devicecmd"
		response = self.session.post(url, params=params, data=result.encode('utf-8'))
		
		print(f"Status: {response.status_code}")
		print(f"Response: {response.text}")
		
		return response.text == "OK"
	
	def run_heartbeat_loop(self, interval=30):
		"""Run continuous heartbeat loop"""
		print(f"\n[{self.serial_number}] Starting heartbeat loop (interval: {interval}s)...")
		print("Press Ctrl+C to stop")
		
		try:
			while True:
				cmd_id, command = self.poll_commands()
				
				if cmd_id:
					print(f"Received command: {command}")
					# Simulate command execution
					time.sleep(1)
					self.send_command_result(cmd_id, "OK: Command executed")
				
				time.sleep(interval)
		
		except KeyboardInterrupt:
			print("\nStopped by user")


def run_test_scenario(server_url, serial_number):
	"""Run a complete test scenario"""
	print("=" * 60)
	print("ZKTeco Device Simulator - Test Scenario")
	print("=" * 60)
	
	device = ZKDeviceSimulator(server_url, serial_number)
	
	# 1. Handshake
	if not device.handshake():
		print("Handshake failed!")
		return
	
	time.sleep(1)
	
	# 2. Send user info
	users = [
		{'pin': '101', 'name': 'John Doe', 'privilege': '0', 'card_no': '1001'},
		{'pin': '102', 'name': 'Jane Smith', 'privilege': '0', 'card_no': '1002'},
	]
	device.send_userinfo(users)
	
	time.sleep(1)
	
	# 3. Send attendance logs
	now = datetime.now()
	attlogs = [
		{'pin': '101', 'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'), 'status': '0', 'verify': '1'},
		{'pin': '102', 'timestamp': now.strftime('%Y-%m-%d %H:%M:%S'), 'status': '1', 'verify': '1'},
	]
	device.send_attlog(attlogs)
	
	time.sleep(1)
	
	# 4. Send fingerprint template
	templates = [
		{'pin': '101', 'fid': '0', 'size': '1024', 'valid': '1', 'template': 'SAMPLE_TEMPLATE_DATA_101_0'},
	]
	device.send_fingertmp(templates)
	
	time.sleep(1)
	
	# 5. Poll for commands (once)
	cmd_id, command = device.poll_commands()
	if cmd_id:
		device.send_command_result(cmd_id, "OK")
	
	print("\n" + "=" * 60)
	print("Test scenario completed!")
	print("=" * 60)


if __name__ == "__main__":
	if len(sys.argv) < 3:
		print("Usage: python test_device_simulator.py <server_url> <serial_number> [mode]")
		print("Modes: test (default), heartbeat")
		print("\nExample:")
		print("  python test_device_simulator.py http://localhost:8000 DEVICE001 test")
		print("  python test_device_simulator.py http://localhost:8000 DEVICE001 heartbeat")
		sys.exit(1)
	
	server_url = sys.argv[1]
	serial_number = sys.argv[2]
	mode = sys.argv[3] if len(sys.argv) > 3 else "test"
	
	if mode == "heartbeat":
		device = ZKDeviceSimulator(server_url, serial_number)
		device.handshake()
		device.run_heartbeat_loop()
	else:
		run_test_scenario(server_url, serial_number)
