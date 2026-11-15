"""Apply the plain-language findings to the existing seven-slide PDF.

Usage: python scripts/revise_detailed_deck.py ORIGINAL.pdf OUTPUT.pdf
The original pages are retained; updated language is selectable PDF text.
"""

import sys
from io import BytesIO

import fitz
from reportlab.lib.utils import ImageReader
from reportlab.pdfgen import canvas
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


BACKGROUND = (7 / 255, 13 / 255, 21 / 255)
WHITE = (235 / 255, 242 / 255, 250 / 255)
CYAN = (126 / 255, 221 / 255, 249 / 255)
MUTED = (166 / 255, 185 / 255, 207 / 255)


def cover(page, rect):
    x0, y0, x1, y1 = rect
    page.setFillColorRGB(*BACKGROUND)
    page.rect(x0, 540 - y1, x1 - x0, y1 - y0, fill=1, stroke=0)


def line(page, point, text, size, color, *, bold=False):
    font = "DejaVu-Bold" if bold else "DejaVu"
    page.setFillColorRGB(*color)
    page.setFont(font, size)
    page.drawString(point[0], 540 - point[1], text)


def main():
    if len(sys.argv) != 3:
        raise SystemExit("Usage: revise_detailed_deck.py ORIGINAL.pdf OUTPUT.pdf")

    original = fitz.open(sys.argv[1])
    if len(original) != 7:
        raise ValueError("NASA submission deck must contain exactly seven slides")

    pdf = canvas.Canvas(sys.argv[2], pagesize=(960, 540))
    pdfmetrics.registerFont(TTFont("DejaVu", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"))
    pdfmetrics.registerFont(TTFont("DejaVu-Bold", "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"))
    pdf.setTitle("Analog Coverage Gap Map — 7-slide NASA Space Apps demonstration")

    for slide_number, source_page in enumerate(original):
        # Use the original full-page artwork; retain all figures and the seven-page format.
        pix = source_page.get_pixmap(matrix=fitz.Matrix(1280 / 960, 1280 / 960), alpha=False)
        pdf.drawImage(ImageReader(BytesIO(pix.tobytes("png"))), 0, 0, width=960, height=540)
        if slide_number == 0:
            cover(pdf, (43, 222, 625, 388))
            line(pdf, (48, 252), "Are our Earth field-test sites", 25, CYAN, bold=True)
            line(pdf, (48, 283), "a match for Moon terrain?", 25, CYAN, bold=True)
            line(pdf, (48, 330), "We check known sites, reveal missing shape matches,", 16, WHITE)
            line(pdf, (48, 354), "and surface new places worth investigating.", 16, WHITE)
        elif slide_number == 4:
            cover(pdf, (45, 460, 920, 525))
            line(pdf, (48, 480), "The gap is in this reference list, not proof that no suitable place exists on Earth.", 15, CYAN)
            line(pdf, (48, 504), "All counts refer to sampled windows and one fixed shape threshold.", 13, MUTED)
        elif slide_number == 6:
            cover(pdf, (40, 27, 927, 521))
            line(pdf, (48, 65), "Why the result matters", 31, WHITE, bold=True)
            line(pdf, (48, 122), "Known Earth analog sites may miss the terrain shapes", 22, WHITE)
            line(pdf, (48, 150), "of specific lunar targets.", 22, WHITE)
            line(pdf, (48, 207), "What we found", 20, CYAN, bold=True)
            line(pdf, (48, 243), "60 of 145 sampled Moon squares have no match in our known-site list.", 17, WHITE)
            line(pdf, (48, 270), "A search of 300 more Earth locations finds possible leads for six.", 17, WHITE)
            line(pdf, (48, 322), "What changes", 20, CYAN, bold=True)
            line(pdf, (48, 357), "Researchers can inspect a candidate, its nearest known-site alternative,", 17, WHITE)
            line(pdf, (48, 384), "and the measured differences before deciding what to check on the ground.", 17, WHITE)
            line(pdf, (48, 431), "Not yet a validated site-selection method; two tests failed, one was inconclusive.", 14, MUTED)
            line(pdf, (48, 479), "Explore: ronnieurhomie.github.io/analog-coverage-gap-map/", 15, CYAN)
            line(pdf, (48, 506), "NASA Space Apps 2026  |  Ron  |  Analog Intelligence", 12, MUTED)
        pdf.showPage()

    pdf.save()
    original.close()


if __name__ == "__main__":
    main()
