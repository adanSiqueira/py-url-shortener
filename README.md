# Py URL Shortener

## Project Overview

**Py URL Shortener** is a Python-based backend project that allows users to shorten URLs, track clicks, set expiration dates, and monitor usage statistics. The application demonstrates a professional, layered architecture with scalability, containerization, and real-world backend best practices.

**Core Features:**
- Shorten long URLs and generate a unique short identifier
- Redirect users to the original URL
- URL expiration mechanism
- Click tracking (count, IP, timestamp, and user-agent)
- Modular architecture suitable for future expansion
- Containerized deployment using Docker and a reverse proxy

---

## Architecture

The project uses a **Layered Architecture** with a light microservices approach:

- **API Layer (FastAPI)**: Exposes endpoints and handles requests and validations.
- **Service Layer**: Implements business logic such as short_id generation, expiration, and click tracking.
- **Database Layer (PostgreSQL)**: Stores URLs, clicks, and analytics.
- **Proxy Layer (Traefik)**: Routes requests, manages HTTPS, and load balancing.
- **Cache Layer (optional - Redis)**: Speeds up access to popular URLs and statistics.

**Advantages:**
- Decoupled layers allow easier testing and maintenance
- Scalable and modular for future microservices
- Professional deployment setup with containerization and reverse proxy

---

## Architecture Diagram
```mermaid
flowchart TD
    %% User interaction
    A[User] --> B["HTTP/HTTPS → Reverse Proxy 
    (Traefik)"]
    
    %% API Layer
    B --> C["API Layer 
    (FastAPI + Uvicorn)"]
    
    %% Service and Cache Layers
    C --> D["Service Layer 
    (Business Logic: short_id, expiration, tracking)"]
    C --> E["Cache Layer 
    (Redis)"]
    
    %% Database Layer
    D --> F["Database Layer (PostgreSQL: URLs, clicks, statistics)"]
    E --> F
    
    %% Styles
    style A fill:#993399,stroke:#333,stroke-width:2px,color:#fff
    style B fill:#3366cc,stroke:#333,stroke-width:2px,color:#fff
    style C fill:#3366cc,stroke:#333,stroke-width:2px,color:#fff
    style D fill:#339933,stroke:#333,stroke-width:2px,color:#fff
    style E fill:#ff9900,stroke:#333,stroke-width:2px,color:#000
    style F fill:#666666,stroke:#333,stroke-width:2px,color:#fff

```
