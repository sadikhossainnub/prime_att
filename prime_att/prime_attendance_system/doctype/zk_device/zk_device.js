// ZK Device form customization

frappe.ui.form.on('ZK Device', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			// Pull Users button
			frm.add_custom_button(__('Pull Users'), function() {
				frappe.confirm(
					__('This will send a command to the device to upload all user information. Continue?'),
					function() {
						frappe.call({
							method: 'prime_att.zkteco.enrollment_manager.pull_users_from_device',
							args: {
								device_sn: frm.doc.serial_number
							},
							callback: function(r) {
								frappe.msgprint({
									title: __('Command Sent'),
									message: __('Pull users command sent. Users will be created/updated when device responds.'),
									indicator: 'green'
								});
							}
						});
					}
				);
			}, __('Actions'));
			
			// View Raw Logs button
			frm.add_custom_button(__('View Raw Logs'), function() {
				frappe.set_route('List', 'ZK Raw Log', {device: frm.doc.name});
			}, __('View'));
			
			// View Punches button
			frm.add_custom_button(__('View Punches'), function() {
				frappe.set_route('List', 'ZK Punch', {device: frm.doc.name});
			}, __('View'));
			
			// View Commands button
			frm.add_custom_button(__('View Commands'), function() {
				frappe.set_route('List', 'ZK Device Command', {device: frm.doc.name});
			}, __('View'));
			
			// Show online/offline indicator
			if (frm.doc.is_online) {
				frm.dashboard.add_indicator(__('Status: Online'), 'green');
			} else {
				frm.dashboard.add_indicator(__('Status: Offline'), 'red');
			}
			
			// Show last activity
			if (frm.doc.last_activity) {
				let last_seen = frappe.datetime.comment_when(frm.doc.last_activity);
				frm.dashboard.add_comment(__('Last Activity: {0}', [last_seen]), 'blue', true);
			}
		}
	}
});
