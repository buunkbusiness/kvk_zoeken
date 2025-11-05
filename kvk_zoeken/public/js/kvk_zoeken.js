// KVK Zoeken client-side JavaScript

frappe.provide("kvk_zoeken");

kvk_zoeken.search = function(options) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'kvk_zoeken.api.search_kvk',
            args: options,
            callback: function(r) {
                if (r.message) {
                    resolve(r.message);
                } else {
                    reject(r.exc || "Unknown error");
                }
            }
        });
    });
};

kvk_zoeken.get_complete_data = function(kvk_nummer, geo_data = false) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'kvk_zoeken.api.get_complete_company_data',
            args: {
                kvk_nummer: kvk_nummer,
                geo_data: geo_data
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    resolve(r.message);
                } else {
                    reject(r.exc || (r.message ? r.message.error : "Unknown error"));
                }
            }
        });
    });
};

kvk_zoeken.get_basisprofiel = function(kvk_nummer, geo_data = false) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'kvk_zoeken.api.get_kvk_basisprofiel',
            args: {
                kvk_nummer: kvk_nummer,
                geo_data: geo_data
            },
            callback: function(r) {
                if (r.message && !r.message.error) {
                    resolve(r.message);
                } else {
                    reject(r.exc || (r.message ? r.message.error : "Unknown error"));
                }
            }
        });
    });
};

kvk_zoeken.create_relation = function(kvk_nummer) {
    return new Promise((resolve, reject) => {
        frappe.call({
            method: 'kvk_zoeken.api.create_relation_from_kvk',
            args: {
                kvk_nummer: kvk_nummer
            },
            callback: function(r) {
                if (r.message && r.message.success) {
                    resolve(r.message);
                } else {
                    reject(r.exc || (r.message ? r.message.error : "Unknown error"));
                }
            }
        });
    });
};

// Add KVK search button to Relation form
frappe.ui.form.on('Relation', {
    refresh: function(frm) {
        if (frm.doc.__islocal) {
            frm.add_custom_button(__('Search KVK'), function() {
                // Create a dialog for KVK search
                let d = new frappe.ui.Dialog({
                    title: __('Search KVK'),
                    fields: [
                        {
                            label: __('Search Term'),
                            fieldname: 'search_term',
                            fieldtype: 'Data',
                            description: __('Enter KVK number, company name, or postcode')
                        }
                    ],
                    primary_action_label: __('Search'),
                    primary_action: function(values) {
                        if (!values.search_term) {
                            frappe.msgprint(__('Please enter a search term'));
                            return;
                        }
                        
                        // Show loading indicator
                        d.set_message(__('Searching...'));
                        
                        // Call the search API
                        kvk_zoeken.search({
                            search_term: values.search_term
                        }).then(result => {
                            d.clear_message();
                            
                            if (!result.resultaten || result.resultaten.length === 0) {
                                d.set_message(__('No results found'));
                                return;
                            }
                            
                            // Create a field for displaying results
                            d.fields_dict.results_html = d.fields_dict.results_html || {};
                            
                            // Generate HTML for results with enhanced information
                            let html = '<div class="results-container">';
                            html += '<table class="table table-bordered">';
                            html += '<thead><tr><th>KVK Number</th><th>Name</th><th>Type</th><th>City</th><th>Status</th><th>Action</th></tr></thead>';
                            html += '<tbody>';
                            
                            result.resultaten.forEach(item => {
                                html += '<tr>';
                                html += `<td>${item.kvkNummer}</td>`;
                                html += `<td>${item.naam}</td>`;
                                html += `<td>${item.type || '-'}</td>`;
                                html += `<td>${item.adres && item.adres.plaats ? item.adres.plaats : '-'}</td>`;
                                html += `<td><span class="indicator ${item.actief === 'Ja' ? 'green' : 'red'}">${item.actief === 'Ja' ? 'Active' : 'Inactive'}</span></td>`;
                                html += `<td>`;
                                html += `<button class="btn btn-xs btn-primary select-company" data-kvk="${item.kvkNummer}" style="margin-right: 5px;">Quick Select</button>`;
                                html += `<button class="btn btn-xs btn-info get-full-details" data-kvk="${item.kvkNummer}">Full Details</button>`;
                                html += `</td>`;
                                html += '</tr>';
                            });
                            
                            html += '</tbody></table></div>';
                            
                            // Add the results to the dialog
                            $(d.body).find('.results-container').remove();
                            $(d.body).append(html);
                            
                            // Add click handler for quick select buttons
                            $(d.body).find('.select-company').on('click', function() {
                                const kvkNummer = $(this).data('kvk');
                                const company = result.resultaten.find(item => item.kvkNummer === kvkNummer);
                                
                                if (company) {
                                    kvk_zoeken.fill_form_with_basic_data(frm, company);
                                    d.hide();
                                }
                            });
                            
                            // Add click handler for full details buttons
                            $(d.body).find('.get-full-details').on('click', function() {
                                const kvkNummer = $(this).data('kvk');
                                const $btn = $(this);
                                
                                $btn.prop('disabled', true).text('Loading...');
                                
                                // Get complete company data
                                kvk_zoeken.get_complete_data(kvkNummer, true).then(completeData => {
                                    $btn.prop('disabled', false).text('Full Details');
                                    
                                    if (completeData.success && completeData.processed_data) {
                                        kvk_zoeken.show_company_details_dialog(completeData, frm);
                                        d.hide();
                                    } else {
                                        frappe.msgprint(__('Could not fetch complete company details: ') + (completeData.error || 'Unknown error'));
                                    }
                                }).catch(error => {
                                    $btn.prop('disabled', false).text('Full Details');
                                    frappe.msgprint(__('Error fetching company details: ') + error);
                                });
                            });
                        }).catch(error => {
                            d.clear_message();
                            d.set_message(__('Error: ') + error);
                        });
                    }
                });
                
                d.show();
            });
        }
    }
});

// Helper function to fill form with basic company data from search results
kvk_zoeken.fill_form_with_basic_data = function(frm, company) {
    frm.set_value('relation_name', company.naam);
    frm.set_value('kvk_number', company.kvkNummer);
    
    if (company.rsin) {
        frm.set_value('rsin_number', company.rsin);
    }
    
    if (company.vestigingsnummer) {
        frm.set_value('establishment_number', company.vestigingsnummer);
    }
    
    if (company.adres) {
        if (company.adres.straatnaam && company.adres.huisnummer) {
            frm.set_value('address_line1', `${company.adres.straatnaam} ${company.adres.huisnummer}${company.adres.huisletter || ''}`);
        } else if (company.adres.straatHuisnummer) {
            frm.set_value('address_line1', company.adres.straatHuisnummer);
        }
        
        frm.set_value('postal_code', company.adres.postcode || '');
        frm.set_value('city', company.adres.plaats || company.adres.postcodeWoonplaats || '');
        frm.set_value('country', company.adres.land || 'Netherlands');
    }
};

// Helper function to show comprehensive company details dialog
kvk_zoeken.show_company_details_dialog = function(completeData, frm) {
    const data = completeData.processed_data;
    const basicInfo = data.basic_info || {};
    
    let html = '<div class="company-details" style="max-height: 500px; overflow-y: auto;">';
    
    // Basic Information Section
    html += '<div class="section">';
    html += '<h4>Basic Information</h4>';
    html += '<table class="table table-condensed">';
    html += `<tr><td><strong>Company Name:</strong></td><td>${basicInfo.company_name || '-'}</td></tr>`;
    html += `<tr><td><strong>KVK Number:</strong></td><td>${basicInfo.kvk_number || '-'}</td></tr>`;
    html += `<tr><td><strong>RSIN:</strong></td><td>${basicInfo.rsin || '-'}</td></tr>`;
    html += `<tr><td><strong>Statutory Name:</strong></td><td>${basicInfo.statutory_name || '-'}</td></tr>`;
    html += `<tr><td><strong>Registration Date:</strong></td><td>${basicInfo.registration_date || '-'}</td></tr>`;
    html += `<tr><td><strong>Company Type:</strong></td><td>${basicInfo.company_type || '-'}</td></tr>`;
    html += '</table>';
    html += '</div>';
    
    // Trade Names Section
    if (basicInfo.trade_names && basicInfo.trade_names.length > 0) {
        html += '<div class="section">';
        html += '<h4>Trade Names</h4>';
        html += '<ul>';
        basicInfo.trade_names.forEach(name => {
            html += `<li>${name}</li>`;
        });
        html += '</ul>';
        html += '</div>';
    }
    
    // Addresses Section
    if (data.addresses && data.addresses.length > 0) {
        html += '<div class="section">';
        html += '<h4>Addresses</h4>';
        data.addresses.forEach((addr, index) => {
            html += `<div class="address-item" style="margin-bottom: 10px; padding: 10px; border: 1px solid #ddd;">`;
            html += `<strong>Address ${index + 1} (${addr.type || 'Unknown Type'})</strong><br>`;
            html += `${addr.full_address || 'No address available'}`;
            if (addr.is_protected) {
                html += '<br><span class="text-muted"><i>Protected Address</i></span>';
            }
            html += '</div>';
        });
        html += '</div>';
    }
    
    // SBI Activities Section
    if (data.sbi_activities && data.sbi_activities.length > 0) {
        html += '<div class="section">';
        html += '<h4>SBI Activities</h4>';
        html += '<table class="table table-condensed table-striped">';
        html += '<thead><tr><th>SBI Code</th><th>Description</th><th>Main Activity</th></tr></thead>';
        html += '<tbody>';
        data.sbi_activities.forEach(sbi => {
            html += '<tr>';
            html += `<td>${sbi.sbi_code}</td>`;
            html += `<td>${sbi.description}</td>`;
            html += `<td>${sbi.is_main_activity ? '<span class="indicator green">Yes</span>' : 'No'}</td>`;
            html += '</tr>';
        });
        html += '</tbody></table>';
        html += '</div>';
    }
    
    // Main Establishment Section
    if (data.main_establishment) {
        const mainEst = data.main_establishment;
        html += '<div class="section">';
        html += '<h4>Main Establishment</h4>';
        html += '<table class="table table-condensed">';
        html += `<tr><td><strong>Establishment Number:</strong></td><td>${mainEst.establishment_number || '-'}</td></tr>`;
        html += `<tr><td><strong>First Trade Name:</strong></td><td>${mainEst.first_trade_name || '-'}</td></tr>`;
        html += `<tr><td><strong>Total Employees:</strong></td><td>${mainEst.total_employees || 0}</td></tr>`;
        html += `<tr><td><strong>Full-time Employees:</strong></td><td>${mainEst.full_time_employees || 0}</td></tr>`;
        html += `<tr><td><strong>Part-time Employees:</strong></td><td>${mainEst.part_time_employees || 0}</td></tr>`;
        html += '</table>';
        
        if (mainEst.websites && mainEst.websites.length > 0) {
            html += '<p><strong>Websites:</strong></p><ul>';
            mainEst.websites.forEach(website => {
                html += `<li><a href="${website}" target="_blank">${website}</a></li>`;
            });
            html += '</ul>';
        }
        html += '</div>';
    }
    
    // Establishments Summary
    if (data.establishments_summary) {
        const estSum = data.establishments_summary;
        html += '<div class="section">';
        html += '<h4>Establishments Summary</h4>';
        html += '<table class="table table-condensed">';
        html += `<tr><td><strong>Total Establishments:</strong></td><td>${estSum.total_establishments || 0}</td></tr>`;
        html += `<tr><td><strong>Commercial:</strong></td><td>${estSum.commercial_establishments || 0}</td></tr>`;
        html += `<tr><td><strong>Non-Commercial:</strong></td><td>${estSum.non_commercial_establishments || 0}</td></tr>`;
        html += '</table>';
        html += '</div>';
    }
    
    html += '</div>';
    
    // Create dialog to show company details
    let detailsDialog = new frappe.ui.Dialog({
        title: __('Complete Company Details - ') + basicInfo.company_name,
        size: 'large',
        fields: [
            {
                fieldtype: 'HTML',
                fieldname: 'company_details',
                options: html
            }
        ],
        primary_action_label: __('Use This Data'),
        primary_action: function() {
            kvk_zoeken.fill_form_with_complete_data(frm, data);
            detailsDialog.hide();
        },
        secondary_action_label: __('Close')
    });
    
    detailsDialog.show();
};

// Helper function to fill form with complete company data
kvk_zoeken.fill_form_with_complete_data = function(frm, data) {
    const basicInfo = data.basic_info || {};
    
    // Basic information
    if (basicInfo.company_name) frm.set_value('relation_name', basicInfo.company_name);
    if (basicInfo.kvk_number) frm.set_value('kvk_number', basicInfo.kvk_number);
    if (basicInfo.rsin) frm.set_value('rsin_number', basicInfo.rsin);
    if (basicInfo.establishment_number) frm.set_value('establishment_number', basicInfo.establishment_number);
    
    // Use the first address if available
    if (data.addresses && data.addresses.length > 0) {
        const addr = data.addresses[0];
        
        let address_line1 = '';
        if (addr.street_name) {
            address_line1 = addr.street_name;
            if (addr.house_number) {
                address_line1 += ` ${addr.house_number}`;
                if (addr.house_letter) address_line1 += addr.house_letter;
                if (addr.house_number_addition) address_line1 += ` ${addr.house_number_addition}`;
            }
        }
        
        if (address_line1) frm.set_value('address_line1', address_line1);
        if (addr.postal_code) frm.set_value('postal_code', addr.postal_code);
        if (addr.city) frm.set_value('city', addr.city);
        if (addr.country) frm.set_value('country', addr.country);
    }
    
    frappe.show_alert({
        message: __('Company data has been filled in the form'),
        indicator: 'green'
    });
};