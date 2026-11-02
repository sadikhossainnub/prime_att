"""
Installation helper functions
"""

import frappe
import json


def setup_defaults():
	"""Create default settings"""
	
	try:
		# ZK Settings
		if not frappe.db.exists("ZK Settings", "ZK Settings"):
			settings = frappe.get_doc({
				"doctype": "ZK Settings",
				"timezone": "Asia/Dhaka",
				"duplicate_tolerance": 5,
				"rate_limit_requests": 60
			})
			
			# Add default status mappings
			settings.append("status_mappings", {
				"status_code": "0",
				"log_type": "IN",
				"description": "Check In"
			})
			settings.append("status_mappings", {
				"status_code": "1",
				"log_type": "OUT",
				"description": "Check Out"
			})
			settings.append("status_mappings", {
				"status_code": "2",
				"log_type": "OUT",
				"description": "Break Out"
			})
			settings.append("status_mappings", {
				"status_code": "3",
				"log_type": "IN",
				"description": "Break In"
			})
			settings.append("status_mappings", {
				"status_code": "4",
				"log_type": "OUT",
				"description": "Overtime Out"
			})
			settings.append("status_mappings", {
				"status_code": "5",
				"log_type": "IN",
				"description": "Overtime In"
			})
			
			settings.insert(ignore_permissions=True)
			print("✓ Created ZK Settings with default status mappings")
	except Exception as e:
		print(f"Note: ZK Settings - {str(e)}")
	
	try:
		# ZK Sync Connector
		if not frappe.db.exists("ZK Sync Connector", "ZK Sync Connector"):
			connector = frappe.get_doc({
				"doctype": "ZK Sync Connector",
				"mode": "Disabled",
				"auto_sync": 1,
				"batch_size": 100
			})
			connector.insert(ignore_permissions=True)
			print("✓ Created ZK Sync Connector")
	except Exception as e:
		print(f"Note: ZK Sync Connector - {str(e)}")
	
	# Create sample command templates
	try:
		create_command_templates()
	except Exception as e:
		print(f"Note: Command templates will be created after DocTypes are set up - {str(e)}")
	
	frappe.db.commit()


def create_command_templates():
	"""Create sample command templates for common devices"""
	
	# Check if DocType exists first
	if not frappe.db.exists("DocType", "ZK Command Template"):
		print("Note: ZK Command Template DocType not created yet, skipping template creation")
		return
	
	templates = [
		{
			"device_model": "F18",
			"command_type": "ENROLL_FP",
			"command_template": "DATA ENROLL_FP PIN={pin}\tFID={fid}\tRETRY={retry}\tOVERWRITE={overwrite}",
			"description": "ZKTeco F18 fingerprint enrollment"
		},
		{
			"device_model": "K40",
			"command_type": "ENROLL_FP",
			"command_template": "DATA ENROLL_FP PIN={pin}\tFID={fid}\tRETRY={retry}\tOVERWRITE={overwrite}",
			"description": "ZKTeco K40 fingerprint enrollment"
		},
		{
			"device_model": "Generic",
			"command_type": "DATA_UPDATE",
			"command_template": "DATA UPDATE USERINFO PIN={pin}\tName={name}\tPrivilege={privilege}\tCard={card}",
			"description": "Generic user info update"
		},
		{
			"device_model": "Generic",
			"command_type": "DATA_DELETE",
			"command_template": "DATA DELETE USERINFO PIN={pin}",
			"description": "Generic user deletion"
		},
		{
			"device_model": "Generic",
			"command_type": "DATA_QUERY",
			"command_template": "DATA QUERY USERINFO",
			"description": "Query all users"
		}
	]
	
	for template in templates:
		try:
			if not frappe.db.exists("ZK Command Template", {
				"device_model": template["device_model"],
				"command_type": template["command_type"]
			}):
				doc = frappe.get_doc({
					"doctype": "ZK Command Template",
					**template
				})
				doc.insert(ignore_permissions=True)
				print(f"✓ Created command template: {template['device_model']} - {template['command_type']}")
		except Exception as e:
			print(f"Note: Could not create template {template['device_model']} - {str(e)}")


def setup_roles():
	"""Set up default roles"""
	
	# Create roles if they don't exist
	roles = [
		{
			"role_name": "ZK Admin",
			"desk_access": 1
		},
		{
			"role_name": "ZK Operator",
			"desk_access": 1
		}
	]
	
	for role in roles:
		if not frappe.db.exists("Role", role["role_name"]):
			doc = frappe.get_doc({
				"doctype": "Role",
				"role_name": role["role_name"],
				"desk_access": role["desk_access"]
			})
			doc.insert(ignore_permissions=True)
			print(f"✓ Created role: {role['role_name']}")
	
	# Add Administrator to ZK Admin role
	if not frappe.db.exists("Has Role", {
		"parent": "Administrator",
		"role": "ZK Admin"
	}):
		admin = frappe.get_doc("User", "Administrator")
		admin.append("roles", {
			"role": "ZK Admin"
		})
		admin.save(ignore_permissions=True)
		print("✓ Added Administrator to ZK Admin role")
	
	frappe.db.commit()


def after_install():
	"""Run after app installation"""
	# Create DocTypes first
	create_all_doctypes()
	
	# Then setup defaults and roles
	setup_defaults()
	setup_roles()
	print("\n✓ Prime Att installation completed successfully!")


def before_uninstall():
	"""Clean up before uninstalling"""
	# Add any cleanup logic here
	pass



def create_all_doctypes():
	"""Create all required doctypes"""
	doctypes = get_doctype_definitions()
	
	for doctype_name, definition in doctypes.items():
		create_doctype(doctype_name, definition)
	
	frappe.db.commit()
	print("✓ All doctypes created successfully!")


def create_doctype(doctype_name, definition):
	"""Create or update a doctype"""
	try:
		if frappe.db.exists("DocType", doctype_name):
			print(f"DocType {doctype_name} already exists, skipping...")
			return
		
		doc = frappe.get_doc(definition)
		doc.insert(ignore_permissions=True)
		print(f"✓ Created DocType: {doctype_name}")
		
	except Exception as e:
		print(f"Error creating {doctype_name}: {str(e)}")
		frappe.log_error(frappe.get_traceback(), f"DocType Creation Error - {doctype_name}")


def get_doctype_definitions():
	"""Return all doctype definitions in correct order (child tables first)"""
	return {
		# Child tables first
		"ZK Status Mapping": get_zk_status_mapping_def(),
		"ZK Person Device": get_zk_person_device_def(),
		
		# Then main DocTypes that don't depend on others
		"ZK Device": get_zk_device_def(),
		"ZK Device Command": get_zk_device_command_def(),
		"ZK Command Template": get_zk_command_template_def(),
		"ZK Raw Log": get_zk_raw_log_def(),
		"ZK Punch": get_zk_punch_def(),
		"ZK Operation Log": get_zk_operation_log_def(),
		
		# Then DocTypes that depend on others
		"ZK Person": get_zk_person_def(),
		"ZK Fingerprint Enrollment": get_zk_fingerprint_enrollment_def(),
		"ZK Check-in Out": get_zk_checkin_out_def(),
		"ZK Sync Log": get_zk_sync_log_def(),
		
		# Finally Single DocTypes with child tables
		"ZK Settings": get_zk_settings_def(),
		"ZK Sync Connector": get_zk_sync_connector_def(),
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
