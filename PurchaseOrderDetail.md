# PurchaseOrderDetail

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores purchase order line items — one row per product line on a purchase order (8,845 line items). It captures what was ordered (ProductID, OrderQty, UnitPrice, LineTotal), when it's due (DueDate), and critically what happened upon receipt — how much was received (ReceivedQty), rejected (RejectedQty), and actually stocked (StockedQty). This is the procurement equivalent of SalesOrderDetail, but with the added receiving/quality dimension that tracks the gap between what was ordered and what made it to inventory.

### Style 2: Query Possibilities & Business Story
This is the line-item detail for every purchase order — each row represents a specific product ordered from a vendor in a specific quantity at a specific price. What makes this table especially valuable is the receiving pipeline: ordered → received → rejected → stocked. Use this table to answer questions like:

- "What products did we purchase and at what unit price?"
- "What's the total spend by product across all purchase orders?"
- "Which products have the highest rejection rate upon receiving?"
- "How much inventory was lost between ordered quantity and stocked quantity?"
- "What's the average unit price we're paying for a specific product over time?"
- "Which purchase orders have items that are past due but not yet fully received?"
- "What's the total quantity stocked vs. ordered — are we getting what we pay for?"
- "Which products have the biggest gap between ReceivedQty and StockedQty?"
- "How does our purchase price compare to the product's list price or standard cost?" (with Product)
- "Which vendors have the worst rejection rates?" (with PurchaseOrderHeader, Vendor)
- "What's our total procurement spend by product category?" (with Product, ProductSubcategory, ProductCategory)
- "Compare what we bought vs. what we sold for each product." (with SalesOrderDetail)

Each line item connects to its parent PurchaseOrderHeader (for vendor, employee, ship method) and to the Product catalog.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per purchase order line item (8,845 rows), containing 11 columns organized as:

- **Identifiers:** PurchaseOrderDetailID (PK, auto-increment), PurchaseOrderID (FK → PurchaseOrderHeader)
- **Product & Pricing:** ProductID (FK → Product), UnitPrice, OrderQty, LineTotal (= OrderQty × UnitPrice)
- **Due Date:** DueDate (expected delivery date for this line item)
- **Receiving Pipeline:** ReceivedQty (total received from vendor), RejectedQty (failed quality check), StockedQty (= ReceivedQty - RejectedQty, what made it to inventory)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

PurchaseOrderDetail is the granular procurement transaction table — 8,845 line items across 4,012 purchase orders (~2.2 items per PO on average). While PurchaseOrderHeader captures who placed the order and with which vendor, this table captures what was ordered, how much, at what price, and most importantly the quality/receiving outcome.

The **ordered → received → rejected → stocked** pipeline is the unique value of this table. It enables quality analysis (rejection rates), vendor reliability assessment (do they deliver what was ordered?), and inventory accuracy (does what we receive actually make it to the shelf?). Combined with Product pricing data, it also supports purchase price variance analysis — are we paying more or less than expected?

### Key Business Logic

- **LineTotal = OrderQty × UnitPrice** — total cost for this line item
- **StockedQty = ReceivedQty - RejectedQty** — what actually made it to inventory
- **ReceivedQty < OrderQty** → vendor short-shipped
- **RejectedQty > 0** → quality issue, items failed inspection
- **StockedQty < OrderQty** → inventory shortfall (short shipment + rejections combined)
- **DueDate** is per line item, not per order — different products on the same PO can have different due dates
- A single PurchaseOrderHeader can have multiple PurchaseOrderDetail lines (different products/quantities)
- **UnitPrice** here may differ from ProductVendor.StandardPrice (negotiated vs. catalog price)

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | PurchaseOrderHeader | PurchaseOrderID | Order-level info (vendor, employee, ship method, totals) |
| → Parent | Product | ProductID | Product catalog (name, cost, category, etc.) |
| ← Via PurchaseOrderHeader | Vendor | VendorID | Which vendor supplied this |
| ← Via PurchaseOrderHeader | Employee | EmployeeID | Who approved the PO |
| ← Via PurchaseOrderHeader | ShipMethod | ShipMethodID | How it was shipped |
| ← Via Product | ProductSubcategory → ProductCategory | ProductSubcategoryID | Product classification |
| ← Via Product | ProductVendor | ProductID + VendorID | Catalog pricing, lead time |
| Comparison | SalesOrderDetail | ProductID | Buy price vs. sell price per product |
| Related | ProductInventory | ProductID | StockedQty feeds into inventory |
| Related | WorkOrder | ProductID | Purchased components used in manufacturing |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each purchase order line item, show the PO number, product name, product category, vendor name, vendor credit rating, employee who approved it, ship method, unit price, and receiving results (received/rejected/stocked)."**

*9 joins: PurchaseOrderDetail → PurchaseOrderHeader → Vendor → Employee → Person → ShipMethod → Product → ProductSubcategory → ProductCategory*

```sql
SELECT
    poh.PurchaseOrderID,
    p.Name AS ProductName,
    pcat.Name AS Category,
    v.Name AS VendorName,
    v.CreditRating,
    per.FirstName || ' ' || per.LastName AS Approver,
    sm.Name AS ShipMethod,
    pod.UnitPrice,
    pod.OrderQty,
    pod.ReceivedQty,
    pod.RejectedQty,
    pod.StockedQty,
    ROUND(pod.LineTotal, 2) AS LineTotal
FROM PurchaseOrderDetail pod
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
JOIN Product p ON pod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID
ORDER BY poh.PurchaseOrderID, pod.PurchaseOrderDetailID;
```

---

**Q2: "Compare our purchase unit price for each product against the vendor's catalog standard price, the product's standard cost, and the product's list price — show the vendor's city/state and credit rating."**

*10 joins: PurchaseOrderDetail → PurchaseOrderHeader → Vendor → BusinessEntityAddress → Address → StateProvince → Product → ProductVendor → ProductSubcategory → ProductCategory*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    v.Name AS VendorName,
    v.CreditRating,
    a.City AS VendorCity,
    sp.Name AS VendorState,
    pod.UnitPrice AS ActualPurchasePrice,
    pv.StandardPrice AS VendorCatalogPrice,
    p.StandardCost AS ProductStdCost,
    p.ListPrice AS ProductListPrice,
    ROUND(pod.UnitPrice - pv.StandardPrice, 2) AS PriceVsCatalog,
    ROUND(p.ListPrice - pod.UnitPrice, 2) AS MarginOverPurchase
FROM PurchaseOrderDetail pod
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN BusinessEntityAddress bea ON v.BusinessEntityID = bea.BusinessEntityID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
JOIN Product p ON pod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductVendor pv ON p.ProductID = pv.ProductID
    AND v.BusinessEntityID = pv.BusinessEntityID
ORDER BY MarginOverPurchase ASC;
```

---

**Q3: "For each product purchased, show the total quantity purchased, total stocked, total rejected, plus total quantity sold and total sales revenue — to see the full buy-to-sell pipeline."**

*6 joins: PurchaseOrderDetail → Product → ProductSubcategory → ProductCategory → SalesOrderDetail → SalesOrderHeader*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    SUM(pod.OrderQty) AS TotalQtyOrdered,
    SUM(pod.ReceivedQty) AS TotalReceived,
    SUM(pod.RejectedQty) AS TotalRejected,
    SUM(pod.StockedQty) AS TotalStocked,
    ROUND(SUM(pod.LineTotal), 2) AS TotalPurchaseCost,
    COALESCE(sales.TotalQtySold, 0) AS TotalQtySold,
    COALESCE(sales.TotalSalesRevenue, 0) AS TotalSalesRevenue,
    ROUND(COALESCE(sales.TotalSalesRevenue, 0) - SUM(pod.LineTotal), 2) AS GrossMargin
FROM PurchaseOrderDetail pod
JOIN Product p ON pod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN (
    SELECT
        ProductID,
        SUM(OrderQty) AS TotalQtySold,
        ROUND(SUM(LineTotal), 2) AS TotalSalesRevenue
    FROM SalesOrderDetail
    GROUP BY ProductID
) sales ON p.ProductID = sales.ProductID
GROUP BY p.ProductID, p.Name, pcat.Name, sales.TotalQtySold, sales.TotalSalesRevenue
ORDER BY GrossMargin DESC;
```

---

**Q4: "Show the receiving details for each vendor, including the vendor's contact person name and role, the products received, rejection rates, and the manufacturing work orders those products fed into."**

*11 joins: PurchaseOrderDetail → PurchaseOrderHeader → Vendor → BusinessEntityContact → Person → ContactType → Product → WorkOrder → ScrapReason*

```sql
SELECT
    v.Name AS VendorName,
    per.FirstName || ' ' || per.LastName AS VendorContact,
    ct.Name AS ContactRole,
    p.Name AS ProductName,
    SUM(pod.OrderQty) AS TotalOrdered,
    SUM(pod.ReceivedQty) AS TotalReceived,
    SUM(pod.RejectedQty) AS TotalRejected,
    ROUND(SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0), 2) AS RejectionRatePct,
    COUNT(DISTINCT wo.WorkOrderID) AS RelatedWorkOrders,
    SUM(wo.ScrappedQty) AS MfgScrap
FROM PurchaseOrderDetail pod
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN BusinessEntityContact bec ON v.BusinessEntityID = bec.BusinessEntityID
LEFT JOIN Person per ON bec.PersonID = per.BusinessEntityID
LEFT JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
JOIN Product p ON pod.ProductID = p.ProductID
LEFT JOIN WorkOrder wo ON p.ProductID = wo.ProductID
LEFT JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
GROUP BY v.Name, per.FirstName, per.LastName, ct.Name, p.Name
ORDER BY RejectionRatePct DESC;
```

---

**Q5: "For products that we both purchase from vendors and stock in inventory, show the product name, category, total quantity stocked from POs, current inventory level by location, and the location's availability and cost rate."**

*8 joins: PurchaseOrderDetail → Product → ProductSubcategory → ProductCategory → ProductInventory → Location → PurchaseOrderHeader → Vendor*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    v.Name AS Vendor,
    SUM(pod.StockedQty) AS TotalStockedFromPOs,
    loc.Name AS InventoryLocation,
    pi.Quantity AS CurrentInventory,
    pi.Shelf,
    pi.Bin,
    loc.CostRate AS LocationCostRate,
    loc.Availability AS LocationAvailability
FROM PurchaseOrderDetail pod
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
JOIN Product p ON pod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN ProductInventory pi ON p.ProductID = pi.ProductID
JOIN Location loc ON pi.LocationID = loc.LocationID
GROUP BY p.Name, pcat.Name, v.Name, loc.Name, pi.Quantity, pi.Shelf, pi.Bin,
         loc.CostRate, loc.Availability
ORDER BY p.Name, loc.Name;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the overall vendor quality scorecard — rejection rate by vendor?"**

*Use case: Vendor quality management / supplier evaluation*

```sql
SELECT
    poh.VendorID,
    COUNT(DISTINCT poh.PurchaseOrderID) AS TotalPOs,
    COUNT(*) AS TotalLineItems,
    SUM(pod.OrderQty) AS TotalQtyOrdered,
    SUM(pod.ReceivedQty) AS TotalReceived,
    SUM(pod.RejectedQty) AS TotalRejected,
    SUM(pod.StockedQty) AS TotalStocked,
    ROUND(SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0), 2) AS RejectionRatePct,
    ROUND(SUM(pod.StockedQty) * 100.0 / NULLIF(SUM(pod.OrderQty), 0), 2) AS FulfillmentRatePct,
    CASE
        WHEN SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0) > 5.0
        THEN 'HIGH REJECTION'
        ELSE 'ACCEPTABLE'
    END AS QualityFlag
FROM PurchaseOrderDetail pod
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
GROUP BY poh.VendorID
ORDER BY RejectionRatePct DESC;
```

---

**Q7: "Which products have we been paying increasingly more for over time — unit price trending upward?"**

*Use case: Procurement cost control / price inflation detection*

```sql
WITH ProductPriceByYear AS (
    SELECT
        pod.ProductID,
        strftime('%Y', poh.OrderDate) AS OrderYear,
        ROUND(AVG(pod.UnitPrice), 2) AS AvgUnitPrice
    FROM PurchaseOrderDetail pod
    JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
    GROUP BY pod.ProductID, strftime('%Y', poh.OrderDate)
)
SELECT
    cur.ProductID,
    cur.OrderYear,
    cur.AvgUnitPrice AS CurrentYearPrice,
    prev.AvgUnitPrice AS PrevYearPrice,
    ROUND(cur.AvgUnitPrice - prev.AvgUnitPrice, 2) AS PriceIncrease,
    ROUND((cur.AvgUnitPrice - prev.AvgUnitPrice) * 100.0 / NULLIF(prev.AvgUnitPrice, 0), 2) AS PriceIncreasePct
FROM ProductPriceByYear cur
JOIN ProductPriceByYear prev
    ON cur.ProductID = prev.ProductID
    AND CAST(cur.OrderYear AS INTEGER) = CAST(prev.OrderYear AS INTEGER) + 1
WHERE cur.AvgUnitPrice > prev.AvgUnitPrice
ORDER BY PriceIncreasePct DESC;
```

---

**Q8: "Which line items are past due — DueDate has passed but ReceivedQty is less than OrderQty?"**

*Use case: Procurement operations — overdue delivery tracking*

```sql
SELECT
    pod.PurchaseOrderID,
    pod.PurchaseOrderDetailID,
    pod.ProductID,
    pod.DueDate,
    CAST(JULIANDAY('now') - JULIANDAY(pod.DueDate) AS INTEGER) AS DaysOverdue,
    pod.OrderQty,
    pod.ReceivedQty,
    pod.OrderQty - pod.ReceivedQty AS OutstandingQty,
    ROUND(pod.UnitPrice * (pod.OrderQty - pod.ReceivedQty), 2) AS OutstandingValue
FROM PurchaseOrderDetail pod
WHERE pod.DueDate < DATE('now')
    AND pod.ReceivedQty < pod.OrderQty
ORDER BY DaysOverdue DESC;
```

---


---

**Q10: "What's the monthly trend of quantities ordered, received, rejected, and stocked — to track procurement volume and quality over time?"**

*Use case: Procurement operations — volume and quality trend*

```sql
SELECT
    strftime('%Y-%m', poh.OrderDate) AS OrderMonth,
    COUNT(*) AS LineItems,
    COUNT(DISTINCT pod.PurchaseOrderID) AS UniqueOrders,
    SUM(pod.OrderQty) AS TotalOrdered,
    SUM(pod.ReceivedQty) AS TotalReceived,
    SUM(pod.RejectedQty) AS TotalRejected,
    SUM(pod.StockedQty) AS TotalStocked,
    ROUND(SUM(pod.RejectedQty) * 100.0 / NULLIF(SUM(pod.ReceivedQty), 0), 2) AS MonthlyRejectionRate,
    ROUND(SUM(pod.LineTotal), 2) AS TotalSpend
FROM PurchaseOrderDetail pod
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
GROUP BY strftime('%Y-%m', poh.OrderDate)
ORDER BY OrderMonth;
```

---
