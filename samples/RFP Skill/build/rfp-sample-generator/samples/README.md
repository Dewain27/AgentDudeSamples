# Sample output

Pre-generated example documents, each a matched **request + response** pair.
These were produced with fixed seeds so they're stable; regenerate or make your
own from the project root:

```bash
python generate.py pair --industry healthcare --project patient-portal
```

| Scenario | Request | Response |
| --- | --- | --- |
| Patient portal (healthcare) | `rfp-request_brightpath-behavioral-health_patient-portal_d3ec.md` | `rfp-response_brightpath-behavioral-health_patient-portal_d3ec.md` |
| Constituent/permitting portal (government) | `rfp-request_city-of-lakemont_constituent-portal_8ac5.md` | `rfp-response_city-of-lakemont_constituent-portal_8ac5.md` |
| Loan origination (financial services) | `rfp-request_summit-ridge-credit-union_loan-origination_8aa6.md` | `rfp-response_summit-ridge-credit-union_loan-origination_8aa6.md` |

Every request pairs with the response of the same filename suffix — they share
an RFP number, budget, and dates because both render from one scenario.

All content is fictional.
