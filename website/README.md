# Ignition Dev Tools documentation site

Install Node.js 22, then run these commands from `website/`:

```sh
npm ci
npm run build
npm run typecheck
npm start
```

The site uses Docusaurus. Edit user guides in `docs/`, navigation in `website/sidebars.ts`, and the landing page in `website/src/pages/index.tsx`. Internal design records remain in the repository and are excluded from the published site.

Pull requests build the docs and check internal links. Main commits deploy to https://thethoughtagen.github.io/ignition-ide-plugins/ through GitHub Pages. Set the repository's Pages build source to GitHub Actions before its first deployment.
