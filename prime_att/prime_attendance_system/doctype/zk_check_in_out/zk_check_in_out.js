// ZK Check-in Out form customization

frappe.ui.form.on('ZK Check-in Out', {
	refresh: function(frm) {
		if (!frm.is_new()) {
			// Retry Sync button (only for failed syncs)
			if (frm.doc.sync_status === 'Failed') {
				frm.add_custom_button(__('Retry Sync'), function() {
					frappe.call({
						method: 'prime_att.zkteco.sync_manager.retry_failed_checkin',
						args: {
							checkin_name: frm.doc.name
						},
						callback: function(r) {
							frappe.msgprint(__('Sync retry queued'));
							setTimeout(function() {
								frm.reload_doc();
							}, 2000);
						}
					});
				});
			}
			
			// Show sync status indicator
			let status_color = {
				'Pending': 'orange',
				'No Mapping': 'red',
				'Synced': 'green',
				'Failed': 'red'
			};
			
			frm.dashboard.add_indicator(
				__('Sync Status: {0}', [frm.doc.sync_status]),
				status_color[frm.doc.sync_status] || 'gray'
			);
			
			// Show error if any
			if (frm.doc.sync_error) {
				frm.dashboard.add_comment(
					__('Error: {0}', [frm.doc.sync_error]),
					'red',
					true
				);
			}
		}
	}
});
