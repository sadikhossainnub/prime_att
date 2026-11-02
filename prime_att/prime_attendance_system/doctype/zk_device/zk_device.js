// ZK Device form customization - Easy & User-Friendly Actions

frappe.ui.form.on('ZK Device', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			// 1. Quick Actions Menu
			frm.add_custom_button(__('Sync All Users to Device'), function() {
				frappe.confirm(
					__('Are you sure you want to push all active users to this device ({0})?', [frm.doc.name]),
					function() {
						frappe.call({
							method: 'prime_att.zkteco.device_manager.sync_all_users_to_device',
							args: { device_sn: frm.doc.serial_number },
							freeze: true,
							freeze_message: __('Queueing user push...')
						});
					}
				);
			}, __('Quick Actions'));

			frm.add_custom_button(__('Sync Device Time'), function() {
				frappe.call({
					method: 'prime_att.zkteco.device_manager.sync_device_time',
					args: { device_sn: frm.doc.serial_number }
				});
			}, __('Quick Actions'));

			frm.add_custom_button(__('Pull Users from Device'), function() {
				frappe.confirm(
					__('This will command the device to upload all registered users to ERP. Continue?'),
					function() {
						frappe.call({
							method: 'prime_att.zkteco.enrollment_manager.pull_users_from_device',
							args: { device_sn: frm.doc.serial_number }
						});
					}
				);
			}, __('Quick Actions'));

			frm.add_custom_button(__('Restart Device'), function() {
				frappe.confirm(
					__('Are you sure you want to restart device {0} remotely?', [frm.doc.name]),
					function() {
						frappe.call({
							method: 'prime_att.zkteco.device_manager.restart_device',
							args: { device_sn: frm.doc.serial_number }
						});
					}
				);
			}, __('Quick Actions'));

			// 2. View Punches / Attendance
			frm.add_custom_button(__('View Punches / Logs'), function() {
				frappe.set_route('List', 'ZK Punch', { device: frm.doc.name });
			});

			// 3. Online / Offline Indicator Badge
			if (frm.doc.is_online) {
				frm.dashboard.add_indicator(__('Status: Online'), 'green');
			} else {
				frm.dashboard.add_indicator(__('Status: Offline / Disconnected'), 'red');
			}

			// 4. Last seen
			if (frm.doc.last_activity) {
				let last_seen = frappe.datetime.comment_when(frm.doc.last_activity);
				frm.dashboard.add_comment(__('Last Ping: {0}', [last_seen]), 'blue', true);
			}
		}
	}
});
