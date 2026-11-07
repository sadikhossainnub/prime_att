"""
iClock Protocol Handler for ZKTeco ADMS

Implements the ZKTeco PUSH SDK / iClock protocol for device communication.
All endpoints must respond with text/plain (not JSON).
"""

import frappe
from frappe.utils import now
import hmac
from werkzeug.wrappers import Response
from werkzeug.exceptions import HTTPException
from urllib.parse import parse_qs
from prime_att.zkteco.device_manager import register_device, get_device_config, update_device_activity




def handle_iclock_before_request():
	"""
	before_request hook: intercepts /iclock/* requests and serves them
	as plain text, bypassing Frappe's default JSON response path.
	
	Must check path first (fast path for non-iclock requests), then
	process /iclock/cdata, /iclock/getrequest, /iclock/devicecmd.
	
	Raises HTTPException with plain-text Response to bypass normal routing.
	"""
	path = frappe.local.request.path
	
	# Fast path: not an iclock request
	if not path.startswith('/iclock/'):
		return
	
	try:
		# Check for valid endpoints
		if path not in ['/iclock/cdata', '/iclock/getrequest', '/iclock/devicecmd']:
			# Unknown iclock path - return plain-text 404
			frappe.db.commit()
			raise HTTPException(response=Response(
				"ERROR: Unknown endpoint",
				status=404,
				mimetype="text/plain"
			))
		
		# Get serial number from query params
		sn = frappe.local.request.args.get('SN', '').strip()
		if not sn:
			frappe.db.commit()
			raise HTTPException(response=Response(
				"ERROR: Missing SN",
				status=400,
				mimetype="text/plain"
			))
		
		# Validate and get device
		device = validate_device(sn)
		if not device:
			frappe.db.commit()
			raise HTTPException(response=Response(
				"ERROR: Invalid or blocked device",
				status=403,
				mimetype="text/plain"
			))
		
		# Route to appropriate handler
		method = frappe.local.request.method
		
		if path == '/iclock/cdata':
			if method == 'GET':
				body = handle_handshake(sn, device)
			else:  # POST
				body = handle_cdata_post(sn, device)
		elif path == '/iclock/getrequest':
			body = handle_getrequest(sn, device)
		elif path == '/iclock/devicecmd':
			body = handle_devicecmd(sn, device)
		
		# Commit before raising HTTPException (Frappe rolls back on HTTPException)
		frappe.db.commit()
		
		# Return plain-text response
		raise HTTPException(response=Response(
			body,
			status=200,
			mimetype="text/plain"
		))
		
	except HTTPException:
		# Re-raise HTTPException as-is
		raise
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "iClock Protocol Error")
		frappe.db.commit()
		raise HTTPException(response=Response(
			"ERROR: Internal error",
			status=500,
			mimetype="text/plain"
		))


def validate_device(sn):
	"""
	Validate device and check if it's blocked
	Returns device doc or None
	
	Security checks:
	- Device exists and is Active/Pending
	- Blocked devices are rejected
	- comm_key validated with constant-time comparison if set
	- Pending devices can handshake but not process data
	"""
	try:
		device = frappe.get_doc("ZK Device", sn)
		
		# Blocked devices rejected
		if device.status == "Blocked":
			frappe.log_error(f"Blocked device attempted connection: {sn}", "Device Auth Failed")
			return None
		
		# Validate comm key if configured (constant-time comparison)
		# Devices may send 'key' or 'comkey' parameter
		comm_key = frappe.local.request.args.get('key', '') or frappe.local.request.args.get('comkey', '')
		if device.comm_key:
			expected_key = device.get_password("comm_key")
			if not expected_key or not hmac.compare_digest(expected_key, comm_key):
				frappe.log_error(f"Invalid comm key for device {sn}", "Device Auth Failed")
				return None
		
		return device
		
	except frappe.DoesNotExistError:
		# Check if auto-registration is enabled
		settings = frappe.get_single("ZK Settings")
		if settings.get("allow_auto_register", 1):
			return register_device(sn)
		else:
			frappe.log_error(f"Unknown device rejected (auto-register disabled): {sn}", "Device Auth Failed")
			return None


def check_rate_limit(sn, ip=None):
	"""
	Check rate limit for device/IP
	Returns True if rate limit exceeded
	UNVERIFIED: Rate limit algorithm - current implementation uses simple counter per minute
	"""
	settings = frappe.get_single("ZK Settings")
	max_requests = settings.get("rate_limit_requests", 60)
	
	if not max_requests:
		return False
	
	cache = frappe.cache()
	minute_key = f"ratelimit:{sn}:{now()[:16]}"  # per minute
	
	count = cache.get(minute_key) or 0
	if count >= max_requests:
		return True
	
	cache.setex(minute_key, 60, count + 1)
	return False


def handle_handshake(sn, device):
	"""
	GET /iclock/cdata?SN=xxx&options=all&pushver=xxx&language=xxx
	Returns device configuration
	
	UNVERIFIED: Response format - based on common iClock implementations
	"""
	args = frappe.local.request.args
	options = args.get('options', '')
	pushver = args.get('pushver', '')
	language = args.get('language', '')
	
	# Log handshake
	create_raw_log(sn, "HANDSHAKE", f"options={options}&pushver={pushver}&language={language}")
	
	# Update device activity
	update_device_activity(sn, pushver, language)
	
	# Get device configuration
	config = get_device_config(device)
	
	# Get settings for poll interval
	settings = frappe.get_single("ZK Settings")
	
	# Check if enrollment is active (use short poll interval)
	has_active_enrollment = frappe.db.exists("ZK Fingerprint Enrollment", {
		"device": sn,
		"status": ["in", ["Queued", "Sent", "Waiting for User"]],
		"creation": [">", frappe.utils.add_to_date(now(), seconds=-settings.get("enrollment_timeout", 180))]
	})
	
	delay = config.get('poll_interval_short', 5) if has_active_enrollment else config.get('delay', 30)
	
	# Build response (UNVERIFIED format)
	lines = []
	lines.append(f"Stamp={config.get('stamp', '9999')}")
	lines.append(f"OpStamp={config.get('opstamp', '9999')}")
	lines.append(f"ErrorDelay={config.get('error_delay', '120')}")
	lines.append(f"Delay={delay}")
	lines.append("TransTimes=00:00;23:59")
	lines.append("TransInterval=1")
	lines.append("TransFlag=TransData AttLog OpLog EnrollUser ChgUser")
	lines.append("Realtime=1")
	lines.append("Encrypt=0")
	
	return "\n".join(lines)


def handle_cdata_post(sn, device):
	"""
	POST /iclock/cdata?SN=xxx&table=ATTLOG
	Body: tab-separated data rows or key=value format
	
	UNVERIFIED: Body format - supporting both tab-separated and key=value
	"""
	# Check rate limit
	if check_rate_limit(sn):
		return "ERROR: Rate limit exceeded"
	
	args = frappe.local.request.args
	table = args.get('table', '').upper()
	
	# Get body with size limit
	settings = frappe.get_single("ZK Settings")
	max_body_size = settings.get("max_post_body_size", 1024 * 1024)  # 1MB default
	
	body = frappe.local.request.get_data(as_text=True)
	if len(body) > max_body_size:
		frappe.log_error(f"POST body too large: {len(body)} bytes from {sn}", "iClock Protocol")
		return "ERROR: Body too large"
	
	# Store raw log immediately
	create_raw_log(sn, table, body)
	
	# Pending devices: store data but don't process
	if device.status == "Pending":
		return "OK"
	
	# Active devices: process in background
	frappe.enqueue(
		'prime_att.zkteco.processor.process_device_data',
		queue='default',
		timeout=300,
		sn=sn,
		table=table,
		body=body
	)
	
	return "OK"


def handle_getrequest(sn, device):
	"""
	GET /iclock/getrequest?SN=xxx
	Heartbeat + command polling
	Returns pending commands or "OK"
	
	Command lifecycle:
	- Pending -> Sent (first time, or retry if timeout and attempts < max)
	- Sent commands with no response after timeout may be resent
	- Destructive commands (REBOOT, CLEAR, DELETE) never auto-resent
	"""
	# Update device activity
	update_device_activity(sn)
	
	# Pending devices don't get commands
	if device.status == "Pending":
		return "OK"
	
	# Get settings
	settings = frappe.get_single("ZK Settings")
	command_timeout = settings.get("command_timeout", 120)
	max_attempts = settings.get("command_max_attempts", 3)
	
	# Check for Pending commands or Sent commands that timed out
	timeout_time = frappe.utils.add_to_date(now(), seconds=-command_timeout)
	
	commands = frappe.get_all(
		"ZK Device Command",
		filters=[
			["device", "=", sn],
			["status", "in", ["Pending", "Sent"]],
			"|",
			["status", "=", "Pending"],
			[
				["status", "=", "Sent"],
				["sent_time", "<", timeout_time],
				["attempts", "<", max_attempts]
			]
		],
		fields=["name", "command", "status", "attempts", "sent_time"],
		order_by="creation asc",
		limit=1
	)
	
	if commands:
		cmd = commands[0]
		cmd_doc = frappe.get_doc("ZK Device Command", cmd.name)
		
		# Check if destructive command - never resend
		is_destructive = any(keyword in cmd_doc.command.upper() 
			for keyword in ["REBOOT", "CLEAR LOG", "CLEAR DATA", "DELETE", "CLEAR ADMIN"])
		
		if cmd.status == "Sent" and is_destructive:
			# Destructive command timed out - mark as Failed
			cmd_doc.status = "Failed"
			cmd_doc.response = "No response (timeout)"
			cmd_doc.save(ignore_permissions=True)
			return "OK"
		
		# Send/resend command
		cmd_doc.status = "Sent"
		cmd_doc.sent_time = now()
		cmd_doc.attempts = (cmd_doc.attempts or 0) + 1
		cmd_doc.save(ignore_permissions=True)
		
		# Return command in iClock format: C:<id>:<command>
		# UNVERIFIED: Command format
		return f"C:{cmd_doc.name}:{cmd_doc.command}"
	
	return "OK"


def handle_devicecmd(sn, device):
	"""
	POST /iclock/devicecmd?SN=xxx&ID=xxx
	Device sends command result
	Body: URL-encoded (Return=0&CMD=...)
	
	UNVERIFIED: Success determined by Return=0 (configurable in settings)
	"""
	args = frappe.local.request.args
	cmd_id = args.get('ID', '').strip()
	
	# Parse body as URL-encoded regardless of Content-Type
	body = frappe.local.request.get_data(as_text=True)
	
	if cmd_id:
		try:
			cmd_doc = frappe.get_doc("ZK Device Command", cmd_id)
			
			# Store raw response
			cmd_doc.response = body
			cmd_doc.completed_time = now()
			
			# Parse response
			try:
				parsed = parse_qs(body)
				return_code = parsed.get('Return', [''])[0] or parsed.get('RETURN', [''])[0] or parsed.get('return', [''])[0]
			except:
				return_code = ''
			
			# Check success condition (UNVERIFIED - configurable)
			settings = frappe.get_single("ZK Settings")
			success_return = settings.get("command_success_return", "0")
			
			if return_code == success_return:
				cmd_doc.status = "Done"
			else:
				cmd_doc.status = "Failed"
			
			cmd_doc.save(ignore_permissions=True)
			
			# If enrollment command completed, update enrollment status
			if cmd_doc.command.startswith("DATA ENROLL") or "ENROLL_FP" in cmd_doc.command:
				update_enrollment_status(cmd_id, cmd_doc.status)
			
		except frappe.DoesNotExistError:
			frappe.log_error(f"Device {sn} sent result for unknown command: {cmd_id}", "iClock Protocol")
	
	return "OK"


def update_enrollment_status(command_id, command_status):
	"""Update enrollment record when command completes"""
	try:
		enrollment = frappe.db.get_value(
			"ZK Fingerprint Enrollment",
			{"command": command_id},
			["name", "status"],
			as_dict=True
		)
		
		if enrollment:
			if command_status == "Done":
				frappe.db.set_value("ZK Fingerprint Enrollment", enrollment.name, {
					"status": "Waiting for User"
				})
			elif command_status == "Failed":
				frappe.db.set_value("ZK Fingerprint Enrollment", enrollment.name, {
					"status": "Failed"
				})
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Enrollment Status Update Failed")


def create_raw_log(sn, table, body):
	"""Store raw payload for debugging and processing"""
	try:
		doc = frappe.get_doc({
			"doctype": "ZK Raw Log",
			"device": sn,
			"log_type": table,
			"payload": body,
			"received_at": now()
		})
		doc.insert(ignore_permissions=True)
	except Exception as e:
		frappe.log_error(frappe.get_traceback(), "Failed to create raw log")
