import frappe

def execute():
	"""Delete ZK Command Template DocType and its table"""
	if frappe.db.exists("DocType", "ZK Command Template"):
		frappe.delete_doc("DocType", "ZK Command Template", ignore_permissions=True, force=True)
		frappe.db.commit()
