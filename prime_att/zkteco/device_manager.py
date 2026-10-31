"""
Device management functions
"""

import frappe
from frappe import _
from frappe.utils import now, add_to_date, get_datetime


def register_device(sn):
	"""Auto-register unknown device with Pending status"""
	try:
		device = frappe.get_doc({
			"doctype": "ZK Device",
			"name": sn,
			"serial_number": sn,
			"status": "Pending",
			"device_name": f"Device {sn}",
			"last_activity": now()
		})
		device.insert(ignore_permissions=True)
		frappe.db.commit()
		return device
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Failed to register device {sn}")
		return None


def update_device_activity(sn, pushver=None, language=None):
	"""Update device last activity timestamp"""
	try:
		device = frappe.get_doc("ZK Device", sn)
		device.last_activity = now()
		if pushver:
			device.push_version = pushver
		if language:
			device.language = language
		device.save(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Failed to update device activity for {sn}")


def get_device_config(device):
	"""Get device configuration for handshake response"""
	
	# Check if there are pending enrollment commands - use short poll interval
	has_pending_enrollment = frappe.db.exists(
		"ZK Fingerprint Enrollment",
		{
			"device": device.name,
			"status": ["in", ["Queued", "Sent", "Waiting for User"]]
		}
	)
	
	delay = device.poll_interval_short if has_pending_enrollment else device.poll_interval
	
	return {
		"stamp": device.stamp or 9999,
		"opstamp": device.opstamp or 9999,
		"error_delay": device.error_delay or 120,
		"delay": delay or 30,
	}


def poll_devices():
	"""
	Scheduled task to check device online/offline status
	Runs every minute
	"""
	devices = frappe.get_all(
		"ZK Device",
		filters={"status": ["in", ["Active", "Pending"]]},
		fields=["name", "serial_number", "last_activity", "poll_interval"]
	)
	
	for device in devices:
		if device.last_activity:
			poll_interval = device.poll_interval or 30
			offline_threshold = add_to_date(device.last_activity, seconds=poll_interval * 3)
			
			if get_datetime(now()) > offline_threshold:
				# Mark device as offline
				frappe.db.set_value("ZK Device", device.name, "is_online", 0)
			else:
				frappe.db.set_value("ZK Device", device.name, "is_online", 1)
	
	frappe.db.commit()


def send_command(device_sn, command, created_by=None):
	"""
	Queue a command for the device
	Returns command doc name
	"""
	cmd = frappe.get_doc({
		"doctype": "ZK Device Command",
		"device": device_sn,
		"command": command,
		"status": "Pending",
		"created_by": created_by or frappe.session.user
	})
	cmd.insert(ignore_permissions=True)
	frappe.db.commit()
	return cmd.name
