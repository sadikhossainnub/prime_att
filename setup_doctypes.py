#!/usr/bin/env python3
"""
Setup script to create all DocTypes for Prime Att
Run with: bench execute prime_att.setup_doctypes.create_all_doctypes
"""

import frappe
import json
import os


def create_all_doctypes():
	"""Create all required doctypes"""
	doctypes = get_doctype_definitions()
	
	for doctype_name, definition in doctypes.items():
		create_doctype(doctype_name, definition)
	
	frappe.db.commit()
	print("All doctypes created successfully!")


def create_doctype(doctype_name, definition):
	"""Create or update a doctype"""
	try:
		if frappe.db.exists("DocType", doctype_name):
			print(f"DocType {doctype_name} already exists, skipping...")
			return
		
		doc = frappe.get_doc(definition)
		doc.insert(ignore_permissions=True)
		print(f"Created DocType: {doctype_name}")
		
	except Exception as e:
		print(f"Error creating {doctype_name}: {str(e)}")
		frappe.log_error(frappe.get_traceback(), f"DocType Creation Error - {doctype_name}")


def get_doctype_definitions():
	"""Return all doctype definitions"""
	return {
		"ZK Settings": get_zk_settings_def(),
		"ZK Status Mapping": get_zk_status_mapping_def(),
		"ZK Device": get_zk_device_def(),
		"ZK Person": get_zk_person_def(),
		"ZK Person Device": get_zk_person_device_def(),
		"ZK Device Command": get_zk_device_command_def(),
		"ZK Command Template": get_zk_command_template_def(),
		"ZK Fingerprint Enrollment": get_zk_fingerprint_enrollment_def(),
		"ZK Raw Log": get_zk_raw_log_def(),
		"ZK Punch": get_zk_punch_def(),
		"ZK Check-in Out": get_zk_checkin_out_def(),
		"ZK Operation Log": get_zk_operation_log_def(),
		"ZK Sync Connector": get_zk_sync_connector_def(),
		"ZK Sync Log": get_zk_sync_log_def(),
	}


def get_zk_settings_def():
	return {
		"doctype": "DocType",
		"name": "ZK Settings",
		"module": "Prime Attendance System",
		"issingle": 1,
		"is_submittable": 0,
		"fields": [
			{"fieldname": "timezone", "label": "Timezone", "fieldtype": "Select", "options": "Asia/Dhaka\nAsia/Kolkata\nAsia/Dubai\nAsia/Singapore\nUTC", "default": "Asia/Dhaka"},
			{"fieldname": "duplicate_tolerance", "label": "Duplicate Tolerance (seconds)", "fieldtype": "Int", "default": "5"},
			{"fieldname": "sb1", "fieldtype": "Section Break", "label": "Status Code Mapping"},
			{"fieldname": "status_mappings", "label": "Status Mappings", "fieldtype": "Table", "options": "ZK Status Mapping"},
			{"fieldname": "sb2", "fieldtype": "Section Break", "label": "Rate Limiting"},
			{"fieldname": "rate_limit_requests", "label": "Max Requests per Minute per Device", "fieldtype": "Int", "default": "60"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1, "write": 1, "create": 1}
		]
	}


def get_zk_status_mapping_def():
	return {
		"doctype": "DocType",
		"name": "ZK Status Mapping",
		"module": "Prime Attendance System",
		"istable": 1,
		"fields": [
			{"fieldname": "status_code", "label": "Status Code", "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "log_type", "label": "Log Type", "fieldtype": "Select", "options": "IN\nOUT", "in_list_view": 1},
			{"fieldname": "description", "label": "Description", "fieldtype": "Data", "in_list_view": 1},
		]
	}


def get_zk_device_def():
	return {
		"doctype": "DocType",
		"name": "ZK Device",
		"module": "Prime Attendance System",
		"naming_rule": "By fieldname",
		"autoname": "field:serial_number",
		"fields": [
			{"fieldname": "serial_number", "label": "Serial Number", "fieldtype": "Data", "reqd": 1, "unique": 1},
			{"fieldname": "device_name", "label": "Device Name", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending\nActive\nBlocked", "default": "Pending", "in_list_view": 1},
			{"fieldname": "is_online", "label": "Is Online", "fieldtype": "Check", "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "device_model", "label": "Device Model", "fieldtype": "Data"},
			{"fieldname": "location", "label": "Location", "fieldtype": "Data"},
			{"fieldname": "ip_address", "label": "IP Address", "fieldtype": "Data"},
			
			{"fieldname": "sb1", "fieldtype": "Section Break", "label": "Configuration"},
			{"fieldname": "comm_key", "label": "Communication Key", "fieldtype": "Password"},
			{"fieldname": "poll_interval", "label": "Poll Interval (seconds)", "fieldtype": "Int", "default": "30"},
			{"fieldname": "poll_interval_short", "label": "Short Poll Interval (seconds)", "fieldtype": "Int", "default": "5", "description": "Used during enrollment"},
			{"fieldname": "cb2", "fieldtype": "Column Break"},
			{"fieldname": "error_delay", "label": "Error Delay (seconds)", "fieldtype": "Int", "default": "120"},
			{"fieldname": "stamp", "label": "Stamp", "fieldtype": "Int", "default": "9999"},
			{"fieldname": "opstamp", "label": "OpStamp", "fieldtype": "Int", "default": "9999"},
			
			{"fieldname": "sb2", "fieldtype": "Section Break", "label": "Device Info"},
			{"fieldname": "push_version", "label": "Push Version", "fieldtype": "Data", "read_only": 1},
			{"fieldname": "language", "label": "Language", "fieldtype": "Data", "read_only": 1},
			{"fieldname": "last_activity", "label": "Last Activity", "fieldtype": "Datetime", "read_only": 1},
			{"fieldname": "cb3", "fieldtype": "Column Break"},
			{"fieldname": "enrollment_command_template", "label": "Enrollment Command Template", "fieldtype": "Small Text", "description": "Override default enrollment command. Use {pin}, {fid}, {retry}, {overwrite}"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "ZK Operator", "read": 1}
		]
	}


def get_zk_person_def():
	return {
		"doctype": "DocType",
		"name": "ZK Person",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "pin", "label": "PIN", "fieldtype": "Data", "reqd": 1, "unique": 1, "in_list_view": 1},
			{"fieldname": "full_name", "label": "Full Name", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "card_no", "label": "Card Number", "fieldtype": "Data"},
			{"fieldname": "privilege", "label": "Privilege", "fieldtype": "Select", "options": "0\n1\n2\n3", "default": "0", "description": "0=User, 1=Enroller, 2=Admin, 3=Super Admin"},
			{"fieldname": "is_active", "label": "Is Active", "fieldtype": "Check", "default": 1, "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "employee", "label": "Employee", "fieldtype": "Data", "description": "ERPNext Employee ID"},
			
			{"fieldname": "sb1", "fieldtype": "Section Break", "label": "Device Registration"},
			{"fieldname": "devices", "label": "Devices", "fieldtype": "Table", "options": "ZK Person Device"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1, "write": 1, "create": 1, "delete": 1},
			{"role": "ZK Operator", "read": 1, "write": 1, "create": 1}
		]
	}


def get_zk_person_device_def():
	return {
		"doctype": "DocType",
		"name": "ZK Person Device",
		"module": "Prime Attendance System",
		"istable": 1,
		"fields": [
			{"fieldname": "device", "label": "Device", "fieldtype": "Link", "options": "ZK Device", "in_list_view": 1},
			{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Not Pushed\nPending\nPushed\nEnrolled", "default": "Not Pushed", "in_list_view": 1},
			{"fieldname": "last_pushed", "label": "Last Pushed", "fieldtype": "Datetime", "in_list_view": 1},
		]
	}


def get_zk_device_command_def():
	return {
		"doctype": "DocType",
		"name": "ZK Device Command",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "device", "label": "Device", "fieldtype": "Link", "options": "ZK Device", "reqd": 1, "in_list_view": 1},
			{"fieldname": "command", "label": "Command", "fieldtype": "Small Text", "reqd": 1},
			{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Pending\nSent\nDone\nFailed", "default": "Pending", "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "created_by", "label": "Created By", "fieldtype": "Link", "options": "User", "default": "user"},
			
			{"fieldname": "sb1", "fieldtype": "Section Break"},
			{"fieldname": "sent_time", "label": "Sent Time", "fieldtype": "Datetime", "read_only": 1},
			{"fieldname": "completed_time", "label": "Completed Time", "fieldtype": "Datetime", "read_only": 1},
			{"fieldname": "response", "label": "Response", "fieldtype": "Text", "read_only": 1},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1, "write": 1, "create": 1},
			{"role": "ZK Operator", "read": 1}
		]
	}


def get_zk_command_template_def():
	return {
		"doctype": "DocType",
		"name": "ZK Command Template",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "device_model", "label": "Device Model", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "command_type", "label": "Command Type", "fieldtype": "Select", "options": "ENROLL_FP\nDATA_UPDATE\nDATA_DELETE\nDATA_QUERY", "reqd": 1, "in_list_view": 1},
			{"fieldname": "command_template", "label": "Command Template", "fieldtype": "Small Text", "reqd": 1},
			{"fieldname": "description", "label": "Description", "fieldtype": "Text"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1, "write": 1, "create": 1}
		]
	}


def get_zk_fingerprint_enrollment_def():
	return {
		"doctype": "DocType",
		"name": "ZK Fingerprint Enrollment",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "person", "label": "Person", "fieldtype": "Link", "options": "ZK Person", "reqd": 1, "in_list_view": 1},
			{"fieldname": "person_pin", "label": "Person PIN", "fieldtype": "Data", "reqd": 1},
			{"fieldname": "device", "label": "Device", "fieldtype": "Link", "options": "ZK Device", "reqd": 1, "in_list_view": 1},
			{"fieldname": "finger_index", "label": "Finger Index (0-9)", "fieldtype": "Select", "options": "0\n1\n2\n3\n4\n5\n6\n7\n8\n9", "reqd": 1, "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "status", "label": "Status", "fieldtype": "Select", "options": "Queued\nSent\nWaiting for User\nEnrolled\nTimeout\nFailed", "default": "Queued", "in_list_view": 1},
			
			{"fieldname": "sb1", "fieldtype": "Section Break"},
			{"fieldname": "command", "label": "Command", "fieldtype": "Link", "options": "ZK Device Command"},
			{"fieldname": "overwrite", "label": "Overwrite Existing", "fieldtype": "Check", "default": 1},
			{"fieldname": "retry_count", "label": "Retry Count", "fieldtype": "Int", "default": 3},
			{"fieldname": "cb2", "fieldtype": "Column Break"},
			{"fieldname": "enrolled_time", "label": "Enrolled Time", "fieldtype": "Datetime"},
			{"fieldname": "template_data", "label": "Template Data", "fieldtype": "Password", "read_only": 1},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1, "write": 1, "create": 1},
			{"role": "ZK Operator", "read": 1, "write": 1, "create": 1}
		]
	}


def get_zk_raw_log_def():
	return {
		"doctype": "DocType",
		"name": "ZK Raw Log",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "device", "label": "Device", "fieldtype": "Link", "options": "ZK Device", "in_list_view": 1},
			{"fieldname": "log_type", "label": "Log Type", "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "received_at", "label": "Received At", "fieldtype": "Datetime", "in_list_view": 1},
			{"fieldname": "payload", "label": "Payload", "fieldtype": "Long Text"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1}
		]
	}


def get_zk_punch_def():
	return {
		"doctype": "DocType",
		"name": "ZK Punch",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "device", "label": "Device", "fieldtype": "Link", "options": "ZK Device", "reqd": 1, "in_list_view": 1},
			{"fieldname": "pin", "label": "PIN", "fieldtype": "Data", "reqd": 1, "in_list_view": 1},
			{"fieldname": "punch_time", "label": "Punch Time", "fieldtype": "Datetime", "reqd": 1, "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "status_code", "label": "Status Code", "fieldtype": "Data"},
			{"fieldname": "verify_type", "label": "Verify Type", "fieldtype": "Data"},
			{"fieldname": "workcode", "label": "Work Code", "fieldtype": "Data"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1},
			{"role": "ZK Operator", "read": 1}
		]
	}


def get_zk_checkin_out_def():
	return {
		"doctype": "DocType",
		"name": "ZK Check-in Out",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "person", "label": "Person", "fieldtype": "Link", "options": "ZK Person", "reqd": 1, "in_list_view": 1},
			{"fieldname": "log_time", "label": "Log Time", "fieldtype": "Datetime", "reqd": 1, "in_list_view": 1},
			{"fieldname": "log_type", "label": "Log Type", "fieldtype": "Select", "options": "IN\nOUT", "reqd": 1, "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "device", "label": "Device", "fieldtype": "Link", "options": "ZK Device"},
			{"fieldname": "punch_record", "label": "Punch Record", "fieldtype": "Link", "options": "ZK Punch"},
			
			{"fieldname": "sb1", "fieldtype": "Section Break", "label": "Sync Status"},
			{"fieldname": "sync_status", "label": "Sync Status", "fieldtype": "Select", "options": "Pending\nNo Mapping\nSynced\nFailed", "default": "Pending", "in_list_view": 1},
			{"fieldname": "synced_checkin_id", "label": "Synced Checkin ID", "fieldtype": "Data"},
			{"fieldname": "cb2", "fieldtype": "Column Break"},
			{"fieldname": "synced_at", "label": "Synced At", "fieldtype": "Datetime"},
			{"fieldname": "retry_count", "label": "Retry Count", "fieldtype": "Int", "default": 0},
			{"fieldname": "sync_error", "label": "Sync Error", "fieldtype": "Text"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1},
			{"role": "ZK Operator", "read": 1}
		]
	}


def get_zk_operation_log_def():
	return {
		"doctype": "DocType",
		"name": "ZK Operation Log",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "device", "label": "Device", "fieldtype": "Link", "options": "ZK Device", "in_list_view": 1},
			{"fieldname": "admin_pin", "label": "Admin PIN", "fieldtype": "Data", "in_list_view": 1},
			{"fieldname": "operation_time", "label": "Operation Time", "fieldtype": "Datetime", "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "operation_id", "label": "Operation ID", "fieldtype": "Data"},
			{"fieldname": "operation_object", "label": "Operation Object", "fieldtype": "Data"},
			{"fieldname": "extra_data", "label": "Extra Data", "fieldtype": "Data"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1}
		]
	}


def get_zk_sync_connector_def():
	return {
		"doctype": "DocType",
		"name": "ZK Sync Connector",
		"module": "Prime Attendance System",
		"issingle": 1,
		"fields": [
			{"fieldname": "mode", "label": "Mode", "fieldtype": "Select", "options": "Disabled\nLocal HRMS\nRemote ERPNext", "default": "Disabled", "reqd": 1},
			{"fieldname": "auto_sync", "label": "Auto Sync", "fieldtype": "Check", "default": 1},
			{"fieldname": "sync_from_date", "label": "Sync From Date", "fieldtype": "Date"},
			{"fieldname": "batch_size", "label": "Batch Size", "fieldtype": "Int", "default": 100},
			
			{"fieldname": "sb1", "fieldtype": "Section Break", "label": "Remote Configuration", "depends_on": "eval:doc.mode=='Remote ERPNext'"},
			{"fieldname": "remote_url", "label": "Remote URL", "fieldtype": "Data", "description": "e.g., https://erpnext.example.com"},
			{"fieldname": "api_key", "label": "API Key", "fieldtype": "Data"},
			{"fieldname": "api_secret", "label": "API Secret", "fieldtype": "Password"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1, "write": 1}
		]
	}


def get_zk_sync_log_def():
	return {
		"doctype": "DocType",
		"name": "ZK Sync Log",
		"module": "Prime Attendance System",
		"fields": [
			{"fieldname": "checkin", "label": "Check-in", "fieldtype": "Link", "options": "ZK Check-in Out", "in_list_view": 1},
			{"fieldname": "person", "label": "Person", "fieldtype": "Link", "options": "ZK Person", "in_list_view": 1},
			{"fieldname": "log_time", "label": "Log Time", "fieldtype": "Datetime", "in_list_view": 1},
			{"fieldname": "cb1", "fieldtype": "Column Break"},
			{"fieldname": "sync_status", "label": "Sync Status", "fieldtype": "Select", "options": "Success\nFailed", "in_list_view": 1},
			{"fieldname": "target_doc", "label": "Target Document", "fieldtype": "Data"},
			{"fieldname": "error_message", "label": "Error Message", "fieldtype": "Text"},
			{"fieldname": "synced_at", "label": "Synced At", "fieldtype": "Datetime"},
		],
		"permissions": [
			{"role": "ZK Admin", "read": 1}
		]
	}


if __name__ == "__main__":
	create_all_doctypes()
