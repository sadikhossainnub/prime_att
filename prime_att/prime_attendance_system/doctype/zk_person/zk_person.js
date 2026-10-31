// ZK Person form customization

frappe.ui.form.on('ZK Person', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			// Push to Devices button
			frm.add_custom_button(__('Push to Device(s)'), function() {
				// Get list of devices from child table
				let device_list = frm.doc.devices.map(d => d.device);
				
				if (device_list.length === 0) {
					frappe.msgprint(__('No devices configured. Please add devices in the Devices table.'));
					return;
				}
				
				frappe.call({
					method: 'prime_att.zkteco.enrollment_manager.push_to_devices',
					args: {
						person_name: frm.doc.name,
						device_list: device_list
					},
					callback: function(r) {
						if (r.message) {
							let html = '<table class="table table-bordered"><tr><th>Device</th><th>Status</th><th>Error</th></tr>';
							r.message.forEach(function(result) {
								html += `<tr><td>${result.device}</td><td>${result.status}</td><td>${result.error || '-'}</td></tr>`;
							});
							html += '</table>';
							
							frappe.msgprint({
								title: __('Push Results'),
								message: html,
								indicator: 'green'
							});
							frm.reload_doc();
						}
					}
				});
			}, __('Actions'));
			
			// Enroll Fingerprint button
			frm.add_custom_button(__('Enroll Fingerprint'), function() {
				enroll_fingerprint_dialog(frm);
			}, __('Actions'));
			
			// Delete from Device button
			frm.add_custom_button(__('Delete from Device'), function() {
				delete_from_device_dialog(frm);
			}, __('Actions'));
		}
	}
});

function enroll_fingerprint_dialog(frm) {
	// Get list of devices
	let device_list = frm.doc.devices.map(d => d.device);
	
	if (device_list.length === 0) {
		frappe.msgprint(__('No devices configured. Please push user to devices first.'));
		return;
	}
	
	let d = new frappe.ui.Dialog({
		title: __('Enroll Fingerprint'),
		fields: [
			{
				fieldname: 'device',
				label: __('Device'),
				fieldtype: 'Link',
				options: 'ZK Device',
				reqd: 1
			},
			{
				fieldname: 'finger_index',
				label: __('Finger Index'),
				fieldtype: 'Select',
				options: '0\n1\n2\n3\n4\n5\n6\n7\n8\n9',
				default: '0',
				reqd: 1,
				description: __('0-9: Left/Right thumb, index, middle, ring, pinky')
			},
			{
				fieldname: 'overwrite',
				label: __('Overwrite Existing'),
				fieldtype: 'Check',
				default: 1
			}
		],
		primary_action_label: __('Start Enrollment'),
		primary_action: function(values) {
			frappe.call({
				method: 'prime_att.zkteco.enrollment_manager.enroll_fingerprint',
				args: {
					person_name: frm.doc.name,
					device_sn: values.device,
					finger_index: values.finger_index,
					overwrite: values.overwrite ? 1 : 0
				},
				callback: function(r) {
					if (r.message) {
						frappe.msgprint({
							title: __('Enrollment Started'),
							message: __('Enrollment queued. Check <a href="/app/zk-fingerprint-enrollment/{0}">Enrollment Status</a>', [r.message]),
							indicator: 'green'
						});
						d.hide();
					}
				}
			});
		}
	});
	
	d.show();
}

function delete_from_device_dialog(frm) {
	let device_list = frm.doc.devices.map(d => d.device);
	
	if (device_list.length === 0) {
		frappe.msgprint(__('No devices configured.'));
		return;
	}
	
	let d = new frappe.ui.Dialog({
		title: __('Delete from Device'),
		fields: [
			{
				fieldname: 'device',
				label: __('Device'),
				fieldtype: 'Link',
				options: 'ZK Device',
				reqd: 1
			}
		],
		primary_action_label: __('Delete'),
		primary_action: function(values) {
			frappe.confirm(
				__('Are you sure you want to delete this user from the device?'),
				function() {
					frappe.call({
						method: 'prime_att.zkteco.enrollment_manager.delete_user_from_device',
						args: {
							person_name: frm.doc.name,
							device_sn: values.device
						},
						callback: function(r) {
							frm.reload_doc();
							d.hide();
						}
					});
				}
			);
		}
	});
	
	d.show();
}
