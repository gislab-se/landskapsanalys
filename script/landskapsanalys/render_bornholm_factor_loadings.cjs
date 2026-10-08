// Rebuild the published table from the v9/v10 factor results and reviewed GIS labels.
// Usage: node script/landskapsanalys/render_bornholm_factor_loadings.cjs
// The generated HTML is committed because GitHub Pages serves it directly.
// GIS descriptions were reviewed against bornholm_topp_botten_rod_gul_gron_med_gis_indata.xlsx;
// the checked-in label CSV preserves them without a runtime Excel dependency.
const fs = require('node:fs');
const path = require('node:path');
const root = path.resolve(__dirname, '../..');
const modelDir = path.join(root, 'docs/geocontext/model_comparisons');

function parseCsv(text) {
  const rows = [];
  let row = [], field = '', quoted = false;
  text = text.replace(/^\uFEFF/, '').replace(/\r\n/g, '\n');
  for (let i = 0; i < text.length; i++) {
    const c = text[i];
    if (c === '"') {
      if (quoted && text[i + 1] === '"') { field += '"'; i++; }
      else quoted = !quoted;
    } else if (!quoted && (c === ',' || c === '\n')) {
      row.push(field); field = '';
      if (c === '\n') { if (row.some(Boolean)) rows.push(row); row = []; }
    } else field += c;
  }
  if (quoted) throw new Error('Unterminated CSV field');
  if (field || row.length) { row.push(field); rows.push(row); }
  const headers = rows.shift();
  return rows.map(values => {
    if (values.length !== headers.length) throw new Error('CSV column count mismatch');
    return Object.fromEntries(headers.map((h, i) => [h, values[i]]));
  });
}

const read = name => fs.readFileSync(name, 'utf8');
const v9Path = path.join(modelDir, 'bornholm_v9_k8_interactive_layers/model/bornholm_v9_k8_interactive_layers_factor_loadings_from_v1.csv');
const v10Path = path.join(modelDir, 'bornholm_v10_landscape_types/model/bornholm_v10_landscape_types_factor_loadings_from_v1.csv');
if (read(v9Path).replace(/\r\n/g, '\n') !== read(v10Path).replace(/\r\n/g, '\n')) {
  throw new Error('v9 and v10 factor results differ; review the shared-table assumption.');
}
const labels = new Map(parseCsv(read(path.join(__dirname, 'config/bornholm_factor_input_labels.csv'))).map(row => [row.gc_name, row]));
const inputs = new Map(parseCsv(read(path.join(modelDir, 'data/landskapsanalys_v3_2_contourterrain68_res9/landskapsanalys_v3_2_contourterrain68_res9_input_layers.csv'))).map(row => [row.gc_name, row]));
const factors = ['F1', 'F2', 'F3', 'F4', 'F5'];
const rows = parseCsv(read(v9Path)).map((row, index) => {
  const id = row.variable.replace(/^(mean|std)_/, '').replace(/_k\d+$/, '');
  const label = labels.get(id), input = inputs.get(id);
  if (!label || !input) throw new Error('Missing GIS metadata: ' + id);
  const scores = Object.fromEntries(factors.map(f => {
    const value = Number(row[f]);
    if (!row[f] || !Number.isFinite(value)) throw new Error('Invalid loading: ' + row.variable + ' ' + f);
    return [f, value];
  }));
  return { variable: row.variable, theme: label.theme_sv, input: label.description_sv,
    source: input.source_name, sourceRow: index + 2, ...scores };
});
const allValues = rows.flatMap(row => factors.map(f => row[f])).sort((a, b) => a - b);
const middle = Math.floor(allValues.length / 2);
const scale = { min: allValues[0], mid: (allValues[middle - 1] + allValues[middle]) / 2, max: allValues.at(-1) };
const manifest = JSON.parse(read(path.join(root, 'apps/potential_model/manifests/landscape/bornholm_landscape_v10.json')));
const data = JSON.stringify({ rows, scale, factorLabels: manifest.factor_labels }).replace(/</g, '\\u003c');
const template = read(path.join(__dirname, 'templates/bornholm_factor_loadings.html'));
if (!template.includes('__FACTOR_DATA__')) throw new Error('Missing data placeholder');
const output = path.join(modelDir, 'bornholm_factor_loadings.html');
fs.writeFileSync(output, template.replace('__FACTOR_DATA__', () => data), 'utf8');
console.log(JSON.stringify({ output: path.relative(root, output), variables: rows.length,
  inputs: new Set(rows.map(row => row.source)).size, factors: factors.length, scale }));
