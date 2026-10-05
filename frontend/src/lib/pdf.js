import * as pdfjsLib from 'pdfjs-dist';
// Vite: bundle the worker as a URL asset and point pdf.js at it.
import pdfWorkerUrl from 'pdfjs-dist/build/pdf.worker.min.mjs?url';

pdfjsLib.GlobalWorkerOptions.workerSrc = pdfWorkerUrl;

/**
 * Processes a PDF file entirely in the browser, extracting one
 * "document" (text + metadata) per page. This mirrors the shape the
 * ingestion graph / retrieval graph expect (`pageContent` + `metadata`),
 * including `metadata.loc.pageNumber`, which the chat UI uses to show
 * source citations.
 *
 * @param {File} file - The PDF file to process.
 * @returns {Promise<Array<{pageContent: string, metadata: object}>>}
 */
export async function processPDF(file) {
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  const docs = [];
  for (let pageNumber = 1; pageNumber <= pdf.numPages; pageNumber++) {
    const page = await pdf.getPage(pageNumber);
    const textContent = await page.getTextContent();
    const pageText = textContent.items.map((item) => item.str).join(' ');

    docs.push({
      pageContent: pageText,
      metadata: {
        source: file.name,
        filename: file.name,
        loc: { pageNumber },
      },
    });
  }

  return docs;
}
