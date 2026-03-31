# Product

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores the product catalog — one row per product (504 products). It captures what the product is (Name, ProductNumber, Color, Size, Weight), how it's classified (ProductLine, Class, Style, ProductSubcategoryID, ProductModelID), its cost and pricing (StandardCost, ListPrice), manufacturing details (MakeFlag, FinishedGoodsFlag, DaysToManufacture), inventory thresholds (SafetyStockLevel, ReorderPoint), and its sales lifecycle (SellStartDate, SellEndDate, DiscontinuedDate). Products can be manufactured in-house or purchased externally (MakeFlag), and can be finished goods or raw components (FinishedGoodsFlag).

### Style 2: Query Possibilities & Business Story
This is the master product table — every item the company sells, manufactures, or stocks lives here. Use this table to answer questions like:

- "How many products are currently active (not discontinued)?"
- "What's the average list price by product line or class?"
- "Which products have the highest markup (ListPrice vs. StandardCost)?"
- "How many products are manufactured in-house vs. purchased from vendors?"
- "Which products take the longest to manufacture?"
- "What colors are available across the product catalog?"
- "Which products have fallen below their safety stock level?" (with ProductInventory)
- "What's the revenue breakdown by product category?" (with SalesOrderDetail)
- "Which product models have the most variants?"
- "List all products that have been discontinued but were still selling last year."
- "Which products have no subcategory assigned?"
- "What's the price distribution of finished goods vs. raw components?"

Each product optionally links to a subcategory (→ category), a product model, and unit measures for size and weight — making it the central node of the entire product domain. It feeds into sales (SalesOrderDetail), purchasing (PurchaseOrderDetail), manufacturing (WorkOrder), inventory (ProductInventory), and bill of materials (BillOfMaterials).

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per product (504 rows), containing 25 columns organized as:

- **Identifiers:** ProductID (PK), Name, ProductNumber, rowguid
- **Classification:** ProductLine (R/M/T/S), Class (H/M/L), Style (W/M/U), ProductSubcategoryID, ProductModelID
- **Physical Attributes:** Color, Size, SizeUnitMeasureCode, Weight, WeightUnitMeasureCode
- **Cost & Pricing:** StandardCost, ListPrice
- **Manufacturing:** MakeFlag (1=made in-house, 0=purchased), FinishedGoodsFlag (1=sellable, 0=component), DaysToManufacture
- **Inventory Thresholds:** SafetyStockLevel, ReorderPoint
- **Lifecycle Dates:** SellStartDate, SellEndDate, DiscontinuedDate
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

Product is the master catalog of everything the company deals with — 504 items ranging from finished bicycles and apparel to raw components like bolts and tubing. It serves as the central reference point across all domains: sales teams sell products, purchasing teams buy components, manufacturing builds assemblies, and warehouses stock inventory. The table is rich with classification, pricing, physical, and lifecycle data that supports analytics across the entire value chain.

### Key Business Logic

- **MakeFlag = 1** → manufactured in-house (linked to WorkOrder); **MakeFlag = 0** → purchased from vendors (linked to ProductVendor/PurchaseOrder)
- **FinishedGoodsFlag = 1** → sellable end-product; **FinishedGoodsFlag = 0** → raw material / component used in assemblies
- **SellEndDate IS NULL** → product is currently active; **NOT NULL** → retired from sale
- **DiscontinuedDate** → permanently pulled from catalog
- **Markup** = ListPrice - StandardCost → profit margin indicator
- **ProductSubcategoryID IS NULL** → uncategorized products (typically raw components)

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | ProductSubcategory → ProductCategory | ProductSubcategoryID | Product hierarchy (nullable) |
| → Parent | ProductModel | ProductModelID | Design/model grouping (nullable) |
| → Parent | UnitMeasure (size) | SizeUnitMeasureCode | Size unit (CM, IN, etc.) |
| → Parent | UnitMeasure (weight) | WeightUnitMeasureCode | Weight unit (LB, KG, etc.) |
| ↓ Child | SalesOrderDetail | ProductID | What was sold |
| ↓ Child | PurchaseOrderDetail | ProductID | What was purchased |
| ↓ Child | WorkOrder | ProductID | What was manufactured |
| ↓ Child | WorkOrderRouting | ProductID | Manufacturing route steps |
| ↓ Child | ProductInventory | ProductID | Stock levels by location |
| ↓ Child | BillOfMaterials | ProductAssemblyID / ComponentID | Assembly ↔ component (self-ref) |
| ↓ Child | ProductCostHistory | ProductID | Cost changes over time |
| ↓ Child | ProductListPriceHistory | ProductID | Price changes over time |
| ↓ Child | ProductVendor | ProductID | Which vendors supply it |
| ↓ Child | ProductDocument | ProductID | Technical documents |
| ↓ Child | ProductProductPhoto | ProductID | Product images |
| ↓ Child | ProductReview | ProductID | Customer reviews |
| ↓ Child | SpecialOfferProduct | ProductID | Promotions/discounts |
| ↓ Child | TransactionHistory | ProductID | Transaction audit trail |
| ↓ Child | ShoppingCartItem | ProductID | Active carts |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each product, show its name, subcategory, category, model name, model description in English, list price, and standard cost."**

*7 joins: Product → ProductSubcategory → ProductCategory → ProductModel → PMPDC → ProductDescription → Culture*

```sql
SELECT
    p.Name AS ProductName,
    p.ListPrice,
    p.StandardCost,
    psub.Name AS Subcategory,
    pcat.Name AS Category,
    pm.Name AS ModelName,
    pd.Description AS ModelDescription
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductModel pm ON p.ProductModelID = pm.ProductModelID
LEFT JOIN ProductModelProductDescriptionCulture pmpdc
    ON pm.ProductModelID = pmpdc.ProductModelID
LEFT JOIN ProductDescription pd ON pmpdc.ProductDescriptionID = pd.ProductDescriptionID
LEFT JOIN Culture cu ON pmpdc.CultureID = cu.CultureID
    AND cu.CultureID = 'en';
```

---

**Q2: "Show each product with its total sales revenue, total quantity sold, the territories where it was sold, and the ship method used for delivery."**

*6 joins: Product → SalesOrderDetail → SalesOrderHeader → SalesTerritory → ShipMethod, plus SpecialOfferProduct*

```sql
SELECT
    p.Name AS ProductName,
    p.ProductNumber,
    st.Name AS Territory,
    sm.Name AS ShipMethod,
    SUM(sod.OrderQty) AS TotalQtySold,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue
FROM Product p
JOIN SalesOrderDetail sod ON p.ProductID = sod.ProductID
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN ShipMethod sm ON soh.ShipMethodID = sm.ShipMethodID
GROUP BY p.Name, p.ProductNumber, st.Name, sm.Name
ORDER BY TotalRevenue DESC;
```

---

**Q3: "For in-house manufactured products, show the product name, category, total work orders, total scrapped quantity, scrap reason, and the manufacturing locations used."**

*7 joins: Product → ProductSubcategory → ProductCategory → WorkOrder → ScrapReason → WorkOrderRouting → Location*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    COUNT(DISTINCT wo.WorkOrderID) AS TotalWorkOrders,
    SUM(wo.ScrappedQty) AS TotalScrapped,
    sr.Name AS ScrapReason,
    loc.Name AS ManufacturingLocation,
    ROUND(SUM(wor.ActualCost), 2) AS TotalMfgCost
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN WorkOrder wo ON p.ProductID = wo.ProductID
LEFT JOIN ScrapReason sr ON wo.ScrapReasonID = sr.ScrapReasonID
JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
    AND p.ProductID = wor.ProductID
JOIN Location loc ON wor.LocationID = loc.LocationID
WHERE p.MakeFlag = 1
GROUP BY p.Name, pcat.Name, sr.Name, loc.Name
ORDER BY TotalScrapped DESC;
```

---

**Q4: "For each product, show its vendors, vendor credit rating, average lead time, the purchase order count, and total quantity purchased — alongside the product's category."**

*6 joins: Product → ProductSubcategory → ProductCategory → ProductVendor → Vendor → PurchaseOrderDetail → PurchaseOrderHeader*

```sql
SELECT
    p.Name AS ProductName,
    pcat.Name AS Category,
    v.Name AS VendorName,
    v.CreditRating,
    pv.AverageLeadTime,
    COUNT(DISTINCT poh.PurchaseOrderID) AS POCount,
    SUM(pod.OrderQty) AS TotalQtyPurchased,
    ROUND(SUM(pod.LineTotal), 2) AS TotalPurchaseCost
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN ProductVendor pv ON p.ProductID = pv.ProductID
JOIN Vendor v ON pv.BusinessEntityID = v.BusinessEntityID
JOIN PurchaseOrderDetail pod ON p.ProductID = pod.ProductID
JOIN PurchaseOrderHeader poh ON pod.PurchaseOrderID = poh.PurchaseOrderID
GROUP BY p.Name, pcat.Name, v.Name, v.CreditRating, pv.AverageLeadTime
ORDER BY TotalPurchaseCost DESC;
```

---

**Q5: "Show each product's name, category, current inventory quantity by location, the bill of materials components it uses, and the unit of measure for each component."**

*7 joins: Product → ProductSubcategory → ProductCategory → ProductInventory → Location → BillOfMaterials → Product(component) → UnitMeasure*

```sql
SELECT
    p.Name AS AssemblyProduct,
    pcat.Name AS Category,
    loc.Name AS InventoryLocation,
    pi.Quantity AS StockOnHand,
    comp.Name AS ComponentName,
    bom.PerAssemblyQty,
    um.Name AS UnitOfMeasure,
    bom.BOMLevel
FROM Product p
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN ProductInventory pi ON p.ProductID = pi.ProductID
LEFT JOIN Location loc ON pi.LocationID = loc.LocationID
LEFT JOIN BillOfMaterials bom ON p.ProductID = bom.ProductAssemblyID
    AND bom.EndDate IS NULL
LEFT JOIN Product comp ON bom.ComponentID = comp.ProductID
LEFT JOIN UnitMeasure um ON bom.UnitMeasureCode = um.UnitMeasureCode
WHERE p.FinishedGoodsFlag = 1
ORDER BY p.Name, bom.BOMLevel;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the profit margin (ListPrice - StandardCost) for each product, and which products have negative or zero margin?"**

*Use case: Pricing review — identify underpriced products*

```sql
SELECT
    Name,
    ProductNumber,
    StandardCost,
    ListPrice,
    ROUND(ListPrice - StandardCost, 2) AS Margin,
    ROUND((ListPrice - StandardCost) * 100.0 / NULLIF(ListPrice, 0), 2) AS MarginPct,
    CASE
        WHEN ListPrice - StandardCost <= 0 THEN 'NEGATIVE/ZERO MARGIN'
        WHEN (ListPrice - StandardCost) / NULLIF(ListPrice, 0) < 0.1 THEN 'LOW MARGIN (<10%)'
        ELSE 'HEALTHY'
    END AS MarginFlag
FROM Product
WHERE ListPrice > 0
ORDER BY Margin ASC;
```

---

**Q7: "How many products are active vs. discontinued vs. retired from sale, broken down by product line?"**

*Use case: Product lifecycle management*

```sql
SELECT
    COALESCE(ProductLine, 'Unassigned') AS ProductLine,
    COUNT(*) AS TotalProducts,
    SUM(CASE WHEN SellEndDate IS NULL AND DiscontinuedDate IS NULL THEN 1 ELSE 0 END) AS Active,
    SUM(CASE WHEN SellEndDate IS NOT NULL AND DiscontinuedDate IS NULL THEN 1 ELSE 0 END) AS RetiredFromSale,
    SUM(CASE WHEN DiscontinuedDate IS NOT NULL THEN 1 ELSE 0 END) AS Discontinued
FROM Product
GROUP BY ProductLine
ORDER BY TotalProducts DESC;
```

---

**Q8: "Which products are below their reorder point based on current total inventory?"**

*Use case: Inventory replenishment alert*

```sql
SELECT
    p.Name,
    p.ProductNumber,
    p.SafetyStockLevel,
    p.ReorderPoint,
    COALESCE(SUM(pi.Quantity), 0) AS TotalStock,
    CASE
        WHEN COALESCE(SUM(pi.Quantity), 0) <= p.ReorderPoint THEN 'REORDER NOW'
        WHEN COALESCE(SUM(pi.Quantity), 0) <= p.SafetyStockLevel THEN 'LOW STOCK'
        ELSE 'OK'
    END AS StockStatus
FROM Product p
LEFT JOIN ProductInventory pi ON p.ProductID = pi.ProductID
GROUP BY p.ProductID, p.Name, p.ProductNumber, p.SafetyStockLevel, p.ReorderPoint
HAVING COALESCE(SUM(pi.Quantity), 0) <= p.ReorderPoint
ORDER BY TotalStock ASC;
```

---

**Q9: "Compare in-house manufactured products vs. vendor-purchased products: average cost, average list price, average days to manufacture, and count."**

*Use case: Make-vs-buy strategic analysis*

```sql
SELECT
    CASE WHEN MakeFlag = 1 THEN 'Manufactured In-House' ELSE 'Purchased from Vendor' END AS SourceType,
    COUNT(*) AS ProductCount,
    ROUND(AVG(StandardCost), 2) AS AvgCost,
    ROUND(AVG(ListPrice), 2) AS AvgListPrice,
    ROUND(AVG(ListPrice - StandardCost), 2) AS AvgMargin,
    ROUND(AVG(DaysToManufacture), 1) AS AvgDaysToMfg,
    SUM(CASE WHEN FinishedGoodsFlag = 1 THEN 1 ELSE 0 END) AS FinishedGoods,
    SUM(CASE WHEN FinishedGoodsFlag = 0 THEN 1 ELSE 0 END) AS Components
FROM Product
GROUP BY MakeFlag;
```

---

**Q10: "What is the average list price by color, and which colors have the most products? Exclude products with no color."**

*Use case: Merchandising / catalog analysis*

```sql
SELECT
    Color,
    COUNT(*) AS ProductCount,
    ROUND(AVG(ListPrice), 2) AS AvgListPrice,
    ROUND(MIN(ListPrice), 2) AS MinPrice,
    ROUND(MAX(ListPrice), 2) AS MaxPrice,
    SUM(CASE WHEN FinishedGoodsFlag = 1 THEN 1 ELSE 0 END) AS FinishedGoods
FROM Product
WHERE Color IS NOT NULL
GROUP BY Color
ORDER BY ProductCount DESC;
```

---
