# ZReal Production Readiness Checklist

**Project:** ZReal — Privacy-First Real Estate RWA Tokenization on Zcash  
**Date:** June 23, 2026  
**Status:** Pre-Production Review

Use this checklist to ensure ZReal is ready for real capital and users.

---

## 1. Core Functionality

- [ ] ZSA Issuance flow works end-to-end (including rich memo + metadata)
- [ ] Legal Shield document processing works reliably (OCR + extraction)
- [ ] ZSA metadata is correctly enriched from Legal Shield documents
- [ ] Investor Portfolio shows real holdings and distribution history
- [ ] Automated dividend payouts work with real Zcash shielded transfers
- [ ] Role-based access (Issuer vs Investor) functions correctly
- [ ] Stripe subscription billing works (checkout + webhooks)
- [ ] Real-time updates (WebSocket + SSE) function reliably

---

## 2. Security

- [ ] All sensitive endpoints protected with authentication
- [ ] WebSocket connections authenticated (currently missing — high priority)
- [ ] Rate limiting enabled on critical endpoints (ZSA issuance, document upload)
- [ ] Security headers properly configured (`SECURE_HSTS_*`, CSP, etc.)
- [ ] Secrets managed securely (not hardcoded)
- [ ] Zcash RPC credentials and `from_zaddr` properly protected
- [ ] Input validation on all user inputs (especially Zcash addresses)
- [ ] Audit logging enabled for sensitive actions (ZSA issuance, distributions)

---

## 3. Infrastructure & Deployment

- [ ] Docker images build successfully
- [ ] `docker-compose.yml` works for local development
- [ ] Kubernetes manifests / Helm chart are production-grade
- [ ] Database migrations are tested and safe
- [ ] Static files served correctly (Whitenoise or CDN)
- [ ] Media files stored securely (preferably object storage)
- [ ] Health check endpoint (`/health/`) is working
- [ ] Celery + Redis configured and running reliably
- [ ] Proper environment variable management (django-environ or similar)

---

## 4. Observability & Monitoring

- [ ] OpenTelemetry tracing enabled and sending data
- [ ] Prometheus metrics exposed and scraped
- [ ] Grafana dashboards created and useful
- [ ] Loki + Promtail collecting logs
- [ ] Falco runtime security rules deployed and alerting
- [ ] Error tracking (Sentry or equivalent) configured
- [ ] Alerts set up for critical failures (ZSA issuance failures, Celery down, etc.)

---

## 5. Data & Privacy

- [ ] Investor shielded addresses stored securely
- [ ] Zcash shielded transactions use `AllowFullyShielded` policy
- [ ] Personal data handling complies with privacy requirements
- [ ] Distribution memos do not leak unnecessary information
- [ ] Backup strategy defined for database and Zcash node/wallet

---

## 6. Operations & Maintenance

- [ ] Management command `process_dividends` documented and tested
- [ ] Celery Beat scheduled tasks configured (if using periodic payouts)
- [ ] Runbook / operational documentation exists for common issues
- [ ] Rollback plan defined for deployments
- [ ] Database backup & restore procedures tested
- [ ] Zcash node / wallet backup strategy documented and tested

---

## 7. Testing & Quality

- [ ] Critical paths have automated tests (ZSA issuance, document upload, distributions)
- [ ] Manual testing performed on main user flows
- [ ] Load testing considered for high-traffic scenarios (if applicable)
- [ ] Security audit or review performed (at minimum internal review)
- [ ] All TODOs and FIXMEs in code reviewed and addressed or documented

---

## 8. Documentation

- [ ] `Report.md` up to date
- [ ] `PRODUCTION_READINESS_CHECKLIST.md` maintained
- [ ] Architecture decisions documented (especially ZSA strategy)
- [ ] Onboarding guide / Interactive Tour covers main features
- [ ] API documentation available (if exposing APIs)

---

## 9. Go-Live Criteria (Must Have)

- [ ] All items in sections 1–3 marked as done
- [ ] WebSocket authentication implemented
- [ ] Investor shielded addresses storage implemented
- [ ] At least one successful end-to-end test on testnet (ZSA + distribution)
- [ ] Monitoring and alerting in place
- [ ] Rollback plan tested

---

## Sign-Off

| Role              | Name          | Date       | Signature |
|-------------------|---------------|------------|---------|
| Technical Lead    |               |            |         |
| Product Owner     |               |            |         |
| Security Reviewer |               |            |         |
| DevOps            |               |            |         |

---

**Next Steps After Checklist Completion**

1. Final security review + penetration test (recommended)
2. Soft launch with limited users / properties
3. Monitor closely for first 2–4 weeks
4. Iterate based on real usage feedback

---

*This checklist should be treated as a living document and updated as the platform evolves.*
