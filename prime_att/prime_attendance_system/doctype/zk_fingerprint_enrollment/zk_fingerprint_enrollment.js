// ZK Fingerprint Enrollment form customization

frappe.ui.form.on('ZK Fingerprint Enrollment', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			// Check Status button
			frm.add_custom_button(__('Check Status'), function() {
				frappe.call({
					method: 'prime_att.zkteco.enrollment_manager.check_enrollment_status',
					args: {
						enrollment_name: frm.doc.name
					},
					callback: function(r) {
						if (r.message) {
							frappe.msgprint({
								title: __('Enrollment Status'),
								message: r.message.message,
								indicator: get_status_indicator(r.message.status)
							});
							frm.reload_doc();
						}
					}
				});
			});
			
			// Retry button (for timeout/failed)
			if (['Timeout', 'Failed'].includes(frm.doc.status)) {
				frm.add_custom_button(__('Retry'), function() {
					frappe.call({
						method: 'prime_att.zkteco.enrollment_manager.enroll_fingerprint',
						args: {
							person_name: frm.doc.person,
							device_sn: frm.doc.device,
							finger_index: frm.doc.finger_index,
							overwrite: frm.doc.overwrite
						},
						callback: function(r) {
							if (r.message) {
								frappe.msgprint(__('Enrollment restarted'));
								frappe.set_route('Form', 'ZK Fingerprint Enrollment', r.message);
							}
						}
					});
				});
			}
			
			// Status indicator
			let status_color = {
				'Queued': 'orange',
				'Sent': 'blue',
				'Waiting for User': 'yellow',
				'Enrolled': 'green',
				'Timeout': 'red',
				'Failed': 'red'
			};
			
			frm.dashboard.add_indicator(
				__('Status: {0}', [frm.doc.status]),
				status_color[frm.doc.status] || 'gray'
			);
			
			// Instruction message based on status
			if (frm.doc.status === 'Waiting for User') {
				frm.dashboard.add_comment(
					__('Please place your finger on the device scanner now.'),
					'blue',
					true
				);
			} else if (frm.doc.status === 'Enrolled') {
				frm.dashboard.add_comment(
					__('Fingerprint successfully enrolled at {0}', [frappe.datetime.str_to_user(frm.doc.enrolled_time)]),
					'green',
					true
				);
			}
		}
	}
});

function get_status_indicator(status) {
	let indicators = {
		'Queued': 'orange',
		'Sent': 'blue',
		'Waiting for User': 'yellow',
		'Enrolled': 'green',
		'Timeout': 'red',
		'Failed': 'red'
	};
	return indicators[status] || 'gray';
}
