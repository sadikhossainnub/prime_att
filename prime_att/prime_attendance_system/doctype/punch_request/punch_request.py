# Copyright (c) 2026, Prime Tech BD and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now, get_datetime, now_datetime


class PunchRequest(Document):
	def validate(self):
		"""Validate punch request"""
		# Validate punch date is not in future
		if get_datetime(f"{self.punch_date} {self.punch_time}") > now_datetime():
			frappe.throw("Punch date/time cannot be in the future")
		
		# Fetch employee details
		if self.employee:
			person = frappe.get_doc("ZK Person", self.employee)
			self.employee_name = person.full_name
			
			# Get department and designation if available
			if hasattr(person, 'department'):
				self.department = person.department
			if hasattr(person, 'designation'):
				self.designation = person.designation
	
	def on_submit(self):
		"""On submit, set to Pending Approval"""
		if self.workflow_state == "Draft":
			self.workflow_state = "Pending Approval"
			self.save()
	
	def before_cancel(self):
		"""Prevent cancel if approved and punch created"""
		if self.workflow_state == "Approved" and self.created_punch:
			frappe.throw("Cannot cancel approved request with created punch. Delete the punch first.")


@frappe.whitelist()
def approve_request(name):
	"""
	Approve punch request and create punch record
	
	Roles: ZK Admin, System Manager only
	"""
	frappe.only_for("ZK Admin", "System Manager")
	
	doc = frappe.get_doc("Punch Request", name)
	
	if doc.workflow_state != "Pending Approval":
		frappe.throw("Only pending requests can be approved")
	
	# Get ZK Person details
	person = frappe.get_doc("ZK Person", doc.employee)
	
	# Create ZK Punch record
	punch_datetime = f"{doc.punch_date} {doc.punch_time}"
	
	try:
		punch = frappe.get_doc({
			"doctype": "ZK Punch",
			"device": doc.device,
			"pin": person.pin,
			"punch_time": punch_datetime,
			"status_code": "0",  # Default to check-in
			"verify_type": "0",  # Manual
			"workcode": "",
		})
		punch.insert(ignore_permissions=True)
		frappe.db.commit()
		
		# Update request
		doc.workflow_state = "Approved"
		doc.approved_by = frappe.session.user
		doc.approved_on = now()
		doc.created_punch = punch.name
		doc.save(ignore_permissions=True)
		
		# Create check-in/out record
		from prime_att.zkteco.processor import create_checkin_out
		create_checkin_out(punch)
		
		frappe.msgprint(f"Request approved and punch created: {punch.name}", indicator="green")
		return punch.name
		
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Punch Request Approval Failed")
		frappe.throw(f"Failed to create punch: {str(e)}")


@frappe.whitelist()
def reject_request(name, rejection_reason=None):
	"""
	Reject punch request
	
	Roles: ZK Admin, System Manager only
	"""
	frappe.only_for("ZK Admin", "System Manager")
	
	doc = frappe.get_doc("Punch Request", name)
	
	if doc.workflow_state != "Pending Approval":
		frappe.throw("Only pending requests can be rejected")
	
	doc.workflow_state = "Rejected"
	doc.approved_by = frappe.session.user
	doc.approved_on = now()
	doc.rejection_reason = rejection_reason or "No reason provided"
	doc.save(ignore_permissions=True)
	
	frappe.msgprint("Request rejected", indicator="red")


@frappe.whitelist()
def submit_for_approval(name):
	"""
	Submit request for approval
	
	Roles: All (creator can submit own request)
	"""
	doc = frappe.get_doc("Punch Request", name)
	
	# Check if user is owner or has permission
	if doc.owner != frappe.session.user and not frappe.has_permission("Punch Request", "submit", doc):
		frappe.throw("You don't have permission to submit this request")
	
	if doc.workflow_state != "Draft":
		frappe.throw("Only draft requests can be submitted")
	
	doc.workflow_state = "Pending Approval"
	doc.save(ignore_permissions=True)
	
	frappe.msgprint("Request submitted for approval", indicator="blue")
	
	# Notify approvers (ZK Admin, System Manager)
	notify_approvers(doc)


def notify_approvers(doc):
	"""Send notification to approvers"""
	try:
		# Get users with ZK Admin or System Manager role
		approvers = frappe.get_all("Has Role", 
			filters={
				"role": ["in", ["ZK Admin", "System Manager"]],
				"parenttype": "User"
			},
			fields=["parent"],
			distinct=True
		)
		
		for approver in approvers:
			frappe.get_doc({
				"doctype": "Notification Log",
				"subject": f"Punch Request {doc.name} needs approval",
				"email_content": f"""
					<p>A new punch request needs your approval:</p>
					<ul>
						<li>Employee: {doc.employee_name}</li>
						<li>Date: {doc.punch_date}</li>
						<li>Time: {doc.punch_time}</li>
						<li>Reason: {doc.reason}</li>
					</ul>
					<p><a href="/app/punch-request/{doc.name}">View Request</a></p>
				""",
				"document_type": doc.doctype,
				"document_name": doc.name,
				"for_user": approver.parent,
				"type": "Alert"
			}).insert(ignore_permissions=True)
		
		frappe.db.commit()
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Failed to notify approvers")
