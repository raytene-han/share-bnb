# flask_jwt_extended.get_jwt_identity()

import os
from dotenv import load_dotenv

from flask import (
    Flask, render_template, request, flash, redirect, session, g, abort, jsonify
)
from flask_debugtoolbar import DebugToolbarExtension
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from models import (
    db, connect_db, User, Message, Listing, Booking, DEFAULT_IMAGE_URL,
    DEFAULT_HEADER_IMAGE_URL, BUCKET_NAME)

import jwt



load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ['DATABASE_URL'].replace("postgres://", "postgresql://"))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET_KEY']

toolbar = DebugToolbarExtension(app)

connect_db(app)
# jwt = JWTManager(app)

SECRET_KEY = os.environ['SECRET_KEY']



##############################################################################
# User signup/login/logout


@app.before_request
def add_user_to_g():
    """If we're logged in, add curr user to Flask global."""

    if CURR_USER_KEY in session:
        g.user = User.query.get(session[CURR_USER_KEY])

    else:
        g.user = None



def do_login(user):
    """Log in user."""

    session[CURR_USER_KEY] = user.id


def do_logout():
    """Log out user."""

    if CURR_USER_KEY in session:
        del session[CURR_USER_KEY]


@app.route('/api/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB. Redirect to home page.

    If form not valid, present form.

    If the there already is a user with that username: flash message
    and re-present form.
    """
    data = request.json


    user = User.signup(
        username=data.get("username"),
        password=data.get("password"),
        email=data.get("email"),
        firstName=data.get("first_name"),
        lastName=data.get("last_name"),
    )
    db.session.commit()
    do_login(user)

    serialized = User.serialize(user)
    access_token = jwt.encode({"username":user.username},SECRET_KEY)

    return jsonify({"access_token":access_token}),201


@app.route('/api/login', methods=["POST"])
def login():
    """Handle user login and return token"""

    data = request.json
    user = User.authenticate(data.get("username"), data.get("password"))
    if not user:
        return jsonify({"error": "invalid credentials"}),401

    serialized = User.serialize(user)
    access_token = jwt.encode({"username":user.username},SECRET_KEY)

    return jsonify(access_token=access_token)


##############################################################################
# Listings routes:

@app.route('/api/listings', methods=["GET", "POST"])
def add_message():
    """Add a listing:

    1. check logged in to get user_id
    2. validate data (price, details?, photo?)
    3. if valid, then add to database
        if photo, call Listing.upload
        update listing with photo url
    """
    price = request.form.get('price')
    details = request.form.get('details')

    listing = Listing(user_id=8, price=float(price), details=details)
    db.session.add(listing)
    db.session.commit()

    photo = request.files['photo']
    photo.filename = f"{listing.id}.jpg"

    photo.save(os.path.join("uploads", secure_filename(photo.filename)))
    url = Listing.upload_file(file_name=photo.filename)
    os.remove(os.path.join("uploads", secure_filename(photo.filename)))

    listing.photos = url
    db.session.commit()
    serialized = Listing.serialize(listing)

    return jsonify(listing=serialized)


@app.get('/api/listings/<int:listing_id>')
def get_listing(listing_id):
    """Get details about a listing."""

    listing = Listing.query.get_or_404(listing_id)
    serialized = Listing.serialize(listing)

    return jsonify(listing=serialized)


@app.post('/api/listings/<int:listing_id>/book')
def book_listing(listing_id):
    """Book a listing."""


    checkin_date = request.json.get('checkin_date')
    checkout_date = request.json.get('checkout_date')

    booking = Booking(user_id=10,
                      listing_id=listing_id,
                      checkin_date=checkin_date,
                      checkout_date=checkout_date)

    db.session.add(booking)
    db.session.commit()

    serialized = Booking.serialize(booking)

    return jsonify(booking=serialized)

@app.post('/api/listings/<int:listing_id>/message')
def message_listing_owner(listing_id):
    """Message an owner about a listing."""

    text = request.json.get('text')
    listing = Listing.query.get_or_404(listing_id)

    message = Message(to_user_id=listing.user_id,
                      from_user_id=10,
                      text=text)

    db.session.add(message)
    db.session.commit()

    serialized = Message.serialize(message)

    return jsonify(message=serialized)

##############################################################################
# Messages routes:

@app.route('/messages', methods=["GET", "POST"])
def get_messages():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    # if not g.user:
    #     flash("Access unauthorized.", "danger")
    #     return redirect("/")

    # form = MessageForm()
    user = User.query.get_or_404(10)
    breakpoint()
    return jsonify({"sent": user.messages_sent, "received": user.messages_received})


##############################################################################
# Homepage and error pages



@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""

    return render_template('404.html'), 404


@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
