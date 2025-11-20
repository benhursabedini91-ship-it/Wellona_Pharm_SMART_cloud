# 📋 eFaktura API - Endpoint-e të Dobishme

**Data**: 2025-11-18  
**API Base**: https://efaktura.mfin.gov.rs/api/publicApi

---

## ✅ ENDPOINT-E QË FUNKSIONOJNË

### 1. **`POST /purchase-invoice/ids`** ⭐⭐⭐⭐⭐
**Përdorimi**: Merr listën e invoice ID-ve në një periudhë  
**Limiti**: **50 faktura MAKSIMUM** (hard limit)  
**Request**:
```json
{
  "dateFrom": "2025-11-01",
  "dateTo": "2025-11-18"
}
```
**Response**:
```json
{
  "PurchaseInvoiceIds": [354107373, 354301027, ...]
}
```
**Status**: ✅ FUNKSIONON - Por 50-invoice limit absolut

---

### 2. **`GET /purchase-invoice/xml`** ⭐⭐⭐⭐⭐
**Përdorimi**: Download UBL XML për 1 fakturë  
**Params**: `?invoiceId=354107373`  
**Response**: UBL 2.1 XML FileStream  
**Status**: ✅ FUNKSIONON PERFEKT - 50 XML të shkarkuara

---

### 3. **`GET /purchase-invoice`** ⭐⭐⭐⭐
**Përdorimi**: Merr **PurchaseInvoiceDto** (metadata e plotë)  
**Params**: `?invoiceId=354107373`  
**Response**:
```json
{
  "invoiceId": 354107373,
  "invoiceNumber": "1234567",
  "senderName": "PHOENIX PHARMA",
  "senderPib": "100123456",
  "status": "New",
  "invoiceDateUtc": "2025-11-15T00:00:00Z",
  "paymentDateUtc": "2025-11-30T00:00:00Z",
  "sumWithoutVat": 125000.00,
  "vatAmount": 25000.00,
  "sumWithVat": 150000.00,
  "discountPercentage": 5.0,
  "lineItems": [
    {
      "itemName": "Product Name",
      "quantity": 10,
      "unitPrice": 1000.00,
      ...
    }
  ],
  ...
}
```
**Status**: ✅ FUNKSIONON - Kthen metadata, JO XML full

---

### 4. **`GET /purchase-invoice/overview`** ⭐⭐⭐
**Përdorimi**: Overview i shpejtë (më pak detaje)  
**Params**: `?invoiceId=354107373`  
**Response**: List (jo dict) - struktura e çuditshme  
**Status**: ⚠️ FUNKSIONON - Por struktura jo e qartë

---

### 5. **`POST /purchase-invoice/acceptRejectPurchaseInvoice`** ⭐⭐⭐⭐
**Përdorimi**: APROVO ose REFUZO fakturë automatikisht  
**Request**:
```json
{
  "invoiceId": 354107373,
  "accepted": true,
  "comment": "Approved by automation"
}
```
**Status**: ❓ NUK E TESTUAM - Por duket premtues për workflow

---

### 6. **`POST /subscribe`** ⭐⭐⭐⭐⭐
**Përdorimi**: EMAIL NOTIFICATIONS për faktura të reja (jo webhook URL!)  
**Request**: POST me body të zbrazët  
**Response**: Subscription ID (GUID)  
**Validity**: 24 orë (duhet re-subscribe çdo ditë)  
**Status**: ✅ **TESTED & WORKING**  
**Current Subscription**: `4212cc6d-9bdd-4166-a1b3-6c235591d01b` (valid until 2025-11-19)  
**Auto-renewal**: Configured via `efaktura_daily_subscribe.ps1` + Task Scheduler  
**See**: `EFAKTURA_WEBHOOK_GUIDE.md` për setup komplet

---

### 7. **`GET /purchase-invoice/pdf`** ⭐⭐⭐
**Përdorimi**: Download PDF (extended format)  
**Params**: `?invoiceId=354107373`  
**Response**: PDF FileStream  
**Status**: ❓ NUK E TESTUAM - Alternative për XML

---

## ❌ ENDPOINT-E QË NUK FUNKSIONOJNË

### 1. **`POST /purchase-invoice/changes`** ❌
**Problemi**: 404 - Endpoint nuk gjendet ose kërkon strukture tjetër  
**Swagger thotë**: GET me `?date=2025-11-18` (date-time format)  
**Realiteti**: 404 Error  
**Status**: ❌ NUK FUNKSIONON - Dokumentimi i gabuar?

---

## 🔄 ALTERNATIVA PËR BULK ACCESS

### **Strategjia 1: Daily Requests** ⚠️
- Kërko **50 faktura për çdo ditë** (1 request/ditë)
- **Rezultat**: Prap 50 maksimum, edhe për 1 ditë
- **Statusi**: ❌ NUK FUNKSIONON

### **Strategjia 2: Filtering** ⚠️
- Përdor `RestrictionItem` për filter (Invoice_Sender_Like='VEGA')
- **Rezultat**: Filtron brenda 50 fakturave, nuk shton më shumë
- **Statusi**: ⚠️ FUNKSIONON për filtering, JO për bypass

### **Strategjia 3: Pagination Parameters** ❌
- pageIndex=0, pageSize=100
- skip=0, take=100
- **Rezultat**: Parametrat pranohen, por IGNOREN - prap 50
- **Statusi**: ❌ NUK FUNKSIONON

### **Strategjia 4: WEBHOOK Subscribe** ⭐⭐⭐⭐⭐
- **Rekomandimi**: Përdor `/subscribe` për real-time notifications
- eFaktura **push-on** faktura të reja në serverin tënd
- **Statusi**: ❓ NUK E TESTUAM - Por duket BEST SOLUTION!

---

## 📊 STATISTIKA AKTUALE

| Metric | Vlerë |
|--------|-------|
| XML të shkarkuara | 51 (50 unikë + 1 i vjetër) |
| Furnitorë uniqë | 8 |
| Periudha | 2025-10-20 deri 2025-11-15 |
| Vlera totale | ~3.5M RSD |
| API Limit | 50 faktura/request (immutable) |
| Rate Limit | 3 requests/second |

---

## 🎯 REKOMANDIME

### **1. Setup Daily Subscription** (Priority 1) ✅ DONE
```bash
# Already configured!
# Task Scheduler runs: efaktura_daily_subscribe.ps1 at 6:00 AM
# Subscription ID: 4212cc6d-9bdd-4166-a1b3-6c235591d01b
# Valid until: 2025-11-19
```
**Status**: ✅ **ACTIVE** - Email notifications enabled  
**See**: `EFAKTURA_WEBHOOK_GUIDE.md` for complete setup guide

### **2. Përdor `/purchase-invoice` për Metadata** (Priority 2)
- Në vend që të parse XML për të gjithë detajet
- Merr `PurchaseInvoiceDto` që ka të gjitha fieldet structured

### **3. Auto-Approve Workflow** (Priority 3)
```python
def auto_approve_invoice(invoice_id):
    url = "https://efaktura.mfin.gov.rs/api/publicApi/purchase-invoice/acceptRejectPurchaseInvoice"
    payload = {
        "invoiceId": invoice_id,
        "accepted": True,
        "comment": "Auto-approved by WPH AI"
    }
    response = session.post(url, json=payload)
```

### **4. Kontakto eFaktura Support**
- Pyet për bulk export ose historical data access
- Shpjego që 50-limit është shumë i vogël për business
- Request special API access ose CSV export

---

## 🔗 DOKUMENTIMI

- **Swagger UI**: https://efaktura.mfin.gov.rs/swagger/index.html
- **PDF Guide**: (Nuk ka dokumentim të detajuar për limits)
- **Support Email**: (Gjej në portal)

---

**PËRFUNDIM**: 50-invoice limit është **absolute dhe i pa-bypassable**. 
Zgjidhja më e mirë është **WEBHOOK subscription** për real-time sync.
