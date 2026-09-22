import test from 'node:test';
import assert from 'node:assert/strict';

import {
  PDFArray,
  PDFDict,
  PDFDocument,
  PDFHexString,
  PDFName,
  PDFRef,
} from 'pdf-lib';

import { addOutlineTree, countOutlineItems } from '../src/pdf/bookmarks.js';

const name = (value) => PDFName.of(value);

function requiredRef(dictionary, key, description) {
  const value = dictionary.get(name(key));
  assert.ok(value instanceof PDFRef, `${description} must be an indirect PDFRef`);
  return value;
}

function lookupDictionary(pdfDoc, ref, description) {
  const value = pdfDoc.context.lookup(ref);
  assert.ok(value instanceof PDFDict, `${description} must resolve to a PDFDict`);
  return value;
}

function assertSameRef(actual, expected, description) {
  assert.ok(actual instanceof PDFRef, `${description} must be a PDFRef`);
  assert.equal(actual.objectNumber, expected.objectNumber, `${description} object number`);
  assert.equal(actual.generationNumber, expected.generationNumber, `${description} generation`);
}

function assertBookmark(pdfDoc, dictionary, { title, pageIndex }) {
  const encodedTitle = dictionary.get(name('Title'));
  assert.ok(encodedTitle instanceof PDFHexString, `${title} must use PDFHexString`);
  assert.equal(encodedTitle.decodeText(), title, `${title} must survive save/load`);

  const destination = dictionary.get(name('Dest'));
  assert.ok(destination instanceof PDFArray, `${title} must have a destination array`);
  assertSameRef(
    destination.get(0),
    pdfDoc.getPage(pageIndex).ref,
    `${title} destination page`,
  );
}

test('writes a nested Unicode outline as linked indirect objects that saves cleanly', async () => {
  const pdfDoc = await PDFDocument.create();
  for (let pageIndex = 0; pageIndex < 4; pageIndex += 1) pdfDoc.addPage();

  const nodes = [
    {
      title: 'Résumé – 서울',
      pageIndex: 0,
      children: [
        { title: '子節 α', pageIndex: 1, children: [] },
        { title: 'مرحبا بالعالم', pageIndex: 2, children: [] },
      ],
    },
    { title: '終章 ✓', pageIndex: 3, children: [] },
  ];

  assert.equal(countOutlineItems(nodes), 4);
  assert.ok(addOutlineTree(pdfDoc, nodes, { openPanel: true }) instanceof PDFRef);

  let bytes;
  await assert.doesNotReject(async () => {
    bytes = await pdfDoc.save();
  }, 'a nested outline must not create a recursive object graph');

  const loaded = await PDFDocument.load(bytes);
  const catalogOutlineRef = loaded.catalog.get(name('Outlines'));
  assert.ok(catalogOutlineRef instanceof PDFRef, 'catalog Outlines must be a PDFRef');

  const pageMode = loaded.catalog.get(name('PageMode'));
  assert.ok(pageMode instanceof PDFName);
  assert.equal(pageMode.toString(), '/UseOutlines');

  const outlineRoot = lookupDictionary(loaded, catalogOutlineRef, 'outline root');
  const chapterOneRef = requiredRef(outlineRoot, 'First', 'outline root First');
  const chapterTwoRef = requiredRef(outlineRoot, 'Last', 'outline root Last');
  const chapterOne = lookupDictionary(loaded, chapterOneRef, 'first top-level item');
  const chapterTwo = lookupDictionary(loaded, chapterTwoRef, 'last top-level item');

  assertSameRef(requiredRef(chapterOne, 'Parent', 'chapter one Parent'), catalogOutlineRef, 'chapter one Parent');
  assertSameRef(requiredRef(chapterOne, 'Next', 'chapter one Next'), chapterTwoRef, 'chapter one Next');
  assertSameRef(requiredRef(chapterTwo, 'Parent', 'chapter two Parent'), catalogOutlineRef, 'chapter two Parent');
  assertSameRef(requiredRef(chapterTwo, 'Prev', 'chapter two Prev'), chapterOneRef, 'chapter two Prev');

  const childOneRef = requiredRef(chapterOne, 'First', 'chapter one First');
  const childTwoRef = requiredRef(chapterOne, 'Last', 'chapter one Last');
  const childOne = lookupDictionary(loaded, childOneRef, 'first child item');
  const childTwo = lookupDictionary(loaded, childTwoRef, 'last child item');

  assertSameRef(requiredRef(childOne, 'Parent', 'first child Parent'), chapterOneRef, 'first child Parent');
  assertSameRef(requiredRef(childOne, 'Next', 'first child Next'), childTwoRef, 'first child Next');
  assertSameRef(requiredRef(childTwo, 'Parent', 'last child Parent'), chapterOneRef, 'last child Parent');
  assertSameRef(requiredRef(childTwo, 'Prev', 'last child Prev'), childOneRef, 'last child Prev');

  assertBookmark(loaded, chapterOne, nodes[0]);
  assertBookmark(loaded, childOne, nodes[0].children[0]);
  assertBookmark(loaded, childTwo, nodes[0].children[1]);
  assertBookmark(loaded, chapterTwo, nodes[1]);
});

test('an empty outline tree leaves the catalog unchanged', async () => {
  const pdfDoc = await PDFDocument.create();
  pdfDoc.addPage();

  assert.equal(countOutlineItems([]), 0);
  assert.equal(addOutlineTree(pdfDoc, [], { openPanel: true }), null);
  assert.equal(pdfDoc.catalog.get(name('Outlines')), undefined);
  assert.equal(pdfDoc.catalog.get(name('PageMode')), undefined);

  const loaded = await PDFDocument.load(await pdfDoc.save());
  assert.equal(loaded.catalog.get(name('Outlines')), undefined);
  assert.equal(loaded.catalog.get(name('PageMode')), undefined);
});
