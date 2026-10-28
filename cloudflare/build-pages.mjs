import {build} from 'esbuild';
import {fileURLToPath} from 'node:url';
import path from 'node:path';

const here = path.dirname(fileURLToPath(import.meta.url));
const origin = process.env.MISEPORT_PUBLIC_ORIGIN || 'https://miseport.pages.dev';
const url = new URL(origin);
if (url.origin !== origin || url.protocol !== 'https:') throw new Error('Expected exact HTTPS origin');
await import('./build-assets.mjs');
await build({entryPoints: [path.join(here, 'pages-entry.mjs')], bundle: true, format: 'esm',
  platform: 'browser', target: 'es2022', outfile: path.join(here, 'public/_worker.js'),
  minify: true, define: {__MISEPORT_HOST__: JSON.stringify(url.host)}});
console.log('Pages Advanced Mode bundle built for exact host:', url.host);
