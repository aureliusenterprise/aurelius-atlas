import { HttpClient } from "@angular/common/http";
import { inject, Injectable, signal } from "@angular/core";

import { TENANCY } from "../tenancy";
import { APP_CONFIG } from "../tokens";

/** The server's answer: the link to the tenant's catalogue dashboard (TDL-06). */
interface DashboardsAnswer {
    readonly url: string;
}

/** The server's path of the tenant's dashboards link, under the API base (TDL-06). */
export const DASHBOARDS_PATH = "/aurelius/v1/tenancy/dashboards";

/**
 * The signed-in user's link to their tenant's dashboards in Grafana, read once
 * per page load with tenancy on (TDL-08, DD-768).
 *
 * The server decides who may see them (TDL-06): the tenant's stewards and
 * administrators and the operators. It answers 200 with the link for them,
 * and 403 or 404 for everyone else. The menu shows the item only on 200; any
 * other answer, or none, leaves the link undefined and makes no noise (TDL-09).
 * With tenancy off there is nothing to ask, and no request is made.
 */
@Injectable({ providedIn: "root" })
export class DashboardsService {
    private readonly _url = signal<string | undefined>(undefined);

    /** The catalogue dashboard's address, `undefined` while unknown or when the user may not see it (TDL-08). */
    readonly url = this._url.asReadonly();

    constructor() {
        if (!inject(TENANCY).enabled) {
            return;
        }
        const base = inject(APP_CONFIG).apiBaseUrl;
        inject(HttpClient)
            .get<DashboardsAnswer>(`${base}${DASHBOARDS_PATH}`)
            .subscribe({
                next: (answer) => this._url.set(typeof answer?.url === "string" ? answer.url : undefined),
                error: () => this._url.set(undefined),
            });
    }
}
