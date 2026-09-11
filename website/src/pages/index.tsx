import React from 'react';
import Layout from '@theme/Layout';
import Link from '@docusaurus/Link';
const cards = [{"title": "Edit embedded scripts", "description": "Pull Python out of a Perspective JSON resource, edit it, then save it back.", "path": "guides/script-editing"}, {"title": "Find the API", "description": "Use completions and hover documentation while working with system APIs.", "path": "guides/lsp-features"}, {"title": "Choose your editor", "description": "Compare installation steps and the differences between editors.", "path": "getting-started/installation"}];
export default function Home(): React.JSX.Element {
 return <Layout title="Ignition Dev Tools" description="API completions, script extraction, and lint feedback for VS Code, Neovim, and Zed.">
  <main><section className="launch-hero"><p className="launch-label">IGNITION / DEVELOPER TOOLS</p><h1>Edit Ignition scripts in your editor.</h1><p className="lead">API completions, script extraction, and lint feedback for VS Code, Neovim, and Zed.</p>
  <div className="launch-actions"><Link className="button button--primary button--lg" to="/docs/getting-started/installation">Get started</Link><Link className="button button--outline button--primary button--lg" to="/docs/getting-started/quickstart">Try a first workflow</Link></div></section>
  <section className="launch-grid" aria-label="Documentation paths">{cards.map(card => <article key={card.path}><h2>{card.title}</h2><p>{card.description}</p><Link to={'/docs/' + card.path}>Read the guide →</Link></article>)}</section>
  <aside className="launch-maintainer"><p>I’m Patrick Mannion. I work on Ignition development tools and write about the work on FIELDNOTES.</p><p><a href="https://awake-iris-z6ww.here.now/about/">About me</a> · <a href="https://www.linkedin.com/in/mannionpatrick/">LinkedIn</a> · <a href="https://x.com/__pattym__">X</a> · <a href="https://github.com/TheThoughtagen/ignition-ide-plugins/graphs/contributors">Project contributors</a></p></aside></main>
 </Layout>;
}
