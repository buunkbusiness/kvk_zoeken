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
                            
                            // Generate HTML for results
                            let html = '<div class="results-container">';
                            html += '<table class="table table-bordered">';
                            html += '<thead><tr><th>KVK Number</th><th>Name</th><th>City</th><th>Action</th></tr></thead>';
                            html += '<tbody>';
                            
                            result.resultaten.forEach(item => {
                                html += '<tr>';
                                html += `<td>${item.kvkNummer}</td>`;
                                html += `<td>${item.naam}</td>`;
                                html += `<td>${item.adres && item.adres.plaats ? item.adres.plaats : '-'}</td>`;
                                html += `<td><button class="btn btn-xs btn-primary select-company" data-kvk="${item.kvkNummer}">Select</button></td>`;
                                html += '</tr>';
                            });
                            
                            html += '</tbody></table></div>';
                            
                            // Add the results to the dialog
                            $(d.body).find('.results-container').remove();
                            $(d.body).append(html);
                            
                            // Add click handler for select buttons
                            $(d.body).find('.select-company').on('click', function() {
                                const kvkNummer = $(this).data('kvk');
                                const company = result.resultaten.find(item => item.kvkNummer === kvkNummer);
                                
                                if (company) {
                                    // Fill the form with company data
                                    frm.set_value('relation_name', company.naam);
                                    frm.set_value('kvk_number', company.kvkNummer);
                                    
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
                                    
                                    d.hide();
                                }
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