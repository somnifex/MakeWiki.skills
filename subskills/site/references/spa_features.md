# Static Wiki SPA Compiler Features

The site compiler is fully mechanical: prose has already been authored and
verified before this step runs. The compiler only packages it.

- **Single HTML Bundle**: CSS, JS, and document data packed into `index.html`.
- **Search Engine**: In-memory token index supporting multi-term queries.
- **Navigation**: URL hash routing with history support (`#README.md`).
- **Responsive Layout**: Mobile-friendly sidebar toggle.