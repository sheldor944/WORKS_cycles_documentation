# SalesOrderHeaderSalesReason

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table is a junction/bridge table linking sales orders to the reasons customers gave for buying — one row per order-reason combination (27,647 records). It captures which order (SalesOrderID → SalesOrderHeader) was associated with which buying reason (SalesReasonID → SalesReason). A single order can have multiple reasons (e.g., "Price" + "Quality"), and the same reason can apply to many orders. This is the "why customers buy" table — it bridges transactional data with customer motivation.

### Style 2: Query Possibilities & Business Story
This is the customer motivation table — it records why customers chose to purchase. When an order is placed, one or more buying reasons can be attached (e.g., "Price," "Quality," "Promotion," "Review," "Manufacturer"). With 27,647 links across 31,465 orders, not every order has a reason — and some have multiple. Use this table to answer questions like:

- "What are the most common reasons customers buy?"
- "How many orders cite multiple buying reasons?"
- "What percentage of orders have no buying reason recorded?"
- "Which buying reasons are associated with the highest average order value?"
- "Do online orders vs. sales-rep orders have different buying reasons?" (with SalesOrderHeader.OnlineOrderFlag)
- "Which territories cite 'Price' as a reason most often?" (with SalesOrderHeader, SalesTerritory)
- "Which salesperson's orders most frequently cite 'Quality' as a reason?" (with SalesPerson)
- "What's the revenue breakdown by buying reason?"
- "Which product categories are most associated with 'Promotion' as a buying reason?" (with SalesOrderDetail, Product, ProductCategory)
- "Do customers who cite 'Review' as a reason have higher order values?"
- "How has the mix of buying reasons changed over time?"
- "Which reason types (Marketing, Promotion, Other) drive the most revenue?" (with SalesReason.ReasonType)

This pure bridge table connects the transactional world (SalesOrderHeader) to the motivational world (SalesReason), enabling powerful customer behavior and marketing effectiveness analysis.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per order-reason combination (27,647 rows), containing 3 columns organized as:

- **Composite PK:** SalesOrderID (FK → SalesOrderHeader), SalesReasonID (FK → SalesReason)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

SalesOrderHeaderSalesReason is the many-to-many bridge between sales orders and customer buying motivations. With 27,647 links across 31,465 orders (~0.88 reasons per order on average), the data tells us that:
- Some orders have no reason recorded (gap between 31,465 orders and 27,647 links)
- Some orders have multiple reasons (total links > unique orders with reasons)
- The 10 buying reasons in SalesReason cover marketing channels, product attributes, and promotional triggers

This table is uniquely valuable for marketing ROI analysis — by connecting reasons to revenue, you can measure which motivations drive the most business. Combined with SalesOrderHeader's channel flag (online vs. rep), territory, and customer data, it enables deep segmentation of customer behavior.

### Key Business Logic

- **Composite PK (SalesOrderID, SalesReasonID)** — one order can have multiple reasons; one reason applies to many orders
- **27,647 rows < 31,465 orders** — not every order has a reason recorded; ~3,818 orders may have no reason
- **Some orders have 2+ reasons** — e.g., a customer bought because of both "Price" and "Quality"
- **SalesReason has 10 rows** with Name and ReasonType (e.g., ReasonType = 'Marketing', 'Promotion', 'Other')
- **No business data** in this junction — all reason details are in SalesReason; all order details in SalesOrderHeader
- **Not causation** — a reason being linked doesn't prove it caused the purchase; it's self-reported or assigned
- **ModifiedDate** = when the link was created/modified

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | SalesOrderHeader (31,465) | SalesOrderID | The order |
| → Parent | SalesReason (10) | SalesReasonID | The buying reason |
| ← Via SalesOrderHeader | Customer → Person / Store | CustomerID | Who bought |
| ← Via SalesOrderHeader | SalesPerson → Employee → Person | SalesPersonID | Who sold |
| ← Via SalesOrderHeader | SalesTerritory | TerritoryID | Where |
| ← Via SalesOrderHeader | SalesOrderDetail → Product | SalesOrderID | What was bought |
| ← Via SalesOrderDetail → Product | ProductSubcategory → ProductCategory | ProductSubcategoryID | Product classification |
| ← Via SalesOrderHeader | CreditCard | CreditCardID | Payment method |
| ← Via SalesOrderHeader | ShipMethod | ShipMethodID | Delivery method |
| ← Via SalesReason | — | ReasonType | Reason classification (Marketing/Promotion/Other) |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each order-reason link, show the order number, order date, customer name, salesperson name, territory, the buying reason, and the reason type."**

*8 joins: SalesOrderHeaderSalesReason → SalesReason → SalesOrderHeader → Customer → Person(customer) → SalesPerson → Employee → Person(rep) → SalesTerritory*

```sql
SELECT
    soh.SalesOrderNumber,
    soh.OrderDate,
    cust.FirstName || ' ' || cust.LastName AS CustomerName,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName,
    st.Name AS Territory,
    sr.Name AS BuyingReason,
    sr.ReasonType
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person cust ON c.PersonID = cust.BusinessEntityID
LEFT JOIN SalesPerson salp ON soh.SalesPersonID = salp.BusinessEntityID
LEFT JOIN Employee e ON salp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person rep ON e.BusinessEntityID = rep.BusinessEntityID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
ORDER BY soh.OrderDate DESC;
```

---

**Q2: "Show which buying reasons are associated with which product categories — join through order details to see what people bought and why."**

*8 joins: SalesOrderHeaderSalesReason → SalesReason → SalesOrderHeader → SalesOrderDetail → Product → ProductSubcategory → ProductCategory*

```sql
SELECT
    sr.Name AS BuyingReason,
    sr.ReasonType,
    pcat.Name AS ProductCategory,
    COUNT(DISTINCT sohsr.SalesOrderID) AS OrderCount,
    SUM(sod.OrderQty) AS TotalUnitsSold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
GROUP BY sr.Name, sr.ReasonType, pcat.Name
ORDER BY sr.Name, TotalRevenue DESC;
```

---

**Q3: "For each buying reason, show the revenue by territory, the channel (online vs. rep), the average order value, and the most common ship method used."**

*6 joins: SalesOrderHeaderSalesReason → SalesReason → SalesOrderHeader → SalesTerritory → ShipMethod*

```sql
SELECT
    sr.Name AS BuyingReason,
    sr.ReasonType,
    st.Name AS Territory,
    CASE WHEN soh.OnlineOrderFlag = 1 THEN 'Online' ELSE 'Sales Rep' END AS Channel,
    sm.Name AS ShipMethod,
    COUNT(DISTINCT sohsr.SalesOrderID) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
GROUP BY sr.Name, sr.ReasonType, st.Name, soh.OnlineOrderFlag, sm.Name
ORDER BY sr.Name, TotalRevenue DESC;
```

---

**Q4: "For each salesperson, show which buying reasons their customers cite most, their department, territory, and total revenue per reason."**

*9 joins: SalesOrderHeaderSalesReason → SalesReason → SalesOrderHeader → SalesPerson → Employee → Person → EmployeeDepartmentHistory → Department → SalesTerritory*

```sql
SELECT
    per.FirstName || ' ' || per.LastName AS SalesPersonName,
    d.Name AS Department,
    st.Name AS Territory,
    sr.Name AS BuyingReason,
    sr.ReasonType,
    COUNT(DISTINCT sohsr.SalesOrderID) AS OrdersWithThisReason,
    ROUND(SUM(soh.TotalDue), 2) AS RevenueFromThisReason
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
GROUP BY per.FirstName, per.LastName, d.Name, st.Name, sr.Name, sr.ReasonType
ORDER BY per.LastName, RevenueFromThisReason DESC;
```

---

**Q5: "Show the buying reasons for orders paid by each credit card type, shipped to each country, with the special offers applied — a full motivation-to-fulfillment view."**

*11 joins: SalesOrderHeaderSalesReason → SalesReason → SalesOrderHeader → CreditCard → Address(ship) → StateProvince → CountryRegion → SalesOrderDetail → SpecialOfferProduct → SpecialOffer → ShipMethod*

```sql
SELECT
    sr.Name AS BuyingReason,
    cc.CardType,
    cr.Name AS ShipCountry,
    so.Description AS SpecialOffer,
    sm.Name AS ShipMethod,
    COUNT(DISTINCT sohsr.SalesOrderID) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
LEFT JOIN CreditCard cc ON soh.CreditCardID = cc.CreditCardID
JOIN Address sa ON soh.ShipToAddressID = sa.AddressID
JOIN StateProvince sp ON sa.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN SpecialOfferProduct sop ON sod.SpecialOfferID = sop.SpecialOfferID
    AND sod.ProductID = sop.ProductID
JOIN SpecialOffer so ON sop.SpecialOfferID = so.SpecialOfferID
GROUP BY sr.Name, cc.CardType, cr.Name, so.Description, sm.Name
ORDER BY TotalRevenue DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What are the most common buying reasons by frequency and revenue?"**

*Use case: Marketing — understanding what drives purchases*

```sql
SELECT
    sr.SalesReasonID,
    sr.Name AS BuyingReason,
    sr.ReasonType,
    COUNT(DISTINCT sohsr.SalesOrderID) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue,
    ROUND(COUNT(DISTINCT sohsr.SalesOrderID) * 100.0 / (
        SELECT COUNT(DISTINCT SalesOrderID) FROM SalesOrderHeaderSalesReason
    ), 2) AS PctOfOrdersWithReasons
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
GROUP BY sr.SalesReasonID, sr.Name, sr.ReasonType
ORDER BY OrderCount DESC;
```

---

**Q7: "How many orders have no buying reason, one reason, or multiple reasons?"**

*Use case: Data quality / customer insight — reason capture rate*

```sql
WITH OrderReasonCounts AS (
    SELECT
        soh.SalesOrderID,
        COUNT(sohsr.SalesReasonID) AS ReasonCount
    FROM SalesOrderHeader soh
    LEFT JOIN SalesOrderHeaderSalesReason sohsr ON soh.SalesOrderID = sohsr.SalesOrderID
    GROUP BY soh.SalesOrderID
)
SELECT
    CASE
        WHEN ReasonCount = 0 THEN 'No Reason'
        WHEN ReasonCount = 1 THEN 'Single Reason'
        ELSE 'Multiple Reasons (' || ReasonCount || ')'
    END AS ReasonBucket,
    COUNT(*) AS OrderCount,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM SalesOrderHeader), 2) AS PctOfAllOrders
FROM OrderReasonCounts
GROUP BY ReasonBucket
ORDER BY OrderCount DESC;
```

---

**Q8: "How do buying reasons differ between online and sales-rep orders?"**

*Use case: Channel strategy — what motivates each channel's customers*

```sql
SELECT
    CASE WHEN soh.OnlineOrderFlag = 1 THEN 'Online' ELSE 'Sales Rep' END AS Channel,
    sr.Name AS BuyingReason,
    sr.ReasonType,
    COUNT(DISTINCT sohsr.SalesOrderID) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue,
    ROUND(COUNT(DISTINCT sohsr.SalesOrderID) * 100.0 / 
        SUM(COUNT(DISTINCT sohsr.SalesOrderID)) OVER (PARTITION BY soh.OnlineOrderFlag), 2) AS PctWithinChannel
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
GROUP BY soh.OnlineOrderFlag, sr.Name, sr.ReasonType
ORDER BY Channel, OrderCount DESC;
```

---

**Q9: "How has the mix of buying reasons changed over time — monthly trend?"**

*Use case: Marketing effectiveness — tracking shifting customer motivations*

```sql
SELECT
    strftime('%Y-%m', soh.OrderDate) AS OrderMonth,
    sr.Name AS BuyingReason,
    COUNT(DISTINCT sohsr.SalesOrderID) AS OrderCount,
    ROUND(SUM(soh.TotalDue), 2) AS Revenue,
    ROUND(COUNT(DISTINCT sohsr.SalesOrderID) * 100.0 /
        SUM(COUNT(DISTINCT sohsr.SalesOrderID)) OVER (PARTITION BY strftime('%Y-%m', soh.OrderDate)), 2) AS PctOfMonthsReasons
FROM SalesOrderHeaderSalesReason sohsr
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
JOIN SalesOrderHeader soh ON sohsr.SalesOrderID = soh.SalesOrderID
GROUP BY strftime('%Y-%m', soh.OrderDate), sr.Name
ORDER BY OrderMonth, OrderCount DESC;
```

---

**Q10: "Which buying reason combinations are most common — what pairs of reasons do customers cite together?"**

*Use case: Customer insight — multi-motivation patterns*

```sql
SELECT
    sr1.Name AS Reason1,
    sr2.Name AS Reason2,
    COUNT(DISTINCT sohsr1.SalesOrderID) AS OrdersWithBothReasons
FROM SalesOrderHeaderSalesReason sohsr1
JOIN SalesOrderHeaderSalesReason sohsr2
    ON sohsr1.SalesOrderID = sohsr2.SalesOrderID
    AND sohsr1.SalesReasonID < sohsr2.SalesReasonID
JOIN SalesReason sr1 ON sohsr1.SalesReasonID = sr1.SalesReasonID
JOIN SalesReason sr2 ON sohsr2.SalesReasonID = sr2.SalesReasonID
GROUP BY sr1.Name, sr2.Name
ORDER BY OrdersWithBothReasons DESC;
```

---
