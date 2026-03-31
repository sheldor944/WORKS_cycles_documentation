# TransactionHistoryArchive

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores archived/historical product transactions — one row per archived transaction (89,253 records). It captures which product was involved (ProductID), what type of transaction occurred (TransactionType — W=Work Order, S=Sales Order, P=Purchase Order), the reference back to the originating order (ReferenceOrderID, ReferenceOrderLineID), when it happened (TransactionDate), and the financial impact (Quantity, ActualCost). This is the cold-storage companion to TransactionHistory (113,443 rows) — older transactions get moved here to keep the active table performant.

### Style 2: Query Possibilities & Business Story
This is the archived audit trail of product-level transactions — every time a product was sold, purchased, or manufactured in past periods, a record was created in TransactionHistory and eventually moved here for archival. It covers the same three transaction streams: sales (S), purchasing (P), and manufacturing/work orders (W). Use this table to answer questions like:

- "What's the total historical cost of all transactions for a specific product?"
- "How many archived sales vs. purchase vs. work order transactions are there?"
- "What's the oldest transaction in the archive?"
- "Which products had the highest transaction volume historically?"
- "What was the average actual cost per transaction type in past periods?"
- "Can I reconstruct a product's full transaction timeline by combining this with TransactionHistory?"
- "What's the total archived cost by transaction type?"
- "Which products have the most archived work order transactions — indicating heavy historical production?"
- "What was the monthly transaction volume trend before archival cutoff?"
- "Are there archived transactions for products that have since been discontinued?" (with Product)
- "What's the historical procurement cost vs. sales revenue for a product?" (filtering by TransactionType)
- "How does archived transaction volume compare to current active transactions?" (with TransactionHistory)

This table has **no foreign keys** — it's a standalone archive. ProductID references are logical (not enforced), and ReferenceOrderID points back to the originating SalesOrder, PurchaseOrder, or WorkOrder, but these links are also not enforced since the source records may also have been archived or modified.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per archived product transaction (89,253 rows), containing 9 columns organized as:

- **Identifiers:** TransactionID (PK — not auto-increment; preserves original ID from TransactionHistory)
- **Product:** ProductID (logical reference to Product — no enforced FK)
- **Source Order:** ReferenceOrderID (the originating order ID), ReferenceOrderLineID (the line item ID, default 0)
- **Transaction Details:** TransactionDate, TransactionType (W=Work Order/Manufacturing, S=Sales Order, P=Purchase Order)
- **Financials:** Quantity (units involved), ActualCost (cost of the transaction)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

TransactionHistoryArchive is the cold-storage counterpart to TransactionHistory — together they form the complete audit trail of every product-level transaction in the system. When transactions in TransactionHistory become old enough (past a retention period), they're moved here to keep the active table lean and performant.

The 89,253 archived records represent older sales, purchases, and manufacturing transactions. The table structure is identical to TransactionHistory, making it easy to UNION them for full historical analysis. However, unlike TransactionHistory, this table has **no enforced foreign keys** — it's deliberately decoupled from the live schema to avoid blocking archival of records when referenced entities change.

The three TransactionTypes tell the complete product cost story:
- **W (Work Order)** — cost of manufacturing the product
- **P (Purchase Order)** — cost of purchasing the product from vendors
- **S (Sales Order)** — revenue from selling the product

### Key Business Logic

- **TransactionID is NOT auto-increment** — it preserves the original TransactionID from TransactionHistory, maintaining traceability
- **TransactionType** = 'W' (Work Order), 'S' (Sales), 'P' (Purchase) — the three core transaction streams
- **ReferenceOrderID** links back to the originating order:
  - If TransactionType = 'W' → ReferenceOrderID = WorkOrderID
  - If TransactionType = 'S' → ReferenceOrderID = SalesOrderID
  - If TransactionType = 'P' → ReferenceOrderID = PurchaseOrderID
- **ReferenceOrderLineID** links to the specific line item (0 = header-level or no line item)
- **No enforced FKs** — ProductID and ReferenceOrderID are logical references only
- **To get full transaction history**, UNION this table with TransactionHistory
- **ActualCost** represents the actual monetary impact of the transaction (cost for W/P, revenue-related cost for S)
- **Quantity** can be positive or negative depending on the transaction context

### Relationships (Logical — Not Enforced)

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Logical | Product | ProductID | Product involved (not enforced FK) |
| → Logical | WorkOrder | ReferenceOrderID (when Type='W') | Manufacturing source |
| → Logical | SalesOrderHeader | ReferenceOrderID (when Type='S') | Sales source |
| → Logical | PurchaseOrderHeader | ReferenceOrderID (when Type='P') | Purchasing source |
| → Logical | SalesOrderDetail | ReferenceOrderID + ReferenceOrderLineID (Type='S') | Sales line item |
| → Logical | PurchaseOrderDetail | ReferenceOrderID + ReferenceOrderLineID (Type='P') | Purchase line item |
| Sibling | TransactionHistory (113,443) | Same schema — UNION for full history | Active transactions |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For archived sales transactions, show the product name, product category, the original sales order number, customer name, territory, and the transaction cost — joining back to live tables where possible."**

*8 joins: TransactionHistoryArchive → Product → ProductSubcategory → ProductCategory → SalesOrderHeader → Customer → Person → SalesTerritory*

```sql
SELECT
    tha.TransactionID,
    tha.TransactionDate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    soh.SalesOrderNumber,
    per.FirstName || ' ' || per.LastName AS CustomerName,
    st.Name AS Territory,
    tha.Quantity,
    ROUND(tha.ActualCost, 2) AS ActualCost
FROM TransactionHistoryArchive tha
JOIN Product p ON tha.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN SalesOrderHeader soh ON tha.ReferenceOrderID = soh.SalesOrderID
LEFT JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person per ON c.PersonID = per.BusinessEntityID
LEFT JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
WHERE tha.TransactionType = 'S'
ORDER BY tha.TransactionDate DESC;
```

---

**Q2: "For archived work order transactions, show the product name, category, the work order details (quantities, scrap), manufacturing locations from routing, and the scrap reason."**

*8 joins: TransactionHistoryArchive → Product → ProductSubcategory → ProductCategory → WorkOrder → ScrapReason → WorkOrderRouting → Location*

```sql
SELECT
    tha.TransactionID,
    tha.TransactionDate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    wo.OrderQty,
    wo.StockedQty,
    wo.ScrappedQty,
    sr.Name AS ScrapReason,
    loc.Name AS MfgLocation,
    tha.Quantity AS TxnQty,
    ROUND(tha.ActualCost, 2) AS TxnCost
FROM TransactionHistoryArchive tha
JOIN Product p ON tha.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN WorkOrder wo ON tha.ReferenceOrderID = wo.WorkOrderID
LEFT JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
LEFT JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
LEFT JOIN Location loc ON wor.LocationID = loc.LocationID
WHERE tha.TransactionType = 'W'
ORDER BY tha.TransactionDate DESC;
```

---

**Q3: "For archived purchase transactions, show the product name, vendor name, vendor credit rating, employee who approved the PO, ship method, and compare the archived transaction cost to the current product standard cost."**

*9 joins: TransactionHistoryArchive → Product → PurchaseOrderHeader → Vendor → Employee → Person → ShipMethod → ProductSubcategory → ProductCategory*

```sql
SELECT
    tha.TransactionID,
    tha.TransactionDate,
    p.Name AS ProductName,
    pcat.Name AS Category,
    p.StandardCost AS CurrentStdCost,
    ROUND(tha.ActualCost, 2) AS ArchivedTxnCost,
    ROUND(tha.ActualCost - p.StandardCost, 2) AS CostDrift,
    v.Name AS VendorName,
    v.CreditRating,
    per.FirstName || ' ' || per.LastName AS POApprover,
    sm.Name AS ShipMethod
FROM TransactionHistoryArchive tha
JOIN Product p ON tha.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN PurchaseOrderHeader poh ON tha.ReferenceOrderID = poh.PurchaseOrderID
LEFT JOIN Vendor v ON poh.VendorID = v.BusinessEntityID
LEFT JOIN Employee e ON poh.EmployeeID = e.BusinessEntityID
LEFT JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
LEFT JOIN ShipMethod sm ON poh.ShipMethodID = sm.ShipMethodID
WHERE tha.TransactionType = 'P'
ORDER BY CostDrift DESC;
```

---

**Q4: "Combine archived and active transactions for a complete product history — show product name, category, transaction type, date, cost, and tag whether each record is 'Active' or 'Archived'."**

*4 joins each, UNION: (TransactionHistoryArchive + TransactionHistory) → Product → ProductSubcategory → ProductCategory*

```sql
SELECT
    'Archived' AS Source,
    tha.TransactionID,
    tha.TransactionDate,
    tha.TransactionType,
    p.Name AS ProductName,
    pcat.Name AS Category,
    tha.Quantity,
    ROUND(tha.ActualCost, 2) AS ActualCost
FROM TransactionHistoryArchive tha
JOIN Product p ON tha.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID

UNION ALL

SELECT
    'Active' AS Source,
    th.TransactionID,
    th.TransactionDate,
    th.TransactionType,
    p.Name AS ProductName,
    pcat.Name AS Category,
    th.Quantity,
    ROUND(th.ActualCost, 2) AS ActualCost
FROM TransactionHistory th
JOIN Product p ON th.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID

ORDER BY TransactionDate DESC;
```

---

**Q5: "For products with archived transactions, show the product name, its current inventory levels by location, the total archived transaction costs by type, and the product's current list price — to understand historical cost vs. current value."**

*7 joins: TransactionHistoryArchive → Product → ProductSubcategory → ProductCategory → ProductInventory → Location*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    p.ListPrice AS CurrentListPrice,
    p.StandardCost AS CurrentStdCost,
    loc.Name AS InventoryLocation,
    pi.Quantity AS CurrentStock,
    SUM(CASE WHEN tha.TransactionType = 'S' THEN tha.ActualCost ELSE 0 END) AS ArchivedSalesCost,
    SUM(CASE WHEN tha.TransactionType = 'P' THEN tha.ActualCost ELSE 0 END) AS ArchivedPurchaseCost,
    SUM(CASE WHEN tha.TransactionType = 'W' THEN tha.ActualCost ELSE 0 END) AS ArchivedMfgCost,
    ROUND(SUM(tha.ActualCost), 2) AS TotalArchivedCost
FROM TransactionHistoryArchive tha
JOIN Product p ON tha.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductInventory pi ON p.ProductID = pi.ProductID
LEFT JOIN Location loc ON pi.LocationID = loc.LocationID
GROUP BY p.ProductID, p.Name, pcat.Name, p.ListPrice, p.StandardCost,
         loc.Name, pi.Quantity
ORDER BY TotalArchivedCost DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the breakdown of archived transactions by type — how many and how much cost for sales, purchases, and work orders?"**

*Use case: Data audit — understanding archive composition*

```sql
SELECT
    TransactionType,
    CASE TransactionType
        WHEN 'S' THEN 'Sales Order'
        WHEN 'P' THEN 'Purchase Order'
        WHEN 'W' THEN 'Work Order'
        ELSE 'Unknown'
    END AS TransactionTypeLabel,
    COUNT(*) AS TransactionCount,
    SUM(Quantity) AS TotalQuantity,
    ROUND(SUM(ActualCost), 2) AS TotalCost,
    ROUND(AVG(ActualCost), 2) AS AvgCostPerTxn,
    MIN(TransactionDate) AS EarliestTransaction,
    MAX(TransactionDate) AS LatestTransaction
FROM TransactionHistoryArchive
GROUP BY TransactionType
ORDER BY TransactionCount DESC;
```

---

**Q7: "Which products have the most archived transactions, and what's their total historical cost?"**

*Use case: Product activity analysis — identifying historically high-volume products*

```sql
SELECT
    ProductID,
    COUNT(*) AS ArchivedTxnCount,
    SUM(CASE WHEN TransactionType = 'S' THEN 1 ELSE 0 END) AS SalesTxns,
    SUM(CASE WHEN TransactionType = 'P' THEN 1 ELSE 0 END) AS PurchaseTxns,
    SUM(CASE WHEN TransactionType = 'W' THEN 1 ELSE 0 END) AS WorkOrderTxns,
    SUM(Quantity) AS TotalQuantity,
    ROUND(SUM(ActualCost), 2) AS TotalHistoricalCost,
    MIN(TransactionDate) AS FirstTxnDate,
    MAX(TransactionDate) AS LastTxnDate
FROM TransactionHistoryArchive
GROUP BY ProductID
ORDER BY ArchivedTxnCount DESC
LIMIT 20;
```

---

**Q8: "What's the monthly transaction volume and cost trend in the archive — when was the busiest period historically?"**

*Use case: Historical trend analysis — seasonality detection*

```sql
SELECT
    strftime('%Y-%m', TransactionDate) AS TxnMonth,
    COUNT(*) AS Transactions,
    SUM(CASE WHEN TransactionType = 'S' THEN 1 ELSE 0 END) AS Sales,
    SUM(CASE WHEN TransactionType = 'P' THEN 1 ELSE 0 END) AS Purchases,
    SUM(CASE WHEN TransactionType = 'W' THEN 1 ELSE 0 END) AS WorkOrders,
    SUM(Quantity) AS TotalQty,
    ROUND(SUM(ActualCost), 2) AS TotalCost
FROM TransactionHistoryArchive
GROUP BY strftime('%Y-%m', TransactionDate)
ORDER BY TxnMonth;
```

---

**Q9: "Compare the size and date ranges of archived vs. active transaction history."**

*Use case: DBA / data governance — archive health check*

```sql
SELECT
    'Active (TransactionHistory)' AS Source,
    COUNT(*) AS RecordCount,
    COUNT(DISTINCT ProductID) AS UniqueProducts,
    MIN(TransactionDate) AS EarliestDate,
    MAX(TransactionDate) AS LatestDate,
    ROUND(SUM(ActualCost), 2) AS TotalCost
FROM TransactionHistory

UNION ALL

SELECT
    'Archived (TransactionHistoryArchive)' AS Source,
    COUNT(*) AS RecordCount,
    COUNT(DISTINCT ProductID) AS UniqueProducts,
    MIN(TransactionDate) AS EarliestDate,
    MAX(TransactionDate) AS LatestDate,
    ROUND(SUM(ActualCost), 2) AS TotalCost
FROM TransactionHistoryArchive;
```

---

**Q10: "Are there archived transactions for products that have since been discontinued?"**

*Use case: Product lifecycle audit — historical activity on dead products*

```sql
SELECT
    tha.ProductID,
    p.Name AS ProductName,
    p.DiscontinuedDate,
    p.SellEndDate,
    COUNT(*) AS ArchivedTxnCount,
    SUM(tha.Quantity) AS TotalQty,
    ROUND(SUM(tha.ActualCost), 2) AS TotalHistoricalCost,
    MIN(tha.TransactionDate) AS FirstArchivedTxn,
    MAX(tha.TransactionDate) AS LastArchivedTxn
FROM TransactionHistoryArchive tha
JOIN Product p ON tha.ProductID = p.ProductID
WHERE p.DiscontinuedDate IS NOT NULL
    OR p.SellEndDate IS NOT NULL
GROUP BY tha.ProductID, p.Name, p.DiscontinuedDate, p.SellEndDate
ORDER BY TotalHistoricalCost DESC;
```

---
