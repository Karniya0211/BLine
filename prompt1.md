# PHASE 3: PRODUCTION & INVENTORY MANAGEMENT

Develop Phase 3 of my existing Billing and Management System project.

The project currently uses:
- Frontend: HTML, CSS, Bootstrap (existing design)
- Backend: Python Flask
- Database: Firebase Firestore
- Authentication: Existing authentication system
- Execution: Localhost

IMPORTANT: This is an extension of my existing project. Do not create a new project or rebuild the application.

## 1. PRODUCTION MANAGEMENT

Implement a complete production management module.

Features:

- Add new production orders.
- Select products for production.
- Enter production quantity.
- Set production start date and expected completion date.
- Track production status:
  - Pending
  - In Progress
  - Completed
  - Cancelled
- Update production progress.
- Record actual production quantity.
- Maintain production history.
- View individual production details.
- Edit and delete production records where appropriate.

## 2. RAW MATERIAL MANAGEMENT

Implement raw material tracking.

Features:

- Add raw materials.
- Store material name, ID, unit, quantity and price.
- Update raw material details.
- Track available raw material stock.
- Record incoming materials.
- Record material consumption during production.
- Maintain raw material transaction history.
- Display low-stock notifications.

## 3. INVENTORY MANAGEMENT

Develop a complete inventory management system.

Features:

- Manage raw materials and finished products.
- Display available stock quantities.
- Automatically update stock when production is completed.
- Deduct raw materials based on production consumption.
- Track stock additions and reductions.
- Maintain inventory transaction history.
- Display low-stock alerts.
- Provide stock search and filtering.
- Prevent negative inventory quantities.

## 4. BILL OF MATERIALS (BOM)

Implement a Bill of Materials system.

Features:

- Create a BOM for each finished product.
- Define the raw materials required to manufacture one unit.
- Specify the quantity of each raw material required.
- Calculate total raw material requirements based on production quantity.
- Check raw material availability before production.
- Deduct consumed materials when production is completed.

Example:

Product: Biscuit Box

| Raw Material | Required per unit |
|---|---:|
| Flour | 0.5 kg |
| Sugar | 0.2 kg |
| Butter | 0.1 kg |
| Packaging | 1 unit |

For 100 biscuit boxes, calculate the total required materials automatically.

## 5. PRODUCTION WORKFLOW

Implement this workflow:

1. Admin creates a production order.
2. Selects the finished product.
3. Enters the required production quantity.
4. System checks the raw material availability.
5. System calculates the required materials using BOM.
6. Production begins.
7. Staff updates production progress.
8. Production is marked as completed.
9. Raw material stock is deducted.
10. Finished goods stock is increased.
11. Inventory records are updated automatically.

## 6. DASHBOARD INTEGRATION

Integrate Phase 3 information into the existing dashboard without changing its current design.

Display:
- Total production orders.
- Pending production orders.
- Completed production orders.
- Total raw material stock.
- Total finished goods stock.
- Low-stock materials.
- Recent production activities.

Use the existing dashboard components and styling.

## 7. FIREBASE FIRESTORE INTEGRATION

Use the existing Firebase Firestore connection.

Create the necessary collections only if they do not already exist:

- production_orders
- raw_materials
- bill_of_materials
- inventory_transactions

Preserve existing collections, documents and field names.

Implement proper database validation and error handling.

Use safe stock update operations to prevent incorrect inventory calculations.

## 8. UI REQUIREMENTS – VERY IMPORTANT

Do not redesign the existing application.

- Maintain the original UI.
- Preserve the existing color scheme.
- Preserve fonts, buttons, forms and tables.
- Preserve the sidebar and navigation.
- Follow the existing page layout.
- Reuse existing CSS and components.
- Add Phase 3 pages using the same design language.
- Do not modify Phase 1 and Phase 2 pages.

## 9. TECHNICAL REQUIREMENTS

- Use Python Flask for backend operations.
- Use existing HTML and CSS for frontend.
- Use the existing Firebase configuration.
- Do not introduce Streamlit.
- Do not create unnecessary JavaScript.
- Do not duplicate existing functionality.
- Maintain the existing project folder structure.
- Write clean and reusable Python code.

## 10. TESTING

Test the following:

- Creating production orders.
- Updating production status.
- Creating and editing raw materials.
- Creating BOM records.
- Calculating raw material requirements.
- Checking material availability.
- Deducting raw materials after production.
- Increasing finished goods stock.
- Maintaining inventory transaction history.
- Displaying low-stock alerts.
- Ensuring Phase 1 and Phase 2 continue working.

## FINAL INSTRUCTION

Implement Phase 3 directly inside my existing Billing Management System.

Do not change existing UI, Phase 1 functionality, Phase 2 functionality, authentication, database structure or business logic unnecessarily.

Only add the required Production and Inventory Management features.

The application must continue running locally using:

python app.py

URL: http://127.0.0.1:5000

Provide the complete updated code for every newly created or modified file and explain the changes made.