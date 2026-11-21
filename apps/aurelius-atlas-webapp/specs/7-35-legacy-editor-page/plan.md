# 7.35 Plan

The steps, in order, with the rules each delivers. The spec is [`spec.md`](./spec.md).

## 0. Before it: the verdicts under tenancy (12.7b, its own increment)

On the standalone stack today, with tenancy on, the editor shows no verdict at all. The validate-entity service
reads the rules as its own service account (VEV-04, DD-499), whose token names no tenant, and the server refuses
it (`AURELIUS-403-00-001 … acts in no tenant`); the service answers 502 and the editor swallows it (EDT-23). Point
3 of the request cannot be seen until the service reads the caller's tenant's rules.

Two ways, to decide before 12.7b's spec:

- **Read with the caller's token, cache per tenant** (recommended): the caller's token names their tenant; on
  a cache miss the service reads that tenant's rules with it, and caches them per tenant. DD-499 refused
  forwarding because a cache filled under one user's visibility leaked to another; per tenant there is no
  leak, as every member of a tenant reads its rules (`atlas-read`). - **The service account in every tenant**:
  made a member of each tenant's organization, as trust does for the operators, and asking Keycloak for a
  token per tenant. The account's reads stay its own, at the price of a realm membership per tenant and a
  token per tenant.

## 1. The page (EDP-01 to EDP-04)

The routes `search/create-entity` and `search/edit-entity/:guid` in the main outlet, the drawer's two editor
routes removed, the pencil and create action re-pointed, the page title, Cancel and the return after Save and
Delete. Unit tests for the routes and the return; the e2e moves from the drawer to the page.

## 2. The form definitions (EDP-05, EDP-06, EDP-11 to EDP-13)

`form-definitions.ts`: the ten tables of the spec as data, one entry per field (attribute, relationship or
not, input, pick type and cardinality, label and placeholder keys). The editor renders a type with a definition
from it, and every other type from EDT-03 as today. One unit test per table, field by field, in order.

## 3. Layout and validation (EDP-07 to EDP-10, EDP-14 to EDP-18)

The two-column field row (`2fr 1fr` above the desktop breakpoint), the verdict lines matched to fields by
attribute with the `--source`/`--target` pair beside the relationship, the yellow definition box, the required
checks with their messages and the foot notice, the U+2019 warnings. Unit tests per rule.

## 4. Docs and verification

The user guide's editing page, with a screenshot per form; the webapp's unit and e2e suites; by hand on the
standalone stack, each form against its table, typing into `name` and `definition` to see the verdicts change.

## Size

Steps 1 to 3 are about 1,200 changed lines of production code, mostly the form definitions and the field row.
If it grows past 1,500, step 1 (the page) goes first as 7.35a and steps 2 and 3 follow as 7.35b.
