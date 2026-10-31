"""
iClock Protocol Handler for ZKTeco ADMS

Implements the ZKTeco PUSH SDK / iClock protocol for device communication.
All endpoints must respond with text/plain (not JSON).
"""

import frappe
from frappe import _
from frappe.utils import now, get_datetime
import re
from urllib.parse import parse_qs, unquote
from prime_att.zkteco.parser import parse_attlog, parse_operlog, parse_userinfo, parse_fingertmp
from prime_att.zkteco.device_manager import register_device, get_device_config, update_device_activity


def validate_device_auth(device=None):
	"""Auth hook to validate device before processing requests"""
	pass  # Will be called by Frappe's auth system


@frappe.whitelist(allow_guest=True, methods=["GET", "POST"])
def iclock_handler(**kwargs):
	"""
	Main entry point for all /iclock/* requests
	Must return plain text, not JSON
	"""
	try:
		frappe.response['type'] = 'text'
		frappe.response['content_type'] = 'text/plain'
		
		# Get path and query parameters
		path = frappe.local.request.path
		method = frappe.local.request.method
		sn = frappe.form_dict.get('SN', '')
		
		# Validate device
		if not sn:
			frappe.response['message'] = "ERROR: Missing SN"
			return
		
		device = validate_device(sn)
		if not device:
			frappe.response['message'] = "ERROR: Invalid or blocked device"
			return
		
		# Route based on path
		if '/iclock/cdata' in path:
			if method == 'GET':
				response = handle_handshake(sn, device)
			else:  # POST
				response = handle_cdata_post(sn, device)
		elif '/iclock/getrequest' in path:
			response = handle_getrequest(sn, device)
		elif '/iclock/devicecmd' in path:
			response = handle_devicecmd(sn, device)
		else:
			response = "ERROR: Unknown endpoint"
		
		frappe.response['message'] = response
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "iClock Protocol Error")
		frappe.response['message'] = "ERROR: Internal error"


def validate_device(sn):
	"""
	Validate device and check if it's blocked
	Returns device doc or None
	"""
	try:
		device = frappe.get_doc("ZK Device", sn)
		if device.status == "Blocked":
			return None
		
		# Validate comm key if configured
		comm_key = frappe.form_dict.get('key', '')
		if device.comm_key and device.comm_key != comm_key:
			frappe.log_error(f"Invalid comm key for device {sn}", "Device Auth Failed")
			return None
		
		return device
		
	except frappe.DoesNotExistError:
		# Auto-register unknown devices
		return register_device(sn)


def handle_handshake(sn, device):
	"""
	GET /iclock/cdata?SN=xxx&options=all&pushver=xxx&language=xxx
	Returns device configuration
	"""
	options = frappe.form_dict.get('options', '')
	pushver = frappe.form_dict.get('pushver', '')
	language = frappe.form_dict.get('language', '')
	
	# Log handshake
	create_raw_log(sn, "HANDSHAKE", f"options={options}&pushver={pushver}&language={language}")
	
	# Update device activity
	update_device_activity(sn, pushver, language)
	
	# Get device configuration
	config = get_device_config(device)
	
	# Build response
	lines = []
	lines.append(f"Stamp={config.get('stamp', '9999')}")
	lines.append(f"OpStamp={config.get('opstamp', '9999')}")
	lines.append(f"ErrorDelay={config.get('error_delay', '120')}")
	lines.append(f"Delay={config.get('delay', '30')}")
	lines.append("TransTimes=00:00;23:59")
	lines.append("TransInterval=1")
	lines.append("TransFlag=TransData AttLog OpLog EnrollUser ChgUser")
	lines.append("Realtime=1")
	lines.append("Encrypt=0")
	
	return "\n".join(lines)


def handle_cdata_post(sn, device):
	"""
	POST /iclock/cdata?SN=xxx&table=ATTLOG
	Body: tab-separated data rows
	"""
	table = frappe.form_dict.get('table', '').upper()
	body = frappe.local.request.get_data(as_text=True)
	
	# Store raw log immediately
	create_raw_log(sn, table, body)
	
	# Process in background
	frappe.enqueue(
		'prime_att.zkteco.processor.process_device_data',
		queue='default',
		timeout=300,
		sn=sn,
		table=table,
		body=body
	)
	
	return "OK"


def handle_getrequest(sn, device):
	"""
	GET /iclock/getrequest?SN=xxx
	Heartbeat + command polling
	Returns pending commands or "OK"
	"""
	# Update device activity
	update_device_activity(sn)
	
	# Check for pending commands
	commands = frappe.get_all(
		"ZK Device Command",
		filters={
			"device": sn,
			"status": ["in", ["Pending", "Sent"]]
		},
		order_by="creation asc",
		limit=1
	)
	
	if commands:
		cmd_doc = frappe.get_doc("ZK Device Command", commands[0].name)
		
		# Mark as sent
		cmd_doc.status = "Sent"
		cmd_doc.sent_time = now()
		cmd_doc.save(ignore_permissions=True)
		frappe.db.commit()
		
		# Return command in iClock format
		return f"C:{cmd_doc.name}:{cmd_doc.command}"
	
	return "OK"


def handle_devicecmd(sn, device):
	"""
	POST /iclock/devicecmd?SN=xxx&ID=xxx
	Device sends command result
	"""
	cmd_id = frappe.form_dict.get('ID', '')
	result = frappe.local.request.get_data(as_text=True)
	
	if cmd_id:
		try:
			cmd_doc = frappe.get_doc("ZK Device Command", cmd_id)
			cmd_doc.status = "Done" if "OK" in result else "Failed"
			cmd_doc.response = result
			cmd_doc.completed_time = now()
			cmd_doc.save(ignore_permissions=True)
			frappe.db.commit()
		except frappe.DoesNotExistError:
			pass
	
	return "OK"


def create_raw_log(sn, table, body):
	"""Store raw payload for debugging and processing"""
	try:
		doc = frappe.get_doc({
			"doctype": "ZK Raw Log",
			"device": sn,
			"log_type": table,
			"payload": body,
			"received_at": now()
		})
		doc.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Failed to create raw log")


def handle_iclock_request():
	"""
	Override for frappe.handler.handle to intercept /iclock requests
	and return plain text instead of JSON
	"""
	if '/iclock/' in frappe.local.request.path:
		return iclock_handler()
	else:
		# Call original handler
		from frappe.handler import handle as original_handle
		return original_handle()
