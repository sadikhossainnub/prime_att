"""
Data parsers for ZKTeco protocol payloads
Handles tab-separated data with varying field counts across firmwares
Also supports key=value format from newer firmware
"""

import frappe
from frappe.utils import get_datetime
from datetime import datetime
import re


def normalize_line(line):
	"""Remove BOM, normalize CRLF to LF, strip whitespace"""
	# Remove UTF-8 BOM if present
	if line.startswith('\ufeff'):
		line = line[1:]
	# Normalize line endings
	line = line.replace('\r\n', '\n').replace('\r', '\n')
	return line.strip()


def parse_attlog(body):
	"""
	Parse ATTLOG (punch records)
	Format: PIN\tDateTime\tStatus\tVerify\tWorkCode\t...
	Or key=value format: PIN=123 DateTime=2024-01-01 10:00:00
	Field count varies by firmware - parse tolerantly
	"""
	records = []
	body = normalize_line(body)
	lines = body.split('\n')
	
	for line_num, line in enumerate(lines, 1):
		line = normalize_line(line)
		if not line:
			continue
		
		try:
			# Detect format: key=value or tab-separated
			if '=' in line and '\t' not in line:
				record = parse_key_value_line(line)
			else:
				fields = line.split('\t')
				if len(fields) < 2:
					frappe.log_error(f"ATTLOG line {line_num} has insufficient fields (need 2+): {line}", "ATTLOG Parse Error")
					continue
				
				record = {
					'pin': fields[0].strip(),
					'timestamp': fields[1].strip(),
					'status': fields[2].strip() if len(fields) > 2 else '0',
					'verify': fields[3].strip() if len(fields) > 3 else '0',
					'workcode': fields[4].strip() if len(fields) > 4 else '',
					'reserved1': fields[5].strip() if len(fields) > 5 else '',
					'reserved2': fields[6].strip() if len(fields) > 6 else '',
				}
			
			# Parse timestamp - skip line if invalid
			timestamp = parse_device_datetime(record.get('timestamp', ''))
			if timestamp is None:
				frappe.log_error(f"ATTLOG line {line_num} has invalid timestamp: {line}", "ATTLOG Parse Error")
				continue
			
			record['timestamp'] = timestamp
			records.append(record)
			
		except Exception as e:
			frappe.log_error(f"Failed to parse ATTLOG line {line_num}: {line}\n{frappe.get_traceback()}", "ATTLOG Parse Error")
	
	return records


def parse_operlog(body):
	"""
	Parse OPERLOG (operation log)
	Format: AdminPIN\tOperTime\tOpID\tOpObject\t...
	Or key=value format
	"""
	records = []
	body = normalize_line(body)
	lines = body.split('\n')
	
	for line_num, line in enumerate(lines, 1):
		line = normalize_line(line)
		if not line:
			continue
		
		try:
			# Detect format: key=value or tab-separated
			if '=' in line and '\t' not in line:
				record = parse_key_value_line(line)
			else:
				fields = line.split('\t')
				if len(fields) < 2:
					frappe.log_error(f"OPERLOG line {line_num} has insufficient fields (need 2+): {line}", "OPERLOG Parse Error")
					continue
				
				record = {
					'admin_pin': fields[0].strip(),
					'oper_time': fields[1].strip(),
					'op_id': fields[2].strip() if len(fields) > 2 else '',
					'op_object': fields[3].strip() if len(fields) > 3 else '',
					'extra': fields[4].strip() if len(fields) > 4 else '',
				}
			
			# Parse timestamp - skip line if invalid
			timestamp = parse_device_datetime(record.get('oper_time', ''))
			if timestamp is None:
				frappe.log_error(f"OPERLOG line {line_num} has invalid timestamp: {line}", "OPERLOG Parse Error")
				continue
			
			record['oper_time'] = timestamp
			records.append(record)
			
		except Exception as e:
			frappe.log_error(f"Failed to parse OPERLOG line {line_num}: {line}\n{frappe.get_traceback()}", "OPERLOG Parse Error")
	
	return records


def parse_userinfo(body):
	"""
	Parse USERINFO (user data)
	Format: PIN\tName\tPrivilege\tPassword\tCardNo\t...
	Or key=value format
	"""
	records = []
	body = normalize_line(body)
	lines = body.split('\n')
	
	for line_num, line in enumerate(lines, 1):
		line = normalize_line(line)
		if not line:
			continue
		
		try:
			# Detect format: key=value or tab-separated
			if '=' in line and '\t' not in line:
				record = parse_key_value_line(line)
			else:
				fields = line.split('\t')
				if len(fields) < 1:
					frappe.log_error(f"USERINFO line {line_num} has no fields: {line}", "USERINFO Parse Error")
					continue
				
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
			frappe.log_error(f"Failed to parse USERINFO line {line_num}: {line}\n{frappe.get_traceback()}", "USERINFO Parse Error")
	
	return records


def parse_fingertmp(body):
	"""
	Parse FINGERTMP (fingerprint template)
	Format: PIN\tFID\tSize\tValid\tTemplate
	Or key=value format
	"""
	records = []
	body = normalize_line(body)
	lines = body.split('\n')
	
	for line_num, line in enumerate(lines, 1):
		line = normalize_line(line)
		if not line:
			continue
		
		try:
			# Detect format: key=value or tab-separated
			if '=' in line and '\t' not in line:
				record = parse_key_value_line(line)
			else:
				fields = line.split('\t')
				if len(fields) < 4:
					frappe.log_error(f"FINGERTMP line {line_num} has insufficient fields (need 4+): {line}", "FINGERTMP Parse Error")
					continue
				
				record = {
					'pin': fields[0].strip(),
					'fid': fields[1].strip(),
					'size': fields[2].strip(),
					'valid': fields[3].strip(),
					'template': fields[4].strip() if len(fields) > 4 else '',
				}
			
			records.append(record)
			
		except Exception as e:
			frappe.log_error(f"Failed to parse FINGERTMP line {line_num}: {line}\n{frappe.get_traceback()}", "FINGERTMP Parse Error")
	
	return records


def parse_key_value_line(line):
	"""
	Parse key=value format line
	Example: PIN=123 DateTime=2024-01-01 10:00:00 Status=1
	"""
	record = {}
	# Match key=value pairs, handling quoted values
	pattern = r'(\w+)=([^\s]+(?:\s+[^\s=]+)*?)(?=\s+\w+=|$)'
	matches = re.findall(pattern, line)
	
	for key, value in matches:
		# Normalize keys to lowercase for consistency
		key_lower = key.lower()
		record[key_lower] = value.strip()
	
	return record


def parse_device_datetime(dt_str):
	"""
	Parse device datetime string - returns None if invalid
	Formats: YYYY-MM-DD HH:MM:SS or variations
	NEVER falls back to now() - invalid timestamps are rejected
	"""
	if not dt_str or not dt_str.strip():
		return None
	
	dt_str = dt_str.strip()
	
	# Try common formats
	formats = [
		'%Y-%m-%d %H:%M:%S',
		'%Y/%m/%d %H:%M:%S',
		'%Y-%m-%d %H:%M',
		'%d/%m/%Y %H:%M:%S',
		'%d/%m/%Y %H:%M',
		'%Y%m%d %H:%M:%S',  # Compact format
		'%Y-%m-%dT%H:%M:%S',  # ISO format
	]
	
	for fmt in formats:
		try:
			dt = datetime.strptime(dt_str, fmt)
			# Sanity check: reject dates before 2000 or after 2100
			if dt.year < 2000 or dt.year > 2100:
				return None
			return dt
		except ValueError:
			continue
	
	# Try frappe's get_datetime as last resort
	try:
		dt = get_datetime(dt_str)
		if dt.year < 2000 or dt.year > 2100:
			return None
		return dt
	except Exception:
		return None
