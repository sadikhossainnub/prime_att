# Punch Request DocType

## Quick Start

### For Employees
1. Create new Punch Request
2. Fill employee, device, date, time, reason
3. Click "Submit for Approval"
4. Wait for approval/rejection notification

### For Approvers (ZK Admin / System Manager)
1. Go to Punch Request list
2. Filter "Pending Approval"
3. Open request
4. Click "Approve" or "Reject"

## Status Flow

```
Draft → Pending Approval → Approved ✓ (Punch Created)
                        → Rejected ✗ (with reason)
```

## Permissions

| Role | Access Level |
|------|-------------|
| All | Create, Read, Write (own), Submit (own) |
| ZK Operator | Full access + Approve/Reject |
| ZK Admin | Full access + Approve/Reject |
| System Manager | Full access |

## Key Features

- ✅ Universal access for all users
- ✅ Approval workflow with notifications
- ✅ Auto punch creation on approval
- ✅ Rejection with mandatory reason
- ✅ Bulk approval support
- ✅ Audit trail with track changes
- ✅ Integration with ZK Punch and Check-in Out

## API Methods

```python
# Submit for approval
punch_request.submit_for_approval(name)

# Approve
punch_request.approve_request(name)

# Reject
punch_request.reject_request(name, rejection_reason)
```

See **FEATURE_PUNCH_REQUEST.md** for complete documentation.
