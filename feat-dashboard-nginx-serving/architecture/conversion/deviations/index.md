# Deviations from Apache Atlas

Every behaviour of Aurelius Atlas that a client could observe and that differs from Apache Atlas 2.4.0 ([ADR 046](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). The parity report links each tolerated difference to its entry here; a difference without an entry is a defect.

| \# | Area | Apache Atlas behaviour | Aurelius Atlas behaviour | Reason | Increment |
| --- | --- | --- | --- | --- | --- |
| DV-01 | Notifications | Publishes entity changes to Kafka; consumes hook messages | Not supported | Out of scope ([ADR 050](<https://aureliusenterprise.github.io/feat-dashboard-nginx-serving/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)) | 0.1 |
| DV-02 | Authorization | Ranger or simple authorizer | Simple authorizer only | Out of scope; Ranger needs its own server | 0.1 |
| DV-03 | Admin | `version` names Apache Atlas 2.4.0 and its build revision | Names Aurelius Atlas, its release and its revision | A client must be able to tell which implementation answers | 0.5 |
| DV-04 | Authentication | Every endpoint except `admin/status` needs a login; the session reports the user, groups and permissions | Until 6.1, no endpoint needs a login; the session reports no user, no groups and no entity permissions | Authentication arrives in 6.1; removed then | 0.5 |
| DV-05 | Admin | The session's `timezones` are Java's `TimeZone.getAvailableIDs()` | The IANA time zone ids of the server's tz database, sorted | Java's list includes legacy three-letter ids the IANA database does not have | 0.5 |
| DV-06 | Types | A type definition's `createdBy` and `updatedBy` name the user who created and last updated it | Until 6.1, absent | There is no login until 6.1; removed then | 1.4 |
| DV-07 | Types | The built-in model types and the patch records name the operating system account the server runs as | Name no user | The account is an accident of deployment, and is the same for every type a process loads | 1.5 |
| DV-08 | Types | A patch without an id is recorded, without an id, at every start | Is applied at every start and not recorded | A record without an id cannot be found again; Atlas never matches it either | 1.5 |
| DV-09 | Dashboards | One process (the web application) serves both dashboards and the API from one origin; `/n` reaches `/n/` through its directory redirect, and its responses carry no hardening headers | The dashboard image serves the dashboards and proxies `/api/` to the API-only server, keeping the one origin: `/n` redirects 308, and the responses carry the hardening headers of the site config — no CSP, as the vendored UI runs inline scripts and `eval` and ADR 046 keeps its behaviour | The one origin is kept for the session cookie and the relative URLs; the split follows the template's serving pattern (DD-034 supersedes DD-018) | 0.6 |
