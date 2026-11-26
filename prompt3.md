# UPDATE: NEW ORDER MUST BE CREATED BY THE LOGGED-IN USER

Modify the existing New Order functionality with the following requirements.

**1. User-created orders**
- The New Order page must be accessible to authorized logged-in users, especially Salesmen.
- The user must create and submit their own orders.
- Automatically identify the currently logged-in user.
- Record the user's ID, name and role with the order.
- Do not require Admin to create an order on behalf of the user.

**2. Order creation form**

The user should be able to:
- Select an existing customer.
- Add customer details.
- Select one or multiple products.
- Enter product quantities.
- View available stock.
- Enter applicable discounts.
- View automatic GST calculations.
- View the final order amount.
- Add order notes.
- Select an expected delivery date.

**3. Order submission**

When the user clicks Submit Order:
- Validate all entered information.
- Generate a unique Order ID.
- Save the order in Firebase Firestore.
- Set status to Pending Approval.
- Record the logged-in user's information.
- Display a successful submission message.
- Automatically show the submitted order in My Orders.

**4. Admin approval**

- Admin must not create the user's order.
- Admin receives the submitted order in Order Management.
- Admin can review, approve or reject it.
- Admin must provide a reason when rejecting an order.

**5. My Orders**

The logged-in user should see only their own orders.

Display:
- Order ID.
- Customer name.
- Order date.
- Products.
- Quantity.
- Total amount.
- Approval status.
- Production status.
- Delivery status.

Allow users to view order details and track progress.

**6. Security**

- Associate every order with its creator's user ID.
- Prevent users from viewing or modifying another user's orders.
- Enforce permissions in Flask backend routes.
- Only Admin can approve or reject orders.
- Do not allow users to modify orders after approval unless the existing workflow explicitly permits it.

**7. Important restrictions**

- Use the existing New Order menu item.
- Do not create another New Order page or sidebar item.
- Do not change the existing UI design.
- Preserve existing Firebase collections and business logic.
- Integrate with existing My Orders and Order Management pages.

Test the complete workflow using separate Salesman and Admin accounts.