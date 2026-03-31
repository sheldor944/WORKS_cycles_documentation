

# Document

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores internal documents and folder structure — one row per document or folder (13 records). It captures the document identity (Title, FileName, FileExtension, DocumentNode hierarchy), who owns it (Owner → Employee), versioning info (Revision, ChangeNumber, Status), whether it's a folder or file (FolderFlag), and the actual file content (Document as BLOB). Documents are organized in a hierarchical tree via DocumentNode/DocumentLevel, similar to a file system.

### Style 2: Query Possibilities & Business Story
This is the company's internal document management table — technical specs, manuals, maintenance docs, and folders are stored here. It's a small but important table (13 records) that tracks document ownership and versioning. Use this table to answer questions like:

- "What documents does a specific employee own?"
- "Which documents have been revised the most times?"
- "What file types (extensions) are stored in the system?"
- "What's the folder vs. file breakdown?"
- "Which documents are currently in draft vs. final status?"
- "What is the document hierarchy — which folders contain which files?"
- "Which products are associated with which documents?" (with ProductDocument)
- "Which employee in which department owns the most documents?" (with Employee, EmployeeDepartmentHistory, Department)
- "Are there any documents that haven't been updated in over a year?"
- "What's the distribution of documents across hierarchy levels?"

Each document is owned by an employee and can optionally be linked to products via ProductDocument. The hierarchical structure (DocumentNode/Level) allows tree traversal queries similar to an org chart or folder explorer.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per document or folder (13 rows), containing 14 columns organized as:

- **Identifiers:** DocumentNode (PK, hierarchy path), DocumentLevel (depth in tree), rowguid
- **Content:** Title, FileName, FileExtension, Document (BLOB — actual file), DocumentSummary
- **Hierarchy/Type:** FolderFlag (1=folder, 0=file), DocumentNode + DocumentLevel (unique together)
- **Ownership:** Owner (FK → Employee)
- **Versioning:** Revision (version label), ChangeNumber (incremental edit count), Status (1=Pending, 2=Approved, 3=Obsolete)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

Document is a lightweight document management system embedded in the database. With only 13 records, it stores a small set of critical internal documents — likely product specifications, maintenance guides, manufacturing instructions, and supporting materials. The table uses a hierarchical node structure (similar to the Employee OrganizationNode) to represent a folder tree, where folders (FolderFlag=1) contain files (FolderFlag=0) at various nesting depths.

Every document has an owner (an Employee), version tracking via Revision and ChangeNumber, and a workflow Status indicating whether the document is pending approval, finalized, or obsolete. The actual file content is stored as a BLOB, while metadata (name, extension, summary) enables searchability without loading file content.

### Key Business Logic

- **DocumentNode** encodes position in the hierarchy tree (e.g., "/1/", "/1/2/", "/1/2/1/") — similar to a materialized path pattern
- **DocumentLevel** = depth in the tree (0 = root, 1 = first level folders/files, etc.)
- **FolderFlag = 1** → it's a folder (container); **0** → it's an actual file/document
- **Status** likely maps to: 1 = Pending/Draft, 2 = Approved/Active, 3 = Obsolete
- **ChangeNumber** increments with each edit — a quick way to see how many times a doc has been modified
- **Revision** is a human-readable version string (e.g., "1.0", "2.1")
- **Document (BLOB)** stores the actual file content — could be PDF, DOC, etc., determined by FileExtension

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | Employee → Person → BusinessEntity | Owner | Employee who owns/maintains the document |
| ↓ Child | ProductDocument | DocumentNode | Links documents to products (32 links) |
| ← Via ProductDocument | Product | ProductID | Which products this document relates to |
| Self-referencing | Document | DocumentNode hierarchy | Parent-child folder/file structure |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each document, show the title, file name, owner's full name, owner's email, owner's job title, their current department, and the department group."**

*7 joins: Document → Employee → Person → EmailAddress → EmployeeDepartmentHistory → Department*

```sql
SELECT
    doc.Title,
    doc.FileName,
    doc.FileExtension,
    doc.Status,
    p.FirstName || ' ' || p.LastName AS OwnerName,
    ea.EmailAddress AS OwnerEmail,
    e.JobTitle AS OwnerJobTitle,
    d.Name AS Department,
    d.GroupName AS DepartmentGroup
FROM Document doc
JOIN Employee e ON doc.Owner = e.BusinessEntityID
JOIN Person p ON e.BusinessEntityID = p.BusinessEntityID
LEFT JOIN EmailAddress ea ON e.BusinessEntityID = ea.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
ORDER BY doc.Title;
```

---

**Q2: "Show each document with its linked product names, product categories, product list price, and the owner's name and territory — if the owner is also a salesperson."**

*9 joins: Document → ProductDocument → Product → ProductSubcategory → ProductCategory → Employee → Person → SalesPerson → SalesTerritory*

```sql
SELECT
    doc.Title AS DocumentTitle,
    doc.FileName,
    p.Name AS ProductName,
    pcat.Name AS Category,
    p.ListPrice,
    per.FirstName || ' ' || per.LastName AS OwnerName,
    e.JobTitle,
    st.Name AS SalesTerritory
FROM Document doc
JOIN ProductDocument pd ON doc.DocumentNode = pd.DocumentNode
JOIN Product p ON pd.ProductID = p.ProductID
LEFT JOIN ProductSubcategory psub ON p.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
JOIN Employee e ON doc.Owner = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
LEFT JOIN SalesPerson sp ON e.BusinessEntityID = sp.BusinessEntityID
LEFT JOIN SalesTerritory st ON sp.TerritoryID = st.TerritoryID
ORDER BY doc.Title, p.Name;
```

---

**Q3: "For each document linked to a product, show the document title, product name, the vendors who supply that product, vendor credit rating, and the owner's home city/state."**

*10 joins: Document → ProductDocument → Product → ProductVendor → Vendor → Employee → Person → BusinessEntityAddress → Address → StateProvince*

```sql
SELECT
    doc.Title AS DocumentTitle,
    doc.FileExtension,
    p.Name AS ProductName,
    v.Name AS VendorName,
    v.CreditRating,
    per.FirstName || ' ' || per.LastName AS OwnerName,
    a.City AS OwnerCity,
    sp.Name AS OwnerState
FROM Document doc
JOIN ProductDocument pd ON doc.DocumentNode = pd.DocumentNode
JOIN Product p ON pd.ProductID = p.ProductID
JOIN ProductVendor pv ON p.ProductID = pv.ProductID
JOIN Vendor v ON pv.BusinessEntityID = v.BusinessEntityID
JOIN Employee e ON doc.Owner = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN BusinessEntityAddress bea ON e.BusinessEntityID = bea.BusinessEntityID
JOIN Address a ON bea.AddressID = a.AddressID
JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
ORDER BY doc.Title;
```

---

**Q4: "List documents whose linked products have active work orders, showing the document title, product name, work order quantity, manufacturing location, and the document owner's pay rate."**

*9 joins: Document → ProductDocument → Product → WorkOrder → WorkOrderRouting → Location → Employee → EmployeePayHistory*

```sql
SELECT
    doc.Title AS DocumentTitle,
    p.Name AS ProductName,
    wo.OrderQty,
    wo.StartDate AS WorkOrderStart,
    loc.Name AS ManufacturingLocation,
    per.FirstName || ' ' || per.LastName AS OwnerName,
    eph.Rate AS OwnerPayRate
FROM Document doc
JOIN ProductDocument pd ON doc.DocumentNode = pd.DocumentNode
JOIN Product p ON pd.ProductID = p.ProductID
JOIN WorkOrder wo ON p.ProductID = wo.ProductID
    AND wo.EndDate IS NULL
JOIN WorkOrderRouting wor ON wo.WorkOrderID = wor.WorkOrderID
JOIN Location loc ON wor.LocationID = loc.LocationID
JOIN Employee e ON doc.Owner = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate = (
        SELECT MAX(eph2.RateChangeDate)
        FROM EmployeePayHistory eph2
        WHERE eph2.BusinessEntityID = e.BusinessEntityID
    )
ORDER BY wo.OrderQty DESC;
```

---

**Q5: "Show documents alongside their linked products' sales performance — total revenue, total orders, and the top territory — plus the document owner's department and shift."**

*10 joins: Document → ProductDocument → Product → SalesOrderDetail → SalesOrderHeader → SalesTerritory → Employee → EmployeeDepartmentHistory → Department → Shift*

```sql
SELECT
    doc.Title AS DocumentTitle,
    p.Name AS ProductName,
    st.Name AS TopTerritory,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(sod.LineTotal), 2) AS TotalRevenue,
    per.FirstName || ' ' || per.LastName AS OwnerName,
    d.Name AS OwnerDepartment,
    sh.Name AS OwnerShift
FROM Document doc
JOIN ProductDocument pd ON doc.DocumentNode = pd.DocumentNode
JOIN Product p ON pd.ProductID = p.ProductID
JOIN SalesOrderDetail sod ON p.ProductID = sod.ProductID
JOIN SalesOrderHeader soh ON sod.SalesOrderID = soh.SalesOrderID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
JOIN Employee e ON doc.Owner = e.BusinessEntityID
JOIN Person per ON e.BusinessEntityID = per.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN Shift sh ON edh.ShiftID = sh.ShiftID
GROUP BY doc.Title, p.Name, st.Name, per.FirstName, per.LastName, d.Name, sh.Name
ORDER BY TotalRevenue DESC;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What is the breakdown of documents by status — how many are pending, approved, or obsolete?"**

*Use case: Document compliance / review pipeline*

```sql
SELECT
    CASE Status
        WHEN 1 THEN 'Pending/Draft'
        WHEN 2 THEN 'Approved/Active'
        WHEN 3 THEN 'Obsolete'
        ELSE 'Unknown (' || Status || ')'
    END AS StatusLabel,
    COUNT(*) AS DocCount,
    SUM(CASE WHEN FolderFlag = 0 THEN 1 ELSE 0 END) AS Files,
    SUM(CASE WHEN FolderFlag = 1 THEN 1 ELSE 0 END) AS Folders,
    GROUP_CONCAT(Title, ', ') AS DocumentTitles
FROM Document
GROUP BY Status
ORDER BY Status;
```

---

**Q7: "Which documents have been changed the most times, and when were they last modified?"**

*Use case: Identifying frequently revised documents for stability review*

```sql
SELECT
    Title,
    FileName,
    FileExtension,
    Revision,
    ChangeNumber,
    Status,
    ModifiedDate,
    DocumentSummary
FROM Document
WHERE FolderFlag = 0
ORDER BY ChangeNumber DESC;
```

---

**Q8: "Show the folder/file hierarchy — which folders exist and what files are under them?"**

*Use case: Document repository navigation / audit*

```sql
SELECT
    d.DocumentNode,
    d.DocumentLevel,
    CASE WHEN d.FolderFlag = 1 THEN '📁 Folder' ELSE '📄 File' END AS NodeType,
    d.Title,
    d.FileName,
    d.FileExtension,
    d.Status,
    parent.Title AS ParentFolder
FROM Document d
LEFT JOIN Document parent
    ON d.DocumentLevel = parent.DocumentLevel + 1
    AND d.DocumentNode LIKE parent.DocumentNode || '%'
    AND parent.FolderFlag = 1
ORDER BY d.DocumentNode;
```

---

**Q9: "Which file types (extensions) are in the system, and what's the average number of revisions per type?"**

*Use case: IT / content management — file type analysis*

```sql
SELECT
    FileExtension,
    COUNT(*) AS FileCount,
    ROUND(AVG(ChangeNumber), 1) AS AvgChanges,
    MAX(ChangeNumber) AS MaxChanges,
    GROUP_CONCAT(Title, ', ') AS Files
FROM Document
WHERE FolderFlag = 0
GROUP BY FileExtension
ORDER BY FileCount DESC;
```

---

**Q10: "Which employees own documents, and how many documents does each own? Are there any employees owning obsolete documents?"**

*Use case: Document ownership audit / housekeeping*

```sql
SELECT
    doc.Owner AS EmployeeID,
    COUNT(*) AS TotalDocsOwned,
    SUM(CASE WHEN doc.FolderFlag = 0 THEN 1 ELSE 0 END) AS FilesOwned,
    SUM(CASE WHEN doc.FolderFlag = 1 THEN 1 ELSE 0 END) AS FoldersOwned,
    SUM(CASE WHEN doc.Status = 3 THEN 1 ELSE 0 END) AS ObsoleteDocs,
    SUM(CASE WHEN doc.Status = 1 THEN 1 ELSE 0 END) AS PendingDocs,
    MAX(doc.ModifiedDate) AS LastDocModified
FROM Document doc
GROUP BY doc.Owner
ORDER BY TotalDocsOwned DESC;
```

---
