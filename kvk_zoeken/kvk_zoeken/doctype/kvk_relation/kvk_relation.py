# Copyright (c) 2025, Buunk Business and contributors
# For license information, please see license.txt

import frappe
from frappe.model.document import Document
from frappe.utils import now_datetime

class KVKRelation(Document):
    def validate(self):
        self.validate_kvk_number()
    
    def validate_kvk_number(self):
        if not self.kvk_number.isdigit() or len(self.kvk_number) != 8:
            frappe.throw("KVK Number must be 8 digits")
    
    def before_save(self):
        self.last_synced = now_datetime()
    
    def after_insert(self):
        # Create relation in the target doctype if auto_create_relations is enabled
        try:
            settings = frappe.get_single("KVK Settings")
            if settings.auto_create_relations and settings.default_relation_type and not self.relation_docname:
                self.create_relation(settings.default_relation_type)
        except frappe.DoesNotExistError:
            # Settings don't exist yet, skip auto-creation
            frappe.log_error("KVK Settings not found, skipping auto-creation of relation", "KVK Relation")
    
    def create_relation(self, relation_type):
        """Create a relation in the target doctype"""
        if not relation_type or relation_type == "None":
            return
        
        try:
            # Get the relation doctype from settings
            try:
                settings = frappe.get_single("KVK Settings")
                relation_doctype = settings.relation_doctype or "Relation"
            except frappe.DoesNotExistError:
                relation_doctype = "Relation"  # Default if settings don't exist
            
            # Check if the relation doctype exists
            if not frappe.db.exists("DocType", relation_doctype):
                frappe.log_error(f"DocType {relation_doctype} does not exist", "KVK Relation Error")
                return
            
            # Create the relation
            relation = frappe.new_doc(relation_doctype)
            
            # Map fields based on the target doctype
            if relation_doctype == "Relation":
                relation.relation_name = self.company_name
                relation.kvk_number = self.kvk_number
                relation.relation_type = "Company"
                
                # Address fields
                if self.street and self.house_number:
                    relation.address_line1 = f"{self.street} {self.house_number}"
                    if self.house_letter:
                        relation.address_line1 += self.house_letter
                
                relation.postal_code = self.postal_code
                relation.city = self.city
                relation.country = self.country
                relation.is_active = self.status == "Active"
            
            # Insert the relation
            relation.insert()
            
            # Update the relation_docname field
            self.relation_docname = relation.name
            self.relation_type = relation_type
            self.db_update()
            
            frappe.msgprint(f"Relation {relation.name} created successfully")
            
        except Exception as e:
            frappe.log_error(f"Error creating relation: {str(e)}", "KVK Relation Error")