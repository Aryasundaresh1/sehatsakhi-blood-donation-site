from flask import Flask, render_template, request, redirect
import pymysql
from datetime import datetime

app = Flask(__name__)

# Database connection
db = pymysql.connect(
    host="localhost",
    user="root",
    password="root@123",
    database="blood_donation"
)
cursor = db.cursor()

# Home Page
@app.route('/')
def index():
    return render_template("index.html")

# Add Donor
@app.route('/add_donor', methods=['GET', 'POST'])
def add_donor():
    if request.method == 'POST':
        data = request.form
        query = """
            INSERT INTO blood_donor (name, age, gender, blood_group, contact, address, last_donation_date)
            VALUES (%s, %s, %s, %s, %s, %s, %s)
        """
        values = (
            data['name'], data['age'], data['gender'], data['blood_group'],
            data['contact'], data['address'], data['last_donation_date']
        )
        cursor.execute(query, values)
        db.commit()
        return redirect('/')
    return render_template("add_donor.html")

# View Donors
@app.route('/view_donors')
def view_donors():
    cursor.execute("SELECT * FROM blood_donor")
    donors = cursor.fetchall()
    return render_template("view_donors.html", donors=donors)

# Donate Blood
@app.route('/donate_blood', methods=['GET', 'POST'])
def donate_blood():
    if request.method == 'POST':
        donor_id = request.form['donor_id']
        blood_group = request.form['blood_group']
        quantity = int(request.form['quantity'])

        # Fetch donor's actual blood group from DB
        cursor.execute("SELECT blood_group FROM blood_donor WHERE donor_id = %s", (donor_id,))
        result = cursor.fetchone()

        if not result:
            return "Invalid donor ID", 400

        donor_blood_group = result[0]

        # Check if donor blood group matches the blood group in form
        if donor_blood_group != blood_group:
            return f"Error: Donor's blood group is {donor_blood_group}. Cannot donate {blood_group}.", 400

        # If all okay, proceed with insertions and updates
        cursor.execute("""
            INSERT INTO donation_record (donor_id, donation_date, blood_group, quantity_donated)
            VALUES (%s, NOW(), %s, %s)
        """, (donor_id, blood_group, quantity))

        cursor.execute("""
            INSERT INTO blood_stock (blood_group, quantity_in_units)
            VALUES (%s, %s)
            ON DUPLICATE KEY UPDATE quantity_in_units = quantity_in_units + %s
        """, (blood_group, quantity, quantity))

        cursor.execute("""
            UPDATE blood_donor SET last_donation_date = %s WHERE donor_id = %s
        """, (datetime.now().date(), donor_id))

        db.commit()
        return redirect('/donation_log')

    # GET request
    cursor.execute("SELECT donor_id, name, blood_group FROM blood_donor")
    donors = cursor.fetchall()
    return render_template("donate_blood.html", donors=donors)


# View Stock
@app.route('/view_stock')
def view_stock():
    cursor.execute("SELECT * FROM blood_stock")
    stock = cursor.fetchall()
    return render_template("view_stock.html", stock=stock)

# Request Blood
@app.route('/request_blood', methods=['GET', 'POST'])
def request_blood():
    if request.method == 'POST':
        data = request.form
        quantity = int(data['quantity_required'])
        blood_group = data['blood_group_required']

        # Check availability
        cursor.execute("SELECT quantity_in_units FROM blood_stock WHERE blood_group = %s", (blood_group,))
        result = cursor.fetchone()

        status = 'Rejected'
        if result and result[0] >= quantity:
            status = 'Fulfilled'
            cursor.execute("""
                UPDATE blood_stock SET quantity_in_units = quantity_in_units - %s
                WHERE blood_group = %s
            """, (quantity, blood_group))

        cursor.execute("""
            INSERT INTO blood_request (requester_name, requester_contact, blood_group_required, quantity_required, status)
            VALUES (%s, %s, %s, %s, %s)
        """, (
            data['requester_name'], data['requester_contact'],
            blood_group, quantity, status
        ))

        db.commit()
        return redirect('/view_requests')

    return render_template("request_blood.html")

# View Blood Requests
@app.route('/view_requests')
def view_requests():
    cursor.execute("SELECT * FROM blood_request")
    requests = cursor.fetchall()
    return render_template("view_requests.html", requests=requests)

# View Donation Log
@app.route('/donation_log')
def donation_log():
    cursor.execute("""
        SELECT dr.donation_id, bd.name, dr.blood_group, dr.quantity_donated, dr.donation_date
        FROM donation_record dr
        JOIN blood_donor bd ON dr.donor_id = bd.donor_id
        ORDER BY dr.donation_date DESC
    """)
    records = cursor.fetchall()
    return render_template("donation_log.html", records=records)

if __name__ == '__main__':
    app.run(debug=True)
