// Copyright (c) 2026, Prime Tech BD and contributors
// For license information, please see license.txt

frappe.listview_settings['ZK Punch'] = {
	onload: function(listview) {
		// Add "Fetch Punches" button in list view
		listview.page.add_inner_button(__('Fetch Punches from Device'), function() {
			// Show device picker dialog
			frappe.prompt([
				{
					fieldname: 'device',
					label: __('Select Device'),
					fieldtype: 'Link',
					options: 'ZK Device',
					reqd: 1,
					get_query: function() {
						return {
							filters: {
								status: ['in', ['Active', 'Pending']]
							}
						};
					}
				}
			],
			function(values) {
				// Call fetch function
				frappe.call({
					method: 'prime_att.zkteco.device_manager.fetch_punches_from_device',
					args: {
						device_sn: values.device
					},
					freeze: true,
					freeze_message: __('Queuing fetch command...'),
					callback: function(r) {
						if (!r.exc) {
							listview.refresh();
						}
					}
				});
			},
			__('Fetch Punches'),
			__('Fetch')
			);
		});
	}
};

