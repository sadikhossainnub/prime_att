"""
Installation helper functions
"""

import frappe


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
	setup_defaults()
	setup_roles()
	print("\n✓ Prime Att installation completed successfully!")


def before_uninstall():
	"""Clean up before uninstalling"""
	# Add any cleanup logic here
	pass
