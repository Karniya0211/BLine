# FactoryFlow – Complete Portal Updates & Improvements

Update the existing FactoryFlow project with the following changes without redesigning the UI or affecting unrelated features.

### 1. Owner Portal (`owner@factoryflow.com`)
- Remove Inventory Management, My Orders, Dispatch Management, User Management, and System Settings.

### 2. Admin Portal (`admin@factoryflow.com`)
- Remove Bill of Materials, Inventory Management, My Orders, and Financial Management.

### 3. Sales Portal (`sales@factoryflow.com`)
- Remove Customer Master and System Settings.

### 4. Supervisor Portal (`supervisor@factoryflow.com`)
- Remove System Settings.
- Ensure Inventory Management and Bill of Materials are fully functional.

### 5. Auditor Portal (`auditor@factoryflow.com`)
- Remove Inventory Management, Product Master, Customer Master, Supplier Master, Raw Material Master, and System Settings.
- Enable GST Billing for the Auditor.
- Ensure Financial Management works correctly.

### 6. Customer Dropdown Synchronization
- In GST Billing, display all existing customers in the customer dropdown.
- Automatically update customer dropdowns across all relevant portals whenever a new customer is created.
- In Dispatch Management, ensure the Target Invoice dropdown displays all updated customer and invoice records.

### 7. Dashboard Corrections
- Remove duplicate values from all portal dashboards.
- Display only accurate, existing database records.
- Ensure dashboard figures are dynamically updated and synchronized.

### 8. Legal Pages
- Combine Terms of Service and Privacy Policy into a single unified page across all portals.

### 9. Password Reset
- Implement email-based OTP/code delivery on the FactoryFlow login page.
- Ensure the verification code is sent to the registered email address.
- Allow users to securely recover/reset their passwords after verification.

### 10. Create Employee Account – First Page
Add a **Create Employee Account** section to the first page of FactoryFlow with these fields:

- Full Name
- Email Address
- Phone Number
- Assign Role (dropdown containing available employee roles)

Requirements:
- Allow the Owner/Admin to create employee accounts.
- Save employee details in the database.
- Automatically assign the correct role and portal permissions.
- Integrate with the existing authentication system.
- Ensure newly created accounts can log in to their assigned portals.

### Final Requirements
- Preserve the existing UI design, layout, and styling.
- Maintain the existing database structure wherever possible.
- Implement proper role-based access control.
- Ensure all dropdowns and dashboards use live database records.
- Do not break existing features or workflows.
- Remove only the specifically mentioned modules.
- Test every modified feature, portal, authentication flow, and database synchronization.
- Fix all errors before considering the update complete.

**Important:** Do not create duplicate modules, records, accounts, or database collections. Make all requested changes functional, not just visual.