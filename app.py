from flask import Flask, render_template, request, redirect, flash, url_for, session
import json
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "your_secret_key"  # Ganti dengan kunci rahasia Anda

# Load email dan password dari config.json
with open("config.json", "r") as config_file:
    config = json.load(config_file)
    stored_email = config.get("email")
    stored_password_hash = config.get("password")


@app.route("/")
def home():
    if "logged_in" in session:
        return redirect(url_for("livecam"))
    return render_template("index.html")

@app.route("/login", methods=["POST"])
def login():
    email = request.form["email"]
    password = request.form["password"]

    # Validasi email dan password dengan hashing
    if email == stored_email and check_password_hash(stored_password_hash, password):
        session["logged_in"] = True
        session["user_email"] = email
        flash("Login successful!", "success")
        return redirect(url_for("livecam"))
    else:
        flash("Invalid email or password. Please try again.", "danger")
        return redirect(url_for("home"))

@app.route("/livecam")
def livecam():
    if "logged_in" not in session:
        flash("Please log in to access the Live Cam.", "warning")
        return redirect(url_for("home"))
    return render_template("livecam.html", user_email=session["user_email"])

@app.route("/logout")
def logout():
    session.pop("logged_in", None)
    session.pop("user_email", None)
    flash("You have been logged out.", "info")
    return redirect(url_for("home"))

@app.route("/data")
def data():
    if "logged_in" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("home"))
    return render_template("data.html")

@app.route("/setting")
def setting():
    if "logged_in" not in session:
        flash("Please log in to access this page.", "warning")
        return redirect(url_for("home"))
    return render_template("setting.html")

if __name__ == "__main__":
    app.run(debug=True)
