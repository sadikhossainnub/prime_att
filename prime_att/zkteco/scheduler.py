"""
Scheduled tasks for ZK device management
"""

import frappe
from frappe.utils import now_datetime, add_to_date


@frappe.whitelist()
def mark_timeout_enrollments():
	"""
	Mark old enrollments as Timeout if they haven't completed
	Runs every 10 minutes
	"""
	settings = frappe.get_single("ZK Settings")
	timeout_seconds = settings.enrollment_timeout or 180
	
	# Calculate cutoff time
	cutoff = add_to_date(now_datetime(), seconds=-timeout_seconds)
	
	# Find old enrollments still in progress
	old_enrollments = frappe.get_all(
		"ZK Fingerprint Enrollment",
		filters={
			"status": ["in", ["Queued", "Sent", "Waiting for User"]],
			"creation": ["<", cutoff]
		},
		fields=["name"]
	)
	
	for enrollment in old_enrollments:
		doc = frappe.get_doc("ZK Fingerprint Enrollment", enrollment.name)
		doc.status = "Timeout"
		doc.add_comment("Comment", f"Enrollment timed out after {timeout_seconds} seconds")
		doc.save(ignore_permissions=True)
	
	if old_enrollments:
		frappe.db.commit()
		frappe.log_error(
			f"Marked {len(old_enrollments)} enrollments as Timeout",
			"Enrollment Timeout Cleanup"
		)


@frappe.whitelist()
def mark_timeout_commands():
	"""
	Mark old commands as Timeout if device hasn't responded
	Runs every 5 minutes
	"""
	settings = frappe.get_single("ZK Settings")
	timeout_seconds = settings.command_timeout or 120
	
	# Calculate cutoff time
	cutoff = add_to_date(now_datetime(), seconds=-timeout_seconds)
	
	# Find old commands still pending
	old_commands = frappe.get_all(
		"ZK Device Command",
		filters={
			"status": ["in", ["Queued", "Sent"]],
			"modified": ["<", cutoff]
		},
		fields=["name"]
	)
	
	for command in old_commands:
		doc = frappe.get_doc("ZK Device Command", command.name)
		doc.status = "Timeout"
		doc.add_comment("Comment", f"Command timed out after {timeout_seconds} seconds")
		doc.save(ignore_permissions=True)
	
	if old_commands:
		frappe.db.commit()
		frappe.log_error(
			f"Marked {len(old_commands)} commands as Timeout",
			"Command Timeout Cleanup"
		)


@frappe.whitelist()
def cleanup_old_punches():
	"""
	Archive or clean up old ZK Punch records (optional maintenance)
	Runs daily - keep last 90 days by default
	"""
	# TODO: Make retention period configurable in ZK Settings
	retention_days = 90
	cutoff = add_to_date(now_datetime(), days=-retention_days)
	
	# Count old punches
	old_count = frappe.db.count("ZK Punch", {
		"punch_time": ["<", cutoff]
	})
	
	if old_count > 0:
		frappe.log_error(
			f"Found {old_count} old punch records (>{retention_days} days). "
			"Consider archiving or deleting them.",
			"Punch Cleanup Notice"
		)
