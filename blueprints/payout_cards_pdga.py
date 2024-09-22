import csv
import datetime
import requests
from io import BytesIO
from pprint import pprint
from bs4 import BeautifulSoup
from flask import Blueprint, render_template, flash, request, Response, redirect, url_for
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.pdfgen import canvas
from reportlab.lib.units import inch
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


payout_cards_pdga_bp = Blueprint('payout_cards_pdga', __name__)


@payout_cards_pdga_bp.route('/payout_cards_pdga', methods=["GET"])
def payout_cards_get():
    return render_template('payout_cards_pdga.html')


@payout_cards_pdga_bp.route('/payout_cards_pdga', methods=["POST"])
def payout_cards_post():
    tournament_id = request.form.get('tournamentId')
    if not tournament_id.isnumeric():
        flash("Invalid tournament ID", "danger")
        return redirect(url_for('payout_cards.payout_cards_get'))
    
    parameters = {"TournID": tournament_id, "AdditionalEventInfo": "true"}
    tourney_result = requests.get(f"https://www.pdga.com/apps/tournament/live-api/live_results_fetch_event", params=parameters)
    tourney_json = tourney_result.json()

    tournament_name = tourney_json["data"]["Name"]
    tournament_location = tourney_json["data"]["Location"]
    tournament_rounds = tourney_json["data"]["Rounds"]
    tournament_date_range = tourney_json["data"]["DateRange"]
    tournament_tier = tourney_json["data"]["Tier"]

    divisions = {}
    for division in tourney_json["data"]["Divisions"]:
        divisions[division["Division"]] = {}
        divisions[division["Division"]]["players"] = division["Players"]
        divisions[division["Division"]]["name"] = division["ShortName"]
        divisions[division["Division"]]["results"] = []
        parameters = {"TournID": tournament_id, "Division": division['Division'], "Round": tournament_rounds}
        results_result = requests.get(
            f"https://www.pdga.com/apps/tournament/live-api/live_results_fetch_round", params=parameters)

        results_json = results_result.json()
        for score in results_json["data"]["scores"]:
            if not score["Prize"]:
                break
            divisions[division["Division"]]["results"].append(
                [
                    score["RunningPlace"],
                    score["Name"],
                    score["Tied"],
                    f"+ {score['ToPar']}" if score["ToPar"] > 0 else str(score["ToPar"])
                ]
            )
    
    tourney_info = f"{tournament_name}, a PDGA {tournament_tier} Tier."
    tourney_info_two = f"{tournament_location} on {tournament_date_range}."

    output_filename = f"payout-cards-{datetime.datetime.now().strftime('%Y%m%d%H%M%S')}.pdf"

    # store in memory instead of writing to disk
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=letter)

    width, height = letter  # keep for later
    for division in divisions:
        counter = 0
        ordinal = lambda n: str(n) + 'tsnrhtdd'[n % 5 * (n % 100 ^ 15 > 4 > n % 10)::4]
        for player in divisions[division]['results']:
            print(player)
            if counter % 2 == 0:
                if counter > 0:
                    c.showPage()
                c.setFont('Helvetica-Bold', 32)
                output_string = f"{division} - {ordinal(player[0])} Place"
                if player[3]:
                    output_string = f"{output_string} (TIED)"
                c.setFont('Helvetica-Bold', 32)
                c.drawString(1 * inch, 9.5 * inch, output_string)
                c.setFont('Helvetica-Bold', 28)
                c.drawString(1 * inch, 8.75 * inch, f"{player[1]} : {player[4]}")
                c.line(0, 5.5 * inch, 100 * inch, 5.5 * inch)
                c.setFont('Helvetica-Bold', 64)
                c.drawString(1 * inch, 7.5 * inch, player[2])
                c.setFont('Helvetica-Bold', 12)
                c.drawString(1 * inch, 6.75 * inch, tourney_info)
                c.drawString(1 * inch, 6.5 * inch, tourney_info_two)
            else:
                output_string = f"{division} - {ordinal(player[0])} Place"
                if player[3]:
                    output_string = f"{output_string} (TIED)"
                c.setFont('Helvetica-Bold', 32)
                c.drawString(1 * inch, 4 * inch, output_string)
                c.setFont('Helvetica-Bold', 28)
                c.drawString(1 * inch, 3.25 * inch, f"{player[1]} : {player[4]}")
                c.setFont('Helvetica-Bold', 64)
                c.drawString(1 * inch, 2 * inch, player[2])
                c.setFont('Helvetica-Bold', 12)
                c.drawString(1 * inch, 1.25 * inch, tourney_info)
                c.drawString(1 * inch, 1 * inch, tourney_info_two)
            counter += 1

    c.save()
    buffer.seek(0)
    response = Response(buffer, content_type='application/pdf')
    response.headers.set('Content-Disposition', 'attachment', filename=output_filename)
    return response
