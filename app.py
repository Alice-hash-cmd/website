from flask import Flask, Blueprint, jsonify, request, render_template, request, redirect, url_for, session, flash, send_from_directory
from flask_sqlalchemy import SQLAlchemy
# from werkzeug.security import generate_password_hash, check_password_hash
# from werkzeug.security import generate_password_hash, check_password_hash
import os
from flask_migrate import Migrate
import jwt
from flask_cors import CORS
from datetime import datetime, timedelta
SECRET_KEY = "hotel"  ## don't remove it this is the secrete key
app = Flask(__name__)
app.secret_key = os.urandom(24)

# app.config['Sapp.config['UPLOAD_FOLDER'] = 'uploads/'QLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
# app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost/hotel_website'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://root:123456@localhost:3306/hotel_website'

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
routes = Blueprint("app", __name__)

db = SQLAlchemy(app)
migrate = Migrate(app, db)

# if not os.path.exists(app.config['UPLOAD_FOLDER']):
#     os.makedirs(app.config['UPLOAD_FOLDER'])


# Models
class User(db.Model):
    __tablename__ = "users"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(512), nullable=False)
    role = db.Column(db.String(20), default="user", nullable=False)  # 'user' or 'admin'

    bookings = db.relationship(
        "Booking", cascade="all, delete-orphan", backref="user", lazy="dynamic"
    )

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    def __repr__(self):
        return f"<User {self.username}>"


# Hotel model
class Hotel(db.Model):
    __tablename__ = "hotels"
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    city = db.Column(db.String(50), nullable=False)
    capacity = db.Column(db.Integer, nullable=False)
    peak_season_rate = db.Column(db.Float, nullable=False)
    off_peak_rate = db.Column(db.Float, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # Cascade delete for associated rooms
    rooms = db.relationship(
        "Room", cascade="all, delete-orphan", backref="hotel", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Hotel {self.name} in {self.city}>"

# Room model
class Room(db.Model):
    __tablename__ = "rooms"
    id = db.Column(db.Integer, primary_key=True)
    hotel_id = db.Column(db.Integer, db.ForeignKey("hotels.id"), nullable=False)
    room_type = db.Column(db.String(20), nullable=False)  # Standard, Double, Family
    price = db.Column(db.Float, nullable=False)
    is_available = db.Column(db.Boolean, default=True)

    # Cascade delete for associated bookings
    bookings = db.relationship(
        "Booking", cascade="all, delete-orphan", backref="room", lazy="dynamic"
    )

    def __repr__(self):
        return f"<Room {self.room_type} in Hotel {self.hotel_id}>"



class Booking(db.Model):
    __tablename__ = "bookings"
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)
    room_id = db.Column(db.Integer, db.ForeignKey("rooms.id"), nullable=False)
    booking_date = db.Column(db.DateTime, default=datetime.utcnow)
    staying_date = db.Column(db.DateTime, nullable=False)  # Check-in date
    checkout_date = db.Column(db.DateTime, nullable=False)  # New field for checkout date
    status = db.Column(
        db.String(20), default="pending"
    )  # Status could be 'pending', 'confirmed', or 'canceled'
    discount = db.Column(db.Float, default=0.0)  # Discount applied on booking
    final_price = db.Column(db.Float, nullable=False)  # Final price after discount

    def calculate_discount(self, base_price):
        """
        Calculate discount based on the number of days in advance the booking is made.
        """
        if not self.staying_date or not self.booking_date:
            raise ValueError("Staying date or booking date is not set")

        days_in_advance = (self.staying_date - self.booking_date).days
        print(days_in_advance)

        if 80 <= days_in_advance <= 90:
            return base_price * 0.30  # 30% discount
        elif 60 <= days_in_advance <= 79:
            return base_price * 0.20  # 20% discount
        elif 45 <= days_in_advance <= 59:
            return base_price * 0.10  # 10% discount
        else:
            return 0.0  # No discount

    def calculate_final_price(self):
        """
        Calculate the final price after applying the discount.
        """

        try:
            room = Room.query.get(self.room_id)
            if room:
                base_price = room.price
                num_days = (self.checkout_date - self.staying_date).days
                total_base_price = base_price * num_days
                self.discount = self.calculate_discount(total_base_price)
                self.final_price = total_base_price - self.discount
            else:
                self.discount = 0.0
                self.final_price = 0.0
        except Exception as e:
            # Log the exception (optional, useful for debugging)
            print(f"Error occurred: {e}")
            # Set discount and final_price to 0.0 in case of an error
            self.discount = 0.0
            self.final_price = 0.0

    def __repr__(self):
        return (
            f"<Booking {self.id} for Room {self.room_id} by User {self.user_id}, "
            f"Check-in: {self.staying_date}, Check-out: {self.checkout_date}>"
        )

class ContactUs(db.Model):
    __tablename__ = "contact_us"

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), nullable=False)
    message = db.Column(db.Text, nullable=False)
    submitted_at = db.Column(db.DateTime, default=datetime.utcnow)
    username = db.Column(db.String(100), nullable=False)

    def __repr__(self):
        return f"<ContactUs id={self.id}, name={self.name}, email={self.email}, message={self.message[:30]}>"

    def save(self):
        """
        Save the contact form submission to the database.
        This simulates some business logic to process the contact us data.
        """
        db.session.add(self)
        db.session.commit()
        db.session.refresh(self)

# Routes
def generate_token(user):
    payload = {
        "id": user.id,
        "username": user.username,
        "role": user.role,
        "exp": datetime.utcnow() + timedelta(hours=1),
    }
    return jwt.encode(payload, SECRET_KEY, algorithm="HS256")

def generate_password_hash(password):
    return password

def check_password_hash(old, new):
    return old == new

# Initialize the database
@routes.route("/api/init-db", methods=["GET"])
def initialize_database():
    try:
        db.create_all()
        return jsonify({"message": "Database initialized successfully!"}), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@routes.route("/api/contactUs", methods=["POST"])
def add_contactUs():
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    try:
        # Get data from request body
        data = request.get_json()

        # Validate required fields
        name = data.get("name")
        email = data.get("email")
        message = data.get("message")

        if not name or not email or not message:
            return jsonify({"message": "Missing required fields: name, email, message"}), 400

        # Create a new ContactUs record
        contact = ContactUs(
            name=name,
            email=email,
            message=message,
            username=user.username
        )

        # Add the record to the database
        db.session.add(contact)
        db.session.commit()

        # Return success response
        return jsonify({"message": "Thank you for contacting us! We will get back to you soon."}), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"message": "Unexpected error occurred", "error": str(e)}), 500

@routes.route("/api/contactUs", methods=["GET"])
def get_all_contact_us():
    try:
        # Query all ContactUs entries
        contact_us_entries = ContactUs.query.all()

        # Convert the result to a list of dictionaries
        contact_list = [
            {
                "id": contact.id,
                "name": contact.name,
                "email": contact.email,
                "message": contact.message,
                "submitted_at": contact.submitted_at,
                "username": contact.username
            }
            for contact in contact_us_entries
        ]

        # Return the list of contact entries
        return jsonify(contact_list), 200

    except Exception as e:
        # Handle unexpected errors
        return jsonify({"message": "Unexpected error occurred", "error": str(e)}), 500


# User Signup
@routes.route("/api/signup", methods=["POST"])
def signup():
    data = request.json
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    role = data.get("role", "user")

    if (
        User.query.filter_by(username=username).first()
        or User.query.filter_by(email=email).first()
    ):
        return jsonify({"message": "User already exists!"}), 400

    if role not in ["user", "admin"]:
        return jsonify({"message": "Invalid role!"}), 400

    user = User(username=username, email=email, role=role)
    user.set_password(password)

    db.session.add(user)
    db.session.commit()
    return (
        jsonify({"message": f"User '{username}' created successfully as '{role}'!"}),
        200,
    )


# User Login
@routes.route("/api/login", methods=["POST"])
def login():
    data = request.json
    username = data.get("username")
    password = data.get("password")

    user = User.query.filter_by(username=username).first()
    if not user or not user.check_password(password):
        return jsonify({"message": "Invalid credentials"}), 401

    token = generate_token(user)
    return jsonify({"token": token, "role": user.role}), 200


# Get User Info
@routes.route("/api/user", methods=["GET"])
def get_user():
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])
        return (
            jsonify({"id": user.id, "username": user.username, "role": user.role}),
            200,
        )
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401


@routes.route("/api/allusers", methods=["GET"])
def get_all_users():
    token = request.headers.get("Authorization")

    # Check if token is provided
    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token

    try:
        # Decode the token
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])

        # Ensure the user has admin privileges
        if user.role != "admin":
            return jsonify({"message": "Access denied"}), 403

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    try:
        # Fetch all users from the database
        users = User.query.all()

        # Serialize the user data
        users_data = [
            {
                "id": user.id,
                "username": user.username,
                "email": user.email,
                "role": user.role,
            }
            for user in users
        ]

        return (
            jsonify({"users": users_data, "message": "Users retrieved successfully"}),
            200,
        )

    except Exception as e:
        return jsonify({"message": "Failed to retrieve users", "error": str(e)}), 500


@routes.route("/api/user/<int:user_id>", methods=["PUT"])
def update_password(user_id):
    token = request.headers.get("Authorization")

    # Check if token is provided
    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token

    try:
        # Decode the token
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])

        # Ensure the user has admin privileges
        if user.role != "admin":
            return jsonify({"message": "Access denied"}), 403

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    # Find the user whose password needs to be updated
    user = User.query.get(user_id)

    if not user:
        return jsonify({"message": "User not found."}), 404

    try:
        data = request.json

        user.set_password(data.get("new_password"))

        # Commit the changes to the database
        db.session.commit()
        return (
            jsonify(
                {"message": f"Password updated successfully for user {user.email}."}
            ),
            200,
        )
    except Exception as e:
        db.session.rollback()
        print(e)
        return jsonify({"message": "Failed to update password.", "error": str(e)}), 500


@routes.route("/api/hotels/search", methods=["GET"])
def search_hotels():
    # Optionally handle token validation here if needed
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])

        # Get the city (location) parameter from the query string
        city = request.args.get("city", "").strip()  # Get city from query params

        # Optionally get a search term (like hotel name or any other field)
        search_term = request.args.get("search", "").strip()

        # Query hotels based on city and/or search term
        query = Hotel.query

        if city:
            query = query.filter(
                Hotel.city.ilike(f"%{city}%")
            )  # Case-insensitive match for city

        if search_term:
            query = query.filter(
                Hotel.name.ilike(f"%{search_term}%")
            )  # Case-insensitive match for name

        # Fetch filtered hotels
        hotels = query.all()

        # Serialize the hotel data to return it
        hotels_data = []
        for hotel in hotels:
            hotels_data.append(
                {
                    "id": hotel.id,
                    "name": hotel.name,
                    "city": hotel.city,
                    "capacity": hotel.capacity,
                    "peak_season_rate": hotel.peak_season_rate,
                    "off_peak_rate": hotel.off_peak_rate,
                }
            )

        return jsonify(hotels_data), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401


@routes.route("/api/hotels", methods=["GET"])
def get_hotels():
    # Optionally handle token validation here if needed
    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])

        # Fetch all hotels from the database
        hotels = Hotel.query.all()

        # Serialize the hotel data to return it
        hotels_data = []
        for hotel in hotels:
            hotels_data.append(
                {
                    "id": hotel.id,
                    "name": hotel.name,
                    "city": hotel.city,
                    "capacity": hotel.capacity,
                    "peak_season_rate": hotel.peak_season_rate,
                    "off_peak_rate": hotel.off_peak_rate,
                }
            )

        return jsonify(hotels_data), 200

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401


@routes.route("/api/hotels/<int:hotel_id>/bookings", methods=["GET"])
def get_bookings_by_hotel(hotel_id):
    try:
        # Fetch all bookings for the given hotel ID by joining with Room and User models
        bookings = (
            db.session.query(Booking)
            .join(Room)
            .join(User)  # Join with User model to get the username
            .filter(Room.hotel_id == hotel_id)
            .all()
        )

        # Serialize the booking data
        bookings_data = [
            {
                "id": booking.id,
                "room_id": booking.room_id,
                "user_id": booking.user_id,
                "username": booking.user.username,  # Fetch the username from User model
                "booking_date": booking.booking_date,
                "staying_date": booking.staying_date,
                "checkout_date": booking.checkout_date,
                "status": booking.status,
                "room_type": booking.room.room_type,  # Assuming room_type is in Room model
            }
            for booking in bookings
        ]

        return jsonify(bookings_data), 200

    except Exception as e:
        return jsonify({"message": "Error fetching bookings", "error": str(e)}), 500


@routes.route("/api/hotel", methods=["POST"])
def add_hotel():

    token = request.headers.get("Authorization")

    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token

    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])

        # Check if the user has a valid role or permissions if necessary
        if user.role != "admin":  # Or any other condition you need
            return jsonify({"message": "Access denied"}), 403

    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    # Get the hotel data from the request body
    data = request.get_json()

    # Validate the incoming data
    if (
        not data.get("name")
        or not data.get("city")
        or not data.get("capacity")
        or not data.get("peak_season_rate")
        or not data.get("off_peak_rate")
    ):
        return (
            jsonify({"message": "Missing required fields: name, city, capacity"}),
            400,
        )

    try:
        # Create a new hotel
        new_hotel = Hotel(
            name=data["name"],
            city=data["city"],
            capacity=data["capacity"],
            peak_season_rate=data["peak_season_rate"],
            off_peak_rate=data["off_peak_rate"],
        )

        # Add the hotel to the database
        db.session.add(new_hotel)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Hotel added successfully",
                    "hotel": {
                        "name": new_hotel.name,
                        "city": new_hotel.city,
                        "capacity": new_hotel.capacity,
                    },
                }
            ),
            201,
        )

    except Exception as e:
        db.session.rollback()
        return jsonify({"message": "Failed to add hotel", "error": str(e)}), 500


# API to get all rooms
@routes.route("/api/rooms", methods=["GET"])
def get_rooms():
    try:
        hotel_id = request.args.get(
            "hotel_id", type=int
        )  # Get hotel_id from query parameters

        if hotel_id:
            # If hotel_id is provided, filter rooms by hotel_id
            rooms = Room.query.filter_by(hotel_id=hotel_id).all()
        else:
            # If hotel_id is not provided, return all rooms
            rooms = Room.query.all()

        result = []
        for room in rooms:
            result.append(
                {
                    "id": room.id,
                    "hotel_id": room.hotel_id,
                    "room_type": room.room_type,
                    "price": room.price,
                    "is_available": room.is_available,
                }
            )

        return jsonify(result), 200

    except Exception as e:
        print(e)
        return jsonify({"error": "Failed to fetch rooms."}), 500


# API to add a room
@routes.route("/api/rooms", methods=["POST"])
def add_room():
    data = request.get_json()
    hotel_id = data.get("hotel_id")
    room_type = data.get("room_type")
    price = data.get("price")
    is_available = data.get("is_available", True)

    if not hotel_id or not room_type or price is None:
        return jsonify({"error": "Missing required fields"}), 400

    hotel = Hotel.query.get(hotel_id)
    if not hotel:
        return jsonify({"error": "Hotel not found"}), 404

    new_room = Room(
        hotel_id=hotel_id, room_type=room_type, price=price, is_available=is_available
    )
    db.session.add(new_room)
    db.session.commit()

    return jsonify({"message": "Room added successfully", "room_id": new_room.id}), 201


@routes.route("/api/bookings", methods=["POST"])
def book_room():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    data = request.get_json()
    room_id = data.get("room_id")
    staying_date = data.get("stay_date")
    checkout_date = data.get("checkout_date")


    if not room_id:
        return jsonify({"message": "Room ID is required"}), 400

    room = Room.query.get(room_id)
    if not room:
        return jsonify({"message": "Room not found"}), 404

    if not room.is_available:
        return jsonify({"message": "Room is not available"}), 400

    try:
        # Convert staying_date_str to a datetime object
        staying_date = datetime.strptime(staying_date, "%Y-%m-%d")
        checkout_date = datetime.strptime(checkout_date, "%Y-%m-%d")
    except ValueError:
        return jsonify({"message": "Invalid date format. Use YYYY-MM-DD."}), 400

    # Create a new booking
    booking = Booking(
        user_id=user.id, room_id=room_id, staying_date=staying_date, checkout_date=checkout_date, status="booked"
    )

    # Ensure the booking_date is set (if it's None, use the current time)
    if not booking.booking_date:
        booking.booking_date = datetime.utcnow()

    # Calculate final price and discount for the booking
    booking.calculate_final_price()

    # Mark the room as unavailable
    room.is_available = False

    # Add to the database session and commit
    db.session.add(booking)
    db.session.commit()

    return (
        jsonify(
            {
                "message": "Room booked successfully",
                "booking_id": booking.id,
                "final_price": booking.final_price,
                "discount": booking.discount,
            }
        ),
        201,
    )


@routes.route("/api/bookings", methods=["GET"])
def get_user_bookings():
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    # Fetch bookings for the logged-in user
    bookings = Booking.query.filter_by(user_id=user.id).all()

    # Serialize booking data with hotel name, room price, staying date, discount, and final price
    bookings_data = []
    for booking in bookings:
        room = Room.query.get(booking.room_id)  # Assuming Room model has room details
        hotel = Hotel.query.get(room.hotel_id)  # Assuming Hotel model has hotel details

        # Ensure discount and final price are calculated
        booking.calculate_final_price()

        bookings_data.append(
            {
                "id": booking.id,
                "room_id": booking.room_id,
                "hotel_name": hotel.name,  # Include the hotel name
                "room_price": room.price,  # Include the room price
                "booking_date": booking.booking_date,
                "staying_date": booking.staying_date,
                "checkout_date": booking.checkout_date,
                "status": booking.status,
                "discount": booking.discount,  # Add the discount
                "final_price": booking.final_price,  # Add the final price after discount
            }
        )

    return jsonify({"bookings": bookings_data}), 200


# API to cancel a booking
@routes.route("/api/bookings/<int:booking_id>", methods=["DELETE"])
def cancel_booking(booking_id):
    token = request.headers.get("Authorization")
    if not token:
        return jsonify({"message": "Token is missing"}), 401

    token = token.split(" ")[1] if " " in token else token
    try:
        decoded = jwt.decode(token, SECRET_KEY, algorithms=["HS256"])
        user = User.query.get(decoded["id"])
    except jwt.ExpiredSignatureError:
        return jsonify({"message": "Token has expired"}), 401
    except jwt.InvalidTokenError:
        return jsonify({"message": "Invalid token"}), 401

    booking = Booking.query.get(booking_id)
    if not booking:
        return jsonify({"message": "Booking not found"}), 404

    if booking.user_id != user.id:
        return jsonify({"message": "You can only cancel your own bookings"}), 403

    # Cancel the booking and make the room available again
    room = booking.room
    room.is_available = True
    booking.status = "canceled"
    db.session.commit()

    return jsonify({"message": "Booking canceled successfully"}), 200


@routes.route("/api/hotels/<int:hotel_id>", methods=["PUT"])
def update_hotel(hotel_id):
    try:
        # Fetch the hotel by ID
        hotel = Hotel.query.get(hotel_id)
        if not hotel:
            return jsonify({"message": "Hotel not found"}), 404

        # Get updated data from request
        data = request.get_json()
        hotel.name = data.get("name", hotel.name)
        hotel.city = data.get("city", hotel.city)
        hotel.capacity = data.get("capacity", hotel.capacity)
        hotel.peak_season_rate = data.get("peak_season_rate", hotel.peak_season_rate)
        hotel.off_peak_rate = data.get("off_peak_rate", hotel.off_peak_rate)

        # Commit the changes
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Hotel updated successfully",
                    "hotel": {
                        "id": hotel.id,
                        "name": hotel.name,
                        "city": hotel.city,
                        "capacity": hotel.capacity,
                        "peak_season_rate": hotel.peak_season_rate,
                        "off_peak_rate": hotel.off_peak_rate,
                    },
                }
            ),
            200,
        )

        # return jsonify({"message": "Hotel updated successfully"}), 200
    except Exception as e:
        return jsonify({"message": "Error updating hotel", "error": str(e)}), 500


@routes.route("/api/hotels/<int:hotel_id>", methods=["DELETE"])
def delete_hotel(hotel_id):
    try:
        # Fetch the hotel by ID
        hotel = Hotel.query.get(hotel_id)
        if not hotel:
            return jsonify({"message": f"Hotel with ID {hotel_id} not found"}), 404

        # Optional: Check for any existing bookings or dependencies
        if hasattr(hotel, "bookings") and hotel.bookings.count() > 0:
            return (
                jsonify(
                    {
                        "message": "Cannot delete hotel with existing bookings",
                        "bookings_count": hotel.bookings.count(),
                    }
                ),
                409,
            )

        # Store hotel details for response
        hotel_details = {"id": hotel.id, "name": hotel.name, "city": hotel.city}

        # Delete the hotel
        db.session.delete(hotel)
        db.session.commit()

        return (
            jsonify(
                {
                    "message": "Hotel deleted successfully",
                    "deleted_hotel": hotel_details,
                }
            ),
            200,
        )

    except IntegrityError as e:
        db.session.rollback()
        return (
            jsonify(
                {
                    "message": "Cannot delete hotel due to existing relationships",
                    "error": str(e),
                }
            ),
            409,
        )

    except SQLAlchemyError as e:
        db.session.rollback()
        return jsonify({"message": "Database error occurred", "error": str(e)}), 500

    except Exception as e:
        if db.session.is_active:
            db.session.rollback()
        return jsonify({"message": "Unexpected error occurred", "error": str(e)}), 500


# reports


def get_booking_revenue_report(start_date, end_date):
    bookings = Booking.query.filter(
        Booking.booking_date >= start_date,
        Booking.booking_date <= end_date,
        Booking.status == "confirmed",
    ).all()

    total_revenue = sum(booking.final_price for booking in bookings)

    report = {
        "Start Date": start_date.strftime("%Y-%m-%d"),
        "End Date": end_date.strftime("%Y-%m-%d"),
        "Total Revenue": total_revenue,
        "Number of Bookings": len(bookings),
    }

    return report


@routes.route("/api/report/revenue", methods=["GET"])
def booking_revenue_report():
    start_date = request.args.get("start_date")
    end_date = request.args.get("end_date")

    if not start_date or not end_date:
        return jsonify({"error": "Start date and end date are required"}), 400

    try:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        end_date = datetime.strptime(end_date, "%Y-%m-%d")

    except ValueError:
        return jsonify({"error": "Invalid date format. Use YYYY-MM-DD"}), 400

    report = get_booking_revenue_report(start_date, end_date)
    return jsonify(report)


def get_top_users(limit=5):
    # Assuming 'Booking.status' is the field that tracks booking status, where 'canceled' is the canceled status
    users = (
        User.query.join(Booking)
        .filter(Booking.status != "canceled")  # Exclude canceled bookings
        .group_by(User.id)
        .order_by(db.func.sum(Booking.final_price).desc())
        .limit(limit)
        .all()
    )

    report = []

    for user in users:
        # Calculate total spent from non-canceled bookings only
        total_spent = sum(
            booking.final_price
            for booking in user.bookings
            if booking.status != "canceled"
        )
        report.append(
            {
                "User ID": user.id,
                "Username": user.username,
                "Email": user.email,
                "Total Spend": total_spent,
                "Number of Bookings": sum(
                    1 for booking in user.bookings if booking.status != "canceled"
                ),
            }
        )

    return report


@routes.route("/api/report/top-users", methods=["GET"])
def top_users_report():
    limit = request.args.get("limit", default=5, type=int)
    report = get_top_users(limit)
    return jsonify(report)


def get_all_time_top_sales_by_hotel():
    # Query all confirmed bookings
    bookings = Booking.query.filter(Booking.status == "booked").all()

    # Aggregate sales by hotel
    hotel_sales = {}
    print(bookings)
    for booking in bookings:
        hotel = booking.room.hotel
        print(hotel)
        if hotel.id not in hotel_sales:
            hotel_sales[hotel.id] = {
                "hotel_name": hotel.name,
                "city": hotel.city,
                "total_sales": 0,
            }
        hotel_sales[hotel.id]["total_sales"] += booking.final_price

    # Find the top-performing hotel
    top_hotel = max(hotel_sales.values(), key=lambda x: x["total_sales"], default=None)

    return {
        "top_hotel": top_hotel,
        "all_hotels": list(hotel_sales.values()),
    }
@routes.route("/api/sales/top-hotel", methods=["GET"])
def all_time_top_sales_by_hotel():
    try:
        report = get_all_time_top_sales_by_hotel()
        return jsonify(report), 200
    except Exception as e:
        return jsonify({"error": str(e)}), 500


CORS(app, resources={r"/api/*": {"origins": "*"}})
app.register_blueprint(routes)

if __name__ == '__main__':
    # Make sure the app is in the context before creating the tables
    with app.app_context():
        db.create_all()  # Create database tables

    app.run(debug=True)
