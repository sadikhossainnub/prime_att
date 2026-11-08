frappe.pages['my-attandence'].on_page_load = function(wrapper) {
	var page = frappe.ui.make_app_page({
		parent: wrapper,
		title: __('My Attendance'),
		single_column: true
	});

	frappe.my_attendance_view = new MyAttendanceView(page);
};

class MyAttendanceView {
	constructor(page) {
		this.page = page;
		this.today = frappe.datetime.get_today();
		let parts = this.today.split('-');
		this.selected_year = parseInt(parts[0]);
		this.selected_month = parseInt(parts[1]);
		this.selected_person = null;
		this.is_admin = false;

		this.load_styles();
		this.setup_page();
		this.load_data();
	}

	load_styles() {
		if ($('#my-att-styles').length === 0) {
			let css = `
				.my-attendance-wrapper { padding: 15px 0 40px 0; color: var(--text-color, #1f272e); }
				.my-att-user-bar { background: var(--card-bg, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 8px; padding: 14px 20px; margin-bottom: 20px; display: flex; justify-content: space-between; align-items: center; box-shadow: var(--card-shadow, 0 1px 3px rgba(0,0,0,0.05)); }
				.my-att-user-info { display: flex; align-items: center; gap: 14px; }
				.my-att-avatar { width: 44px; height: 44px; border-radius: 50%; background: #2490ef; color: #fff; display: flex; align-items: center; justify-content: center; font-size: 18px; font-weight: 600; }
				.my-att-user-details h4 { margin: 0; font-size: 16px; font-weight: 600; color: var(--heading-color, #111827); }
				.my-att-user-details p { margin: 2px 0 0 0; font-size: 12px; color: var(--text-muted, #64748b); }
				.my-att-section-title { font-size: 15px; font-weight: 600; margin-bottom: 12px; color: var(--heading-color, #0f172a); display: flex; align-items: center; gap: 8px; }
				.today-summary-card { background: var(--card-bg, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 10px; padding: 20px; margin-bottom: 25px; box-shadow: var(--card-shadow, 0 1px 4px rgba(0,0,0,0.06)); }
				.today-stats-grid { display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 16px; margin-bottom: 16px; }
				.today-stat-box { background: var(--subtle-fg, #f8fafc); border: 1px solid var(--border-color, #f1f5f9); border-radius: 8px; padding: 12px 16px; }
				.today-stat-box .stat-label { font-size: 12px; color: var(--text-muted, #64748b); text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 4px; }
				.today-stat-box .stat-value { font-size: 20px; font-weight: 700; color: var(--heading-color, #1e293b); }
				.today-stat-box.highlight { background: #f0fdf4; border-color: #bbf7d0; }
				.today-stat-box.highlight .stat-value { color: #166534; }
				.today-punches-container { border-top: 1px dashed var(--border-color, #e2e8f0); padding-top: 14px; margin-top: 10px; }
				.today-punches-container .punches-header { font-size: 13px; font-weight: 600; margin-bottom: 8px; color: var(--text-muted, #475569); }
				.punches-chips-list { display: flex; flex-wrap: wrap; gap: 10px; }
				.punch-chip { display: inline-flex; align-items: center; gap: 6px; padding: 6px 12px; border-radius: 20px; font-size: 12px; font-weight: 500; border: 1px solid transparent; }
				.punch-chip.in { background: #ecfdf5; color: #065f46; border-color: #a7f3d0; }
				.punch-chip.out { background: #eff6ff; color: #1e40af; border-color: #bfdbfe; }
				.punch-chip.other { background: #f1f5f9; color: #334155; border-color: #cbd5e1; }
				.punch-chip .punch-badge { font-size: 10px; font-weight: 700; padding: 2px 6px; border-radius: 4px; background: rgba(0,0,0,0.08); }
				.month-filter-bar { background: var(--card-bg, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 8px; padding: 12px 18px; margin-bottom: 20px; display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; gap: 12px; }
				.month-summary-badges { display: flex; flex-wrap: wrap; gap: 12px; }
				.metric-pill { display: inline-flex; align-items: center; gap: 6px; padding: 4px 10px; background: var(--subtle-fg, #f8fafc); border: 1px solid var(--border-color, #e2e8f0); border-radius: 6px; font-size: 12px; }
				.metric-pill .metric-num { font-weight: 700; color: var(--heading-color, #0f172a); }
				.my-att-table-container { background: var(--card-bg, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 8px; overflow: hidden; box-shadow: var(--card-shadow, 0 1px 3px rgba(0,0,0,0.05)); }
				.my-att-table { width: 100%; border-collapse: collapse; font-size: 13px; text-align: left; }
				.my-att-table thead th { background: var(--subtle-fg, #f8fafc); color: var(--text-muted, #475569); font-weight: 600; padding: 12px 16px; border-bottom: 1px solid var(--border-color, #e2e8f0); text-transform: uppercase; font-size: 11px; letter-spacing: 0.5px; }
				.my-att-table tbody tr { border-bottom: 1px solid var(--border-color, #f1f5f9); transition: background-color 0.15s ease; }
				.my-att-table tbody tr:hover { background-color: var(--hover-bg, #f8fafc); }
				.my-att-table tbody tr.is-today { background-color: #fefce8 !important; font-weight: 600; }
				.my-att-table tbody tr.is-weekend { background-color: #fafafa; opacity: 0.85; }
				.my-att-table td { padding: 12px 16px; vertical-align: middle; }
				.att-badge { display: inline-block; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: 600; text-align: center; white-space: nowrap; }
				.att-badge.present { background: #dcfce7; color: #15803d; }
				.att-badge.absent { background: #fee2e2; color: #b91c1c; }
				.att-badge.half-day { background: #fef3c7; color: #b45309; }
				.att-badge.weekend { background: #f1f5f9; color: #64748b; }
				.att-badge.upcoming { background: #f8fafc; color: #94a3b8; border: 1px dashed #cbd5e1; }
				.att-badge.on-leave { background: #e0e7ff; color: #4338ca; }
				.my-att-empty-card { background: var(--card-bg, #ffffff); border: 1px solid var(--border-color, #e2e8f0); border-radius: 12px; padding: 44px 24px; text-align: center; max-width: 620px; margin: 30px auto; box-shadow: 0 4px 12px rgba(0, 0, 0, 0.05); }
				.empty-icon-wrapper { width: 68px; height: 68px; background: #eff6ff; border-radius: 50%; display: inline-flex; align-items: center; justify-content: center; margin-bottom: 18px; }
				.empty-card-title { font-size: 18px; font-weight: 700; color: var(--heading-color, #0f172a); margin-bottom: 10px; }
				.empty-card-desc { font-size: 13.5px; line-height: 1.6; color: var(--text-muted, #475569); margin: 0 auto 16px auto; max-width: 520px; }
				.empty-card-hint { display: inline-flex; align-items: center; gap: 8px; background: #f8fafc; border: 1px solid #e2e8f0; border-radius: 6px; padding: 8px 14px; font-size: 12px; color: #64748b; margin-top: 6px; }
				.hint-tag { background: #e2e8f0; color: #334155; font-weight: 600; font-size: 10px; padding: 2px 6px; border-radius: 4px; text-transform: uppercase; }
			`;
			$('<style id="my-att-styles">').text(css).appendTo('head');
		}
	}

	setup_page() {
		let me = this;

		// Add Refresh Button
		this.page.set_primary_action(__('Refresh'), function() {
			me.load_data();
		}, 'refresh');

		// Month Field
		let month_options = [
			{ value: 1, label: __('January') },
			{ value: 2, label: __('February') },
			{ value: 3, label: __('March') },
			{ value: 4, label: __('April') },
			{ value: 5, label: __('May') },
			{ value: 6, label: __('June') },
			{ value: 7, label: __('July') },
			{ value: 8, label: __('August') },
			{ value: 9, label: __('September') },
			{ value: 10, label: __('October') },
			{ value: 11, label: __('November') },
			{ value: 12, label: __('December') }
		];

		this.month_field = this.page.add_field({
			fieldname: 'month',
			label: __('Month'),
			fieldtype: 'Select',
			options: month_options,
			default: this.selected_month,
			change: function() {
				me.selected_month = parseInt(this.get_value());
				me.load_data();
			}
		});

		// Year Field
		let year_options = [];
		let current_yr = new Date().getFullYear();
		for (let y = current_yr - 3; y <= current_yr + 1; y++) {
			year_options.push({ value: y, label: y.toString() });
		}

		this.year_field = this.page.add_field({
			fieldname: 'year',
			label: __('Year'),
			fieldtype: 'Select',
			options: year_options,
			default: this.selected_year,
			change: function() {
				me.selected_year = parseInt(this.get_value());
				me.load_data();
			}
		});

		// Base HTML Container
		this.page.main.html(`
			<div class="my-attendance-wrapper">
				<div id="my-att-banner"></div>
				<div id="my-att-today-section"></div>
				<div id="my-att-month-section"></div>
			</div>
		`);
	}

	setup_admin_employee_selector(data) {
		let me = this;
		if (data.is_admin && !this.admin_field_added) {
			this.admin_field_added = true;
			this.is_admin = true;

			// Add employee selector only for admin/system manager
			frappe.call({
				method: 'prime_att.prime_attendance_system.page.my_attandence.my_attandence.get_employees_for_admin',
				callback: function(r) {
					if (r.message && r.message.length > 0) {
						let options = [{ value: '', label: __('Current User (Self)') }];
						r.message.forEach(function(emp) {
							options.push({
								value: emp.name,
								label: `${emp.full_name || 'User'} (${emp.pin})`
							});
						});

						me.admin_emp_field = me.page.add_field({
							fieldname: 'admin_employee_override',
							label: __('View As (Admin Only)'),
							fieldtype: 'Select',
							options: options,
							default: '',
							change: function() {
								me.selected_person = this.get_value() || null;
								me.load_data();
							}
						});
					}
				}
			});
		}
	}

	load_data() {
		let me = this;
		frappe.dom.freeze(__('Loading Attendance...'));

		frappe.call({
			method: 'prime_att.prime_attendance_system.page.my_attandence.my_attandence.get_my_attendance_dashboard',
			args: {
				year: me.selected_year,
				month: me.selected_month,
				person_override: me.selected_person
			},
			callback: function(r) {
				frappe.dom.unfreeze();
				if (r.message) {
					if (r.message.is_admin) {
						me.setup_admin_employee_selector(r.message);
					}
					if (!r.message.success) {
						me.render_empty(r.message);
					} else {
						me.render_dashboard(r.message);
					}
				}
			},
			error: function() {
				frappe.dom.unfreeze();
			}
		});
	}

	render_empty(res) {
		$('#my-att-banner').html('');
		$('#my-att-today-section').html('');

		let title = (res && res.title) ? res.title : __('Employee Profile Not Linked');
		let message = (res && res.message) ? res.message : (typeof res === 'string' ? res : __('No employee profile is connected to this account.'));
		let is_admin = (res && res.is_admin) || this.is_admin;

		let admin_actions = '';
		if (is_admin) {
			admin_actions = `
				<div class="empty-state-actions" style="margin-top: 18px; display: flex; justify-content: center; gap: 10px;">
					<button class="btn btn-primary btn-sm" onclick="frappe.set_route('List', 'Employee')">
						${__('Go to Employee List')}
					</button>
					<button class="btn btn-default btn-sm" onclick="frappe.set_route('List', 'ZK Person')">
						${__('ZK Person')}
					</button>
				</div>
			`;
		}

		let html = `
			<div class="my-att-empty-card">
				<div class="empty-icon-wrapper">
					<svg width="36" height="36" viewBox="0 0 24 24" fill="none" stroke="#2563eb" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
						<path d="M20 21v-2a4 4 0 0 0-4-4H8a4 4 0 0 0-4 4v2"></path>
						<circle cx="12" cy="7" r="4"></circle>
						<line x1="18" y1="8" x2="23" y2="8"></line>
						<line x1="20.5" y1="5.5" x2="20.5" y2="10.5"></line>
					</svg>
				</div>
				<h3 class="empty-card-title">${title}</h3>
				<p class="empty-card-desc">${message}</p>
				${(res && res.action_hint) ? `<div class="empty-card-hint"><span class="hint-tag">${__('Tip')}</span> ${res.action_hint}</div>` : ''}
				${admin_actions}
			</div>
		`;
		$('#my-att-month-section').html(html);
	}

	render_dashboard(data) {
		this.render_banner(data.person);
		this.render_today(data.today);
		this.render_monthly(data.month_summary, data.attendance_list);
	}

	render_banner(person) {
		let initial = (person.full_name || 'U').charAt(0).toUpperCase();
		let html = `
			<div class="my-att-user-bar">
				<div class="my-att-user-info">
					<div class="my-att-avatar">${initial}</div>
					<div class="my-att-user-details">
						<h4>${frappe.utils.escape_html(person.full_name)}</h4>
						<p>
							<span><strong>PIN:</strong> ${frappe.utils.escape_html(person.pin)}</span>
							${person.employee_id ? ` &nbsp;|&nbsp; <span><strong>Employee ID:</strong> ${frappe.utils.escape_html(person.employee_id)}</span>` : ''}
						</p>
					</div>
				</div>
				<span class="badge badge-primary" style="font-size: 11px; padding: 5px 10px;">${__('Personal Attendance')}</span>
			</div>
		`;
		$('#my-att-banner').html(html);
	}

	render_today(today) {
		let punch_status_badge = today.status_badge === 'green' ? 'success' : (today.status_badge === 'info' ? 'info' : 'secondary');

		// Generate punch chips
		let chips_html = '';
		if (today.punches && today.punches.length > 0) {
			today.punches.forEach(function(p) {
				let chip_class = p.type === 'IN' ? 'in' : (p.type === 'OUT' ? 'out' : 'other');
				chips_html += `
					<div class="punch-chip ${chip_class}" title="Device: ${frappe.utils.escape_html(p.device || 'N/A')}">
						<span class="punch-badge">${p.type}</span>
						<span>${p.time}</span>
					</div>
				`;
			});
		} else {
			chips_html = `<span class="text-muted" style="font-size: 13px;">${__('No punches recorded yet today.')}</span>`;
		}

		let html = `
			<div class="my-att-section-title">
				<span>🕒 ${__("Today's Punch Summary")}</span>
				<span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">&nbsp;— ${today.date}</span>
			</div>
			<div class="today-summary-card">
				<div class="today-stats-grid">
					<div class="today-stat-box">
						<div class="stat-label">${__('Current Status')}</div>
						<div class="stat-value">
							<span class="badge badge-${punch_status_badge}" style="font-size: 14px; padding: 4px 10px;">
								${today.status}
							</span>
						</div>
					</div>
					<div class="today-stat-box highlight">
						<div class="stat-label">${__('First In-Time')}</div>
						<div class="stat-value">${today.in_time}</div>
					</div>
					<div class="today-stat-box highlight">
						<div class="stat-label">${__('Last Out-Time')}</div>
						<div class="stat-value">${today.out_time}</div>
					</div>
					<div class="today-stat-box">
						<div class="stat-label">${__('Total Hours Today')}</div>
						<div class="stat-value" style="color: #2563eb;">${today.working_hours}</div>
					</div>
					<div class="today-stat-box">
						<div class="stat-label">${__('Total Punches')}</div>
						<div class="stat-value">${today.count}</div>
					</div>
				</div>

				<div class="today-punches-container">
					<div class="punches-header">${__("Today's Punches (In - Out Timeline):")}</div>
					<div class="punches-chips-list">
						${chips_html}
					</div>
				</div>
			</div>
		`;
		$('#my-att-today-section').html(html);
	}

	render_monthly(summary, list) {
		let html = `
			<div class="my-att-section-title" style="margin-top: 10px;">
				<span>📅 ${__('Monthly Attendance List')}</span>
				<span style="font-size: 12px; font-weight: normal; color: var(--text-muted);">&nbsp;— ${summary.month_name} ${summary.year}</span>
			</div>

			<div class="month-filter-bar">
				<div class="month-summary-badges">
					<div class="metric-pill">
						<span>${__('Total Days')}:</span>
						<span class="metric-num">${summary.total_days}</span>
					</div>
					<div class="metric-pill" style="border-left: 3px solid #16a34a;">
						<span>${__('Present')}:</span>
						<span class="metric-num" style="color: #16a34a;">${summary.present_days}</span>
					</div>
					<div class="metric-pill" style="border-left: 3px solid #dc2626;">
						<span>${__('Absent')}:</span>
						<span class="metric-num" style="color: #dc2626;">${summary.absent_days}</span>
					</div>
					<div class="metric-pill" style="border-left: 3px solid #d97706;">
						<span>${__('Half Day')}:</span>
						<span class="metric-num" style="color: #d97706;">${summary.half_days}</span>
					</div>
					<div class="metric-pill" style="border-left: 3px solid #64748b;">
						<span>${__('Weekend')}:</span>
						<span class="metric-num">${summary.weekend_days}</span>
					</div>
					<div class="metric-pill" style="border-left: 3px solid #2563eb;">
						<span>${__('Total Worked')}:</span>
						<span class="metric-num" style="color: #2563eb;">${summary.total_working_hours}</span>
					</div>
				</div>
			</div>

			<div class="my-att-table-container">
				<table class="my-att-table">
					<thead>
						<tr>
							<th style="width: 22%;">${__('Date')}</th>
							<th style="width: 18%;">${__('Attendance Status')}</th>
							<th style="width: 20%;">${__('In - Time')}</th>
							<th style="width: 20%;">${__('Out - Time')}</th>
							<th style="width: 20%;">${__('Total Working Hour')}</th>
						</tr>
					</thead>
					<tbody>
		`;

		if (!list || list.length === 0) {
			html += `
				<tr>
					<td colspan="5" class="text-center text-muted" style="padding: 30px;">
						${__('No attendance records found for this period.')}
					</td>
				</tr>
			`;
		} else {
			list.forEach(function(row) {
				let row_class = '';
				if (row.is_today) row_class = 'is-today';
				else if (row.is_weekend) row_class = 'is-weekend';

				let status_class = 'present';
				if (row.attendance_status === 'Absent') status_class = 'absent';
				else if (row.attendance_status === 'Half Day') status_class = 'half-day';
				else if (row.attendance_status === 'Weekend') status_class = 'weekend';
				else if (row.attendance_status === 'Upcoming') status_class = 'upcoming';
				else if (row.attendance_status === 'On Leave') status_class = 'on-leave';

				// Details popup if punches exist
				let punches_info = '';
				if (row.punches && row.punches.length > 0) {
					let punch_strs = row.punches.map(p => `${p.time} (${p.type})`).join(', ');
					punches_info = ` title="Punches: ${frappe.utils.escape_html(punch_strs)}"`;
				}

				html += `
					<tr class="${row_class}"${punches_info}>
						<td>
							<strong>${frappe.utils.escape_html(row.date)}</strong>
							${row.is_today ? ` <span class="badge badge-warning" style="font-size: 10px; margin-left: 4px;">${__('Today')}</span>` : ''}
						</td>
						<td>
							<span class="att-badge ${status_class}">
								${frappe.utils.escape_html(row.attendance_status)}
							</span>
						</td>
						<td>
							${row.in_time !== '-' ? `<span style="font-weight: 500; color: #166534;">🟢 ${row.in_time}</span>` : '<span class="text-muted">-</span>'}
						</td>
						<td>
							${row.out_time !== '-' ? `<span style="font-weight: 500; color: #1e40af;">🔴 ${row.out_time}</span>` : '<span class="text-muted">-</span>'}
						</td>
						<td>
							${row.total_working_hour !== '-' ? `<strong style="color: #0f172a;">⏱️ ${row.total_working_hour}</strong>` : '<span class="text-muted">-</span>'}
						</td>
					</tr>
				`;
			});
		}

		html += `
					</tbody>
				</table>
			</div>
		`;

		$('#my-att-month-section').html(html);
	}
}
