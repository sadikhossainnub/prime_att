// Copyright (c) 2026, Prime Tech BD and contributors

frappe.listview_settings['Punch Request'] = {
	get_indicator: function(doc) {
		if (doc.workflow_state === 'Approved') {
			return [__('Approved'), 'green', 'workflow_state,=,Approved'];
		} else if (doc.workflow_state === 'Rejected') {
			return [__('Rejected'), 'red', 'workflow_state,=,Rejected'];
		} else if (doc.workflow_state === 'Pending Approval') {
			return [__('Pending Approval'), 'orange', 'workflow_state,=,Pending Approval'];
		} else if (doc.workflow_state === 'Draft') {
			return [__('Draft'), 'gray', 'workflow_state,=,Draft'];
		}
	},
	
	onload: function(listview) {
		// Add bulk approve button for admins
		if (frappe.user.has_role(['ZK Admin', 'System Manager'])) {
			listview.page.add_action_item(__('Bulk Approve Selected'), function() {
				let selected = listview.get_checked_items();
				if (selected.length === 0) {
					frappe.msgprint(__('Please select requests to approve'));
					return;
				}
				
				frappe.confirm(
					__('Approve {0} selected requests?', [selected.length]),
					function() {
						let failed = 0;
						let success = 0;
						
						selected.forEach(function(item, index) {
							frappe.call({
								method: 'prime_att.prime_attendance_system.doctype.punch_request.punch_request.approve_request',
								args: { name: item.name },
								freeze: false,
								callback: function(r) {
									if (r.exc) {
										failed++;
									} else {
										success++;
									}
									
									// Show summary after last item
									if (index === selected.length - 1) {
										frappe.msgprint(__('Approved: {0}, Failed: {1}', [success, failed]));
										listview.refresh();
									}
								}
							});
						});
					}
				);
			});
		}
	}
};
