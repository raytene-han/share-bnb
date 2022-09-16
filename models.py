"""SQLAlchemy models for Warbler."""

from datetime import datetime

from flask_bcrypt import Bcrypt
from flask_sqlalchemy import SQLAlchemy

import logging
import boto3
from botocore.exceptions import ClientError
import os
from dotenv import load_dotenv

load_dotenv()

bcrypt = Bcrypt()
db = SQLAlchemy()

DEFAULT_IMAGE_URL = "https://share-bnb-rh.s3.amazonaws.com/DEFAULT_YARD.jpeg"
BUCKET_NAME = os.environ['BUCKET_NAME']

class Booking(db.Model):
    """Connection of a user & listing -> booking."""

    __tablename__ = 'bookings'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        nullable=False
    )

    listing_id = db.Column(
        db.Integer,
        db.ForeignKey('listings.id', ondelete="cascade"),
        nullable=False
    )

    checkin_date = db.Column(
        db.DateTime,
        nullable=False
    )

    checkout_date = db.Column(
        db.DateTime,
        nullable=False
    )

    booking_date = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow
    )

    def serialize(self):
        """Serialize booking to a dict of booking info."""

        return {
            "id": self.id,
            "userId": self.user_id,
            "listingId": self.listing_id,
            "checkinDate": self.checkin_date,
            "checkoutDate": self.checkout_date,
            "bookingDate": self.booking_date,
        }


class Listing(db.Model):
    """Connection of a user -> listing."""

    __tablename__ = 'listings'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete="cascade"),
        nullable=False
    )

    name = db.Column(
        db.Text,
        nullable=False
    )

    photo = db.Column(
        db.Text,
        default=DEFAULT_IMAGE_URL
    )

    price = db.Column(
        db.Numeric(10,2),
        nullable=False
    )

    details = db.Column(
        db.Text
    )

    @classmethod
    def upload_file(cls, file_name, object_name=None):
        """Upload a file to an S3 bucket

        :param file_name: File to upload
        :param bucket: Bucket to upload to
        :param object_name: S3 object name. If not specified then file_name is used
        :return: True if file was uploaded, else False
        """
        mimetype = 'image/jpeg'
        # If S3 object_name was not specified, use file_name
        if object_name is None:
            object_name = os.path.basename(file_name)

        # Upload the file
        s3_client = boto3.client('s3')
        try:
            response = s3_client.upload_file(f"uploads/{file_name}",
                                            BUCKET_NAME,
                                            object_name,
                                            ExtraArgs={
                                                "ContentType": mimetype
                                                    })
        except ClientError as e:
            logging.error(e)
            return False
        return f"https://{BUCKET_NAME}.s3.amazonaws.com/{file_name}"

    def serialize(self):
        """Serialize listing to a dict of listing info."""

        return {
            "id": self.id,
            "userId": self.user_id,
            "name": self.name,
            "photo": self.photo,
            "price": self.price,
            "details": self.details,
        }

class Message(db.Model):
    """A message to another user."""

    __tablename__ = 'messages'

    id = db.Column(
        db.Integer,
        primary_key=True,
    )

    to_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    from_user_id = db.Column(
        db.Integer,
        db.ForeignKey('users.id', ondelete='CASCADE'),
        nullable=False,
    )

    text = db.Column(
        db.String(140),
        nullable=False,
    )

    timestamp = db.Column(
        db.DateTime,
        nullable=False,
        default=datetime.utcnow,
    )

    def serialize(self):
        """Serialize message to a dict of message info."""

        return {
            "id": self.id,
            "toUserId": self.to_user_id,
            "fromUserId": self.from_user_id,
            "text": self.text,
            "timestamp": self.timestamp,
        }


class User(db.Model):
    """User in the system."""

    __tablename__ = 'users'

    id = db.Column(
        db.Integer,
        primary_key=True,
        autoincrement=True
    )

    email = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    username = db.Column(
        db.Text,
        nullable=False,
        unique=True,
    )

    password = db.Column(
        db.Text,
        nullable=False,
    )

    first_name = db.Column(
        db.Text,
        nullable=False,
    )

    last_name = db.Column(
        db.Text,
        nullable=False,
    )

    listings = db.relationship('Listing', backref="user")

    bookings = db.relationship('Booking', backref="user")

    messages_received = db.relationship(
        "Message",
        foreign_keys=[Message.to_user_id]
    )

    messages_sent = db.relationship(
        "Message",
        foreign_keys=[Message.from_user_id]
    )

    def __repr__(self):
        return f"<User #{self.id}: {self.username}, {self.email}>"

    @classmethod
    def signup(cls, username, email, password, firstName, lastName):
        """Sign up user.

        Hashes password and adds user to system.
        """

        hashed_pwd = bcrypt.generate_password_hash(password).decode('UTF-8')

        user = User(
            username=username,
            email=email,
            password=hashed_pwd,
            first_name=firstName,
            last_name=lastName
        )

        db.session.add(user)
        return user

    @classmethod
    def authenticate(cls, username, password):
        """Find user with `username` and `password`.

        This is a class method (call it on the class, not an individual user.)
        It searches for a user whose password hash matches this password
        and, if it finds such a user, returns that user object.

        If this can't find matching user (or if password is wrong), returns
        False.
        """

        user = cls.query.filter_by(username=username).first()

        if user:
            is_auth = bcrypt.check_password_hash(user.password, password)
            if is_auth:
                return user

        return False

    def serialize(self):
        """Serialize user to a dict of user info."""

        return {
            "id": self.id,
            "username": self.username,
            "email": self.email,
            "firstName": self.first_name,
            "lastName": self.last_name
        }




def connect_db(app):
    """Connect this database to provided Flask app.

    You should call this in your Flask app.
    """

    db.app = app
    db.init_app(app)

