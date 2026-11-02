"""
Data parsers for ZKTeco protocol payloads
Handles tab-separated data with varying field counts across firmwares
"""

import frappe
from frappe.utils import get_datetime, now_datetime
from datetime import datetime


def parse_attlog(body):
	"""
	Parse ATTLOG (punch records)
	Format: PIN\tDateTime\tStatus\tVerify\tWorkCode\t...
	Field count varies by firmware - parse tolerantly
	"""
	records = []
	lines = body.strip().split('\n')
	
	for line in lines:
		if not line.strip():
			continue
		
		fields = line.split('\t')
		if len(fields) < 2:
			continue
		
		try:
			record = {
				'pin': fields[0].strip(),
				'timestamp': parse_device_datetime(fields[1].strip()),
				'status': fields[2].strip() if len(fields) > 2 else '0',
				'verify': fields[3].strip() if len(fields) > 3 else '0',
				'workcode': fields[4].strip() if len(fields) > 4 else '',
				'reserved1': fields[5].strip() if len(fields) > 5 else '',
				'reserved2': fields[6].strip() if len(fields) > 6 else '',
			}
			records.append(record)
		except Exception as e:
			frappe.log_error(f"Failed to parse ATTLOG line: {line}\n{frappe.get_traceback()}", "ATTLOG Parse Error")
	
	return records


def parse_operlog(body):
	"""
	Parse OPERLOG (operation log)
	Format: AdminPIN\tOperTime\tOpID\tOpObject\t...
	"""
	records = []
	lines = body.strip().split('\n')
	
	for line in lines:
		if not line.strip():
			continue
		
		fields = line.split('\t')
		if len(fields) < 2:
			continue
		
		try:
			record = {
				'admin_pin': fields[0].strip(),
				'oper_time': parse_device_datetime(fields[1].strip()),
				'op_id': fields[2].strip() if len(fields) > 2 else '',
				'op_object': fields[3].strip() if len(fields) > 3 else '',
				'extra': fields[4].strip() if len(fields) > 4 else '',
			}
			records.append(record)
		except Exception as e:
			frappe.log_error(f"Failed to parse OPERLOG line: {line}\n{frappe.get_traceback()}", "OPERLOG Parse Error")
	
	return records


def parse_userinfo(body):
	"""
	Parse USERINFO (user data)
	Format: PIN\tName\tPrivilege\tPassword\tCardNo\t...
	"""
	records = []
	lines = body.strip().split('\n')
	
	for line in lines:
		if not line.strip():
			continue
		
		fields = line.split('\t')
		if len(fields) < 1:
			continue
		
		try:
			record = {
				'pin': fields[0].strip(),
				'name': fields[1].strip() if len(fields) > 1 else '',
				'privilege': fields[2].strip() if len(fields) > 2 else '0',
				'password': fields[3].strip() if len(fields) > 3 else '',
				'card_no': fields[4].strip() if len(fields) > 4 else '',
				'group': fields[5].strip() if len(fields) > 5 else '',
				'timezone': fields[6].strip() if len(fields) > 6 else '',
				'verify_mode': fields[7].strip() if len(fields) > 7 else '',
			}
			records.append(record)
		except Exception as e:
			frappe.log_error(f"Failed to parse USERINFO line: {line}\n{frappe.get_traceback()}", "USERINFO Parse Error")
	
	return records


def parse_fingertmp(body):
	"""
	Parse FINGERTMP (fingerprint template)
	Format: PIN\tFID\tSize\tValid\tTemplate
	"""
	records = []
	lines = body.strip().split('\n')
	
	for line in lines:
		if not line.strip():
			continue
		
		fields = line.split('\t')
		if len(fields) < 4:
			continue
		
		try:
			record = {
				'pin': fields[0].strip(),
				'fid': fields[1].strip(),
				'size': fields[2].strip(),
				'valid': fields[3].strip(),
				'template': fields[4].strip() if len(fields) > 4 else '',
			}
			records.append(record)
		except Exception as e:
			frappe.log_error(f"Failed to parse FINGERTMP line: {line}\n{frappe.get_traceback()}", "FINGERTMP Parse Error")
	
	return records


def parse_device_datetime(dt_str):
	"""
	Parse device datetime string
	Formats: YYYY-MM-DD HH:MM:SS or variations
	"""
	formats = [
		'%Y-%m-%d %H:%M:%S',
		'%Y/%m/%d %H:%M:%S',
		'%Y-%m-%d %H:%M',
		'%d/%m/%Y %H:%M:%S',
		'%d/%m/%Y %H:%M',
	]
	
	for fmt in formats:
		try:
			dt = datetime.strptime(dt_str, fmt)
			return dt
		except ValueError:
			continue
	
	# If all else fails, try frappe's get_datetime
	try:
		return get_datetime(dt_str)
	except Exception:
		return now_datetime()
