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
	"""
	Update device last activity timestamp
	Uses set_value with update_modified=False for efficiency
	"""
	try:
		updates = {"last_activity": now()}
		if pushver:
			updates["push_version"] = pushver
		if language:
			updates["language"] = language
		
		frappe.db.set_value("ZK Device", sn, updates, update_modified=False)
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


def send_command(device_sn, command, created_by=None, action_name=None):
	"""
	Queue a command for the device
	Returns command doc name
	"""
	if not action_name:
		action_name = derive_action_name(command)

	cmd = frappe.get_doc({
		"doctype": "ZK Device Command",
		"action_name": action_name,
		"device": device_sn,
		"command": command,
		"status": "Pending",
		"created_by": created_by or frappe.session.user
	})
	cmd.insert(ignore_permissions=True)
	frappe.db.commit()
	return cmd.name


def derive_action_name(command):
	"""Derive user-friendly action name from raw command string"""
	if "ENROLL_FP" in command:
		return "Fingerprint Enrollment"
	elif "UPDATE USERINFO" in command:
		return "Push / Update User"
	elif "DELETE USERINFO" in command:
		return "Delete User"
	elif "QUERY USERINFO" in command:
		return "Pull Users from Device"
	elif "QUERY ATTLOG" in command:
		return "Fetch Attendance Logs"
	elif "SET OPTIONS" in command or "DateTime" in command:
		return "Sync Time / Settings"
	elif "REBOOT" in command:
		return "Restart Device"
	elif "CLEAR LOG" in command:
		return "Clear Attendance Log"
	return "Custom Device Action"


@frappe.whitelist()
def restart_device(device_sn):
	"""
	Send reboot command to device
	
	Roles: ZK Admin, System Manager only
	"""
	frappe.only_for("ZK Admin", "System Manager")
	
	cmd_id = send_command(device_sn, "REBOOT", action_name="Restart Device")
	frappe.msgprint(_("Restart command has been queued for {0}.").format(device_sn), indicator="blue")
	return cmd_id


@frappe.whitelist()
def sync_device_time(device_sn):
	"""
	Sync current server time to device
	
	Roles: ZK Admin, System Manager only
	"""
	frappe.only_for("ZK Admin", "System Manager")
	
	# Format for ZKTeco time sync: SET OPTIONS DateTime=YYYY-MM-DD HH:MM:SS
	current_time = frappe.utils.now()
	cmd = f"SET OPTIONS DateTime={current_time}"
	cmd_id = send_command(device_sn, cmd, action_name="Sync Device Time")
	frappe.msgprint(_("Time sync command has been queued ({0}).").format(current_time), indicator="green")
	return cmd_id


@frappe.whitelist()
def sync_all_users_to_device(device_sn):
	"""
	Push all active ZK Person records to this device
	Skips placeholder persons (auto-created from unknown PINs)
	
	Roles: ZK Admin, System Manager only
	"""
	frappe.only_for("ZK Admin", "System Manager")
	
	# Filter out placeholder persons
	persons = frappe.get_all(
		"ZK Person", 
		filters={
			"is_active": 1,
			"is_placeholder": ["!=", 1]  # Skip placeholders
		}, 
		fields=["name", "pin", "full_name", "privilege", "card_no"]
	)
	
	if not persons:
		frappe.msgprint(_("No active persons found to sync."))
		return 0
	
	count = 0
	for p in persons:
		cmd = f"DATA UPDATE USERINFO PIN={p.pin}\tName={p.full_name or ''}\tPrivilege={p.privilege or '0'}\tPassword=\tCard={p.card_no or ''}"
		send_command(device_sn, cmd, action_name=f"Push User ({p.full_name or p.pin})")
		count += 1
	
	frappe.msgprint(_("Queued sync for {0} users to device {1}.").format(count, device_sn), indicator="green")
	return count


@frappe.whitelist()
def fetch_punches_from_device(device_sn):
	"""
	Request device to send attendance logs (punches)
	
	Roles: ZK Admin, System Manager, ZK Operator
	"""
	frappe.only_for("ZK Admin", "System Manager", "ZK Operator")
	
	# Get command template from settings
	settings = frappe.get_single("ZK Settings")
	cmd = settings.cmd_fetch_attlog or "DATA QUERY ATTLOG"
	
	cmd_id = send_command(device_sn, cmd, action_name="Fetch Attendance Logs")
	frappe.msgprint(
		_("Punch fetch command queued for device {0}. Punches will appear shortly.").format(device_sn),
		indicator="blue"
	)
	return cmd_id
