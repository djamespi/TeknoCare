// Usage: node render_erd.cjs <path-to-@viz-js/viz/dist/viz.cjs>
const fs = require('node:fs');
const path = require('node:path');

async function main() {
  const { instance } = require(path.resolve(process.argv[2]));
  const viz = await instance();
  const dot = fs.readFileSync(path.join(__dirname, 'teknocare_improved_erd.dot'), 'utf8');
  const result = viz.render(dot, { format: 'svg', engine: 'dot' });
  for (const warning of result.errors) console.error(warning.message);
  if (result.status !== 'success') throw new Error('Graphviz layout failed');
  fs.writeFileSync(path.join(__dirname, 'teknocare_improved_erd.svg'), result.output);
  console.log('Exported editable SVG.');
}
main().catch(error => { console.error(error); process.exitCode = 1; });
