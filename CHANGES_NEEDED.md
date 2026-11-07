# Remaining Changes Required for prime_att v16 Compliance

## Status: PARTIALLY IMPLEMENTED

### ✅ COMPLETED

1. **Plain-text /iclock/* responses (Issue #1)** - DONE
   - Rewrote handle_iclock_before_request to use HTTPException with werkzeug Response
   - Removed invalid frappe.response['type']='text'
   - Added frappe.db.commit() before raising HTTPException
   - Fast path check for non-iclock requests
   - Removed duplicate iclock_handler, website_route_rules, auth_hooks, handle_iclock_request

2. **Command lifecycle basics (Issue #2)** - PARTIALLY DONE
   - ZK Device Command: Changed to autoincrement naming ✅
   - Added attempts field ✅
   - Implemented timeout and retry logic ✅
   - Destructive commands handled (REBOOT, CLEAR, DELETE) ✅
   - Fixed devicecmd to parse Return= from URL-encoded body ✅
   - Configurable success condition (command_success_return) ✅

3. **Security - Device validation (Issue #3)** - PARTIALLY DONE
   - Added hmac.compare_digest for comm_key ✅
   - Added allow_auto_register checkbox ✅
   - Pending devices store but don't process ✅
   - Rate limiting implemented ✅
   - Max POST body size check ✅

4. **ZK Settings expanded (Issues #2, #3, #5, #6)** - DONE
   - Added security fields (allow_auto_register, max_post_body_size) ✅
   - Added command lifecycle fields (timeout, max_attempts, success_return, enrollment_timeout) ✅
   - Added IN/OUT mode selector ✅
   - Added editable command templates (UNVERIFIED) ✅

### ⚠️ IN PROGRESS / NEEDS COMPLETION

5. **Security - Role checks on whitelisted methods (Issue #3)**
   - Files to update:
     - `prime_att/zkteco/enrollment_manager.py`: Add `frappe.only_for()` to all whitelisted functions
     - `prime_att/zkteco/sync_manager.py`: Add role checks
     - `prime_att/zkteco/device_manager.py`: Add role checks
   - Required roles:
     - ZK Admin / System Manager: restart_device, sync_device_time, sync_all_users_to_device, delete_user_from_device, check_enrollment_status
     - ZK Operator allowed: enroll_fingerprint, push_to_devices, pull_users_from_device, bulk_map_employees
   - Remove ignore_permissions where not needed

6. **Standalone without ERPNext (Issue #4)**
   - Update ZK Person DocType JSON:
     - Change employee field from Link to Data (employee_id)
   - Create employee_doctype_available() helper function
   - Update all code that references Employee to check availability first
   - Files to update:
     - `prime_att/prime_attendance_system/doctype/zk_person/zk_person.json`
     - `prime_att/prime_attendance_system/doctype/zk_person/zk_person.py`
     - `prime_att/zkteco/sync_manager.py`
     - `prime_att/zkteco/enrollment_manager.py`
   - Update pyproject.toml: requires-python = ">=3.10"

7. **IN/OUT detection modes (Issue #5)**
   - Implement in processor.py:
     - Mode a: Device status mapping (current) ✅ partial
     - Mode b: Alternate per person per day
     - Mode c: First/Last of day
   - Process punches in time order
   - Unknown status must NOT default to IN
   - Files: `prime_att/zkteco/processor.py`

8. **Parser improvements (Issue #6)**
   - Update parser.py:
     - NEVER fall back to now() for invalid timestamps - skip line and log error
     - Support both tab-separated AND key=value formats (e.g., "USER PIN=1<TAB>Name=...")
     - Handle CRLF and BOM
     - Update parse_attlog, parse_userinfo, parse_operlog, parse_fingertmp
   - Files: `prime_att/zkteco/parser.py`

9. **HRMS sync fixes (Issue #7)**
   - sync_remote in sync_manager.py:
     - Fix fields=['name'] - use proper params with json.dumps
     - Check response status before POST
     - Mark Failed with reason on error
   - Auto-retry "No Mapping" check-ins when person gets employee_id
   - Add "Sync Now" button on ZK Sync Connector (with role check)
   - retry_failed_checkin must enqueue, not run inline
   - Keep sync idempotent
   - Files: `prime_att/zkteco/sync_manager.py`

10. **Enrollment and users (Issue #8)**
    - Scheduler: mark old enrollments as Timeout (based on enrollment_timeout)
    - Auto-update enrollment to "Waiting for User" when command result arrives (✅ implemented)
    - Add is_placeholder flag to ZK Person JSON
    - sync_all_users_to_device: skip placeholders
    - Person form: support push/enroll without pre-selected devices
    - Files:
      - `prime_att/prime_attendance_system/doctype/zk_person/zk_person.json`
      - `prime_att/prime_attendance_system/doctype/zk_person/zk_person.py`
      - `prime_att/prime_attendance_system/doctype/zk_person/zk_person.js`
      - `prime_att/zkteco/enrollment_manager.py`
      - `prime_att/zkteco/device_manager.py` (poll_devices scheduler)

11. **Reliability and cleanup (Issue #9)**
    - update_device_activity: use frappe.db.set_value(..., update_modified=False)
    - Creating ZK Person: handle concurrent inserts (DuplicateEntryError)
    - Remove duplicate DocType definitions in install_script.py
    - Files:
      - `prime_att/zkteco/device_manager.py`
      - `prime_att/zkteco/processor.py`
      - `prime_att/install_script.py`

12. **nginx configuration (Issue #1)**
    - Update nginx/iclock.conf:
      - Add proxy_set_header X-Frappe-Site-Name instruction
      - Clarify location block must be inside server block
      - Explain bench port (default 8000)
    - Update README.md with same info

13. **Tests (Issue from requirements)**
    - Create/update tests in tests/ folder:
      - test_plain_text_response.py: Verify text/plain, not JSON/HTML
      - test_attlog_processing.py: ATTLOG creates punch
      - test_duplicate_tolerance.py
      - test_pending_device.py: Pending stored but not processed
      - test_comm_key.py: Wrong key rejected
      - test_command_lifecycle.py: Resend limits, destructive not resent
      - test_devicecmd.py: Return=0 marks Done
      - test_bad_timestamp.py: Invalid timestamp skipped, not now()
      - test_alternate_inout.py
      - test_remote_sync.py: Duplicate check
      - test_no_mapping_retry.py
      - test_role_enforcement.py

14. **Update CONFLICTS.md and README.md**
    - Ensure they match current implementation
    - Document all UNVERIFIED items
    - Add testing steps with curl examples

### 📝 NOTES

**UNVERIFIED items in code:**
- Response format for handshake
- Command formats (enroll, push, delete, reboot, pull, sync time)
- Body formats (tab-separated vs key=value)
- Return code for success (assumed Return=0)
- Rate limiting algorithm
- All command templates in ZK Settings

**Next Steps:**
1. Complete issues #3-#11 above
2. Write comprehensive tests
3. Test with actual F18 device or simulator
4. Update documentation
5. Create migration script for existing installations

**Testing Priority:**
1. Plain-text response (blocking)
2. Command lifecycle and resend logic
3. Security: role enforcement
4. Parser: bad timestamps, format detection
5. HRMS sync: duplicate prevention
6. Enrollment workflow
