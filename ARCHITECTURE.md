# ZReal Architecture Diagram

```mermaid
graph TD
    subgraph Frontend
        A[Issuer Dashboard]
        B[Investor Portfolio]
        C[Interactive Tour]
        D[Modals: ZSA + Legal Shield]
    end

    subgraph Backend Django
        E[Views & APIs]
        F[Models: Property, Investment, Distribution, ValuationHistory]
        G[ExternalValuationService]
        H[ZcashClient]
    end

    subgraph Background Tasks Celery
        I[process_dividend_payouts]
        J[monitor_zcash_transactions]
        K[revalue_all_tokenized_properties]
    end

    subgraph Data Layer
        L[(PostgreSQL + PostGIS)]
        M[(Redis)]
    end

    subgraph Blockchain
        N[Zcash Testnet/Mainnet<br/>Shielded Transactions]
    end

    subgraph Observability
        O[OpenTelemetry]
        P[Prometheus + Grafana]
        Q[Loki + Promtail]
        R[Falco + Sidekick]
    end

    A --> E
    B --> E
    D --> E
    E --> F
    E --> G
    E --> H
    G --> F
    H --> N
    I --> H
    I --> F
    J --> H
    J --> F
    K --> G
    K --> F
    F --> L
    E --> M
    I --> M
    J --> M
    K --> M

    E --> O
    I --> O
    J --> O
    K --> O
    O --> P
    E --> Q
    H --> R
```

## Key Components

| Layer              | Technology                          | Responsibility |
|--------------------|-------------------------------------|----------------|
| **Frontend**       | Django Templates + Tailwind         | Premium UI for Issuers & Investors |
| **Backend**        | Django + DRF                        | Business logic, APIs, Auth |
| **Valuation**      | `ExternalValuationService`          | Heuristic + External API |
| **Blockchain**     | `ZcashClient` + `z_sendmany`        | Shielded ZSA & Dividend txs |
| **Background**     | Celery + Redis                      | Dividends, Monitoring, Re-valuation |
| **Data**           | PostgreSQL + PostGIS                | Core data + geospatial |
| **Observability**  | OTel + Prometheus + Grafana + Loki + Falco | Full visibility + security |

## Data Flow Highlights

- **ZSA Issuance** → `ZcashClient` → Shielded tx + rich memo
- **Dividend Payout** → Celery → `ZcashClient.distribute_shielded_payments()` → On-chain
- **Valuation** → `ExternalValuationService` → Heuristic or External API → History saved
- **Real-time** → WebSocket (Channels) + `DashboardEvent` model

This architecture is designed to be **scalable, auditable, and privacy-first**.
