// Copyright (c) 2025, Buunk Business and contributors
// For license information, please see license.txt

frappe.ui.form.on('KVK Settings', {
    refresh: function(frm) {
        // Add test connection button
        frm.add_custom_button(__('Test Connection'), function() {
            if (!frm.doc.api_key) {
                frappe.msgprint(__('Please enter an API key first'));
                return;
            }
            
            frm.call('test_connection')
                .then(r => {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Connection successful'),
                            indicator: 'green'
                        });
                    } else {
                        frappe.show_alert({
                            message: __('Connection failed: ') + (r.message ? r.message.message : 'Unknown error'),
                            indicator: 'red'
                        });
                    }
                });
        });
        
        // Add help information
        frm.set_intro(__('Configure the KVK API integration settings here. You need to obtain an API key from the KVK Developer Portal.'));
    },
    
    enabled: function(frm) {
        // If enabled, make sure API key is provided
        if (frm.doc.enabled && !frm.doc.api_key) {
            frappe.msgprint(__('Please provide an API key to enable the integration'));
            frm.set_value('enabled', 0);
        }
    }
});