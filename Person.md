# Person

---

## 📋 Short Description

### Style 1: Conceptual Summary
This table stores person records — one row per individual (19,972 people). It captures their identity (FirstName, MiddleName, LastName, Title, Suffix), what type of person they are (PersonType — employee, customer, vendor contact, etc.), their marketing preferences (EmailPromotion), and optional extended data (AdditionalContactInfo, Demographics as XML/text). Person sits in the middle of the inheritance chain BusinessEntity → Person → Employee, and is the central people table that virtually every other domain references.

### Style 2: Query Possibilities & Business Story
This is the master people table — every individual the company interacts with lives here: employees, individual customers, store contacts, vendor contacts. It provides the name and identity layer on top of BusinessEntity. Use this table to answer questions like:

- "How many people are in the system by type (employee, customer, vendor contact, etc.)?"
- "What is the full name of a specific employee or customer?"
- "How many people have opted into email promotions?"
- "What's the breakdown of people by PersonType?"
- "Which people have a title (Mr., Ms., Dr.) and which don't?"
- "How many people share the same last name?"
- "Who are the individual customers vs. store-associated customers?"
- "Which vendor contacts are in the system?" (with BusinessEntityContact, Vendor)
- "What's the full profile of a person — name, email, phone, address, credit card?" (with EmailAddress, PersonPhone, BusinessEntityAddress, PersonCreditCard)
- "List all employees with their full names and job titles." (with Employee)
- "Which salesperson has which full name and what territory?" (with SalesPerson, SalesTerritory)
- "Find customers by name who placed orders above a certain value." (with Customer, SalesOrderHeader)

Person connects upward to BusinessEntity (for addresses, contacts) and downward/laterally to Employee, Customer, EmailAddress, Password, PersonCreditCard, and BusinessEntityContact — making it the identity hub for all people-related queries.

### Style 3: Grouped & Complete (Column Reference)
This table stores one row per person (19,972 rows), containing 13 columns organized as:

- **Identifiers:** BusinessEntityID (PK, FK → BusinessEntity), rowguid
- **Person Type:** PersonType (SC=Store Contact, IN=Individual Customer, SP=Sales Person, EM=Employee, VC=Vendor Contact, GC=General Contact)
- **Name:** Title (Mr./Ms./Dr. etc., nullable), FirstName, MiddleName (nullable), LastName, Suffix (Jr./Sr. etc., nullable)
- **Name Format:** NameStyle (0=Western "First Last", 1=Eastern "Last First")
- **Marketing:** EmailPromotion (0=no emails, 1=from AdventureWorks, 2=from AdventureWorks+partners)
- **Extended Data:** AdditionalContactInfo (XML/text, nullable), Demographics (XML/text — income, education, etc., nullable)
- **Audit:** ModifiedDate

---

## 📖 Extensive Description

### Purpose & Business Context

Person is the single largest people table in the database (19,972 rows) and serves as the universal identity layer for every individual — employees, customers, vendor contacts, store contacts, and general contacts. It inherits from BusinessEntity (which provides a universal ID and links to addresses/contacts) and is itself extended by Employee (for work-specific data) and referenced by Customer (for purchasing behavior).

The PersonType discriminator is critical — it tells you what role this person plays:
- **EM** (Employee) — 290 employees, extended in Employee table
- **SP** (Sales Person) — subset of employees who sell, extended in SalesPerson
- **IN** (Individual Customer) — direct-to-consumer buyers
- **SC** (Store Contact) — people associated with retail stores
- **VC** (Vendor Contact) — people at supplier companies
- **GC** (General Contact) — other contacts

The Demographics column (XML/text) can contain rich demographic data like income level, education, home ownership, commute distance, etc. — valuable for customer segmentation but requires parsing.

### Key Business Logic

- **BusinessEntityID** is both PK and FK — it doesn't auto-generate here; it inherits the ID from BusinessEntity
- **PersonType** determines how this person is used across the system and which child tables apply
- **EmailPromotion** drives marketing opt-in: 0 = no contact, 1 = company emails only, 2 = company + partner emails
- **NameStyle = 0** → Western format (FirstName LastName); **1** → Eastern format (LastName FirstName)
- **Demographics** is stored as XML/text — contains structured demographic attributes that can be parsed for analytics
- **AdditionalContactInfo** is stored as XML/text — extra phone numbers, email aliases, etc.
- Not every BusinessEntity is a Person (20,777 entities vs. 19,972 persons) — the gap (~805) represents Stores, Vendors, and other non-person entities

### Relationships

| Direction | Table | Join Key | Notes |
|-----------|-------|----------|-------|
| → Parent | BusinessEntity | BusinessEntityID | Universal root entity (addresses, contacts) |
| ↓ Child/Extension | Employee | BusinessEntityID | 290 persons are employees |
| ↓ Child/Extension | Customer (via PersonID) | BusinessEntityID | Individual customers |
| ↓ Child | EmailAddress | BusinessEntityID | Email addresses (1:many) |
| ↓ Child | Password | BusinessEntityID | Login credentials (1:1) |
| ↓ Child | PersonCreditCard → CreditCard | BusinessEntityID | Payment cards (many:many) |
| ← Via BusinessEntity | BusinessEntityAddress → Address → StateProvince | BusinessEntityID | Person's addresses |
| ← Via BusinessEntity | BusinessEntityContact → ContactType | PersonID | Person as a contact for a business entity |
| ↓ Via Employee | EmployeeDepartmentHistory → Department, Shift | BusinessEntityID | Department assignments |
| ↓ Via Employee | EmployeePayHistory | BusinessEntityID | Pay rate history |
| ↓ Via Employee → SalesPerson | SalesOrderHeader | SalesPersonID | Orders sold by this person |
| ↓ Via Customer | SalesOrderHeader | CustomerID → PersonID | Orders placed by this person |

---

## 🔗 10 NL → SQL Examples

### Join-Heavy Queries (5)

---

**Q1: "For each person, show their full name, person type, email, home address (city, state, country), and address type — covering all people in the system."**

*7 joins: Person → EmailAddress → BusinessEntityAddress → AddressType → Address → StateProvince → CountryRegion*

```sql
SELECT
    p.PersonType,
    p.Title,
    p.FirstName || ' ' || COALESCE(p.MiddleName || ' ', '') || p.LastName AS FullName,
    p.Suffix,
    ea.EmailAddress,
    at.Name AS AddressType,
    a.City,
    sp.Name AS StateName,
    cr.Name AS Country
FROM Person p
LEFT JOIN EmailAddress ea ON p.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON p.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN AddressType at ON bea.AddressTypeID = at.AddressTypeID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
ORDER BY p.LastName, p.FirstName;
```

---

**Q2: "For every employee-type person, show their full name, job title, department, shift, current pay rate, email, and the credit card types they have on file."**

*9 joins: Person → Employee → EmployeeDepartmentHistory → Department → Shift → EmployeePayHistory → EmailAddress → PersonCreditCard → CreditCard*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS FullName,
    e.JobTitle,
    d.Name AS Department,
    sh.Name AS Shift,
    eph.Rate AS CurrentPayRate,
    ea.EmailAddress,
    cc.CardType,
    cc.ExpYear AS CardExpYear
FROM Person p
JOIN Employee e ON p.BusinessEntityID = e.BusinessEntityID
JOIN EmployeeDepartmentHistory edh ON e.BusinessEntityID = edh.BusinessEntityID
    AND edh.EndDate IS NULL
JOIN Department d ON edh.DepartmentID = d.DepartmentID
JOIN Shift sh ON edh.ShiftID = sh.ShiftID
JOIN EmployeePayHistory eph ON e.BusinessEntityID = eph.BusinessEntityID
    AND eph.RateChangeDate = (
        SELECT MAX(eph2.RateChangeDate)
        FROM EmployeePayHistory eph2
        WHERE eph2.BusinessEntityID = e.BusinessEntityID
    )
LEFT JOIN EmailAddress ea ON p.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN PersonCreditCard pcc ON p.BusinessEntityID = pcc.BusinessEntityID
LEFT JOIN CreditCard cc ON pcc.CreditCardID = cc.CreditCardID
WHERE p.PersonType = 'EM'
ORDER BY p.LastName;
```

---

**Q3: "For individual customers (PersonType = 'IN'), show their full name, email, address, the total number of orders they've placed, total revenue, and the territories they've ordered from."**

*9 joins: Person → Customer → SalesOrderHeader → SalesTerritory → EmailAddress → BusinessEntityAddress → Address → StateProvince → CountryRegion*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS CustomerName,
    ea.EmailAddress,
    a.City,
    sp.Name AS StateName,
    cr.Name AS Country,
    st.Name AS SalesTerritory,
    COUNT(DISTINCT soh.SalesOrderID) AS TotalOrders,
    ROUND(SUM(soh.TotalDue), 2) AS TotalRevenue
FROM Person p
JOIN Customer c ON p.BusinessEntityID = c.PersonID
JOIN SalesOrderHeader soh ON c.CustomerID = soh.CustomerID
JOIN SalesTerritory st ON soh.TerritoryID = st.TerritoryID
LEFT JOIN EmailAddress ea ON p.BusinessEntityID = ea.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON p.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince sp ON a.StateProvinceID = sp.StateProvinceID
LEFT JOIN CountryRegion cr ON sp.CountryRegionCode = cr.CountryRegionCode
WHERE p.PersonType = 'IN'
GROUP BY p.FirstName, p.LastName, ea.EmailAddress, a.City, sp.Name, cr.Name, st.Name
ORDER BY TotalRevenue DESC;
```

---

**Q4: "For store contacts (PersonType = 'SC'), show their name, the store they're associated with, the store's salesperson name, the contact type (role), and the store's address."**

*10 joins: Person → BusinessEntityContact → ContactType → Store → SalesPerson → Employee → Person(salesperson) → BusinessEntityAddress → Address → StateProvince*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS ContactName,
    ct.Name AS ContactRole,
    s.Name AS StoreName,
    sp_person.FirstName || ' ' || sp_person.LastName AS AssignedSalesPersonName,
    a.City AS StoreCity,
    spr.Name AS StoreState
FROM Person p
JOIN BusinessEntityContact bec ON p.BusinessEntityID = bec.PersonID
JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
JOIN Store s ON bec.BusinessEntityID = s.BusinessEntityID
LEFT JOIN SalesPerson sp ON s.SalesPersonID = sp.BusinessEntityID
LEFT JOIN Employee e ON sp.BusinessEntityID = e.BusinessEntityID
LEFT JOIN Person sp_person ON e.BusinessEntityID = sp_person.BusinessEntityID
LEFT JOIN BusinessEntityAddress bea ON s.BusinessEntityID = bea.BusinessEntityID
LEFT JOIN Address a ON bea.AddressID = a.AddressID
LEFT JOIN StateProvince spr ON a.StateProvinceID = spr.StateProvinceID
WHERE p.PersonType = 'SC'
ORDER BY s.Name, ct.Name;
```

---

**Q5: "For vendor contacts (PersonType = 'VC'), show their name, contact role, vendor name, vendor credit rating, the products the vendor supplies, product categories, and the total PO spend with that vendor."**

*11 joins: Person → BusinessEntityContact → ContactType → Vendor → ProductVendor → Product → ProductSubcategory → ProductCategory → PurchaseOrderHeader*

```sql
SELECT
    p.FirstName || ' ' || p.LastName AS VendorContactName,
    ct.Name AS ContactRole,
    v.Name AS VendorName,
    v.CreditRating,
    prod.Name AS ProductSupplied,
    pcat.Name AS ProductCategory,
    COALESCE(po_summary.TotalPOs, 0) AS TotalPOs,
    COALESCE(po_summary.TotalSpend, 0) AS TotalSpend
FROM Person p
JOIN BusinessEntityContact bec ON p.BusinessEntityID = bec.PersonID
JOIN ContactType ct ON bec.ContactTypeID = ct.ContactTypeID
JOIN Vendor v ON bec.BusinessEntityID = v.BusinessEntityID
LEFT JOIN ProductVendor pv ON v.BusinessEntityID = pv.BusinessEntityID
LEFT JOIN Product prod ON pv.ProductID = prod.ProductID
LEFT JOIN ProductSubcategory psub ON prod.ProductSubcategoryID = psub.ProductSubcategoryID
LEFT JOIN ProductCategory pcat ON psub.ProductCategoryID = pcat.ProductCategoryID
LEFT JOIN (
    SELECT
        VendorID,
        COUNT(*) AS TotalPOs,
        ROUND(SUM(TotalDue), 2) AS TotalSpend
    FROM PurchaseOrderHeader
    GROUP BY VendorID
) po_summary ON v.BusinessEntityID = po_summary.VendorID
WHERE p.PersonType = 'VC'
ORDER BY v.Name, p.LastName;
```

---

### Practical Business Use-Case Queries (5)

---

**Q6: "What's the breakdown of people by PersonType?"**

*Use case: Data inventory — understanding who's in the system*

```sql
SELECT
    PersonType,
    CASE PersonType
        WHEN 'EM' THEN 'Employee'
        WHEN 'SP' THEN 'Sales Person'
        WHEN 'IN' THEN 'Individual Customer'
        WHEN 'SC' THEN 'Store Contact'
        WHEN 'VC' THEN 'Vendor Contact'
        WHEN 'GC' THEN 'General Contact'
        ELSE 'Unknown'
    END AS PersonTypeLabel,
    COUNT(*) AS PersonCount,
    SUM(CASE WHEN Title IS NOT NULL THEN 1 ELSE 0 END) AS WithTitle,
    SUM(CASE WHEN MiddleName IS NOT NULL THEN 1 ELSE 0 END) AS WithMiddleName,
    SUM(CASE WHEN Suffix IS NOT NULL THEN 1 ELSE 0 END) AS WithSuffix
FROM Person
GROUP BY PersonType
ORDER BY PersonCount DESC;
```

---

**Q7: "How many people have opted in to each level of email promotion, and what's the distribution by person type?"**

*Use case: Marketing — email campaign targeting*

```sql
SELECT
    PersonType,
    CASE EmailPromotion
        WHEN 0 THEN 'No Emails'
        WHEN 1 THEN 'AdventureWorks Only'
        WHEN 2 THEN 'AW + Partners'
    END AS EmailOptIn,
    COUNT(*) AS PersonCount,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY PersonType), 1) AS PctWithinType
FROM Person
GROUP BY PersonType, EmailPromotion
ORDER BY PersonType, EmailPromotion;
```

---

**Q8: "What are the most common last names in the system, and what person types do they span?"**

*Use case: Data quality / deduplication investigation*

```sql
SELECT
    LastName,
    COUNT(*) AS Occurrences,
    COUNT(DISTINCT PersonType) AS PersonTypesSpanned,
    GROUP_CONCAT(DISTINCT PersonType) AS PersonTypes,
    COUNT(DISTINCT FirstName) AS UniqueFirstNames
FROM Person
GROUP BY LastName
HAVING COUNT(*) > 5
ORDER BY Occurrences DESC
LIMIT 20;
```

---


---
