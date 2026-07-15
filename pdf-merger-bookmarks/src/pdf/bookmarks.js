import {
  PDFArray,
  PDFDict,
  PDFHexString,
  PDFName,
  PDFNumber,
  PDFRef,
} from 'pdf-lib';

const NAMES = {
  count: PDFName.of('Count'),
  dest: PDFName.of('Dest'),
  first: PDFName.of('First'),
  last: PDFName.of('Last'),
  next: PDFName.of('Next'),
  outlines: PDFName.of('Outlines'),
  pageMode: PDFName.of('PageMode'),
  parent: PDFName.of('Parent'),
  prev: PDFName.of('Prev'),
  title: PDFName.of('Title'),
  type: PDFName.of('Type'),
};

export function countOutlineItems(nodes = []) {
  return nodes.reduce(
    (total, node) => total + 1 + countOutlineItems(node.children || []),
    0,
  );
}

function cleanTitle(value) {
  const title = String(value ?? '')
    .replace(/\u0000/g, '')
    .replace(/\s+/g, ' ')
    .trim();
  return (title || 'Untitled bookmark').slice(0, 512);
}

function isValidPageIndex(pdfDoc, pageIndex) {
  return Number.isInteger(pageIndex)
    && pageIndex >= 0
    && pageIndex < pdfDoc.getPageCount();
}

function registerLevel(pdfDoc, nodes, parentRef) {
  const { context } = pdfDoc;
  const safeNodes = nodes.filter((node) => isValidPageIndex(pdfDoc, node.pageIndex));

  const entries = safeNodes.map((node) => {
    const destination = PDFArray.withContext(context);
    destination.push(pdfDoc.getPage(node.pageIndex).ref);
    destination.push(PDFName.of('Fit'));

    const dictionary = PDFDict.withContext(context);
    dictionary.set(NAMES.title, PDFHexString.fromText(cleanTitle(node.title)));
    dictionary.set(NAMES.parent, parentRef);
    dictionary.set(NAMES.dest, destination);

    return {
      node,
      dictionary,
      ref: context.register(dictionary),
      descendantCount: 0,
    };
  });

  entries.forEach((entry, index) => {
    if (index > 0) entry.dictionary.set(NAMES.prev, entries[index - 1].ref);
    if (index + 1 < entries.length) entry.dictionary.set(NAMES.next, entries[index + 1].ref);

    const children = registerLevel(pdfDoc, entry.node.children || [], entry.ref);
    if (children.entries.length > 0) {
      entry.dictionary.set(NAMES.first, children.entries[0].ref);
      entry.dictionary.set(NAMES.last, children.entries.at(-1).ref);
      entry.dictionary.set(NAMES.count, PDFNumber.of(children.totalCount));
      entry.descendantCount = children.totalCount;
    }
  });

  return {
    entries,
    totalCount: entries.reduce(
      (total, entry) => total + 1 + entry.descendantCount,
      0,
    ),
  };
}

export function addOutlineTree(pdfDoc, nodes = [], { openPanel = true } = {}) {
  if (nodes.length === 0 || pdfDoc.getPageCount() === 0) return null;

  const { context } = pdfDoc;
  const outlineRoot = PDFDict.withContext(context);
  outlineRoot.set(NAMES.type, PDFName.of('Outlines'));
  const outlineRootRef = context.register(outlineRoot);

  const level = registerLevel(pdfDoc, nodes, outlineRootRef);
  if (level.entries.length === 0) return null;

  outlineRoot.set(NAMES.first, level.entries[0].ref);
  outlineRoot.set(NAMES.last, level.entries.at(-1).ref);
  outlineRoot.set(NAMES.count, PDFNumber.of(level.totalCount));

  pdfDoc.catalog.set(NAMES.outlines, outlineRootRef);
  if (openPanel) pdfDoc.catalog.set(NAMES.pageMode, PDFName.of('UseOutlines'));

  return outlineRootRef;
}

export function isIndirectReference(value) {
  return value instanceof PDFRef;
}
