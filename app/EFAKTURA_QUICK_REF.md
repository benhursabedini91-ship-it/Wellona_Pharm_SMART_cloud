# ⚡ eFaktura - Quick Reference Card

## 🎯 DAILY COMMANDS

### **Subscribe for Notifications** (Daily)
```bash
$env:WPH_EFAKT_API_KEY="f7b40af0-9689-4872-8d59-4779f7961175"
python efaktura_webhook.py subscribe
```

### **Fetch Invoices** (Manual)
```bash
python fetch_all_invoices.py --from 2025-11-01 --to 2025-11-18
```

### **Import to Database** (Dry-run)
```bash
$env:WPH_DB_PASS="wellona-server"
python import_efaktura_safe.py --dry-run --user smart_pedja
```

### **Complete Automation** (All-in-one)
```bash
powershell -ExecutionPolicy Bypass -File efaktura_complete_daily.ps1
```

---

## 📊 STATUS CHECK

```bash
# Subscription
python efaktura_webhook.py check
cat efaktura_subscription_id.txt

# Files
ls ../staging/faktura_uploads/INV_*.xml | measure

# Logs
cat logs\efaktura_daily_$(Get-Date -Format 'yyyy-MM-dd').log

# Task Scheduler
Get-ScheduledTask -TaskName "eFaktura*"
```

---

## 🔑 CREDENTIALS

**API Key**: `f7b40af0-9689-4872-8d59-4779f7961175`  
**DB User**: `smart_pedja`  
**DB Pass**: `wellona-server`  
**DB Name**: `wph_ai`  
**Subscription ID**: `4212cc6d-9bdd-4166-a1b3-6c235591d01b`

---

## 📁 KEY FILES

| File | Purpose |
|------|---------|
| `efaktura_webhook.py` | Subscription mgmt |
| `fetch_all_invoices.py` | Download XMLs |
| `import_efaktura_safe.py` | Import to DB |
| `efaktura_complete_daily.ps1` | Full automation |
| `efaktura_subscription_id.txt` | Current sub |

---

## 🚨 TROUBLESHOOTING

| Issue | Fix |
|-------|-----|
| 401 Error | Check API key |
| 429 Error | Wait 2 seconds |
| Subscription expired | Re-run subscribe |
| No emails | Check eFaktura settings |
| Import fails | Run --dry-run first |

---

## 📞 QUICK HELP

**Full Docs**: `EFAKTURA_FINAL_STATUS.md`  
**API Ref**: `EFAKTURA_ENDPOINTS_GUIDE.md`  
**Setup**: `EFAKTURA_WEBHOOK_GUIDE.md`  

**Support**: https://efaktura.mfin.gov.rs
