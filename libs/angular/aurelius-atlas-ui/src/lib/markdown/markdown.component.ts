import { ChangeDetectionStrategy, Component, computed, input } from "@angular/core";
import { Marked, type RendererThis, type Tokens } from "marked";

/**
 * The Bulma renderers of the Aurelius `MarkdownComponent` (the legacy
 * `libs/components/src/lib/markdown/markdown.component.ts`, clone commit
 * b05738982), re-expressed as a marked renderer object. The legacy
 * registered them on the shared `MarkdownService` singleton from the
 * component constructor (DD-321's defect); a per-component `Marked`
 * instance carries the same four mappings without the global state.
 * Headings land on the Bulma title ramp, a blockquote lands on the Bulma
 * message, tables land on the striped Bulma table, and an image lands on
 * the Bulma figure. `this` is marked's renderer context (the token
 * parser).
 */
const bulmaRenderers = {
    heading(this: RendererThis, token: Tokens.Heading): string {
        return `<h${token.depth} class="title is-${token.depth}">${this.parser.parseInline(token.tokens)}</h${token.depth}>`;
    },
    blockquote(this: RendererThis, token: Tokens.Blockquote): string {
        return `<article class="message"><div class="message-body">${this.parser.parse(token.tokens)}</div></article>`;
    },
    image(token: Tokens.Image): string {
        const title = token.title === null ? "" : ` title="${token.title.replaceAll('"', "&quot;")}"`;
        return `<figure class="image"${title}><img src="${token.href}" alt="${token.text}"></figure>`;
    },
    table(this: RendererThis, token: Tokens.Table): string {
        const head = token.header.map((cell) => `<th>${this.parser.parseInline(cell.tokens)}</th>`).join("");
        const body = token.rows
            .map((row) => `<tr>${row.map((cell) => `<td>${this.parser.parseInline(cell.tokens)}</td>`).join("")}</tr>`)
            .join("");
        return `<div class="table-container"><table class="table is-striped is-hoverable is-fullwidth"><thead><tr>${head}</tr></thead><tbody>${body}</tbody></table></div>`;
    },
};

/** The renderer instance: marked with the Bulma mappings, parse always sync. */
const marked = new Marked({ async: false, renderer: bulmaRenderers });

/**
 * The Aurelius markdown block (`models4insight-markdown`, UIC-21, DD-321):
 * markdown text rendered to HTML and shown in a Bulma `content` block.
 * The component is presentational: the caller passes the text (DD-136) and
 * this owns the rendering. The HTML reaches the DOM through an
 * `[innerHTML]` binding, which Angular sanitizes in the HTML context — the
 * XSS guard the legacy relied on and that marked itself does not provide.
 */
@Component({
    selector: "aurelius-atlas-ui-markdown",
    imports: [],
    template: `<div class="content aurelius-markdown" [innerHTML]="html()"></div>`,
    styleUrl: "./markdown.component.scss",
    changeDetection: ChangeDetectionStrategy.OnPush,
})
export class Markdown {
    /** The markdown source. */
    readonly markdown = input.required<string>();

    /** The rendered HTML: marked with the Bulma mappings, untrusted — the
     * `[innerHTML]` binding sanitizes it (Angular's HTML context). */
    protected readonly html = computed(() => marked.parse(this.markdown()) as string);
}
