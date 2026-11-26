# Settings and Alerts

The header's right hand side holds two icons: a gear for Settings and a bell for Alerts. This page covers both, and the account menu beside them. Every choice on this page is yours alone, and it does not change anyone else's catalogue.

## Open the drawers

The gear opens the **Settings** drawer and the bell opens the **Alerts** drawer. Both are icon-only, with no text label, and the icon you opened lights up while its drawer is open. Only one drawer sits over the screen at a time, so opening the bell replaces Settings.

Close a drawer with its X, by clicking beside it, or by pressing Escape. The bell carries a dot when something is unread, coloured by the most serious unread item, and it rings once when a new group of alerts arrives.

## The settings

The settings panel holds these choices, in this order:

| Setting | Options | What happens when you change it |
| --- | --- | --- |
| Appearance | Auto, Light, Dark | Applies at once, no reload. |
| Language | en-US, nl-NL | Reloads the page in that language. |
| Search by | Words, Meaning, Both | Runs the search on screen again. |
| Time zone | Browser default, then the server's list | Applies after you reload the page. |
| Default table page size | 5, 10, 20, 50 | Stored for later, and used by no screen yet. |
| Usage telemetry | On or off | Off stops at once. On needs a reload. |
| Version | Text only | Shows the app name and the server version. |

**Appearance** starts on Auto, which follows your operating system. **Language** is the only setting that reloads the page. Its help line says so: "Switching language reloads the page in that language." **Search by** is covered in [Find data](<https://aureliusenterprise.github.io/feat-webapp-versioned-docs-link/user-guide/find-data/#words-meaning-and-both>).

> [!WARNING]
>
> **Default table page size does nothing yet**
>
> This setting stores your choice, and no screen reads it. Search results always page in tens, and the other tables use their own fixed sizes. The gap is known. Do not expect the number to change anything you can see.

The panel below holds those choices in that order.

![The Settings drawer.](<https://aureliusenterprise.github.io/feat-webapp-versioned-docs-link/assets/user-guide/settings-panel.png>)

## Usage telemetry

Telemetry is on by default. It sends three things to your own deployment's collector: a trace for each API call, uncaught browser errors with their stack trace, and page-performance timings. It also adds a trace header to API calls so an operator can follow one click across services. Each browser tab carries a random session id, so an operator can count journeys without naming you. Your sign-in token rides the telemetry push, which is how the collector accepts it.

Turning telemetry off stops the exports at once. Turning it on needs a reload, because the webapp builds its telemetry only when it starts. The panel states this too: "Turning it on takes effect after a reload."

Your choices live in your browser, not in your account. A different browser or machine starts from the defaults again. Language is the one exception, and the webapp saves it to your account as a courtesy, so the sign-in page greets you in the language you last used.

## The alerts drawer

Alerts are grouped by severity, and the drawer's chips read **Info**, **Warnings**, and **Errors**. A chip shows how many groups it holds and dots when it holds something unread. Click a chip to hide or show that severity. A severity with nothing holds its chip greyed out.

Each alert row shows its message, a timestamp in your chosen time zone, and a `×3` chip when the same message arrived several times inside a minute. **Clear all** empties the drawer and cannot be undone, and a row's delete button dismisses that row.

An empty drawer reads **No alerts**. The feed lives in memory only, so a reload empties it. That is by design.

Alerts appear when the webapp hits a failure it cannot show in place: a failed API call, a failed search, a broken lineage read, or an uncaught error. An expired session files a warning, "Your session has expired. Signing you in again.", and the webapp signs you in and returns you where you were.

## The account menu

Your name sits at the far right of the header. Open it and the menu holds:

- **Tenant**: the tenant you are acting in, shown when your deployment serves several tenants.
- **Switch tenant**: sign in again and choose a different tenant. You return to the page you were on.
- **Dashboards**: opens the deployment's dashboards, when the server publishes an address for them.
- **Account security**: opens your account, where you change your password.
- **Logout**: ends your session.

**Switch tenant** does not sign you out first. It asks your identity provider which tenant you want this time, then brings you back where you were. A session serves one tenant at a time.

## Try it

1. Click the gear. Switch **Appearance** to **Dark** and watch the screen change without a reload.
2. Switch **Language** to `nl-NL`. The page reloads in Dutch. Open Settings again and switch back.
3. Click the bell. With nothing wrong it reads **No alerts**.
4. Break something on purpose: open Settings, choose **Meaning**, and search on a deployment with no meaning index. The alert "Search by meaning is not available on this server" appears, and the mode falls back to **Words**.
