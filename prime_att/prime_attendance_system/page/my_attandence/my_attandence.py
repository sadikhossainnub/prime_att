# Copyright (c) 2026, Prime Tech BD and contributors
# For license information, please see license.txt

import calendar
import datetime
import frappe
from frappe import _
from frappe.utils import (
	getdate,
	now_datetime,
	format_time,
	format_datetime,
	get_datetime,
	time_diff_in_seconds,
)


@frappe.whitelist()
def get_my_attendance_dashboard(year=None, month=None, person_override=None):
	"""
	Returns attendance and punch data strictly for the logged-in employee.
	Supports both ERPNext Employee (standard) and ZK Person (standalone).
	Condition: Employee can ONLY see their own data, not anyone else's.
	(System Manager / ZK Admin can optionally pass person_override for testing/admin purposes).
	"""
	user = frappe.session.user
	if not user or user == "Guest":
		frappe.throw(_("Please log in to view your attendance."), frappe.PermissionError)

	# Security check: Only System Manager or ZK Admin can override person
	roles = frappe.get_roles(user)
	is_admin = bool(set(roles).intersection({"System Manager", "Administrator", "ZK Admin"}))
	if not is_admin:
		person_override = None

	profile = get_user_employee_profile(user, person_override)
	if not profile:
		if is_admin:
			msg = _(
				"Your user account ({0}) is not linked to an Employee profile yet. "
				"As an Administrator, you can link your User ID in the Employee / ZK Person form, "
				"or select an employee from the dropdown above to view their attendance."
			).format(f"<b>{user}</b>")
			action_hint = _("Tip: In Employee Master, set 'User ID' to your user account, or select an employee above.")
		else:
			msg = _(
				"We couldn't find an employee profile linked to your user account ({0}). "
				"To view your daily punches and attendance summary, your account needs to be connected to your employee profile. "
				"Please contact your HR department or System Administrator."
			).format(f"<b>{user}</b>")
			action_hint = _("Please reach out to your HR department to map your User ID to your Employee record.")

		return {
			"success": False,
			"has_person": False,
			"is_admin": is_admin,
			"user": user,
			"title": _("Employee Profile Not Linked"),
			"message": msg,
			"action_hint": action_hint,
		}

	# Parse year & month
	today = getdate()
	try:
		year = int(year) if year else today.year
		month = int(month) if month else today.month
	except (ValueError, TypeError):
		year = today.year
		month = today.month

	# 1. Today's punches
	today_data = get_today_punches(profile, today)

	# 2. Monthly attendance list
	monthly_data = get_monthly_attendance(profile, year, month, today)

	return {
		"success": True,
		"has_person": True,
		"is_admin": is_admin,
		"person": {
			"name": profile.get("name"),
			"pin": profile.get("pin"),
			"full_name": profile.get("full_name") or f"Employee: {profile.get('name')}",
			"employee_id": profile.get("employee_id") or profile.get("name") or "",
		},
		"today": today_data,
		"month_summary": monthly_data["summary"],
		"attendance_list": monthly_data["attendance_list"],
	}


def get_user_employee_profile(user, person_override=None):
	"""
	Resolves Employee / ZK Person profile for the given user.
	Prioritizes ERPNext Employee if installed, then ZK Person.
	"""
	# If admin specified an override
	if person_override:
		# Check Employee DocType first if available
		if frappe.db.table_exists("tabEmployee"):
			emp = frappe.db.get_value(
				"Employee",
				{"name": person_override},
				["name", "attendance_device_id", "employee_name", "user_id"],
				as_dict=True,
			)
			if emp:
				zk_person = frappe.db.get_value(
					"ZK Person", {"employee_id": emp.name}, ["name", "pin", "full_name"], as_dict=True
				) if frappe.db.table_exists("tabZK Person") else None
				return {
					"name": zk_person.name if zk_person else emp.name,
					"employee_id": emp.name,
					"pin": emp.attendance_device_id or (zk_person.pin if zk_person else emp.name),
					"full_name": emp.employee_name or (zk_person.full_name if zk_person else emp.name),
					"zk_person": zk_person.name if zk_person else None,
				}

		# Check ZK Person
		if frappe.db.table_exists("tabZK Person"):
			zk = frappe.db.get_value(
				"ZK Person", {"name": person_override}, ["name", "pin", "full_name", "employee_id"], as_dict=True
			) or frappe.db.get_value(
				"ZK Person", {"pin": person_override}, ["name", "pin", "full_name", "employee_id"], as_dict=True
			)
			if zk:
				return {
					"name": zk.name,
					"employee_id": zk.employee_id or zk.name,
					"pin": zk.pin,
					"full_name": zk.full_name,
					"zk_person": zk.name,
				}

	# 1. Primary: Match via ERPNext Employee DocType (user_id)
	if frappe.db.table_exists("tabEmployee"):
		emp = frappe.db.get_value(
			"Employee",
			{"user_id": user},
			["name", "attendance_device_id", "employee_name", "user_id"],
			as_dict=True,
		)
		if emp:
			zk_person = None
			if frappe.db.table_exists("tabZK Person"):
				zk_person = frappe.db.get_value(
					"ZK Person", {"employee_id": emp.name}, ["name", "pin", "full_name"], as_dict=True
				)
				if not zk_person and emp.attendance_device_id:
					zk_person = frappe.db.get_value(
						"ZK Person", {"pin": emp.attendance_device_id}, ["name", "pin", "full_name"], as_dict=True
					)
			return {
				"name": zk_person.name if zk_person else emp.name,
				"employee_id": emp.name,
				"pin": emp.attendance_device_id or (zk_person.pin if zk_person else emp.name),
				"full_name": emp.employee_name or (zk_person.full_name if zk_person else emp.name),
				"zk_person": zk_person.name if zk_person else None,
			}

	# 2. Match ZK Person directly (if user_id field exists)
	if frappe.db.table_exists("tabZK Person"):
		fields = ["name", "pin", "full_name", "employee_id"]
		if frappe.db.has_column("ZK Person", "user_id"):
			fields.append("user_id")
			zk = frappe.db.get_value("ZK Person", {"user_id": user}, fields, as_dict=True)
			if zk:
				return {
					"name": zk.name,
					"employee_id": zk.employee_id or zk.name,
					"pin": zk.pin,
					"full_name": zk.full_name,
					"zk_person": zk.name,
				}

		# Match by employee_id == user or pin == user
		zk = frappe.db.get_value("ZK Person", {"employee_id": user}, fields, as_dict=True) or \
			frappe.db.get_value("ZK Person", {"pin": user}, fields, as_dict=True)
		if zk:
			return {
				"name": zk.name,
				"employee_id": zk.employee_id or zk.name,
				"pin": zk.pin,
				"full_name": zk.full_name,
				"zk_person": zk.name,
			}

	# 3. Fallback for Administrator preview
	if user == "Administrator":
		if frappe.db.table_exists("tabEmployee"):
			emp = frappe.db.get_value(
				"Employee",
				{"status": ["!=", "Left"]},
				["name", "attendance_device_id", "employee_name"],
				as_dict=True,
			)
			if emp:
				return {
					"name": emp.name,
					"employee_id": emp.name,
					"pin": emp.attendance_device_id or emp.name,
					"full_name": emp.employee_name or emp.name,
					"zk_person": None,
				}
		if frappe.db.table_exists("tabZK Person"):
			zk = frappe.db.get_value("ZK Person", {"is_active": 1}, ["name", "pin", "full_name", "employee_id"], as_dict=True)
			if zk:
				return {
					"name": zk.name,
					"employee_id": zk.employee_id or zk.name,
					"pin": zk.pin,
					"full_name": zk.full_name,
					"zk_person": zk.name,
				}

	return None


def get_today_punches(person, today_date):
	"""
	Fetch all punches for today and compute today's in/out/hours status.
	Supports Employee Checkin (ERPNext), ZK Check-in Out, and ZK Punch.
	"""
	start_str = f"{today_date} 00:00:00"
	end_str = f"{today_date} 23:59:59"

	raw_punches = []
	emp_id = person.get("employee_id") or person.get("name")
	zk_person_name = person.get("zk_person") or person.get("name")
	pin = person.get("pin")

	# 1. Check ERPNext Employee Checkin
	if frappe.db.table_exists("tabEmployee Checkin") and emp_id:
		emp_checkins = frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": emp_id,
				"time": ["between", [start_str, end_str]],
			},
			fields=["name", "time", "log_type", "device_id"],
			order_by="time asc",
		)
		for ec in emp_checkins:
			raw_punches.append({
				"dt": ec.time,
				"log_type": ec.log_type or "IN",
				"device": ec.device_id or "",
				"source": "Employee Checkin",
			})

	# 2. Check ZK Check-in Out
	if frappe.db.table_exists("tabZK Check-in Out") and zk_person_name:
		checkins = frappe.get_all(
			"ZK Check-in Out",
			filters={
				"person": zk_person_name,
				"log_time": ["between", [start_str, end_str]],
			},
			fields=["name", "log_time", "log_type", "device"],
			order_by="log_time asc",
		)
		for c in checkins:
			already_included = any(
				abs((rp["dt"] - c.log_time).total_seconds()) < 5 for rp in raw_punches
			)
			if not already_included:
				raw_punches.append({
					"dt": c.log_time,
					"log_type": c.log_type or "PUNCH",
					"device": c.device or "",
					"source": "ZK Check-in Out",
				})

	# 3. Check ZK Punch
	if frappe.db.table_exists("tabZK Punch") and pin:
		punches = frappe.get_all(
			"ZK Punch",
			filters={
				"pin": pin,
				"punch_time": ["between", [start_str, end_str]],
			},
			fields=["name", "punch_time", "status_code", "device"],
			order_by="punch_time asc",
		)
		for p in punches:
			already_included = any(
				abs((rp["dt"] - p.punch_time).total_seconds()) < 5 for rp in raw_punches
			)
			if not already_included:
				log_type = "OUT" if str(p.status_code) in ["1", "2", "4"] else "IN"
				raw_punches.append({
					"dt": p.punch_time,
					"log_type": log_type,
					"device": p.device or "",
					"source": "ZK Punch",
				})

	# Sort chronologically
	raw_punches.sort(key=lambda x: x["dt"])

	punch_list = []
	for p in raw_punches:
		punch_list.append({
			"raw_datetime": str(p["dt"]),
			"time": p["dt"].strftime("%I:%M:%S %p"),
			"time_short": p["dt"].strftime("%I:%M %p"),
			"type": p["log_type"],
			"device": p["device"],
		})

	# Compute first in and last out
	in_time_str = "-"
	out_time_str = "-"
	total_working_hours = "-"
	status_text = "Not Punched Today"
	status_badge = "gray"

	if punch_list:
		first_punch = raw_punches[0]
		last_punch = raw_punches[-1]

		in_time_str = first_punch["dt"].strftime("%I:%M %p")

		if len(raw_punches) > 1:
			out_time_str = last_punch["dt"].strftime("%I:%M %p")
			diff_sec = (last_punch["dt"] - first_punch["dt"]).total_seconds()
			hours = int(diff_sec // 3600)
			mins = int((diff_sec % 3600) // 60)
			total_working_hours = f"{hours}h {mins}m"
			
			if last_punch["log_type"] == "OUT":
				status_text = "Punched Out"
				status_badge = "info"
			else:
				status_text = "Punched In"
				status_badge = "green"
		else:
			status_text = "Punched In"
			status_badge = "green"
			# Currently in progress
			diff_sec = (now_datetime() - first_punch["dt"]).total_seconds()
			if diff_sec > 0:
				hours = int(diff_sec // 3600)
				mins = int((diff_sec % 3600) // 60)
				total_working_hours = f"{hours}h {mins}m (Active)"

	return {
		"date": today_date.strftime("%d %b %Y (%A)"),
		"today_date": str(today_date),
		"punches": punch_list,
		"count": len(punch_list),
		"in_time": in_time_str,
		"out_time": out_time_str,
		"working_hours": total_working_hours,
		"status": status_text,
		"status_badge": status_badge,
	}


def get_monthly_attendance(person, year, month, today_date):
	"""
	Generate monthly attendance report with columns:
	Date, Attendance Status, In-Time, Out-Time, Total Working Hour
	"""
	num_days = calendar.monthrange(year, month)[1]
	start_month_str = f"{year}-{month:02d}-01 00:00:00"
	end_month_str = f"{year}-{month:02d}-{num_days:02d} 23:59:59"

	# 1. Fetch ERPNext Attendance records for the month if available
	erp_attendance_map = {}
	emp_id = person.get("employee_id") or person.get("name")
	zk_person_name = person.get("zk_person") or person.get("name")
	pin = person.get("pin")

	if frappe.db.table_exists("tabAttendance"):
		att_records = frappe.get_all(
			"Attendance",
			filters={
				"employee": ["in", [emp_id, person.get("name")]],
				"attendance_date": ["between", [f"{year}-{month:02d}-01", f"{year}-{month:02d}-{num_days:02d}"]],
				"docstatus": 1,
			},
			fields=["attendance_date", "status", "in_time", "out_time", "working_hours"],
		)
		for att in att_records:
			erp_attendance_map[str(att.attendance_date)] = att

	# 2. Fetch Employee Checkin records for the month (ERPNext)
	checkin_map = {}
	if frappe.db.table_exists("tabEmployee Checkin") and emp_id:
		ec_records = frappe.get_all(
			"Employee Checkin",
			filters={
				"employee": emp_id,
				"time": ["between", [start_month_str, end_month_str]],
			},
			fields=["name", "time", "log_type", "device_id"],
			order_by="time asc",
		)
		for ec in ec_records:
			d_str = ec.time.strftime("%Y-%m-%d")
			if d_str not in checkin_map:
				checkin_map[d_str] = []
			checkin_map[d_str].append({
				"log_time": ec.time,
				"log_type": ec.log_type or "IN",
				"device": ec.device_id or "",
			})

	# 3. Fetch ZK Check-in Out records for the entire month
	if frappe.db.table_exists("tabZK Check-in Out") and zk_person_name:
		records = frappe.get_all(
			"ZK Check-in Out",
			filters={
				"person": zk_person_name,
				"log_time": ["between", [start_month_str, end_month_str]],
			},
			fields=["name", "log_time", "log_type", "device"],
			order_by="log_time asc",
		)
		for r in records:
			d_str = r.log_time.strftime("%Y-%m-%d")
			if d_str not in checkin_map:
				checkin_map[d_str] = []
			already_has = any(
				abs((x.get("log_time", x.get("punch_time")) - r.log_time).total_seconds()) < 5
				for x in checkin_map[d_str]
			)
			if not already_has:
				checkin_map[d_str].append(r)

	# 4. Fetch ZK Punch records for the entire month as fallback
	if frappe.db.table_exists("tabZK Punch") and pin:
		punch_records = frappe.get_all(
			"ZK Punch",
			filters={
				"pin": pin,
				"punch_time": ["between", [start_month_str, end_month_str]],
			},
			fields=["name", "punch_time", "status_code", "device"],
			order_by="punch_time asc",
		)
		for pr in punch_records:
			d_str = pr.punch_time.strftime("%Y-%m-%d")
			if d_str not in checkin_map:
				checkin_map[d_str] = []
			# Check duplicate
			already_has = any(
				abs((x.get("log_time", x.get("punch_time")) - pr.punch_time).total_seconds()) < 5
				for x in checkin_map[d_str]
			)
			if not already_has:
				checkin_map[d_str].append({
					"log_time": pr.punch_time,
					"log_type": "OUT" if str(pr.status_code) in ["1", "2", "4"] else "IN",
					"device": pr.device,
				})

	# 5. Generate daily list
	attendance_list = []
	present_count = 0
	absent_count = 0
	half_day_count = 0
	weekend_count = 0
	total_worked_seconds = 0

	for day in range(1, num_days + 1):
		cur_date = datetime.date(year, month, day)
		cur_date_str = cur_date.strftime("%Y-%m-%d")
		day_name = cur_date.strftime("%a")
		weekday = cur_date.weekday()  # 4 = Friday, 5 = Saturday, 6 = Sunday
		is_weekend = weekday in [4, 5]  # Fri & Sat weekend (standard in Bangladesh)
		is_future = cur_date > today_date

		# Check punches for this day
		day_punches = checkin_map.get(cur_date_str, [])
		day_punches.sort(key=lambda x: x.get("log_time", x.get("punch_time")))

		in_time_val = None
		out_time_val = None
		working_hours_str = "-"
		working_hours_num = 0.0

		if day_punches:
			first_p = day_punches[0].get("log_time", day_punches[0].get("punch_time"))
			last_p = day_punches[-1].get("log_time", day_punches[-1].get("punch_time"))

			in_time_val = first_p.strftime("%I:%M %p")

			if len(day_punches) > 1:
				out_time_val = last_p.strftime("%I:%M %p")
				diff_sec = (last_p - first_p).total_seconds()
				if diff_sec > 0:
					working_hours_num = round(diff_sec / 3600.0, 2)
					total_worked_seconds += diff_sec
					hrs = int(diff_sec // 3600)
					mins = int((diff_sec % 3600) // 60)
					working_hours_str = f"{hrs}h {mins}m"
			else:
				# Single punch (only In)
				out_time_val = "-"
				working_hours_str = "-"

		# Determine Attendance Status
		erp_att = erp_attendance_map.get(cur_date_str)
		if erp_att:
			status = erp_att.get("status") or "Present"
			if erp_att.get("in_time") and not in_time_val:
				in_time_val = get_datetime(erp_att["in_time"]).strftime("%I:%M %p")
			if erp_att.get("out_time") and not out_time_val:
				out_time_val = get_datetime(erp_att["out_time"]).strftime("%I:%M %p")
			if erp_att.get("working_hours") and working_hours_str == "-":
				working_hours_num = erp_att["working_hours"]
				hrs = int(working_hours_num)
				mins = int(round((working_hours_num - hrs) * 60))
				working_hours_str = f"{hrs}h {mins}m"
				total_worked_seconds += working_hours_num * 3600
		else:
			if day_punches:
				if working_hours_num >= 4.0:
					status = "Present"
				elif working_hours_num > 0.0:
					status = "Half Day"
				else:
					status = "Present"
			else:
				if is_future:
					status = "Upcoming"
				elif is_weekend:
					status = "Weekend"
				else:
					status = "Absent"

		# Count summaries (only for past or today)
		if not is_future:
			if status in ["Present", "Work From Home"]:
				present_count += 1
			elif status in ["Half Day"]:
				half_day_count += 1
			elif status in ["Absent"]:
				absent_count += 1
			elif status in ["Weekend"]:
				weekend_count += 1

		# Formatted punch details for popover/tooltip
		all_punches_formatted = [
			{
				"time": p.get("log_time", p.get("punch_time")).strftime("%I:%M:%S %p"),
				"type": p.get("log_type", "IN"),
				"device": p.get("device", ""),
			}
			for p in day_punches
		]

		attendance_list.append({
			"date": f"{cur_date.strftime('%d %b %Y')} ({day_name})",
			"raw_date": cur_date_str,
			"day_name": day_name,
			"is_today": cur_date == today_date,
			"is_weekend": is_weekend,
			"attendance_status": status,
			"in_time": in_time_val or "-",
			"out_time": out_time_val or "-",
			"total_working_hour": working_hours_str,
			"working_hours_num": working_hours_num,
			"punch_count": len(day_punches),
			"punches": all_punches_formatted,
		})

	# Total working hours for the month
	total_hrs = int(total_worked_seconds // 3600)
	total_mins = int((total_worked_seconds % 3600) // 60)
	total_worked_str = f"{total_hrs}h {total_mins}m"

	return {
		"summary": {
			"year": year,
			"month": month,
			"month_name": calendar.month_name[month],
			"total_days": num_days,
			"present_days": present_count,
			"absent_days": absent_count,
			"half_days": half_day_count,
			"weekend_days": weekend_count,
			"total_working_hours": total_worked_str,
		},
		"attendance_list": attendance_list,
	}


@frappe.whitelist()
def get_employees_for_admin():
	"""
	Returns list of active Employees (or ZK Persons) for System Manager / ZK Admin testing/selection.
	Regular users are forbidden from calling this.
	"""
	user = frappe.session.user
	roles = frappe.get_roles(user)
	if not bool(set(roles).intersection({"System Manager", "Administrator", "ZK Admin"})):
		frappe.throw(_("Permission denied."), frappe.PermissionError)

	if frappe.db.table_exists("tabEmployee"):
		return frappe.get_all(
			"Employee",
			filters={"status": ["!=", "Left"]},
			fields=[
				"name",
				"attendance_device_id as pin",
				"employee_name as full_name",
				"name as employee_id",
			],
			order_by="employee_name asc",
		)

	if frappe.db.table_exists("tabZK Person"):
		return frappe.get_all(
			"ZK Person",
			filters={"is_active": 1},
			fields=["name", "pin", "full_name", "employee_id"],
			order_by="full_name asc",
		)

	return []
