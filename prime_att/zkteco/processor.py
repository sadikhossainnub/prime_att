"""
Background processor for device data
"""

import frappe
from frappe import _
from frappe.utils import now, get_datetime
from prime_att.zkteco.parser import parse_attlog, parse_operlog, parse_userinfo, parse_fingertmp
import pytz


def get_or_create_person(pin, is_placeholder=True):
	"""
	Get existing person or create new one with DuplicateEntryError handling
	Returns person name
	"""
	# First try to get existing
	person_name = frappe.db.get_value("ZK Person", {"pin": pin}, "name")
	if person_name:
		return person_name
	
	# Try to create new
	try:
		person_doc = frappe.get_doc({
			"doctype": "ZK Person",
			"pin": pin,
			"full_name": f"User {pin}",
			"is_active": 1,
			"is_placeholder": 1 if is_placeholder else 0
		})
		person_doc.insert(ignore_permissions=True)
		frappe.db.commit()
		return person_doc.name
		
	except frappe.exceptions.DuplicateEntryError:
		# Another process created it concurrently - fetch it
		frappe.db.rollback()
		person_name = frappe.db.get_value("ZK Person", {"pin": pin}, "name")
		if person_name:
			return person_name
		# Still not found? Log error and raise
		frappe.log_error(f"Failed to get or create person with PIN {pin}", "Person Creation Error")
		raise


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
					"is_active": 1,
					"is_placeholder": 0  # Device pushed user, not a placeholder
				})
				person.insert(ignore_permissions=True)
			
			# Update fields
			person.full_name = record['name'] or person.full_name or f"User {record['pin']}"
			person.card_no = record['card_no'] or person.card_no
			person.privilege = record['privilege'] or person.privilege or "0"
			person.is_active = 1
			person.is_placeholder = 0  # Promote placeholder if it was one
			
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
			# Get or create person (handles concurrent creation)
			person_name = get_or_create_person(record['pin'], is_placeholder=True)
			
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
		# Get or create person (handles concurrent creation)
		person = get_or_create_person(punch.pin, is_placeholder=True)
		
		# Determine log type (IN/OUT) - pass pin and device for alternate/first-last modes
		log_type = get_log_type_from_status(
			punch.status_code, 
			punch.punch_time,
			person_pin=punch.pin,
			device=punch.device
		)
		
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


def get_log_type_from_status(status_code, punch_time, person_pin=None, device=None):
	"""
	Determine IN/OUT from status code and rules
	Supports three modes:
	1. Device Status Mapping - use status code mappings
	2. Alternate Per Person Per Day - odd=IN, even=OUT (first punch of day is IN)
	3. First/Last of Day - first punch=IN, last=OUT
	"""
	settings = frappe.get_single("ZK Settings")
	mode = settings.inout_mode or "Device Status Mapping"
	
	if mode == "Device Status Mapping":
		# Use status mappings from settings
		for mapping in settings.status_mappings:
			if mapping.status_code == str(status_code):
				return mapping.log_type
		
		# Fallback: standard ZKTeco status codes
		# 0=Check-In, 1=Check-Out, 2=Break-Out, 3=Break-In, 4=OT-In, 5=OT-Out
		status_int = int(status_code) if str(status_code).isdigit() else -1
		if status_int in (1, 3, 5):  # Standard check-out codes
			return "OUT"
		return "IN"  # Default to IN for unknown/check-in codes
	
	elif mode == "Alternate Per Person Per Day":
		# Count punches for this person on this day
		if not person_pin or not punch_time:
			return "IN"  # Safe fallback
		
		# Get date part only
		punch_date = frappe.utils.get_datetime(punch_time).date()
		
		# Count existing punches for this person on this date
		person_name = frappe.db.get_value("ZK Person", {"pin": person_pin}, "name")
		if not person_name:
			return "IN"  # First punch for unknown person
		
		count = frappe.db.count("ZK Check-in Out", {
			"person": person_name,
			"log_time": ["between", [
				f"{punch_date} 00:00:00",
				f"{punch_date} 23:59:59"
			]]
		})
		
		# First punch (count=0) = IN, then alternate
		return "IN" if count % 2 == 0 else "OUT"
	
	elif mode == "First/Last of Day":
		# First punch of day = IN, all others = OUT (simple rule)
		# More sophisticated: actually determine based on time proximity
		if not person_pin or not punch_time:
			return "IN"
		
		punch_date = frappe.utils.get_datetime(punch_time).date()
		person_name = frappe.db.get_value("ZK Person", {"pin": person_pin}, "name")
		if not person_name:
			return "IN"
		
		# Check if there are any punches earlier today
		earlier_punch = frappe.db.get_value("ZK Check-in Out", {
			"person": person_name,
			"log_time": ["between", [
				f"{punch_date} 00:00:00",
				punch_time
			]]
		}, "name")
		
		# If there's an earlier punch, this is OUT; otherwise IN
		return "OUT" if earlier_punch else "IN"
	
	# Default fallback
	return "IN"


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
