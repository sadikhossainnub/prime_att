"""
Fingerprint enrollment management
"""

import frappe
from frappe import _
from prime_att.zkteco.device_manager import send_command


@frappe.whitelist()
def enroll_fingerprint(person_name, device_sn, finger_index, overwrite=1):
	"""
	Start fingerprint enrollment process
	1. Ensure user exists on device (push USERINFO if needed)
	2. Send ENROLL_FP command
	3. Device enters enrollment mode
	4. Store enrollment record
	"""
	person = frappe.get_doc("ZK Person", person_name)
	device = frappe.get_doc("ZK Device", device_sn)
	
	# Validate finger index
	if not (0 <= int(finger_index) <= 9):
		frappe.throw(_("Finger index must be between 0 and 9"))
	
	# Check if user exists on device
	device_status = None
	for dev in person.devices:
		if dev.device == device_sn:
			device_status = dev.status
			break
	
	if device_status not in ["Pushed", "Enrolled"]:
		# Push user info first
		push_userinfo_to_device(person, device)
	
	# Create enrollment record
	enrollment = frappe.get_doc({
		"doctype": "ZK Fingerprint Enrollment",
		"person": person_name,
		"person_pin": person.pin,
		"device": device_sn,
		"finger_index": str(finger_index),
		"status": "Queued",
		"overwrite": int(overwrite),
		"retry_count": 3
	})
	enrollment.insert()
	frappe.db.commit()
	
	# Send enrollment command
	send_enrollment_command(enrollment, device)
	
	return enrollment.name


def send_enrollment_command(enrollment, device):
	"""
	Send ENROLL_FP command to device
	Command format is configurable per device
	"""
	# Get command template
	template = get_enrollment_command_template(device)
	
	# Build command
	command = template.format(
		pin=enrollment.person_pin,
		fid=enrollment.finger_index,
		retry=enrollment.retry_count,
		overwrite=enrollment.overwrite
	)
	
	# Send command
	cmd_id = send_command(device.name, command, frappe.session.user)
	
	# Update enrollment
	enrollment.command = cmd_id
	enrollment.status = "Sent"
	enrollment.save(ignore_permissions=True)
	frappe.db.commit()


def get_enrollment_command_template(device):
	"""
	Get enrollment command template for device
	Falls back to default if not configured
	"""
	if device.enrollment_command_template:
		return device.enrollment_command_template
	
	# Check for template based on device model/firmware
	if device.device_model:
		template = frappe.db.get_value(
			"ZK Command Template",
			{"device_model": device.device_model, "command_type": "ENROLL_FP"},
			"command_template"
		)
		if template:
			return template
	
	# Default template
	return "DATA ENROLL_FP PIN={pin}\tFID={fid}\tRETRY={retry}\tOVERWRITE={overwrite}"


@frappe.whitelist()
def push_to_devices(person_name, device_list=None):
	"""
	Push user info to selected devices
	If device_list is None, push to all configured devices
	"""
	person = frappe.get_doc("ZK Person", person_name)
	
	if not device_list:
		device_list = [dev.device for dev in person.devices]
	elif isinstance(device_list, str):
		import json
		device_list = json.loads(device_list)
	
	results = []
	for device_sn in device_list:
		try:
			device = frappe.get_doc("ZK Device", device_sn)
			push_userinfo_to_device(person, device)
			results.append({"device": device_sn, "status": "Success"})
		except Exception as e:
			results.append({"device": device_sn, "status": "Failed", "error": str(e)})
			frappe.log_error(frappe.get_traceback(), f"Failed to push to device {device_sn}")
	
	frappe.db.commit()
	return results


def push_userinfo_to_device(person, device):
	"""
	Send DATA UPDATE USERINFO command to device
	Format: PIN	Name	Privilege	Password	Card
	"""
	command = f"DATA UPDATE USERINFO PIN={person.pin}\tName={person.full_name or ''}\t"\
	          f"Privilege={person.privilege or '0'}\tPassword=\tCard={person.card_no or ''}"
	
	cmd_id = send_command(device.name, command, frappe.session.user)
	
	# Update person device status
	device_found = False
	for dev in person.devices:
		if dev.device == device.name:
			dev.status = "Pending"
			dev.last_pushed = frappe.utils.now()
			device_found = True
			break
	
	if not device_found:
		person.append("devices", {
			"device": device.name,
			"status": "Pending",
			"last_pushed": frappe.utils.now()
		})
	
	person.save(ignore_permissions=True)


@frappe.whitelist()
def delete_user_from_device(person_name, device_sn):
	"""Delete user from device"""
	person = frappe.get_doc("ZK Person", person_name)
	device = frappe.get_doc("ZK Device", device_sn)
	
	command = f"DATA DELETE USERINFO PIN={person.pin}"
	cmd_id = send_command(device.name, command, frappe.session.user)
	
	# Update person device status
	for dev in person.devices:
		if dev.device == device.name:
			person.remove(dev)
			break
	
	person.save()
	frappe.msgprint(_("Delete command sent to device"))


@frappe.whitelist()
def pull_users_from_device(device_sn):
	"""
	Request device to send all user info
	Command: DATA QUERY USERINFO
	"""
	device = frappe.get_doc("ZK Device", device_sn)
	command = "DATA QUERY USERINFO"
	cmd_id = send_command(device.name, command, frappe.session.user)
	
	frappe.msgprint(_("Pull users command sent. Users will be created/updated when device responds."))
	return cmd_id


@frappe.whitelist()
def check_enrollment_status(enrollment_name):
	"""Check status of enrollment"""
	enrollment = frappe.get_doc("ZK Fingerprint Enrollment", enrollment_name)
	
	# Check command status
	if enrollment.command:
		cmd = frappe.get_doc("ZK Device Command", enrollment.command)
		if cmd.status == "Done" and enrollment.status == "Sent":
			enrollment.status = "Waiting for User"
			enrollment.save()
	
	return {
		"status": enrollment.status,
		"message": get_enrollment_status_message(enrollment)
	}


def get_enrollment_status_message(enrollment):
	"""Get user-friendly status message"""
	messages = {
		"Queued": "Waiting to send command to device",
		"Sent": "Command sent, waiting for device confirmation",
		"Waiting for User": "Please place finger on device to enroll",
		"Enrolled": "Fingerprint enrolled successfully",
		"Timeout": "Enrollment timed out, please retry",
		"Failed": "Enrollment failed, please retry"
	}
	return messages.get(enrollment.status, enrollment.status)


@frappe.whitelist()
def bulk_map_employees():
	"""
	Bulk mapping tool - map unmapped persons to employees
	Returns list of unmapped persons
	"""
	# Get unmapped persons
	unmapped = frappe.get_all(
		"ZK Person",
		filters={
			"employee": ["is", "not set"],
			"is_active": 1
		},
		fields=["name", "pin", "full_name", "card_no"]
	)
	
	# Try to auto-map by attendance_device_id
	mapped_count = 0
	for person_info in unmapped:
		employee = frappe.db.get_value(
			"Employee",
			{"attendance_device_id": person_info.pin},
			"name"
		)
		if employee:
			frappe.db.set_value("ZK Person", person_info.name, "employee", employee)
			mapped_count += 1
	
	if mapped_count > 0:
		frappe.db.commit()
	
	# Get remaining unmapped
	unmapped = frappe.get_all(
		"ZK Person",
		filters={
			"employee": ["is", "not set"],
			"is_active": 1
		},
		fields=["name", "pin", "full_name", "card_no"]
	)
	
	return {
		"auto_mapped": mapped_count,
		"unmapped": unmapped
	}
