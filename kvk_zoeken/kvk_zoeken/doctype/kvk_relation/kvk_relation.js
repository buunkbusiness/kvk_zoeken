// Copyright (c) 2025, Buunk Business and contributors
// For license information, please see license.txt

frappe.ui.form.on('KVK Relation', {
    refresh: function(frm) {
        // Add button to sync with KVK API
        frm.add_custom_button(__('Sync with KVK'), function() {
            frappe.call({
                method: 'kvk_zoeken.api.sync_kvk_relation',
                args: {
                    kvk_number: frm.doc.kvk_number
                },
                callback: function(r) {
                    if (r.message && r.message.success) {
                        frappe.show_alert({
                            message: __('Synced successfully'),
                            indicator: 'green'
                        });
                        frm.refresh();
                    } else {
                        frappe.show_alert({
                            message: __('Sync failed: ') + (r.message ? r.message.message : 'Unknown error'),
                            indicator: 'red'
                        });
                    }
                }
            });
        });
        
        // Add button to create relation if not already created
        if (!frm.doc.relation_docname) {
            frm.add_custom_button(__('Create Relation'), function() {
                let d = new frappe.ui.Dialog({
                    title: __('Create Relation'),
                    fields: [
                        {
                            label: __('Relation Type'),
                            fieldname: 'relation_type',
                            fieldtype: 'Select',
                            options: 'Customer\nSupplier\nLead\nProspect',
                            reqd: 1
                        }
                    ],
                    primary_action_label: __('Create'),
                    primary_action: function(values) {
                        frappe.call({
                            method: 'kvk_zoeken.kvk_zoeken.doctype.kvk_relation.kvk_relation.create_relation',
                            args: {
                                kvk_relation: frm.doc.name,
                                relation_type: values.relation_type
                            },
                            callback: function(r) {
                                if (r.message && r.message.success) {
                                    frappe.show_alert({
                                        message: __('Relation created successfully'),
                                        indicator: 'green'
                                    });
                                    frm.refresh();
                                } else {
                                    frappe.show_alert({
                                        message: __('Failed to create relation: ') + 
                                            (r.message ? r.message.message : 'Unknown error'),
                                        indicator: 'red'
                                    });
                                }
                                d.hide();
                            }
                        });
                    }
                });
                d.show();
            });
        }
    }
});