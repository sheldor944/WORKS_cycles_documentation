# PurchaseOrderHeader

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores purchase order headers — one row per purchase order (4,012 POs). It captures who approved/placed the order (EmployeeID → Employee), which supplier it was placed with (VendorID → Vendor), how it's being shipped (ShipMethodID → ShipMethod), key dates (OrderDate, ShipDate), order status (Status 1–4), and financial totals (SubTotal, TaxAmt, Freight, TotalDue). This is the procurement counterpart to SalesOrderHeader — tracking money going out to vendors rather than coming in from customers.

### Style 2: Query Possibilities & Business Story
This is the main procurement table — every purchase order placed with a vendor starts here. It's the buying side of the business, where the company orders raw materials, components, and supplies from external vendors. Use this table to answer questions like:

- "How much did we spend on vendor purchases last quarter?"
- "Which vendor receives the most purchase orders?"
- "Which employee approves the highest value of POs?"
- "What's the average time between order date and ship date for POs?"
- "How many POs are still pending vs. approved vs. completed?"
- "What's the freight cost as a percentage of total procurement spend?"
- "Which shipping method is used most for vendor orders?"
- "How does monthly procurement spend trend over time?"
- "Which vendors have the most unshipped/delayed orders?"
- "What's the average PO value by vendor or by approving employee?"
- "How does procurement spending compare to sales revenue?" (with SalesOrderHeader)
- "What products are we buying and from whom?" (with PurchaseOrderDetail, Product)

Each PO connects to the employee who placed it, the vendor supplying goods, and the shipping method. Line-item details (products, quantities, prices) live in PurchaseOrderDetail.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per purchase order (4,012 rows), containing 13 columns organized as:

- **Identifiers:** PurchaseOrderID (PK, auto-increment)
- **Dates:** OrderDate, ShipDate, ModifiedDate
- **Status/Versioning:** Status (1=Pending, 2=Approved, 3=Rejected, 4=Complete), RevisionNumber
- **People & Vendor:** EmployeeID (FK → Employee, the approver), VendorID (FK → Vendor, the supplier)
- **Shipping:** ShipMethodID (FK → ShipMethod)
- **Financials:** SubTotal, TaxAmt, Freight, TotalDue (= SubTotal + TaxAmt + Freight)

---

## 📖 Extensive Description

### Purpose & Business Context

PurchaseOrderHeader is the backbone of the procurement/purchasing system — 4,012 purchase orders placed with external vendors. While SalesOrderHeader tracks revenue coming in, PurchaseOrderHeader tracks costs going out. Together they complete the buy-sell cycle: the company buys raw materials/components from vendors (PurchaseOrder), manufactures or assembles products (WorkOrder), and sells finished goods to customers (SalesOrder).

Every PO is placed by an employee (the buyer/approver), directed at a specific vendor, and shipped via a chosen method. The financial columns mirror SalesOrderHeader's structure (SubTotal + TaxAmt + Freight = TotalDue), enabling direct comparisons between procurement costs and sales revenue.

### Key Business Logic

- **Status** maps to: 1 = Pending, 2 = Approved, 3 = Rejected, 4 = Complete
- **RevisionNumber** tracks how many times the PO was modified after creation
- **ShipDate IS NULL** → order hasn't shipped yet from the vendor
- **TotalDue = SubTotal + TaxAmt + Freight** — total cost owed to the vendor
- **EmployeeID** is the employee who created/approved the PO — not necessarily the same as a salesperson
- A single PO can have multiple line items in PurchaseOrderDetail (different products, quantities)
- Vendors are also BusinessEntities — so they share the same address/contact infrastructure as people and stores

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| ↓ Child | PurchaseOrderDetail (8,845) | PurchaseOrderID | Line items — products, qty, price, received/rejected/stocked |
| → Parent | Employee → Person → BusinessEntity | EmployeeID | Who approved/placed the PO |
| → Parent | Vendor → BusinessEntity | VendorID | Supplier the PO is placed with |
| → Parent | ShipMethod | ShipMethodID | How goods are shipped from vendor |
| Related | ProductVendor | VendorID + ProductID | Vendor-product catalog (pricing, lead times) |
| Comparison | SalesOrderHeader | — | Revenue vs. procurement cost analysis |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each purchase order, show the PO ID, order date, approving employee's full name and job title, vendor name and credit rating, ship method, and total due."**

*6 joins: PurchaseOrderHeader → Employee → Person → Vendor → ShipMethod*

```sql
SELECT
    poh.PurchaseOrderID,
    poh.OrderDate,
    poh.Status,
    p.FirstName || ' ' || p.LastName AS ApproverName,
    e.JobTitle AS ApproverTitle,
    v.Name AS VendorName,
    v.CreditRating,
    sm.Name AS ShipMethod,
    ROUND(poh.TotalDue, 2) AS TotalDue
FROM PurchaseOrderHeader poh
JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID
ORDER BY poh.OrderDate DESC;
```

---

**Q2: "Show each purchase order's line items with product name, product category, vendor name, vendor's city/state, and the employee's department who approved it."**

*11 joins: PurchaseOrderHeader → PurchaseOrderDetail → Product → ProductSubcategory → ProductCategory → Vendor → BusinessEntityAddress → Address → StateProvince → Employee → EmployeeDepartmentHistory → Department*

```sql
SELECT
    poh.PurchaseOrderID,
    poh.OrderDate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    pod.OrderQty,
    ROUND(pod.LineTotal, 2) AS LineTotal,
    v.Name AS VendorName,
    a.City AS VendorCity,
    sp.Name AS VendorState,
    d.Name AS ApproverDepartment
FROM PurchaseOrderHeader poh
JOIN PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
JOIN Product p ON pod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN BusinessEntityAddress bea ON v.BusinessEntityID = bea.BusinessEntityID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
ORDER BY poh.PurchaseOrderID, pod.PurchaseOrderDetailID;
```

---

**Q3: "For each PO, show the vendor name, products ordered, whether those products are also sold to customers, and if so the total sales revenue generated — comparing purchase cost vs. sales revenue per product."**

*8 joins: PurchaseOrderHeader → PurchaseOrderDetail → Product → Vendor → SalesOrderDetail → SalesOrderHeader*

```sql
SELECT
    v.Name AS VendorName,
    p.Name AS ProductName,
    SUM(pod.OrderQty) AS TotalQtyPurchased,
    ROUND(SUM(pod.LineTotal), 2) AS TotalPurchaseCost,
    COALESCE(sales.TotalQtySold, 0) AS TotalQtySold,
    COALESCE(sales.TotalSalesRevenue, 0) AS TotalSalesRevenue,
    ROUND(COALESCE(sales.TotalSalesRevenue, 0) - SUM(pod.LineTotal), 2) AS NetMargin
FROM PurchaseOrderHeader poh
JOIN PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
JOIN Product p ON pod.ProductID = p.ProductID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN (
    SELECT
        sod.ProductID,
        SUM(sod.OrderQty) AS TotalQtySold,
        ROUND(SUM(sod.LineTotal), 2) AS TotalSalesRevenue
    FROM SalesOrderDetail sod
    GROUP BY sod.ProductID
) sales ON p.ProductID = sales.ProductID
GROUP BY v.Name, p.Name, sales.TotalQtySold, sales.TotalSalesRevenue
ORDER BY NetMargin DESC;
```

---

**Q4: "Show each PO with the vendor name, vendor's country, the ship method, the approver's full name and email, the approver's pay rate, and the products with their unit of measure."**

*12 joins: PurchaseOrderHeader → PurchaseOrderDetail → Product → Vendor → BusinessEntityAddress → Address → StateProvince → CountryRegion → ShipMethod → Employee → Person → EmailAddress → EmployeePayHistory + ProductVendor → UnitMeasure*

```sql
SELECT
    poh.PurchaseOrderID,
    v.Name AS VendorName,
    cr.Name AS VendorCountry,
    sm.Name AS ShipMethod,
    per.FirstName || ' ' || per.LastName AS ApproverName,
    ea.EmailAddress AS ApproverEmail,
    eph.Rate AS ApproverPayRate,
    p.Name AS ProductName,
    pod.OrderQty,
    um.Name AS UnitOfMeasure,
    ROUND(pod.LineTotal, 2) AS LineTotal
FROM PurchaseOrderHeader poh
JOIN PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
JOIN Product p ON pod.ProductID = p.ProductID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN BusinessEntityAddress bea ON v.BusinessEntityID = bea.BusinessEntityID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID
JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
LEFT JOIN EmailAddress ea ON e.BusinessEntityID = ea.BusinessEntityID
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate = (
        SELECT MAX(eph2.RateChangeDate)
        FROM EmployeePayHistory eph2
        WHERE eph2.BusinessEntityID = e.BusinessEntityID
    )
LEFT JOIN ProductVendor pv ON p.ProductID = pv.ProductID
    AND v.BusinessEntityID = pv.BusinessEntityID
LEFT JOIN UnitMeasure um ON pv.UnitMeasureCode = um.UnitMeasureCode
ORDER BY poh.PurchaseOrderID;
```

---

**Q5: "For completed POs, show the vendor, products ordered, the received vs. rejected quantities, the work orders those products went into, the manufacturing locations, and the scrap rate."**

*9 joins: PurchaseOrderHeader → PurchaseOrderDetail → Product → Vendor → WorkOrder → ScrapReason → WorkOrderRouting → Location*

```sql
SELECT
    v.Name AS VendorName,
    p.Name AS ProductName,
    pod.OrderQty AS Ordered,
    pod.ReceivedQty AS Received,
    pod.RejectedQty AS Rejected,
    pod.StockedQty AS Stocked,
    wo.OrderQty AS MfgOrderQty,
    wo.ScrappedQty AS MfgScrapped,
    sr.Name AS ScrapReason,
    loc.Name AS MfgLocation,
    ROUND(wor.ActualCost, 2) AS MfgActualCost
FROM PurchaseOrderHeader poh
JOIN PurchaseOrderDetail pod ON poh.PurchaseOrderID = pod.PurchaseOrderID
JOIN Product p ON pod.ProductID = p.ProductID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN WorkOrder wo ON p.ProductID = wo.ProductID
LEFT JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
LEFT JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
LEFT JOIN Location loc ON wor.LocationID = loc.LocationID
WHERE poh.Status = 4
ORDER BY v.Name, p.Name;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the monthly procurement spend trend, and how does it compare month-over-month?"**

*Use case: Finance — procurement budget tracking*

```sql
WITH MonthlySpend AS (
    SELECT
        strftime('%Y-%m', OrderDate) AS OrderMonth,
        COUNT(*) AS POCount,
        ROUND(SUM(TotalDue), 2) AS TotalSpend,
        ROUND(AVG(TotalDue), 2) AS AvgPOValue
    FROM PurchaseOrderHeader
    GROUP BY strftime('%Y-%m', OrderDate)
)
SELECT
    OrderMonth,
    POCount,
    TotalSpend,
    AvgPOValue,
    LAG(TotalSpend) OVER (ORDER BY OrderMonth) AS PrevMonthSpend,
    ROUND(TotalSpend - COALESCE(LAG(TotalSpend) OVER (ORDER BY OrderMonth), 0), 2) AS MoM_Change
FROM MonthlySpend
ORDER BY OrderMonth;
```

---

**Q7: "Which vendors account for the most procurement spend, and what percentage of total spend does each represent?"**

*Use case: Vendor concentration risk / strategic sourcing*

```sql
WITH VendorSpend AS (
    SELECT
        VendorID,
        COUNT(*) AS POCount,
        ROUND(SUM(TotalDue), 2) AS TotalSpend
    FROM PurchaseOrderHeader
    GROUP BY VendorID
),
GrandTotal AS (
    SELECT SUM(TotalSpend) AS AllSpend FROM VendorSpend
)
SELECT
    vs.VendorID,
    vs.POCount,
    vs.TotalSpend,
    ROUND(vs.TotalSpend * 100.0 / gt.AllSpend, 2) AS SpendSharePct,
    SUM(vs.TotalSpend) OVER (ORDER BY vs.TotalSpend DESC) AS RunningTotal,
    ROUND(SUM(vs.TotalSpend) OVER (ORDER BY vs.TotalSpend DESC) * 100.0 / gt.AllSpend, 2) AS CumulativePct
FROM VendorSpend vs
CROSS JOIN GrandTotal gt
ORDER BY vs.TotalSpend DESC;
```

---

**Q8: "What's the PO status breakdown — how many are pending, approved, rejected, and complete — along with the total value in each status?"**

*Use case: Procurement pipeline visibility*

```sql
SELECT
    CASE Status
        WHEN 1 THEN 'Pending'
        WHEN 2 THEN 'Approved'
        WHEN 3 THEN 'Rejected'
        WHEN 4 THEN 'Complete'
        ELSE 'Unknown (' || Status || ')'
    END AS StatusLabel,
    COUNT(*) AS POCount,
    ROUND(SUM(TotalDue), 2) AS TotalValue,
    ROUND(AVG(TotalDue), 2) AS AvgPOValue,
    SUM(CASE WHEN ShipDate IS NULL THEN 1 ELSE 0 END) AS NotYetShipped,
    ROUND(SUM(Freight), 2) AS TotalFreight
FROM PurchaseOrderHeader
GROUP BY Status
ORDER BY Status;
```

---

**Q9: "Which employees approve the most POs, and what's their average PO value? Flag anyone who approves more than 500 POs."**

*Use case: Internal controls / approval workload distribution*

```sql
SELECT
    EmployeeID,
    COUNT(*) AS POsApproved,
    ROUND(SUM(TotalDue), 2) AS TotalApprovedValue,
    ROUND(AVG(TotalDue), 2) AS AvgPOValue,
    MIN(OrderDate) AS FirstPO,
    MAX(OrderDate) AS LastPO,
    CASE
        WHEN COUNT(*) > 500 THEN 'HIGH VOLUME APPROVER'
        ELSE 'NORMAL'
    END AS WorkloadFlag
FROM PurchaseOrderHeader
GROUP BY EmployeeID
ORDER BY POsApproved DESC;
```

---

**Q10: "What's the average days between order and ship for completed POs, broken down by ship method? Which methods are slowest?"**

*Use case: Logistics — vendor shipping performance*

```sql
SELECT
    ShipMethodID,
    COUNT(*) AS CompletedPOs,
    ROUND(AVG(JULIANDAY(ShipDate) - JULIANDAY(OrderDate)), 1) AS AvgDaysToShip,
    MIN(CAST(JULIANDAY(ShipDate) - JULIANDAY(OrderDate) AS INTEGER)) AS FastestDays,
    MAX(CAST(JULIANDAY(ShipDate) - JULIANDAY(OrderDate) AS INTEGER)) AS SlowestDays,
    ROUND(SUM(Freight), 2) AS TotalFreight,
    ROUND(AVG(Freight), 2) AS AvgFreight
FROM PurchaseOrderHeader
WHERE Status = 4
    AND ShipDate IS NOT NULL
GROUP BY ShipMethodID
ORDER BY AvgDaysToShip DESC;
```

---
