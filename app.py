from flask import Flask, render_template, request, jsonify, send_file,Response,redirect, url_for, session
# from flask_session import Session
from pymongo import MongoClient
import gridfs
from bson import ObjectId
import io
from cryptography.fernet import Fernet
from datetime import timedelta, datetime
from uuid import uuid4

import base64
import json
import time

# In-memory session token store
valid_tokens = {}  # token -> {email, id, expiry}
valid_bio_data = {}
TOKEN_EXPIRY = timedelta(minutes=20)

pi_message = None
pi_status=None
CENTER_NAME=None

# Initialize Flask app
app = Flask(__name__)
app.secret_key = "my_secret_key_is_very_long_and_random_1234567890abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ!@#$%^&*()"
app.permanent_session_lifetime = timedelta(minutes=20)

# MongoDB connection
client = MongoClient("mongodb+srv://User-devwithme:user-devwithme@api-checkup.it4iz.mongodb.net/?retryWrites=true&w=majority")
db = client["new_voter_register_db"]
collection = db['voter_register_collection']
fs = gridfs.GridFS(db)

officer_db=client['Officer']
officer_collection=officer_db["Poling Officer"]

vote_database=client["official_website_db"]
vote_collection=vote_database["votes"]

little_db=client["Comuniceting_DB"]
little_collection=None

#failed database collection 
failed_db=client["failed_attempts"]
failed_collection=failed_db["users"]
#voted database

# Encryption key
key = b'_d9SNtBvMGuEEV2vcC_FfbHzw2BSY9SQzdpNCNtEhXI='
cipher_suite = Fernet(key)  

CURRENT_VOTER_ID=None
CURRENT_USER_BIOMETRIC=None
ID_AUTH_KEY=None

def string_to_bytes(input_string: str, encoding: str = 'utf-8') -> bytes:
    return input_string.encode(encoding)

def decrypt_data(encrypted_data):
    """
    Decrypts the given encrypted data using Fernet symmetric encryption.
    Handles both normal string data and numerical list data.
    """
    try:
        decrypted_bytes = cipher_suite.decrypt(encrypted_data)  # Decrypt the data

        try:
            # Attempt to decode as a string
            return decrypted_bytes.decode()
        except UnicodeDecodeError:
            # If decoding fails, return as a list of integers
            return list(decrypted_bytes)
    except Exception as e:
        print("Error decoding decrypted data:", e)
        return None
# def decrypt_all_data(encrypted_data):
def decrypt_all_data(encrypted_data):
    """
    Decrypts the given encrypted data using Fernet symmetric encryption.
    """
    decrypted_data = cipher_suite.decrypt(encrypted_data)    
    
    try:
        return decrypted_data.decode()  # Convert bytes back to string if possible
    except Exception as e:
        print("Error decoding decrypted data:", e)
        return list(encrypted_data)  # Convert bytes back to list of integers if string conversion fails

def get_image_from_gridfs(photo_file_id):
    try:
        image_file = fs.get(photo_file_id)
        return image_file.read()
    except Exception as e:
        print(f"Error retrieving image: {e}")
        return None
def check_voter_is_not_voted(voter_id):
    if vote_collection.find_one({"voterId":voter_id}):
        return False
    return True

def get_voter_data(voter_id):
    if check_voter_is_not_voted(voter_id)==True:
        STAMP=session["STAMP"]
        # print("\n\n",STAMP,"\n")

        try:
            voter = collection.find_one({"voter_id": voter_id})
            if voter:  
                global CURRENT_USER_BIOMETRIC,ID_AUTH_KEY
                # CURRENT_VOTER_ID=voter["voter_id"]
                session["CURRENT_VOTER_ID"]=voter["voter_id"]
                CURRENT_USER_BIOMETRIC=voter["fingerprint_data"]
                session["ID_AUTH_KEY"]=voter["identity_key"]
                # print(CURRENT_USER_BIOMETRIC)
                # print(voter["photo_file_id"])
                image_id=ObjectId(voter["photo"])
                file = fs.get(image_id)
                encrypted_Fingerprint_data=voter["fingerprint_data"]
                decrypted_Fingerprint_data=decrypt_data(encrypted_Fingerprint_data)

                # print("*************",decrypted_Fingerprint_data,"*************")
                
                with open("retrived_image.jpg", "wb") as f:
                        f.write(file.read())
                return {
                    # "id": str(voter["_id"]),
                    "name": voter["name"],
                    "date_of_birth":voter["date_of_birth"],
                    "voterId": voter["voter_id"],
                    "state": voter["state"],
                    "district": voter["district"],
                    "constitution": voter["constituency"],
                    "gender": voter["gender"],
                    "pin":voter["pin"],
                    "area":voter["area"],
                                        
                    "fingerprint": decrypted_Fingerprint_data,
                    "STAMP":STAMP,
                    "vote_status":"not voted"
                                       
                }
            
            return None
        except Exception as e:
            print(f"Error retrieving voter data: {e}")
            return None
    return {"vote_status":"Voter Already Voted"}
#default route
@app.route("/", methods=["GET", "POST"])
def handle_login():
    if request.method == "POST":
        data = request.get_json()
        if not data:
            return jsonify({"error": "No data provided"}), 400

        user_id = data.get("id")
        encrypted_user_email = data.get("email")
        encrypted_polling_center_stamp=data.get("polling_center")

        # print("\nId=",user_id,"\nemail=",encrypted_user_email,"\n center=",encrypted_polling_center_stamp)
        user_email=decrypt_data(string_to_bytes(encrypted_user_email))
        polling_center_stamp=decrypt_data(string_to_bytes(encrypted_polling_center_stamp))

        print("\n\n\nId=",user_id,"\nemail=",user_email,"\n center=",polling_center_stamp)
               
        # little database collection connection creating for one polling booth
        global little_collection
        polling_center_stamp=str(polling_center_stamp)
        little_collection=little_db[polling_center_stamp]


        if not user_id or not user_email:
            return jsonify({"error": "Missing id or email"}), 400

        # officer_data=officer_collection.find_one({"officer_id":user_id})
        if officer_collection.find_one({"officer_id":user_id}):
            
            token = str(uuid4())
            expiry = datetime.utcnow() + TOKEN_EXPIRY

            valid_tokens[token] = {
                    "USER_ID": user_id,
                    "USER_EMAIL": user_email,
                    "STAMP":polling_center_stamp,
                    "expires_at": expiry,
                }
            
            redirect_url = url_for("search_page", token=token, _external=True)
            return redirect(redirect_url)
            
                
        else:
            
            return jsonify({"error": "Invalid user credentials"}), 505

        
    return "Please POST login credentials to access the search page.", 401

@app.route("/search_page", methods=["GET", "POST"])
def search_page():
    token = request.args.get("token")

    if "USER_ID" in session and "USER_EMAIL" in session and "STAMP" in session:
        pass
    elif token in valid_tokens:
        token_data = valid_tokens[token]
        if token_data["expires_at"] > datetime.utcnow():
            session.permanent = True
            session["USER_ID"] = token_data["USER_ID"]
            session["USER_EMAIL"] = token_data["USER_EMAIL"]
            session["STAMP"] = token_data["STAMP"]
            if not session.get("first_activity"):
                session["first_activity"] = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S.%f")
        else:
            del valid_tokens[token]
            return redirect(url_for("handle_login"))
    else:
        return redirect(url_for("handle_login"))

    if request.method == "GET":
        return render_template("search.html")

    if request.method == "POST":
        voter_id = request.form.get("voter_id")
        print(f"\n\n voter Id given :{voter_id} ")
        voter_data = get_voter_data(voter_id)
        if voter_data["vote_status"]!="Voter Already Voted":
            #debug
            print("\n\n data exist and not voted\n")
            try:
                if little_collection !=None:
                    if little_collection.count_documents({}) == 0:
                        little_collection.insert_one(voter_data)
                        print("collection ready")
                    else :
                        print("One Data sent to the collection, Please wait")
                else:
                    print("little database not found")
            except Exception as e:
                print("one data already stored", e)

            if voter_data:
                # Safely serialize data for JSON
                for key in list(voter_data.keys()):
                    value = voter_data[key]
                    if isinstance(value, bytes):
                        voter_data[key] = value.decode("utf-8", errors="ignore")
                    elif isinstance(value, ObjectId):
                        voter_data[key] = str(value)

                try:
                    with open("retrived_image.jpg", "rb") as img_file:
                        image_bytes = img_file.read()
                        encoded_image = base64.b64encode(image_bytes).decode('utf-8')
                    voter_data["photo_base64"] = encoded_image
                except Exception as e:
                    print("Error encoding image:", e)
                    voter_data["photo_base64"] = None

                return jsonify(voter_data)
            else:
                return jsonify({"error": "Voter not found"}), 404
            
        elif voter_data["vote_status"]=="Voter Already Voted":
            print("\n\n voted\n\n")
            return jsonify({"vote_status":"Voter already Voted"})


@app.route('/logout')
def logout():
    session["active_window"] = False
    session.clear()
    print("Session ended")
    return render_template("logout.html")

@app.route("/check_session")
def check_session():
    user_id = session.get("USER_ID")
    user_email = session.get("USER_EMAIL")
    now = datetime.utcnow()
    first_activity = session.get("first_activity")

    print("Session Check → USER_ID:", user_id, "| USER_EMAIL:", user_email)

    if user_id and user_email and first_activity:
        first_activity_time = datetime.strptime(first_activity, "%Y-%m-%d %H:%M:%S.%f")
        if (now - first_activity_time).total_seconds() < app.permanent_session_lifetime.total_seconds():
            return jsonify({"active": True})
        else:
            session.clear()
            print("Session expired due to timeout.")
            return jsonify({"active": False, "message": "session ended"}), 401
    else:
        print("No valid session found.")
        return jsonify({"active": False, "message": "session ended"}), 401

@app.route("/pi_response", methods=["POST"])
def evm_response():
    global pi_message,ID_AUTH_KEY,pi_status
    if request.method == "POST":

        if vote_collection.find_one({"voter_id":CURRENT_VOTER_ID}):
        
            pi_status = True              

            return jsonify({"response": "Vote received"}), 200
        
    return "Invalid request", 400

    #if vote done properly
    
    # 
@app.route('/events')
def events():
    def event_stream():
        global pi_message
        last_message = None
        while True:
            if pi_message != last_message:
                last_message = pi_message
                if last_message:
                    yield f"data: {last_message}\n\n"
            time.sleep(1)
    return Response(event_stream(), mimetype="text/event-stream")

@app.route("/get_pi_response", methods=["GET"])
def get_pi_response():   
    global pi_status,pi_message

    CURRENT_VOTER_ID=session["CURRENT_VOTER_ID"]
    # voter_id should be changed in voterId in final testing
    voting_status=vote_collection.find_one({"voterId":CURRENT_VOTER_ID})
    if voting_status:


        return jsonify({"message": f"Vote Succesfull for{CURRENT_VOTER_ID}","signal":True})
    
    elif failed_collection.find_one({"voterId":CURRENT_VOTER_ID}):
        return jsonify({"message": "Biometric not matched!!\n Warning!!","signal":False})
    else :
        return None


# ****************************makeing browser specification for securinty*********************
@app.before_request
def only_allow_edge_browser():
    user_agent = request.headers.get('User-Agent', '')
    # print(f"User-Agent: {user_agent}")

    # Allow if request comes from Edge browser
    if "Edg/" in user_agent or "Edge/" in user_agent:
        return  # Allow

    # Allow if request comes from Python requests (for API posting)
    if user_agent.startswith("python-requests/"):
        return  # Allow

    # Otherwise, block
    return "❌ Access Denied: Please use Microsoft Edge Browser only.", 403



@app.route("/validate_tab", methods=["POST"])
def validate_tab():
    tab_id = request.json.get("tab_id")

    if "tab_id" not in session:
        session["tab_id"] = tab_id
        return jsonify(allowed=True)

    if session["tab_id"] == tab_id:
        return jsonify(allowed=True)
    
    return jsonify(allowed=False)

@app.route("/clear_tab", methods=["POST"])
def clear_tab():
    # On window unload
    tab_id = request.json.get("tab_id")
    if session.get("tab_id") == tab_id:
        session.pop("tab_id", None)
    return '', 204

@app.route("/already_open")
def already_open():
    return "<h1>Access Blocked: Only one active tab allowed!</h1>"



#**************************************************************************
SESSION_TIMEOUT = 10
@app.route('/protected')
def protected():
    # Check if session active
    if not session.get('active_tab'):
        session['active_tab'] = True
        session['last_active'] = datetime.utcnow()
        return "Protected Page Loaded. <script src='/static/main.js'></script>"

    # Session already active, check heartbeat
    last_active = session.get('last_active')
    if last_active and datetime.utcnow() - last_active < timedelta(seconds=SESSION_TIMEOUT):
        return redirect(url_for('blocked'))

    # Otherwise, allow and reset active
    session['last_active'] = datetime.utcnow()
    return "Protected Page Loaded. <script src='/static/main.js'></script>"

@app.route('/heartbeat', methods=['POST'])
def heartbeat():
    # Update last_active time
    session['last_active'] = datetime.utcnow()
    return jsonify(status='alive')

@app.route('/blocked')
def blocked():
    return "<h1>Blocked: Only one active tab allowed!</h1>"

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=3000) 
