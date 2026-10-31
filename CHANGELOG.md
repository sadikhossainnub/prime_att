# Changelog

All notable changes to Prime Att will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2024-10-31

### Added
- Complete iClock protocol implementation
  - GET /iclock/cdata - Device handshake
  - POST /iclock/cdata - Data upload (ATTLOG, USERINFO, FINGERTMP, OPERLOG)
  - GET /iclock/getrequest - Command polling
  - POST /iclock/devicecmd - Command results
- Device management
  - Auto-registration of unknown devices
  - Device status (Pending/Active/Blocked)
  - Online/offline detection
  - Last activity tracking
  - Configurable poll intervals
  - Communication key authentication
- User management
  - ZK Person doctype with device mapping
  - Push to Devices functionality
  - Pull users from device
  - Delete user from device
  - Employee mapping (two methods)
  - Bulk mapping tool
- Fingerprint enrollment
  - Interactive enrollment workflow
  - Multi-finger support (0-9)
  - Configurable command templates
  - Walk-up enrollment support
  - Status tracking (Queued → Sent → Waiting → Enrolled)
  - Retry mechanism
  - Encrypted template storage
- Punch processing
  - Raw punch storage (ZK Punch)
  - Check-in/out conversion (ZK Check-in Out)
  - Timezone conversion
  - Duplicate detection with tolerance
  - Status code mapping
  - Unknown PIN handling
- HRMS synchronization
  - Local HRMS mode
  - Remote ERPNext mode
  - Idempotent sync (no duplicates)
  - Automatic background sync
  - Exponential backoff retry
  - Manual retry for failed records
  - Comprehensive sync logging
- Command system
  - Command queue (ZK Device Command)
  - Command templates (ZK Command Template)
  - Bidirectional communication
  - Command status tracking
  - Timeout handling
- Logging & debugging
  - Raw payload logging (ZK Raw Log)
  - Operation logging (ZK Operation Log)
  - Sync logging (ZK Sync Log)
  - Error tracking
- Security
  - Role-based access (ZK Admin, ZK Operator)
  - Encrypted biometric templates
  - Device authentication
  - Rate limiting
- UI enhancements
  - Custom buttons on forms
  - Interactive dialogs
  - Status indicators
  - Navigation shortcuts
- Testing tools
  - Device simulator (test and heartbeat modes)
  - Unit tests
  - Sample payloads
- Documentation
  - README with installation guide
  - QUICKSTART guide (15-minute setup)
  - TESTING guide with regression checklist
  - API documentation
  - SUMMARY document
  - Nginx configuration template
- Installation tools
  - Automated setup script
  - DocType creation script
  - Default settings initialization
  - Role setup
- Compatibility
  - Frappe v15.x support
  - Frappe v16.x support
  - ZKTeco F18, K40, K50 devices
  - All iClock-compatible devices

### Technical Details
- 31 files created
- 14 DocTypes implemented
- ~3500+ lines of code
- 7 core Python modules
- 4 JavaScript client files
- 6 documentation files
- Complete test suite

### Dependencies
- pytz >= 2021.1
- requests >= 2.25.1
- frappe >= 15.0.0

## [Unreleased]

### Planned
- Multi-timezone support (per-device)
- Face/photo template support
- Access control (door) commands
- Mobile app for direct punch submission
- Offline mode with local caching
- Analytics dashboard
- CSV bulk import/export
- Advanced IN/OUT determination rules

### Notes
- No dashboards - HRMS handles this
- No alerts - HRMS handles this
- No shift logic - HRMS handles this
- No attendance calculation - HRMS handles this

These are intentional design decisions to keep Prime Att focused on device communication and data collection, while HRMS handles business logic.

## Version History

- **1.0.0** (2024-10-31) - Initial release
  - Complete feature set as specified
  - Production-ready
  - Fully tested and documented
