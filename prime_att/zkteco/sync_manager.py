"""
HRMS Sync Manager - handles both Local and Remote sync
"""

import frappe
from frappe import _
from frappe.utils import now, get_datetime
import requests
from requests.auth import HTTPBasicAuth
import json


def employee_doctype_available():
	"""Check if Employee DocType is available (ERPNext/HRMS installed)"""
	return frappe.db.table_exists("tabEmployee")


def sync_checkin(checkin_name):
	"""
	Sync a single check-in record to HRMS
	Called from processor after creating checkin
	"""
	try:
		checkin = frappe.get_doc("ZK Check-in Out", checkin_name)
		
		# Skip if already synced
		if checkin.sync_status == "Synced":
			return
		
		# Get connector settings
		connector = frappe.get_single("ZK Sync Connector")
		
		if connector.mode == "Disabled":
			return
		
		# Get person mapping
		person = frappe.get_doc("ZK Person", checkin.person)
		employee_id = get_employee_id(person)
		
		if not employee_id:
			checkin.sync_status = "No Mapping"
			checkin.sync_error = "Person not mapped to Employee"
			checkin.save(ignore_permissions=True)
			frappe.db.commit()
			return
		
		# Check if already synced (idempotent)
		if checkin.synced_checkin_id:
			checkin.sync_status = "Synced"
			checkin.save(ignore_permissions=True)
			frappe.db.commit()
			return
		
		# Sync based on mode
		if connector.mode == "Local HRMS":
			success, result = sync_local(checkin, employee_id)
		else:  # Remote ERPNext
			success, result = sync_remote(checkin, employee_id, connector)
		
		if success:
			checkin.sync_status = "Synced"
			checkin.synced_checkin_id = result
			checkin.sync_error = None
			checkin.synced_at = now()
		else:
			checkin.sync_status = "Failed"
			checkin.sync_error = result
			checkin.retry_count = (checkin.retry_count or 0) + 1
		
		checkin.save(ignore_permissions=True)
		frappe.db.commit()
		
		# Create sync log
		create_sync_log(checkin, success, result)
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), f"Sync failed for {checkin_name}")


def sync_local(checkin, employee_id):
	"""Sync to local HRMS (if installed)"""
	try:
		# Check if Employee DocType is available
		if not employee_doctype_available():
			return False, "Employee DocType not available (ERPNext/HRMS not installed)"
		
		# Check for duplicate
		existing = frappe.db.exists(
			"Employee Checkin",
			{
				"employee": employee_id,
				"time": checkin.log_time
			}
		)
		
		if existing:
			return True, existing
		
		# Create Employee Checkin
		emp_checkin = frappe.get_doc({
			"doctype": "Employee Checkin",
			"employee": employee_id,
			"log_type": checkin.log_type,
			"time": checkin.log_time,
			"device_id": checkin.device,
			"skip_auto_attendance": 0
		})
		emp_checkin.insert(ignore_permissions=True)
		frappe.db.commit()
		
		return True, emp_checkin.name
		
	except Exception as e:
		return False, str(e)


def sync_remote(checkin, employee_id, connector):
	"""Sync to remote ERPNext via API"""
	try:
		if not connector.remote_url or not connector.api_key:
			return False, "Remote URL or API credentials not configured"
		
		# Prepare API request
		url = f"{connector.remote_url.rstrip('/')}/api/resource/Employee Checkin"
		
		headers = {
			"Authorization": f"token {connector.api_key}:{connector.get_password('api_secret')}",
			"Content-Type": "application/json"
		}
		
		data = {
			"employee": employee_id,
			"log_type": checkin.log_type,
			"time": checkin.log_time.strftime("%Y-%m-%d %H:%M:%S"),
			"device_id": checkin.device
		}
		
		# Check for duplicate first (GET) - FIX: Use proper params and json.dumps
		filters = [["employee", "=", employee_id], ["time", "=", data['time']]]
		fields = ["name"]
		
		params = {
			"filters": json.dumps(filters),
			"fields": json.dumps(fields)
		}
		
		check_response = requests.get(url, headers=headers, params=params, timeout=10)
		
		# Check response status before proceeding
		if check_response.status_code != 200:
			return False, f"Duplicate check failed: {check_response.status_code} - {check_response.text}"
		
		existing = check_response.json().get("data", [])
		if existing:
			return True, existing[0].get("name")
		
		# Create new record (POST)
		response = requests.post(url, headers=headers, json=data, timeout=30)
		
		if response.status_code in [200, 201]:
			result = response.json()
			return True, result.get("data", {}).get("name")
		else:
			return False, f"API Error {response.status_code}: {response.text}"
			
	except requests.exceptions.Timeout:
		return False, "Request timeout"
	except requests.exceptions.ConnectionError:
		return False, "Connection error - cannot reach remote server"
	except Exception as e:
		return False, str(e)


def get_employee_id(person):
	"""Get employee ID from ZK Person mapping"""
	# Check if employee_id field is set
	if person.employee_id:
		return person.employee_id
	
	# Legacy: check old employee field (Link)
	if hasattr(person, 'employee') and person.employee:
		# Migrate to employee_id
		person.employee_id = person.employee
		person.save(ignore_permissions=True)
		frappe.db.commit()
		return person.employee_id
	
	# Try reverse lookup by attendance_device_id (only if Employee DocType available)
	if employee_doctype_available():
		employee = frappe.db.get_value("Employee", {"attendance_device_id": person.pin}, "name")
		if employee:
			# Update mapping
			person.employee_id = employee
			person.save(ignore_permissions=True)
			frappe.db.commit()
			return employee
	
	return None


def create_sync_log(checkin, success, result):
	"""Create sync log entry"""
	try:
		log = frappe.get_doc({
			"doctype": "ZK Sync Log",
			"checkin": checkin.name,
			"person": checkin.person,
			"log_time": checkin.log_time,
			"sync_status": "Success" if success else "Failed",
			"target_doc": result if success else None,
			"error_message": None if success else result,
			"synced_at": now()
		})
		log.insert(ignore_permissions=True)
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Failed to create sync log")


def retry_failed_syncs():
	"""
	Scheduled task to retry failed syncs
	Runs hourly with exponential backoff
	"""
	connector = frappe.get_single("ZK Sync Connector")
	
	if connector.mode == "Disabled" or not connector.auto_sync:
		return
	
	# Get failed checkins with exponential backoff
	failed_checkins = frappe.get_all(
		"ZK Check-in Out",
		filters={
			"sync_status": "Failed",
			"retry_count": ["<", 5]
		},
		fields=["name", "retry_count", "modified"],
		limit=connector.batch_size or 100
	)
	
	for checkin_info in failed_checkins:
		# Exponential backoff: 1hr, 2hr, 4hr, 8hr, 16hr
		retry_delay_hours = 2 ** (checkin_info.retry_count or 0)
		next_retry = frappe.utils.add_to_date(checkin_info.modified, hours=retry_delay_hours)
		
		if get_datetime(now()) >= next_retry:
			frappe.enqueue(
				sync_checkin,
				queue='default',
				checkin_name=checkin_info.name
			)


def bulk_sync_pending():
	"""
	Manually trigger bulk sync of pending check-ins
	"""
	connector = frappe.get_single("ZK Sync Connector")
	
	if connector.mode == "Disabled":
		frappe.throw(_("Sync connector is disabled"))
	
	# Get pending checkins
	filters = {"sync_status": ["in", ["Pending", "No Mapping"]]}
	if connector.sync_from_date:
		filters["log_time"] = [">=", connector.sync_from_date]
	
	pending = frappe.get_all(
		"ZK Check-in Out",
		filters=filters,
		limit=connector.batch_size or 100
	)
	
	for checkin_info in pending:
		frappe.enqueue(
			sync_checkin,
			queue='default',
			checkin_name=checkin_info.name
		)
	
	frappe.msgprint(_("Queued {0} check-ins for sync").format(len(pending)))


@frappe.whitelist()
def retry_failed_checkin(checkin_name):
	"""
	Manually retry a single failed check-in
	
	Roles: ZK Admin, System Manager
	"""
	frappe.only_for("ZK Admin", "System Manager")
	
	# Enqueue instead of running inline
	frappe.enqueue(
		sync_checkin,
		queue='default',
		checkin_name=checkin_name
	)
	frappe.msgprint(_("Retry queued"))
