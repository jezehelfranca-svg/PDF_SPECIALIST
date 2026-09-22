import { createHash } from 'node:crypto';
import { copyFile, readFile, rm, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const distDir = resolve('dist');
const source = resolve(distDir, 'index.html');
const release = resolve(distDir, 'pdf_merger_bookmarks_v2.0.0.html');
const checksum = resolve(distDir, 'pdf_merger_bookmarks_v2.0.0.html.sha256');

await copyFile(source, release);
await rm(source);

const html = await readFile(release);
const digest = createHash('sha256').update(html).digest('hex');
await writeFile(checksum, `${digest}  pdf_merger_bookmarks_v2.0.0.html\n`, 'utf8');

console.log(`Release created: ${release}`);
console.log(`SHA-256: ${digest}`);
