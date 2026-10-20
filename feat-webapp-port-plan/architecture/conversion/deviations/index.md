# Deviations from Apache Atlas

Every behaviour of Aurelius Atlas that a client could observe and that differs from Apache Atlas 2.4.0 ([ADR 046](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>)). The parity report links each tolerated difference to its entry here; a difference without an entry is a defect.

> [!NOTE]
>
> **DV-04 is temporary**
>
> The most visible row in this table — "no endpoint needs a login" — is the current state of a planned sequence, not a security posture: authentication arrives with increment 6.1 and the deviation is removed then. Until 6.1, read every anonymous call in this repository as development-arrangement behaviour, not production design ([ADR 039](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/039-data-is-protected-where-it-travels-and-where-it-rests/index.md>) names the boundary; [ADR 046](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/046-the-catalogue-keeps-its-public-contract/index.md>) keeps the shape Atlas clients expect when it lands).

| \# | Area | Apache Atlas behaviour | Aurelius Atlas behaviour | Reason | Increment |
| --- | --- | --- | --- | --- | --- |
| DV-01 | Notifications | Publishes entity changes to Kafka; consumes hook messages | Not supported | Out of scope ([ADR 050](<https://aureliusenterprise.github.io/feat-webapp-port-plan/architecture/adr/050-the-system-carries-only-what-the-catalogue-needs/index.md>)) | 0.1 |
| DV-02 | Authorization | Ranger or simple authorizer | Simple authorizer only | Out of scope; Ranger needs its own server | 0.1 |
| DV-03 | Admin | `version` names Apache Atlas 2.4.0 and its build revision | Names Aurelius Atlas, its release and its revision | A client must be able to tell which implementation answers | 0.5 |
| DV-04 | Authentication | Every endpoint except `admin/status` needs a login; the session reports the user, groups and permissions | Until 6.1, no endpoint needs a login; the session reports no user, no groups and no entity permissions | Authentication arrives in 6.1; removed then | 0.5 |
| DV-05 | Admin | The session's `timezones` are Java's `TimeZone.getAvailableIDs()` | The IANA time zone ids of the server's tz database, sorted | Java's list includes legacy three-letter ids the IANA database does not have | 0.5 |
| DV-06 | Types | A type definition's `createdBy` and `updatedBy` name the user who created and last updated it | Until 6.1, absent | There is no login until 6.1; removed then | 1.4 |
| DV-07 | Types | The built-in model types and the patch records name the operating system account the server runs as | Name no user | The account is an accident of deployment, and is the same for every type a process loads | 1.5 |
| DV-08 | Types | A patch without an id is recorded, without an id, at every start | Is applied at every start and not recorded | A record without an id cannot be found again; Atlas never matches it either | 1.5 |
| DV-09 | Types | `/v2/types/typedefs` and its headers list each kind in the hash order of the registry; of two `notsupertype` filters, the first in the request parameters' hash order applies | Each kind sorted by name; the first `notsupertype` in the request applies | Hash order is not something a client can rely on (DD-034) | 1.6 |
| DV-10 | Types | A write body that is not an `AtlasTypesDef` is answered by Jersey's JSON provider | `400 BAD_REQUEST` with Atlas's error body | Atlas's source and tests do not state its answer | 1.6 |
| DV-11 | Interface | Serves its own dashboards: `dashboardv2` at `/` and `dashboardv3` at `/n/` | Serves the Aurelius webapp, a web interface of its own design (ADR 053) | The product interface is Aurelius's own; the Atlas dashboards stay as the parity reference | 7.10 |
