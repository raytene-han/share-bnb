# flask_jwt_extended.get_jwt_identity()

import os
from dotenv import load_dotenv

from flask import (
    Flask, request, jsonify
)
from flask_debugtoolbar import DebugToolbarExtension
from flask_cors import CORS
from sqlalchemy.exc import IntegrityError
from werkzeug.utils import secure_filename

from models import (
    db, connect_db, User, Message, Listing, Booking, BUCKET_NAME)

# import jwt

from flask_jwt_extended import create_access_token
from flask_jwt_extended import get_jwt_identity
from flask_jwt_extended import jwt_required
from flask_jwt_extended import JWTManager
from sqlalchemy import func, or_

load_dotenv()

CURR_USER_KEY = "curr_user"

app = Flask(__name__)
CORS(app)

# Get DB_URI from environ variable (useful for production/testing) or,
# if not set there, use development local db.
app.config['SQLALCHEMY_DATABASE_URI'] = (
    os.environ['DATABASE_URL'].replace("postgres://", "postgresql://"))
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_ECHO'] = False
app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = True
app.config['SECRET_KEY'] = os.environ['SECRET_KEY']
app.config['JWT_SECRET_KEY'] = os.environ['JWT_SECRET_KEY']
app.config['JWT_ACCESS_TOKEN_EXPIRES'] = False

toolbar = DebugToolbarExtension(app)

connect_db(app)
jwt = JWTManager(app)

SECRET_KEY = os.environ['SECRET_KEY']



##############################################################################
# User signup/login

@app.route('/api/signup', methods=["GET", "POST"])
def signup():
    """Handle user signup.

    Create new user and add to DB.
    """

    data = request.json

    user = User.signup(
        username=data.get("username"),
        password=data.get("password"),
        email=data.get("email"),
        firstName=data.get("firstName"),
        lastName=data.get("lastName"),
    )

    db.session.add(user)
    db.session.commit()

    access_token = create_access_token(identity=user.username)

    return jsonify(token=access_token), 201


@app.route('/api/login', methods=["POST"])
def login():
    """Handle user login and return token."""

    username = request.json.get("username", None)
    password = request.json.get("password", None)
    user = User.authenticate(username, password)

    if not user:
        return jsonify({"error": "invalid credentials"}),400

    access_token = create_access_token(identity=username)

    return jsonify(token=access_token)

@app.route('/api/users/<username>', methods=["GET"])
@jwt_required()
def get_user(username):
    """Return user object as json"""
    if username == get_jwt_identity():
        user = User.query.filter_by(username=username).one()
        serialized = User.serialize(user)
        return jsonify(user=serialized)


    return jsonify({"error": "invalid user"}),400


##############################################################################
# Listings routes:

@app.get('/api/listings')
def get_all_listings():
    """See all listings."""

    try:
        name = request.args["name"]
        listings = Listing.query.filter(Listing.name.ilike(f"%{name}%")).all()
    except:
        listings = Listing.query.all()

    serialized = [Listing.serialize(l) for l in listings]

    return jsonify(listings=serialized)


@app.post('/api/listings')
@jwt_required()
def create_listing():
    """Add a listing."""

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).one()

    name = request.form.get('name')
    price = request.form.get('price')
    details = request.form.get('details')

    listing = Listing(user_id=user.id,
                      name=name,
                      price=float(price),
                      details=details)
    db.session.add(listing)
    db.session.commit()

    if request.files.get('photo'):
        photo = request.files.get('photo')
        photo.filename = f"{listing.id}.jpg"

        photo.save(os.path.join("uploads", secure_filename(photo.filename)))
        url = Listing.upload_file(file_name=photo.filename)
        os.remove(os.path.join("uploads", secure_filename(photo.filename)))

        listing.photo = url

    db.session.commit()
    serialized = Listing.serialize(listing)

    return jsonify(listing=serialized), 201



@app.get('/api/listings/<int:listing_id>')
def get_listing(listing_id):
    """Get details about a listing."""

    listing = Listing.query.get_or_404(listing_id)
    serialized = Listing.serialize(listing)

    return jsonify(listing=serialized)


@app.post('/api/listings/<int:listing_id>/book')
@jwt_required()
def book_listing(listing_id):
    """Book a listing."""

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).one()

    checkin_date = request.json.get('checkin_date')
    checkout_date = request.json.get('checkout_date')

    booking = Booking(user_id=user.id,
                      listing_id=listing_id,
                      checkin_date=checkin_date,
                      checkout_date=checkout_date)

    db.session.add(booking)
    db.session.commit()

    serialized = Booking.serialize(booking)

    return jsonify(booking=serialized), 201

@app.post('/api/listings/<int:listing_id>/message')
@jwt_required()
def message_listing_owner(listing_id):
    """Message an owner about a listing."""

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).one()

    text = request.json.get('text')
    listing = Listing.query.get_or_404(listing_id)

    message = Message(to_user_id=listing.user_id,
                      from_user_id=user.id,
                      text=text)

    db.session.add(message)
    db.session.commit()

    serialized = Message.serialize(message)

    return jsonify(message=serialized), 201

##############################################################################
# Messages routes:

@app.get('/api/messages')
@jwt_required()
def get_messages():
    """Add a message:

    Show form if GET. If valid, update message and redirect to user page.
    """

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).one()
    # messages = (Message.query.filter(Message.to_user_id==user.id)
    #             .order_by(Message.from_user_id).all())
    # breakpoint()
    sent = [Message.serialize(m) for m in user.messages_sent]
    recd = [Message.serialize(m) for m in user.messages_received]

    conversations = Message.query.with_entities(
        Message.from_user_id, User.username)\
            .filter(Message.from_user_id != user.id)\
            .group_by(Message.from_user_id,User.username)\
            .join(User,User.id == Message.from_user_id)\
            .all()
    serialized = [{"id":c[0],"username":c[1]} for c in conversations]

    return jsonify(conversations=serialized)


@app.route('/api/messages/<int:user_id>', methods=["GET", "POST"])
@jwt_required()
def open_conversation(user_id):
    """Gets messages with one person.

    Return messages if GET, add new message if POST.
    """

    username = get_jwt_identity()
    user = User.query.filter_by(username=username).one()

    if request.method == "GET":
        messages = Message.query.filter(((Message.to_user_id==user_id) &
                                        (Message.from_user_id==user.id)) |
                                        ((Message.to_user_id==user.id) &
                                        (Message.from_user_id==user_id)))\
                                        .order_by(Message.id)\
                                        .all()
       
        serialized = [Message.serialize(m) for m in messages]
        
        return jsonify(messages=serialized)

    else:
        message = Message(
            to_user_id=user_id,
            from_user_id=user.id,
            text=request.json.get("text")
            )
        db.session.add(message)
        db.session.commit()

        serialized = Message.serialize(message)

        return jsonify(message=serialized), 201


##############################################################################
# Homepage and error pages



@app.errorhandler(404)
def page_not_found(e):
    """404 NOT FOUND page."""

    return jsonify({"error": "Page not found."}), 404


@app.after_request
def add_header(response):
    """Add non-caching headers on every request."""

    # https://developer.mozilla.org/en-US/docs/Web/HTTP/Headers/Cache-Control
    response.cache_control.no_store = True
    return response
