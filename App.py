from flask import Flask, jsonify, request
from cent import Client
import mariadb
import json
from datetime import datetime, timedelta
from flask_cors import CORS
from flask_bcrypt import Bcrypt
from flask_jwt_extended import (
    JWTManager,
    create_access_token,
    jwt_required,
    get_jwt_identity,
)

app = Flask(__name__)
CORS(app)
bcrypt = Bcrypt(app)
app.config["JWT_SECRET_KEY"] = (
    "5e23747839d30aa094caff9fb1b7e62d36439372229d88ddfcf00eda3e5e600b"
)
jwt = JWTManager(app)

ACCESS_TOKEN_EXPIRES = timedelta(minutes=30)
app.config["JWT_ACCESS_TOKEN_EXPIRES"] = ACCESS_TOKEN_EXPIRES

CENTRIFUGO_URL = "http://localhost:8000/api"
CENTRIFUGO_API_KEY = "a04f1d0865bffa3c982f319bb84b35af97738f8953e11b0d746727028e40d548"

centrifugo_client = Client(CENTRIFUGO_URL, api_key=CENTRIFUGO_API_KEY)


def get_db_connection():
    conn = mariadb.connect(
        user="root",
        password="",
        host="localhost",
        port=3306,
        database="chat_app",
    )
    return conn


@app.route("/register", methods=["POST"])
def register():
    data = request.get_json()
    fullname = data["fullname"]
    username = data["username"]
    password = data["password"]

    password_hash = bcrypt.generate_password_hash(password).decode("utf-8")

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (fullname, username, password_hash) VALUES (?, ?, ?)",
            (fullname, username, password_hash),
        )
        conn.commit()
        conn.close()
        return jsonify({"message": f"User {username} registered successfully"}), 200
    except mariadb.Error as e:
        return jsonify({"error": str(e)}), 400


@app.route("/login", methods=["POST"])
def login():
    data = request.get_json()
    username = data["username"]
    password = data["password"]

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT id, password_hash, username, fullname FROM users WHERE username = ?",
        (username,),
    )
    user = cursor.fetchone()
    conn.close()

    if user and bcrypt.check_password_hash(user[1], password):
        access_token = create_access_token(identity=user[0])
        return (
            jsonify(
                {
                    "access_token": access_token,
                    "user_id": user[0],
                    "username": user[2],
                    "fullname": user[3],
                }
            ),
            200,
        )
    else:
        return jsonify({"message": "Invalid username or password"}), 401


@app.route("/protected/users", methods=["GET"])
def get_users():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id, username, fullname FROM users")
    users = cursor.fetchall()
    conn.close()

    user_list = [
        {"id": user[0], "username": user[1], "fullname": user[2]} for user in users
    ]
    return jsonify(user_list)


def get_user_id_by_name(name):
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT id FROM users WHERE username = ?", (name,))
    user = cursor.fetchone()
    conn.close()
    return user[0]


def serialize_row(row, columns):
    """Convert row tuple to dictionary and handle datetime fields."""
    data_dict = {}
    for idx, col in enumerate(columns):
        value = row[idx]
        if isinstance(value, datetime):
            data_dict[col] = value.isoformat()
        else:
            data_dict[col] = value
    return data_dict


@app.route("/protected/groups", methods=["POST"])
def get_groups():
    data = request.get_json()
    username = data["username"]
    user_id = get_user_id_by_name(username.strip())

    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "SELECT * FROM groups INNER JOIN group_members ON (group_members.group_id = groups.id) WHERE group_members.user_id = ?",
        (user_id,),
    )
    groups = cursor.fetchall()
    columns = [description[0] for description in cursor.description]
    conn.close()
    groups_list = [serialize_row(group, columns) for group in groups]
    return jsonify(groups_list)


@app.route("/protected/create_group", methods=["POST"])
def create_group():
    data = request.get_json()
    group_name = data["group_name"]
    member_ids = data["member_ids"]
    created_by = data["created_by"]

    conn = get_db_connection()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO groups (group_name, created_by) VALUES (?, ?)",
        (group_name, created_by),
    )
    group_id = cursor.lastrowid

    for member_id in member_ids:
        cursor.execute(
            "INSERT INTO group_members (group_id, user_id) VALUES (?, ?)",
            (group_id, member_id),
        )

    conn.commit()
    conn.close()

    return jsonify({"success": True, "group_id": group_id, "group_name": group_name})


@app.route("/protected/send", methods=["POST"])
@jwt_required()
def send_message():
    data = request.get_json()
    sender_id = data["sender_id"]
    message_text = data["message"]
    recipient_id = data.get("recipient_id")
    group_id = data.get("group_id")

    conn = get_db_connection()
    cursor = conn.cursor()

    if recipient_id:
        cursor.execute(
            "INSERT INTO messages (sender_id, recipient_id, message) VALUES (?, ?, ?)",
            (sender_id, recipient_id, message_text),
        )
        conn.commit()
        centrifugo_client.publish(
            f"user_{recipient_id}", {"username": sender_id, "message": message_text}
        )

    elif group_id:
        cursor.execute(
            "INSERT INTO group_messages (group_id, sender_id, message) VALUES (?, ?, ?)",
            (group_id, sender_id, message_text),
        )
        conn.commit()
        centrifugo_client.publish(
            f"group_{group_id}", {"username": sender_id, "message": message_text}
        )

    conn.close()
    return jsonify({"success": True})


@app.route("/protected", methods=["GET"])
@jwt_required()
def protected():
    current_user_id = get_jwt_identity()
    return jsonify({"message": f"Welcome user {current_user_id}!"}), 200


if __name__ == "__main__":
    app.run(debug=True)
