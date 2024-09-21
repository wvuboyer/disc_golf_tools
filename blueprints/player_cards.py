import csv
import datetime
from io import BytesIO
from flask import Blueprint, render_template, flash, request, Response
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


player_cards_bp = Blueprint('player_cards', __name__)


@player_cards_bp.route('/player_cards', methods=["GET"])
def player_cards_get():
    return render_template('player_cards.html')


@player_cards_bp.route('/player_cards', methods=["POST"])
def player_cards_post():
    def validate_csv(csv_data):
        if len(csv_data.splitlines()) > 1000:
            return False
        for line in csv_data.splitlines():
            parts = line.split(',')
            if len(parts) != 2 or len(parts[0].strip()) > 32 or len(parts[1].strip()) > 5:
                return False
        reader = csv.reader(csv_data.splitlines())
        for row in reader:
            if len(row) != 2 or not row[0].strip():
                return False
        return True

    def fit_text_to_width(text, max_width, canvas, font_name='Liberation Sans Bold', initial_font_size=48):
        current_font_size = initial_font_size

        while True:
            canvas.setFont(font_name, current_font_size)
            text_width = canvas.stringWidth(text, font_name, current_font_size)

            if text_width <= max_width:
                break
            else:
                current_font_size -= 1

        return current_font_size

    csv_data = request.form.get('playerData')

    if validate_csv(csv_data):
        reader = csv.reader(csv_data.splitlines())
        cards_text = [{'name': row[0], 'division': row[1]} for row in reader]
        output_filename = f"cards-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

        # store in memory instead of writing to disk
        buffer = BytesIO()
        c = canvas.Canvas(buffer, pagesize=letter)

        # set the card dimensions
        width, height = letter
        card_height = height / 3

        pdfmetrics.registerFont(TTFont('Liberation Sans Bold', 'fonts/LiberationSans-Bold.ttf'))

        for i, card in enumerate(cards_text):
            if i > 0 and i % 3 == 0:
                c.showPage()

            c.setFont("Liberation Sans Bold", fit_text_to_width(card['name'], 5.5 * inch, c))

            card_index_on_page = i % 3
            y_position = height - (card_index_on_page + 1) * card_height

            text_y_position = y_position + card_height - (0.75 * inch)

            c.drawString(0.5 * inch, text_y_position, card['name'].strip())

            c.setFont("Liberation Sans Bold", 48)
            c.drawRightString(width - 0.5 * inch, text_y_position, card['division'].strip())

            if card_index_on_page < 2 or (i == (len(cards_text) - 1) and card_index_on_page < 2):
                c.setDash(1, 20)
                c.setStrokeColor(colors.black)
                line_y_position = y_position
                c.line(0.25 * inch, line_y_position, width - 0.25 * inch, line_y_position)
                c.setDash()

        c.save()
        buffer.seek(0)
        response = Response(buffer, content_type='application/pdf')
        response.headers.set('Content-Disposition', 'attachment', filename=output_filename)
        return response
    else:
        flash('Invalid CSV data. Please check the format.', 'danger')
        return render_template('player_cards.html', csv_data=csv_data)
