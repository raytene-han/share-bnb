"""Listing model tests."""

# run these tests like:
#
#    python -m unittest test_listing_model.py


import os
from unittest import TestCase

from models import db, User, Listing

# BEFORE we import our app, let's set an environmental variable
# to use a different database for tests (we need to do this
# before we import our app, since that will have already
# connected to the database

os.environ['DATABASE_URL'] = "postgresql:///sharebnb_test"
os.environ['BUCKET_NAME'] = "UXEAHT"

# Now we can import app

from app import app

# Create our tables (we do this here, so we only create the tables
# once for all tests --- in each test, we'll delete the data
# and create fresh new clean test data

db.create_all()


class ListingModelTestCase(TestCase):
    def setUp(self):
        User.query.delete()
        # Listing.query.delete()

        u1 = User.signup("u1", "u1@email.com", "password", "userFirst1","userLast1" )
        u2 = User.signup("u2", "u2@email.com", "password", "userFirst2","userLast2" )
        

        db.session.commit()
        self.u1_id = u1.id
        self.u2_id = u2.id

        l1 = Listing(user_id=self.u1_id, price=100, details="cool test locale")
        l2 = Listing(user_id=self.u2_id, price=200, details="cool test2 locale")
        
        # db.session.add_all(l1,l2)
        db.session.add(l1)
        db.session.add(l2)
        db.session.commit()

        self.l1_id = l1.id
        self.l2_id = l2.id
        
        self.client = app.test_client()

    def tearDown(self):
        db.session.rollback()

    # #################### Listing tests

    def test_get_listings(self):
        listings = Listing.query.all()
        listing = Listing.query.get(self.l1_id)
        

        self.assertEqual(len(listings),2)
        self.assertEqual(listing.details, "cool test locale")
        self.assertEqual(listing.id, self.l1_id)
        self.assertEqual(listing.photos, None)
        self.assertEqual(listing.price, 100.00)
        self.assertEqual(listing.user_id, self.u1_id)
		    

    # def test_is_following(self):
    #     u1 = Listing.query.get(self.u1_id)
    #     u2 = Listing.query.get(self.u2_id)

    #     u1.following.append(u2)
    #     db.session.commit()

    #     self.assertTrue(u1.is_following(u2))
    #     self.assertFalse(u2.is_following(u1))

    # def test_is_followed_by(self):
    #     u1 = Listing.query.get(self.u1_id)
    #     u2 = Listing.query.get(self.u2_id)

    #     u1.following.append(u2)
    #     db.session.commit()

    #     self.assertTrue(u2.is_followed_by(u1))
    #     self.assertFalse(u1.is_followed_by(u2))

    # # #################### Signup Tests

    # def test_valid_signup(self):
    #     u1 = Listing.query.get(self.u1_id)

    #     self.assertEqual(u1.Listingname, "u1")
    #     self.assertEqual(u1.email, "u1@email.com")
    #     self.assertNotEqual(u1.password, "password")
    #     # Bcrypt strings should start with $2b$
    #     self.assertTrue(u1.password.startswith("$2b$"))

    # # #################### Authentication Tests

    # def test_valid_authentication(self):
    #     u1 = Listing.query.get(self.u1_id)

    #     u = Listing.authenticate("u1", "password")
    #     self.assertEqual(u, u1)

    # def test_invalid_Listingname(self):
    #     self.assertFalse(Listing.authenticate("bad-Listingname", "password"))

    # def test_wrong_password(self):
    #     self.assertFalse(Listing.authenticate("u1", "bad-password"))
