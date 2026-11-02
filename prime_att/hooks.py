app_name = "prime_att"
app_title = "Prime Att"
app_publisher = "Prime Tech BD"
app_description = "ZKTeco ADMS (iClock protocol) server with device management, fingerprint enrollment, and HRMS sync"
app_email = "sayedtkg@gmail.com"
app_license = "mit"

# Apps
# ------------------

required_apps = ["frappe"]

# Each item in the list will be shown as an app in the apps page
# add_to_apps_screen = [
# 	{
# 		"name": "prime_att",
# 		"logo": "/assets/prime_att/logo.png",
# 		"title": "Prime Attendance System",
# 		"route": "/prime_att",
# 		"has_permission": "prime_att.api.permission.has_app_permission"
# 	}
# ]

# Includes in <head>
# ------------------

# include js, css files in header of desk.html
# app_include_css = "/assets/prime_att/css/prime_att.css"
# app_include_js = "/assets/prime_att/js/prime_att.js"

# include js, css files in header of web template
# web_include_css = "/assets/prime_att/css/prime_att.css"
# web_include_js = "/assets/prime_att/js/prime_att.js"

# include custom scss in every website theme (without file extension ".scss")
# website_theme_scss = "prime_att/public/scss/website"

# include js, css files in header of web form
# webform_include_js = {"doctype": "public/js/doctype.js"}
# webform_include_css = {"doctype": "public/css/doctype.css"}

# include js in page
# page_js = {"page" : "public/js/file.js"}

# include js in doctype views
# doctype_js = {"doctype" : "public/js/doctype.js"}
# doctype_list_js = {"doctype" : "public/js/doctype_list.js"}
# doctype_tree_js = {"doctype" : "public/js/doctype_tree.js"}
# doctype_calendar_js = {"doctype" : "public/js/doctype_calendar.js"}

# Svg Icons
# ------------------
# include app icons in desk
# app_include_icons = "prime_att/public/icons.svg"

# Home Pages
# ----------

# application home page (will override Website Settings)
# home_page = "login"

# website user home page (by Role)
# role_home_page = {
# 	"Role": "home_page"
# }

# Generators
# ----------

# automatically create page for each record of this doctype
# website_generators = ["Web Page"]

# automatically load and sync documents of this doctype from downstream apps
# importable_doctypes = [doctype_1]

# Jinja
# ----------

# add methods and filters to jinja environment
# jinja = {
# 	"methods": "prime_att.utils.jinja_methods",
# 	"filters": "prime_att.utils.jinja_filters"
# }

# Installation
# ------------

after_install = "prime_att.install_script.after_install"
before_uninstall = "prime_att.install_script.before_uninstall"

# Uninstallation
# ------------

# before_uninstall = "prime_att.uninstall.before_uninstall"
# after_uninstall = "prime_att.uninstall.after_uninstall"

# Integration Setup
# ------------------
# To set up dependencies/integrations with other apps
# Name of the app being installed is passed as an argument

# before_app_install = "prime_att.utils.before_app_install"
# after_app_install = "prime_att.utils.after_app_install"

# Integration Cleanup
# -------------------
# To clean up dependencies/integrations with other apps
# Name of the app being uninstalled is passed as an argument

# before_app_uninstall = "prime_att.utils.before_app_uninstall"
# after_app_uninstall = "prime_att.utils.after_app_uninstall"

# Build
# ------------------
# To hook into the build process

# after_build = "prime_att.build.after_build"

# Desk Notifications
# ------------------
# See frappe.core.notifications.get_notification_config

# notification_config = "prime_att.notifications.get_notification_config"

# Permissions
# -----------
# Permissions evaluated in scripted ways

# permission_query_conditions = {
# 	"Event": "frappe.desk.doctype.event.event.get_permission_query_conditions",
# }
#
# has_permission = {
# 	"Event": "frappe.desk.doctype.event.event.has_permission",
# }

# Document Events
# ---------------
# Hook on document methods and events

# doc_events = {
# 	"*": {
# 		"on_update": "method",
# 		"on_cancel": "method",
# 		"on_trash": "method"
# 	}
# }

# Scheduled Tasks
# ---------------

scheduler_events = {
	"cron": {
		"* * * * *": [
			"prime_att.zkteco.device_manager.poll_devices"
		]
	},
	"hourly": [
		"prime_att.zkteco.sync_manager.retry_failed_syncs"
	]
}

# Intercept /iclock/* requests before Frappe routing to return plain-text
before_request = ["prime_att.zkteco.iclock_protocol.handle_iclock_before_request"]

# Website route handlers (guest access for device endpoints)
website_route_rules = [
	{"from_route": "/iclock/<path:path>", "to_route": "iclock"},
]

# Auth hooks for device authentication
auth_hooks = [
	"prime_att.zkteco.iclock_protocol.validate_device_auth"
]

# Testing
# -------

# before_tests = "prime_att.install.before_tests"

# Extend DocType Class
# ------------------------------
#
# Specify custom mixins to extend the standard doctype controller.
# extend_doctype_class = {
# 	"Task": "prime_att.custom.task.CustomTaskMixin"
# }

# Overriding Methods
# ------------------------------
#
# override_whitelisted_methods = {
# 	"frappe.desk.doctype.event.event.get_events": "prime_att.event.get_events"
# }
#
# each overriding function accepts a `data` argument;
# generated from the base implementation of the doctype dashboard,
# along with any modifications made in other Frappe apps
# override_doctype_dashboards = {
# 	"Task": "prime_att.task.get_dashboard_data"
# }

# exempt linked doctypes from being automatically cancelled
#
# auto_cancel_exempted_doctypes = ["Auto Repeat"]

# Ignore links to specified DocTypes when deleting documents
# -----------------------------------------------------------

# ignore_links_on_delete = ["Communication", "ToDo"]

# Request Events
# ----------------
# before_request = ["prime_att.utils.before_request"]
# after_request = ["prime_att.utils.after_request"]

# Job Events
# ----------
# before_job = ["prime_att.utils.before_job"]
# after_job = ["prime_att.utils.after_job"]

# User Data Protection
# --------------------

# user_data_fields = [
# 	{
# 		"doctype": "{doctype_1}",
# 		"filter_by": "{filter_by}",
# 		"redact_fields": ["{field_1}", "{field_2}"],
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_2}",
# 		"filter_by": "{filter_by}",
# 		"partial": 1,
# 	},
# 	{
# 		"doctype": "{doctype_3}",
# 		"strict": False,
# 	},
# 	{
# 		"doctype": "{doctype_4}"
# 	}
# ]

# Authentication and authorization
# --------------------------------

# auth_hooks = [
# 	"prime_att.auth.validate"
# ]

# Automatically update python controller files with type annotations for this app.
# export_python_type_annotations = True

# default_log_clearing_doctypes = {
# 	"Logging DocType Name": 30  # days to retain logs
# }

# Translation
# ------------
# List of apps whose translatable strings should be excluded from this app's translations.
# ignore_translatable_strings_from = []

