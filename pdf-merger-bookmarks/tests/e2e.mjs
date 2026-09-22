import { chromium } from '@playwright/test';
import { mkdir, readdir, rm } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath, pathToFileURL } from 'node:url';

const projectRoot = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const fixtureDir = path.join(projectRoot, 'tests', 'fixtures');
const releasePath = path.join(
  projectRoot,
  'dist',
  'pdf_merger_bookmarks_v2.0.0.html',
);
const outputPath = path.join(
  projectRoot,
  'output',
  'pdf',
  'qa_merged_bookmarks.pdf',
);
const screenshotPath = path.join(projectRoot, 'tmp', 'pdfs', 'app_qa.png');
const mobileScreenshotPath = path.join(projectRoot, 'tmp', 'pdfs', 'app_qa_mobile.png');

const chromeCandidates = [
  process.env.BROWSER_PATH,
  'C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe',
  'C:\\Program Files (x86)\\Microsoft\\Edge\\Application\\msedge.exe',
].filter(Boolean);

const fixtureNames = await readdir(fixtureDir);
const betaName = fixtureNames.find((name) => name.endsWith('_Beta.pdf'));
if (!betaName) throw new Error('Unicode Beta fixture was not generated.');

const alphaPath = path.join(fixtureDir, 'Alpha_packet.pdf');
const betaPath = path.join(fixtureDir, betaName);

await mkdir(path.dirname(outputPath), { recursive: true });
await mkdir(path.dirname(screenshotPath), { recursive: true });
await rm(outputPath, { force: true });

let lastLaunchError;
let browser;
for (const executablePath of chromeCandidates) {
  try {
    browser = await chromium.launch({
      executablePath,
      headless: true,
      args: ['--allow-file-access-from-files'],
    });
    break;
  } catch (error) {
    lastLaunchError = error;
  }
}
if (!browser) throw lastLaunchError || new Error('No Chromium browser is available.');

const page = await browser.newPage({
  viewport: { width: 1440, height: 1100 },
  deviceScaleFactor: 1,
});

const consoleErrors = [];
const runtimeErrors = [];
const externalRequests = [];

page.on('console', (message) => {
  if (message.type() === 'error') consoleErrors.push(message.text());
});
page.on('pageerror', (error) => runtimeErrors.push(error.message));
page.on('request', (request) => {
  if (/^https?:/i.test(request.url())) externalRequests.push(request.url());
});
await page.route(/^https?:/i, (route) => route.abort());

function ensure(condition, message) {
  if (!condition) throw new Error(message);
}

try {
  await page.goto(pathToFileURL(releasePath).href, { waitUntil: 'load' });
  await page.waitForSelector('[data-testid="drop-zone"]');

  ensure(await page.title() === 'Atlas PDF Merger - Bookmarked PDF merging', 'Unexpected page title.');
  ensure(await page.locator('[data-testid="merge-button"]').isDisabled(), 'Merge must start disabled.');

  await page.locator('[data-testid="file-input"]').setInputFiles([alphaPath, betaPath]);
  await page.waitForFunction(
    () => document.querySelectorAll('[data-testid="file-card"]').length === 2,
  );
  await page.waitForFunction(
    () => !document.querySelector('[data-testid="merge-button"]').disabled,
  );

  const cards = page.locator('[data-testid="file-card"]');
  ensure((await cards.nth(0).locator('.source-name').textContent()).includes('Alpha_packet'), 'Initial Alpha order is wrong.');
  ensure((await cards.nth(1).locator('.source-name').textContent()).includes('_Beta.pdf'), 'Initial Beta order is wrong.');

  await cards.nth(1).getByRole('button', { name: /^Move .* up$/ }).click();
  const focusedAction = await page.evaluate(
    () => document.activeElement?.dataset.action,
  );
  ensure(focusedAction === 'move-down', 'Reorder control did not retain keyboard focus.');
  await cards.nth(0).getByRole('button', { name: /^Move .* down$/ }).click();
  await cards.nth(1).getByRole('button', { name: /^Move .* up$/ }).click();

  ensure((await cards.nth(0).locator('.source-name').textContent()).includes('_Beta.pdf'), 'Repeated reorder did not leave Beta first.');
  ensure((await cards.nth(1).locator('.source-name').textContent()).includes('Alpha_packet'), 'Repeated reorder did not leave Alpha second.');
  const orderBeforeSelfDrop = await cards.locator('.source-name').allTextContents();
  await cards.nth(0).dragTo(cards.nth(0));
  const orderAfterSelfDrop = await cards.locator('.source-name').allTextContents();
  ensure(JSON.stringify(orderAfterSelfDrop) === JSON.stringify(orderBeforeSelfDrop), 'Self-drop changed file order.');

  const bookmarkValues = await page
    .locator('[data-action="bookmark-title"]')
    .evaluateAll((inputs) => inputs.map((input) => input.value));
  ensure(bookmarkValues[0].endsWith('_Beta'), 'Unicode Beta bookmark title was not preserved.');
  ensure(bookmarkValues[1] === 'Alpha_packet', 'Alpha bookmark title is wrong.');
  ensure(await page.locator('#exportBookmarkCount').textContent() === '5', 'Expected two file bookmarks plus three source bookmarks.');

  await page.locator('#outputName').fill('qa_merged_bookmarks');
  await page.screenshot({ path: screenshotPath, fullPage: true });
  await page.setViewportSize({ width: 390, height: 844 });
  await page.screenshot({ path: mobileScreenshotPath, fullPage: true });
  const hasHorizontalOverflow = await page.evaluate(
    () => document.documentElement.scrollWidth > window.innerWidth + 1,
  );
  ensure(!hasHorizontalOverflow, 'Mobile layout has horizontal overflow.');
  ensure(await page.locator('.settings-panel').isVisible(), 'Mobile export settings are hidden.');
  await page.setViewportSize({ width: 1440, height: 1100 });

  const downloadPromise = page.waitForEvent('download');
  await page.locator('[data-testid="merge-button"]').click();
  const download = await downloadPromise;
  ensure(download.suggestedFilename() === 'qa_merged_bookmarks.pdf', 'Download filename is wrong.');
  await download.saveAs(outputPath);

  await page.waitForFunction(
    () => document.querySelector('[data-testid="status"]').textContent.includes('is ready'),
  );

  ensure(runtimeErrors.length === 0, `Runtime errors: ${runtimeErrors.join(' | ')}`);
  ensure(consoleErrors.length === 0, `Console errors: ${consoleErrors.join(' | ')}`);
  ensure(externalRequests.length === 0, `App made external requests: ${externalRequests.join(' | ')}`);

  console.log(
    JSON.stringify(
      {
        result: 'PASS',
        order: bookmarkValues,
        output: outputPath,
        screenshot: screenshotPath,
        offlineExternalRequests: externalRequests.length,
        mobileScreenshot: mobileScreenshotPath,
      },
      null,
      2,
    ),
  );
} finally {
  await browser.close();
}
