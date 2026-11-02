// Copyright (c) 2026, Prime Tech BD and contributors
// For license information, please see license.txt

frappe.ui.form.on("ZK Device Command", {
	refresh(frm) {
		// Friendly indicator badge
		if (frm.doc.status === "Pending") {
			frm.dashboard.add_indicator(__("Waiting for Device / অপেক্ষমান"), "orange");
		} else if (frm.doc.status === "Sent") {
			frm.dashboard.add_indicator(__("Device Processing / মেশিনে পাঠানো হয়েছে"), "blue");
		} else if (frm.doc.status === "Done") {
			frm.dashboard.add_indicator(__("Completed Successfully / সফল"), "green");
		} else if (frm.doc.status === "Failed") {
			frm.dashboard.add_indicator(__("Failed / ব্যর্থ"), "red");
		}
	}
});
