from __future__ import annotations

import io
import typing


from pypdf import PdfReader, PdfWriter
from pdfminer.converter import TextConverter
from pdfminer.layout import LAParams
from pdfminer.pdfdocument import PDFDocument
from pdfminer.pdfinterp import PDFPageInterpreter, PDFResourceManager
from pdfminer.pdfpage import PDFPage
from pdfminer.pdfparser import PDFParser

if typing.TYPE_CHECKING:
    from PyPDF2 import PageObject
    from collections.abc import Iterator

def pdf_page_iterator(pdf_file: str) -> Iterator:
    """Iterate over pdf pages returning byte arrays containing each page."""
    yield from PdfReader(pdf_file, strict=False).pages


def extract_text(page: PageObject) -> str:
    """Extract a string with the text from a byte array of a pdf page."""
    pdf_page_bytes = get_page_bytes(page)
    output_string = io.StringIO()
    # with open(sys.argv[1], 'rb') as in_file:
    parser = PDFParser(pdf_page_bytes)
    doc = PDFDocument(parser)
    rsrcmgr = PDFResourceManager()
    device = TextConverter(rsrcmgr, output_string, laparams=LAParams())
    interpreter = PDFPageInterpreter(rsrcmgr, device)
    for new_page in PDFPage.create_pages(doc):
        interpreter.process_page(new_page)
    return output_string.getvalue()


def get_page_bytes(page: PageObject) -> typing.BinaryIO:
    output = PdfWriter()
    output.add_page(page)
    out = io.BytesIO()
    output.write(out)
    return out
