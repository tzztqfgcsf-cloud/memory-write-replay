"""Regenerate the vector PDF for Figure 1. Requires reportlab; no model calls.

The counts are unchanged from the source manuscript. Candidate-variant wording
and exposure wording are aligned with the consolidated main text.
"""
from pathlib import Path
from reportlab.pdfgen.canvas import Canvas
from reportlab.lib.colors import HexColor, white, black
from reportlab.lib.styles import ParagraphStyle
from reportlab.platypus import Paragraph
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import os
import reportlab

ROOT = Path(__file__).resolve().parents[1]
W, H = 640, 414
FONT_DIR = Path(reportlab.__file__).resolve().parent / 'fonts'
FONT_MAP = {}
if all((FONT_DIR / p).exists() for p in ['Vera.ttf', 'VeraBd.ttf', 'VeraIt.ttf', 'VeraBI.ttf']):
    for old, new, filename in [('Times-Roman','FigureTimes','Vera.ttf'), ('Times-Bold','FigureTimes-Bold','VeraBd.ttf'), ('Times-Italic','FigureTimes-Italic','VeraIt.ttf'), ('Times-BoldItalic','FigureTimes-BoldItalic','VeraBI.ttf')]:
        pdfmetrics.registerFont(TTFont(new, str(FONT_DIR / filename)))
        FONT_MAP[old] = new
    pdfmetrics.registerFontFamily('FigureTimes', normal='FigureTimes', bold='FigureTimes-Bold', italic='FigureTimes-Italic', boldItalic='FigureTimes-BoldItalic')
c = Canvas(str(ROOT / 'media/figure_01.pdf'), pagesize=(W, H), pageCompression=1, initialFontName=FONT_MAP.get('Times-Roman', 'Times-Roman'))
c.setTitle('Figure 1: attribution, reference sensitivity, and decision exposure')
c.setAuthor('')
MUTED = HexColor('#6B6A66')
AGREE = HexColor('#8A9099')
ALLOW = HexColor('#C9CDD3')
LITERAL = HexColor('#8FB9EC')
WITNESS = HexColor('#2A78D6')
REMAIN = HexColor('#EB6834')

def text(x, top, string, font='Times-Roman', size=11.5, color=black, align='left'):
    c.setFont(FONT_MAP.get(font, font), size)
    c.setFillColor(color)
    y = H - top - size
    {'left': c.drawString, 'right': c.drawRightString, 'center': c.drawCentredString}[align](x, y, string)

def para(x, top, string, width, size=11, leading=13, color=black, max_height=60):
    p = Paragraph(string, ParagraphStyle('p', fontName=FONT_MAP.get('Times-Roman','Times-Roman'), fontSize=size, leading=leading, textColor=color))
    _, height = p.wrap(width, max_height)
    assert height <= max_height, (string, height, max_height)
    p.drawOn(c, x, H-top-height)

def rect(x, top, w, h, color, stroke=False):
    c.setFillColor(color)
    c.setStrokeColor(color if stroke else black)
    c.rect(x, H-top-h, w, h, fill=not stroke, stroke=stroke)

def frame(top, title, subtitle):
    c.setStrokeColor(black)
    c.setLineWidth(.7)
    c.rect(.4, H-top-124, W-.8, 124, fill=0, stroke=1)
    text(12, top+8, title, 'Times-Bold', 13)
    text(12, top+27, subtitle, size=10.6, color=MUTED)

frame(0, 'A  Attribution: recovery need not require evidence checks', 'Gemini 2.5 Flash, same saved proposals')
para(12, 46, '<i>Final-state reading:</i> evidence checks add 33 points.', 304, max_height=29)
para(12, 67, '<b>Replay:</b> Allow recovers the same 11 corrections; in 16 of 17 traced holds, the corrected tuple was missing from both fact lists.', 301, max_height=53)
for idx, (label, val, color) in enumerate([('AGREE',22,AGREE),('ALLOW',33,ALLOW),('LITERAL',33,LITERAL),('WITNESS',33,WITNESS)]):
    y = 29 + 19*idx
    text(406, y, label, size=10.5, align='right')
    rect(415, y, val*4.85, 13, color)
    text(420+val*4.85, y, f'{val} / 33', size=11)
text(415, 106, 'corrections completed', size=10, color=MUTED)

frame(135, 'B  Specification: avoided violations include candidate variants', '21 configurations, same saved Review proposals')
para(12, 181, '<i>Final-state reading:</i> the gate cuts violations from 146 to 64.', 304, max_height=29)
para(12, 211, '<b>Replay:</b> 71 of the 82 come from append holds shared by every rule; 52 meet mechanical candidate-variant criteria.', 301, max_height=44)
text(337, 163, '146 reference-violating states; 82 avoided', size=10.5)
scale=243/146
x=337
for n,color in [(64,REMAIN),(52,ALLOW),(19,AGREE),(11,WITNESS)]:
    rect(x,184,n*scale,17,color)
    c.setStrokeColor(white)
    c.setLineWidth(.6)
    c.line(x,H-184,x,H-201)
    x+=n*scale
text(337+32*scale,186,'64',size=10,align='center')
text(337+90*scale,186,'52 candidates',size=9.5,align='center')
text(337+125.5*scale,186,'19',size=10,color=white,align='center')
text(337+140.5*scale,186,'11',size=10,color=white,align='center')
text(337,205,'64 remain',size=9.8,color=MUTED)
text(501,205,'71 append holds',size=9,color=MUTED,align='center')
para(570,204,'11 correction<br/>holds',57,size=8.3,leading=9.5,color=MUTED,max_height=20)
para(337,225,'Candidate variant: a mechanical match in subject or value form; semantic equivalence unvalidated.',288,size=10.1,leading=11.7,color=MUTED,max_height=29)

frame(270, 'C  Opportunity: many rule ties have zero exposure', 'Configurations whose proposals reach the held set H')
para(12,316,'<i>Final-state reading:</i> the rules are equivalent.',304,max_height=29)
para(12,341,'<b>Replay:</b> on hollow configurations no proposal reached H, so these outputs do not test distinguishing decisions.',301,max_height=44)
for y,label,exposed in [(300,'Controlled-path proposals',9),(342,'Review proposals',5)]:
    text(337,y,label,size=10.5)
    text(626,y,f'{21-exposed} of 21 unexposed',size=10.5,align='right')
    for i in range(21):
        x=337+i*13.65
        if i<exposed:
            rect(x,y+18,9.7,9.7,WITNESS)
        else:
            c.setLineWidth(.9)
            rect(x+.45,y+18.45,8.8,8.8,MUTED,stroke=True)
text(482,380,'same 21 configurations in both rows',size=9.8,color=MUTED,align='center')
text(.6,401,'Counts pool three repetitions. Reference violations follow the frozen state specification.',font='Times-Italic',size=10.1,color=MUTED)
c.showPage()
c.save()
print(ROOT / 'media/figure_01.pdf')
