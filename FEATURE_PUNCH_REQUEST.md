# Punch Request - Documentation

## Overview

**Punch Request** হল একটি approval-based system যা employees দের manual punch request করতে দেয় যখন তারা device-এ punch করতে ভুলে যায় বা punch করতে পারেনি।

## Key Features

### 1. **Universal Access**
- সব users request তৈরি করতে পারবে (Role: All)
- নিজের request submit করতে পারবে
- অন্যের request দেখতে পারবে (read permission)

### 2. **Approval Workflow**
চারটি status:
- **Draft** - Initial state, editing করা যায়
- **Pending Approval** - Submit করার পর, approval এর জন্য waiting
- **Approved** - Admin approve করেছে, punch record তৈরি হয়েছে
- **Rejected** - Admin reject করেছে with reason

### 3. **Role-Based Permissions**

| Role | Create | Read | Write | Submit | Approve/Reject | Delete |
|------|--------|------|-------|--------|----------------|--------|
| All | ✅ | ✅ | ✅ (own) | ✅ (own) | ❌ | ❌ |
| ZK Operator | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| ZK Admin | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |
| System Manager | ✅ | ✅ | ✅ | ✅ | ✅ | ✅ |

### 4. **Auto Notifications**
- Submit করলে ZK Admin এবং System Manager দের notification যায়
- Notification Log-এ alert হিসেবে থাকে

### 5. **Punch Creation**
- Approve হলে automatically ZK Punch record তৈরি হয়
- ZK Check-in Out record ও তৈরি হয় (HRMS sync এর জন্য)
- Created punch এর link request-এ save হয়

## Usage Guide

### For Employees (All Users)

#### Step 1: Create Request
1. Navigate to: **Punch Request** → **New**
2. Fill in:
   - **Employee:** Select yourself from ZK Person list
   - **Device:** Select device (auto-populated if only one)
   - **Request Type:** 
     - Manual Punch - নতুন punch add করার জন্য
     - Missed Punch - ভুলে যাওয়া punch এর জন্য
     - Correction - ভুল punch correct করার জন্য
   - **Punch Date:** কোন তারিখের punch
   - **Punch Time:** কত সময়ে punch করেছিলেন/করতে চান
   - **Reason:** কেন এই request করছেন (required)
3. Click **Save**

#### Step 2: Submit for Approval
1. Review সব information
2. Click **Submit for Approval** button
3. Status change হবে **Pending Approval**-তে
4. Approvers দের notification যাবে

#### Step 3: Wait for Decision
- Email/Notification check করুন approval/rejection এর জন্য
- Request list-এ status দেখতে পারবেন
- Approved হলে created punch দেখতে পারবেন
- Rejected হলে rejection reason দেখতে পারবেন

### For Approvers (ZK Admin / System Manager)

#### Step 1: Review Requests
1. Navigate to: **Punch Request** list
2. Filter by: **Pending Approval**
3. Open request to review details:
   - Employee information
   - Requested date/time
   - Reason
   - Request type

#### Step 2: Approve or Reject

**To Approve:**
1. Click **Approve** button
2. Confirm approval
3. System automatically:
   - Creates ZK Punch record
   - Creates ZK Check-in Out record
   - Updates request status to **Approved**
   - Records approver name and timestamp
   - Notifies employee (optional)

**To Reject:**
1. Click **Reject** button
2. Enter rejection reason (required)
3. System updates:
   - Status to **Rejected**
   - Records rejector name and timestamp
   - Saves rejection reason
   - Notifies employee (optional)

#### Bulk Approval
1. Select multiple pending requests (checkbox)
2. Click **Bulk Approve Selected** (Action dropdown)
3. Confirm bulk approval
4. System processes all selected requests

## Field Descriptions

### Employee Information Section
- **Employee ID** (Link to ZK Person) - কে punch request করছে
- **Employee Name** (Read-only) - Auto-fetched
- **Department** (Read-only) - Auto-fetched if available
- **Designation** (Read-only) - Auto-fetched if available

### Request Details Section
- **Device** (Link to ZK Device) - কোন device-এ punch হয়েছিল/হবে
- **Request Type** (Select) - Manual Punch / Missed Punch / Correction
- **Punch Date** (Date) - কোন date-এ punch (cannot be future)
- **Punch Time** (Time) - কত সময়ে punch (HH:MM:SS)

### Reason Section
- **Reason for Request** (Text) - কেন এই request করছেন (required)

### Status Section
- **Status** (Select, Read-only) - Draft / Pending / Approved / Rejected
- **Approved/Rejected By** (Link to User) - কে approve/reject করেছে
- **Approved/Rejected On** (Datetime) - কখন approve/reject হয়েছে

### Punch Details Section (Approved only)
- **Created Punch Record** (Link to ZK Punch) - Created punch এর link

### Rejection Section (Rejected only)
- **Rejection Reason** (Text) - কেন reject করা হয়েছে

## API Methods

### 1. Submit for Approval
```python
frappe.call({
    method: 'prime_att.prime_attendance_system.doctype.punch_request.punch_request.submit_for_approval',
    args: { name: 'PR-0001' }
})
```

### 2. Approve Request
```python
frappe.call({
    method: 'prime_att.prime_attendance_system.doctype.punch_request.punch_request.approve_request',
    args: { name: 'PR-0001' }
})
```

### 3. Reject Request
```python
frappe.call({
    method: 'prime_att.prime_attendance_system.doctype.punch_request.punch_request.reject_request',
    args: {
        name: 'PR-0001',
        rejection_reason: 'Invalid date/time'
    }
})
```

## Validation Rules

1. **Punch Date/Time:**
   - Cannot be in the future
   - Must be valid date and time format

2. **Employee:**
   - Must exist in ZK Person
   - Must be required field

3. **Device:**
   - Must exist in ZK Device
   - Preferably Active status

4. **Reason:**
   - Required field
   - Cannot be empty

5. **Status Transitions:**
   - Draft → Pending Approval (on submit)
   - Pending Approval → Approved (by admin)
   - Pending Approval → Rejected (by admin)
   - Cannot go back from Approved/Rejected

## Notifications

### On Submit (Pending Approval)
**To:** ZK Admin, System Manager  
**Subject:** Punch Request {name} needs approval  
**Content:**
```
A new punch request needs your approval:
- Employee: {employee_name}
- Date: {punch_date}
- Time: {punch_time}
- Reason: {reason}

[View Request]
```

### On Approval (Optional - can be customized)
**To:** Request Creator  
**Subject:** Your Punch Request {name} has been approved  

### On Rejection (Optional - can be customized)
**To:** Request Creator  
**Subject:** Your Punch Request {name} has been rejected  
**Content:** Rejection reason included

## Reports & Filters

### Standard Filters
- **Status:** Draft / Pending / Approved / Rejected
- **Employee:** Filter by employee
- **Device:** Filter by device
- **Punch Date:** Date range

### Custom Reports (Future)
- Pending Approval Report
- Approved Requests by Employee
- Rejected Requests Analysis
- Daily/Monthly Request Summary

## Security & Audit

### Audit Trail
- Track Changes enabled - সব modifications logged
- Created By, Modified By automatically tracked
- Approval/Rejection timestamp saved
- Approver/Rejector name saved

### Data Integrity
- Cannot modify approved requests
- Cannot delete approved requests with punch
- Rejection reason mandatory
- Status transitions controlled

## Best Practices

### For Employees
1. ✅ Request করার সাথে সাথে proper reason দিন
2. ✅ Correct date এবং time verify করুন submit করার আগে
3. ✅ একই punch এর জন্য duplicate request করবেন না
4. ✅ Status regularly check করুন

### For Approvers
1. ✅ Request details carefully review করুন
2. ✅ Reason reasonable কিনা check করুন
3. ✅ Date/time conflict check করুন (duplicate punch)
4. ✅ Reject করলে clear reason দিন
5. ✅ Regular intervals-এ pending requests check করুন

### For Administrators
1. ✅ Regular reporting দেখুন abuse detect করার জন্য
2. ✅ Policy set করুন কতদিন পর্যন্ত request করা যাবে
3. ✅ Notification settings configure করুন
4. ✅ Backup maintain করুন

## Troubleshooting

### Request Not Submitting
- Check all required fields filled
- Verify date/time not in future
- Check network connection
- Review browser console for errors

### Notification Not Received
- Check Notification Settings in User profile
- Verify email configuration in Site Settings
- Check Notification Log doctype
- Ensure approvers have correct roles

### Punch Not Created After Approval
- Check Error Log for errors
- Verify ZK Person exists with valid PIN
- Ensure device exists and accessible
- Check create_checkin_out function logs

### Cannot Approve/Reject
- Verify you have ZK Admin or System Manager role
- Check request is in Pending Approval status
- Ensure no browser cache issues
- Review user permissions

## Technical Details

### File Structure
```
prime_att/prime_attendance_system/doctype/punch_request/
├── __init__.py
├── punch_request.json          # DocType definition
├── punch_request.py            # Server-side controller
├── punch_request.js            # Client-side controller
├── punch_request_list.js       # List view customization
└── test_punch_request.py       # Unit tests
```

### Database Schema
- **Table:** `tabPunch Request`
- **Naming:** PR-#### (auto-increment)
- **Is Submittable:** Yes (document workflow)
- **Track Changes:** Yes (audit trail)

### Integration Points
- **ZK Person:** Employee selection
- **ZK Device:** Device selection
- **ZK Punch:** Punch creation on approval
- **ZK Check-in Out:** Check-in/out creation via processor

## Future Enhancements

Possible improvements:
- [ ] Email notifications on status change
- [ ] SMS notifications
- [ ] Mobile app support
- [ ] Batch request creation
- [ ] Auto-approval rules (based on criteria)
- [ ] Request templates for common scenarios
- [ ] Calendar view for requests
- [ ] Manager-level approval (multi-level)
- [ ] Integration with leave management
- [ ] Geolocation validation
- [ ] Attachment support (proof/documents)

## Related Documentation

- TESTING_GUIDE.md - Testing procedures
- FEATURE_PUNCH_FETCH.md - Punch fetch feature
- API.md - API reference

---

**Version:** 2.0.0  
**Created:** November 2, 2026  
**DocType:** Punch Request  
**Module:** Prime Attendance System  
**Status:** Ready for testing
