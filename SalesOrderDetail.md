# SalesOrderDetail

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores sales order line items — one row per product line on a sales order (121,317 line items). It captures what was sold (ProductID, OrderQty, UnitPrice), any discount applied (UnitPriceDiscount via SpecialOfferID), the computed line total (LineTotal), and shipment tracking (CarrierTrackingNumber). This is the largest transactional table in the database and the primary source for product-level sales analytics — revenue, volume, discounting, and product mix analysis all start here.

### Style 2: Query Possibilities & Business Story
This is the line-item detail behind every sales order — each row represents a specific product sold to a customer in a specific quantity at a specific price, potentially with a promotional discount. It's the single most important table for revenue analytics. Use this table to answer questions like:

- "What are the top-selling products by revenue and quantity?"
- "What's the total revenue by product category?"
- "How much revenue was lost to discounts?"
- "Which special offers/promotions drove the most sales volume?"
- "What's the average order size (number of line items per order)?"
- "What's the average unit price and discount rate by product?"
- "Which products are frequently bought together on the same order?"
- "How does product revenue trend month over month?"
- "What's the revenue by territory, salesperson, or customer?" (with SalesOrderHeader)
- "Which products have the highest discount rate — are we giving away margin?"
- "What's the carrier tracking coverage — how many items have tracking numbers?"
- "Compare sell price to standard cost — what's the actual margin per line item?" (with Product)
- "Which promotions are most effective at driving volume without destroying margin?" (with SpecialOffer)

Each line item connects to its parent SalesOrderHeader (for customer, salesperson, territory, dates, payment) and to SpecialOfferProduct (which links both the promotion and the product). This is the sales-side counterpart of PurchaseOrderDetail.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per sales order line item (121,317 rows), containing 11 columns organized as:

- **Identifiers:** SalesOrderDetailID (PK, auto-increment), SalesOrderID (FK → SalesOrderHeader), rowguid
- **Product & Promotion:** ProductID (FK via SpecialOfferProduct), SpecialOfferID (FK via SpecialOfferProduct — composite FK)
- **Pricing:** UnitPrice, UnitPriceDiscount (0.00 = no discount, decimal fraction e.g., 0.02 = 2%), LineTotal (= OrderQty × UnitPrice × (1 - UnitPriceDiscount))
- **Quantity:** OrderQty
- **Shipping:** CarrierTrackingNumber (nullable — tracking ID from carrier)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

SalesOrderDetail is the largest transactional table in the database (121,317 rows across 31,465 orders — ~3.9 items per order average) and is the definitive source for product-level sales analysis. While SalesOrderHeader captures the order envelope (who, when, where, how paid), this table captures what was actually sold — every product, quantity, price, discount, and line total.

The composite FK to SpecialOfferProduct (SpecialOfferID + ProductID) is a key design element — it means every line item is associated with a promotion, even if it's the "No Discount" default offer. This enables precise tracking of which promotions drove which sales.

Combined with SalesOrderHeader (for customer, territory, salesperson, dates) and Product (for cost, category, model), this table powers virtually every sales KPI: revenue, units sold, average selling price, discount impact, product mix, basket analysis, and margin analysis.

### Key Business Logic

- **LineTotal = OrderQty × UnitPrice × (1 - UnitPriceDiscount)** — the final revenue for this line
- **UnitPriceDiscount** is a decimal fraction: 0.00 = no discount, 0.02 = 2% off, 0.10 = 10% off, etc.
- **SpecialOfferID** references via composite FK to SpecialOfferProduct — even "no discount" items have a SpecialOfferID (typically ID = 1 for "No Discount")
- **CarrierTrackingNumber** is nullable — not all items have carrier tracking; may be NULL for in-store pickup or unshipped items
- **UnitPrice** here may differ from Product.ListPrice — it's the actual selling price at the time of sale
- Multiple line items per SalesOrderID — one order can contain many products
- This table does NOT have receiving/rejection columns (unlike PurchaseOrderDetail) — it's purely the sell side

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | SalesOrderHeader | SalesOrderID | Order envelope (customer, dates, payment, territory) |
| → Parent | SpecialOfferProduct → SpecialOffer | SpecialOfferID + ProductID | Promotion applied |
| → Parent | SpecialOfferProduct → Product | SpecialOfferID + ProductID | Product sold |
| ← Via SalesOrderHeader | Customer → Person / Store | CustomerID | Who bought it |
| ← Via SalesOrderHeader | SalesPerson → Employee → Person | SalesPersonID | Who sold it |
| ← Via SalesOrderHeader | SalesTerritory | TerritoryID | Where it was sold |
| ← Via SalesOrderHeader | Address (Ship/Bill) → StateProvince → CountryRegion | AddressID | Geography |
| ← Via SalesOrderHeader | CreditCard | CreditCardID | Payment method |
| ← Via SalesOrderHeader | ShipMethod | ShipMethodID | Shipping method |
| ← Via Product | ProductSubcategory → ProductCategory | ProductSubcategoryID | Product classification |
| ← Via Product | ProductModel | ProductModelID | Product model grouping |
| Comparison | PurchaseOrderDetail | ProductID | Buy price vs. sell price |
| Related | TransactionHistory | ReferenceOrderID = SalesOrderID | Audit trail |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each line item, show the order number, order date, customer name, product name, product category, special offer description, unit price, discount, and line total."**

*9 joins: SalesOrderDetail → SalesOrderHeader → Customer → Person → SpecialOfferProduct → SpecialOffer → Product → ProductSubcategory → ProductCategory*

```sql
SELECT
    soh.SalesOrderNumber,
    soh.OrderDate,
    per.FirstName || ' ' || per.LastName AS CustomerName,
    p.Name AS ProductName,
    pcat.Name AS Category,
    so.Description AS Promotion,
    so.DiscountPct AS OfferDiscountPct,
    sod.UnitPrice,
    sod.UnitPriceDiscount AS ActualDiscountApplied,
    sod.OrderQty,
    ROUND(sod.LineTotal, 2) AS LineTotal
FROM SalesOrderDetail sod
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN Customer c ON soh.CustomerID = c.CustomerID
LEFT JOIN Person per ON c.PersonID = per.BusinessEntityID
JOIN SpecialOfferProduct sop ON sod.SpecialOfferID = sop.SpecialOfferID
    AND sod.ProductID = sop.ProductID
JOIN SpecialOffer so ON sop.SpecialOfferID = so.SpecialOfferID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
ORDER BY soh.OrderDate DESC, soh.SalesOrderNumber;
```

---

**Q2: "Show each line item with the product name, the salesperson who sold it, their territory, the shipping address city/state/country, the ship method, and the credit card type used."**

*11 joins: SalesOrderDetail → SalesOrderHeader → SalesPerson → Employee → Person(rep) → SalesTerritory → Address(ship) → StateProvince → CountryRegion → ShipMethod → CreditCard*

```sql
SELECT
    soh.SalesOrderNumber,
    p.Name AS ProductName,
    sod.OrderQty,
    ROUND(sod.LineTotal, 2) AS LineTotal,
    rep.FirstName || ' ' || rep.LastName AS SalesPersonName,
    st.Name AS Territory,
    sa.City AS ShipCity,
    sp.Name AS ShipState,
    cr.Name AS ShipCountry,
    sm.Name AS ShipMethod,
    cc.CardType
FROM SalesOrderDetail sod
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN SalesPerson salp ON soh.SalesPersonID = salp.BusinessEntityID
LEFT JOIN Employee e ON salp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person rep ON e.BusinessEntityID = rep.BusinessEntityID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN Address sa ON soh.ShipToAddressID = sa.AddressID
JOIN StateProvince sp ON sa.StateProvinceID = sp.StateProvinceID
JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
LEFT JOIN CreditCard cc ON soh.CreditCardID = cc.CreditCardID
ORDER BY sod.LineTotal DESC;
```

---

**Q3: "For each product sold, show its name, category, model, English description, the total quantity sold and revenue, and compare the selling price to the product's standard cost for margin analysis."**

*8 joins: SalesOrderDetail → Product → ProductSubcategory → ProductCategory → ProductModel → ProductModelProductDescriptionCulture → ProductDescription → Culture*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    pm.Name AS ModelName,
    pd.Description AS ModelDescription,
    p.StandardCost,
    ROUND(AVG(sod.UnitPrice), 2) AS AvgSellingPrice,
    ROUND(AVG(sod.UnitPrice) - p.StandardCost, 2) AS AvgMarginPerUnit,
    SUM(sod.OrderQty) AS TotalQtySold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue,
    ROUND(SUM(sod.LineTotal) - (p.StandardCost * SUM(sod.OrderQty)), 2) AS TotalGrossProfit
FROM SalesOrderDetail sod
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductModel pm ON p.ProductModelID = pm.ProductModelID
LEFT JOIN ProductModelProductDescriptionCulture pmpdc
    ON pm.ProductModelID = pmpdc.ProductModelID
LEFT JOIN ProductDescription pd ON pmpdc.ProductDescriptionID = pd.ProductDescriptionID
LEFT JOIN Culture cu ON pmpdc.CultureID = cu.CultureID AND cu.CultureID = 'en'
GROUP BY p.ProductID, p.Name, pcat.Name, pm.Name, pd.Description, p.StandardCost
ORDER BY TotalRevenue DESC;
```

---

**Q4: "For orders placed by store customers, show the store name, store's assigned salesperson, the products bought, the promotion applied, and the buying reason cited for each order."**

*10 joins: SalesOrderDetail → SalesOrderHeader → Customer → Store → SalesPerson → Employee → Person → SpecialOffer → SalesOrderHeaderSalesReason → SalesReason*

```sql
SELECT
    s.Name AS StoreName,
    rep.FirstName || ' ' || rep.LastName AS StoreSalesPerson,
    soh.SalesOrderNumber,
    p.Name AS ProductName,
    sod.OrderQty,
    ROUND(sod.LineTotal, 2) AS LineTotal,
    so.Description AS Promotion,
    sod.UnitPriceDiscount AS Discount,
    sr.Name AS BuyingReason
FROM SalesOrderDetail sod
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN Customer c ON soh.CustomerID = c.CustomerID
JOIN Store s ON c.StoreID = s.BusinessEntityID
LEFT JOIN SalesPerson sp ON s.SalesPersonID = sp.BusinessEntityID
LEFT JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person rep ON e.BusinessEntityID = rep.BusinessEntityID
JOIN Product p ON sod.ProductID = p.ProductID
JOIN SpecialOfferProduct sop ON sod.SpecialOfferID = sop.SpecialOfferID
    AND sod.ProductID = sop.ProductID
JOIN SpecialOffer so ON sop.SpecialOfferID = so.SpecialOfferID
LEFT JOIN SalesOrderHeaderSalesReason sohsr ON soh.SalesOrderID = sohsr.SalesOrderID
LEFT JOIN SalesReason sr ON sohsr.SalesReasonID = sr.SalesReasonID
ORDER BY s.Name, soh.SalesOrderNumber;
```

---

**Q5: "Show the full product journey for each line item: product name, the vendor who supplied it, purchase cost, the manufacturing cost (from work order routing), and the final selling price and margin — by sales territory."**

*11 joins: SalesOrderDetail → SalesOrderHeader → SalesTerritory → Product → ProductVendor → Vendor → WorkOrder → WorkOrderRouting*

```sql
SELECT
    st.Name AS Territory,
    p.Name AS ProductName,
    v.Name AS Supplier,
    ROUND(AVG(pv.StandardPrice), 2) AS AvgVendorPrice,
    ROUND(AVG(mfg.MfgCostPerUnit), 2) AS AvgMfgCostPerUnit,
    ROUND(AVG(sod.UnitPrice), 2) AS AvgSellingPrice,
    ROUND(AVG(sod.UnitPrice) - COALESCE(AVG(pv.StandardPrice), 0) - COALESCE(AVG(mfg.MfgCostPerUnit), 0), 2) AS EstimatedMarginPerUnit,
    SUM(sod.OrderQty) AS TotalQtySold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue
FROM SalesOrderDetail sod
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN Product p ON sod.ProductID = p.ProductID
LEFT JOIN ProductVendor pv ON p.ProductID = pv.ProductID
LEFT JOIN Vendor v ON pv.BusinessEntityID = v.BusinessEntityID
LEFT JOIN (
    SELECT
        wo.ProductID,
        ROUND(SUM(wor.ActualCost) / NULLIF(SUM(wo.OrderQty), 0), 2) AS MfgCostPerUnit
    FROM WorkOrder wo
    JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
    GROUP BY wo.ProductID
) mfg ON p.ProductID = mfg.ProductID
GROUP BY st.Name, p.Name, v.Name
ORDER BY TotalRevenue DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What are the top 20 best-selling products by revenue, and how much was their revenue impacted by discounts?"**

*Use case: Product performance — revenue and discount impact*

```sql
SELECT
    ProductID,
    SUM(OrderQty) AS TotalQtySold,
    ROUND(SUM(UnitPrice * OrderQty), 2) AS GrossRevenue_BeforeDiscount,
    ROUND(SUM(LineTotal), 2) AS NetRevenue_AfterDiscount,
    ROUND(SUM(UnitPrice * OrderQty) - SUM(LineTotal), 2) AS DiscountAmount,
    ROUND((SUM(UnitPrice * OrderQty) - SUM(LineTotal)) * 100.0
        / NULLIF(SUM(UnitPrice * OrderQty), 0), 2) AS DiscountImpactPct,
    ROUND(AVG(UnitPriceDiscount) * 100, 2) AS AvgDiscountPct,
    COUNT(*) AS LineItemCount
FROM SalesOrderDetail
GROUP BY ProductID
ORDER BY NetRevenue_AfterDiscount DESC
LIMIT 20;
```

---

**Q7: "What's the effectiveness of each special offer — total revenue, units moved, average discount, and number of orders affected?"**

*Use case: Marketing — promotion ROI analysis*

```sql
SELECT
    sod.SpecialOfferID,
    COUNT(*) AS LineItems,
    COUNT(DISTINCT sod.SalesOrderID) AS OrdersAffected,
    SUM(sod.OrderQty) AS TotalUnitsMoved,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue,
    ROUND(AVG(sod.UnitPriceDiscount) * 100, 2) AS AvgDiscountPct,
    ROUND(SUM(sod.UnitPrice * sod.OrderQty) - SUM(sod.LineTotal), 2) AS TotalDiscountGiven,
    ROUND(AVG(sod.LineTotal), 2) AS AvgLineTotal
FROM SalesOrderDetail sod
GROUP BY sod.SpecialOfferID
ORDER BY TotalRevenue DESC;
```

---

**Q8: "What's the average basket size (items per order) and average order revenue? Identify orders with unusually high line item counts."**

*Use case: Sales operations — order complexity analysis*

```sql
WITH OrderBasket AS (
    SELECT
        SalesOrderID,
        COUNT(*) AS LineItems,
        SUM(OrderQty) AS TotalUnits,
        ROUND(SUM(LineTotal), 2) AS OrderRevenue
    FROM SalesOrderDetail
    GROUP BY SalesOrderID
)
SELECT
    ROUND(AVG(LineItems), 1) AS AvgLineItemsPerOrder,
    ROUND(AVG(TotalUnits), 1) AS AvgUnitsPerOrder,
    ROUND(AVG(OrderRevenue), 2) AS AvgOrderRevenue,
    MAX(LineItems) AS MaxLineItems,
    MAX(TotalUnits) AS MaxUnits,
    SUM(CASE WHEN LineItems > 20 THEN 1 ELSE 0 END) AS LargeOrders_Over20Items
FROM OrderBasket;
```

---

**Q9: "What percentage of line items have a carrier tracking number, and what's the revenue split between tracked and untracked shipments?"**

*Use case: Logistics — shipment tracking coverage*

```sql
SELECT
    CASE
        WHEN CarrierTrackingNumber IS NOT NULL THEN 'Tracked'
        ELSE 'Not Tracked'
    END AS TrackingStatus,
    COUNT(*) AS LineItems,
    ROUND(COUNT(*) * 100.0 / (SELECT COUNT(*) FROM SalesOrderDetail), 2) AS PctOfLineItems,
    SUM(OrderQty) AS TotalUnits,
    ROUND(SUM(LineTotal), 2) AS TotalRevenue,
    ROUND(AVG(LineTotal), 2) AS AvgLineTotal
FROM SalesOrderDetail
GROUP BY CASE WHEN CarrierTrackingNumber IS NOT NULL THEN 'Tracked' ELSE 'Not Tracked' END;
```

---

**Q10: "Show the monthly revenue trend from line items, with total units sold, average discount rate, and number of unique products sold per month."**

*Use case: Executive dashboard — monthly sales KPIs*

```sql
SELECT
    strftime('%Y-%m', soh.OrderDate) AS SalesMonth,
    COUNT(*) AS LineItems,
    COUNT(DISTINCT sod.SalesOrderID) AS UniqueOrders,
    COUNT(DISTINCT sod.ProductID) AS UniqueProducts,
    SUM(sod.OrderQty) AS TotalUnitsSold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue,
    ROUND(AVG(sod.UnitPriceDiscount) * 100, 2) AS AvgDiscountPct,
    ROUND(SUM(sod.UnitPrice * sod.OrderQty) - SUM(sod.LineTotal), 2) AS TotalDiscountsGiven,
    ROUND(AVG(sod.LineTotal), 2) AS AvgLineValue
FROM SalesOrderDetail sod
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
GROUP BY strftime('%Y-%m', soh.OrderDate)
ORDER BY SalesMonth;
```

---
