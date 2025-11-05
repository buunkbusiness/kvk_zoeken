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
            
            // Show loading message
            frappe.show_alert({
                message: __('Testing connection...'),
                indicator: 'blue'
            });
            
            frm.call('test_connection')
                .then(r => {
                    if (r.message) {
                        const result = r.message;
                        
                        if (result.overall_success || (result.search_api && result.search_api.success) || (result.basisprofiel_api && result.basisprofiel_api.success)) {
                            // Show detailed success results
                            let message = '<div>';
                            message += '<h4>Connection Test Results</h4>';
                            
                            if (result.search_api) {
                                const searchIcon = result.search_api.success ? '✅' : '❌';
                                message += `<p>${searchIcon} <strong>Search API:</strong> ${result.search_api.message}</p>`;
                            }
                            
                            if (result.basisprofiel_api) {
                                const basisprofielIcon = result.basisprofiel_api.success ? '✅' : '❌';
                                message += `<p>${basisprofielIcon} <strong>Basisprofiel API:</strong> ${result.basisprofiel_api.message}</p>`;
                            }
                            
                            if (result.overall_success) {
                                message += '<p><strong>Status:</strong> <span style="color: green;">KVK integration is working correctly!</span></p>';
                            } else if ((result.search_api && result.search_api.success) || (result.basisprofiel_api && result.basisprofiel_api.success)) {
                                message += '<p><strong>Status:</strong> <span style="color: orange;">Partial functionality available.</span></p>';
                            }
                            
                            message += '</div>';
                            
                            frappe.msgprint({
                                title: __('Connection Test Results'),
                                message: message,
                                indicator: result.overall_success ? 'green' : 'orange'
                            });
                        } else {
                            // Show error results
                            let errorMessage = '<div>';
                            errorMessage += '<h4>Connection Test Failed</h4>';
                            
                            if (result.search_api) {
                                errorMessage += `<p>❌ <strong>Search API:</strong> ${result.search_api.message}</p>`;
                            }
                            
                            if (result.basisprofiel_api) {
                                errorMessage += `<p>❌ <strong>Basisprofiel API:</strong> ${result.basisprofiel_api.message}</p>`;
                            }
                            
                            errorMessage += '<p><strong>Please check your API key and try again.</strong></p>';
                            errorMessage += '</div>';
                            
                            frappe.msgprint({
                                title: __('Connection Test Failed'),
                                message: errorMessage,
                                indicator: 'red'
                            });
                        }
                    } else {
                        frappe.show_alert({
                            message: __('Connection test failed: Unknown error'),
                            indicator: 'red'
                        });
                    }
                })
                .catch(error => {
                    frappe.show_alert({
                        message: __('Connection test failed: ') + (error.message || 'Unknown error'),
                        indicator: 'red'
                    });
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