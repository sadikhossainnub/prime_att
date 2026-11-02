"""
Background processor for device data
"""

import frappe
from frappe import _
from frappe.utils import now, get_datetime
from prime_att.zkteco.parser import parse_attlog, parse_operlog, parse_userinfo, parse_fingertmp
import pytz


def process_device_data(sn, table, body):
	"""
	Process device data in background
	Called via enqueue from iclock_protocol
	"""
	try:
		if table == "ATTLOG":
			process_attlog(sn, body)
		elif table == "OPERLOG":
			process_operlog(sn, body)
		elif table == "USERINFO":
			process_userinfo(sn, body)
		elif table == "FINGERTMP":
			process_fingertmp(sn, body)
		else:
			frappe.log_error(f"Unknown table type: {table}", "Device Data Processor")
	
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Failed to process {table} from {sn}")


def process_attlog(sn, body):
	"""Process attendance log records"""
	records = parse_attlog(body)
	
	for record in records:
		try:
			# Convert to site timezone
			punch_time = convert_to_site_timezone(record['timestamp'])
			
			# Check for duplicate (within tolerance)
			tolerance_seconds = get_duplicate_tolerance()
			
			existing = frappe.db.exists(
				"ZK Punch",
				{
					"device": sn,
					"pin": record['pin'],
					"punch_time": ["between", [
						frappe.utils.add_to_date(punch_time, seconds=-tolerance_seconds),
						frappe.utils.add_to_date(punch_time, seconds=tolerance_seconds)
					]]
				}
			)
			
			if existing:
				continue  # Skip duplicate
			
			# Create punch record
			punch = frappe.get_doc({
				"doctype": "ZK Punch",
				"device": sn,
				"pin": record['pin'],
				"punch_time": punch_time,
				"status_code": record['status'],
				"verify_type": record['verify'],
				"workcode": record['workcode'],
			})
			punch.insert(ignore_permissions=True)
			
			# Create check-in/out record
			create_checkin_out(punch)
			
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), f"Failed to process ATTLOG record: {record}")
	
	frappe.db.commit()


def process_operlog(sn, body):
	"""Process operation log records"""
	records = parse_operlog(body)
	
	for record in records:
		try:
			# Store operation log (for audit trail)
			log = frappe.get_doc({
				"doctype": "ZK Operation Log",
				"device": sn,
				"admin_pin": record['admin_pin'],
				"operation_time": convert_to_site_timezone(record['oper_time']),
				"operation_id": record['op_id'],
				"operation_object": record['op_object'],
				"extra_data": record['extra']
			})
			log.insert(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), f"Failed to process OPERLOG record: {record}")
	
	frappe.db.commit()


def process_userinfo(sn, body):
	"""Process user info - create or update ZK Person"""
	records = parse_userinfo(body)
	
	for record in records:
		try:
			# Check if person exists
			person = None
			if frappe.db.exists("ZK Person", {"pin": record['pin']}):
				person = frappe.get_doc("ZK Person", {"pin": record['pin']})
			else:
				person = frappe.get_doc({
					"doctype": "ZK Person",
					"pin": record['pin'],
					"full_name": record['name'] or f"User {record['pin']}",
					"is_active": 1
				})
				person.insert(ignore_permissions=True)
			
			# Update fields
			person.full_name = record['name'] or person.full_name or f"User {record['pin']}"
			person.card_no = record['card_no'] or person.card_no
			person.privilege = record['privilege'] or person.privilege or "0"
			person.is_active = 1
			
			# Update device registration status
			device_found = False
			for dev in person.devices:
				if dev.device == sn:
					dev.status = "Pushed"
					device_found = True
					break
			
			if not device_found:
				person.append("devices", {
					"device": sn,
					"status": "Pushed"
				})
			
			person.save(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), f"Failed to process USERINFO record: {record}")
	
	frappe.db.commit()


def process_fingertmp(sn, body):
	"""Process fingerprint template"""
	records = parse_fingertmp(body)
	
	for record in records:
		try:
			# Find person
			if not frappe.db.exists("ZK Person", {"pin": record['pin']}):
				# Create unmapped person
				person = frappe.get_doc({
					"doctype": "ZK Person",
					"pin": record['pin'],
					"full_name": f"User {record['pin']}",
					"is_active": 1
				})
				person.insert(ignore_permissions=True)
			
			# Update enrollment status if there's a pending enrollment
			enrollments = frappe.get_all(
				"ZK Fingerprint Enrollment",
				filters={
					"device": sn,
					"person_pin": record['pin'],
					"finger_index": record['fid'],
					"status": ["in", ["Queued", "Sent", "Waiting for User"]]
				}
			)
			
			for enrollment in enrollments:
				enroll_doc = frappe.get_doc("ZK Fingerprint Enrollment", enrollment.name)
				enroll_doc.status = "Enrolled"
				enroll_doc.template_data = record['template']  # Password fieldtype handles encryption on save
				enroll_doc.enrolled_time = now()
				enroll_doc.save(ignore_permissions=True)
			
			# Update person device status
			person = frappe.get_doc("ZK Person", {"pin": record['pin']})
			for dev in person.devices:
				if dev.device == sn:
					dev.status = "Enrolled"
					break
			person.save(ignore_permissions=True)
			
		except Exception as e:
			frappe.log_error(frappe.get_traceback(), f"Failed to process FINGERTMP record: {record}")
	
	frappe.db.commit()


def create_checkin_out(punch):
	"""Create ZK Check-in Out record from punch"""
	try:
		# Get person
		person = frappe.db.get_value("ZK Person", {"pin": punch.pin}, "name")
		
		if not person:
			# Create unmapped person
			person_doc = frappe.get_doc({
				"doctype": "ZK Person",
				"pin": punch.pin,
				"full_name": f"User {punch.pin}",
				"is_active": 1
			})
			person_doc.insert(ignore_permissions=True)
			person = person_doc.name
		
		# Determine log type (IN/OUT)
		log_type = get_log_type_from_status(punch.status_code, punch.punch_time)
		
		# Create check-in/out
		checkin = frappe.get_doc({
			"doctype": "ZK Check-in Out",
			"person": person,
			"log_time": punch.punch_time,
			"log_type": log_type,
			"device": punch.device,
			"punch_record": punch.name,
			"sync_status": "Pending"
		})
		checkin.insert(ignore_permissions=True)
		
		# Try to sync if connector is enabled - use dotted string path for background job
		frappe.enqueue(
			'prime_att.zkteco.sync_manager.sync_checkin',
			queue='default',
			checkin_name=checkin.name
		)
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Failed to create check-in/out for punch {punch.name}")


def get_log_type_from_status(status_code, punch_time):
	"""Determine IN/OUT from status code and rules"""
	# Get status mapping from settings
	settings = frappe.get_single("ZK Settings")
	
	for mapping in settings.status_mappings:
		if mapping.status_code == str(status_code):
			return mapping.log_type
	
	# Fallback: odd-numbered punches of the day = OUT, even-numbered = IN
	# ZKTeco status codes: 0=Check-In, 1=Check-Out, 2=Break-Out, 3=Break-In, 4=OT-In, 5=OT-Out
	status_int = int(status_code) if str(status_code).isdigit() else -1
	if status_int in (1, 3, 5):  # Standard check-out codes
		return "OUT"
	return "IN"  # Default to IN for unknown/check-in codes


def convert_to_site_timezone(dt):
	"""Convert device datetime to site timezone"""
	settings = frappe.get_single("ZK Settings")
	device_tz = pytz.timezone(settings.timezone or "Asia/Dhaka")
	site_tz = pytz.timezone(frappe.utils.get_time_zone())
	
	# If dt is naive, localize to device timezone
	if dt.tzinfo is None:
		dt = device_tz.localize(dt)
	
	# Convert to site timezone and return naive
	return dt.astimezone(site_tz).replace(tzinfo=None)


def get_duplicate_tolerance():
	"""Get duplicate tolerance in seconds from settings"""
	settings = frappe.get_single("ZK Settings")
	return settings.duplicate_tolerance or 5


def encrypt_template(template_data):
	"""Encrypt fingerprint template (simplified - use proper encryption in production)"""
	from frappe.utils.password import encrypt
	return encrypt(template_data)


def decrypt_template(encrypted_data):
	"""Decrypt fingerprint template"""
	from frappe.utils.password import decrypt
	return decrypt(encrypted_data)
