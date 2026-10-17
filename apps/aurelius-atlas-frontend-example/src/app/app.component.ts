import { KeyValuePipe } from "@angular/common";
import { ChangeDetectionStrategy, Component, inject } from "@angular/core";
import { RouterOutlet } from "@angular/router";
import { DarkMode, Header } from "aurelius-atlas-ui";
import { AuthService } from "./services/auth.service";
import { LocaleService } from "./services/locale.service";

@Component({
    imports: [DarkMode, Header, KeyValuePipe, RouterOutlet],
    selector: "aurelius-atlas-frontend-example-root",
    templateUrl: "./app.component.html",
    styleUrl: "./app.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class App {
    /**
     * The authentication service is injected to access the current authentication state.
     */
    protected readonly authService = inject(AuthService);

    /**
     * The locale service is injected to access the current locale and build locale-specific URLs.
     */
    protected readonly localeService = inject(LocaleService);
}
