# 11. PORTAL ACCESS MANAGEMENT & ROLE-BASED ACCESS CONTROL (RBAC)

Carefully inspect my original project PPT / problem statement and determine which user roles require access to which portals, pages, modules and operations.

Implement the portal access system according to the actual project requirements.

Do not give every user access to every portal.

## A. SALESMAN PORTAL

The Salesman should have access to:

- Salesman Dashboard.
- Customer details and customer selection.
- Product catalogue and product availability.
- Create new customer orders.
- Submit orders to Admin for approval.
- View submitted orders.
- Track order status.
- View order history.
- View relevant sales information.

Restrictions:
- Cannot approve or reject orders.
- Cannot modify inventory.
- Cannot manage raw materials.
- Cannot manage production.
- Cannot modify GST configurations.
- Cannot access Admin-only settings.

## B. ADMIN PORTAL

The Admin should have access to:

- Admin Dashboard.
- User and role management.
- Customer management.
- Product management.
- Order verification.
- Approve or reject orders.
- Sales management.
- GST billing and invoice generation.
- PDF invoice downloads.
- Inventory overview.
- Stock management.
- Production overview.
- Dispatch management.
- Payment tracking.
- Business reports.
- GST reports.
- System settings.

The Admin should have the authority to manage the overall system according to the PPT requirements.

## C. PRODUCTION SUPERVISOR PORTAL

The Production Supervisor should have access to:

- Production Dashboard.
- Production order details.
- Approved orders requiring production.
- Raw material availability.
- Raw material management as permitted.
- Bill of Materials (BOM).
- Production planning.
- Production runs.
- Production status updates.
- Production quantity tracking.
- Wastage recording.
- Expected versus actual production.
- Finished goods updates.
- Production history.
- Relevant production reports.

Restrictions:
- Cannot approve sales orders unless explicitly permitted by the PPT.
- Cannot modify GST billing.
- Cannot access Admin-only user management.
- Cannot modify financial records.

## D. REPORTS PORTAL

Implement a Reports Portal with access determined by the PPT.

Include relevant reports such as:

- Sales reports.
- GST reports.
- Production reports.
- Raw material stock reports.
- Finished goods stock reports.
- Wastage reports.
- Production cost per packet.
- Outstanding payment reports.
- Order reports.

Apply role-based restrictions:
- Admin can access overall business reports.
- Production Supervisor can access production and inventory-related reports.
- Salesman can access only relevant sales and order information.
- Other report permissions must follow the original PPT.

## E. ROLE-BASED ACCESS CONTROL

Implement proper authentication and authorization.

Requirements:

1. Assign a role to every registered user.
2. Redirect users to their respective dashboards after login.
3. Display only the navigation options permitted for their role.
4. Restrict unauthorized pages.
5. Restrict unauthorized backend Flask routes.
6. Prevent users from accessing restricted pages by manually entering URLs.
7. Validate permissions on every sensitive operation.
8. Prevent unauthorized database modifications.
9. Maintain user activity and important transaction logs.
10. Allow Admin to manage user roles where specified in the PPT.

Do not rely only on hiding sidebar links. Enforce permissions on the Flask backend as well.

## F. PORTAL ACCESS MATRIX

Create and implement a permission matrix based on the original PPT.

Use this as the initial role mapping and adjust it according to the actual PPT requirements.

| Module | Salesman | Admin | Production Supervisor |
|---|---|---|---|
| Sales Dashboard | Yes | Yes | No |
| Customer Orders | Create/View | Full Access | View Approved Orders |
| Order Approval | No | Yes | No |
| Product Catalogue | View | Full Access | View |
| GST Billing | No | Full Access | No |
| PDF Invoices | View permitted records | Full Access | No |
| Raw Materials | No | Full Access | Manage as permitted |
| BOM | No | Full Access | Manage |
| Production | No | View/Manage | Full Access |
| Inventory | View permitted stock | Full Access | Production Stock |
| Wastage Tracking | No | View | Manage |
| Dispatch | No | Manage | View if required |
| Payments | View permitted status | Full Access | No |
| Business Reports | Limited | Full Access | Limited |
| User Management | No | Yes | No |
| System Settings | No | Yes | No |

## G. PORTAL NAVIGATION

After successful login:

- Salesman → Salesman Dashboard.
- Admin → Admin Dashboard.
- Production Supervisor → Production Dashboard.

Provide a separate Reports Portal or reports section with appropriate permissions.

Ensure each portal has its own relevant sidebar navigation and dashboard information.

## H. PPT VERIFICATION – MANDATORY

Before implementing the access system:

1. Read the original project PPT completely.
2. Identify every user role mentioned.
3. Identify all portals and their purposes.
4. Identify which role performs each activity.
5. Identify which operations require approval.
6. Identify which information each role can view, create, edit or delete.
7. Compare PPT requirements with the existing application.
8. Identify missing portals and permissions.
9. Implement the correct access permissions.
10. Do not invent additional user roles or permissions without justification.

If the existing application has incorrect permissions, correct them according to the PPT.

## I. ACCESS CONTROL TESTING

Test each role independently.

- Log in as Salesman and verify permitted access.
- Log in as Admin and verify full administrative access.
- Log in as Production Supervisor and verify production access.
- Attempt to access restricted URLs manually.
- Attempt unauthorized create, edit and delete operations.
- Verify that restricted operations are rejected.
- Verify that each user is redirected to the correct dashboard.

Provide a role-wise access testing report.

FINAL REQUIREMENT:

Every user must access only the portal and functionalities assigned to their role according to the original project PPT.

Implement role-based access control throughout the entire Flask application, including frontend navigation, backend routes and Firebase operations.