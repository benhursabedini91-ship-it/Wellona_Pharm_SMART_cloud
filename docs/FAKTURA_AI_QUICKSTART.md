# Faktura AI — Quick Start Guide

## 🚀 TL;DR

**Problem**: 20+ hours/month manually entering supplier invoices into ERP  
**Solution**: Automated pipeline that fetches, validates, and commits invoices while you sleep  
**Timeline**: 4-6 weeks for MVP  
**ROI**: 108% return in 3 years, pays for itself in 16-18 months

---

## 📊 Visual Overview

```
03:00 AM ─┐
          ├─► FTP Watch (Phoenix)  ──┐
03:15 AM ─┤                          │
          └─► Email Fetch (Vega)   ──┤
                                      │
                                      v
                              ┌───────────────┐
                              │  XML Parser   │
                              │  + Validator  │
                              └───────┬───────┘
                                      │
                      ┌───────────────┼───────────────┐
                      │               │               │
                      v               v               v
                  CLEAN (99%)    REVIEW (90-98%)   ERROR (<90%)
                      │               │               │
                      v               v               v
                 Auto-Commit     Web UI Queue    Quarantine
                 (ERP KU-*)      (Manual OK)     (Logs)
                      │               │               │
                      v               v               v
06:00 AM ────────► Proknjizi ◄────────┴───────────────┘
                      │
                      v
             ✅ Invoice Posted
             📧 Daily Report Sent
```

---

## 🎯 Core Features

### Phase 1 MVP (Weeks 1-6)
- ✅ Automatic FTP/Email fetching
- ✅ Multi-supplier XML parsing (Phoenix, Vega, Sopharma, Farmalogist)
- ✅ Product matching (sifra + barcode)
- ✅ Price/rabat validation
- ✅ Total reconciliation (±0.1%)
- ✅ Duplicate detection (SHA256 hash)
- ✅ Web UI review queue
- ✅ Auto-commit to ERP (UI automation)

### Phase 2+ (Months 2-6)
- 📄 PDF OCR support (Tesseract)
- 📊 Cross-check vs Order Brain
- 📱 Mobile notifications
- 🤖 AI schema learning
- 🔗 Direct DB integration (no UI automation)

---

## 💰 Cost Breakdown

| Item | Cost |
|------|------|
| Development (120-160h × 3,000 RSD/h) | 360,000-480,000 RSD |
| Infrastructure (storage, etc.) | 6,000 RSD/year |
| Monthly maintenance (2h × 3,000 RSD/h) | 6,000 RSD/month |
| **Total Year 1** | **~450,000 RSD (~$4,500 USD)** |

**Savings**: 20+ hours/month × 1,500 RSD/h = **30,000 RSD/month**  
**Payback**: 16-18 months  
**3-Year ROI**: +486,000 RSD (108%)

---

## 📋 Implementation Checklist

### Week 1-2: Foundation
- [ ] Create PostgreSQL schema (`ops.faktura_in`, `ops.faktura_items`)
- [ ] Build 4 supplier XML mappers (JSON configs)
- [ ] Enhance `faktura_ai_mvp.py` with DB writes
- [ ] Create web UI: `faktura_review.html`

### Week 3-4: Automation
- [ ] Build FTP watcher (`fetch_ftp.py`)
- [ ] Build IMAP fetcher (`fetch_mail.py`)
- [ ] Add SHA256 deduplication
- [ ] Configure Task Scheduler (03:00, 03:15, 03:30)

### Week 5-6: ERP Integration
- [ ] Build UI automation (`commit_erp.ps1`)
- [ ] Test in `ebdev` with 10 invoices
- [ ] Create rollback procedure
- [ ] Add email alerts (daily summary)

---

## 🔑 Success Metrics

| KPI | Target |
|-----|--------|
| Match Rate | ≥99% |
| Auto-Commit Rate | ≥80% |
| Processing Time | <30 sec/invoice |
| Error Rate | <2% |
| Time Savings | 20+ hours/month |

---

## 🚨 Risk Mitigation

| Risk | Solution |
|------|----------|
| ERP UI changes | Version checking + fallback to manual |
| XML schema changes | Auto-detect + alert admin |
| Duplicate commits | SHA256 hash + unique constraint |
| Network failures | Retry logic + offline queue |

---

## 📞 Next Steps

1. **Review** full research doc: `docs/FAKTURA_AI_RESEARCH.md`
2. **Approve** Phase 1 scope
3. **Gather** 10-20 sample XMLs from each supplier
4. **Schedule** kickoff meeting (30 min)
5. **Begin** development Week 1

---

## 📚 Related Documents

- **Full Research**: [`FAKTURA_AI_RESEARCH.md`](./FAKTURA_AI_RESEARCH.md) (12 sections, 2,000+ lines)
- **Current MVP**: `app/faktura_ai_mvp.py` (255 lines, working)
- **Process Docs**: `wphAI logjika dhe plani.txt` (3,700+ lines)
- **Existing Config**: `configs/faktura_ai.json` (sample)

---

**Questions?** → Open this document and the full research side-by-side  
**Ready to start?** → Confirm approval and we begin Week 1 tomorrow! ✅

