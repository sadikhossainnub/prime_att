// Copyright (c) 2026, Prime Tech BD and contributors
// For license information, please see license.txt

frappe.ui.form.on('Punch Request', {
	refresh: function(frm) {
		// Set default device if only one exists
		if (frm.is_new() && !frm.doc.device) {
			frappe.call({
				method: 'frappe.client.get_list',
				args: {
					doctype: 'ZK Device',
					filters: { status: 'Active' },
					fields: ['name'],
					limit: 1
				},
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						frm.set_value('device', r.message[0].name);
					}
				}
			});
		}
		
		// Add action buttons based on status
		if (frm.doc.workflow_state === 'Draft' && !frm.is_new()) {
			frm.add_custom_button(__('Submit for Approval'), function() {
				frappe.call({
					method: 'prime_att.prime_attendance_system.doctype.punch_request.punch_request.submit_for_approval',
					args: { name: frm.doc.name },
					freeze: true,
					callback: function(r) {
						if (!r.exc) {
							frm.reload_doc();
						}
					}
				});
			}).addClass('btn-primary');
		}
		
		if (frm.doc.workflow_state === 'Pending Approval') {
			// Check if user has approval permission
			if (frappe.user.has_role(['ZK Admin', 'System Manager'])) {
				frm.add_custom_button(__('Approve'), function() {
					frappe.confirm(
						__('Are you sure you want to approve this request?'),
						function() {
							frappe.call({
								method: 'prime_att.prime_attendance_system.doctype.punch_request.punch_request.approve_request',
								args: { name: frm.doc.name },
								freeze: true,
								freeze_message: __('Creating punch record...'),
								callback: function(r) {
									if (!r.exc) {
										frm.reload_doc();
										frappe.show_alert({
											message: __('Request approved successfully'),
											indicator: 'green'
										});
									}
								}
							});
						}
					);
				}).addClass('btn-success');
				
				frm.add_custom_button(__('Reject'), function() {
					frappe.prompt([
						{
							fieldname: 'rejection_reason',
							label: __('Rejection Reason'),
							fieldtype: 'Text',
							reqd: 1
						}
					],
					function(values) {
						frappe.call({
							method: 'prime_att.prime_attendance_system.doctype.punch_request.punch_request.reject_request',
							args: {
								name: frm.doc.name,
								rejection_reason: values.rejection_reason
							},
							freeze: true,
							callback: function(r) {
								if (!r.exc) {
									frm.reload_doc();
									frappe.show_alert({
										message: __('Request rejected'),
										indicator: 'red'
									});
								}
							}
						});
					},
					__('Reject Request'),
					__('Reject')
					);
				}).addClass('btn-danger');
			}
		}
		
		// View created punch button
		if (frm.doc.workflow_state === 'Approved' && frm.doc.created_punch) {
			frm.add_custom_button(__('View Punch Record'), function() {
				frappe.set_route('Form', 'ZK Punch', frm.doc.created_punch);
			});
		}
		
		// Set indicator colors
		frm.page.set_indicator();
	},
	
	employee: function(frm) {
		// Fetch employee details
		if (frm.doc.employee) {
			frappe.call({
				method: 'frappe.client.get',
				args: {
					doctype: 'ZK Person',
					name: frm.doc.employee
				},
				callback: function(r) {
					if (r.message) {
						frm.set_value('employee_name', r.message.full_name);
						if (r.message.department) {
							frm.set_value('department', r.message.department);
						}
						if (r.message.designation) {
							frm.set_value('designation', r.message.designation);
						}
					}
				}
			});
		}
	},
	
	punch_date: function(frm) {
		// Validate future date
		if (frm.doc.punch_date) {
			let today = frappe.datetime.get_today();
			if (frm.doc.punch_date > today) {
				frappe.msgprint(__('Punch date cannot be in the future'));
				frm.set_value('punch_date', today);
			}
		}
	}
});

// Set indicator based on workflow state
frappe.ui.form.on('Punch Request', {
	refresh: function(frm) {
		if (frm.doc.workflow_state === 'Draft') {
			frm.page.set_indicator(__('Draft'), 'gray');
		} else if (frm.doc.workflow_state === 'Pending Approval') {
			frm.page.set_indicator(__('Pending Approval'), 'orange');
		} else if (frm.doc.workflow_state === 'Approved') {
			frm.page.set_indicator(__('Approved'), 'green');
		} else if (frm.doc.workflow_state === 'Rejected') {
			frm.page.set_indicator(__('Rejected'), 'red');
		}
	}
});
