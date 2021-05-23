import sqlite3


def save_report(app, converted, creation_date):
    app.db_connection.execute(
        f"""INSERT INTO Report
            (CustomerID, Date, Type, PaymentMean, Description, Currency, Amount, AmountInPln, CreationDate)
            VALUES ({converted['customer_id']}, '{converted['date']}', '{converted['type']}',
            '{converted['payment_mean']}', '{converted['description']}', '{converted['currency']}',
            {converted['amount']}, {converted['amount_in_pln']}, '{creation_date}')""")
    app.db_connection.commit()


def test_id(app, table, tested_id):
    app.db_connection.row_factory = sqlite3.Row
    return app.db_connection.execute(
        f"SELECT 1 FROM {table} WHERE CustomerID = {tested_id}").fetchone()


def insert_last_report(app, customer_id, creation_date):
    app.db_connection.execute(
        f"""INSERT INTO LastReportForCustomer (CustomerID, LastReportDate)
                VALUES ({customer_id}, '{creation_date}')""")
    app.db_connection.commit()


def update_last_report(app, customer_id, creation_date):
    app.db_connection.execute(
        f"""UPDATE LastReportForCustomer SET LastReportDate = '{creation_date}' WHERE CustomerID = {customer_id}""")
    app.db_connection.commit()


def get_last_report_date(app, customer_id):
    return app.db_connection.execute(
        f"""SELECT LastReportDate FROM LastReportForCustomer WHERE CustomerID = {customer_id}""").fetchone()


def get_report_for_customer_by_date(app, customer_id, creation_date):
    return app.db_connection.execute(
        f"""SELECT CustomerID customer_id, Date date, Type type, PaymentMean payment_mean, Description description,
        Currency currency, Amount amount, AmountInPln amount_in_pln FROM Report
        WHERE CustomerID = {customer_id} and CreationDate = '{creation_date}'
        ORDER BY Date ASC""").fetchall()
