# SalesOrderHeader

---

## 📋 Short Description

The **SalesOrderHeader** table is the primary sales transaction table containing **31,465 orders**. Each row represents a single sales order with information about when it was placed, who bought it, where it ships, how it's paid for, and the order's financial totals (subtotal, tax, freight, total due). It connects to customers, salespersons, territories, addresses, credit cards, currency rates, and shipping methods — making it the central hub of the entire sales domain.

---

## 📖 Extensive Description

### Purpose & Business Context

**SalesOrderHeader** is the backbone of the sales transactional system in this AdventureWorks database. Every time a customer places an order — whether online or through a sales representative — a record is created here. It captures the full lifecycle of an order from placement through shipment, and serves as the master record that ties together **who** ordered, **what** they ordered (via SalesOrderDetail), **where** it ships, **how** it's paid, and **when** key milestones occurred.

This is the single most interconnected table in the database, with **direct foreign keys to 8+ other tables**, making it the ideal starting point for virtually any sales analytics question.



Got it! Let me refine my understanding of the 3 styles:

- **Style 1:** Conceptual summary — what's in the table, key columns grouped by purpose, what kind of queries are possible
- **Style 2:** Business-oriented — tells the story of the table with **example questions a user could ask** (no column names, those are in Style 3)
- **Style 3:** Technical/grouped — every column listed and categorized

Let me redo just the short descriptions for SalesOrderHeader so you can validate:

---

### Style 1: Conceptual Summary
This table stores sales order headers — one row per order. It captures who ordered (CustomerID), when (OrderDate, DueDate, ShipDate), where it ships (ShipToAddressID, BillToAddressID, TerritoryID), how it was paid (CreditCardID, CurrencyRateID), and order totals (SubTotal, TaxAmt, Freight, TotalDue). Orders can be online or in-store (OnlineOrderFlag) and have a status (1–6). You can query revenue trends, fulfillment speed, channel performance, and shipping cost analysis from this table.

### Style 2: Query Possibilities & Business Story
This is the main sales order table — every purchase a customer makes starts here. Use this table to answer questions like:

- "What was the total revenue last quarter?"
- "How many orders are still unshipped?"
- "Which territory generates the most sales?"
- "What's the average time between order placement and shipping?"
- "How do online orders compare to sales-rep orders in volume and revenue?"
- "Which credit card type is used most frequently?"
- "What percentage of total order cost goes to freight and tax?"
- "Which salesperson is responsible for the highest-value orders?"
- "Are there customers with a declining average order value over time?"
- "How many orders involved a currency conversion?"

Each order connects to a customer, optionally a salesperson, a territory, billing and shipping addresses, a shipping method, a credit card, and an exchange rate — making it the central hub for any sales analysis.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per sales order (31,465 rows), containing 25 columns organized as:

- **Identifiers:** SalesOrderID (PK), SalesOrderNumber, rowguid
- **Dates:** OrderDate, DueDate, ShipDate, ModifiedDate
- **Status/Flags:** Status (1–6), OnlineOrderFlag (0/1), RevisionNumber
- **People & Geography:** CustomerID, SalesPersonID, TerritoryID
- **Addresses & Shipping:** BillToAddressID, ShipToAddressID, ShipMethodID
- **Payment:** CreditCardID, CreditCardApprovalCode, CurrencyRateID
- **Customer References:** PurchaseOrderNumber, AccountNumber
- **Financials:** SubTotal, TaxAmt, Freight, TotalDue
- **Misc:** Comment

---

### Column-Level Breakdown

| Column | Description |
|--------|-------------|
| **SalesOrderID** | Auto-incrementing primary key. Unique identifier for each order. |
| **RevisionNumber** | Tracks how many times the order has been revised/modified (default 0). |
| **OrderDate** | When the order was placed (defaults to current timestamp). |
| **DueDate** | Expected completion/delivery date. |
| **ShipDate** | Actual ship date. NULL means the order hasn't shipped yet. |
| **Status** | Order status code (default 1). Likely: 1=In Process, 2=Approved, 3=Backordered, 4=Rejected, 5=Shipped, 6=Cancelled. |
| **OnlineOrderFlag** | 1 = online order (no salesperson), 0 = placed by sales rep. |
| **SalesOrderNumber** | Human-readable unique order number (e.g., "SO43659"). |
| **PurchaseOrderNumber** | Customer's PO number (applicable for B2B/store orders). |
| **AccountNumber** | Customer's account number reference. |
| **CustomerID** | FK → **Customer** — identifies who placed the order. |
| **SalesPersonID** | FK → **SalesPerson** — NULL for online orders; populated for rep-assisted sales. |
| **TerritoryID** | FK → **SalesTerritory** — geographic region the order falls under. |
| **BillToAddressID** | FK → **Address** — billing address. |
| **ShipToAddressID** | FK → **Address** — shipping address (may differ from billing). |
| **ShipMethodID** | FK → **ShipMethod** — shipping carrier/method used. |
| **CreditCardID** | FK → **CreditCard** — payment card used (NULL if other payment method). |
| **CreditCardApprovalCode** | Authorization code from credit card processor. |
| **CurrencyRateID** | FK → **CurrencyRate** — exchange rate applied (NULL if USD/base currency). |
| **SubTotal** | Sum of line item totals before tax and freight. |
| **TaxAmt** | Total tax applied to the order. |
| **Freight** | Shipping/freight charges. |
| **TotalDue** | Final amount = SubTotal + TaxAmt + Freight. |
| **Comment** | Free-text notes on the order. |
| **rowguid** | Unique GUID for replication/integration. |
| **ModifiedDate** | Last modification timestamp. |

### Relationships to Other Tables

| Relationship | Table | Cardinality | Join Key |
|-------------|-------|-------------|----------|
| **Order Line Items** | SalesOrderDetail | 1:Many | SalesOrderID |
| **Order Reasons** | SalesOrderHeaderSalesReason → SalesReason | Many:Many | SalesOrderID |
| **Customer** | Customer → Person / Store | Many:1 | CustomerID |
| **Sales Rep** | SalesPerson → Employee → Person | Many:1 | SalesPersonID |
| **Territory** | SalesTerritory → CountryRegion | Many:1 | TerritoryID |
| **Billing Address** | Address → StateProvince → CountryRegion | Many:1 | BillToAddressID |
| **Shipping Address** | Address → StateProvince → CountryRegion | Many:1 | ShipToAddressID |
| **Shipping Method** | ShipMethod | Many:1 | ShipMethodID |
| **Credit Card** | CreditCard ← PersonCreditCard → Person | Many:1 | CreditCardID |
| **Currency Rate** | CurrencyRate → Currency (From/To) | Many:1 | CurrencyRateID |

### How It Fits in the Data Story

```
Customer places order
        │
        ▼
  SalesOrderHeader ◄── central hub
   │    │    │    │
   │    │    │    └── CreditCard (payment)
   │    │    └── ShipMethod (delivery)
   │    └── SalesPerson (who sold it)
   └── SalesTerritory (where)
        │
        ▼
  SalesOrderDetail (what products, quantities, prices)
        │
        ▼
  Product → ProductSubcategory → ProductCategory
```

### What You Can Ask

- Revenue, order volume, and average order value over time
- Online vs. offline (rep-assisted) order analysis
- Sales performance by territory, salesperson, or customer
- Shipping analysis (ship times, methods, freight costs)
- Payment method analysis (credit card types)
- Order status/fulfillment tracking
- Tax and freight as a percentage of revenue
- Currency/international order analysis
- Bill-to vs. ship-to address discrepancies
- Seasonal/temporal ordering patterns

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each sales order placed in 2013, show the order number, customer name, salesperson name, territory name, ship method, credit card type, and total due."**

*Joins: SalesOrderHeader → Customer → Person (customer) → SalesPerson → Employee → Person (salesperson) → SalesTerritory → ShipMethod → CreditCard = 8 joins*

```sql
SELECT
    soh.SalesOrderNumber,
    soh.OrderDate,
    pc.FirstName || ' ' || pc.LastName AS CustomerName,
    ps.FirstName || ' ' || ps.LastName AS SalesPersonName,
    st.Name AS TerritoryName,
    sm.Name AS ShipMethod,
    cc.CardType,
    soh.TotalDue
FROM SalesOrderHeader soh
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person pc ON c.PersonID = pc.BusinessEntityID
LEFT JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
LEFT JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person ps ON e.BusinessEntityID = ps.BusinessEntityID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
LEFT JOIN CreditCard cc ON soh.CreditCardID = cc.CreditCardID
WHERE strftime('%Y', soh.OrderDate) = '2013';
```

---

**Q2: "List all orders with the product names, product categories, billing city/state, shipping city/state, and the currency used for the exchange rate — for orders that involved a currency conversion."**

*Joins: SalesOrderHeader → SalesOrderDetail → Product → ProductSubcategory → ProductCategory → Address (bill) → StateProvince (bill) → Address (ship) → StateProvince (ship) → CurrencyRate → Currency = 11 joins*

```sql
SELECT
    soh.SalesOrderNumber,
    p.Name AS ProductName,
    pcat.Name AS CategoryName,
    ba.City AS BillCity,
    bsp.Name AS BillState,
    sa.City AS ShipCity,
    ssp.Name AS ShipState,
    cr.AverageRate,
    cf.Name AS FromCurrency,
    ct.Name AS ToCurrency,
    sod.LineTotal
FROM SalesOrderHeader soh
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN Address ba ON soh.BillToAddressID = ba.AddressID
JOIN StateProvince bsp ON ba.StateProvinceID = bsp.StateProvinceID
JOIN Address sa ON soh.ShipToAddressID = sa.AddressID
JOIN StateProvince ssp ON sa.StateProvinceID = ssp.StateProvinceID
JOIN CurrencyRate cr ON soh.CurrencyRateID = cr.CurrencyRateID
JOIN Currency cf ON cr.FromCurrencyCode = cf.CurrencyCode
JOIN Currency ct ON cr.ToCurrencyCode = ct.CurrencyCode;
```

---

**Q3: "Show each salesperson's name, their department, their territory, and total revenue from orders — including the reasons customers gave for buying."**

*Joins: SalesOrderHeader → SalesPerson → Employee → Person → EmployeeDepartmentHistory → Department → SalesTerritory → SalesOrderHeaderSalesReason → SalesReason = 8 joins*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS SalesPersonName,
    d.Name AS Department,
    st.Name AS Territory,
    sr.Name AS SalesReason,
    SUM(soh.TotalDue) AS TotalRevenue,
    COUNT(DISTINCT soh.SalesOrderID) AS OrderCount
FROM SalesOrderHeader soh
JOIN SalesPerson sp ON soh.SalesPersonID = sp.BusinessEntityID
JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN SalesOrderHeaderSalesReason sohsr ON soh.SalesOrderID = sohsr.SalesOrderID
JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
GROUP BY p.FirstName, p.LastName, d.Name, st.Name, sr.Name;
```

---

**Q4: "For each order shipped to a Canadian province, show the order details with the product name, vendor who supplies that product, the store name that placed the order, and the tax rate applicable to the shipping state."**

*Joins: SalesOrderHeader → SalesOrderDetail → Product → ProductVendor → Vendor → Address (ship) → StateProvince → CountryRegion → Customer → Store → SalesTaxRate = 11 joins*

```sql
SELECT
    soh.SalesOrderNumber,
    p.Name AS ProductName,
    v.Name AS VendorName,
    s.Name AS StoreName,
    sa.City AS ShipCity,
    sp.Name AS ShipState,
    str.TaxRate,
    sod.LineTotal
FROM SalesOrderHeader soh
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN Product p ON sod.ProductID = p.ProductID
JOIN ProductVendor pv ON p.ProductID = pv.ProductID
JOIN Vendor v ON pv.BusinessEntityID = v.BusinessEntityID
JOIN Address sa ON soh.ShipToAddressID = sa.AddressID
JOIN StateProvince sp ON sa.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion crg ON sp.CountryRegionCode = crg.CountryRegionCode
JOIN Customer c ON soh.CustomerID = c.CustomerID
JOIN Store s ON c.StoreID = s.BusinessEntityID
LEFT JOIN SalesTaxRate str ON sp.StateProvinceID = str.StateProvinceID
WHERE crg.CountryRegionCode = 'CA';
```

---

**Q5: "Show the full order journey: order number, customer email, product name, product model description (in English), special offer applied, ship method, and the country of the shipping address."**

*Joins: SalesOrderHeader → SalesOrderDetail → SpecialOfferProduct → SpecialOffer → Product → ProductModel → PMPDC → ProductDescription → Culture → Customer → Person → EmailAddress → Address (ship) → StateProvince → CountryRegion → ShipMethod = 15 joins*

```sql
SELECT
    soh.SalesOrderNumber,
    ea.EmailAddress,
    p.Name AS ProductName,
    pd.Description AS ProductModelDescription,
    so.Description AS SpecialOfferDescription,
    so.DiscountPct,
    sm.Name AS ShipMethod,
    crg.Name AS ShipCountry,
    sod.LineTotal
FROM SalesOrderHeader soh
JOIN SalesOrderDetail sod ON soh.SalesOrderID = sod.SalesOrderID
JOIN SpecialOfferProduct sop ON sod.SpecialOfferID = sop.SpecialOfferID
    AND sod.ProductID = sop.ProductID
JOIN SpecialOffer so ON sop.SpecialOfferID = so.SpecialOfferID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductModel pm ON p.ProductModelID = pm.ProductModelID
LEFT JOIN ProductModelProductDescriptionCulture pmpdc
    ON pm.ProductModelID = pmpdc.ProductModelID
LEFT JOIN ProductDescription pd ON pmpdc.ProductDescriptionID = pd.ProductDescriptionID
LEFT JOIN Culture cu ON pmpdc.CultureID = cu.CultureID AND cu.CultureID = 'en'
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person per ON c.PersonID = per.BusinessEntityID
LEFT JOIN EmailAddress ea ON per.BusinessEntityID = ea.BusinessEntityID
JOIN Address sa ON soh.ShipToAddressID = sa.AddressID
JOIN StateProvince sp ON sa.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion crg ON sp.CountryRegionCode = crg.CountryRegionCode
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What is the monthly revenue trend for the last 2 years, broken down by online vs. offline orders?"**

*Use case: Executive dashboard — channel performance over time*

```sql
SELECT
    strftime('%Y-%m', OrderDate) AS OrderMonth,
    CASE WHEN OnlineOrderFlag = 1 THEN 'Online' ELSE 'Sales Rep' END AS Channel,
    COUNT(*) AS OrderCount,
    ROUND(SUM(TotalDue), 2) AS Revenue,
    ROUND(AVG(TotalDue), 2) AS AvgOrderValue
FROM SalesOrderHeader
WHERE OrderDate >= DATE('now', '-2 years')
GROUP BY OrderMonth, OnlineOrderFlag
ORDER BY OrderMonth, OnlineOrderFlag;
```

---

**Q7: "What is the average number of days between order date and ship date, grouped by order status? Also show how many orders are still unshipped."**

*Use case: Operations/fulfillment — order processing efficiency*

```sql
SELECT
    Status,
    COUNT(*) AS OrderCount,
    SUM(CASE WHEN ShipDate IS NULL THEN 1 ELSE 0 END) AS UnshippedOrders,
    ROUND(AVG(
        CASE WHEN ShipDate IS NOT NULL
        THEN JULIANDAY(ShipDate) - JULIANDAY(OrderDate)
        END
    ), 1) AS AvgDaysToShip,
    ROUND(SUM(TotalDue), 2) AS TotalRevenue
FROM SalesOrderHeader
GROUP BY Status
ORDER BY Status;
```

---

**Q8: "Which territories have the highest freight cost as a percentage of total revenue? Flag territories where freight exceeds 5% of subtotal."**

*Use case: Supply chain / logistics cost optimization*

```sql
SELECT
    TerritoryID,
    COUNT(*) AS Orders,
    ROUND(SUM(SubTotal), 2) AS TotalSubTotal,
    ROUND(SUM(Freight), 2) AS TotalFreight,
    ROUND(SUM(Freight) * 100.0 / NULLIF(SUM(SubTotal), 0), 2) AS FreightPctOfSubtotal,
    CASE
        WHEN SUM(Freight) * 100.0 / NULLIF(SUM(SubTotal), 0) > 5.0
        THEN '⚠️ HIGH'
        ELSE '✅ OK'
    END AS FreightAlert
FROM SalesOrderHeader
GROUP BY TerritoryID
ORDER BY FreightPctOfSubtotal DESC;
```

---

**Q9: "Identify customers who have placed more than 10 orders but whose average order value has been declining year-over-year."**

*Use case: Customer retention / churn risk detection*

```sql
WITH CustomerYearlyStats AS (
    SELECT
        CustomerID,
        strftime('%Y', OrderDate) AS OrderYear,
        COUNT(*) AS Orders,
        ROUND(AVG(TotalDue), 2) AS AvgOrderValue
    FROM SalesOrderHeader
    GROUP BY CustomerID, strftime('%Y', OrderDate)
),
CustomerTotalOrders AS (
    SELECT CustomerID, SUM(Orders) AS TotalOrders
    FROM CustomerYearlyStats
    GROUP BY CustomerID
    HAVING SUM(Orders) > 10
),
YoYComparison AS (
    SELECT
        cys.CustomerID,
        cys.OrderYear,
        cys.AvgOrderValue,
        LAG(cys.AvgOrderValue) OVER (PARTITION BY cys.CustomerID ORDER BY cys.OrderYear) AS PrevYearAOV
    FROM CustomerYearlyStats cys
    JOIN CustomerTotalOrders cto ON cys.CustomerID = cto.CustomerID
)
SELECT
    CustomerID,
    OrderYear,
    AvgOrderValue,
    PrevYearAOV,
    ROUND(AvgOrderValue - PrevYearAOV, 2) AS AOV_Change
FROM YoYComparison
WHERE PrevYearAOV IS NOT NULL
    AND AvgOrderValue < PrevYearAOV
ORDER BY CustomerID, OrderYear;
```

---

**Q10: "Show a summary of orders by credit card type vs. orders with no credit card, including average order value and percentage of total revenue each payment method represents."**

*Use case: Finance / payment analytics*

```sql
WITH PaymentSummary AS (
    SELECT
        COALESCE(cc.CardType, 'No Credit Card') AS PaymentMethod,
        COUNT(*) AS OrderCount,
        ROUND(SUM(soh.TotalDue), 2) AS Revenue,
        ROUND(AVG(soh.TotalDue), 2) AS AvgOrderValue
    FROM SalesOrderHeader soh
    LEFT JOIN CreditCard cc ON soh.CreditCardID = cc.CreditCardID
    GROUP BY COALESCE(cc.CardType, 'No Credit Card')
),
GrandTotal AS (
    SELECT SUM(Revenue) AS TotalRevenue FROM PaymentSummary
)
SELECT
    ps.PaymentMethod,
    ps.OrderCount,
    ps.Revenue,
    ps.AvgOrderValue,
    ROUND(ps.Revenue * 100.0 / gt.TotalRevenue, 2) AS RevenueSharePct
FROM PaymentSummary ps
CROSS JOIN GrandTotal gt
ORDER BY ps.Revenue DESC;
```

---
