from flask import Flask, render_template, request, redirect, url_for, jsonify
import sqlite3
import secrets
from werkzeug.security import generate_password_hash, check_password_hash

# Gemini imports
from google import genai
from dotenv import load_dotenv
import os


# ---------------------------------
# LOAD ENVIRONMENT VARIABLES
# ---------------------------------

load_dotenv()


# ---------------------------------
# FLASK APP
# ---------------------------------

app = Flask(__name__)

DATABASE = "users.db"


# ---------------------------------
# GEMINI SETUP
# ---------------------------------

client = genai.Client(
    api_key=os.getenv("GEMINI_API_KEY")
)


# ---------------------------------
# DATABASE SETUP
# ---------------------------------

# def init_db():
#     conn = sqlite3.connect(DATABASE)
#     cursor = conn.cursor()

#     cursor.execute("""
#         CREATE TABLE IF NOT EXISTS users (
#             id INTEGER PRIMARY KEY AUTOINCREMENT,
#             fullname TEXT NOT NULL,
#             username TEXT UNIQUE NOT NULL,
#             email TEXT UNIQUE NOT NULL,
#             password TEXT NOT NULL
#         )
#     """)

#     conn.commit()
#     conn.close()
# ---------------------------------
# DATABASE SETUP
# ---------------------------------

def init_db():

    # Connect to the SQLite database
    # If users.db doesn't exist, SQLite will create it
    conn = sqlite3.connect(DATABASE)

    # Create a cursor so we can execute SQL commands
    cursor = conn.cursor()


    # ---------------------------------
    # USERS TABLE
    # ---------------------------------

    # This is your existing users table.
    # It stores information about registered users.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            fullname TEXT NOT NULL,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL
        )
    """)


    # ---------------------------------
    # PASSWORD RESET TABLE
    # ---------------------------------

    # This table will be used when a user
    # forgets their password.
    #
    # We don't store the password here.
    # We store a temporary reset token.
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS password_resets (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            token TEXT UNIQUE NOT NULL,
            expires_at TEXT NOT NULL,
            FOREIGN KEY (user_id) REFERENCES users(id)
        )
    """)


    # Save all database changes
    conn.commit()

    # Close the database connection
    conn.close()

# ---------------------------------
# WELCOME / HOME PAGE
# ---------------------------------

@app.route("/")
def home():
    return render_template("index.html")


# ---------------------------------
# SIGN UP
# ---------------------------------

@app.route("/signup", methods=["GET", "POST"])
def signup():

    if request.method == "POST":

        fullname = request.form["fullname"].strip()
        username = request.form["username"].strip()
        email = request.form["email"].strip()
        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check password confirmation
        if password != confirm_password:
            return "Passwords do not match."

        # Hash the password before saving it
        hashed_password = generate_password_hash(password)

        try:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()

            cursor.execute("""
                INSERT INTO users
                (fullname, username, email, password)
                VALUES (?, ?, ?, ?)
            """, (
                fullname,
                username,
                email,
                hashed_password
            ))

            conn.commit()
            conn.close()

            # Successful signup -> go to Sign In
            return redirect(url_for("signin"))

        except sqlite3.IntegrityError:
            return "Username or email already exists."

    return render_template("signup.html")


# ---------------------------------
# SIGN IN
# ---------------------------------

@app.route("/signin", methods=["GET", "POST"])
def signin():

    if request.method == "POST":

        username_or_email = request.form["username_or_email"].strip()
        password = request.form["password"]

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, fullname, username, email, password
            FROM users
            WHERE username = ? OR email = ?
        """, (
            username_or_email,
            username_or_email
        ))

        user = cursor.fetchone()

        conn.close()

        # User does not exist
        if user is None:
            return "User not found."

        # Password stored in the database
        stored_password = user[4]

        # Check entered password against hashed password
        if check_password_hash(stored_password, password):

            # Successful signin -> go to index.html
            return redirect(url_for("home"))

        return "Incorrect password."

    return render_template("signin.html")

# # ---------------------------------
# CHAT WITH GEMINI
# ---------------------------------

@app.route("/chat", methods=["POST"])
def chat():

    data = request.get_json()

    user_message = data.get("message", "").strip()

    # Don't send an empty message to Gemini
    if not user_message:
        return jsonify({
            "error": "Message cannot be empty."
        }), 400

    try:

        response = client.models.generate_content(
            model="gemini-3.6-flash",
            contents=user_message
        )

        return jsonify({
            "response": response.text
        })

    except Exception as e:

        print("Gemini API Error:", e)

        return jsonify({
            "error": "Something went wrong while contacting Gemini."
        }), 500

# ---------------------------------
# FORGOT PASSWORD
# ---------------------------------

@app.route("/forgot-password", methods=["GET", "POST"])
def forgot_password():

    # Check if the user submitted the form
    if request.method == "POST":

        # Get the email entered by the user
        email = request.form["email"].strip()

        # Connect to the database
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()

        # Search for the user using their email
        cursor.execute("""
            SELECT id, email
            FROM users
            WHERE email = ?
        """, (email,))

        # Get the user information
        user = cursor.fetchone()

        # If no account exists with this email
        if user is None:
            conn.close()
            return "No account found with this email."

        # Get the user's ID
        user_id = user[0]

        # Create a secure random reset token
        token = secrets.token_urlsafe(32)

        # Store the token in the password_resets table
        # The token will expire after 15 minutes
        cursor.execute("""
            INSERT INTO password_resets
            (user_id, token, expires_at)
            VALUES (?, ?, datetime('now', '+15 minutes'))
        """, (
            user_id,
            token
        ))

        # Save the changes to the database
        conn.commit()

        # Close the database connection
        conn.close()

        # Create the reset link
        reset_link = url_for(
            "reset_password",
            token=token
        )

        # Redirect the user to the reset-password page
        return redirect(reset_link)

    # Display the forgot-password page
    return render_template("forgot_password.html")
# ---------------------------------
# RESET PASSWORD
# ---------------------------------

@app.route("/reset-password/<token>", methods=["GET", "POST"])
def reset_password(token):

    # Connect to the database
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()

    # Check if the token exists and is still valid
    cursor.execute("""
        SELECT user_id
        FROM password_resets
        WHERE token = ?
        AND expires_at > datetime('now')
    """, (token,))

    reset = cursor.fetchone()

    # Token is invalid or expired
    if reset is None:
        conn.close()
        return "Invalid or expired reset token."

    # Get the user ID connected to this token
    user_id = reset[0]

    # If the user submitted the new password
    if request.method == "POST":

        password = request.form["password"]
        confirm_password = request.form["confirm_password"]

        # Check if both passwords match
        if password != confirm_password:
            conn.close()
            return "Passwords do not match."

        # Hash the new password
        hashed_password = generate_password_hash(password)

        # Update the user's password
        cursor.execute("""
            UPDATE users
            SET password = ?
            WHERE id = ?
        """, (
            hashed_password,
            user_id
        ))

        # Delete the used token
        cursor.execute("""
            DELETE FROM password_resets
            WHERE token = ?
        """, (token,))

        # Save changes
        conn.commit()
        conn.close()

        # Go back to Sign In
        return redirect(url_for("signin"))

    # Show the reset-password page
    conn.close()

    return render_template(
        "reset_password.html",
        token=token
    )
# ---------------------------------
# START APPLICATION
# ---------------------------------

if __name__ == "__main__":
    init_db()
    app.run(debug=True)