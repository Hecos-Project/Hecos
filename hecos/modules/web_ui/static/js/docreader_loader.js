/**
 * Hecos Document Reader — Document Loaders
 * PDF.js loader, PDF text & page extraction, HTML/MD/TXT document parsing.
 */

(function() {
    'use strict';

    let _pdfjsLoaded = false;

    function loadPDFJS(callback) {
        if (window.pdfjsLib) {
            if (!window.pdfjsLib.GlobalWorkerOptions.workerSrc) {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = 
                    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
            }
            _pdfjsLoaded = true;
            if (callback) callback();
            return;
        }
        const fallbackScript = document.createElement('script');
        fallbackScript.src = 'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.min.js';
        fallbackScript.onload = () => {
            if (window.pdfjsLib) {
                window.pdfjsLib.GlobalWorkerOptions.workerSrc = 
                    'https://cdnjs.cloudflare.com/ajax/libs/pdf.js/3.11.174/pdf.worker.min.js';
                _pdfjsLoaded = true;
                if (callback) callback();
            }
        };
        fallbackScript.onerror = () => {
            console.error('[DocReader] Failed to load PDF.js');
        };
        document.head.appendChild(fallbackScript);
    }

    async function loadPDFDocument(url, sessionId) {
        const STATE = (window.DocReaderState && window.DocReaderState.state) ? window.DocReaderState.state : {};
        return new Promise((resolve, reject) => {
            loadPDFJS(async () => {
                try {
                    const loadingTask = window.pdfjsLib.getDocument({ url: url, withCredentials: true });
                    const pdf = await loadingTask.promise;
                    if (sessionId && STATE._sessionId !== sessionId) {
                        try { pdf.destroy(); } catch (e) {}
                        return reject(new Error('Document session expired'));
                    }
                    const pages = [];
                    
                    for (let i = 1; i <= pdf.numPages; i++) {
                        if (sessionId && STATE._sessionId !== sessionId) {
                            try { pdf.destroy(); } catch (e) {}
                            return reject(new Error('Document session expired'));
                        }
                        const page = await pdf.getPage(i);
                        const textContent = await page.getTextContent();
                        const pageText = textContent.items
                            .map(item => item.str)
                            .join(' ')
                            .replace(/\s+/g, ' ')
                            .trim();
                        // Always include page so images & canvas render even for pure comic/image pages
                        pages.push({
                            pageNum: i,
                            text: pageText || '',
                            pdfPage: page,
                            textContent: textContent
                        });
                    }
                    resolve({ pages: pages, pdfDoc: pdf, docType: 'pdf' });
                } catch (e) {
                    reject(e);
                }
            });
        });
    }

    async function loadTextDocument(url, ext, rawFilePath) {
        const response = await fetch(url);
        const text = await response.text();
        
        if (ext === 'html' || ext === 'htm') {
            const parser = new DOMParser();
            const doc = parser.parseFromString(text, 'text/html');
            doc.querySelectorAll('script').forEach(el => el.remove());

            // Rewrite relative images to /api/local_file
            const basePath = rawFilePath ? rawFilePath.substring(0, rawFilePath.lastIndexOf('/') + 1) : '';
            doc.querySelectorAll('img').forEach(img => {
                const src = img.getAttribute('src');
                if (src && !src.startsWith('http://') && !src.startsWith('https://') && !src.startsWith('data:') && !src.startsWith('/api/')) {
                    if (basePath) {
                        img.src = `/api/local_file?path=${encodeURIComponent(basePath + src)}`;
                    }
                }
                img.style.maxWidth = '100%';
                img.style.borderRadius = '8px';
                img.style.margin = '12px 0';
                img.style.boxShadow = '0 4px 16px rgba(0,0,0,0.3)';
            });

            const bodyHtml = doc.body ? doc.body.innerHTML : text;
            const bodyText = doc.body ? doc.body.innerText : text;
            return {
                pages: [{
                    pageNum: 1,
                    text: bodyText.trim(),
                    htmlContent: bodyHtml
                }],
                docType: 'html'
            };
        }

        if (ext === 'md') {
            const basePath = rawFilePath ? rawFilePath.substring(0, rawFilePath.lastIndexOf('/') + 1) : '';
            let renderedHtml = text
                .replace(/!\[([^\]]*)\]\(([^)]+)\)/g, (match, alt, src) => {
                    let fullSrc = src;
                    if (!src.startsWith('http') && !src.startsWith('data:') && !src.startsWith('/api/')) {
                        if (basePath) fullSrc = `/api/local_file?path=${encodeURIComponent(basePath + src)}`;
                    }
                    return `<div style="text-align:center;margin:16px 0;"><img src="${fullSrc}" alt="${alt}" style="max-width:100%;border-radius:8px;box-shadow:0 4px 20px rgba(0,0,0,0.4);"/><div style="font-size:0.8em;opacity:0.6;margin-top:4px;">${alt}</div></div>`;
                })
                .replace(/^### (.*$)/gim, '<h3 style="color:#c4b5fd;margin:16px 0 8px;">$1</h3>')
                .replace(/^## (.*$)/gim, '<h2 style="color:#a78bfa;margin:20px 0 10px;">$1</h2>')
                .replace(/^# (.*$)/gim, '<h1 style="color:#8b5cf6;margin:24px 0 12px;">$1</h1>')
                .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
                .replace(/\*(.*?)\*/g, '<em>$1</em>');

            return {
                pages: [{
                    pageNum: 1,
                    text: text.trim(),
                    htmlContent: renderedHtml
                }],
                docType: 'md'
            };
        }

        return {
            pages: [{ pageNum: 1, text: text.trim() }],
            docType: 'txt'
        };
    }

    window.DocReaderLoader = {
        loadPDFJS,
        loadPDFDocument,
        loadTextDocument
    };

})();
