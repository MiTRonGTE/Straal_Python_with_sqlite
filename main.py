# coding: utf-8
# uvicorn main:app
# pytest test.py

import string
from fastapi import FastAPI, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse, HTMLResponse
from models import *  # modele porzyjmowanych danych
from database_operations import *
from utils import *

app = FastAPI()

id_payment_info = {}
Acce_Char = string.ascii_letters + " '-"  # znaki  dozwolone w imieniu i nazwisku
customer_id = None


# zamiana błędu nieprawidłowych danych z 422 do 400
@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    return PlainTextResponse(str(exc), status_code=400)


@app.on_event("startup")
async def startup():
    app.db_connection = sqlite3.connect("database.db")
    app.db_connection.text_factory = lambda b: b.decode(errors="ignore")  # northwind specific


@app.on_event("shutdown")
async def shutdown():
    app.db_connection.close()


# funkcja przekształcająca pay_by_link dla klienta
def pay_by_link_requester(pbl_array, creation_date, raport=False):
    # potwierdzenie czy został wysłany pbl
    if pbl_array is None:
        return

    # odczyt kolejnych pbl z listy pbl_array
    for i in range(len(pbl_array)):
        pbl = pbl_array[i]

        # walidacja currency (waluta)
        try_currency(pbl.currency)

        # przekonwertowanie daty do UTC i pobranie waluty z danego dnia
        utc_date = get_utc_time(pbl.created_at)
        exchange_rate = get_exchange_rate(pbl.currency, utc_date)

        # składanie response_pbl
        try:
            converted_pbl = {}
            if pbl.customer_id and raport:
                converted_pbl["customer_id"] = pbl.customer_id

            converted_pbl.update({
                    "date": utc_date,
                    "type": "pay_by_link",
                    "payment_mean": pbl.bank,
                    "description": pbl.description,
                    "currency": pbl.currency.upper(),
                    "amount": pbl.amount,
                    "amount_in_pln": (int(pbl.amount) * exchange_rate)//1,
                })
            send_report_to_db(converted_pbl, creation_date, raport)
            app.last_payment_info.append(converted_pbl)
        except:
            raise HTTPException(status_code=400)


# funkcja przekształcająca dp dla klienta
def dp_requester(dp_array, creation_date, raport=False):
    # potwierdzenie czy został wysłany dp
    if dp_array is None:
        return

    # odczyt kolejnych dp z listy dp_array
    for i in range(len(dp_array)):
        dp = dp_array[i]

        # walidacja currency (waluta)
        try_currency(dp.currency)

        # przekonwertowanie daty do UTC i pobranie waluty z danego dnia
        utc_date = get_utc_time(dp.created_at)
        exchange_rate = get_exchange_rate(dp.currency, utc_date)

        # składanie response_dp
        try:
            converted_dp = {}
            if dp.customer_id and raport:
                converted_dp["customer_id"] = dp.customer_id
            converted_dp.update({
                "date": utc_date,
                "type": "dp",
                "payment_mean": dp.iban,
                "description": dp.description,
                "currency": dp.currency.upper(),
                "amount": dp.amount,
                "amount_in_pln": (int(dp.amount) * exchange_rate)//1,
            })
            send_report_to_db(converted_dp, creation_date, raport)
            app.last_payment_info.append(converted_dp)
        except:
            raise HTTPException(status_code=400)


# funkcja przekształcająca card dla klienta
def card_requester(card_array, creation_date, raport=False):
    # potwierdzenie czy został wysłany dp
    if card_array is None:
        return

    # odczyt kolejnych card z listy card_array
    for i in range(len(card_array)):
        card = card_array[i]

        # walidacja cardholder_name i cardholder_surname czy nie zawierają niedozwolonych znaków
        for name in [card.cardholder_name, card.cardholder_surname]:
            for test in name:
                if test not in Acce_Char:
                    raise HTTPException(status_code=400)

        # walidacja currency (waluta)
        try_currency(card.currency)

        # przekonwertowanie daty do UTC i pobranie waluty z danego dnia
        utc_date = get_utc_time(card.created_at)
        exchange_rate = get_exchange_rate(card.currency, utc_date)

        # składanie response_card
        try:
            int(card.card_number)
            converted_card = {}
            if card.customer_id and raport:
                converted_card["customer_id"] = card.customer_id

            converted_card.update({
                "date": utc_date,
                "type": "card",
                "payment_mean": f"{card.cardholder_name.title()} {card.cardholder_surname.title()}"
                                f" {card.card_number[:4] + 8 * '*' + card.card_number[-4:]}",
                "description": card.description,
                "currency": card.currency.upper(),
                "amount": card.amount,
                "amount_in_pln": (int(card.amount) * exchange_rate) // 1,
            })
            send_report_to_db(converted_card, creation_date, raport)
            app.last_payment_info.append(converted_card)
        except:
            raise HTTPException(status_code=400)


# potwierdzenie że wszystkie wysłane id klienta są takie same a następnie zwrócenie id_customer
def try_id(pbl, dp, card):

    if len(pbl) > 0 and pbl[0].customer_id:
        id_customer = pbl[0].customer_id
    elif len(dp) > 0 and dp[0].customer_id:
        id_customer = dp[0].customer_id
    elif len(card) > 0 and card[0].customer_id:
        id_customer = card[0].customer_id
    else:
        raise HTTPException(status_code=400)

    pbl_len = len(pbl)
    dp_len = len(dp)
    card_len = len(card)
    max_len = max(pbl_len, dp_len, card_len)

    for i in range(max_len):
        if i < pbl_len and pbl[i].customer_id != id_customer and type(pbl[i].customer_id) != int:
            raise HTTPException(status_code=400)
        if i < dp_len and dp[i].customer_id != id_customer and type(dp[i].customer_id) != int:
            raise HTTPException(status_code=400)
        if i < card_len and card[i].customer_id != id_customer and type(card[i].customer_id) != int:
            raise HTTPException(status_code=400)

    return id_customer


def send_report_to_db(converted, creation_date, raport: bool):
    if not raport:
        return
    save_report(app, converted, creation_date)


def try_id_database(tested_id: int, category: str):
    return test_id(app, category, tested_id) is not None


def add_to_last_report_for_customer(customer_id, creation_date):
    if not try_id_database(customer_id, "LastReportForCustomer"):
        insert_last_report(app, customer_id, creation_date)

    elif try_id_database(customer_id, "LastReportForCustomer"):
        update_last_report(app, customer_id, creation_date)


def get_last_report_for_customer(customer_id):
    if not try_id_database(customer_id, "LastReportForCustomer"):
        raise HTTPException(status_code=400)

    last_report_date = get_last_report_date(app, customer_id)
    if last_report_date is None:
        raise HTTPException(status_code=400)

    last_report = get_report_for_customer_by_date(app, customer_id, last_report_date["LastReportDate"])
    if last_report is None:
        raise HTTPException(status_code=400)

    return last_report


@app.get("/", response_class=HTMLResponse)
def root():
    return """
    <title> Straal Python Kamil Pawlicki Recruitment Task</title>
    <h1 style="color: #5e9ca0;"><span style="color: #666699;">Kamil Pawlicki</span></h1>
        <ul>
            <li><strong>Github</strong> - <a href="https://github.com/MiTRonGTE/Straal_Python_with_sqlite">https://github.com/MiTRonGTE/Straal_Python_with_sqlite</a></li>
            <li><strong>Heroku</strong> - <a href="https://recruitment-task-straal-db.herokuapp.com/">https://recruitment-task-straal-db.herokuapp.com/</a></li>
        </ul>
    """


# endpoint pobierajacy dane o płatnością i konwertuje je do raportu
@app.post("/report")
async def report_post_func(report: RequestReport):
    app.last_payment_info = []
    pay_by_link_requester(report.pay_by_link, None)
    dp_requester(report.dp, None)
    card_requester(report.card, None)
    app.last_payment_info.sort(key=get_date)
    return app.last_payment_info


# endpoint pobierajacy dane o płatnością i konwertuje je z dodatkowym przypisaniem id do raportu
@app.post("/customer-report")
async def report_pay_id(report: RequestReport):
    app.last_payment_info = []
    data_req = datetime.utcnow()

    if report.pay_by_link is None:
        report.pay_by_link = []
    pay_by_link_requester(report.pay_by_link, data_req, True)
    if report.dp is None:
        report.dp = []
    dp_requester(report.dp, data_req,  True)
    if report.card is None:
        report.card = []
    card_requester(report.card, data_req, True)
    
    app.last_payment_info.sort(key=get_date)

    c_id = try_id(report.pay_by_link, report.dp, report.card)
    add_to_last_report_for_customer(c_id, data_req)
    id_payment_info[c_id] = app.last_payment_info
    app.last_payment_info.sort(key=get_date)
    return app.last_payment_info


# endpoint wyświetlający raport dla wskazanego id
@app.get("/customer-report/{customer_id}")
async def customer_report_id(customer_id: int):

    data = get_last_report_for_customer(customer_id)
    if data:
        return data
    else:
        raise HTTPException(status_code=400)
