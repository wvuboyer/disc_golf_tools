import csv
import datetime
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from flask import Blueprint, render_template, flash, request, Response, redirect, url_for
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


payout_cards_bp = Blueprint('payout_cards', __name__)


@payout_cards_bp.route('/payout_cards', methods=["GET"])
def payout_cards_get():
    return render_template('payout_cards.html')


@payout_cards_bp.route('/payout_cards', methods=["POST"])
def payout_cards_post():
    tournament_id = request.form.get('tournamentId')
    if not tournament_id.isnumeric():
        flash("Invalid tournament ID", "danger")
        return redirect(url_for('payout_cards.payout_cards_get'))
    parameters = {'TournID': tournament_id}
    response = requests.get("https://www.pdga.com/apps/tournament/manager/payouts_projected", params=parameters)

    try:
        response.raise_for_status()
    except requests.exceptions.HTTPError:
        flash("Could not find that tournament ID", "danger")
        return redirect(url_for('payout_cards.payout_cards_get'))

    if "Payouts for this event have not been published." in str(response.content):
        flash("Payouts for this event have not been published.", "danger")
        return redirect(url_for('payout_cards.payout_cards_get'))

    soup = BeautifulSoup(response.content, 'html.parser')

    title_tag = soup.find('h1', class_='payout-print-title')
    event_title = title_tag.text.strip() if title_tag else "Title not found"

    division_tables = soup.find_all('table', class_='payout-print')
    payouts_data = []

    for table in division_tables:
        division_name = table.find('th').text.strip()
        if "MP" in division_name or "FP" in division_name:
            continue

        place_prize_rows = table.find_all('tr')[1:]

        for row in place_prize_rows:
            try:
                place_cell, prize_cell = row.find_all('td')
                place = place_cell.text.strip()
                prize = prize_cell.text.strip().replace(u'\xa0', u' ').replace(' ', '')

                if not place.isnumeric():
                    break

                payouts_data.append({'division': division_name, 'place': place, 'prize': prize})
            except ValueError:
                continue

    if len(payouts_data) == 0:
        flash("No divisions eligible for payouts were found.", "danger")
        return redirect(url_for('payout_cards.payout_cards_get'))

    output_filename = f"payout-cards-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

    # store in memory instead of writing to disk
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    # set the card dimensions
    width, height = letter
    card_height = height / 3

    pdfmetrics.registerFont(TTFont('Liberation Sans Bold', 'fonts/LiberationSans-Bold.ttf'))

    for i, card in enumerate(payouts_data):
        if i > 0 and i % 3 == 0:
            c.showPage()

        c.setFont("Liberation Sans Bold", 48)

        card_index_on_page = i % 3
        y_position = height - (card_index_on_page + 1) * card_height

        text_y_position = y_position + card_height - (0.75 * inch)

        c.drawString(0.5 * inch, text_y_position, card['division'].strip())

        c.setFont("Liberation Sans Bold", 48)
        c.drawRightString(width - 0.5 * inch, text_y_position, f"Place: {card['place'].strip()}")

        text_y_position = y_position + card_height - (2.5 * inch)
        c.setFont("Liberation Sans Bold", 75)
        c.drawCentredString(width * 0.5, text_y_position, f"Payout: {card['prize'].strip()}")

        text_y_position = y_position + (0.25 * inch)
        c.setFont("Liberation Sans Bold", 18)
        c.drawCentredString(width * 0.5, text_y_position, f"{event_title}")

        if card_index_on_page < 2 or (i == (len(payouts_data) - 1) and card_index_on_page < 2):
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
